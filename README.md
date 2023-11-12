## PyDOS_virtkeyboard - PyDOS running on a tablet?

**The modules needed to add virtual keyboard support to [PyDOS](https://github.com/RetiredWizard/PyDOS)**

**Check out the demo video at https://youtu.be/AVLaLuzFrxY**  
**The PyDOS repository: https://github.com/RetiredWizard/PyDOS**

Currently this requires:
  - CircuitPython 9.x (alpha) - See [releases](https://github.com/RetiredWizard/PyDOS_virtkeyboard/releases) for firmware download

The hardware currently supported uses one or more of:
  - "dot clock"/"666" display
  - ili9341 TFT LCD display
  - FocalTech capacitive touch chips (Currently supports FT6206 & FT6236)
  - GOODIX GT911 touch controller
  - TSC2007 touch controller

This has only been tested using the [HackTablet](https://hackaday.io/project/185831-hacktablet-crestron-tss-752-teardown-rebuild), the [MaTouch ESP32-S3 7"](https://www.makerfabs.com/index.php?route=product/product&product_id=774) and the [Adafruit TFT FeatherWing V2](https://www.adafruit.com/product/3315)

The [**lib/pydos_ui_virt.py**](https://github.com/RetiredWizard/PyDOS_virtkeyboard/blob/main/lib/pydos_ui_virt.py) file performs the keyboard abstraction for PyDOS. 

To setup the virtual keyboard in PyDOS follow the standard PyDOS installation instructions and after
the setup.bat file has been run perform the following steps:

1) On the microcontroller rename /lib/pydos_ui.py to /lib/pydos_ui_uart.py
2) copy the contents of this repository to the microcontroller
3) On the microcontroller rename /lib/pydos_ui_virt.py to /lib/pydos_ui.py

The following files in the /lib/ folder are only required for the indicated board

Hacktablet:
  - /lib/adafruit_focaltouch.mpy

MaTouch ESP32-S3:
  - /lib/gt911_touch.py

Adafruit TFT Featherwing:
  - /lib/adafruit_ili9341.mpy
  - /lib/adafruit_tsc2007.mpy

  Only the keyboard bitmap that matches the width of your display is needed in the /lib/ folder.