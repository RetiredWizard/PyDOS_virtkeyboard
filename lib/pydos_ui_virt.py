from sys import stdin,stdout,implementation

import board
import displayio
import dotclockframebuffer
import framebufferio
import adafruit_imageload
import terminalio
from adafruit_display_text import bitmap_label as label
import busio
import time
from supervisor import runtime

if board.board_id == "makerfabs_tft7":
    from gt911_touch import GT911_Touch as Touch_Screen
elif board.board_id == "espressif_esp32s3_devkitc_1_n8r8_hacktablet":
    from adafruit_focaltouch import Adafruit_FocalTouch as Touch_Screen

import digitalio
from microcontroller import pin

class PyDOS_UI:
    
    def __init__(self):
        # Setup Touch detection
        SCL_pin = board.SCL
        SDA_pin = board.SDA
        if 'TOUCH_RES' in dir(board):
            RES_pin = digitalio.DigitalInOut(board.TOUCH_RES)
        else:
            RES_pin = None

        # Makerfabs board ties IRQ to ground
        # IRQ not used in this version but possibly could improve
        # GT911 performance on boards that have it connected to the panel
        #if 'TOUCH_IRQ' in dir(board):
        #    IRQ_PIN = digitalio.DigitalInOut(board.TOUCH_IRQ)
        #else:
        #    IRQ_PIN = None

        self._calibrated = False
        self.i2c = busio.I2C(SCL_pin, SDA_pin)
        if RES_pin is not None:
            self.ts = Touch_Screen(self.i2c, RES_pin, debug=False)
        else:
            self.ts = Touch_Screen(self.i2c, debug=False)
        self.touches = []
        
        self.SHIFTED = False
        self.CAPLOCK = False

        displayio.release_displays()

        fb=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS)
        self._display=framebufferio.FramebufferDisplay(fb)

        self._kbd_row = self._display.height - 260
        keyboard_bitmap,keyboard_palette = adafruit_imageload.load("/lib/keyboard.bmp",bitmap=displayio.Bitmap,palette=displayio.Palette)
        htile=displayio.TileGrid(keyboard_bitmap,pixel_shader=keyboard_palette)
        htile.x=15
        htile.y=self._kbd_row
        self._kbd_group = displayio.Group()
        self._kbd_group.append(htile)

        font = terminalio.FONT
        color = 0xFFFFFF
        self._keyedTxt = label.Label(font, text="", color=color)
        self._keyedTxt.x = 15
        self._keyedTxt.y = self._display.height - 280
        self._keyedTxt.scale = 2
        self._kbd_group.append(self._keyedTxt)
        
        self._shftIndicator = label.Label(font,text="",color=0x00FF00)
        self._shftIndicator.x = 15
        self._shftIndicator.y = 15
        self._shftIndicator.scale = 2
        self._kbd_group.append(self._shftIndicator)
        self._capsIndicator = label.Label(font,text="",color=0x00FF00)
        self._capsIndicator.x = 90
        self._capsIndicator.y = 15
        self._capsIndicator.scale = 2
        self._kbd_group.append(self._capsIndicator)

        self._touched = False

        #self._row1Keys = [600,555,510,465,420,375,330,285,240,195,150,105,60,0]
        self._row1Keys = [665,615,565,515,465,415,365,315,265,215,165,115,68,0]
        self._row1Letters = ['\x08','=','-','0','9','8','7','6','5','4','3','2','1','`']
        self._row1Uppers = ['\x08','+','_',')','(','*','&','^','%','$','#','@','!','~']
        #self._row2Keys = [615,570,525,485,440,395,350,305,260,215,175,130,80,0]
        self._row2Keys = [695,645,595,545,495,445,395,345,295,245,195,145,95,0]
        self._row2Letters = ['\\',']','[','p','o','i','u','y','t','r','e','w','q','\x09']
        self._row2Uppers = ['|','}','{']
        #self._row3Keys = [590,545,500,455,410,365,320,275,230,185,140,95,0]
        self._row3Keys = [650,600,550,500,450,400,350,300,250,200,150,100,0]
        self._row3Letters = ['\n',"'",';','l','k','j','h','g','f','d','s',"a",'C']
        self._row3Uppers = ['\n','"',':']
        #self._row4Keys = [565,520,475,430,385,340,295,250,205,160,115,0]
        self._row4Keys = [635,585,535,485,435,385,335,285,235,185,135,0]
        self._row4Letters = ['S','/','.',',','m','n','b','v','c','x','z','S']
        self._row4Uppers = ['S','?','>','<']
        #self._row5Keys = [640,460,200,110,0]
        self._row5Keys = [710,520,220,125,0]
        self._row5Letters = ['X','',' ','','\x1b']

        ts_calib = self.calibrate()
        self._calibXfact = self._display.width/(ts_calib[2]-ts_calib[0]+1)
        self._calibXadj = ts_calib[0]
        self._calibYfact = self._display.height/(ts_calib[3]-ts_calib[1]+1)
        self._calibYadj = ts_calib[1]

    def calibrate(self):

        while self.virt_touched():
            pass

        font = terminalio.FONT
        color = 0xFFFFFF
        count = 5
        calibTxt1 = label.Label(font, text="Press the upper left/lower right box", color=color)
        calibTxt1.x = 50
        calibTxt1.y = 100
        calibTxt1.scale = 3
        calibTxt2 = label.Label(font, text="Repeatedly until the counter reaches 0", color=color)
        calibTxt2.x = 50
        calibTxt2.y = 140
        calibTxt2.scale = 3
        calibCount = label.Label(font, text=str(count), color=color)
        calibCount.x = 250
        calibCount.y = 200
        calibCount.scale = 4

        block = displayio.Shape(10,10)
        pal = displayio.Palette(2)
        pal[0] = 0xFFFFFF
        pal[1] = 0xFFFFFF
        for y in range(10):
            block.set_boundary(y,0,9)
        block_tile = displayio.TileGrid(block,pixel_shader=pal)
        block_tile.x = 0
        block_tile.y = 0

        calib_scr = displayio.Group()
        calib_scr.append(calibTxt1)
        calib_scr.append(calibTxt2)
        calib_scr.append(block_tile)
        calib_scr.append(calibCount)

        self._display.root_group = calib_scr

        smallest_X = self._display.width
        smallest_Y = self._display.height
        while count > 0:
            if self.virt_touched():
                point = self.touches[0]
                smallest_X = min(smallest_X,point["x"])
                smallest_Y = min(smallest_Y,point["y"])
                count -= 1
                calibCount.text=str(count)

                while self.virt_touched():
                    pass

        smallest_X -= 5
        smallest_Y -= 5

        block_tile.x = self._display.width - 10
        block_tile.y = self._display.height - 10

        count = 5
        calibCount.text=str(count)

        largest_X = 1
        largest_Y = 1
        while count > 0:
            if self.virt_touched():
                point = self.touches[0]
                largest_X = max(largest_X,point["x"])
                largest_Y = max(largest_Y,point["y"])
                count -= 1
                calibCount.text=str(count)

                while self.virt_touched():
                    pass

        largest_X += 5
        largest_Y += 5

        self._display.root_group=displayio.CIRCUITPYTHON_TERMINAL
        self._calibrated = True
        print("Screen Calibrated: (%s,%s) (%s,%s)" % (smallest_X,smallest_Y,largest_X,largest_Y))
        return (smallest_X,smallest_Y,largest_X,largest_Y)

    def serial_bytes_available(self):
        self._touched = False
        if self.virt_touched():
            retval = 1
            self._touched = True
        else:        
            # Does the same function as supervisor.runtime.serial_bytes_available
            retval = runtime.serial_bytes_available

        return retval


    def uart_bytes_available(self):
        # Does the same function as supervisor.runtime.serial_bytes_available
        retval = runtime.serial_bytes_available

        return retval


    def read_keyboard(self,num):
        if self.virt_touched() or self._touched:
            if self.touches[0]['x'] > self._display.width*.925 and self.touches[0]['y'] < 85:
                retVal = '\n'
            else:
                retVal = self.read_virtKeyboard(num)
                if retVal == "":
                    retVal = '\n'
        else:
            retVal = stdin.read(num)

        return retVal
    
    def get_screensize(self):
        return (round(self._display.height*.04),round(self._display.width*.0817))

    def _identifyLocation(self,xloc,yloc):
        if yloc < self._kbd_row+11:
            retKey = ""
        elif yloc > self._kbd_row+203:    # 435
            retKey = self._row5Letters[next(a[0] for a in enumerate(self._row5Keys) if a[1]<=xloc)]
        elif yloc >= self._kbd_row+148:   # 390
            retKey = self._row4Letters[next(a[0] for a in enumerate(self._row4Keys) if a[1]<=xloc)]
        elif yloc >= self._kbd_row+103:   # 345
            retKey = self._row3Letters[next(a[0] for a in enumerate(self._row3Keys) if a[1]<=xloc)]
        elif yloc >= self._kbd_row+57:    # 300
            retKey = self._row2Letters[next(a[0] for a in enumerate(self._row2Keys) if a[1]<=xloc)]
        else:                            # 255
            retKey = self._row1Letters[next(a[0] for a in enumerate(self._row1Keys) if a[1]<=xloc)]

        if retKey == 'S':
            if not self.SHIFTED:
                self.SHIFTED = True
            elif not self.CAPLOCK:
                self.SHIFTED = False
            retKey = ''
        elif retKey == 'C':
            self.CAPLOCK = not self.CAPLOCK
            self.SHIFTED = self.CAPLOCK
            retKey = ''
        elif retKey == 'X':
            retKey = '\x00'


        if self.CAPLOCK:
            self.SHIFTED = True
        
        if len(retKey) != 0 and self.SHIFTED:
            self.SHIFTED = self.CAPLOCK
                
            if retKey.upper() != retKey:
                retKey = retKey.upper()
            else:
                if retKey in self._row1Letters:
                    retKey = self._row1Uppers[self._row1Letters.index(retKey)]
                elif retKey in self._row2Letters[0:3]:
                    retKey = self._row2Uppers[self._row2Letters.index(retKey)]
                elif retKey in self._row3Letters[0:3]:
                    retKey = self._row3Uppers[self._row3Letters.index(retKey)]
                elif retKey in self._row4Letters[0:4]:
                    retKey = self._row4Uppers[self._row4Letters.index(retKey)]

        return retKey
    
    def virt_touched(self):
        if self.ts.touched:
            self.touches = self.ts.touches
            if self.touches != []:
                if self._calibrated:
                    for point in self.touches:
                        point['x'] = round(point['x']*self._calibXfact) - self._calibXadj
                        point['y'] = round(point['y']*self._calibYfact) - self._calibYadj

                return True

        if not self._touched:
            self.touches = []
        return False

    def read_virtKeyboard(self,num=0):
        self._display.root_group=self._kbd_group

        while self.virt_touched():
            pass

        self.SHIFTED = self.CAPLOCK
        self._shftIndicator.text = ('SHIFT' if self.SHIFTED else '')
        self._capsIndicator.text = ('LOCK' if self.CAPLOCK else '')

        keyString = ""
        keysPressed = 0
        while True:
            if self.virt_touched():
                point = self.touches[0]
                #print(point)
                pressedKey = self._identifyLocation(point["x"],point["y"])
                
                if pressedKey == '\x08':
                    keyString = keyString[:-1]
                    self._keyedTxt.text = keyString
                    pressedKey = ''
                elif pressedKey == '\n':
                    break
                elif pressedKey == '\x00':
                    keyString = ""
                    break
                keyString += pressedKey
                    
                self._shftIndicator.text = ('SHIFT' if self.SHIFTED else '')
                self._capsIndicator.text = ('LOCK' if self.CAPLOCK else '')
                if len(pressedKey) != 0:
                    self._keyedTxt.text = keyString.replace('\x1b',"E")
                    keysPressed += 1
                    if num > 0 and keysPressed >= num:
                        break
                    
                while self.virt_touched():
                    pass

            time.sleep(0.0001)

        #while len(self._kbd_group) > 1:
        #    self._kbd_group.pop()
        self._keyedTxt.text = ""
        self._display.root_group = displayio.CIRCUITPYTHON_TERMINAL
        return keyString

Pydos_ui = PyDOS_UI()

def input(disp_text=None):

    if disp_text != None:
        print(disp_text,end="")
        
    keys = ''
    while True:
        if Pydos_ui.uart_bytes_available():
            done = False
            while Pydos_ui.uart_bytes_available():
                keys += stdin.read(1)
                if keys[-1] != '\x08':
                    print(keys[-1],end="")
                else:
                    if len(keys) > 1:
                        print('\x08 \x08',end="")
                    keys = keys[:-2]

                if keys[-1:] == '\n':
                    keys = keys[:-1]
                    done = True
                    break
            if done:
                break
        elif Pydos_ui.virt_touched():
            if Pydos_ui.touches[0]['x'] > 740 and Pydos_ui.touches[0]['y'] < 75:
                keys = ''
            else:
                keys = Pydos_ui.read_virtKeyboard()
            print(keys)
            while Pydos_ui.virt_touched():
                pass
            break
        
    return keys
