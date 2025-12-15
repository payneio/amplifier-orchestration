"""
Password Reset Feature

Provides functionality for users to reset their passwords securely.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict


class PasswordResetManager:
    """Manages password reset tokens and operations."""
    
    def __init__(self, token_expiry_hours: int = 24):
        self.token_expiry_hours = token_expiry_hours
        self.reset_tokens: Dict[str, Dict] = {}
    
    def generate_reset_token(self, user_email: str) -> str:
        """
        Generate a secure password reset token for a user.
        
        Args:
            user_email: Email address of the user requesting reset
            
        Returns:
            Secure reset token string
        """
        # Generate cryptographically secure token
        token = secrets.token_urlsafe(32)
        
        # Store token with expiry time
        self.reset_tokens[token] = {
            'email': user_email,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=self.token_expiry_hours),
            'used': False
        }
        
        return token
    
    def validate_token(self, token: str) -> Optional[str]:
        """
        Validate a password reset token.
        
        Args:
            token: Reset token to validate
            
        Returns:
            User email if valid, None otherwise
        """
        if token not in self.reset_tokens:
            return None
        
        token_data = self.reset_tokens[token]
        
        # Check if token has expired
        if datetime.now() > token_data['expires_at']:
            return None
        
        # Check if token has already been used
        if token_data['used']:
            return None
        
        return token_data['email']
    
    def reset_password(self, token: str, new_password: str, auth_manager=None) -> bool:
        """
        Reset user password using a valid token.
        
        Args:
            token: Valid reset token
            new_password: New password to set
            auth_manager: Optional AuthenticationManager instance to update user password
            
        Returns:
            True if password was reset successfully, False otherwise
        """
        email = self.validate_token(token)
        
        if not email:
            return False
        
        # Validate password strength
        if not self._validate_password_strength(new_password):
            print("Password does not meet security requirements")
            return False
        
        # Mark token as used
        self.reset_tokens[token]['used'] = True
        
        # If auth_manager provided, update the password in the system
        if auth_manager:
            updated = auth_manager.update_password_by_email(email, new_password)
            if updated:
                print(f"Password reset successful for {email}")
                return True
            else:
                print(f"Failed to update password for {email}")
                return False
        
        # In a real application, update the database here
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        print(f"Password reset successful for {email}")
        print(f"New password hash: {password_hash}")
        
        return True
    
    def _validate_password_strength(self, password: str) -> bool:
        """
        Validate password meets security requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            True if password is strong enough
        """
        if len(password) < 8:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        return has_upper and has_lower and has_digit and has_special
    
    def send_reset_email(self, email: str, token: str) -> bool:
        """
        Send password reset email to user.
        
        Args:
            email: User's email address
            token: Reset token
            
        Returns:
            True if email sent successfully
        """
        # In production, integrate with email service
        reset_link = f"https://example.com/reset-password?token={token}"
        
        print(f"Sending password reset email to: {email}")
        print(f"Reset link: {reset_link}")
        print(f"Token expires in {self.token_expiry_hours} hours")
        
        return True


# Example usage
if __name__ == "__main__":
    manager = PasswordResetManager()
    
    # User requests password reset
    user_email = "user@example.com"
    token = manager.generate_reset_token(user_email)
    manager.send_reset_email(user_email, token)
    
    # User clicks link and submits new password
    success = manager.reset_password(token, "NewSecure@Pass123")
    print(f"\nPassword reset status: {'Success' if success else 'Failed'}")
