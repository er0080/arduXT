# Expanded Scancode Support Specification

**Version**: 1.0
**Date**: 2026-01-22
**Status**: Draft

## Overview

This specification describes the expansion of arduXT to support the complete XT Scancode Set 1, including VT100 escape sequence parsing for special keys, automatic shift modifier handling, and numeric keypad support.

## Goals

1. Support the complete XT Scancode Set 1 (83-key PC/XT keyboard)
2. Parse VT100 escape sequences for navigation and function keys
3. Automatically generate shift make/break codes for shifted characters
4. Support toggle behavior for lock keys (Caps/Num/Scroll Lock)
5. Distinguish between main keyboard and numeric keypad

## Current Implementation

### Supported Keys (v1.0 baseline)

- **Letters**: A-Z (26 keys)
- **Numbers**: 0-9 (10 keys)
- **Punctuation**: `-`, `=`, `[`, `]`, `;`, `'`, `` ` ``, `\`, `,`, `.`, `/` (11 keys)
- **Special keys**: Space, Enter, Backspace, Tab, Escape (5 keys)

**Total**: 52 keys

### Current Limitations

- No function key support
- No navigation key support (arrows, Home, End, etc.)
- No modifier key support (Shift, Ctrl, Alt)
- No lock key support (Caps Lock, Num Lock, Scroll Lock)
- No numeric keypad support
- Shifted characters not supported

## Proposed Implementation

### 1. Complete XT Scancode Set 1 Mapping

#### Main Keyboard Layout

| Key | Make Code | Break Code | Notes |
|-----|-----------|------------|-------|
| **Function Keys** | | | |
| F1 | 0x3B | 0xBB | |
| F2 | 0x3C | 0xBC | |
| F3 | 0x3D | 0xBD | |
| F4 | 0x3E | 0xBE | |
| F5 | 0x3F | 0xBF | |
| F6 | 0x40 | 0xC0 | |
| F7 | 0x41 | 0xC1 | |
| F8 | 0x42 | 0xC2 | |
| F9 | 0x43 | 0xC3 | |
| F10 | 0x44 | 0xC4 | |
| **Modifier Keys** | | | |
| Left Shift | 0x2A | 0xAA | |
| Right Shift | 0x36 | 0xB6 | |
| Ctrl | 0x1D | 0x9D | |
| Alt | 0x38 | 0xB8 | |
| **Lock Keys** | | | |
| Caps Lock | 0x3A | 0xBA | Toggle behavior |
| Num Lock | 0x45 | 0xC5 | Toggle behavior |
| Scroll Lock | 0x46 | 0xC6 | Toggle behavior |
| **Navigation Keys** | | | |
| Up Arrow | 0x48 | 0xC8 | |
| Down Arrow | 0x50 | 0xD0 | |
| Left Arrow | 0x4B | 0xCB | |
| Right Arrow | 0x4D | 0xCD | |
| Home | 0x47 | 0xC7 | |
| End | 0x4F | 0xCF | |
| Page Up | 0x49 | 0xC9 | |
| Page Down | 0x51 | 0xD1 | |
| Insert | 0x52 | 0xD2 | |
| Delete | 0x53 | 0xD3 | |
| **System Keys** | | | |
| Escape | 0x01 | 0x81 | Already supported |
| Backspace | 0x0E | 0x8E | Already supported |
| Tab | 0x0F | 0x8F | Already supported |
| Enter | 0x1C | 0x9C | Already supported |
| Space | 0x39 | 0xB9 | Already supported |

#### Numeric Keypad

| Key | Make Code | Break Code | Notes |
|-----|-----------|------------|-------|
| KP 0 / Insert | 0x52 | 0xD2 | Shared with Insert |
| KP 1 / End | 0x4F | 0xCF | Shared with End |
| KP 2 / Down | 0x50 | 0xD0 | Shared with Down |
| KP 3 / PgDn | 0x51 | 0xD1 | Shared with PgDn |
| KP 4 / Left | 0x4B | 0xCB | Shared with Left |
| KP 5 | 0x4C | 0xCC | Center key |
| KP 6 / Right | 0x4D | 0xCD | Shared with Right |
| KP 7 / Home | 0x47 | 0xC7 | Shared with Home |
| KP 8 / Up | 0x48 | 0xC8 | Shared with Up |
| KP 9 / PgUp | 0x49 | 0xC9 | Shared with PgUp |
| KP * (Multiply) | 0x37 | 0xB7 | |
| KP - (Minus) | 0x4A | 0xCA | |
| KP + (Plus) | 0x4E | 0xCE | |
| KP . / Delete | 0x53 | 0xD3 | Shared with Delete |

**Note**: XT keyboards share scancodes between keypad and navigation keys. Num Lock determines behavior on the PC side.

#### Shifted Characters

Characters that require Shift key on XT keyboard:

| ASCII | Key | Scancode | Shift Required |
|-------|-----|----------|----------------|
| ! | 1 | 0x02 | Yes |
| @ | 2 | 0x03 | Yes |
| # | 3 | 0x04 | Yes |
| $ | 4 | 0x05 | Yes |
| % | 5 | 0x06 | Yes |
| ^ | 6 | 0x07 | Yes |
| & | 7 | 0x08 | Yes |
| * | 8 | 0x09 | Yes |
| ( | 9 | 0x0A | Yes |
| ) | 0 | 0x0B | Yes |
| _ | - | 0x0C | Yes |
| + | = | 0x0D | Yes |
| { | [ | 0x1A | Yes |
| } | ] | 0x1B | Yes |
| \| | \ | 0x2B | Yes |
| : | ; | 0x27 | Yes |
| " | ' | 0x28 | Yes |
| ~ | `` ` `` | 0x29 | Yes |
| < | , | 0x33 | Yes |
| > | . | 0x34 | Yes |
| ? | / | 0x35 | Yes |

### 2. VT100 Escape Sequence Support

arduXT will parse standard VT100 escape sequences for special keys.

#### Navigation Keys

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

#### Function Keys

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

#### Modifier Keys (Optional)

For terminals that support explicit modifier sequences:

| Sequence | Key | XT Scancode |
|----------|-----|-------------|
| `ESC[1;2` prefix | Shift held | 0x2A (make only) |
| `ESC[1;5` prefix | Ctrl held | 0x1D (make only) |
| `ESC[1;3` prefix | Alt held | 0x38 (make only) |

**Note**: Standard VT100 doesn't send explicit Shift/Ctrl/Alt sequences. These are optional extensions.

### 3. Escape Sequence Parser Design

#### State Machine

The parser implements a simple state machine:

```
States:
- NORMAL: Regular character input
- ESC: Received ESC (0x1B), waiting for next char
- CSI: Received ESC[, collecting sequence
- SS3: Received ESCO, collecting single-char sequence

Transitions:
NORMAL + 0x1B → ESC
ESC + '[' → CSI
ESC + 'O' → SS3
ESC + other → back to NORMAL (invalid)
CSI + digit → collect digit
CSI + '~' → process sequence, back to NORMAL
CSI + letter → process sequence, back to NORMAL
SS3 + letter → process sequence, back to NORMAL
```

#### Buffer Management

- **Escape buffer**: 8-byte buffer for collecting escape sequences
- **Buffer index**: Track current position in buffer
- **Timeout**: 100ms timeout to reset state machine if incomplete sequence

### 4. Shifted Character Handling

When a shifted character is received (e.g., `!`):

1. Send Left Shift make code (0x2A)
2. Send base key make code (e.g., 0x02 for '1')
3. Delay (key press duration, 50ms default)
4. Send base key break code (e.g., 0x82)
5. Send Left Shift break code (0xAA)

**Implementation**:
```cpp
void sendKeyWithShift(uint8_t baseCode) {
  sendXTScancode(0x2A);           // Shift make
  sendXTScancode(baseCode);       // Key make
  delay(50);                      // Key press duration
  sendXTScancode(baseCode | 0x80); // Key break
  sendXTScancode(0xAA);           // Shift break
}
```

### 5. Lock Key Behavior

Lock keys (Caps Lock, Num Lock, Scroll Lock) use toggle behavior:

1. Send make code
2. Delay (50ms)
3. Send break code
4. No state tracking needed (PC handles lock state)

**Implementation**:
```cpp
void sendToggleKey(uint8_t scancode) {
  sendXTScancode(scancode);        // Make
  delay(50);                       // Key press duration
  sendXTScancode(scancode | 0x80); // Break
}
```

### 6. Architecture Changes

#### New Functions

1. **`parseEscapeSequence()`**: Process escape sequence buffer and return scancode
2. **`sendKeyWithShift(uint8_t baseCode)`**: Send key with shift modifiers
3. **`sendToggleKey(uint8_t scancode)`**: Send lock key toggle
4. **`isShiftedChar(char c)`**: Check if character requires shift
5. **`getBaseKey(char c)`**: Get base key scancode for shifted character

#### Modified Functions

1. **`loop()`**: Add escape sequence state machine
2. **`charToXTScancode()`**: Expand to all printable ASCII characters

#### New Data Structures

```cpp
// Parser state
enum EscapeState {
  STATE_NORMAL,
  STATE_ESC,
  STATE_CSI,
  STATE_SS3
};

// Escape sequence buffer
char escBuffer[8];
uint8_t escIndex = 0;
EscapeState escState = STATE_NORMAL;
unsigned long escTimeout = 0;
```

## Testing Plan

### Unit Tests

1. **Basic ASCII**: Verify all printable ASCII characters
2. **Shifted characters**: Verify shift make/break wrapping
3. **Function keys**: Test F1-F10 sequences
4. **Navigation keys**: Test all arrow and navigation sequences
5. **Lock keys**: Verify toggle behavior
6. **Keypad**: Test numeric keypad sequences (if distinguishable)

### Integration Tests

1. **PuTTY configuration**: Verify VT100 mode settings
2. **Real XT PC**: Test on actual IBM PC/XT hardware
3. **Edge cases**: Incomplete sequences, rapid input, timeout behavior

## PuTTY Configuration

Recommended PuTTY settings for VT100 compatibility:

```
Connection → Data → Terminal-type string: "vt100"
Terminal → Keyboard:
  - Function keys: VT100+
  - Home and End keys: Standard
  - Arrow keys: ANSI
  - Keypad: Normal
```

## Performance Considerations

- **Escape sequence timeout**: 100ms (configurable)
- **Key press duration**: 50ms (configurable)
- **Buffer size**: 8 bytes (sufficient for longest VT100 sequence)
- **Memory overhead**: ~20 bytes for parser state

## Future Enhancements

1. **Extended scancodes**: Support E0-prefixed scancodes (not in XT)
2. **Configurable mapping**: Store custom keymaps in EEPROM
3. **LED feedback**: Drive Caps/Num/Scroll Lock LEDs
4. **Bidirectional**: Receive commands from PC (rare on XT)
5. **Multiple profiles**: Switch between different keymap profiles

## References

- [XT Scancode Set 1](https://sharktastica.co.uk/topics/keyboard-scancodes#Set1)
- [VT100 Escape Sequences](https://vt100.net/docs/vt100-ug/chapter3.html)
- [IBM PC/XT Keyboard Protocol](https://github.com/tmk/tmk_keyboard/wiki/IBM-PC-XT-Keyboard-Protocol)
- [BrokenThorn Scancode Reference](https://brokenthorn.com/Resources/OSDevScanCodes.html)

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-22 | Initial specification |
