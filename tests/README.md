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

The fuzz testing framework provides long-duration stress testing with comprehensive modifier-based coverage to systematically identify edge cases, timing issues, and failure modes.

### Overview

The fuzzer uses a **modifier-based category system** that tests all possible combinations of modifier keys with different key types. This systematic approach ensures complete coverage of the keyboard emulator's functionality.

**Modifier Combinations (8 total):**
- `none` - No modifiers
- `shift` - Shift only
- `ctrl` - Ctrl only
- `alt` - Alt only
- `shift_ctrl` - Shift+Ctrl
- `shift_alt` - Shift+Alt
- `ctrl_alt` - Ctrl+Alt
- `shift_ctrl_alt` - All three modifiers

**Key Types (6 categories):**
- `letters` - a-z (26 keys)
- `digits` - 0-9 (10 keys)
- `punctuation` - Space, -, =, [, ], ;, ', `, \, ,, ., / (12 keys)
- `function` - F1-F12 (12 keys)
- `navigation` - Arrows, Home, End, Insert, Delete, PgUp, PgDn (10 keys)
- `special` - Enter, Tab, Backspace, Escape (4 keys)

This creates **48 distinct test categories** (8 modifiers × 6 key types). Each test randomly selects a key and modifier combination, generating the appropriate VT100 escape sequence or control code.

### Running Fuzz Tests

```bash
# Build with test flags (REQUIRED)
cd ..
./build.sh /dev/ttyACM0 test-verbose

# Quick test (5 minutes) with both reports
cd tests/
uv run fuzz_arduxt.py /dev/ttyACM0 --duration 300 --report stats.json --failures failures.json

# Standard test (1 hour) with reports
uv run fuzz_arduxt.py /dev/ttyACM0 --duration 3600 --report stats.json --failures failures.json

# Overnight test (8 hours) with reports
uv run fuzz_arduxt.py /dev/ttyACM0 --duration 28800 --report overnight_stats.json --failures overnight_failures.json

# Count-based test (10,000 inputs)
uv run fuzz_arduxt.py /dev/ttyACM0 --count 10000 --report stats.json --failures failures.json
```

### Fuzz Test Options

```bash
# Show all options
uv run fuzz_arduxt.py --help

# Common options
--duration SECONDS      # Test duration in seconds
--count NUMBER          # Number of inputs to send
--baudrate RATE         # Baud rate (default: 9600)
--timeout SECONDS       # Response timeout (default: 1.0)
--delay SECONDS         # Inter-keystroke delay (default: 0.075)
--report FILENAME       # Save statistics report to JSON file
--failures FILENAME     # Save detailed failure log to JSON file
```

**Important**: Use both `--report` and `--failures` for complete analysis. The statistics report contains per-category metrics, while the failure log contains detailed information about every failure.

### Understanding Fuzz Reports

**Real-Time Progress Display:**
```
Elapsed: 0:05:23 | Inputs: 4230 | Success: 98.3% | Throughput: 13.1/s | Avg Response: 52.4ms | Failures: 72
```

**Summary Output (sorted by failure rate):**
```
Category Breakdown (sorted by failure rate):
  ctrl_alt_function        :   142 total,   28 failures ( 80.3% success)
  shift_ctrl_alt_letters   :    89 total,   12 failures ( 86.5% success)
  shift_ctrl_navigation    :   105 total,    8 failures ( 92.4% success)
  alt_function             :   156 total,    5 failures ( 96.8% success)

Categories with 100% success:
  letters                  :   423 total
  shift_letters            :   387 total
  digits                   :   198 total
```

The summary shows:
- **Per-category success rates**: Identify problematic modifier combinations
- **Sorted by failures**: Categories with most failures appear first
- **100% success categories**: Shows robust implementations
- **Performance metrics**: Throughput and response times
- **Recent failures**: Last 10 failures with human-readable descriptions

**Statistics Report JSON** (`--report stats.json`):
```json
{
  "summary": {
    "duration_seconds": 323,
    "total_inputs": 4230,
    "success_rate": 98.3,
    "throughput_per_second": 13.1
  },
  "category_statistics": {
    "ctrl_alt_function": {
      "total": 142,
      "successes": 114,
      "failures": 28,
      "success_rate": 80.3
    }
  }
}
```

**Failure Log JSON** (`--failures failures.json`):
```json
{
  "metadata": {
    "total_failures": 72,
    "total_tests": 4230
  },
  "failures": [
    {
      "timestamp": "2026-01-23T17:12:15",
      "category": "ctrl_alt_function",
      "key_description": "Ctrl+Alt+F5",
      "input_hex": "1b5b31353b377e",
      "input_bytes": [27, 91, 49, 53, 59, 55, 126],
      "error_type": "timeout"
    }
  ]
}
```

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
- If failures cluster in specific modifier combinations (e.g., "ctrl_alt_function")
- Indicates issues with that modifier/key type combination
- Focus debugging on VT100 escape sequence generation for those modifiers
- Check CSI parameter encoding (modifier values: Shift=1, Alt=2, Ctrl=4)

**Example Analysis**:
- **High failures in `ctrl_alt_*` categories**: Check Ctrl+Alt escape sequence generation
- **High failures in `*_function` categories**: Check function key CSI format with modifiers
- **High failures in `shift_ctrl_*` categories**: Check multi-modifier combinations

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

Review both JSON files for comprehensive failure analysis:

```python
import json
from collections import Counter, defaultdict

# Load statistics report
with open('stats.json') as f:
    stats = json.load(f)

# Find categories with lowest success rates
categories = stats['category_statistics']
sorted_cats = sorted(categories.items(),
                     key=lambda x: x[1]['success_rate'])

print("Categories with lowest success rates:")
for cat, data in sorted_cats[:5]:
    print(f"  {cat}: {data['success_rate']:.1f}% "
          f"({data['failures']}/{data['total']} failures)")

# Load failure log
with open('failures.json') as f:
    failures = json.load(f)

# Analyze error types by category
error_by_category = defaultdict(lambda: defaultdict(int))
for failure in failures['failures']:
    error_by_category[failure['category']][failure['error_type']] += 1

print("\nError types by category:")
for category, errors in error_by_category.items():
    print(f"  {category}: {dict(errors)}")

# Find specific failing keys
print("\nMost common failing key descriptions:")
key_failures = Counter(f['key_description'] for f in failures['failures'])
for key, count in key_failures.most_common(10):
    print(f"  {key}: {count} failures")
```

Common failure patterns:
- **Timeout errors**: Arduino not responding, possible buffer overflow or parser hang
- **Unexpected errors**: Arduino returns ERROR message for valid input
- **Modifier-specific patterns**: Certain modifier combinations consistently fail
- **Key-type specific**: Certain key types (e.g., function, navigation) fail more
- **Failures after long runs**: Potential memory leaks or buffer management issues

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
