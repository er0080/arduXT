# arduXT - XT Keyboard Emulator

A DFRobot Beetle-based XT keyboard emulator that receives keystrokes via USB Serial and outputs IBM PC/XT compatible keyboard signals. This allows modern computers to send keystrokes to vintage IBM PC/XT systems that require a 5-pin DIN keyboard connector.

## Features

- Full XT keyboard protocol implementation
- USB Serial input for easy keystroke transmission
- ASCII to XT scancode mapping for letters, numbers, and common punctuation
- Precise timing for XT protocol compatibility (~12.5 kHz clock)
- Make and break code generation for proper key press/release simulation
- Ultra-compact form factor (20mm x 22mm)

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
- **Data format**: 1 start bit (0) + 8 data bits (LSB first) + 1 stop bit (1)
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

```bash
# Compile the sketch (from project root)
arduino-cli compile --fqbn arduino:avr:leonardo .

# Upload to Leonardo (replace PORT with your actual port)
arduino-cli upload -p /dev/cu.usbmodem14101 --fqbn arduino:avr:leonardo .
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

### Letters
- A-Z (case insensitive)

### Numbers
- 0-9

### Special Keys
- Space
- Enter
- Backspace
- Tab
- Escape

### Punctuation
- `-` Minus/Hyphen
- `=` Equals
- `[` Left Bracket
- `]` Right Bracket
- `;` Semicolon
- `'` Apostrophe
- `` ` `` Grave Accent
- `\` Backslash
- `,` Comma
- `.` Period
- `/` Slash

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
- Extended scancode support (function keys, numpad)
- Bidirectional communication (PC commands to keyboard)
- Configurable pin assignments
- EEPROM configuration storage
