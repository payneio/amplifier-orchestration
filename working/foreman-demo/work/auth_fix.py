"""
Authentication Bug Fix - Token Validation and Session Management

This module addresses the intermittent authentication failures reported by users.
The fix includes:
1. Proper token validation with timezone-aware datetime handling
2. Robust session expiration checking
3. Better error handling and logging
4. Race condition prevention in token validation
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple


class AuthenticationError(Exception):
    """Custom exception for authentication failures"""
    pass


class SessionManager:
    """
    Manages user sessions with improved token validation and expiration handling.
    
    Fixes:
    - Added timezone-aware datetime comparisons to prevent timezone mismatch issues
    - Implemented proper token validation with constant-time comparison
    - Added session refresh logic to prevent premature expiration
    - Improved error handling with specific error messages for debugging
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.token_length = 32  # 256 bits of entropy
        self.session_duration = timedelta(hours=24)
        self.refresh_threshold = timedelta(hours=1)  # Refresh if < 1 hour remaining
    
    def generate_secure_token(self) -> str:
        """
        Generate a cryptographically secure random token.
        
        Returns:
            str: A secure random token as hexadecimal string
        """
        return secrets.token_hex(self.token_length)
    
    def create_session(self, user_id: int) -> Tuple[str, datetime]:
        """
        Create a new session for the user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Tuple of (token, expires_at)
        """
        token = self.generate_secure_token()
        expires_at = datetime.now(timezone.utc) + self.session_duration
        
        # Store session in database
        query = """
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """
        self.db.execute(query, (user_id, token, expires_at))
        self.db.commit()
        
        return token, expires_at
    
    def validate_token(self, token: str) -> Optional[int]:
        """
        Validate a session token and return the associated user_id.
        
        This method fixes the intermittent authentication failures by:
        1. Using timezone-aware datetime for proper expiration checking
        2. Implementing constant-time comparison to prevent timing attacks
        3. Automatically refreshing sessions that are close to expiring
        4. Properly handling edge cases and database errors
        
        Args:
            token: The session token to validate
            
        Returns:
            The user_id if token is valid, None otherwise
            
        Raises:
            AuthenticationError: If token validation fails with specific reason
        """
        if not token or len(token) != self.token_length * 2:  # hex encoding doubles length
            raise AuthenticationError("Invalid token format")
        
        try:
            # Fetch session from database
            query = """
                SELECT id, user_id, token, expires_at
                FROM sessions
                WHERE token = ?
                LIMIT 1
            """
            result = self.db.execute(query, (token,)).fetchone()
            
            if not result:
                raise AuthenticationError("Token not found")
            
            session_id, user_id, stored_token, expires_at_str = result
            
            # Use constant-time comparison to prevent timing attacks
            if not secrets.compare_digest(token, stored_token):
                raise AuthenticationError("Token mismatch")
            
            # Parse expiration time and ensure it's timezone-aware
            # This fixes the main bug - timezone handling was causing intermittent failures
            if isinstance(expires_at_str, str):
                expires_at = datetime.fromisoformat(expires_at_str)
            else:
                expires_at = expires_at_str
            
            # Ensure expires_at is timezone-aware
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            # Get current time as timezone-aware
            now = datetime.now(timezone.utc)
            
            # Check if session has expired
            if now >= expires_at:
                # Clean up expired session
                self.db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                self.db.commit()
                raise AuthenticationError("Session expired")
            
            # Auto-refresh sessions that are close to expiring
            # This prevents race conditions where a session expires during a request
            time_remaining = expires_at - now
            if time_remaining < self.refresh_threshold:
                new_expires_at = now + self.session_duration
                update_query = """
                    UPDATE sessions
                    SET expires_at = ?
                    WHERE id = ?
                """
                self.db.execute(update_query, (new_expires_at, session_id))
                self.db.commit()
            
            return user_id
            
        except AuthenticationError:
            raise
        except Exception as e:
            # Log the error for debugging
            print(f"Unexpected error during token validation: {e}")
            raise AuthenticationError(f"Token validation failed: {str(e)}")
    
    def revoke_session(self, token: str) -> bool:
        """
        Revoke a session by deleting it from the database.
        
        Args:
            token: The session token to revoke
            
        Returns:
            True if session was revoked, False if not found
        """
        query = "DELETE FROM sessions WHERE token = ?"
        result = self.db.execute(query, (token,))
        self.db.commit()
        return result.rowcount > 0
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions from the database.
        Should be run periodically as a maintenance task.
        
        Returns:
            Number of sessions deleted
        """
        now = datetime.now(timezone.utc)
        query = "DELETE FROM sessions WHERE expires_at < ?"
        result = self.db.execute(query, (now,))
        self.db.commit()
        return result.rowcount


class AuthService:
    """
    High-level authentication service that uses SessionManager.
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.session_manager = SessionManager(db_connection)
    
    def login(self, email: str, password: str) -> Optional[str]:
        """
        Authenticate a user and create a session.
        
        Args:
            email: User's email address
            password: User's password (plaintext)
            
        Returns:
            Session token if authentication succeeds, None otherwise
        """
        # Fetch user from database
        query = "SELECT id, password_hash FROM users WHERE email = ?"
        result = self.db.execute(query, (email,)).fetchone()
        
        if not result:
            return None
        
        user_id, password_hash = result
        
        # Verify password
        if not self._verify_password(password, password_hash):
            return None
        
        # Create session
        token, _ = self.session_manager.create_session(user_id)
        return token
    
    def authenticate_request(self, token: str) -> Optional[int]:
        """
        Authenticate a request using a session token.
        
        Args:
            token: The session token from the request
            
        Returns:
            User ID if authenticated, None otherwise
        """
        try:
            return self.session_manager.validate_token(token)
        except AuthenticationError as e:
            print(f"Authentication failed: {e}")
            return None
    
    def logout(self, token: str) -> bool:
        """
        Log out a user by revoking their session.
        
        Args:
            token: The session token to revoke
            
        Returns:
            True if logout succeeded, False otherwise
        """
        return self.session_manager.revoke_session(token)
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.
        
        Note: In production, use a proper password hashing library like bcrypt or argon2.
        This is a simplified example.
        """
        # This is a simplified example - use bcrypt/argon2 in production
        computed_hash = hashlib.sha256(password.encode()).hexdigest()
        return secrets.compare_digest(computed_hash, password_hash)


# Migration script to fix existing sessions
def migrate_existing_sessions(db_connection):
    """
    One-time migration to fix existing sessions in the database.
    Ensures all expires_at timestamps are timezone-aware.
    """
    query = "SELECT id, expires_at FROM sessions"
    sessions = db_connection.execute(query).fetchall()
    
    updated = 0
    for session_id, expires_at_str in sessions:
        if isinstance(expires_at_str, str):
            expires_at = datetime.fromisoformat(expires_at_str)
        else:
            expires_at = expires_at_str
        
        # If timezone-naive, assume UTC and update
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            update_query = "UPDATE sessions SET expires_at = ? WHERE id = ?"
            db_connection.execute(update_query, (expires_at, session_id))
            updated += 1
    
    db_connection.commit()
    return updated
