#   ___ ___     _____   _________   ____  __.  __           ___.    .__             __   
#  /   |   \   /  _  \  \_   ___ \ |    |/ _|_/  |_ _____   \_ |__  |  |    ____  _/  |_ 
# /    ~    \ /  /_\  \ /    \  \/ |      <  \   __\\__  \   | __ \ |  |  _/ __ \ \   __\
# \    Y    //    |    \\     \____|    |  \  |  |   / __ \_ | \_\ \|  |__\  ___/  |  |  
#  \___|_  / \____|__  / \______  /|____|__ \ |__|  (____  / |___  /|____/ \___  > |__|  
#        \/          \/         \/         \/            \/      \/            \/        
#
# Thank you for agreeing to hack on this HACKtablet!
# I hope you enjoy exploring what you can achieve 
# this touchscreen CircuitPython device.
# 
#                                        - kmatch 
#
# Resources
# ---------
# Background on the hardware, custom PCB schematic and layout:
# https://hackaday.io/project/185831-hacktablet-crestron-tss-752-teardown-rebuild
#
# Datasheet for the touchscreen display panel:
# https://cdn.hackaday.io/files/1858317950593504/ET070001DM6_Ver.6_20110520_201801111821.pdf
#
# The main github issue on the CircuitPython repository:
# https://github.com/adafruit/circuitpython/issues/6049
#
# The technical manual for the ESP32-S3, including information about its LCD peripheral:
# https://www.espressif.com/sites/default/files/documentation/esp32-s3_technical_reference_manual_en.pdf
#
# foamyguy's CircuitPython fork (the objective is to get this merged into the CircuitPython main repository)
# The latest updates could eventually be put somewhere else, but at least this is a start.
# https://github.com/foamyguy/circuitpython/tree/foamy_tablet


import time
import busio
import board
#import adafruit_focaltouch
import displayio
import dotclockframebuffer
import framebufferio
import terminalio
from rainbowio import colorwheel
import adafruit_imageload
from pydos_ui import Pydos_ui


#SCL_pin = board.IO41  # set to a pin that you want to use for SCL
#SDA_pin = board.IO42  # set to a pin that you want to use for SDA

#IRQ_pin = board.IO40  # select a pin to connect to the display's interrupt pin ("IRQ") - not used in this code


#i2c = busio.I2C(SCL_pin, SDA_pin)


#ft = adafruit_focaltouch.Adafruit_FocalTouch(i2c, debug=False)
ft = Pydos_ui.ts

displayio.release_displays()


# load the background "HACKtablet" image

hack_bitmap, hack_palette = adafruit_imageload.load("HACKtablet.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)

hack_tilegrid = displayio.TileGrid(hack_bitmap, 
                    pixel_shader=hack_palette,
                    )


# setup the display

# create the list of 16 datapins (RGB565)

# initialize the dotclock display.  
# Feel free to tweak these settings and see what 
# happens/  It may cause glitching depending upon what
# settings you use.

print('Creating DotClockFrameBuffer.')


#fb=dotclockdisplay.DotClockFramebuffer(
#    width=800, height=480, 
#    hsync=board.IO47, vsync=board.IO48,
#    de=board.IO45,
#    pclock=board.IO21,
#    data_pins=datapin_list,
#    pclock_frequency= 24*1000*1000, # 24000000 # 24 MHz
#    hsync_back_porch = 100, # 100
#    hsync_front_porch = 40, # 40
#    hsync_pulse_width = 5,  # 5
#    vsync_back_porch = 25,  # 25
#    vsync_front_porch = 10, # 10
#    vsync_pulse_width = 1,  # 1
#    pclock_active_neg = 1,  # 1
#    bounce_buffer_size_px = 1000 * 15, # 15000
#    )

fb=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS)


print('Creating DotClockFrameBuffer Display.')

display=framebufferio.FramebufferDisplay(fb)
#        force_refresh=True,
#        )

display.root_group = None
display.refresh()


# create the bouncing square

box_size=50
corner_box_size=20
width=display.width
height=display.height

color_count=0 

# Create a bitmap with two colors
box_bitmap = displayio.Bitmap(box_size, box_size, 2)
# Create a two color palette
box_palette = displayio.Palette(2)
box_palette[0] = 0x000000
box_palette[1] = colorwheel(color_count)

box_bitmap.fill(1)
box_tilegrid = displayio.TileGrid(box_bitmap, pixel_shader=box_palette)

x_velocity = 2
y_velocity = 2


# Create a Group to hold the bouncing square
box_group = displayio.Group()
box_group.append(box_tilegrid)

box_group.x=10
box_group.y=10

# Create the overall main display group

main_group = displayio.Group()

main_group.append(hack_tilegrid)
main_group.append(box_group)

display.root_group = main_group

while True:

    if ft.touched:
        ts = ft.touches # This touch controller can measure up to 10 points!
        # print(ts)
        if ts != []: # Double check that the touchpoint list isn't empty.
            point = ts[0] # Just use the first touch point
            if point['x'] > 740 and point['y'] < 75:
                display.root_group = displayio.CIRCUITPYTHON_TERMINAL
                break
            # print(point)
            (box_group.x, box_group.y) = (point["x"], point["y"])

    if ((box_group.x + box_size) > width-5) or (box_group.x < 5):
        x_velocity *= -1
        # print ("changed direction x")
    if ((box_group.y + box_size) > height-5) or (box_group.y < 5):
        y_velocity *= -1
        # print ("changed direction y")

    # update the bouncing box color
    box_palette[1] = colorwheel(color_count)
    color_count += 1

    (box_group.x, box_group.y) = (box_group.x + x_velocity, box_group.y + y_velocity)

    time.sleep(0.0001)
