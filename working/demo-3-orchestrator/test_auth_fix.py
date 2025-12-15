"""
Test suite for authentication bug fix.

Tests the sliding window session expiration fix that prevents
intermittent authentication failures for active users.
"""

import time
from datetime import datetime, timedelta
from login_auth import AuthenticationManager


def test_session_expiration_with_activity():
    """
    Test that active sessions are extended (sliding window).
    
    This test verifies the fix for intermittent authentication failures
    where active users were being logged out after the initial timeout period.
    """
    # Create auth manager with 1 minute timeout for faster testing
    auth = AuthenticationManager(session_timeout_minutes=1)
    
    # Register and login a user
    auth.register_user("test_user", "password123", "test@example.com")
    session_token = auth.login("test_user", "password123")
    
    assert session_token is not None, "Login should succeed"
    
    # Simulate activity over 2 minutes (longer than timeout)
    # by validating session every 30 seconds
    for i in range(4):  # 4 iterations * 30 seconds = 2 minutes
        time.sleep(30)
        
        # Validate session (simulating user activity)
        username = auth.validate_session(session_token)
        
        assert username == "test_user", f"Session should remain valid at iteration {i+1}"
        print(f"✓ Session valid after {(i+1)*30} seconds of activity")
    
    print("\n✓ Test passed: Active sessions are properly extended (sliding window)")


def test_session_expiration_without_activity():
    """
    Test that inactive sessions expire correctly.
    
    Verifies that sessions without activity expire after the timeout period.
    """
    # Create auth manager with 1 minute timeout
    auth = AuthenticationManager(session_timeout_minutes=1)
    
    # Register and login a user
    auth.register_user("test_user2", "password123", "test2@example.com")
    session_token = auth.login("test_user2", "password123")
    
    assert session_token is not None, "Login should succeed"
    
    # Validate immediately - should work
    username = auth.validate_session(session_token)
    assert username == "test_user2", "Session should be valid immediately"
    print("✓ Session valid immediately after login")
    
    # Wait for session to expire (65 seconds to be safe)
    print("Waiting for session to expire (65 seconds)...")
    time.sleep(65)
    
    # Try to validate - should fail
    username = auth.validate_session(session_token)
    assert username is None, "Session should be expired after timeout"
    print("✓ Session correctly expired after timeout period")
    
    print("\n✓ Test passed: Inactive sessions expire correctly")


def test_concurrent_session_validation():
    """
    Test thread-safety of session validation.
    
    Verifies that concurrent session validations don't cause race conditions.
    """
    import threading
    
    auth = AuthenticationManager(session_timeout_minutes=5)
    
    # Register and login
    auth.register_user("concurrent_user", "password123", "concurrent@example.com")
    session_token = auth.login("concurrent_user", "password123")
    
    results = []
    errors = []
    
    def validate_session():
        try:
            for _ in range(10):
                username = auth.validate_session(session_token)
                results.append(username)
                time.sleep(0.01)
        except Exception as e:
            errors.append(str(e))
    
    # Create multiple threads
    threads = [threading.Thread(target=validate_session) for _ in range(5)]
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    # Verify no errors occurred
    assert len(errors) == 0, f"No errors should occur: {errors}"
    
    # Verify all validations succeeded
    assert all(username == "concurrent_user" for username in results), \
        "All validations should return correct username"
    
    print(f"✓ {len(results)} concurrent validations completed successfully")
    print("\n✓ Test passed: Thread-safe session validation works correctly")


def test_session_extension_timing():
    """
    Test that session expiration time is correctly extended.
    
    Verifies that the expires_at timestamp is properly updated on each validation.
    """
    auth = AuthenticationManager(session_timeout_minutes=5)
    
    # Register and login
    auth.register_user("timing_user", "password123", "timing@example.com")
    session_token = auth.login("timing_user", "password123")
    
    # Get initial expiration time
    with auth._sessions_lock:
        initial_expires_at = auth.sessions[session_token]['expires_at']
    
    print(f"Initial expiration: {initial_expires_at}")
    
    # Wait 2 seconds
    time.sleep(2)
    
    # Validate session (should extend expiration)
    auth.validate_session(session_token)
    
    # Get new expiration time
    with auth._sessions_lock:
        new_expires_at = auth.sessions[session_token]['expires_at']
    
    print(f"New expiration: {new_expires_at}")
    
    # Verify expiration was extended
    time_difference = (new_expires_at - initial_expires_at).total_seconds()
    
    assert time_difference >= 2, \
        f"Expiration should be extended by at least 2 seconds, got {time_difference}"
    
    print(f"✓ Expiration extended by {time_difference:.1f} seconds")
    print("\n✓ Test passed: Session expiration time is correctly extended")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Authentication Bug Fix")
    print("=" * 60)
    print()
    
    print("Test 1: Session expiration with activity (sliding window)")
    print("-" * 60)
    test_session_expiration_with_activity()
    print()
    
    print("Test 2: Session expiration without activity")
    print("-" * 60)
    test_session_expiration_without_activity()
    print()
    
    print("Test 3: Concurrent session validation (thread safety)")
    print("-" * 60)
    test_concurrent_session_validation()
    print()
    
    print("Test 4: Session extension timing")
    print("-" * 60)
    test_session_extension_timing()
    print()
    
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
