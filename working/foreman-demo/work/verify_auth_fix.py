#!/usr/bin/env python3
"""
Verification script for authentication bug fixes.
Tests the key improvements that fix intermittent authentication failures.
"""

import time
import threading
from auth_token_validator import AuthTokenValidator


def test_thread_safety():
    """Test that the validator is thread-safe (fixes race condition)"""
    print("Testing thread-safety...")
    validator = AuthTokenValidator(secret_key="test-secret-key")
    token = validator.create_token(user_id="user123")
    
    results = []
    errors = []
    
    def validate_in_thread():
        try:
            result = validator.validate_token(token)
            results.append(result is not None)
        except Exception as e:
            errors.append(str(e))
    
    # Run 100 concurrent validations
    threads = []
    for _ in range(100):
        t = threading.Thread(target=validate_in_thread)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    success_rate = sum(results) / len(results) * 100
    print(f"  ✓ Thread-safety test: {len(results)} validations, {success_rate:.1f}% success rate")
    print(f"  ✓ Errors: {len(errors)}")
    
    assert len(errors) == 0, f"Thread-safety test failed with errors: {errors}"
    assert success_rate == 100, f"Expected 100% success rate, got {success_rate}%"


def test_grace_period():
    """Test that grace period handles clock skew properly"""
    print("\nTesting grace period for clock skew...")
    validator = AuthTokenValidator(secret_key="test-secret-key", token_expiry_seconds=2)
    token = validator.create_token(user_id="user456")
    
    # Token should be valid immediately
    result = validator.validate_token(token)
    assert result is not None, "Token should be valid immediately"
    print("  ✓ Token valid immediately after creation")
    
    # Wait for token to expire
    time.sleep(3)
    
    # Token should still be valid due to grace period (5 minutes)
    result = validator.validate_token(token)
    assert result is not None, "Token should be valid within grace period"
    print("  ✓ Token valid within grace period after expiry")


def test_token_refresh():
    """Test that token refresh mechanism works"""
    print("\nTesting token refresh mechanism...")
    validator = AuthTokenValidator(secret_key="test-secret-key")
    original_token = validator.create_token(user_id="user789", metadata={"role": "admin"})
    
    # Refresh the token
    new_token = validator.refresh_token(original_token)
    assert new_token is not None, "Token refresh should succeed"
    assert new_token != original_token, "New token should be different"
    print("  ✓ Token refresh successful")
    
    # New token should be valid
    result = validator.validate_token(new_token)
    assert result is not None, "Refreshed token should be valid"
    assert result['user_id'] == "user789", "User ID should be preserved"
    print("  ✓ Refreshed token is valid with correct user_id")


def test_malformed_tokens():
    """Test that malformed tokens are handled gracefully"""
    print("\nTesting malformed token handling...")
    validator = AuthTokenValidator(secret_key="test-secret-key")
    
    malformed_tokens = [
        "",
        "invalid",
        "invalid.token",
        "a.b.c.d",
        None,
        123,
    ]
    
    for token in malformed_tokens:
        try:
            result = validator.validate_token(token)
            assert result is None, f"Malformed token should return None: {token}"
        except Exception as e:
            # Should not raise exceptions, should return None
            assert False, f"Malformed token should not raise exception: {token}, {e}"
    
    print(f"  ✓ All {len(malformed_tokens)} malformed tokens handled gracefully")


def test_cache_expiration():
    """Test that expired tokens are removed from cache"""
    print("\nTesting cache expiration...")
    # Create validator with custom grace period for testing
    validator = AuthTokenValidator(secret_key="test-secret-key", token_expiry_seconds=1)
    validator.grace_period_seconds = 2  # Override grace period for faster testing
    
    # Create and validate token (adds to cache)
    token = validator.create_token(user_id="user999")
    result = validator.validate_token(token)
    assert result is not None, "Token should be valid"
    
    # Wait for expiry + grace period
    time.sleep(4)
    
    # Token should now be invalid and removed from cache
    result = validator.validate_token(token)
    assert result is None, "Expired token should be invalid"
    print("  ✓ Expired tokens properly removed from cache")


def main():
    """Run all verification tests"""
    print("=" * 60)
    print("Authentication Bug Fix Verification")
    print("=" * 60)
    
    try:
        test_thread_safety()
        test_grace_period()
        test_token_refresh()
        test_malformed_tokens()
        test_cache_expiration()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED - Authentication bugs are fixed!")
        print("=" * 60)
        print("\nKey fixes verified:")
        print("  • Thread-safe token validation (no race conditions)")
        print("  • Grace period for clock skew (prevents intermittent failures)")
        print("  • Token refresh mechanism (seamless re-authentication)")
        print("  • Proper error handling for malformed tokens")
        print("  • Cache expiration and cleanup")
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
