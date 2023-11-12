import board
from adafruit_turtle import Color, turtle
import displayio

try:
    from pydos_ui import input
except:
    pass

if 'DISPLAY' not in dir(board):
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
    display = board.DISPLAY

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