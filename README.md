# baudrate-detector
I found a python script that detects baudrate in UART connections, but it was in python2, so I rewrote it for python3 instead. Claude was used to clean up the code because my version was a bit more messy.

Usage:
```
usage: baudrate.py [-h] -p PORT [-t THRESHOLD] [-T TIMEOUT] [-m] [-v]

Detect or monitor a serial port baudrate.

options:
  -h, --help                  show this help message and exit
  -p, --port PORT             Serial port (e.g. /dev/ttyUSB0)
  -t, --threshold THRESHOLD   Number of valid chars needed to confirm baudrate (default: 25)
  -T, --timeout TIMEOUT       Seconds to wait per baudrate before trying the next (default: 5)
  -m, --manual                Manual mode: use u/d keys to cycle baudrates yourself
  -v, --verbose               Print received characters to stderr
```
