#!/usr/bin/env python3
"""
Test runner for the volume bot.
This script runs all tests in the tests directory.
"""

import os
import sys
import pytest

def main():
    """Run the tests."""
    # Change to the directory of this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Run pytest with the tests directory
    print("Running tests from", os.path.abspath('tests'))
    result = pytest.main(["-v", "tests"])
    
    # Return the exit code from pytest
    sys.exit(result)

if __name__ == "__main__":
    main() 