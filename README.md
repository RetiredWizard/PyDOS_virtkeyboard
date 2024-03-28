# PyDOS_virtkeyboard - PyDOS running on a tablet?

**The modules needed to add virtual keyboard support to [PyDOS](https://github.com/RetiredWizard/PyDOS)**

**Check out the demo video at https://youtu.be/AVLaLuzFrxY**  
**The PyDOS repository: https://github.com/RetiredWizard/PyDOS**

Currently this requires:
  - CircuitPython 9.x - See https://www.circuitpython.org/downloads for firmware download

The hardware currently supported uses one or more of:
  - "dot clock"/"666" display
  - ili9341 TFT LCD display
  - FocalTech capacitive touch chips (Currently supports FT6206 & FT6236)
  - GOODIX GT911 touch controller
  - TSC2007 touch controller
  - XPT2046 touch controller

As far as I know there currently is no fully functional GT911 touch library for CircuitPython or MicroPython, but the **gt911_touch.py** library included here, uses a similar API as the Adafruit FocalTech and TSC2007 libraries and seems to work well enough for the virtual keyboard to be usable. The GT911demo.py program is a simple demonstration using the library to operate the touch panel.

The PyDOS virtual keyboard has only been tested using the [HackTablet](https://hackaday.io/project/185831-hacktablet-crestron-tss-752-teardown-rebuild), the [MaTouch ESP32-S3 7"](https://www.makerfabs.com/index.php?route=product/product&product_id=774), the [Adafruit TFT FeatherWing V2](https://www.adafruit.com/product/3315) and the [Sunton-ESP32-2432S028](https://www.makerfabs.com/sunton-esp32-2-8-inch-tft-with-touch.html) ("Cheap Yellow Display").

The [**lib/pydos_ui_virt.py**](https://github.com/RetiredWizard/PyDOS_virtkeyboard/blob/main/lib/pydos_ui_virt.py) file performs the keyboard abstraction for PyDOS.  

Up/Down arrow, command history and line editing is supported. The Hacktablet has the arrow icons printed along the right border of the screen but for other tablets the vitual keyboard bitmap has not yet been updated.

To setup the virtual keyboard in PyDOS follow the standard PyDOS installation instructions and after
the setup.bat file has been run perform the following steps:

1) On the microcontroller rename /lib/pydos_ui.py to /lib/pydos_ui_uart.py
2) copy the contents of this repository to the microcontroller
3) On the microcontroller rename /lib/pydos_ui_virt.py to /lib/pydos_ui.py

## Files Not Needed By Supported Boards

The following files in the /lib/ folder can be deleted (or not copied) for the indicated board

For the Hacktablet delete:
  - /lib/adafruit_ili9341.mpy
  - /lib/adafruit_tsc2007.mpy
  - /lib/gt911_touch.py
  - /lib/pydos_xpt2046.py
  - /lib/keyboard320.bmp
  - /lib/keyboard1024.bmp

for MaTouch ESP32-S3 7" delete:
  - /lib/adafruit_focaltouch.mpy
  - /lib/adafruit_ili9341.mpy
  - /lib/adafruit_tsc2007.mpy
  - /lib/pydos_xpt2046.py
  - /lib/keyboard320.bmp

for Adafruit TFT Featherwing delete:
  - /lib/adafruit_focaltouch.mpy
  - /lib/gt911_touch.py
  - /lib/pydos_xpt2046.py
  - /lib/keyboard800.bmp
  - /lib/keyboard1024.bmp

for a Cheap Yellow Display delete:
  - /lib/adafruit_focaltouch.mpy
  - /lib/adafruit_ili9341.mpy
  - /lib/gt911_touch.py
  - /lib/adafruit_tsc2007.mpy
  - /lib/keyboard800.bmp
  - /lib/keyboard1024.bmp

  Only the keyboard bitmap that matches the width of your display is needed in the /lib/ folder.