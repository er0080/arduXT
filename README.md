# arduXT - XT Keyboard Emulator

A DFRobot Beetle-based XT keyboard emulator that receives keystrokes via USB Serial and outputs IBM PC/XT compatible keyboard signals. This allows modern computers to send keystrokes to vintage IBM PC/XT systems that require a 5-pin DIN keyboard connector.

## Features

- **Complete XT Scancode Set 1 support** (83-key PC/XT keyboard layout)
- **VT100 escape sequence parsing** for function and navigation keys
- **Automatic shift modifier handling** for shifted characters (!@#$%^&*() etc.)
- **Function keys** F1-F12 with modifier support (Alt+Fn, Ctrl+Fn, Ctrl+Alt+Fn)
- **Navigation keys** (arrows, Home, End, PgUp, PgDn, Insert, Delete)
- **Control sequences** Ctrl+A through Ctrl+Z
- **Alt combinations** Alt+letter, Alt+number, Alt+Shift+key
- **Full ASCII character support** including all printable characters
- **Precise timing** for XT protocol compatibility (~12.5 kHz clock)
- **USB Serial input** for easy keystroke transmission
- **Hardware-in-the-loop test suite** with 97 comprehensive tests
- **Ultra-compact form factor** (20mm x 22mm DFRobot Beetle)

## Hardware Requirements

- **DFRobot Beetle** (ATmega32U4, Leonardo-compatible)
  - Board info: https://wiki.dfrobot.com/Beetle_SKU_DFR0282
  - Dimensions: 20mm x 22mm x 3.8mm
- **5-pin DIN connector** (for PC/XT keyboard port)
- **Jumper wires**
- **Resistors** (optional, for level shifting if needed)

### Important Power Notes

- **Operating voltage**: 4.5-5V DC
- **WARNING**: 6V will damage the board by overvoltage
- Power via Micro USB or VCC/GND pads

## XT Keyboard Protocol

The IBM PC/XT keyboard uses a serial protocol with the following characteristics:

- **Clock frequency**: 10-16 kHz (typically ~12.5 kHz)
- **Data format**: 1 start bit (1) + 8 data bits (LSB first)
- **Voltage levels**: TTL (0-5V)
- **Master**: Keyboard generates both clock and data signals
- **Idle state**: Both clock and data lines HIGH

### Scancode Format

- **Make code**: Sent when key is pressed (e.g., 0x1E for 'A')
- **Break code**: Make code + 0x80 (e.g., 0x9E for 'A' release)

## Wiring Diagram

### DFRobot Beetle to XT Keyboard Port (5-pin DIN)

![5-pin DIN connector pinout](https://sharktastica.co.uk/resources/images/pinouts/host_xt-rst_180din5.jpg)

**Pin Assignments:**
- **Pin 1**: Clock (from Beetle Pin 9)
- **Pin 2**: Data (from Beetle Pin 10)
- **Pin 3**: Reset (leave unconnected or tie to +5V via 10K resistor)
- **Pin 4**: Ground
- **Pin 5**: +5V (Power - can power Beetle or provide from Beetle)

### Pin Connections

| Beetle Pin | XT Signal | DIN Pin | Description |
|------------|-----------|---------|-------------|
| D9         | Clock     | 1       | Clock signal (~12.5 kHz) |
| D10        | Data      | 2       | Serial data signal |
| VCC (+)    | +5V       | 5       | Power (optional, max 5V!) |
| GND (-)    | Ground    | 4       | Common ground |

**Important Notes**:
- DIN Pin 3 (Reset) can be left unconnected or tied to +5V through a 10K resistor
- Beetle pins 2/3 are used for I2C (SDA/SCL) and should not be used for this project
- Pins 9, 10, 11 are the only general-purpose digital I/O pins on the Beetle
- **Never exceed 5V** on the Beetle VCC; 6V will damage the board

## Installation & Setup

### 1. Install Arduino CLI

```bash
brew install arduino-cli
```

### 2. Configure Arduino CLI for DFRobot Beetle

```bash
# Initialize configuration
arduino-cli config init

# Update core index
arduino-cli core update-index

# Install AVR core (includes Leonardo support for Beetle)
arduino-cli core install arduino:avr
```

**Note**: The DFRobot Beetle uses the same bootloader as Arduino Leonardo, so use the `arduino:avr:leonardo` board identifier.

### 3. Connect DFRobot Beetle

Connect your DFRobot Beetle via Micro USB. Find the port:

```bash
arduino-cli board list
```

Look for a port like `/dev/cu.usbmodem*` with board type "Arduino Leonardo" (Beetle is Leonardo-compatible).

### 4. Compile and Upload

#### Using the Build Helper Script (Recommended)

The easiest way to build and upload is using the `build.sh` helper script:

```bash
# Make script executable (first time only)
chmod +x build.sh

# Production build (default - no debug output, GPIO enabled)
./build.sh /dev/cu.usbmodem14101

# View all build options
./build.sh --help
```

#### Manual Compilation

For manual control or custom configurations:

```bash
# Compile the sketch (from project root)
arduino-cli compile --fqbn arduino:avr:leonardo .

# Upload to Leonardo (replace PORT with your actual port)
arduino-cli upload -p /dev/cu.usbmodem14101 --fqbn arduino:avr:leonardo .

# Or combine both commands
arduino-cli compile --fqbn arduino:avr:leonardo . && \
  arduino-cli upload -p /dev/cu.usbmodem14101 --fqbn arduino:avr:leonardo .
```

**Build Modes**: For debugging or testing, you can enable additional output with compile-time flags:

```bash
# Verbose mode (adds scancode debug output)
arduino-cli compile --fqbn arduino:avr:leonardo \
  --build-property "compiler.cpp.extra_flags=-DVERBOSE_SCANCODES" .

# Test mode (disables GPIO for serial testing without hardware)
arduino-cli compile --fqbn arduino:avr:leonardo \
  --build-property "compiler.cpp.extra_flags=-DARDUXT_TEST_MODE" .
```

Or use the build script:
```bash
./build.sh /dev/cu.usbmodem14101 verbose      # Verbose mode
./build.sh /dev/cu.usbmodem14101 test         # Test mode
./build.sh /dev/cu.usbmodem14101 test-verbose # Both modes
```

**Note for Apple Silicon users**: The Arduino AVR toolchain doesn't have native ARM64 support. Compile on an x64 platform or use Docker/VM.

## Usage

### 1. Connect Hardware

Wire the DFRobot Beetle to your PC/XT's keyboard port according to the wiring diagram above.

### 2. Open Serial Monitor

```bash
# Using arduino-cli
arduino-cli monitor -p /dev/cu.usbmodem14101 -c baudrate=9600

# Or using screen
screen /dev/cu.usbmodem14101 9600
```

### 3. Send Keystrokes

Type characters in the serial terminal. Each character will be:
1. Echoed back to the serial monitor
2. Converted to XT scancode
3. Transmitted to the PC/XT as a make code (key press)
4. Followed by a break code (key release) after 50ms

### Example

```
Received: H
Received: e
Received: l
Received: l
Received: o
```

The PC/XT will receive these as proper keyboard scancodes.

## Supported Keys

arduXT supports the complete XT Scancode Set 1 (83-key PC/XT keyboard layout).

### Printable Characters

**Letters**: A-Z, a-z (uppercase automatically sends with Shift)

**Numbers**: 0-9

**Shifted Characters** (automatically wrapped with Shift make/break):
- `!` `@` `#` `$` `%` `^` `&` `*` `(` `)`
- `_` `+` `{` `}` `|` `:` `"` `<` `>` `?` `~`

**Unshifted Punctuation**:
- `-` `=` `[` `]` `;` `'` `` ` `` `\` `,` `.` `/`

### Special Keys

**Control Keys**: Space, Enter, Backspace, Tab, Escape

### Function Keys (VT100 Sequences)

Requires terminal configured for VT100 mode:

| Key | VT100 Sequence | XT Scancode |
|-----|----------------|-------------|
| F1 | `ESCOP` | 0x3B |
| F2 | `ESCOQ` | 0x3C |
| F3 | `ESCOR` | 0x3D |
| F4 | `ESCOS` | 0x3E |
| F5 | `ESC[15~` | 0x3F |
| F6 | `ESC[17~` | 0x40 |
| F7 | `ESC[18~` | 0x41 |
| F8 | `ESC[19~` | 0x42 |
| F9 | `ESC[20~` | 0x43 |
| F10 | `ESC[21~` | 0x44 |
| F11 | `ESC[23~` | 0x57 |
| F12 | `ESC[24~` | 0x58 |

**Modifier Support**: Function keys support modifiers via CSI parameters:
- `Alt+Fn`: `ESC[15;3~` (modifier = 3)
- `Ctrl+Fn`: `ESC[15;5~` (modifier = 5)
- `Ctrl+Alt+Fn`: `ESC[15;7~` (modifier = 7)
- `Shift+Fn`: `ESC[15;2~` (modifier = 2)

F1-F4 also support double-ESC sequences for Alt modifier:
- `Alt+F1`: `ESC ESC O P` or `ESC[1;3P`

### Navigation Keys (VT100 Sequences)

| Key | VT100 Sequence | XT Scancode |
|-----|----------------|-------------|
| Up Arrow | `ESC[A` | 0x48 |
| Down Arrow | `ESC[B` | 0x50 |
| Right Arrow | `ESC[C` | 0x4D |
| Left Arrow | `ESC[D` | 0x4B |
| Home | `ESC[H` or `ESC[1~` | 0x47 |
| End | `ESC[F` or `ESC[4~` | 0x4F |
| Insert | `ESC[2~` | 0x52 |
| Delete | `ESC[3~` | 0x53 |
| Page Up | `ESC[5~` | 0x49 |
| Page Down | `ESC[6~` | 0x51 |

**Note**: Numeric keypad keys share scancodes with navigation keys on XT keyboards. Num Lock determines behavior on the PC side.

### Control Sequences

Control sequences are sent as ASCII control characters (0x01-0x1A):

| Sequence | ASCII Code | XT Scancode (Ctrl + key) |
|----------|------------|--------------------------|
| Ctrl+A | 0x01 | Ctrl (0x1D) + A (0x1E) |
| Ctrl+B | 0x02 | Ctrl (0x1D) + B (0x30) |
| ... | ... | ... |
| Ctrl+Z | 0x1A | Ctrl (0x1D) + Z (0x2C) |

**Ctrl+Alt Combinations**: Sent as `ESC` followed by the control character:
- `Ctrl+Alt+A`: `ESC 0x01`

### Alt Key Combinations

Alt combinations are sent using double-ESC sequences:

**Alt+Letter**: `ESC ESC <char>` or `ESC <char>`
- Example: `Alt+A` = `ESC ESC a` or `ESC a`

**Alt+Number**: `ESC ESC <digit>`
- Example: `Alt+1` = `ESC ESC 1`

**Alt+Shift+Key**: Modifier parameter in escape sequences
- Example: `Alt+Shift+F5` = `ESC[15;2;3~`

## Terminal Configuration (PuTTY)

To use function keys and navigation keys with arduXT, configure your terminal to send VT100 escape sequences.

### PuTTY Settings

1. **Connection → Data**:
   - Terminal-type string: `vt100`

2. **Terminal → Keyboard**:
   - The Function keys and keypad: `VT100+`
   - The Home and End keys: `Standard`
   - The Backspace key: `Control-H`
   - Initial state of cursor keys: `Normal`
   - Initial state of numeric keypad: `Normal`

3. **Connection → Serial**:
   - Speed (baud): `9600`
   - Data bits: `8`
   - Stop bits: `1`
   - Parity: `None`
   - Flow control: `None`

### Testing VT100 Sequences

You can verify escape sequences are being sent correctly by watching the serial monitor output. When you press a function or navigation key, you should see:

```
ESC received
CSI sequence
Sequence parsed: 0x48
```

Or for function keys:

```
ESC received
SS3 sequence
Sequence parsed: 0x3B
```

### Other Terminal Emulators

- **screen**: Use `TERM=vt100 screen /dev/cu.usbmodem14101 9600`
- **minicom**: Set terminal type to VT100 in configuration
- **arduino-cli monitor**: Limited VT100 support, PuTTY recommended

## Testing

arduXT includes a comprehensive hardware-in-the-loop test suite with 97 tests covering:
- Basic characters (lowercase, uppercase, digits, spaces)
- Punctuation (shifted and unshifted)
- Control sequences (Ctrl+A through Ctrl+Z)
- Function keys (F1-F12)
- Function key modifiers (Alt+Fn, Ctrl+Fn, Ctrl+Alt+Fn)
- Navigation keys (arrows, Home, End, etc.)
- Alt combinations (Alt+letter, Alt+number, Alt+Shift+key)
- Special cases (standalone ESC, escape sequence timeouts)

### Running Tests

```bash
# Navigate to tests directory
cd tests/

# Install dependencies (using uv package manager)
uv sync

# Build Arduino sketch with test flags
cd ..
./build.sh /dev/cu.usbmodem14101 test-verbose

# Run test suite
cd tests/
uv run test_arduxt.py /dev/cu.usbmodem14101
```

For detailed test documentation, see [tests/README.md](tests/README.md).

**Test Requirements**:
- `uv` package manager (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Arduino sketch compiled with `ARDUXT_TEST_MODE` and `VERBOSE_SCANCODES` flags
- DFRobot Beetle connected via USB

## Customization

### Adjusting Clock Frequency

The XT protocol typically uses 10-16 kHz. The default is ~12.5 kHz. To adjust:

```cpp
#define XT_CLK_HALF_PERIOD 40  // 80us period = 12.5 kHz
```

Change this value in `arduXT.ino`:
- Increase for slower clock (e.g., 50 = 10 kHz)
- Decrease for faster clock (e.g., 31 = 16 kHz)

### Key Repeat Delay

Default key press duration is 50ms. Adjust in the main loop:

```cpp
delay(50);  // Change this value
```

### Adding More Scancodes

Extend the `charToXTScancode()` function to support additional keys. Full XT scancode reference:
- Function keys (F1-F10): 0x3B-0x44
- Cursor keys: Up (0x48), Down (0x50), Left (0x4B), Right (0x4D)
- Modifier keys: Shift (0x2A/0x36), Ctrl (0x1D), Alt (0x38)

## Troubleshooting

### No response from PC/XT
- Check wiring connections
- Verify correct DIN pin numbering (numbering varies by DIN standard)
- Try adjusting clock frequency
- Ensure both Arduino and PC/XT share common ground

### Garbled output
- Clock frequency may be too fast/slow for your system
- Check signal integrity with oscilloscope if available
- Verify proper idle state (both lines HIGH)

### Beetle not responding
- Press reset button on Beetle (if accessible)
- Reupload sketch
- Check Micro USB cable connection
- Verify power supply is within 4.5-5V range

## Technical References

- [DFRobot Beetle Wiki](https://wiki.dfrobot.com/Beetle_SKU_DFR0282)
- [IBM PC/XT Keyboard Protocol](https://github.com/tmk/tmk_keyboard/wiki/IBM-PC-XT-Keyboard-Protocol)
- [XT Scancode Set](https://sharktastica.co.uk/topics/keyboard-scancodes#Set1)
- [BrokenThorn Scancode Reference](https://brokenthorn.com/Resources/OSDevScanCodes.html)
- [Arduino Leonardo Pinout](https://docs.arduino.cc/hardware/leonardo) (Beetle is Leonardo-compatible)

## License

MIT License - Feel free to modify and distribute.

## Contributing

Contributions welcome! Areas for improvement:
- Bidirectional communication (PC commands to keyboard)
- Configurable pin assignments via runtime commands
- EEPROM configuration storage
- Adjustable timing parameters via serial commands
