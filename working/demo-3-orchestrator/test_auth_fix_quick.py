"""
Quick test suite for authentication bug fix.

Tests the sliding window session expiration fix without long delays.
"""

from datetime import datetime, timedelta
from login_auth import AuthenticationManager


def test_session_extension_on_validation():
    """
    Test that session expiration is extended on each validation.
    
    This verifies the fix for intermittent authentication failures.
    """
    auth = AuthenticationManager(session_timeout_minutes=30)
    
    # Register and login a user
    auth.register_user("test_user", "password123", "test@example.com")
    session_token = auth.login("test_user", "password123")
    
    assert session_token is not None, "Login should succeed"
    print("✓ User registered and logged in successfully")
    
    # Get initial expiration time
    with auth._sessions_lock:
        initial_expires_at = auth.sessions[session_token]['expires_at']
        initial_created_at = auth.sessions[session_token]['created_at']
    
    print(f"✓ Initial session created at: {initial_created_at}")
    print(f"✓ Initial expiration time: {initial_expires_at}")
    
    # Calculate expected initial expiration (30 minutes from creation)
    expected_initial_expiry = initial_created_at + timedelta(minutes=30)
    time_diff = abs((initial_expires_at - expected_initial_expiry).total_seconds())
    assert time_diff < 1, "Initial expiration should be 30 minutes from creation"
    print("✓ Initial expiration correctly set to 30 minutes from creation")
    
    # Validate session (this should extend the expiration)
    username = auth.validate_session(session_token)
    assert username == "test_user", "Session validation should succeed"
    print("✓ Session validated successfully")
    
    # Get new expiration time
    with auth._sessions_lock:
        new_expires_at = auth.sessions[session_token]['expires_at']
        new_last_activity = auth.sessions[session_token]['last_activity']
    
    print(f"✓ New last activity time: {new_last_activity}")
    print(f"✓ New expiration time: {new_expires_at}")
    
    # Verify expiration was extended (should now be 30 minutes from validation time)
    expected_new_expiry = new_last_activity + timedelta(minutes=30)
    time_diff = abs((new_expires_at - expected_new_expiry).total_seconds())
    assert time_diff < 1, "New expiration should be 30 minutes from validation time"
    print("✓ Expiration correctly extended to 30 minutes from validation")
    
    # Verify the expiration was actually pushed forward
    extension_seconds = (new_expires_at - initial_expires_at).total_seconds()
    assert extension_seconds > 0, "Expiration should be extended forward in time"
    print(f"✓ Expiration extended by {extension_seconds:.2f} seconds")
    
    print("\n✓ Test passed: Session expiration is extended on validation (sliding window)")


def test_expired_session_removal():
    """
    Test that expired sessions are properly removed.
    """
    auth = AuthenticationManager(session_timeout_minutes=30)
    
    # Register and login
    auth.register_user("test_user2", "password123", "test2@example.com")
    session_token = auth.login("test_user2", "password123")
    
    assert session_token is not None, "Login should succeed"
    print("✓ User registered and logged in successfully")
    
    # Manually set expiration to the past
    with auth._sessions_lock:
        auth.sessions[session_token]['expires_at'] = datetime.now() - timedelta(minutes=1)
    
    print("✓ Manually set session to expired state")
    
    # Try to validate - should fail and remove session
    username = auth.validate_session(session_token)
    assert username is None, "Expired session should return None"
    print("✓ Expired session validation correctly returned None")
    
    # Verify session was removed
    with auth._sessions_lock:
        assert session_token not in auth.sessions, "Expired session should be removed"
    
    print("✓ Expired session was removed from sessions dict")
    print("\n✓ Test passed: Expired sessions are properly removed")


def test_multiple_validations_extend_session():
    """
    Test that multiple validations continue to extend the session.
    """
    auth = AuthenticationManager(session_timeout_minutes=30)
    
    # Register and login
    auth.register_user("test_user3", "password123", "test3@example.com")
    session_token = auth.login("test_user3", "password123")
    
    print("✓ User registered and logged in successfully")
    
    # Perform multiple validations and track expiration times
    expiration_times = []
    
    for i in range(5):
        # Validate session
        username = auth.validate_session(session_token)
        assert username == "test_user3", f"Validation {i+1} should succeed"
        
        # Record expiration time
        with auth._sessions_lock:
            expiration_times.append(auth.sessions[session_token]['expires_at'])
        
        print(f"✓ Validation {i+1}: Session extended to {expiration_times[-1]}")
    
    # Verify each validation extended the expiration
    for i in range(1, len(expiration_times)):
        time_diff = (expiration_times[i] - expiration_times[i-1]).total_seconds()
        assert time_diff >= 0, f"Expiration should not go backwards (iteration {i})"
    
    print(f"✓ All {len(expiration_times)} validations successfully extended the session")
    print("\n✓ Test passed: Multiple validations continue to extend session")


def test_thread_safety_basics():
    """
    Test basic thread safety of session operations.
    """
    import threading
    
    auth = AuthenticationManager(session_timeout_minutes=30)
    
    # Register and login
    auth.register_user("concurrent_user", "password123", "concurrent@example.com")
    session_token = auth.login("concurrent_user", "password123")
    
    print("✓ User registered and logged in successfully")
    
    results = []
    errors = []
    
    def validate_session():
        try:
            for _ in range(10):
                username = auth.validate_session(session_token)
                results.append(username)
        except Exception as e:
            errors.append(str(e))
    
    # Create multiple threads
    threads = [threading.Thread(target=validate_session) for _ in range(3)]
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    # Verify no errors occurred
    assert len(errors) == 0, f"No errors should occur: {errors}"
    print(f"✓ No errors in {len(results)} concurrent validations")
    
    # Verify all validations succeeded
    assert all(username == "concurrent_user" for username in results), \
        "All validations should return correct username"
    print(f"✓ All {len(results)} validations returned correct username")
    
    print("\n✓ Test passed: Basic thread safety verified")


if __name__ == "__main__":
    print("=" * 70)
    print("Quick Test Suite: Authentication Bug Fix")
    print("=" * 70)
    print()
    
    print("Test 1: Session extension on validation (sliding window)")
    print("-" * 70)
    test_session_extension_on_validation()
    print()
    
    print("Test 2: Expired session removal")
    print("-" * 70)
    test_expired_session_removal()
    print()
    
    print("Test 3: Multiple validations extend session")
    print("-" * 70)
    test_multiple_validations_extend_session()
    print()
    
    print("Test 4: Thread safety basics")
    print("-" * 70)
    test_thread_safety_basics()
    print()
    
    print("=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)
    print()
    print("Summary of fix:")
    print("- Implemented sliding window session expiration")
    print("- Sessions now extend on each validation/activity")
    print("- Prevents intermittent auth failures for active users")
    print("- Maintains security by expiring inactive sessions")
