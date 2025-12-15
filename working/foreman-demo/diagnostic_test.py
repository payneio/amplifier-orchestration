"""
Diagnostic Test Suite

This test suite verifies that the core system components are functioning correctly.
It checks:
1. Issue manager functionality
2. File system operations
3. Python environment
4. Module imports
5. Basic system health
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path


class DiagnosticTest:
    """Run diagnostic tests on the system."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def run_test(self, test_name, test_func):
        """Run a single test and record the result."""
        try:
            test_func()
            self.passed += 1
            self.results.append(f"✓ {test_name}")
            return True
        except Exception as e:
            self.failed += 1
            self.results.append(f"✗ {test_name}: {str(e)}")
            return False
    
    def test_python_version(self):
        """Verify Python version is 3.7+"""
        version = sys.version_info
        assert version.major == 3 and version.minor >= 7, \
            f"Python 3.7+ required, found {version.major}.{version.minor}"
    
    def test_file_system_read(self):
        """Test file system read operations."""
        # Check if current directory is accessible
        assert os.path.exists('.'), "Current directory not accessible"
        assert os.access('.', os.R_OK), "Current directory not readable"
    
    def test_file_system_write(self):
        """Test file system write operations."""
        test_file = '.diagnostic_test_temp'
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            with open(test_file, 'r') as f:
                content = f.read()
            assert content == 'test', "File write/read mismatch"
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)
    
    def test_work_directory_exists(self):
        """Verify work directory exists."""
        assert os.path.exists('work'), "Work directory not found"
        assert os.path.isdir('work'), "Work is not a directory"
    
    def test_auth_module_exists(self):
        """Verify auth token validator module exists."""
        auth_file = 'work/auth_token_validator.py'
        assert os.path.exists(auth_file), f"{auth_file} not found"
    
    def test_auth_module_import(self):
        """Test importing the auth module."""
        sys.path.insert(0, 'work')
        try:
            import auth_token_validator
            assert hasattr(auth_token_validator, 'TokenValidator'), \
                "TokenValidator class not found"
        finally:
            sys.path.remove('work')
    
    def test_datetime_operations(self):
        """Test datetime operations work correctly."""
        now = datetime.now(timezone.utc)
        assert isinstance(now, datetime), "datetime.now(timezone.utc) failed"
        
        # Test datetime formatting
        iso_str = now.isoformat()
        assert isinstance(iso_str, str), "datetime.isoformat() failed"
    
    def test_path_operations(self):
        """Test pathlib operations."""
        current = Path('.')
        assert current.exists(), "Path('.') doesn't exist"
        
        # Test path resolution
        resolved = current.resolve()
        assert resolved.exists(), "Path resolution failed"
    
    def test_string_operations(self):
        """Test basic string operations."""
        test_str = "diagnostic test"
        assert test_str.upper() == "DIAGNOSTIC TEST", "String upper() failed"
        assert test_str.replace("test", "check") == "diagnostic check", \
            "String replace() failed"
    
    def test_list_operations(self):
        """Test basic list operations."""
        test_list = [1, 2, 3, 4, 5]
        assert len(test_list) == 5, "List length incorrect"
        assert sum(test_list) == 15, "List sum incorrect"
        assert test_list[0] == 1, "List indexing failed"
    
    def test_dict_operations(self):
        """Test basic dictionary operations."""
        test_dict = {'key1': 'value1', 'key2': 'value2'}
        assert test_dict['key1'] == 'value1', "Dict access failed"
        assert len(test_dict) == 2, "Dict length incorrect"
        assert 'key1' in test_dict, "Dict membership test failed"
    
    def test_exception_handling(self):
        """Test exception handling works."""
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            assert str(e) == "Test exception", "Exception message incorrect"
        else:
            raise AssertionError("Exception not raised")
    
    def run_all_tests(self):
        """Run all diagnostic tests."""
        print("=" * 60)
        print("DIAGNOSTIC TEST SUITE")
        print("=" * 60)
        print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
        print()
        
        # Run all tests
        self.run_test("Python version check", self.test_python_version)
        self.run_test("File system read", self.test_file_system_read)
        self.run_test("File system write", self.test_file_system_write)
        self.run_test("Work directory exists", self.test_work_directory_exists)
        self.run_test("Auth module exists", self.test_auth_module_exists)
        self.run_test("Auth module import", self.test_auth_module_import)
        self.run_test("Datetime operations", self.test_datetime_operations)
        self.run_test("Path operations", self.test_path_operations)
        self.run_test("String operations", self.test_string_operations)
        self.run_test("List operations", self.test_list_operations)
        self.run_test("Dictionary operations", self.test_dict_operations)
        self.run_test("Exception handling", self.test_exception_handling)
        
        # Print results
        print()
        print("=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        for result in self.results:
            print(result)
        
        print()
        print("-" * 60)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        print("-" * 60)
        print(f"Completed at: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60)
        
        return self.failed == 0


def main():
    """Main entry point for diagnostic tests."""
    diagnostic = DiagnosticTest()
    success = diagnostic.run_all_tests()
    
    if success:
        print("\n✓ All diagnostic tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {diagnostic.failed} test(s) failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
