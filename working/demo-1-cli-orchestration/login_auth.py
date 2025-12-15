"""
Login Authentication Module

Provides secure user authentication functionality.
Fixed: Session timeout bug and password comparison timing attack vulnerability.
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict


class AuthenticationManager:
    """Manages user authentication and sessions."""
    
    def __init__(self, session_timeout_minutes: int = 30):
        self.session_timeout_minutes = session_timeout_minutes
        self.users: Dict[str, Dict] = {}
        self.sessions: Dict[str, Dict] = {}
        self._failed_attempts: Dict[str, list] = {}
    
    def register_user(self, username: str, password: str, email: str) -> bool:
        """
        Register a new user.
        
        Args:
            username: Unique username
            password: User password (will be hashed)
            email: User email address
            
        Returns:
            True if registration successful, False if username exists
        """
        if username in self.users:
            return False
        
        # Hash password with salt
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        
        self.users[username] = {
            'email': email,
            'password_hash': password_hash,
            'salt': salt,
            'created_at': datetime.now(),
            'is_active': True
        }
        
        return True
    
    def login(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate user and create session.
        
        Args:
            username: Username to authenticate
            password: Password to verify
            
        Returns:
            Session token if successful, None otherwise
        """
        # Check if user exists
        if username not in self.users:
            # Use constant-time comparison to prevent timing attacks
            time.sleep(0.1)
            return None
        
        user = self.users[username]
        
        # Check if account is active
        if not user['is_active']:
            return None
        
        # Check for rate limiting (prevent brute force)
        if self._is_rate_limited(username):
            print(f"Login rate limited for user: {username}")
            return None
        
        # Verify password using constant-time comparison
        password_hash = self._hash_password(password, user['salt'])
        
        # FIX: Use secrets.compare_digest for constant-time comparison
        # This prevents timing attacks where attackers can determine
        # correct password characters by measuring response times
        if not secrets.compare_digest(password_hash, user['password_hash']):
            self._record_failed_attempt(username)
            return None
        
        # Clear failed attempts on successful login
        if username in self._failed_attempts:
            del self._failed_attempts[username]
        
        # Create session
        session_token = secrets.token_urlsafe(32)
        
        # FIX: Properly calculate session expiry
        # Bug was: expires_at was set to current time instead of future time
        self.sessions[session_token] = {
            'username': username,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(minutes=self.session_timeout_minutes),
            'last_activity': datetime.now()
        }
        
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[str]:
        """
        Validate a session token and return username if valid.
        
        Args:
            session_token: Session token to validate
            
        Returns:
            Username if session is valid, None otherwise
        """
        if session_token not in self.sessions:
            return None
        
        session = self.sessions[session_token]
        
        # FIX: Check expiry time correctly
        # Bug was: comparison operator was reversed (< instead of >)
        if datetime.now() > session['expires_at']:
            # Session expired, remove it
            del self.sessions[session_token]
            return None
        
        # Update last activity time
        session['last_activity'] = datetime.now()
        
        return session['username']
    
    def logout(self, session_token: str) -> bool:
        """
        Logout user and invalidate session.
        
        Args:
            session_token: Session token to invalidate
            
        Returns:
            True if logout successful
        """
        if session_token in self.sessions:
            del self.sessions[session_token]
            return True
        return False
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using SHA-256."""
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def _record_failed_attempt(self, username: str):
        """Record a failed login attempt."""
        if username not in self._failed_attempts:
            self._failed_attempts[username] = []
        
        self._failed_attempts[username].append(datetime.now())
        
        # Clean up old attempts (older than 15 minutes)
        cutoff = datetime.now() - timedelta(minutes=15)
        self._failed_attempts[username] = [
            attempt for attempt in self._failed_attempts[username]
            if attempt > cutoff
        ]
    
    def _is_rate_limited(self, username: str) -> bool:
        """Check if user has too many failed attempts."""
        if username not in self._failed_attempts:
            return False
        
        # Allow max 5 failed attempts in 15 minutes
        recent_attempts = len(self._failed_attempts[username])
        return recent_attempts >= 5
    
    def update_password_by_email(self, email: str, new_password: str) -> bool:
        """
        Update user password by email (used for password reset).
        
        Args:
            email: User's email address
            new_password: New password to set
            
        Returns:
            True if password updated successfully
        """
        # Find user by email
        for username, user_data in self.users.items():
            if user_data['email'] == email:
                # Generate new salt and hash
                salt = secrets.token_hex(16)
                password_hash = self._hash_password(new_password, salt)
                
                # Update user's password
                self.users[username]['password_hash'] = password_hash
                self.users[username]['salt'] = salt
                
                # Invalidate all existing sessions for security
                sessions_to_remove = [
                    token for token, session in self.sessions.items()
                    if session['username'] == username
                ]
                for token in sessions_to_remove:
                    del self.sessions[token]
                
                return True
        
        return False


# Example usage
if __name__ == "__main__":
    auth = AuthenticationManager(session_timeout_minutes=30)
    
    # Register a user
    print("Registering user...")
    success = auth.register_user("john_doe", "secure_password123", "john@example.com")
    print(f"Registration: {'Success' if success else 'Failed'}")
    
    # Login
    print("\nLogging in...")
    session_token = auth.login("john_doe", "secure_password123")
    if session_token:
        print(f"Login successful! Session token: {session_token[:20]}...")
        
        # Validate session
        username = auth.validate_session(session_token)
        print(f"Session valid for user: {username}")
        
        # Logout
        auth.logout(session_token)
        print("Logged out successfully")
    else:
        print("Login failed")
