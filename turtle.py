import board
from adafruit_turtle import Color, turtle
try:
    from pydos_ui import input
except:
    pass

import framebufferio
import dotclockframebuffer
import displayio

displayio.release_displays()

fb=dotclockframebuffer.DotClockFramebuffer(**board.TFT,**board.TIMINGS800)
display = framebufferio.FramebufferDisplay(fb)


try:
	turtle = turtle(board.DISPLAY)
	benzsize = min(board.DISPLAY.width, board.DISPLAY.height) * 0.5
except:
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
