#!/usr/bin/env python3
"""
arduXT Fuzz Testing Framework

Long-duration fuzz testing to identify edge cases, timing issues,
and failure modes in the arduXT keyboard emulator.

Usage:
    python fuzz_arduxt.py /dev/ttyACM0 --duration 3600    # Run for 1 hour
    python fuzz_arduxt.py /dev/ttyACM0 --count 100000     # Send 100k inputs
    python fuzz_arduxt.py /dev/ttyACM0 --duration 14400 --report stats.json --failures failures.json
"""

import serial
import time
import random
import argparse
import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Tuple, Optional


class FuzzStatistics:
    """Track fuzz testing statistics with per-category metrics"""

    def __init__(self):
        self.start_time = time.time()
        self.total_inputs = 0
        self.successful_inputs = 0
        self.failed_inputs = 0
        self.timeouts = 0
        self.unexpected_responses = 0

        # Per-category tracking
        self.category_counts = defaultdict(int)
        self.category_successes = defaultdict(int)
        self.category_failures = defaultdict(int)

        self.response_times = []
        self.failures = []
        self.max_response_time = 0.0
        self.min_response_time = float('inf')

    def record_success(self, category: str, response_time: float):
        """Record a successful input"""
        self.total_inputs += 1
        self.successful_inputs += 1
        self.category_counts[category] += 1
        self.category_successes[category] += 1

        self.response_times.append(response_time)
        self.max_response_time = max(self.max_response_time, response_time)
        if response_time > 0:
            self.min_response_time = min(self.min_response_time, response_time)

    def record_failure(self, category: str, input_data: bytes, key_desc: str,
                      expected: str, actual: str, error_type: str):
        """Record a failed input"""
        self.total_inputs += 1
        self.failed_inputs += 1
        self.category_counts[category] += 1
        self.category_failures[category] += 1

        if error_type == "timeout":
            self.timeouts += 1
        elif error_type == "unexpected":
            self.unexpected_responses += 1

        self.failures.append({
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'key_description': key_desc,
            'input_hex': input_data.hex(),
            'input_bytes': list(input_data),
            'expected': expected,
            'actual': actual,
            'error_type': error_type
        })

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time

    def get_throughput(self) -> float:
        """Get inputs per second"""
        elapsed = self.get_elapsed_time()
        return self.total_inputs / elapsed if elapsed > 0 else 0

    def get_average_response_time(self) -> float:
        """Get average response time"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    def get_success_rate(self) -> float:
        """Get success rate as percentage"""
        if self.total_inputs == 0:
            return 0.0
        return (self.successful_inputs / self.total_inputs) * 100

    def get_category_success_rate(self, category: str) -> float:
        """Get success rate for a specific category"""
        total = self.category_counts.get(category, 0)
        if total == 0:
            return 0.0
        successes = self.category_successes.get(category, 0)
        return (successes / total) * 100


class KeystrokeGenerator:
    """Generate random keystrokes with random modifier combinations"""

    # Base keys - single keypresses (not including modifiers themselves)
    BASE_KEYS = {
        # Regular characters (a-z)
        'letters': [(chr(i), i) for i in range(ord('a'), ord('z')+1)],

        # Digits (0-9)
        'digits': [(chr(i), i) for i in range(ord('0'), ord('9')+1)],

        # Punctuation and special characters
        'punctuation': [
            (' ', 0x20), ('-', 0x2D), ('=', 0x3D), ('[', 0x5B), (']', 0x5D),
            (';', 0x3B), ("'", 0x27), ('`', 0x60), ('\\', 0x5C), (',', 0x2C),
            ('.', 0x2E), ('/', 0x2F),
        ],

        # Function keys (F1-F12)
        'function': [
            ('F1', b'\x1bOP'), ('F2', b'\x1bOQ'), ('F3', b'\x1bOR'), ('F4', b'\x1bOS'),
            ('F5', b'\x1b[15~'), ('F6', b'\x1b[17~'), ('F7', b'\x1b[18~'), ('F8', b'\x1b[19~'),
            ('F9', b'\x1b[20~'), ('F10', b'\x1b[21~'), ('F11', b'\x1b[23~'), ('F12', b'\x1b[24~'),
        ],

        # Navigation keys
        'navigation': [
            ('Up', b'\x1b[A'), ('Down', b'\x1b[B'), ('Right', b'\x1b[C'), ('Left', b'\x1b[D'),
            ('Home', b'\x1b[H'), ('End', b'\x1b[F'), ('Insert', b'\x1b[2~'), ('Delete', b'\x1b[3~'),
            ('PageUp', b'\x1b[5~'), ('PageDown', b'\x1b[6~'),
        ],

        # Special keys
        'special': [
            ('Enter', b'\r'), ('Tab', b'\t'), ('Backspace', b'\x08'), ('Escape', b'\x1b'),
        ],
    }

    # Modifier combinations (including none)
    MODIFIER_COMBINATIONS = [
        ('none', []),
        ('shift', ['shift']),
        ('ctrl', ['ctrl']),
        ('alt', ['alt']),
        ('shift_ctrl', ['shift', 'ctrl']),
        ('shift_alt', ['shift', 'alt']),
        ('ctrl_alt', ['ctrl', 'alt']),
        ('shift_ctrl_alt', ['shift', 'ctrl', 'alt']),
    ]

    def __init__(self):
        # Flatten all base keys into a single pool
        self.all_keys = []
        for key_type, keys in self.BASE_KEYS.items():
            self.all_keys.extend([(k, v, key_type) for k, v in keys])

    def generate(self) -> Tuple[bytes, str, str]:
        """Generate a random keystroke with random modifiers

        Returns:
            (data_bytes, category, description)
        """
        # Randomly select a base key
        key_name, key_data, key_type = random.choice(self.all_keys)

        # Randomly select a modifier combination
        mod_name, modifiers = random.choice(self.MODIFIER_COMBINATIONS)

        # Build the category name
        if mod_name == 'none':
            category = f"{key_type}"
        else:
            category = f"{mod_name}_{key_type}"

        # Build description
        if modifiers:
            mod_str = '+'.join([m.capitalize() for m in modifiers])
            description = f"{mod_str}+{key_name}"
        else:
            description = key_name

        # Generate the actual byte sequence
        data = self._build_sequence(key_name, key_data, key_type, modifiers)

        return data, category, description

    def _build_sequence(self, key_name: str, key_data, key_type: str, modifiers: List[str]) -> bytes:
        """Build the actual byte sequence for a key + modifiers"""

        # Function keys and navigation keys use escape sequences
        if key_type in ['function', 'navigation', 'special']:
            if not modifiers:
                # No modifiers - just the base sequence
                return key_data
            else:
                # With modifiers, need to use CSI format with modifier parameter
                # Modifier encoding: 1 + sum of (Shift=1, Alt=2, Ctrl=4)
                mod_value = 1
                if 'shift' in modifiers:
                    mod_value += 1
                if 'alt' in modifiers:
                    mod_value += 2
                if 'ctrl' in modifiers:
                    mod_value += 4

                # Convert base sequence to CSI format with modifier
                if key_type == 'function':
                    # Function keys
                    if key_name in ['F1', 'F2', 'F3', 'F4']:
                        # SS3 format -> CSI format
                        fn_char = key_data[-1:]  # Last char (P, Q, R, S)
                        return f'\x1b[1;{mod_value}{fn_char.decode()}'.encode('utf-8')
                    else:
                        # Already CSI format (ESC[nn~)
                        # Extract number from ESC[nn~
                        num_str = key_data.decode('utf-8')[2:-1]  # Extract '15' from '\x1b[15~'
                        return f'\x1b[{num_str};{mod_value}~'.encode('utf-8')

                elif key_type == 'navigation':
                    # Navigation keys
                    if key_name in ['Up', 'Down', 'Right', 'Left', 'Home', 'End']:
                        # Single char navigation (ESC[A)
                        nav_char = key_data[-1:]
                        return f'\x1b[1;{mod_value}{nav_char.decode()}'.encode('utf-8')
                    else:
                        # Multi-char navigation (ESC[n~)
                        num_str = key_data.decode('utf-8')[2:-1]
                        return f'\x1b[{num_str};{mod_value}~'.encode('utf-8')

                elif key_type == 'special':
                    # Special keys - handle modifiers differently
                    if key_name == 'Escape' and 'alt' in modifiers:
                        # Alt+Escape = double ESC
                        return b'\x1b\x1b'
                    else:
                        # For other special keys with modifiers, just send the base key
                        # (Tab, Enter, Backspace don't have standard escape sequences with modifiers)
                        return key_data

        # Regular characters (letters, digits, punctuation)
        else:
            # Build the sequence with actual XT scancodes approach
            if isinstance(key_data, int):
                char_byte = bytes([key_data])
            else:
                char_byte = key_data.encode('utf-8') if isinstance(key_data, str) else key_data

            # Handle modifiers for regular keys
            if 'ctrl' in modifiers and 'alt' in modifiers:
                # Ctrl+Alt+key = ESC followed by Ctrl code
                if key_type == 'letters':
                    ctrl_code = ord(key_name) - ord('a') + 1  # Convert to Ctrl+A..Z (0x01..0x1A)
                    return b'\x1b' + bytes([ctrl_code])
                else:
                    # For non-letters, just send ESC + character
                    return b'\x1b' + char_byte

            elif 'alt' in modifiers:
                # Alt+key = ESC followed by character
                return b'\x1b' + char_byte

            elif 'ctrl' in modifiers:
                # Ctrl+key = control code
                if key_type == 'letters':
                    ctrl_code = ord(key_name) - ord('a') + 1
                    return bytes([ctrl_code])
                else:
                    # For non-letters, just send the character
                    return char_byte

            elif 'shift' in modifiers:
                # Shift+key = shifted character
                if key_type == 'letters':
                    return key_name.upper().encode('utf-8')
                elif key_type == 'digits':
                    # Shift+digit = symbols
                    shift_map = {'0': ')', '1': '!', '2': '@', '3': '#', '4': '$',
                               '5': '%', '6': '^', '7': '&', '8': '*', '9': '('}
                    return shift_map.get(key_name, key_name).encode('utf-8')
                elif key_type == 'punctuation':
                    # Shift+punctuation
                    shift_map = {'-': '_', '=': '+', '[': '{', ']': '}', ';': ':',
                               "'": '"', '`': '~', '\\': '|', ',': '<', '.': '>', '/': '?'}
                    return shift_map.get(key_name, key_name).encode('utf-8')

            # No modifiers or unhandled combination
            return char_byte


class ArduXTFuzzer:
    """Fuzz testing framework for arduXT"""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0, delay: float = 0.075):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.delay = delay
        self.serial = None
        self.generator = KeystrokeGenerator()
        self.stats = FuzzStatistics()

    def connect(self):
        """Connect to the Arduino"""
        print(f"Connecting to {self.port} at {self.baudrate} baud...")
        self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(2)  # Wait for Arduino reset

        # Clear any startup messages
        while self.serial.in_waiting:
            self.serial.readline()

        print("Connected!")

    def send_and_verify(self, data: bytes, category: str, description: str) -> bool:
        """Send data and verify response"""
        start_time = time.time()

        try:
            # Clear any stale data from receive buffer
            self.serial.reset_input_buffer()

            # Send the data
            self.serial.write(data)
            self.serial.flush()

            # Give Arduino time to process
            time.sleep(0.05)

            # Read response
            response_lines = []
            deadline = time.time() + self.timeout

            while time.time() < deadline:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response_lines.append(line)

                    # Check if we got a complete response
                    if any('SCANCODE:' in line or 'ERROR:' in line for line in response_lines):
                        break
                time.sleep(0.01)

            response_time = time.time() - start_time
            response = '\n'.join(response_lines)

            # Validation
            if not response_lines:
                self.stats.record_failure(category, data, description, "response", "timeout", "timeout")
                return False

            if 'ERROR:' in response:
                self.stats.record_failure(category, data, description, "success", response, "unexpected")
                return False

            # Success
            self.stats.record_success(category, response_time)
            return True

        except Exception as e:
            self.stats.record_failure(category, data, description, "success", str(e), "exception")
            return False

    def display_progress(self):
        """Display real-time progress"""
        elapsed = self.stats.get_elapsed_time()
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        throughput = self.stats.get_throughput()
        success_rate = self.stats.get_success_rate()
        avg_response = self.stats.get_average_response_time() * 1000

        print(f"\r"
              f"Elapsed: {elapsed_str} | "
              f"Inputs: {self.stats.total_inputs} | "
              f"Success: {success_rate:.1f}% | "
              f"Throughput: {throughput:.1f}/s | "
              f"Avg Response: {avg_response:.1f}ms | "
              f"Failures: {self.stats.failed_inputs}",
              end='', flush=True)

    def run(self, duration: Optional[int] = None, count: Optional[int] = None):
        """Run fuzz testing"""
        print("\n" + "="*70)
        print("arduXT Fuzz Testing Framework")
        print("="*70)

        if duration:
            print(f"Duration: {duration} seconds ({duration/3600:.1f} hours)")
            end_time = time.time() + duration
        else:
            end_time = None

        if count:
            print(f"Target count: {count} inputs")

        print("\nStarting fuzz testing...\n")

        try:
            while True:
                # Check termination conditions
                if end_time and time.time() >= end_time:
                    break
                if count and self.stats.total_inputs >= count:
                    break

                # Generate and send random input
                data, category, description = self.generator.generate()
                self.send_and_verify(data, category, description)

                # Display progress every 10 inputs
                if self.stats.total_inputs % 10 == 0:
                    self.display_progress()

                # Delay between keystrokes
                time.sleep(self.delay)

        except KeyboardInterrupt:
            print("\n\nFuzz testing interrupted by user.")

        print("\n\nFuzz testing complete!")

    def generate_report(self, filename: Optional[str] = None) -> Dict:
        """Generate fuzz testing statistics report"""
        elapsed = self.stats.get_elapsed_time()

        # Build per-category statistics
        category_stats = {}
        for category in self.stats.category_counts.keys():
            total = self.stats.category_counts[category]
            successes = self.stats.category_successes[category]
            failures = self.stats.category_failures[category]
            success_rate = self.stats.get_category_success_rate(category)

            category_stats[category] = {
                'total': total,
                'successes': successes,
                'failures': failures,
                'success_rate': success_rate
            }

        report = {
            'summary': {
                'start_time': datetime.fromtimestamp(self.stats.start_time).isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_seconds': elapsed,
                'duration_hours': elapsed / 3600,
                'total_inputs': self.stats.total_inputs,
                'successful_inputs': self.stats.successful_inputs,
                'failed_inputs': self.stats.failed_inputs,
                'success_rate': self.stats.get_success_rate(),
                'throughput_per_second': self.stats.get_throughput(),
            },
            'performance': {
                'average_response_time_ms': self.stats.get_average_response_time() * 1000,
                'min_response_time_ms': self.stats.min_response_time * 1000 if self.stats.min_response_time != float('inf') else 0,
                'max_response_time_ms': self.stats.max_response_time * 1000,
            },
            'errors': {
                'timeouts': self.stats.timeouts,
                'unexpected_responses': self.stats.unexpected_responses,
                'total_failures': self.stats.failed_inputs,
            },
            'category_statistics': category_stats,
        }

        # Save to file if specified
        if filename:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nStatistics report saved to: {filename}")

        return report

    def save_failures(self, filename: str):
        """Save detailed failure log to separate file"""
        failure_log = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_failures': len(self.stats.failures),
                'total_tests': self.stats.total_inputs,
            },
            'failures': self.stats.failures
        }

        with open(filename, 'w') as f:
            json.dump(failure_log, f, indent=2)

        print(f"Failure log saved to: {filename}")

    def print_summary(self):
        """Print human-readable summary"""
        elapsed = self.stats.get_elapsed_time()

        print("\n" + "="*70)
        print("FUZZ TESTING SUMMARY")
        print("="*70)
        print(f"\nDuration: {timedelta(seconds=int(elapsed))}")
        print(f"Total Inputs: {self.stats.total_inputs}")
        print(f"Successful: {self.stats.successful_inputs} ({self.stats.get_success_rate():.2f}%)")
        print(f"Failed: {self.stats.failed_inputs}")
        print(f"  - Timeouts: {self.stats.timeouts}")
        print(f"  - Unexpected: {self.stats.unexpected_responses}")
        print(f"\nPerformance:")
        print(f"  Throughput: {self.stats.get_throughput():.2f} inputs/sec")
        print(f"  Avg Response Time: {self.stats.get_average_response_time()*1000:.2f}ms")
        print(f"  Min Response Time: {self.stats.min_response_time*1000:.2f}ms")
        print(f"  Max Response Time: {self.stats.max_response_time*1000:.2f}ms")

        # Per-category breakdown with success rates
        print(f"\nCategory Breakdown (sorted by failure rate):")

        # Sort by failure rate (highest first)
        categories = []
        for category in self.stats.category_counts.keys():
            total = self.stats.category_counts[category]
            failures = self.stats.category_failures[category]
            success_rate = self.stats.get_category_success_rate(category)
            categories.append((category, total, failures, success_rate))

        categories.sort(key=lambda x: x[2], reverse=True)  # Sort by failures

        for category, total, failures, success_rate in categories:
            if failures > 0:
                print(f"  {category:25s}: {total:5d} total, {failures:4d} failures ({success_rate:5.1f}% success)")

        # Show categories with no failures
        print(f"\nCategories with 100% success:")
        for category, total, failures, success_rate in categories:
            if failures == 0:
                print(f"  {category:25s}: {total:5d} total")

        if self.stats.failures:
            print(f"\nRecent Failures (last 10):")
            for failure in self.stats.failures[-10:]:
                print(f"  [{failure['timestamp']}] {failure['category']:20s} "
                      f"{failure['key_description']:20s} Error: {failure['error_type']}")

        print("="*70)

    def close(self):
        """Close serial connection"""
        if self.serial:
            self.serial.close()


def main():
    parser = argparse.ArgumentParser(
        description='arduXT Fuzz Testing Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run for 5 minutes with reports
  python fuzz_arduxt.py /dev/ttyACM0 --duration 300 --report stats.json --failures failures.json

  # Send 1000 random inputs
  python fuzz_arduxt.py /dev/ttyACM0 --count 1000

  # Run for 1 hour with custom delay
  python fuzz_arduxt.py /dev/ttyACM0 --duration 3600 --delay 0.1 --report stats.json
        """
    )

    parser.add_argument('port', help='Serial port (e.g., /dev/ttyACM0, COM3)')
    parser.add_argument('--duration', type=int, help='Test duration in seconds')
    parser.add_argument('--count', type=int, help='Number of inputs to send')
    parser.add_argument('--baudrate', type=int, default=9600, help='Baud rate (default: 9600)')
    parser.add_argument('--timeout', type=float, default=1.0, help='Response timeout in seconds (default: 1.0)')
    parser.add_argument('--delay', type=float, default=0.075, help='Inter-keystroke delay in seconds (default: 0.075)')
    parser.add_argument('--report', type=str, help='Save statistics report to JSON file')
    parser.add_argument('--failures', type=str, help='Save detailed failure log to JSON file')

    args = parser.parse_args()

    # Validate arguments
    if not args.duration and not args.count:
        parser.error("Must specify either --duration or --count")

    # Create and run fuzzer
    fuzzer = ArduXTFuzzer(args.port, args.baudrate, args.timeout, args.delay)

    try:
        fuzzer.connect()
        fuzzer.run(duration=args.duration, count=args.count)
        fuzzer.print_summary()
        fuzzer.generate_report(args.report)

        if args.failures:
            fuzzer.save_failures(args.failures)

    finally:
        fuzzer.close()


if __name__ == '__main__':
    main()
