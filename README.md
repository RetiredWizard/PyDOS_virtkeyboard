## PyDOS-virtkeyboard

**The modules needed to add virtual keyboard support to PyDOS**

The **lib/pydos_ui_virt.py** file performs the keyboard abstraction for PyDOS. 

To setup the virtual keyboard in PyDOS follow the standard PyDOS installation instructions and after
the setup.bat file has been run perform the following steps:

1) On the microcontroller rename /lib/pydos_ui.py to /lib/pydos_ui_uart.py
2) copy the contents of this repository to the microcontroller
