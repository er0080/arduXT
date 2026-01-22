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

// XT Protocol Timing (microseconds)
#define XT_CLK_HALF_PERIOD 40  // ~12.5 kHz clock (80us full period)

void setup() {
  // Initialize GPIO pins for XT keyboard interface
  pinMode(XT_CLK_PIN, OUTPUT);
  pinMode(XT_DATA_PIN, OUTPUT);

  // XT keyboard idle state: both lines HIGH
  digitalWrite(XT_CLK_PIN, HIGH);
  digitalWrite(XT_DATA_PIN, HIGH);

  // Initialize USB Serial for receiving keystrokes
  Serial.begin(9600);

  // Wait for Serial connection (Leonardo requires this)
  while (!Serial) {
    ; // Wait for USB serial port to connect
  }

  Serial.println("arduXT - XT Keyboard Emulator");
  Serial.println("Ready to receive keystrokes...");
}

void loop() {
  // Check for incoming serial data
  if (Serial.available() > 0) {
    char incomingChar = Serial.read();

    // Echo back for debugging
    Serial.print("Received: ");
    Serial.println(incomingChar);

    // Convert to XT scancode and send
    uint8_t scancode = charToXTScancode(incomingChar);
    if (scancode != 0) {
      sendXTScancode(scancode);        // Send make code
      delay(50);                       // Key press duration
      sendXTScancode(scancode | 0x80); // Send break code (make + 0x80)
    }
  }
}

/*
 * Send a single byte using XT keyboard protocol
 * XT format: Start bit (1) + 8 data bits (LSB first)
 * Note: No stop bit in XT protocol
 */
void sendXTScancode(uint8_t scancode) {
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
}

/*
 * Generate one clock pulse for XT protocol
 * Clock idles HIGH, pulses LOW
 */
void xtClockPulse() {
  delayMicroseconds(XT_CLK_HALF_PERIOD);
  digitalWrite(XT_CLK_PIN, LOW);
  delayMicroseconds(XT_CLK_HALF_PERIOD);
  digitalWrite(XT_CLK_PIN, HIGH);
}

/*
 * Convert ASCII character to XT scancode
 * Returns 0 if character is not mapped
 */
uint8_t charToXTScancode(char c) {
  // Convert to uppercase for simplicity
  if (c >= 'a' && c <= 'z') {
    c = c - 32;
  }

  // Basic ASCII to XT scancode mapping
  switch (c) {
    // Letters (A-Z)
    case 'A': return 0x1E;
    case 'B': return 0x30;
    case 'C': return 0x2E;
    case 'D': return 0x20;
    case 'E': return 0x12;
    case 'F': return 0x21;
    case 'G': return 0x22;
    case 'H': return 0x23;
    case 'I': return 0x17;
    case 'J': return 0x24;
    case 'K': return 0x25;
    case 'L': return 0x26;
    case 'M': return 0x32;
    case 'N': return 0x31;
    case 'O': return 0x18;
    case 'P': return 0x19;
    case 'Q': return 0x10;
    case 'R': return 0x13;
    case 'S': return 0x1F;
    case 'T': return 0x14;
    case 'U': return 0x16;
    case 'V': return 0x2F;
    case 'W': return 0x11;
    case 'X': return 0x2D;
    case 'Y': return 0x15;
    case 'Z': return 0x2C;

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

    // Punctuation
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
