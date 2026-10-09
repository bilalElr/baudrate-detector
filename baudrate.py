#!/usr/bin/env python3
import sys
import time
import serial
from threading import Thread


class RawInput:
    """Gets a single character from standard input. Does not echo to the screen."""
    def __init__(self):
        try:
            self.impl = RawInputWindows()
        except ImportError:
            self.impl = RawInputUnix()

    def __call__(self):
        return self.impl()


class RawInputUnix:
    def __call__(self):
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class RawInputWindows:
    def __call__(self):
        import msvcrt
        return msvcrt.getch().decode('latin-1')


class Baudrate:
    VERSION = '1.0'
    READ_TIMEOUT = 5
    BAUDRATES = [
        "9600",
        "19200",
        "38400",
        "57600",
        "115200",
    ]
    UPKEYS   = ['u', 'U', 'A']
    DOWNKEYS = ['d', 'D', 'B']
    MIN_CHAR_COUNT = 25
    WHITESPACE  = [' ', '\t', '\r', '\n']
    PUNCTUATION = ['.', ',', ':', ';', '?', '!']
    VOWELS      = ['a', 'A', 'e', 'E', 'i', 'I', 'o', 'O', 'u', 'U']

    def __init__(self, port=None, threshold=MIN_CHAR_COUNT, timeout=READ_TIMEOUT,
                 name=None, auto=True, verbose=False):
        self.port = port
        self.threshold = threshold
        self.timeout = timeout
        self.name = name
        self.auto_detect = auto
        self.verbose = verbose
        self.index = len(self.BAUDRATES) - 1
        self.valid_characters = []
        self.ctlc = False
        self.thread = None
        self._gen_char_list()

    def _gen_char_list(self):
        """Build list of printable ASCII + whitespace characters."""
        self.valid_characters = [chr(c) for c in range(ord(' '), ord('~') + 1)]
        for c in self.WHITESPACE:
            if c not in self.valid_characters:
                self.valid_characters.append(c)

    def _print(self, data):
        if self.verbose:
            sys.stderr.write(data)
            sys.stderr.flush()

    def Open(self):
        self.serial = serial.Serial(self.port, timeout=self.timeout)
        self.NextBaudrate(0)

    def NextBaudrate(self, updn):
        self.index += updn
        if self.index >= len(self.BAUDRATES):
            self.index = 0
        elif self.index < 0:
            self.index = len(self.BAUDRATES) - 1
        sys.stderr.write('\n\n@@@@@@@@@@@@@@@@@@@@@ Baudrate: %s @@@@@@@@@@@@@@@@@@@@@\n\n'
                         % self.BAUDRATES[self.index])
        sys.stderr.flush()
        self.serial.flush()
        self.serial.baudrate = int(self.BAUDRATES[self.index])
        self.serial.flush()

    def HandleKeypress(self, *args):
        """Manual mode: u/d to cycle baudrates, Ctrl-C to quit."""
        get_char = RawInput()
        while not self.ctlc:
            c = get_char()
            if c in self.UPKEYS:
                self.NextBaudrate(1)
            elif c in self.DOWNKEYS:
                self.NextBaudrate(-1)
            elif c in ['\x03', 'q', 'Q']:
                self.ctlc = True
                break

    def Detect(self):
        count = 0
        whitespace = 0
        punctuation = 0
        vowels = 0
        start_time = 0
        timed_out = False

        if not self.auto_detect:
            self.thread = Thread(target=self.HandleKeypress, daemon=True)
            self.thread.start()

        while True:
            if self.ctlc:
                break

            if start_time == 0:
                start_time = time.time()

            raw = self.serial.read(1)
            if not raw:
                timed_out = True
            else:
                # Decode the byte; replace undecodable bytes with a placeholder
                try:
                    ch = raw.decode('ascii')
                except UnicodeDecodeError:
                    ch = None

                if self.auto_detect:
                    if ch and ch in self.valid_characters:
                        if ch in self.WHITESPACE:
                            whitespace += 1
                        elif ch in self.PUNCTUATION:
                            punctuation += 1
                        elif ch in self.VOWELS:
                            vowels += 1
                        count += 1
                        self._print(ch)
                    else:
                        # Bad character — reset counters and try next baudrate
                        count = whitespace = punctuation = vowels = 0
                        start_time = 0
                        self.NextBaudrate(1)
                else:
                    if ch:
                        self._print(ch)

                if (self.auto_detect and count >= self.threshold
                        and whitespace > 0 and punctuation > 0 and vowels > 0):
                    sys.stderr.write('\n\n@@@ Detected baudrate: %s @@@\n\n'
                                     % self.BAUDRATES[self.index])
                    break

                if (time.time() - start_time) >= self.timeout:
                    timed_out = True

            if timed_out:
                if self.auto_detect:
                    count = whitespace = punctuation = vowels = 0
                    start_time = 0
                    timed_out = False
                    self.NextBaudrate(1)
                else:
                    timed_out = False
                    start_time = 0


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Detect or monitor a serial port baudrate.')
    parser.add_argument('-p', '--port',      required=True,  help='Serial port (e.g. /dev/ttyUSB0)')
    parser.add_argument('-t', '--threshold', type=int, default=Baudrate.MIN_CHAR_COUNT,
                        help='Number of valid chars needed to confirm baudrate (default: 25)')
    parser.add_argument('-T', '--timeout',   type=float, default=Baudrate.READ_TIMEOUT,
                        help='Seconds to wait per baudrate before trying the next (default: 5)')
    parser.add_argument('-m', '--manual',    action='store_true',
                        help='Manual mode: use u/d keys to cycle baudrates yourself')
    parser.add_argument('-v', '--verbose',   action='store_true',
                        help='Print received characters to stderr')
    args = parser.parse_args()

    b = Baudrate(
        port=args.port,
        threshold=args.threshold,
        timeout=args.timeout,
        auto=not args.manual,
        verbose=args.verbose,
    )
    b.Open()
    try:
        b.Detect()
    except KeyboardInterrupt:
        pass
    finally:
        b.serial.close()
