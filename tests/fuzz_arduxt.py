#!/usr/bin/env python3
"""
arduXT Fuzz Testing Framework

Long-duration fuzz testing to identify edge cases, timing issues,
and failure modes in the arduXT keyboard emulator.

Usage:
    python fuzz_arduxt.py /dev/ttyACM0 --duration 3600    # Run for 1 hour
    python fuzz_arduxt.py /dev/ttyACM0 --count 100000     # Send 100k inputs
    python fuzz_arduxt.py /dev/ttyACM0 --duration 14400 --report fuzz_report.json
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
    """Track fuzz testing statistics"""

    def __init__(self):
        self.start_time = time.time()
        self.total_inputs = 0
        self.successful_inputs = 0
        self.failed_inputs = 0
        self.timeouts = 0
        self.unexpected_responses = 0
        self.category_counts = defaultdict(int)
        self.response_times = []
        self.failures = []
        self.max_response_time = 0.0
        self.min_response_time = float('inf')

    def record_success(self, category: str, response_time: float):
        """Record a successful input"""
        self.total_inputs += 1
        self.successful_inputs += 1
        self.category_counts[category] += 1
        self.response_times.append(response_time)
        self.max_response_time = max(self.max_response_time, response_time)
        if response_time > 0:
            self.min_response_time = min(self.min_response_time, response_time)

    def record_failure(self, category: str, input_data: bytes,
                      expected: str, actual: str, error_type: str):
        """Record a failed input"""
        self.total_inputs += 1
        self.failed_inputs += 1
        self.category_counts[category] += 1

        if error_type == "timeout":
            self.timeouts += 1
        elif error_type == "unexpected":
            self.unexpected_responses += 1

        self.failures.append({
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'input': input_data.hex() if isinstance(input_data, bytes) else str(input_data),
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


class KeystrokeGenerator:
    """Generate random keystrokes covering all arduXT functionality"""

    # Basic ASCII printable characters
    ASCII_PRINTABLE = [chr(i) for i in range(32, 127)]

    # Control sequences (Ctrl+A through Ctrl+Z)
    CTRL_SEQUENCES = [bytes([i]) for i in range(0x01, 0x1B)]

    # Function keys F1-F12 (VT100 sequences)
    FUNCTION_KEYS = [
        b'\x1bOP',      # F1
        b'\x1bOQ',      # F2
        b'\x1bOR',      # F3
        b'\x1bOS',      # F4
        b'\x1b[15~',    # F5
        b'\x1b[17~',    # F6
        b'\x1b[18~',    # F7
        b'\x1b[19~',    # F8
        b'\x1b[20~',    # F9
        b'\x1b[21~',    # F10
        b'\x1b[23~',    # F11
        b'\x1b[24~',    # F12
    ]

    # Navigation keys
    NAVIGATION_KEYS = [
        b'\x1b[A',      # Up
        b'\x1b[B',      # Down
        b'\x1b[C',      # Right
        b'\x1b[D',      # Left
        b'\x1b[H',      # Home
        b'\x1b[F',      # End
        b'\x1b[2~',     # Insert
        b'\x1b[3~',     # Delete
        b'\x1b[5~',     # Page Up
        b'\x1b[6~',     # Page Down
    ]

    # Modifier combinations for function keys (;2=Shift, ;3=Alt, ;5=Ctrl, ;7=Ctrl+Alt)
    MODIFIERS = [2, 3, 5, 7]

    # Malformed escape sequences for edge case testing
    MALFORMED_SEQUENCES = [
        b'\x1b',            # Standalone ESC
        b'\x1b[',           # Incomplete CSI
        b'\x1b[999~',       # Invalid CSI code
        b'\x1b[A' * 50,     # Repeated sequence
        b'\x1b' * 10,       # Multiple ESC
        b'\x1bX',           # Invalid ESC sequence
        b'\x1b[;',          # Malformed CSI
    ]

    def __init__(self):
        self.categories = {
            'ascii': 40,           # 40% ASCII characters
            'ctrl': 15,            # 15% Control sequences
            'function': 15,        # 15% Function keys
            'function_mod': 10,    # 10% Function keys with modifiers
            'navigation': 10,      # 10% Navigation keys
            'alt_combo': 5,        # 5% Alt combinations
            'malformed': 5,        # 5% Malformed sequences
        }

    def generate(self) -> Tuple[bytes, str]:
        """Generate a random keystroke and return (data, category)"""
        # Select category based on weights
        category = random.choices(
            list(self.categories.keys()),
            weights=list(self.categories.values())
        )[0]

        if category == 'ascii':
            char = random.choice(self.ASCII_PRINTABLE)
            return char.encode('utf-8'), 'ascii'

        elif category == 'ctrl':
            return random.choice(self.CTRL_SEQUENCES), 'ctrl'

        elif category == 'function':
            return random.choice(self.FUNCTION_KEYS), 'function'

        elif category == 'function_mod':
            # Generate function key with modifier
            fn_base = random.choice([
                'P', 'Q', 'R', 'S',  # F1-F4 (SS3 format)
                '15', '17', '18', '19', '20', '21', '23', '24'  # F5-F12 (CSI format)
            ])
            modifier = random.choice(self.MODIFIERS)

            if fn_base in ['P', 'Q', 'R', 'S']:
                # SS3 format with modifier
                seq = f'\x1b[1;{modifier}{fn_base}'.encode('utf-8')
            else:
                # CSI format with modifier
                seq = f'\x1b[{fn_base};{modifier}~'.encode('utf-8')

            return seq, 'function_mod'

        elif category == 'navigation':
            return random.choice(self.NAVIGATION_KEYS), 'navigation'

        elif category == 'alt_combo':
            # Alt+character (ESC followed by character)
            char = random.choice(self.ASCII_PRINTABLE)
            return b'\x1b' + char.encode('utf-8'), 'alt_combo'

        elif category == 'malformed':
            return random.choice(self.MALFORMED_SEQUENCES), 'malformed'

        return b'a', 'ascii'  # Fallback


class ArduXTFuzzer:
    """Fuzz testing framework for arduXT"""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
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

    def send_and_verify(self, data: bytes, category: str) -> bool:
        """Send data and verify response"""
        start_time = time.time()

        try:
            # Send the data
            self.serial.write(data)
            self.serial.flush()

            # Read response (with timeout)
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
                time.sleep(0.001)

            response_time = time.time() - start_time
            response = '\n'.join(response_lines)

            # Basic validation - did we get any response?
            if not response_lines:
                self.stats.record_failure(category, data, "response", "timeout", "timeout")
                return False

            # Check for explicit errors
            if 'ERROR:' in response and category != 'malformed':
                self.stats.record_failure(category, data, "success", response, "unexpected")
                return False

            # Success
            self.stats.record_success(category, response_time)
            return True

        except Exception as e:
            self.stats.record_failure(category, data, "success", str(e), "exception")
            return False

    def display_progress(self):
        """Display real-time progress"""
        elapsed = self.stats.get_elapsed_time()
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        throughput = self.stats.get_throughput()
        success_rate = self.stats.get_success_rate()
        avg_response = self.stats.get_average_response_time() * 1000  # Convert to ms

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
                data, category = self.generator.generate()
                self.send_and_verify(data, category)

                # Display progress every 10 inputs
                if self.stats.total_inputs % 10 == 0:
                    self.display_progress()

                # Add small random delay (0-10ms) to simulate realistic typing
                time.sleep(random.uniform(0, 0.01))

        except KeyboardInterrupt:
            print("\n\nFuzz testing interrupted by user.")

        print("\n\nFuzz testing complete!")

    def generate_report(self, filename: Optional[str] = None) -> Dict:
        """Generate fuzz testing report"""
        elapsed = self.stats.get_elapsed_time()

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
            'category_breakdown': dict(self.stats.category_counts),
            'failures': self.stats.failures[-100:],  # Last 100 failures
        }

        # Save to file if specified
        if filename:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to: {filename}")

        return report

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

        print(f"\nCategory Breakdown:")
        for category, count in sorted(self.stats.category_counts.items(),
                                     key=lambda x: x[1], reverse=True):
            percentage = (count / self.stats.total_inputs * 100) if self.stats.total_inputs > 0 else 0
            print(f"  {category:20s}: {count:6d} ({percentage:5.1f}%)")

        if self.stats.failures:
            print(f"\nRecent Failures (last 10):")
            for failure in self.stats.failures[-10:]:
                print(f"  [{failure['timestamp']}] {failure['category']:15s} "
                      f"Input: {failure['input'][:20]} Error: {failure['error_type']}")

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
  # Run for 1 hour
  python fuzz_arduxt.py /dev/ttyACM0 --duration 3600

  # Send 100,000 random inputs
  python fuzz_arduxt.py /dev/ttyACM0 --count 100000

  # Run for 4 hours with JSON report
  python fuzz_arduxt.py /dev/ttyACM0 --duration 14400 --report fuzz_report.json

  # Run overnight (8 hours) on custom port
  python fuzz_arduxt.py /dev/cu.usbmodem14101 --duration 28800 --baudrate 9600
        """
    )

    parser.add_argument('port', help='Serial port (e.g., /dev/ttyACM0, COM3)')
    parser.add_argument('--duration', type=int, help='Test duration in seconds')
    parser.add_argument('--count', type=int, help='Number of inputs to send')
    parser.add_argument('--baudrate', type=int, default=9600, help='Baud rate (default: 9600)')
    parser.add_argument('--timeout', type=float, default=1.0, help='Response timeout in seconds (default: 1.0)')
    parser.add_argument('--report', type=str, help='Save JSON report to file')

    args = parser.parse_args()

    # Validate arguments
    if not args.duration and not args.count:
        parser.error("Must specify either --duration or --count")

    # Create and run fuzzer
    fuzzer = ArduXTFuzzer(args.port, args.baudrate, args.timeout)

    try:
        fuzzer.connect()
        fuzzer.run(duration=args.duration, count=args.count)
        fuzzer.print_summary()
        fuzzer.generate_report(args.report)
    finally:
        fuzzer.close()


if __name__ == '__main__':
    main()
