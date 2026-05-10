import unittest
from pathlib import Path
import sys

# Add the parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import test modules
from test_data_validation import TestDataValidation
from test_components import TestComponents

def run_test_suite():
    """Run all test cases and generate a test report"""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases from each test module
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataValidation))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestComponents))
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print('\nTest Summary:')
    print(f'Tests Run: {result.testsRun}')
    print(f'Failures: {len(result.failures)}')
    print(f'Errors: {len(result.errors)}')
    
    # Return True if all tests passed
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == '__main__':
    success = run_test_suite()
    sys.exit(0 if success else 1)