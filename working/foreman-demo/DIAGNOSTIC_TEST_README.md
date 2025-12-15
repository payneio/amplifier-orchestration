# Diagnostic Test Suite

## Overview

The diagnostic test suite (`diagnostic_test.py`) is a comprehensive system health check that verifies core functionality of the codebase. It runs automated tests to ensure the environment is properly configured and all essential components are working correctly.

## Purpose

This test suite is designed to:
- Verify the Python environment is correctly configured
- Test file system operations (read/write)
- Validate module imports and dependencies
- Check basic language features and operations
- Provide a quick health check for the system

## Test Coverage

The diagnostic suite includes 12 tests covering:

### 1. **Python Version Check**
- Verifies Python 3.7+ is installed
- Ensures compatibility with modern Python features

### 2. **File System Read**
- Tests directory accessibility
- Validates read permissions

### 3. **File System Write**
- Tests write operations
- Creates and removes temporary test files
- Validates write/read consistency

### 4. **Work Directory Exists**
- Verifies the `work/` directory is present
- Ensures project structure is intact

### 5. **Auth Module Exists**
- Checks for `work/auth_token_validator.py`
- Validates critical module files are present

### 6. **Auth Module Import**
- Tests importing the authentication module
- Verifies the `TokenValidator` class is available
- Ensures no import errors

### 7. **Datetime Operations**
- Tests timezone-aware datetime operations
- Validates `datetime.now(timezone.utc)` functionality
- Checks ISO format string conversion

### 8. **Path Operations**
- Tests `pathlib.Path` functionality
- Validates path resolution
- Checks path existence operations

### 9. **String Operations**
- Tests basic string manipulation
- Validates `upper()`, `replace()` methods

### 10. **List Operations**
- Tests list indexing and length
- Validates list sum operations

### 11. **Dictionary Operations**
- Tests dictionary access and membership
- Validates key-value operations

### 12. **Exception Handling**
- Verifies exception raising and catching
- Tests error message handling

## Usage

### Running the Tests

```bash
python3 diagnostic_test.py
```

### Expected Output

When all tests pass:
```
============================================================
DIAGNOSTIC TEST SUITE
============================================================
Started at: 2025-12-13T00:07:09.392004+00:00


============================================================
TEST RESULTS
============================================================
✓ Python version check
✓ File system read
✓ File system write
✓ Work directory exists
✓ Auth module exists
✓ Auth module import
✓ Datetime operations
✓ Path operations
✓ String operations
✓ List operations
✓ Dictionary operations
✓ Exception handling

------------------------------------------------------------
Total Tests: 12
Passed: 12
Failed: 0
Success Rate: 100.0%
------------------------------------------------------------
Completed at: 2025-12-13T00:07:09.407500+00:00
============================================================

✓ All diagnostic tests passed!
```

### Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed

## Integration

### Continuous Integration

Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run Diagnostic Tests
  run: python3 diagnostic_test.py
```

### Pre-deployment Check

Run before deploying to verify system health:

```bash
python3 diagnostic_test.py && echo "Ready to deploy"
```

### Debugging

If tests fail, the output will show which specific test failed and why:

```
✗ Python version check: Python 3.7+ required, found 3.6
```

## Maintenance

### Adding New Tests

To add a new test:

1. Create a test method in the `DiagnosticTest` class:
   ```python
   def test_new_feature(self):
       """Test description."""
       # Test implementation
       assert condition, "Error message"
   ```

2. Add the test to `run_all_tests()`:
   ```python
   self.run_test("New feature test", self.test_new_feature)
   ```

### Best Practices

- Keep tests fast (< 1 second each)
- Tests should be independent
- Use descriptive test names
- Include clear error messages
- Clean up any temporary resources

## Troubleshooting

### Common Issues

**Test fails: "Work directory not found"**
- Ensure you're running from the project root directory
- Verify the `work/` directory exists

**Test fails: "Auth module import"**
- Check that `work/auth_token_validator.py` exists
- Verify the file has no syntax errors

**Test fails: "File system write"**
- Check write permissions in current directory
- Ensure disk space is available

## Technical Details

### Dependencies

- Python 3.7+
- Standard library only (no external dependencies)

### Test Framework

Uses a custom lightweight test framework that:
- Runs tests sequentially
- Catches and reports exceptions
- Tracks pass/fail statistics
- Provides formatted output

### Timezone Handling

All datetime operations use timezone-aware objects:
```python
datetime.now(timezone.utc)  # Modern approach
```

This avoids deprecation warnings and ensures consistent behavior across systems.

## Future Enhancements

Potential improvements:
- Add network connectivity tests
- Test database connections
- Validate configuration files
- Check for required environment variables
- Add performance benchmarks
- Integrate with pytest for more features

## License

This diagnostic test suite is part of the project and follows the same license.
