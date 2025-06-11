"""
Simple test to verify pytest is working.
"""

import unittest

class TestSimple(unittest.TestCase):
    """Simple test cases."""
    
    def test_true(self):
        """Test that True is true."""
        self.assertTrue(True)
    
    def test_math(self):
        """Test basic math operations."""
        self.assertEqual(2 + 2, 4)
        self.assertNotEqual(2 * 3, 7)

if __name__ == '__main__':
    unittest.main() 