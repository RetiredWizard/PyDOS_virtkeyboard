import board
import gifio
import displayio
import time
from pydos_ui import Pydos_ui
try:
    from pydos_ui import input
except:
    pass

"""
import rgbmatrix
import framebufferio
displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=4,
    rgb_pins=[
        board.MTX_R1,
        board.MTX_G1,
        board.MTX_B1,
        board.MTX_R2,
        board.MTX_G2,
        board.MTX_B2
    ],
    addr_pins=[
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE
)
display = framebufferio.FramebufferDisplay(matrix)
"""

if '_display' not in dir(Pydos_ui) and 'DISPLAY' not in dir(board):
    try:
        import framebufferio
        import dotclockframebuffer
    except:
        import adafruit_ili9341

    displayio.release_displays()

    try:
        fb=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS)
        display = framebufferio.FramebufferDisplay(fb)
    except:
        spi = board.SPI()
        disp_bus=displayio.FourWire(spi,command=board.D10,chip_select=board.D9, \
            reset=board.D6)
        display=adafruit_ili9341.ILI9341(disp_bus,width=320,height=240)

else:
    try:
        display = Pydos_ui._display
    except:
        display = board.DISPLAY

splash = displayio.Group()

fname = input("Enter filename:")
try:
    while Pydos_ui.virt_touched():
        pass
except:
    pass
input('Press "Enter" to continue, press "q" to quit')

odgcc = gifio.OnDiskGif(fname)

start = time.monotonic()
next_delay = odgcc.next_frame() # Load the first frame
end = time.monotonic()
overhead = end - start

facecc = displayio.TileGrid(odgcc.bitmap, \
    pixel_shader=displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565_SWAPPED))

splash.append(facecc)

#try:
#    board.DISPLAY.root_group = splash
#except:
display.root_group = splash

cmnd = ""
# Display repeatedly.
while cmnd.upper() != "Q":

    if Pydos_ui.serial_bytes_available():
        cmnd = Pydos_ui.read_keyboard(1)
        print(cmnd, end="", sep="")
        if cmnd in "qQ":
            break
    display.root_group=splash
    #time.sleep(max(0, next_delay - overhead))
    time.sleep(0.1)
    next_delay = odgcc.next_frame()
#    next_delay = odgp.next_frame()

splash.pop()
display.root_group = displayio.CIRCUITPYTHON_TERMINAL