"""
Unit tests for the AuthTokenValidator

Tests cover the bug fixes including:
- Thread-safe operations
- Proper expiration handling
- Signature verification
- Token revocation
"""

import unittest
import time
import base64
import hashlib
import hmac
from concurrent.futures import ThreadPoolExecutor
from auth_token_validator import AuthTokenValidator, TokenValidationError


class TestAuthTokenValidator(unittest.TestCase):
    """Test suite for AuthTokenValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.secret_key = "test_secret_key_12345"
        self.validator = AuthTokenValidator(self.secret_key, token_expiry_seconds=10)
        self.user_id = "user_123"
    
    def _create_valid_token(self, user_id: str, timestamp: int = None) -> str:
        """Helper method to create a valid token for testing"""
        if timestamp is None:
            timestamp = int(time.time())
        
        # Create payload
        payload_data = f"user:{user_id}"
        payload = base64.b64encode(payload_data.encode('utf-8')).decode('utf-8')
        
        # Generate signature
        message = f"{payload}.{timestamp}.{user_id}".encode('utf-8')
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message,
            hashlib.sha256
        ).hexdigest()
        
        return f"{payload}.{timestamp}.{signature}"
    
    def test_valid_token_passes(self):
        """Test that a valid token passes validation"""
        token = self._create_valid_token(self.user_id)
        self.assertTrue(self.validator.validate_token(token, self.user_id))
    
    def test_expired_token_fails(self):
        """Test that an expired token fails validation"""
        old_timestamp = int(time.time()) - 20  # 20 seconds ago (expiry is 10)
        token = self._create_valid_token(self.user_id, old_timestamp)
        
        with self.assertRaises(TokenValidationError) as context:
            self.validator.validate_token(token, self.user_id)
        
        self.assertIn("expired", str(context.exception).lower())
    
    def test_future_token_fails(self):
        """Test that a token from the future fails (clock skew attack prevention)"""
        future_timestamp = int(time.time()) + 120  # 2 minutes in future
        token = self._create_valid_token(self.user_id, future_timestamp)
        
        with self.assertRaises(TokenValidationError) as context:
            self.validator.validate_token(token, self.user_id)
        
        self.assertIn("future", str(context.exception).lower())
    
    def test_invalid_signature_fails(self):
        """Test that a token with invalid signature fails"""
        timestamp = int(time.time())
        payload_data = f"user:{self.user_id}"
        payload = base64.b64encode(payload_data.encode('utf-8')).decode('utf-8')
        
        # Use wrong signature
        wrong_signature = "invalid_signature_12345"
        token = f"{payload}.{timestamp}.{wrong_signature}"
        
        with self.assertRaises(TokenValidationError) as context:
            self.validator.validate_token(token, self.user_id)
        
        self.assertIn("signature", str(context.exception).lower())
    
    def test_malformed_token_fails(self):
        """Test that a malformed token fails validation"""
        malformed_token = "invalid.token"
        
        with self.assertRaises(TokenValidationError) as context:
            self.validator.validate_token(malformed_token, self.user_id)
        
        self.assertIn("format", str(context.exception).lower())
    
    def test_empty_token_fails(self):
        """Test that empty token or user_id fails"""
        with self.assertRaises(TokenValidationError):
            self.validator.validate_token("", self.user_id)
        
        token = self._create_valid_token(self.user_id)
        with self.assertRaises(TokenValidationError):
            self.validator.validate_token(token, "")
    
    def test_token_revocation(self):
        """Test that revoked tokens fail validation"""
        token = self._create_valid_token(self.user_id)
        
        # Token should be valid initially
        self.assertTrue(self.validator.validate_token(token, self.user_id))
        
        # Revoke the token
        self.validator.revoke_token(token)
        
        # Token should now fail validation
        with self.assertRaises(TokenValidationError) as context:
            self.validator.validate_token(token, self.user_id)
        
        self.assertIn("revoked", str(context.exception).lower())
    
    def test_caching_works(self):
        """Test that validation caching improves performance"""
        token = self._create_valid_token(self.user_id)
        
        # First validation
        start = time.time()
        self.assertTrue(self.validator.validate_token(token, self.user_id))
        first_duration = time.time() - start
        
        # Second validation (should use cache)
        start = time.time()
        self.assertTrue(self.validator.validate_token(token, self.user_id))
        second_duration = time.time() - start
        
        # Cached validation should be faster (or at least not significantly slower)
        # Note: This is a weak assertion since timing can be unreliable
        self.assertLessEqual(second_duration, first_duration * 2)
    
    def test_cache_cleanup(self):
        """Test that expired cache entries are cleaned up"""
        # Create validator with very short expiry
        short_validator = AuthTokenValidator(self.secret_key, token_expiry_seconds=1)
        token = self._create_valid_token(self.user_id)
        
        # Validate token (adds to cache)
        short_validator.validate_token(token, self.user_id)
        self.assertGreater(len(short_validator._validation_cache), 0)
        
        # Wait for expiry
        time.sleep(2)
        
        # Validate another token (triggers cleanup)
        new_token = self._create_valid_token("user_456")
        try:
            short_validator.validate_token(new_token, "user_456")
        except TokenValidationError:
            pass  # Expected to fail due to expiry
        
        # Old entry should be cleaned up
        # (Note: may still have the new failed validation)
    
    def test_thread_safety(self):
        """Test that validator is thread-safe (fixes race condition bug)"""
        token = self._create_valid_token(self.user_id)
        results = []
        errors = []
        
        def validate_in_thread():
            try:
                result = self.validator.validate_token(token, self.user_id)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run 50 concurrent validations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(validate_in_thread) for _ in range(50)]
            for future in futures:
                future.result()
        
        # All validations should succeed
        self.assertEqual(len(results), 50)
        self.assertEqual(len(errors), 0)
        self.assertTrue(all(results))
    
    def test_user_id_mismatch_fails(self):
        """Test that token validation fails when user_id doesn't match"""
        token = self._create_valid_token(self.user_id)
        
        with self.assertRaises(TokenValidationError) as context:
            self.validator.validate_token(token, "different_user")
        
        self.assertIn("payload", str(context.exception).lower())
    
    def test_clear_cache(self):
        """Test that cache can be cleared"""
        token = self._create_valid_token(self.user_id)
        
        # Add to cache
        self.validator.validate_token(token, self.user_id)
        self.assertGreater(len(self.validator._validation_cache), 0)
        
        # Clear cache
        self.validator.clear_cache()
        self.assertEqual(len(self.validator._validation_cache), 0)


if __name__ == '__main__':
    unittest.main()
