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

if '_display' not in dir(Pydos_ui):
    import framebufferio
    import dotclockframebuffer

    displayio.release_displays()

    fb=dotclockframebuffer.DotClockFramebuffer(**board.TFT,**board.TIMINGS800)
    display = framebufferio.FramebufferDisplay(fb)
else:
    display = Pydos_ui._display

splash = displayio.Group()

fname = input("Enter filename:")
while Pydos_ui.virt_touched():
    pass
input('Press "Enter" to continue, press "q" to quit')

odgcc = gifio.OnDiskGif(fname)
#odgp = gifio.OnDiskGif('homer-64x64.gif')

start = time.monotonic()
next_delay = odgcc.next_frame() # Load the first frame
#odgp.next_frame()
end = time.monotonic()
overhead = end - start

facecc = displayio.TileGrid(odgcc.bitmap, \
    pixel_shader=displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565_SWAPPED))
#facep = displayio.TileGrid(odgp.bitmap, pixel_shader=odgp.palette)
#facep.x = 64

splash.append(facecc)
#splash.append(facep)

try:
    board.DISPLAY.root_group = splash
except:
    #display.root_group = splash
    display.show(splash)

cmnd = ""
# Display repeatedly.
while cmnd.upper() != "Q":

    if Pydos_ui.serial_bytes_available():
        cmnd = Pydos_ui.read_keyboard(1)
        print(cmnd, end="", sep="")
        if cmnd in "qQ":
            break
    display.show(splash)
    #time.sleep(max(0, next_delay - overhead))
    time.sleep(0.3)
    next_delay = odgcc.next_frame()
#    next_delay = odgp.next_frame()

splash.pop()
try:
    board.DISPLAY.root_group = displayio.CIRCUITPYTHON_TERMINAL
except:
    #display.root_group = displayio.CIRCUITPYTHON_TERMINAL
    display.show(None)
