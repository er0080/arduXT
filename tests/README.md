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

### TEST_MODE (disabled by default)
Disables GPIO operations for faster testing without hardware:
```cpp
#define TEST_MODE
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
├── test_arduxt.py      # Main test harness
├── pyproject.toml      # Project dependencies
├── requirements.txt    # Alternative dependency list
└── README.md           # This file
```
