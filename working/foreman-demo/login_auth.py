"""
Authentication Manager with Session Management

This module implements secure user authentication with the following features:
- Sliding window session expiration (fixes intermittent auth failures)
- Thread-safe session management
- Secure password hashing
- Session cleanup for expired sessions

Bug Fix: Implements sliding window session expiration where each session validation
extends the session timeout, preventing active users from being logged out.
"""

import hashlib
import secrets
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class AuthenticationManager:
    """
    Manages user authentication and session handling.
    
    Key features:
    - Sliding window session expiration: Active sessions are automatically extended
    - Thread-safe operations using locks
    - Secure token generation using secrets module
    - Automatic cleanup of expired sessions
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        """
        Initialize the authentication manager.
        
        Args:
            session_timeout_minutes: Session timeout duration in minutes (default: 30)
        """
        self.session_timeout_minutes = session_timeout_minutes
        self.users: Dict[str, Dict[str, Any]] = {}  # username -> user data
        self.sessions: Dict[str, Dict[str, Any]] = {}  # token -> session data
        self._users_lock = threading.RLock()
        self._sessions_lock = threading.RLock()
    
    def _hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """
        Hash a password with a salt using SHA-256.
        
        Args:
            password: The plaintext password
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Combine password and salt, then hash
        combined = f"{password}{salt}".encode('utf-8')
        hashed = hashlib.sha256(combined).hexdigest()
        
        return hashed, salt
    
    def _verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: The plaintext password to verify
            hashed_password: The stored hash
            salt: The salt used for hashing
            
        Returns:
            True if password matches, False otherwise
        """
        computed_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(computed_hash, hashed_password)
    
    def register_user(self, username: str, password: str, email: str) -> bool:
        """
        Register a new user.
        
        Args:
            username: Unique username
            password: User's password (will be hashed)
            email: User's email address
            
        Returns:
            True if registration successful, False if user already exists
        """
        with self._users_lock:
            if username in self.users:
                return False
            
            # Hash the password
            hashed_password, salt = self._hash_password(password)
            
            # Store user data
            self.users[username] = {
                'username': username,
                'password_hash': hashed_password,
                'salt': salt,
                'email': email,
                'created_at': datetime.now()
            }
            
            return True
    
    def login(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate a user and create a session.
        
        Args:
            username: The username
            password: The password
            
        Returns:
            Session token if authentication successful, None otherwise
        """
        with self._users_lock:
            # Check if user exists
            if username not in self.users:
                return None
            
            user = self.users[username]
            
            # Verify password
            if not self._verify_password(password, user['password_hash'], user['salt']):
                return None
        
        # Create session token
        session_token = secrets.token_urlsafe(32)
        
        with self._sessions_lock:
            # Store session with expiration time
            self.sessions[session_token] = {
                'username': username,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(minutes=self.session_timeout_minutes),
                'last_activity': datetime.now()
            }
        
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[str]:
        """
        Validate a session token and extend its expiration (sliding window).
        
        This implements the bug fix: Each validation extends the session timeout,
        preventing active users from being logged out due to intermittent failures.
        
        Args:
            session_token: The session token to validate
            
        Returns:
            Username if session is valid, None otherwise
        """
        if not session_token:
            return None
        
        with self._sessions_lock:
            # Check if session exists
            if session_token not in self.sessions:
                return None
            
            session = self.sessions[session_token]
            now = datetime.now()
            
            # Check if session has expired
            if now > session['expires_at']:
                # Remove expired session
                del self.sessions[session_token]
                return None
            
            # BUG FIX: Extend session expiration (sliding window)
            # This prevents active users from being logged out
            session['expires_at'] = now + timedelta(minutes=self.session_timeout_minutes)
            session['last_activity'] = now
            
            return session['username']
    
    def logout(self, session_token: str) -> bool:
        """
        Log out a user by removing their session.
        
        Args:
            session_token: The session token to invalidate
            
        Returns:
            True if logout successful, False if session not found
        """
        with self._sessions_lock:
            if session_token in self.sessions:
                del self.sessions[session_token]
                return True
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions from memory.
        
        This should be called periodically to free up memory.
        
        Returns:
            Number of sessions removed
        """
        now = datetime.now()
        removed_count = 0
        
        with self._sessions_lock:
            expired_tokens = [
                token for token, session in self.sessions.items()
                if now > session['expires_at']
            ]
            
            for token in expired_tokens:
                del self.sessions[token]
                removed_count += 1
        
        return removed_count
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user information (excluding sensitive data).
        
        Args:
            username: The username to look up
            
        Returns:
            Dictionary with user info, or None if user not found
        """
        with self._users_lock:
            if username not in self.users:
                return None
            
            user = self.users[username]
            return {
                'username': user['username'],
                'email': user['email'],
                'created_at': user['created_at']
            }
    
    def get_active_sessions_count(self) -> int:
        """
        Get the count of currently active (non-expired) sessions.
        
        Returns:
            Number of active sessions
        """
        # First cleanup expired sessions
        self.cleanup_expired_sessions()
        
        with self._sessions_lock:
            return len(self.sessions)


# Example usage
if __name__ == "__main__":
    # Create authentication manager
    auth = AuthenticationManager(session_timeout_minutes=30)
    
    # Register a user
    if auth.register_user("john_doe", "secure_password123", "john@example.com"):
        print("✓ User registered successfully")
    
    # Login
    token = auth.login("john_doe", "secure_password123")
    if token:
        print(f"✓ Login successful, token: {token[:20]}...")
    
    # Validate session
    username = auth.validate_session(token)
    if username:
        print(f"✓ Session valid for user: {username}")
    
    # Get user info
    user_info = auth.get_user_info("john_doe")
    if user_info:
        print(f"✓ User info: {user_info}")
    
    # Logout
    if auth.logout(token):
        print("✓ Logout successful")
    
    # Verify session is invalid after logout
    username = auth.validate_session(token)
    if username is None:
        print("✓ Session correctly invalidated after logout")
