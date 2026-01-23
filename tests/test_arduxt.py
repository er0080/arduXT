#!/usr/bin/env python3
"""
Hardware-in-the-Loop Test Suite for arduXT
Requires: pyserial (uv pip install pyserial)
Usage: python3 test_arduxt.py /dev/cu.usbmodem14101
"""

import serial
import time
import sys
import argparse
from typing import List, Tuple, Optional


class ArduXTTester:
    """Test harness for arduXT keyboard emulator"""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        """Initialize serial connection to arduXT device"""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.test_count = 0
        self.pass_count = 0
        self.fail_count = 0

    def connect(self):
        """Open serial connection and wait for device ready"""
        print(f"Connecting to {self.port} at {self.baudrate} baud...")
        self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(2)  # Wait for Arduino reset after serial connection

        # Read and display startup message
        startup = self.read_lines(timeout=0.5)
        for line in startup:
            print(f"  Device: {line}")

        if any("arduXT" in line for line in startup):
            print("✓ Device connected and ready\n")
            return True
        else:
            print("✗ Device did not send expected startup message\n")
            return False

    def disconnect(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()

    def send_char(self, char: str):
        """Send a single character to the device"""
        self.serial.write(char.encode('utf-8'))
        self.serial.flush()

    def send_bytes(self, data: bytes):
        """Send raw bytes to the device"""
        self.serial.write(data)
        self.serial.flush()

    def send_escape_sequence(self, sequence: str):
        """Send an escape sequence (ESC + sequence)"""
        self.serial.write(b'\x1b' + sequence.encode('utf-8'))
        self.serial.flush()

    def read_lines(self, timeout: float = 0.2, count: int = None) -> List[str]:
        """Read lines from serial until timeout or count reached"""
        lines = []
        self.serial.timeout = timeout
        start_time = time.time()

        while True:
            if count and len(lines) >= count:
                break
            if time.time() - start_time > timeout * 2:
                break

            try:
                line = self.serial.readline().decode('utf-8').strip()
                if line:
                    lines.append(line)
                    start_time = time.time()  # Reset timeout on new data
                elif time.time() - start_time > timeout:
                    break
            except UnicodeDecodeError:
                continue

        self.serial.timeout = self.timeout
        return lines

    def expect_output(self, expected: List[str], timeout: float = 0.3) -> Tuple[bool, List[str]]:
        """
        Read output and check if it contains expected strings
        Returns (success, actual_output)
        """
        actual = self.read_lines(timeout=timeout)

        # Check if all expected strings appear in output (in order)
        actual_str = "\n".join(actual)
        for exp in expected:
            if exp not in actual_str:
                return False, actual

        return True, actual

    def test(self, name: str, input_data, expected_output: List[str],
             use_raw_bytes: bool = False, delay: float = 0.1):
        """
        Run a single test case

        Args:
            name: Test description
            input_data: Character, string, or bytes to send
            expected_output: List of strings that should appear in output
            use_raw_bytes: If True, send input_data as raw bytes
            delay: Time to wait before reading response
        """
        self.test_count += 1
        print(f"Test {self.test_count}: {name}")

        # Send input
        if use_raw_bytes:
            self.send_bytes(input_data)
        elif isinstance(input_data, str):
            for char in input_data:
                self.send_char(char)
                time.sleep(0.01)  # Small delay between characters
        else:
            self.send_char(input_data)

        time.sleep(delay)

        # Check output
        success, actual = self.expect_output(expected_output)

        if success:
            self.pass_count += 1
            print(f"  ✓ PASS")
            if actual:
                for line in actual:
                    print(f"    {line}")
        else:
            self.fail_count += 1
            print(f"  ✗ FAIL")
            print(f"  Expected output containing: {expected_output}")
            print(f"  Actual output:")
            for line in actual:
                print(f"    {line}")

        print()
        return success

    def print_summary(self):
        """Print test results summary"""
        print("=" * 60)
        print(f"Test Summary: {self.test_count} tests")
        print(f"  ✓ Passed: {self.pass_count}")
        print(f"  ✗ Failed: {self.fail_count}")
        print(f"  Success rate: {100 * self.pass_count / self.test_count:.1f}%")
        print("=" * 60)


def run_test_suite(tester: ArduXTTester):
    """Execute comprehensive test suite"""

    print("=" * 60)
    print("HARDWARE-IN-THE-LOOP TEST SUITE")
    print("=" * 60)
    print()

    # ===================================================================
    # Basic Character Tests
    # ===================================================================
    print("--- Basic Character Tests ---\n")

    tester.test("Lowercase letter 'a'", 'a', ["INPUT: 0x61", "KEY: a"])
    tester.test("Lowercase letter 'z'", 'z', ["INPUT: 0x7A", "KEY: z"])
    tester.test("Uppercase letter 'A'", 'A', ["INPUT: 0x41", "KEY: A (shifted)"])
    tester.test("Digit '0'", '0', ["INPUT: 0x30", "KEY: 0"])
    tester.test("Digit '9'", '9', ["INPUT: 0x39", "KEY: 9"])
    tester.test("Space character", ' ', ["INPUT: 0x20"])

    # ===================================================================
    # Punctuation Tests
    # ===================================================================
    print("--- Punctuation Tests ---\n")

    tester.test("Minus '-'", '-', ["INPUT: 0x2D", "KEY: -"])
    tester.test("Equals '='", '=', ["INPUT: 0x3D", "KEY: ="])
    tester.test("Left bracket '['", '[', ["INPUT: 0x5B", "KEY: ["])
    tester.test("Semicolon ';'", ';', ["INPUT: 0x3B", "KEY: ;"])
    tester.test("Comma ','", ',', ["INPUT: 0x2C", "KEY: ,"])
    tester.test("Period '.'", '.', ["INPUT: 0x2E", "KEY: ."])
    tester.test("Slash '/'", '/', ["INPUT: 0x2F", "KEY: /"])

    # ===================================================================
    # Shifted Character Tests
    # ===================================================================
    print("--- Shifted Character Tests ---\n")

    tester.test("Exclamation '!'", '!', ["INPUT: 0x21", "KEY: ! (shifted)"])
    tester.test("At sign '@'", '@', ["INPUT: 0x40", "KEY: @ (shifted)"])
    tester.test("Hash '#'", '#', ["INPUT: 0x23", "KEY: # (shifted)"])
    tester.test("Dollar '$'", '$', ["INPUT: 0x24", "KEY: $ (shifted)"])
    tester.test("Percent '%'", '%', ["INPUT: 0x25", "KEY: % (shifted)"])
    tester.test("Caret '^'", '^', ["INPUT: 0x5E", "KEY: ^ (shifted)"])
    tester.test("Ampersand '&'", '&', ["INPUT: 0x26", "KEY: & (shifted)"])
    tester.test("Asterisk '*'", '*', ["INPUT: 0x2A", "KEY: * (shifted)"])
    tester.test("Left paren '('", '(', ["INPUT: 0x28", "KEY: ( (shifted)"])
    tester.test("Right paren ')'", ')', ["INPUT: 0x29", "KEY: ) (shifted)"])
    tester.test("Underscore '_'", '_', ["INPUT: 0x5F", "KEY: _ (shifted)"])
    tester.test("Plus '+'", '+', ["INPUT: 0x2B", "KEY: + (shifted)"])

    # ===================================================================
    # Control Character Tests
    # ===================================================================
    print("--- Control Character Tests ---\n")

    # Ctrl+A = 0x01, Ctrl+Z = 0x1A
    tester.test("Ctrl+A", b'\x01', ["INPUT: 0x1", "KEY: Ctrl+a"], use_raw_bytes=True)
    tester.test("Ctrl+C", b'\x03', ["INPUT: 0x3", "KEY: Ctrl+c"], use_raw_bytes=True)
    tester.test("Ctrl+D", b'\x04', ["INPUT: 0x4", "KEY: Ctrl+d"], use_raw_bytes=True)
    tester.test("Ctrl+Z", b'\x1A', ["INPUT: 0x1A", "KEY: Ctrl+z"], use_raw_bytes=True)

    # Special keys
    tester.test("Tab character", '\t', ["INPUT: 0x9"])
    tester.test("Newline", '\n', ["INPUT: 0xA"])
    tester.test("Carriage return", '\r', ["INPUT: 0xD"])
    tester.test("Backspace", '\b', ["INPUT: 0x8"])

    # ===================================================================
    # Escape Sequence Tests - Arrow Keys
    # ===================================================================
    print("--- Arrow Key Tests (ESC[X) ---\n")

    tester.test("Up arrow", b'\x1b[A', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x48"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Down arrow", b'\x1b[B', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x50"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Right arrow", b'\x1b[C', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x4D"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Left arrow", b'\x1b[D', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x4B"],
                use_raw_bytes=True, delay=0.2)

    # ===================================================================
    # Escape Sequence Tests - Function Keys
    # ===================================================================
    print("--- Function Key Tests (ESCOX) ---\n")

    tester.test("F1 key", b'\x1bOP', ["ESC received", "SS3 sequence", "KEY: Escape sequence -> 0x3B"],
                use_raw_bytes=True, delay=0.2)
    tester.test("F2 key", b'\x1bOQ', ["ESC received", "SS3 sequence", "KEY: Escape sequence -> 0x3C"],
                use_raw_bytes=True, delay=0.2)
    tester.test("F3 key", b'\x1bOR', ["ESC received", "SS3 sequence", "KEY: Escape sequence -> 0x3D"],
                use_raw_bytes=True, delay=0.2)
    tester.test("F4 key", b'\x1bOS', ["ESC received", "SS3 sequence", "KEY: Escape sequence -> 0x3E"],
                use_raw_bytes=True, delay=0.2)

    # ===================================================================
    # Escape Sequence Tests - Extended Keys (ESC[n~)
    # ===================================================================
    print("--- Extended Key Tests (ESC[n~) ---\n")

    tester.test("Home key", b'\x1b[1~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x47"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Insert key", b'\x1b[2~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x52"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Delete key", b'\x1b[3~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x53"],
                use_raw_bytes=True, delay=0.2)
    tester.test("End key", b'\x1b[4~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x4F"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Page Up key", b'\x1b[5~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x49"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Page Down key", b'\x1b[6~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x51"],
                use_raw_bytes=True, delay=0.2)

    tester.test("F5 key", b'\x1b[15~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x3F"],
                use_raw_bytes=True, delay=0.2)
    tester.test("F6 key", b'\x1b[17~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x40"],
                use_raw_bytes=True, delay=0.2)
    tester.test("F7 key", b'\x1b[18~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x41"],
                use_raw_bytes=True, delay=0.2)
    tester.test("F8 key", b'\x1b[19~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x42"],
                use_raw_bytes=True, delay=0.2)
    tester.test("F9 key", b'\x1b[20~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x43"],
                use_raw_bytes=True, delay=0.2)
    tester.test("F10 key", b'\x1b[21~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x44"],
                use_raw_bytes=True, delay=0.2)
    tester.test("F11 key", b'\x1b[23~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x57"],
                use_raw_bytes=True, delay=0.2)
    tester.test("F12 key", b'\x1b[24~', ["ESC received", "CSI sequence", "KEY: Escape sequence -> 0x58"],
                use_raw_bytes=True, delay=0.2)

    # ===================================================================
    # Alt+Function Key Tests
    # ===================================================================
    print("--- Alt+Function Key Tests ---\n")

    # Alt+F1 through Alt+F4 (SS3 sequences)
    tester.test("Alt+F1", b'\x1b\x1bOP', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+F2", b'\x1b\x1bOQ', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+F3", b'\x1b\x1bOR', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+F4", b'\x1b\x1bOS', ["ESC received"],
                use_raw_bytes=True, delay=0.2)

    # Alt+F5 through Alt+F12 (CSI sequences with modifier)
    tester.test("Alt+F5", b'\x1b[15;3~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+F6", b'\x1b[17;3~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+F7", b'\x1b[18;3~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+F8", b'\x1b[19;3~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+F9", b'\x1b[20;3~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+F10", b'\x1b[21;3~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+F11", b'\x1b[23;3~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+F12", b'\x1b[24;3~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)

    # ===================================================================
    # Ctrl+Function Key Tests
    # ===================================================================
    print("--- Ctrl+Function Key Tests ---\n")

    # Ctrl+F1 through Ctrl+F4 (CSI sequences with modifier)
    tester.test("Ctrl+F1", b'\x1b[1;5P', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+F2", b'\x1b[1;5Q', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+F3", b'\x1b[1;5R', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+F4", b'\x1b[1;5S', ["ESC received"],
                use_raw_bytes=True, delay=0.2)

    # Ctrl+F5 through Ctrl+F12 (CSI sequences with modifier)
    tester.test("Ctrl+F5", b'\x1b[15;5~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+F6", b'\x1b[17;5~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+F7", b'\x1b[18;5~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+F8", b'\x1b[19;5~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+F9", b'\x1b[20;5~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+F10", b'\x1b[21;5~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+F11", b'\x1b[23;5~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+F12", b'\x1b[24;5~', ["ESC received"],
                use_raw_bytes=True, delay=0.2)

    # ===================================================================
    # Ctrl+Alt Combination Tests
    # ===================================================================
    print("--- Ctrl+Alt Combination Tests ---\n")

    # Ctrl+Alt+letter combinations (ESC followed by Ctrl+letter)
    tester.test("Ctrl+Alt+A", b'\x1b\x01', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+Alt+C", b'\x1b\x03', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+Alt+D", b'\x1b\x04', ["ESC received"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Ctrl+Alt+Z", b'\x1b\x1A', ["ESC received"],
                use_raw_bytes=True, delay=0.2)

    # ===================================================================
    # Shift+Ctrl Combination Tests
    # ===================================================================
    print("--- Shift+Ctrl Combination Tests ---\n")

    # Shift+Ctrl+letter combinations (typically same as Ctrl+letter)
    tester.test("Shift+Ctrl+A", b'\x01', ["INPUT: 0x1", "KEY: Ctrl+a"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Shift+Ctrl+C", b'\x03', ["INPUT: 0x3", "KEY: Ctrl+c"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Shift+Ctrl+Z", b'\x1A', ["INPUT: 0x1A", "KEY: Ctrl+z"],
                use_raw_bytes=True, delay=0.2)

    # ===================================================================
    # Shift+Alt Combination Tests
    # ===================================================================
    print("--- Shift+Alt Combination Tests ---\n")

    # Shift+Alt+letter combinations (ESC followed by uppercase letter)
    tester.test("Shift+Alt+A", b'\x1bA', ["ESC received", "KEY: Alt+A"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Shift+Alt+Z", b'\x1bZ', ["ESC received", "KEY: Alt+Z"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Shift+Alt+1 (!)", b'\x1b!', ["ESC received", "KEY: Alt+!"],
                use_raw_bytes=True, delay=0.2)

    # ===================================================================
    # Alt Key Tests (Basic)
    # ===================================================================
    print("--- Alt Key Tests (ESC+char) ---\n")

    tester.test("Alt+a", b'\x1ba', ["ESC received", "KEY: Alt+a"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+1", b'\x1b1', ["ESC received", "KEY: Alt+1"],
                use_raw_bytes=True, delay=0.2)
    tester.test("Alt+A (uppercase)", b'\x1bA', ["ESC received", "KEY: Alt+A"],
                use_raw_bytes=True, delay=0.2)

    # ===================================================================
    # Standalone ESC Key Test
    # ===================================================================
    print("--- Standalone ESC Key Test ---\n")

    tester.test("Standalone ESC key", b'\x1b', ["ESC received", "KEY: ESC (standalone)"],
                use_raw_bytes=True, delay=0.15)

    # ===================================================================
    # String Tests
    # ===================================================================
    print("--- String/Sentence Tests ---\n")

    tester.test("Word 'hello'", "hello", ["INPUT: 0x68", "INPUT: 0x65", "INPUT: 0x6C", "INPUT: 0x6F"])
    tester.test("Sentence 'Hi'", "Hi", ["INPUT: 0x48", "INPUT: 0x69"])

    # ===================================================================
    # Error/Edge Case Tests
    # ===================================================================
    print("--- Error and Edge Case Tests ---\n")

    # Unknown escape sequence
    tester.test("Unknown sequence ESC[999~", b'\x1b[999~',
                ["ESC received", "CSI sequence", "ERROR: Unknown escape sequence"],
                use_raw_bytes=True, delay=0.2)

    # Ctrl+Alt+A sequence (now valid)
    tester.test("Ctrl+Alt+A via ESC+Ctrl code", b'\x1b\x01',
                ["ESC received", "KEY: Ctrl+Alt+a"],
                use_raw_bytes=True, delay=0.2)


def main():
    parser = argparse.ArgumentParser(
        description='Hardware-in-the-Loop Test Suite for arduXT',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test_arduxt.py /dev/cu.usbmodem14101
  python3 test_arduxt.py /dev/ttyACM0
  python3 test_arduxt.py COM3  (Windows)

  # Using uv:
  uv run test_arduxt.py /dev/cu.usbmodem14101
        """
    )
    parser.add_argument('port', help='Serial port (e.g., /dev/cu.usbmodem14101)')
    parser.add_argument('-b', '--baudrate', type=int, default=9600,
                       help='Baud rate (default: 9600)')
    parser.add_argument('-t', '--timeout', type=float, default=1.0,
                       help='Serial timeout in seconds (default: 1.0)')

    args = parser.parse_args()

    # Create tester and connect
    tester = ArduXTTester(args.port, args.baudrate, args.timeout)

    try:
        if not tester.connect():
            print("Failed to connect to device")
            return 1

        # Run test suite
        run_test_suite(tester)

        # Print summary
        tester.print_summary()

        # Return exit code based on results
        return 0 if tester.fail_count == 0 else 1

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    finally:
        tester.disconnect()


if __name__ == "__main__":
    sys.exit(main())
