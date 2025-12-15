"""
Unit tests for authentication bug fix

Tests cover:
1. Token generation and validation
2. Session expiration handling
3. Timezone-aware datetime handling
4. Edge cases and error conditions
5. Session refresh logic
"""

import unittest
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import sys
import os

# Import the fixed authentication module
from auth_fix import SessionManager, AuthService, AuthenticationError, migrate_existing_sessions


class TestSessionManager(unittest.TestCase):
    """Test cases for SessionManager class"""
    
    def setUp(self):
        """Set up test database before each test"""
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Create test tables
        self.cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Insert test user
        self.cursor.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
            (1, "test@example.com", "dummyhash")
        )
        self.conn.commit()
        
        self.session_manager = SessionManager(self.conn)
    
    def tearDown(self):
        """Clean up after each test"""
        self.conn.close()
    
    def test_generate_secure_token(self):
        """Test that tokens are generated with correct length and uniqueness"""
        token1 = self.session_manager.generate_secure_token()
        token2 = self.session_manager.generate_secure_token()
        
        # Check length (hex encoding doubles the byte length)
        self.assertEqual(len(token1), 64)
        self.assertEqual(len(token2), 64)
        
        # Check uniqueness
        self.assertNotEqual(token1, token2)
        
        # Check format (hexadecimal)
        self.assertTrue(all(c in '0123456789abcdef' for c in token1))
    
    def test_create_session(self):
        """Test session creation"""
        token, expires_at = self.session_manager.create_session(1)
        
        # Verify token format
        self.assertEqual(len(token), 64)
        
        # Verify expiration is in the future
        self.assertGreater(expires_at, datetime.now(timezone.utc))
        
        # Verify session is in database
        result = self.cursor.execute(
            "SELECT user_id, token FROM sessions WHERE token = ?",
            (token,)
        ).fetchone()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 1)
        self.assertEqual(result[1], token)
    
    def test_validate_token_success(self):
        """Test successful token validation"""
        token, _ = self.session_manager.create_session(1)
        
        user_id = self.session_manager.validate_token(token)
        self.assertEqual(user_id, 1)
    
    def test_validate_token_not_found(self):
        """Test validation of non-existent token"""
        fake_token = "a" * 64
        
        with self.assertRaises(AuthenticationError) as context:
            self.session_manager.validate_token(fake_token)
        
        self.assertIn("not found", str(context.exception).lower())
    
    def test_validate_token_invalid_format(self):
        """Test validation of malformed token"""
        with self.assertRaises(AuthenticationError) as context:
            self.session_manager.validate_token("short")
        
        self.assertIn("invalid", str(context.exception).lower())
    
    def test_validate_token_expired(self):
        """Test validation of expired token"""
        # Create session with past expiration
        token = self.session_manager.generate_secure_token()
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        self.cursor.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (1, token, expires_at)
        )
        self.conn.commit()
        
        with self.assertRaises(AuthenticationError) as context:
            self.session_manager.validate_token(token)
        
        self.assertIn("expired", str(context.exception).lower())
        
        # Verify expired session was deleted
        result = self.cursor.execute(
            "SELECT * FROM sessions WHERE token = ?",
            (token,)
        ).fetchone()
        self.assertIsNone(result)
    
    def test_validate_token_timezone_aware(self):
        """Test that timezone-aware datetime handling works correctly"""
        # Create session with timezone-aware expiration
        token = self.session_manager.generate_secure_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        
        self.cursor.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (1, token, expires_at)
        )
        self.conn.commit()
        
        # Should validate successfully
        user_id = self.session_manager.validate_token(token)
        self.assertEqual(user_id, 1)
    
    def test_session_refresh_logic(self):
        """Test that sessions close to expiring are automatically refreshed"""
        # Create session expiring in 30 minutes (less than refresh threshold)
        token = self.session_manager.generate_secure_token()
        original_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        self.cursor.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (1, token, original_expires_at)
        )
        self.conn.commit()
        
        # Validate token (should trigger refresh)
        user_id = self.session_manager.validate_token(token)
        self.assertEqual(user_id, 1)
        
        # Check that expiration was extended
        result = self.cursor.execute(
            "SELECT expires_at FROM sessions WHERE token = ?",
            (token,)
        ).fetchone()
        
        new_expires_at = datetime.fromisoformat(result[0])
        if new_expires_at.tzinfo is None:
            new_expires_at = new_expires_at.replace(tzinfo=timezone.utc)
        
        # New expiration should be much later than original
        self.assertGreater(new_expires_at, original_expires_at + timedelta(hours=20))
    
    def test_revoke_session(self):
        """Test session revocation"""
        token, _ = self.session_manager.create_session(1)
        
        # Revoke session
        result = self.session_manager.revoke_session(token)
        self.assertTrue(result)
        
        # Verify session is gone
        db_result = self.cursor.execute(
            "SELECT * FROM sessions WHERE token = ?",
            (token,)
        ).fetchone()
        self.assertIsNone(db_result)
        
        # Try revoking again (should return False)
        result = self.session_manager.revoke_session(token)
        self.assertFalse(result)
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions"""
        # Create mix of valid and expired sessions
        valid_token = self.session_manager.generate_secure_token()
        valid_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        
        expired_token1 = self.session_manager.generate_secure_token()
        expired_token2 = self.session_manager.generate_secure_token()
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        self.cursor.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (1, valid_token, valid_expires)
        )
        self.cursor.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (1, expired_token1, expired_time)
        )
        self.cursor.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (1, expired_token2, expired_time)
        )
        self.conn.commit()
        
        # Run cleanup
        deleted_count = self.session_manager.cleanup_expired_sessions()
        self.assertEqual(deleted_count, 2)
        
        # Verify only valid session remains
        remaining = self.cursor.execute("SELECT token FROM sessions").fetchall()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0][0], valid_token)


class TestAuthService(unittest.TestCase):
    """Test cases for AuthService class"""
    
    def setUp(self):
        """Set up test database before each test"""
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Create test tables
        self.cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        self.conn.commit()
        self.auth_service = AuthService(self.conn)
    
    def tearDown(self):
        """Clean up after each test"""
        self.conn.close()
    
    def test_login_success(self):
        """Test successful login"""
        # Insert test user with known password hash
        import hashlib
        password = "testpassword123"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        self.cursor.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
            (1, "user@example.com", password_hash)
        )
        self.conn.commit()
        
        # Attempt login
        token = self.auth_service.login("user@example.com", password)
        
        self.assertIsNotNone(token)
        self.assertEqual(len(token), 64)
    
    def test_login_wrong_password(self):
        """Test login with incorrect password"""
        import hashlib
        password_hash = hashlib.sha256("correctpassword".encode()).hexdigest()
        
        self.cursor.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
            (1, "user@example.com", password_hash)
        )
        self.conn.commit()
        
        # Attempt login with wrong password
        token = self.auth_service.login("user@example.com", "wrongpassword")
        
        self.assertIsNone(token)
    
    def test_login_user_not_found(self):
        """Test login with non-existent user"""
        token = self.auth_service.login("nonexistent@example.com", "password")
        self.assertIsNone(token)
    
    def test_authenticate_request(self):
        """Test request authentication"""
        import hashlib
        password_hash = hashlib.sha256("password".encode()).hexdigest()
        
        self.cursor.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
            (1, "user@example.com", password_hash)
        )
        self.conn.commit()
        
        # Login to get token
        token = self.auth_service.login("user@example.com", "password")
        
        # Authenticate request
        user_id = self.auth_service.authenticate_request(token)
        self.assertEqual(user_id, 1)
    
    def test_logout(self):
        """Test logout functionality"""
        import hashlib
        password_hash = hashlib.sha256("password".encode()).hexdigest()
        
        self.cursor.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
            (1, "user@example.com", password_hash)
        )
        self.conn.commit()
        
        # Login
        token = self.auth_service.login("user@example.com", "password")
        
        # Logout
        result = self.auth_service.logout(token)
        self.assertTrue(result)
        
        # Try to authenticate with logged out token
        user_id = self.auth_service.authenticate_request(token)
        self.assertIsNone(user_id)


class TestMigration(unittest.TestCase):
    """Test cases for database migration"""
    
    def test_migrate_existing_sessions(self):
        """Test migration of timezone-naive sessions"""
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        
        # Insert sessions with timezone-naive timestamps
        naive_time = datetime(2025, 12, 31, 12, 0, 0)
        cursor.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (1, "token1", naive_time.isoformat())
        )
        cursor.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (1, "token2", naive_time.isoformat())
        )
        conn.commit()
        
        # Run migration
        updated = migrate_existing_sessions(conn)
        self.assertEqual(updated, 2)
        
        conn.close()


if __name__ == '__main__':
    unittest.main()
