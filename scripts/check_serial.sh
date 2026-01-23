#!/bin/bash
# Quick serial check utility - reads startup message and exits
# Usage: ./check_serial.sh [PORT]

PORT="${1:-/dev/ttyACM0}"
TIMEOUT=3

echo "Checking serial output from $PORT..."
echo "Press Ctrl+C if it hangs"
echo "---"

# Use timeout to prevent hanging
timeout $TIMEOUT bash -c "
    stty -F $PORT 9600 raw -echo
    head -n 3 < $PORT
" 2>/dev/null

echo "---"
echo "Done"
