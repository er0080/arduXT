/*
 * arduXT - XT Keyboard Emulator for DFRobot Beetle
 *
 * Receives keystrokes via USB Serial and outputs XT keyboard protocol
 * signals over GPIO pins for use with vintage IBM PC/XT computers.
 *
 * Target Hardware: DFRobot Beetle (ATmega32u4, Leonardo-compatible)
 * Board: https://wiki.dfrobot.com/Beetle_SKU_DFR0282
 *
 * XT Protocol:
 * - Clock frequency: ~10-16 kHz
 * - Data format: Start bit (1) + 8 data bits (LSB first)
 * - Keyboard is master (generates clock and data)
 */

// XT Keyboard Protocol Pins
// Using pins 9 and 10 (general purpose digital I/O on Beetle)
// Note: Pins 2/3 are I2C (SDA/SCL) and should be avoided
#define XT_CLK_PIN   9   // Clock signal to PC
#define XT_DATA_PIN  10  // Data signal to PC

// Activity LED (onboard LED, pin 13 on Leonardo/Beetle)
#define ACTIVITY_LED_PIN LED_BUILTIN  // Pin 13
#define LED_BLINK_DURATION 30         // LED blink duration in milliseconds

// XT Protocol Timing (microseconds)
#define XT_CLK_HALF_PERIOD 40  // ~12.5 kHz clock (80us full period)
#define KEY_PRESS_DURATION 50  // Key press duration in milliseconds
#define ESC_TIMEOUT 100        // Escape sequence timeout in milliseconds

// Testing and Debug Configuration
// These should NOT be defined in source code for production builds.
// Instead, pass them at compile time using --build-property:
//
// Test mode (no GPIO, faster serial testing):
//   arduino-cli compile --fqbn arduino:avr:leonardo --build-property "compiler.cpp.extra_flags=-DARDUXT_TEST_MODE"
//
// Verbose mode (scancode debug output):
//   arduino-cli compile --fqbn arduino:avr:leonardo --build-property "compiler.cpp.extra_flags=-DVERBOSE_SCANCODES"
//
// Both modes:
//   arduino-cli compile --fqbn arduino:avr:leonardo --build-property "compiler.cpp.extra_flags=-DARDUXT_TEST_MODE -DVERBOSE_SCANCODES"
//
// Production build (no flags):
//   arduino-cli compile --fqbn arduino:avr:leonardo
//
// WARNING: Do not uncomment these in source - use compile-time flags instead!
// #define ARDUXT_TEST_MODE
// #define VERBOSE_SCANCODES

// Escape sequence parser state machine
enum EscapeState {
  STATE_NORMAL,  // Normal character input
  STATE_ESC,     // Received ESC, waiting for next char
  STATE_CSI,     // Received ESC[, collecting sequence
  STATE_SS3      // Received ESCO, collecting single-char sequence
};

// Escape sequence parser variables
EscapeState escState = STATE_NORMAL;
char escBuffer[8];
uint8_t escIndex = 0;
unsigned long escTimeout = 0;
bool escAltModifier = false;  // Track Alt from double-ESC (ESC ESC O X)

// Modifier flags from parsed escape sequences
bool parseCtrlMod = false;
bool parseAltMod = false;
bool parseShiftMod = false;

// LED activity indicator state
unsigned long ledOffTime = 0;  // Timestamp when LED should turn back on
bool ledIsBlinking = false;    // Track if LED is currently in blink state

// Modifier key scancodes
#define SC_LSHIFT  0x2A
#define SC_RSHIFT  0x36
#define SC_CTRL    0x1D
#define SC_ALT     0x38

void setup() {
#ifndef ARDUXT_TEST_MODE
  // Initialize GPIO pins for XT keyboard interface
  pinMode(XT_CLK_PIN, OUTPUT);
  pinMode(XT_DATA_PIN, OUTPUT);

  // XT keyboard idle state: both lines HIGH
  digitalWrite(XT_CLK_PIN, HIGH);
  digitalWrite(XT_DATA_PIN, HIGH);
#endif

  // Initialize activity LED (on by default, blinks on serial activity)
  pinMode(ACTIVITY_LED_PIN, OUTPUT);
  digitalWrite(ACTIVITY_LED_PIN, HIGH);  // LED on by default

  // Initialize USB Serial for receiving keystrokes
  Serial.begin(9600);

  // Wait for Serial connection (Leonardo requires this)
  while (!Serial) {
    ; // Wait for USB serial port to connect
  }

  Serial.println("arduXT - XT Keyboard Emulator");
#ifdef ARDUXT_TEST_MODE
  Serial.println("ARDUXT_TEST_MODE: GPIO operations disabled");
#endif
#ifdef VERBOSE_SCANCODES
  Serial.println("VERBOSE MODE: Scancode output enabled");
#endif
  Serial.println("Ready to receive keystrokes...");
}

void loop() {
  // Check if LED blink period is over (non-blocking)
  if (ledIsBlinking && millis() >= ledOffTime) {
    digitalWrite(ACTIVITY_LED_PIN, HIGH);  // Turn LED back on
    ledIsBlinking = false;
  }

  // Check for escape sequence timeout
  if (escState != STATE_NORMAL && millis() > escTimeout) {
    // Timeout handling
    if (escState == STATE_ESC && escIndex == 0) {
      // Standalone ESC key pressed
      Serial.println("KEY: ESC (standalone)");
      sendKey(0x01);  // ESC scancode
    } else {
      Serial.println("ERROR: Escape sequence timeout");
    }
    // Reset state machine
    escState = STATE_NORMAL;
    escIndex = 0;
    escAltModifier = false;
  }

  // Check for incoming serial data
  if (Serial.available() > 0) {
    char incomingChar = Serial.read();

    // Blink LED to indicate serial activity (non-blocking)
    digitalWrite(ACTIVITY_LED_PIN, LOW);  // Turn LED off
    ledOffTime = millis() + LED_BLINK_DURATION;
    ledIsBlinking = true;

    // Escape sequence state machine
    switch (escState) {
      case STATE_NORMAL:
        if (incomingChar == 27) {  // ESC character
          escState = STATE_ESC;
          escIndex = 0;
          escTimeout = millis() + ESC_TIMEOUT;
          Serial.println("ESC received");
        } else {
          // Normal character - process it
          Serial.print("INPUT: 0x");
          Serial.print((uint8_t)incomingChar, HEX);
          if (incomingChar >= 32 && incomingChar <= 126) {
            Serial.print(" (");
            Serial.print(incomingChar);
            Serial.print(")");
          }
          Serial.println();

          // Check for Ctrl sequences (Ctrl+A through Ctrl+Z = 0x01-0x1A)
          if (incomingChar >= 0x01 && incomingChar <= 0x1A) {
            // Ctrl+letter detected
            char letter = incomingChar + 'a' - 1;  // Convert to lowercase letter
            uint8_t baseCode = charToXTScancode(letter);
            if (baseCode != 0) {
              Serial.print("KEY: Ctrl+");
              Serial.println(letter);
              // Send Ctrl+key sequence
              sendXTScancode(SC_CTRL);            // Ctrl make
              sendXTScancode(baseCode);           // Key make
              delay(KEY_PRESS_DURATION);
              sendXTScancode(baseCode | 0x80);    // Key break
              sendXTScancode(SC_CTRL | 0x80);     // Ctrl break
            }
          }
          // Check if this character requires shift
          else if (isShiftedChar(incomingChar)) {
            Serial.print("KEY: ");
            Serial.print(incomingChar);
            Serial.println(" (shifted)");
            uint8_t baseCode = getBaseKey(incomingChar);
            if (baseCode != 0) {
              sendKeyWithShift(baseCode);
            }
          } else {
            // Regular character without shift
            uint8_t scancode = charToXTScancode(incomingChar);
            if (scancode != 0) {
              Serial.print("KEY: ");
              if (incomingChar >= 32 && incomingChar <= 126) {
                Serial.println(incomingChar);
              } else {
                Serial.print("0x");
                Serial.println((uint8_t)incomingChar, HEX);
              }
              sendKey(scancode);
            }
          }
        }
        break;

      case STATE_ESC:
        if (incomingChar == '[') {
          escState = STATE_CSI;
          escTimeout = millis() + ESC_TIMEOUT;
          Serial.println("CSI sequence");
        } else if (incomingChar == 'O') {
          escState = STATE_SS3;
          escTimeout = millis() + ESC_TIMEOUT;
          Serial.println("SS3 sequence");
        } else if (incomingChar == 27) {
          // Double ESC - this is Alt+Fn sequence (ESC ESC O P/Q/R/S)
          // Mark that we're in Alt mode and continue parsing
          escAltModifier = true;
          Serial.println("Double ESC (Alt modifier)");
          // Stay in STATE_ESC to process the next character
        } else if (incomingChar >= 0x01 && incomingChar <= 0x1A) {
          // Ctrl code after ESC = Ctrl+Alt+key sequence
          char letter = incomingChar + 'a' - 1;  // Convert to lowercase letter
          uint8_t baseCode = charToXTScancode(letter);
          if (baseCode != 0) {
            Serial.print("KEY: Ctrl+Alt+");
            Serial.println(letter);
            // Send Ctrl+Alt+key sequence
            sendXTScancode(SC_CTRL);            // Ctrl make
            sendXTScancode(SC_ALT);             // Alt make
            sendXTScancode(baseCode);           // Key make
            delay(KEY_PRESS_DURATION);
            sendXTScancode(baseCode | 0x80);    // Key break
            sendXTScancode(SC_ALT | 0x80);      // Alt break
            sendXTScancode(SC_CTRL | 0x80);     // Ctrl break
          }
          // Reset state
          escState = STATE_NORMAL;
          escIndex = 0;
          escAltModifier = false;
        } else if (incomingChar >= 32 && incomingChar <= 126) {
          // Printable character after ESC = Alt+key sequence
          Serial.print("KEY: Alt+");
          Serial.println(incomingChar);

          // Get the base scancode for this character
          uint8_t baseCode = 0;
          if (isShiftedChar(incomingChar)) {
            baseCode = getBaseKey(incomingChar);
            if (baseCode != 0) {
              // Alt+Shift+key
              sendXTScancode(SC_ALT);             // Alt make
              sendXTScancode(SC_LSHIFT);          // Shift make
              sendXTScancode(baseCode);           // Key make
              delay(KEY_PRESS_DURATION);
              sendXTScancode(baseCode | 0x80);    // Key break
              sendXTScancode(SC_LSHIFT | 0x80);   // Shift break
              sendXTScancode(SC_ALT | 0x80);      // Alt break
            }
          } else {
            baseCode = charToXTScancode(incomingChar);
            if (baseCode != 0) {
              // Alt+key
              sendXTScancode(SC_ALT);             // Alt make
              sendXTScancode(baseCode);           // Key make
              delay(KEY_PRESS_DURATION);
              sendXTScancode(baseCode | 0x80);    // Key break
              sendXTScancode(SC_ALT | 0x80);      // Alt break
            }
          }

          // Reset state
          escState = STATE_NORMAL;
          escIndex = 0;
          escAltModifier = false;
        } else {
          // Invalid sequence, reset
          escState = STATE_NORMAL;
          escIndex = 0;
          escAltModifier = false;
          Serial.println("ERROR: Invalid ESC sequence");
        }
        break;

      case STATE_CSI:
      case STATE_SS3:
        // Collect characters into buffer
        if (escIndex < 7) {
          escBuffer[escIndex++] = incomingChar;
          escTimeout = millis() + ESC_TIMEOUT;

          // Check for sequence terminators
          bool isComplete = false;
          if (escState == STATE_CSI) {
            // CSI sequences end with a letter or ~
            isComplete = (incomingChar >= 'A' && incomingChar <= 'Z') ||
                        (incomingChar >= 'a' && incomingChar <= 'z') ||
                        (incomingChar == '~');
          } else {  // STATE_SS3
            // SS3 sequences are single character
            isComplete = true;
          }

          if (isComplete) {
            // Parse and send the sequence
            uint8_t scancode = parseEscapeSequence();
            if (scancode != 0) {
              Serial.print("KEY: Escape sequence -> 0x");
              Serial.print(scancode, HEX);

              // Check for Alt from double-ESC
              bool hasAlt = parseAltMod || escAltModifier;
              bool hasCtrl = parseCtrlMod;
              bool hasShift = parseShiftMod;

              // Print modifier info
              if (hasCtrl || hasAlt || hasShift) {
                Serial.print(" (");
                if (hasCtrl) Serial.print("Ctrl+");
                if (hasAlt) Serial.print("Alt+");
                if (hasShift) Serial.print("Shift+");
                Serial.print(")");
              }
              Serial.println();

              // Send with modifiers
              if (hasCtrl && hasAlt) {
                // Ctrl+Alt+Key
                sendXTScancode(SC_CTRL);
                sendXTScancode(SC_ALT);
                sendXTScancode(scancode);
                delay(KEY_PRESS_DURATION);
                sendXTScancode(scancode | 0x80);
                sendXTScancode(SC_ALT | 0x80);
                sendXTScancode(SC_CTRL | 0x80);
              } else if (hasCtrl) {
                // Ctrl+Key
                sendXTScancode(SC_CTRL);
                sendXTScancode(scancode);
                delay(KEY_PRESS_DURATION);
                sendXTScancode(scancode | 0x80);
                sendXTScancode(SC_CTRL | 0x80);
              } else if (hasAlt) {
                // Alt+Key
                sendXTScancode(SC_ALT);
                sendXTScancode(scancode);
                delay(KEY_PRESS_DURATION);
                sendXTScancode(scancode | 0x80);
                sendXTScancode(SC_ALT | 0x80);
              } else {
                // No modifiers
                sendKey(scancode);
              }
            } else {
              Serial.println("ERROR: Unknown escape sequence");
            }
            // Reset state machine
            escState = STATE_NORMAL;
            escIndex = 0;
            escAltModifier = false;  // Reset Alt flag
          }
        } else {
          // Buffer overflow, reset
          escState = STATE_NORMAL;
          escIndex = 0;
          escAltModifier = false;
          Serial.println("ERROR: Sequence buffer overflow");
        }
        break;
    }
  }
}

/*
 * Send a single byte using XT keyboard protocol
 * XT format: Start bit (1) + 8 data bits (LSB first)
 * Note: No stop bit in XT protocol
 */
void sendXTScancode(uint8_t scancode) {
#ifdef VERBOSE_SCANCODES
  Serial.print("SCANCODE: 0x");
  Serial.print(scancode, HEX);
  Serial.print(" (");
  Serial.print((scancode & 0x80) ? "BREAK" : "MAKE");
  Serial.println(")");
#endif

#ifndef ARDUXT_TEST_MODE
  // Start bit (DATA high)
  digitalWrite(XT_DATA_PIN, HIGH);
  xtClockPulse();

  // Send 8 data bits (LSB first)
  for (int i = 0; i < 8; i++) {
    digitalWrite(XT_DATA_PIN, (scancode >> i) & 0x01);
    xtClockPulse();
  }

  // Return to idle state
  digitalWrite(XT_CLK_PIN, HIGH);
  digitalWrite(XT_DATA_PIN, HIGH);
#endif
}

/*
 * Generate one clock pulse for XT protocol
 * Clock idles HIGH, pulses LOW
 */
void xtClockPulse() {
#ifndef ARDUXT_TEST_MODE
  delayMicroseconds(XT_CLK_HALF_PERIOD);
  digitalWrite(XT_CLK_PIN, LOW);
  delayMicroseconds(XT_CLK_HALF_PERIOD);
  digitalWrite(XT_CLK_PIN, HIGH);
#endif
}

/*
 * Send a key with automatic shift modifier wrapping
 * Used for shifted characters like !@#$%^&*()
 */
void sendKeyWithShift(uint8_t baseCode) {
  sendXTScancode(SC_LSHIFT);           // Shift make
  sendXTScancode(baseCode);            // Key make
  delay(KEY_PRESS_DURATION);           // Key press duration
  sendXTScancode(baseCode | 0x80);     // Key break
  sendXTScancode(SC_LSHIFT | 0x80);    // Shift break
}

/*
 * Send a toggle key (Caps Lock, Num Lock, Scroll Lock)
 * Sends make then break with delay
 */
void sendToggleKey(uint8_t scancode) {
  sendXTScancode(scancode);            // Make
  delay(KEY_PRESS_DURATION);           // Key press duration
  sendXTScancode(scancode | 0x80);     // Break
}

/*
 * Send a regular key (make, delay, break)
 */
void sendKey(uint8_t scancode) {
  sendXTScancode(scancode);            // Make
  delay(KEY_PRESS_DURATION);           // Key press duration
  sendXTScancode(scancode | 0x80);     // Break
}

/*
 * Check if a character requires shift modifier
 */
bool isShiftedChar(char c) {
  return (c >= 'A' && c <= 'Z') ||
         c == '!' || c == '@' || c == '#' || c == '$' || c == '%' ||
         c == '^' || c == '&' || c == '*' || c == '(' || c == ')' ||
         c == '_' || c == '+' || c == '{' || c == '}' || c == '|' ||
         c == ':' || c == '"' || c == '<' || c == '>' || c == '?' || c == '~';
}

/*
 * Get base key scancode for a character (without shift)
 * For shifted characters, returns the base key scancode
 */
uint8_t getBaseKey(char c) {
  // Shifted number row characters -> base number keys
  switch (c) {
    case '!': return 0x02;  // 1
    case '@': return 0x03;  // 2
    case '#': return 0x04;  // 3
    case '$': return 0x05;  // 4
    case '%': return 0x06;  // 5
    case '^': return 0x07;  // 6
    case '&': return 0x08;  // 7
    case '*': return 0x09;  // 8
    case '(': return 0x0A;  // 9
    case ')': return 0x0B;  // 0
    case '_': return 0x0C;  // -
    case '+': return 0x0D;  // =
    case '{': return 0x1A;  // [
    case '}': return 0x1B;  // ]
    case '|': return 0x2B;  // backslash
    case ':': return 0x27;  // ;
    case '"': return 0x28;  // '
    case '<': return 0x33;  // ,
    case '>': return 0x34;  // .
    case '?': return 0x35;  // /
    case '~': return 0x29;  // `
  }

  // Uppercase letters -> lowercase scancode
  if (c >= 'A' && c <= 'Z') {
    c = c + 32;  // Convert to lowercase
  }

  return charToXTScancode(c);
}

/*
 * Convert ASCII character to XT scancode (base key without modifiers)
 * Returns 0 if character is not mapped
 */
uint8_t charToXTScancode(char c) {
  switch (c) {
    // Lowercase letters (a-z)
    case 'a': return 0x1E;
    case 'b': return 0x30;
    case 'c': return 0x2E;
    case 'd': return 0x20;
    case 'e': return 0x12;
    case 'f': return 0x21;
    case 'g': return 0x22;
    case 'h': return 0x23;
    case 'i': return 0x17;
    case 'j': return 0x24;
    case 'k': return 0x25;
    case 'l': return 0x26;
    case 'm': return 0x32;
    case 'n': return 0x31;
    case 'o': return 0x18;
    case 'p': return 0x19;
    case 'q': return 0x10;
    case 'r': return 0x13;
    case 's': return 0x1F;
    case 't': return 0x14;
    case 'u': return 0x16;
    case 'v': return 0x2F;
    case 'w': return 0x11;
    case 'x': return 0x2D;
    case 'y': return 0x15;
    case 'z': return 0x2C;

    // Numbers (0-9)
    case '0': return 0x0B;
    case '1': return 0x02;
    case '2': return 0x03;
    case '3': return 0x04;
    case '4': return 0x05;
    case '5': return 0x06;
    case '6': return 0x07;
    case '7': return 0x08;
    case '8': return 0x09;
    case '9': return 0x0A;

    // Special keys
    case ' ': return 0x39;  // Space
    case '\n':
    case '\r': return 0x1C; // Enter
    case '\b': return 0x0E; // Backspace
    case '\t': return 0x0F; // Tab
    case 27:   return 0x01; // Escape

    // Unshifted punctuation
    case '-': return 0x0C;  // Minus
    case '=': return 0x0D;  // Equals
    case '[': return 0x1A;  // Left bracket
    case ']': return 0x1B;  // Right bracket
    case ';': return 0x27;  // Semicolon
    case '\'': return 0x28; // Apostrophe
    case '`': return 0x29;  // Grave accent
    case '\\': return 0x2B; // Backslash
    case ',': return 0x33;  // Comma
    case '.': return 0x34;  // Period
    case '/': return 0x35;  // Slash

    default: return 0;      // Unsupported character
  }
}

/*
 * Parse VT100 escape sequence and return XT scancode with modifiers
 * Returns scancode, or 0 if not recognized
 * Sets global variables for modifier state (Ctrl, Alt, Shift)
 */
uint8_t parseEscapeSequence() {
  // Reset modifier flags
  parseCtrlMod = false;
  parseAltMod = false;
  parseShiftMod = false;

  // Null-terminate the buffer
  escBuffer[escIndex] = '\0';

  // CSI sequences (ESC[...)
  if (escState == STATE_CSI) {
    // Check for modifier parameter sequences
    // Format: ESC[n;mX or ESC[n;m~
    // where n = key code, m = modifier (3=Alt, 5=Ctrl, 7=Ctrl+Alt)
    int num = 0;
    int modifier = 0;
    bool hasModifier = false;
    int i = 0;

    // Parse first number
    while (i < escIndex && escBuffer[i] >= '0' && escBuffer[i] <= '9') {
      num = num * 10 + (escBuffer[i] - '0');
      i++;
    }

    // Check for semicolon (modifier separator)
    if (i < escIndex && escBuffer[i] == ';') {
      i++;
      hasModifier = true;
      // Parse modifier number
      while (i < escIndex && escBuffer[i] >= '0' && escBuffer[i] <= '9') {
        modifier = modifier * 10 + (escBuffer[i] - '0');
        i++;
      }
    }

    // Set modifier flags based on modifier value
    if (hasModifier) {
      // Standard xterm modifiers: 2=Shift, 3=Alt, 5=Ctrl, 7=Ctrl+Alt
      if (modifier == 3 || modifier == 7) parseAltMod = true;
      if (modifier == 5 || modifier == 7) parseCtrlMod = true;
      if (modifier == 2) parseShiftMod = true;
    }

    // Arrow keys: ESC[A, ESC[B, ESC[C, ESC[D (no modifiers)
    if (escIndex == 1 && !hasModifier) {
      switch (escBuffer[0]) {
        case 'A': return 0x48;  // Up arrow
        case 'B': return 0x50;  // Down arrow
        case 'C': return 0x4D;  // Right arrow
        case 'D': return 0x4B;  // Left arrow
        case 'H': return 0x47;  // Home (alternate)
        case 'F': return 0x4F;  // End (alternate)
      }
    }

    // CSI sequences with modifiers: ESC[1;5P (Ctrl+F1)
    if (hasModifier && i < escIndex) {
      char terminator = escBuffer[i];
      switch (terminator) {
        case 'P': return 0x3B;  // F1
        case 'Q': return 0x3C;  // F2
        case 'R': return 0x3D;  // F3
        case 'S': return 0x3E;  // F4
        case 'A': return 0x48;  // Up arrow
        case 'B': return 0x50;  // Down arrow
        case 'C': return 0x4D;  // Right arrow
        case 'D': return 0x4B;  // Left arrow
      }
    }

    // Extended keys: ESC[n~ or ESC[n;m~
    if (escIndex >= 2 && escBuffer[escIndex-1] == '~') {
      Serial.print("CSI num: ");
      Serial.print(num);
      if (hasModifier) {
        Serial.print(" modifier: ");
        Serial.print(modifier);
      }
      Serial.println();

      switch (num) {
        case 1: return 0x47;   // Home
        case 2: return 0x52;   // Insert
        case 3: return 0x53;   // Delete
        case 4: return 0x4F;   // End
        case 5: return 0x49;   // Page Up
        case 6: return 0x51;   // Page Down
        case 15: return 0x3F;  // F5
        case 17: return 0x40;  // F6
        case 18: return 0x41;  // F7
        case 19: return 0x42;  // F8
        case 20: return 0x43;  // F9
        case 21: return 0x44;  // F10
        case 23: return 0x57;  // F11 (extended, not standard XT)
        case 24: return 0x58;  // F12 (extended, not standard XT)
      }
    }
  }

  // SS3 sequences (ESCO...)
  if (escState == STATE_SS3) {
    if (escIndex == 1) {
      switch (escBuffer[0]) {
        case 'P': return 0x3B;  // F1
        case 'Q': return 0x3C;  // F2
        case 'R': return 0x3D;  // F3
        case 'S': return 0x3E;  // F4
        // Arrow keys (some terminals send these)
        case 'A': return 0x48;  // Up arrow
        case 'B': return 0x50;  // Down arrow
        case 'C': return 0x4D;  // Right arrow
        case 'D': return 0x4B;  // Left arrow
        case 'H': return 0x47;  // Home
        case 'F': return 0x4F;  // End
      }
    }
  }

  return 0;  // Unrecognized sequence
}
