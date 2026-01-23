#!/bin/bash
# arduXT Build Helper Script
# Simplifies compilation with different build modes

set -e  # Exit on error

FQBN="arduino:avr:leonardo"
PORT="${1:-/dev/ttyACM0}"

function show_usage() {
    cat << EOF
Usage: ./build.sh [PORT] [MODE]

Build and upload arduXT with different configurations.

PORT: Serial port (default: /dev/ttyACM0)
      Examples: /dev/ttyACM0, /dev/cu.usbmodem14101, COM3

MODE: Build mode (default: production)
  production  - Production build (no debug output, GPIO enabled)
  verbose     - Production + scancode debug output
  test        - Test mode (no GPIO, for serial testing)
  test-verbose - Test mode + verbose output (for automated tests)

Examples:
  ./build.sh                           # Production build, upload to /dev/ttyACM0
  ./build.sh /dev/cu.usbmodem14101     # Production build, custom port
  ./build.sh /dev/ttyACM0 verbose      # Verbose mode
  ./build.sh /dev/ttyACM0 test-verbose # Test suite mode

EOF
    exit 0
}

function build_production() {
    echo "🔨 Building: PRODUCTION (no debug, GPIO enabled)"
    arduino-cli compile --fqbn "$FQBN" .
}

function build_verbose() {
    echo "🔨 Building: VERBOSE (scancode debug output)"
    arduino-cli compile --fqbn "$FQBN" \
        --build-property "compiler.cpp.extra_flags=-DVERBOSE_SCANCODES" .
}

function build_test() {
    echo "🔨 Building: TEST MODE (no GPIO)"
    arduino-cli compile --fqbn "$FQBN" \
        --build-property "compiler.cpp.extra_flags=-DTEST_MODE" .
}

function build_test_verbose() {
    echo "🔨 Building: TEST + VERBOSE (for automated tests)"
    arduino-cli compile --fqbn "$FQBN" \
        --build-property "compiler.cpp.extra_flags=-DTEST_MODE -DVERBOSE_SCANCODES" .
}

function upload() {
    echo "📤 Uploading to: $PORT"
    arduino-cli upload -p "$PORT" --fqbn "$FQBN" .
    echo "✅ Upload complete!"
}

# Parse arguments
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_usage
fi

MODE="${2:-production}"

# Build based on mode
case "$MODE" in
    production|prod)
        build_production
        ;;
    verbose|debug)
        build_verbose
        ;;
    test)
        build_test
        ;;
    test-verbose|test-debug)
        build_test_verbose
        ;;
    *)
        echo "❌ Error: Unknown mode '$MODE'"
        echo ""
        show_usage
        ;;
esac

# Upload
upload

echo ""
echo "🎉 Done! Device ready at $PORT"
