#!/bin/bash

# Script to directly run a test trade without going through the menu
cd "$(dirname "$0")/../../.." || exit

# Activate the virtual environment
source venv/bin/activate

# Run the test trade directly
python -m scripts.python.volume_bot --command test-trade

# Exit immediately after the test completes
echo "Test completed. Exiting..."
exit 0 