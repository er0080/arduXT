# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**arduXT** is an Arduino Leonardo-based XT keyboard emulator that translates USB Serial input into IBM PC/XT keyboard protocol signals. The Arduino acts as a bridge between modern computers and vintage PC/XT systems that require 5-pin DIN keyboard connectors.

**Target Hardware**: Arduino Leonardo (ATmega32U4)

## Common Commands

### Compilation and Upload

```bash
# Compile the sketch (verify syntax and generate binary)
arduino-cli compile --fqbn arduino:avr:leonardo .

# Find the Leonardo's port (look for /dev/cu.usbmodem*)
arduino-cli board list

# Upload to Arduino Leonardo
arduino-cli upload -p /dev/cu.usbmodem14101 --fqbn arduino:avr:leonardo .

# Compile and upload in one command
arduino-cli compile --fqbn arduino:avr:leonardo . && arduino-cli upload -p /dev/cu.usbmodem14101 --fqbn arduino:avr:leonardo .
```

### Serial Monitor

```bash
# Monitor serial output (9600 baud)
arduino-cli monitor -p /dev/cu.usbmodem14101 -c baudrate=9600

# Alternative: using screen (Ctrl-A, K to exit)
screen /dev/cu.usbmodem14101 9600
```

### Library Management

```bash
# Search for libraries
arduino-cli lib search <keyword>

# Install a library
arduino-cli lib install "<Library Name>"

# List installed libraries
arduino-cli lib list
```

## Architecture

### Core Components

**arduXT.ino**: Monolithic sketch containing all logic. The architecture is organized into functional blocks:

1. **Pin Definitions** (lines 14-15)
   - `XT_CLK_PIN`: Clock signal output (Pin 2)
   - `XT_DATA_PIN`: Data signal output (Pin 3)

2. **Protocol Timing** (line 18)
   - `XT_CLK_HALF_PERIOD`: Defines clock frequency (~12.5 kHz default)

3. **Serial Input Handler** (in `loop()`)
   - Reads from USB Serial (Leonardo's built-in `Serial` object)
   - Converts ASCII characters to XT scancodes
   - Triggers scancode transmission

4. **XT Protocol Layer** (`sendXTScancode()`, `xtClockPulse()`)
   - `sendXTScancode()`: Implements XT serial protocol (start bit + 8 data bits LSB-first + stop bit)
   - `xtClockPulse()`: Generates precise clock pulses with configurable timing

5. **Scancode Mapping** (`charToXTScancode()`)
   - Translates ASCII characters to XT keyboard scancodes
   - Returns 0 for unmapped characters

### XT Keyboard Protocol Details

The XT protocol implementation follows these specifications:
- **Clock**: Keyboard-generated, ~10-16 kHz (configurable via `XT_CLK_HALF_PERIOD`)
- **Data Format**: 1 start bit (LOW) + 8 data bits (LSB first) + 1 stop bit (HIGH)
- **Idle State**: Both clock and data lines HIGH
- **Make/Break Codes**: Make code for key press, make code + 0x80 for key release

### Signal Flow

```
USB Serial Input → ASCII char → charToXTScancode() → Make code → sendXTScancode()
                                                    ↓
                                                   Delay (50ms)
                                                    ↓
                                                   Break code → sendXTScancode()
```

### Key Timing Constraints

- **Clock Period**: Controlled by `XT_CLK_HALF_PERIOD` (currently 40μs = 12.5 kHz)
- **Key Press Duration**: 50ms between make and break codes
- **Bit Timing**: Clock pulses are synchronized with data bit transitions

## Development Guidelines

### Adding New Scancodes

To support additional keys, extend the `charToXTScancode()` function. Reference:
- Function keys: F1 (0x3B) through F10 (0x44)
- Cursor keys: Up (0x48), Down (0x50), Left (0x4B), Right (0x4D)
- Modifiers: Left Shift (0x2A), Right Shift (0x36), Ctrl (0x1D), Alt (0x38)

### Timing Adjustments

If compatibility issues arise with specific PC/XT systems:
1. Adjust `XT_CLK_HALF_PERIOD` (typical range: 31-50μs)
2. Modify key press duration in `loop()` (currently 50ms)
3. Test with oscilloscope if available to verify signal timing

### Pin Configuration

Current assignment uses digital pins 2-3. If conflicts arise with shields or other hardware:
- Update `XT_CLK_PIN` and `XT_DATA_PIN` definitions
- Avoid pins 0-1 (hardware serial), 13 (built-in LED), or pins with special functions

### Leonardo-Specific Considerations

- **USB Serial**: Uses `Serial` object (built-in USB CDC)
- **Hardware Serial**: `Serial1` available on pins 0 (RX) and 1 (TX) if needed
- **Reset Behavior**: Leonardo requires `while (!Serial)` in `setup()` to wait for USB connection
- **Bootloader**: Leonardo enters bootloader mode briefly on USB connection; may require reset before upload

## Testing

### Manual Testing

1. Upload sketch to Leonardo
2. Connect serial monitor at 9600 baud
3. Type characters and verify:
   - Characters are echoed back
   - No errors or warnings
4. Connect to PC/XT and verify keyboard signals with logic analyzer or actual system response

### Signal Verification

Use a logic analyzer or oscilloscope to verify:
- Clock frequency is within 10-16 kHz range
- Data transitions align with clock pulses
- Idle state: both lines HIGH
- Start bit: data LOW during first clock pulse
- Stop bit: data HIGH during last clock pulse

## Troubleshooting Commands

```bash
# Check if Leonardo is detected
arduino-cli board list

# Verify core is installed
arduino-cli core list

# Compile with verbose output
arduino-cli compile --fqbn arduino:avr:leonardo . --verbose

# Upload with verbose output
arduino-cli upload -p /dev/cu.usbmodem14101 --fqbn arduino:avr:leonardo . --verbose
```

## Project Structure

```
arduXT/
├── arduXT.ino          # Main sketch (all code in one file)
├── README.md           # User documentation, wiring diagrams
└── CLAUDE.md           # This file
```

This project uses a single-file Arduino sketch architecture. For future expansion with multiple files:
- Create `.cpp`/`.h` files in the same directory
- Arduino IDE automatically includes them in compilation
