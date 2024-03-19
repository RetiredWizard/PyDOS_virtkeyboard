"""
MIT License

Copyright (c) 2020

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

------------------------------------------------------------------------------

XPT2046 Touch module for CircuitPython
modified from xpt2046.py of rdagger/micropython-ili9341
https://github.com/rdagger/micropython-ili9341/blob/master/xpt2046.py

Removed interrupt and re-config pin for CircuitPython

3/2024 RetiredWizard - removed normalization function (PyDOS calibration done in Pydos_ui)
"""
from time import sleep
import digitalio

class Touch(object):
    """Serial interface for XPT2046 Touch Screen Controller."""

    # Command constants from ILI9341 datasheet
    GET_X = const(0b11010000)  # X position
    GET_Y = const(0b10010000)  # Y position
    GET_Z1 = const(0b10110000)  # Z1 position
    GET_Z2 = const(0b11000000)  # Z2 position
    GET_TEMP0 = const(0b10000000)  # Temperature 0
    GET_TEMP1 = const(0b11110000)  # Temperature 1
    GET_BATTERY = const(0b10100000)  # Battery monitor
    GET_AUX = const(0b11100000)  # Auxiliary input to ADC
    
    def __init__(self, spi, cs):
        """Initialize touch screen controller.

        Args:
            spi (Class Spi):  SPI interface for OLED
            cs (Class Pin):  Chip select pin
            int_pin (Class Pin):  Touch controller interrupt pin
            int_handler (function): Handler for screen interrupt
        """
        self.spi = spi
        self.cs = cs
        self.cs_io = digitalio.DigitalInOut(cs)
        self.cs_io.direction = digitalio.Direction.OUTPUT
        self.cs_io.value=1
        
        self.rx_buf = bytearray(3)  # Receive buffer
        self.tx_buf = bytearray(3)  # Transmit buffer

        self._last_touch = [{"x": None, "y": None, "id": None}]
        self._last_touch = self._get_touch()

    @property
    def touched(self) -> int:
        curr_touch = self._get_touch()
        if self._last_touch != curr_touch:
            self._last_touch = curr_touch
            return 1
        else:
            return 0

    def _get_touch(self):
        """Take multiple samples to get accurate touch reading."""
        timeout = .1  # set timeout
        confidence = 5
        buff = [[0, 0] for x in range(confidence)]
        buf_length = confidence  # Require a confidence of 5 good samples
        buffptr = 0  # Track current buffer position
        nsamples = 0  # Count samples
        while timeout > 0:
            if nsamples == buf_length:
                x = sum([c[0] for c in buff]) // buf_length
                y = sum([c[1] for c in buff]) // buf_length
                dev = sum([(c[0] - x)**2 +
                          (c[1] - y)**2 for c in buff]) / buf_length
                if dev <= 50:  # Deviation should be under margin of 50
                    return [{"x": x, "y": y, "id": 0}]
            # get a new value
            sample = self.raw_touch()  # get a touch
            if sample is None:
                nsamples = 0    # Invalidate buff
            else:
                buff[buffptr] = sample  # put in buff
                buffptr = (buffptr + 1) % buf_length  # Incr, until rollover
                nsamples = min(nsamples + 1, buf_length)  # Incr. until max

            sleep(.001)
            timeout -= .002
        return self._last_touch

    # pylint: disable=unused-variable
    @property
    def touches(self) -> List[dict]:
        """
        Returns a list of touchpoint dicts, with 'x' and 'y' containing the
        touch coordinates, and 'id' as the touch # for multitouch tracking
        """
        return self._last_touch

    def raw_touch(self):
        """Read raw X,Y touch values.

        Returns:
            tuple(int, int): X, Y
        """
        y = self.send_command(self.GET_X)
        x = self.send_command(self.GET_Y)
        if 100 <= x <= 2000 and 100 <= y <= 2000:
            return (x, y)
        else:
            return None

    def send_command(self, command):
        """Write command to XT2046 (MicroPython).

        Args:
            command (byte): XT2046 command code.
        Returns:
            int: 12 bit response
        """
        self.tx_buf[0] = command
        
        self.cs_io.value=0
        
        self.spi.try_lock()
        self.spi.write_readinto(self.tx_buf, self.rx_buf)
        self.spi.unlock()
        
        self.cs_io.value=1

        return (self.rx_buf[1] << 4) | (self.rx_buf[2] >> 4)
        
