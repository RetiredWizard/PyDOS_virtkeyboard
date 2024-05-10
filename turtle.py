import board
from adafruit_turtle import Color, turtle
import displayio
from os import getenv
try:
    from pydos_ui import Pydos_ui
except:
    Pydos_ui = None
try:
    from pydos_ui import input
except:
    pass
try:
    type(envVars)
except:
    envVars = {}

if 'display' in dir(Pydos_ui):
    display = Pydos_ui.display
elif '_display' in envVars.keys():
    display = envVars['_display']
elif 'DISPLAY' in dir(board):
    display = board.DISPLAY
else:
    try:
        import framebufferio
        import dotclockframebuffer
    except:
        import adafruit_ili9341

    displayio.release_displays()

    if 'TFT_PINS' in dir(board):
        sWdth = getenv('PYDOS_TS_WIDTH')
        if sWdth == None:
            if board.board_id == "makerfabs_tft7":
                sWdth = input("What is the resolution Width of the touch screen? (1024/800/...): ")
            else:
                sWdth = board.TFT_TIMINGS['width']
            if 'updateTOML' in dir(Pydos_ui):
                Pydos_ui.updateTOML("PYDOS_TS_WIDTH",str(sWdth))

        if sWdth == 1024 and "TFT_TIMINGS1024" in dir(board):
            disp_bus=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS1024)
        else:
            disp_bus=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS)
        display=framebufferio.FramebufferDisplay(disp_bus)
    else:
        if 'SPI' in dir(board):
            spi = board.SPI()
        else:
            spi = busio.SPI(clock=board.SCK,MOSI=board.MOSI,MISO=board.MISO)
        disp_bus=displayio.FourWire(spi,command=board.D10,chip_select=board.D9, \
            reset=board.D6)
        display=adafruit_ili9341.ILI9341(disp_bus,width=320,height=240)

turtle = turtle(display)
benzsize = min(display.width, display.height) * 0.5

print("Turtle time! Lets draw a rainbow benzene")

colors = (Color.RED, Color.ORANGE, Color.YELLOW, Color.GREEN, Color.BLUE, Color.PURPLE)

turtle.pendown()
start = turtle.pos()

for x in range(benzsize):
    turtle.pencolor(colors[x%6])
    turtle.forward(x)
    turtle.left(59)
input("Press Enter to continue...")
display.root_group = displayio.CIRCUITPYTHON_TERMINAL
