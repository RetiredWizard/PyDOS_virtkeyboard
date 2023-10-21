## PyDOS_virtkeyboard - PyDOS running on a tablet?

**The modules needed to add virtual keyboard support to [PyDOS](https://github.com/RetiredWizard/PyDOS)**

**Check out the demo video at https://youtu.be/AVLaLuzFrxY**  
**The PyDOS repository: https://github.com/RetiredWizard/PyDOS**

Currently this requires:
  - CircuitPython 9.x (pre-alpha) - See [releases](https://github.com/RetiredWizard/PyDOS_virtkeyboard/releases) for firmware download
  - a "dot clock"/"666" display
  - FocalTech capacitive touch chips (Currently supports FT6206 & FT6236)
  - GOODIX GT911 touch interface

This has only been tested using the [HackTablet](https://hackaday.io/project/185831-hacktablet-crestron-tss-752-teardown-rebuild) and the [MaTouch ESP32-S3 7"](https://www.makerfabs.com/index.php?route=product/product&product_id=774)

The **lib/pydos_ui_virt.py** file performs the keyboard abstraction for PyDOS. 

To setup the virtual keyboard in PyDOS follow the standard PyDOS installation instructions and after
the setup.bat file has been run perform the following steps:

1) On the microcontroller rename /lib/pydos_ui.py to /lib/pydos_ui_uart.py
2) copy the contents of this repository to the microcontroller
3) On the microcontroller rename /lib/pydos_ui_virt.py to /lib/pydos_ui.py
