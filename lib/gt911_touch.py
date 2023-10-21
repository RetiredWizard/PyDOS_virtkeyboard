# SPDX-FileCopyrightText: 2017 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`gt911_touch`
====================================================

CircuitPython driver for GOODix GT911 touch chip.

* Author(s): ladyada, retiredwizard

Implementation Notes
--------------------

**Hardware:**

* MaTouch ESP32-S3 Parallel TFT with Touch 7"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the ESP32-S3 boards:
  https://github.com/adafruit/circuitpython/releases
* Adafruit's Bus Device library (when using I2C/SPI):
  https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

# imports

__version__ = "0.0.0+auto.0"
#__repo__ = "https://github.com/retiredwizard/PyDOS_virtkeyboard.git"

import struct
import digitalio
import time

from adafruit_bus_device.i2c_device import I2CDevice

from micropython import const

try:
    from typing import List
except ImportError:
    pass


_GT_DEFAULT_I2C_ADDR = 0x5D
_GT_SECONDARY_I2C_ADDR = 0x14

_GT_COMMAND = const(0x8040)


_GT_REG_STATUS = const(0x814E)
_GT_POINT1_COORD = const(0x814F)
_GT_REG_PRODID_1 = const(0x8140)
_GT_REG_PRODID_2 = const(0x8141)
_GT_REG_PRODID_3 = const(0x8142)
_GT_REG_PRODID_4 = const(0x8143)
_GT_REG_FIRMVERSH = const(0x8145)
_GT_REG_FIRMVERSL = const(0x8144)
_GT_REG_VENDID = const(0x814A)

_GT_PANNEL_BITFREQH = const(0x8068)
_GT_PANNEL_BITFREQL = const(0x8067)
_GT_SCREEN_TOUCH_LVL = const(0x8053)

_GT_TOUCH_NO = const(0x804C)
_GT_X_THRESHOLD = const(0x8057)
_GT_Y_THRESHOLD = const(0x8058)


class GT911_Touch:
    """
    A driver for the GT911 capacitive touch sensor.
    """

    def __init__(self, i2c, res_pin, i2c_address=None, debug=False, irq_pin=None):

        self._debug = debug
        self._irq_pin = irq_pin

        if type(res_pin) != digitalio.DigitalInOut:
            raise RuntimeError("res_pin must be of type digitalio.DigitalInOut")

        if i2c_address is not None:
            address = i2c_address
        else:
            address = _GT_DEFAULT_I2C_ADDR

        self._reset(address,res_pin,irq_pin)
        try:
            self._i2c = I2CDevice(i2c, address)
        except:
            if debug:
                print("Second reset attempt")
            if i2c_address is None:
                address = _GT_SECONDARY_I2C_ADDR
                try:
                    self._i2c = I2CDevice(i2c,address)
                except:
                    self._reset(address,res_pin,irq_pin)
                    self._i2c = I2CDevice(i2c, address)
            else:
                self._reset(address,res_pin,irq_pin)
                self._i2c = I2CDevice(i2c, address)

        if debug:
            print("I2C Address:",address)
            
        self._last_touch = self._read_last_touch()

        chip_id = chr(self._read(_GT_REG_PRODID_1,1)[0])
        chip_id += chr(self._read(_GT_REG_PRODID_2,1)[0])
        chip_id += chr(self._read(_GT_REG_PRODID_3,1)[0])
        chip_id += chr(self._read(_GT_REG_PRODID_4,1)[0])
        firm_id = self._read(_GT_REG_FIRMVERSH,1)[0]
        firm_id = (firm_id << 8) | self._read(_GT_REG_FIRMVERSL,1)[0]
        vend_id = self._read(_GT_REG_VENDID,1)[0]
        num_touch = self._read(_GT_TOUCH_NO,1)[0] * 0x0F
        x_thresh = self._read(_GT_X_THRESHOLD,1)[0]
        y_thresh = self._read(_GT_Y_THRESHOLD,1)[0]

        if debug:
            print("Number of touchpoints: ",num_touch," X,Y Thresholds: ",x_thresh,",",y_thresh)
            print(
                "chip_id: {:4}, firm_id: {:02X}, vend_id: {:02X}".format(
                    chip_id, firm_id, vend_id
                )
            )
            print("Firmware ID %02X" % firm_id)
            print("Point rate %d Hz" % ((self._read(_GT_PANNEL_BITFREQH, 1)[0] << 8) | self._read(_GT_PANNEL_BITFREQL, 1)[0]))
            print("Thresh %d" % self._read(_GT_SCREEN_TOUCH_LVL, 1)[0])

        self._write(_GT_COMMAND,[0])  # Read coordinates status

    @property
    def touched(self) -> int:
        curr_touch = self._read_last_touch()
        if self._last_touch != curr_touch:
            self._last_touch = curr_touch
            """ If this extra call to _read_last_touch() 
            isn't made then the next touch is missed ?????
            I have no idea why """
            self._read_last_touch()
            return 1
        else:
            return 0

    def _read_last_touch(self):
        self._write(_GT_REG_STATUS,[0])
        test = self._read(_GT_REG_STATUS,1)[0]
        timeout = 1000
        while not (test & 0x80) and (timeout := timeout-1) > 0:
            if test == 0:
                break
            time.sleep(.001)
            self._write(_GT_REG_STATUS,[0])
            test = self._read(_GT_REG_STATUS,1)[0]
        self._write(_GT_REG_STATUS,[0])
        return [v for v in self._read(_GT_POINT1_COORD,7)]

    # pylint: disable=unused-variable
    @property
    def touches(self) -> List[dict]:
        """
        Returns a list of touchpoint dicts, with 'x' and 'y' containing the
        touch coordinates, and 'id' as the touch # for multitouch tracking
        """
        touchpoints = []
        data = self._last_touch

        touchcount = 1
        if self._debug:
            print("touchcount: {}".format(touchcount))

        for i in range(touchcount):
            touch_id = data[0]

            x = data[2] * 256 + data[1]
            y = data[4] * 256 + data[3]

            point = {"x": x, "y": y, "id": touch_id}
            if self._debug:
                print("id: {}, x: {}, y: {}".format(touch_id, x, y))
            touchpoints.append(point)
        return touchpoints
    
    def _reset(self, address, res_pin, irq_pin=None) -> None:
        """ Initialize board - This sometimes fails, Ctrl-D reset to recover """
        time.sleep(.0001)
        res_pin.direction = digitalio.Direction.OUTPUT
        res_pin.value = True
        if irq_pin is not None:
            irq_pin.direction = digitalio.Direction.OUTPUT
            irq_pin.value = False
        time.sleep(.005)
        res_pin.value = False
        time.sleep(.001)
        if irq_pin is not None:
            irq_pin.value = (address != _GT_DEFAULT_I2C_ADDR)
        time.sleep(.001)
        res_pin.value = True
        time.sleep(.01)
        if irq_pin is not None:
            irq_pin.value = False
        time.sleep(.055)
        if irq_pin is not None:
            irq_pin.direction = digitalio.Direction.INPUT
        time.sleep(0.055)

        return

    def _read(self, register, length, irq_pin=None) -> bytearray:
        """Returns an array of 'length' bytes from the 'register'"""
        with self._i2c as i2c:
            if irq_pin is not None:
                while irq_pin.value:
                    pass

            i2c.write(bytes([((register & 0xFF00) >> 8),(register & 0xFF)]))
            result = bytearray(length)
            time.sleep(.1)

            i2c.readinto(result)
            if self._debug:
                print("\t$%02X => %s" % (register, [hex(i) for i in result]))
            return result

    def _write(self, register, values) -> None:
        """Writes an array of 'length' bytes to the 'register'"""
        with self._i2c as i2c:
            values = [((register & 0xFF00) >> 8), (register & 0xFF)] + [(v & 0xFF) for v in values]
            #print("register: %02X, value: %02X" % (values[0], values[1]))
            i2c.write(bytes(values))

            if self._debug:
                print("\t$%02X <= %s" % (values[0], [hex(i) for i in values[1:]]))
                

