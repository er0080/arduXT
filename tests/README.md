# arduXT Test Suite

This directory contains hardware-in-the-loop tests for the arduXT keyboard emulator.

## Prerequisites

This project uses `uv` for Python package management. Install uv if you don't have it:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

## Setup

```bash
# Navigate to tests directory
cd tests/

# Create virtual environment and install dependencies (done automatically with uv run)
uv sync
```

## Building for Tests

**IMPORTANT**: The test suite requires the Arduino sketch to be compiled with test flags enabled.

### Compile and Upload for Testing

```bash
# Navigate to project root
cd /home/eric/dev/arduXT

# Compile with ARDUXT_TEST_MODE and VERBOSE_SCANCODES enabled
arduino-cli compile --fqbn arduino:avr:leonardo \
  --build-property "compiler.cpp.extra_flags=-DARDUXT_TEST_MODE -DVERBOSE_SCANCODES" .

# Upload to device
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:leonardo .

# Or combine both commands
arduino-cli compile --fqbn arduino:avr:leonardo \
  --build-property "compiler.cpp.extra_flags=-DARDUXT_TEST_MODE -DVERBOSE_SCANCODES" . && \
  arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:leonardo .
```

**Why these flags are needed:**
- **ARDUXT_TEST_MODE**: Disables GPIO operations, allowing tests to run faster without physical XT hardware
- **VERBOSE_SCANCODES**: Outputs detailed scancode information (MAKE/BREAK) that the test suite validates

**NEVER uncomment these defines in source code** - always pass them at compile time to prevent accidentally deploying test code to production.

### Quick Build (Using Helper Script)

```bash
# From project root
./build.sh /dev/ttyACM0 test-verbose
```

The build script handles compile-time flags automatically for different modes.

## Running Tests

### Hardware-in-the-Loop Tests

Connect your DFRobot Beetle running arduXT to your computer via USB, then:

```bash
# Find your device port
arduino-cli board list

# Run the test suite (macOS/Linux)
uv run test_arduxt.py /dev/cu.usbmodem14101

# Run the test suite (Linux alternative)
uv run test_arduxt.py /dev/ttyACM0

# Run the test suite (Windows)
uv run test_arduxt.py COM3

# Or activate the virtual environment first
source .venv/bin/activate
python test_arduxt.py /dev/cu.usbmodem14101
```

### Test Options

```bash
# Custom baud rate
uv run test_arduxt.py /dev/cu.usbmodem14101 --baudrate 9600

# Custom timeout
uv run test_arduxt.py /dev/cu.usbmodem14101 --timeout 2.0

# Show help
uv run test_arduxt.py --help
```

## Test Coverage

The test suite covers:

- **Basic Characters**: Lowercase letters, uppercase letters, digits, spaces
- **Punctuation**: All unshifted punctuation keys
- **Shifted Characters**: !, @, #, $, %, ^, &, *, (, ), _, +, etc.
- **Control Characters**: Ctrl+A through Ctrl+Z, Tab, Backspace, Enter
- **Arrow Keys**: Up, Down, Left, Right (ESC[A/B/C/D)
- **Function Keys**: F1-F12 (ESCOP/Q/R/S and ESC[15~/17~/18~/etc.)
- **Extended Keys**: Home, End, Insert, Delete, Page Up, Page Down
- **Alt Keys**: Alt+letter, Alt+number, Alt+Shift+key
- **Special Cases**: Standalone ESC, escape sequence timeouts, invalid sequences

## Test Output

The test harness:
- Sends characters/sequences via USB Serial
- Reads debug output from the Arduino
- Validates that expected output appears
- Reports PASS/FAIL for each test
- Provides a summary at the end

Example output:
```
Test 1: Lowercase letter 'a'
  ✓ PASS
    INPUT: 0x61 (a)
    KEY: a
    SCANCODE: 0x1E (MAKE)
    SCANCODE: 0x9E (BREAK)

Test 15: Up arrow
  ✓ PASS
    ESC received
    CSI sequence
    KEY: Escape sequence -> 0x48
    SCANCODE: 0x48 (MAKE)
    SCANCODE: 0xC8 (BREAK)

==============================================================
Test Summary: 75 tests
  ✓ Passed: 75
  ✗ Failed: 0
  Success rate: 100.0%
==============================================================
```

## Arduino Code Test Modes

The Arduino sketch supports two test-related defines:

### VERBOSE_SCANCODES (enabled by default)
Prints detailed scancode information for each key press:
```cpp
#define VERBOSE_SCANCODES
```
Output includes MAKE/BREAK codes being sent to the XT bus.

### ARDUXT_TEST_MODE (disabled by default)
Disables GPIO operations for faster testing without hardware:
```cpp
#define ARDUXT_TEST_MODE
```
When enabled:
- No GPIO pin initialization
- No clock/data signal generation
- Faster test execution
- Useful for testing protocol logic without hardware

## Adding New Tests

To add new test cases, edit `test_arduxt.py` and add tests to the `run_test_suite()` function:

```python
tester.test("Test description",
            'a',                    # Input character or bytes
            ["INPUT: 0x61", "KEY: a"],  # Expected strings in output
            use_raw_bytes=False,    # Set True for raw byte sequences
            delay=0.1)              # Time to wait before reading
```

The test harness checks that all expected strings appear in the device output (in order).

## CI/CD Integration

To integrate with CI/CD pipelines that have hardware test rigs:

```bash
# Run tests and exit with status code
uv run test_arduxt.py /dev/ttyACM0
echo $?  # 0 = all tests passed, 1 = failures

# Or install dependencies and run directly
uv sync
source .venv/bin/activate
python test_arduxt.py /dev/ttyACM0
```

## Fuzz Testing

The fuzz testing framework provides long-duration stress testing with randomized inputs to identify edge cases, timing issues, and failure modes.

### Overview

Fuzz testing sends randomized keystrokes across all supported functionality:
- ASCII characters (40%)
- Control sequences (15%)
- Function keys (15%)
- Function keys with modifiers (10%)
- Navigation keys (10%)
- Alt combinations (5%)
- Malformed escape sequences (5%)

The fuzzer runs for a specified duration (hours) or input count and generates detailed reports for analysis.

### Running Fuzz Tests

```bash
# Build with test flags (REQUIRED)
cd ..
./build.sh /dev/ttyACM0 test-verbose

# Run fuzz test for 1 hour
cd tests/
uv run fuzz_arduxt.py /dev/ttyACM0 --duration 3600

# Run fuzz test for 4 hours with JSON report
uv run fuzz_arduxt.py /dev/ttyACM0 --duration 14400 --report fuzz_report.json

# Send 100,000 random inputs
uv run fuzz_arduxt.py /dev/ttyACM0 --count 100000

# Overnight test (8 hours)
uv run fuzz_arduxt.py /dev/ttyACM0 --duration 28800 --report overnight_fuzz.json
```

### Fuzz Test Options

```bash
# Show all options
uv run fuzz_arduxt.py --help

# Common options
--duration SECONDS    # Test duration in seconds
--count NUMBER        # Number of inputs to send
--baudrate RATE       # Baud rate (default: 9600)
--timeout SECONDS     # Response timeout (default: 1.0)
--report FILENAME     # Save JSON report to file
```

### Understanding Fuzz Reports

The fuzzer provides real-time progress:
```
Elapsed: 0:15:23 | Inputs: 15432 | Success: 99.8% | Throughput: 16.7/s | Avg Response: 45.2ms | Failures: 31
```

At completion, a detailed summary is displayed:
- **Total Inputs**: Number of random inputs sent
- **Success Rate**: Percentage of successful operations
- **Throughput**: Inputs processed per second
- **Response Times**: Min/Max/Average response times
- **Category Breakdown**: Distribution across input types
- **Recent Failures**: Last 10 failures with details

JSON reports contain:
- Complete statistics
- Performance metrics
- Error breakdown (timeouts, unexpected responses)
- Last 100 failures with timestamps and context

### Interpreting Results

**High Success Rate (>99%)**:
- System is robust and handles most inputs correctly
- Random failures may be acceptable edge cases

**Low Success Rate (<95%)**:
- Indicates potential issues with input handling
- Review failures in JSON report for patterns
- Check for specific categories causing problems

**High Timeout Rate**:
- May indicate buffer overflows or parsing issues
- Arduino may be getting stuck in certain states
- Check escape sequence timeout handling

**Increasing Response Times**:
- Potential memory leaks
- Buffer management issues
- Need to investigate memory usage patterns

**Category-Specific Failures**:
- If failures cluster in one category (e.g., "function_mod")
- Indicates specific code path issues
- Focus debugging on that functionality

### Recommended Test Durations

**Quick Smoke Test**: 1 hour (3,600 seconds)
- Validates basic robustness
- ~60,000 inputs at typical throughput

**Standard Soak Test**: 4 hours (14,400 seconds)
- Identifies medium-term issues
- ~240,000 inputs

**Overnight Test**: 8 hours (28,800 seconds)
- Comprehensive stress testing
- ~480,000 inputs
- Good for finding rare edge cases

**Weekend Test**: 48 hours (172,800 seconds)
- Exhaustive testing
- ~2.9 million inputs
- Identifies memory leaks and long-term stability issues

### Analyzing Failures

Review the JSON report for failure patterns:

```python
import json

# Load report
with open('fuzz_report.json') as f:
    report = json.load(f)

# Check failure categories
for failure in report['failures']:
    print(f"{failure['category']}: {failure['input']} -> {failure['error_type']}")

# Look for patterns
from collections import Counter
error_types = Counter(f['error_type'] for f in report['failures'])
print(f"Error distribution: {error_types}")
```

Common failure patterns:
- **Timeout on malformed sequences**: Expected behavior
- **Unexpected errors on valid inputs**: Requires investigation
- **Failures after long runs**: Potential memory issues

## Troubleshooting

**Device not found:**
- Check USB connection
- Run `arduino-cli board list` to find correct port
- On Linux, you may need to add your user to the `dialout` group:
  ```bash
  sudo usermod -a -G dialout $USER
  # Then log out and back in
  ```

**Timeout errors:**
- Increase timeout: `--timeout 2.0`
- Check baud rate matches Arduino sketch (9600)
- Ensure Arduino is running the correct sketch

**Intermittent failures:**
- Add delays between tests if needed
- Check USB cable quality
- Ensure Beetle is receiving adequate power (4.5-5V, NOT 6V)

**uv not found:**
- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Or use pip: `pip install uv`

## Project Structure

```
tests/
├── .venv/              # Virtual environment (created by uv)
├── test_arduxt.py      # Main test harness (97 functional tests)
├── fuzz_arduxt.py      # Fuzz testing framework (long-duration stress testing)
├── pyproject.toml      # Project dependencies
├── requirements.txt    # Alternative dependency list
└── README.md           # This file
```
