from sys import stdin,stdout,implementation
from os import getenv

import board
import displayio
import framebufferio
import adafruit_imageload
import terminalio
import vectorio
from adafruit_display_text import bitmap_label as label
import busio
import time
from supervisor import runtime

if board.board_id == "makerfabs_tft7":
    import dotclockframebuffer
    from gt911_touch import GT911_Touch as Touch_Screen
elif board.board_id == "espressif_esp32s3_devkitc_1_n8r8_hacktablet":
    import dotclockframebuffer
    from adafruit_focaltouch import Adafruit_FocalTouch as Touch_Screen
else:
    try:
        import adafruit_ili9341
        from adafruit_tsc2007 import TSC2007 as Touch_Screen
    except:
        raise RuntimeError("Unknown/Unsupported Touchscreen")

import digitalio
from microcontroller import pin

class PyDOS_UI:
    
    def __init__(self):
        # Setup Touch detection
        SCL_pin = board.SCL
        SDA_pin = board.SDA
        if 'TOUCH_RESET' in dir(board):
            RES_pin = digitalio.DigitalInOut(board.TOUCH_RESET)
        else:
            RES_pin = None

        # Makerfabs board ties IRQ to ground
        # IRQ not used in this version but possibly could improve
        # GT911 performance on boards that have it connected to the panel
        #if 'TOUCH_IRQ' in dir(board):
        #    IRQ_PIN = digitalio.DigitalInOut(board.TOUCH_IRQ)
        #else:
        #    IRQ_PIN = None

        if 'I2C' in dir(board):
            i2c = board.I2C()
        else:
            i2c = busio.I2C(SCL_pin, SDA_pin)
        if RES_pin is not None:
            self.ts = Touch_Screen(i2c, RES_pin, debug=False)
        else:
            try:
                self.ts = Touch_Screen(i2c, debug=False)
            except:
                self.ts = Touch_Screen(i2c)
        self.touches = []
        self._touched = False

        self.SHIFTED = False
        self.CAPLOCK = False

# Adafruit 2.4" TFT FeatherWing using TSC2007 touch Y dimension is reversed
        self._swapYdir = False

        displayio.release_displays()

        if 'TFT_PINS' in dir(board):
            disp_bus=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS)
            self._display=framebufferio.FramebufferDisplay(disp_bus)
        else:
            if 'SPI' in dir(board):
                spi = board.SPI()
            else:
                spi = busio.SPI(clock=board.SCK,MOSI=board.MOSI,MISO=board.MISO)
            disp_bus=displayio.FourWire(spi,command=board.D10,chip_select=board.D9, \
                reset=board.D6)
            self._display=adafruit_ili9341.ILI9341(disp_bus,width=320,height=240)
            self._swapYdir = True  # TSC2007

        ts_calib = getenv('PYDOS_TS_CALIB')
        try:
            self._ts_calib = eval(ts_calib)
        except:
            self._ts_calib = self.calibrate()
        if len(self._ts_calib) != 4:
            self._ts_calib = self.calibrate()
        self._calibXfact = (self._ts_calib[2]-self._ts_calib[0]+1)/1024
        self._calibXadj = self._ts_calib[0] - 1
        self._calibYfact = (self._ts_calib[3]-self._ts_calib[1]+1)/600
        self._calibYadj = self._ts_calib[1] - 1
        self._calibKBfact = (self._ts_calib[3]-self._ts_calib[1]+1)/self._display.height
        self._calibKBadj = self._ts_calib[1] - 1
        scrCalibX = self._display.width/1024
        scrCalibY = self._display.height/600

        self._kbd_row = self._display.height - round(scrCalibY*330)
        keyboard_bitmap,keyboard_palette = adafruit_imageload.load \
            ("/lib/keyboard"+str(self._display.width)+".bmp", \
            bitmap=displayio.Bitmap,palette=displayio.Palette)
        htile=displayio.TileGrid(keyboard_bitmap,pixel_shader=keyboard_palette)
        htile.x=round(scrCalibX*20)
        htile.y=self._kbd_row
        if self._swapYdir:
            htile.y += 30
        self._kbd_group = displayio.Group()
        self._kbd_group.append(htile)

        font = terminalio.FONT
        color = 0xFFFFFF
        self._keyedTxt = label.Label(font, text="", color=color)
        self._keyedTxt.x = round(scrCalibX*20)
        self._keyedTxt.y = self._display.height - round(scrCalibY*355)
        self._keyedTxt.scale = 2
        self._kbd_group.append(self._keyedTxt)
        
        self._shftIndicator = label.Label(font,text="",color=0x00FF00)
        self._shftIndicator.x = round(scrCalibX*20)
        self._shftIndicator.y = round(scrCalibY*20)
        self._shftIndicator.scale = 2
        self._kbd_group.append(self._shftIndicator)
        self._capsIndicator = label.Label(font,text="",color=0x00FF00)
        self._capsIndicator.x = round(scrCalibX*105)
        self._capsIndicator.y = round(scrCalibY*20)
        self._capsIndicator.scale = 2
        self._kbd_group.append(self._capsIndicator)

        #self._row1Keys = [665,615,565,515,465,415,365,315,265,215,165,115,68,-99999]
        #self._row1Keys = [600,555,510,465,420,375,330,285,240,195,150,105,60,-99999]
        self._row1Keys = [843,780,718,655,593,530,467,404,342,279,216,154,92,-99999]
        self._row1Keys = [self._calibX(x) for x in self._row1Keys]
        self._row1Letters = ['\x08','=','-','0','9','8','7','6','5','4','3','2','1','`']
        self._row1Uppers = ['\x08','+','_',')','(','*','&','^','%','$','#','@','!','~']
        #self._row2Keys = [695,645,595,545,495,445,395,345,295,245,195,145,95,-99999]
        #self._row2Keys = [615,570,525,485,440,395,350,305,260,215,175,130,80,-99999]
        self._row2Keys = [880,818,755,692,629,567,504,441,378,316,253,190,127,-99999]
        self._row2Keys = [self._calibX(x) for x in self._row2Keys]
        self._row2Letters = ['\\',']','[','p','o','i','u','y','t','r','e','w','q','\x09']
        self._row2Uppers = ['|','}','{']
        #self._row3Keys = [650,600,550,500,450,400,350,300,250,200,150,100,-99999]
        #self._row3Keys = [590,545,500,455,410,365,320,275,230,185,140,95,-99999]
        self._row3Keys = [825,763,700,637,574,511,448,385,323,260,197,134,-99999]
        self._row3Keys = [self._calibX(x) for x in self._row3Keys]
        self._row3Letters = ['\n',"'",';','l','k','j','h','g','f','d','s',"a",'C']
        self._row3Uppers = ['\n','"',':']
        #self._row4Keys = [635,585,535,485,435,385,335,285,235,185,135,-99999]
        #self._row4Keys = [565,520,475,430,385,340,295,250,205,160,115,-99999]
        self._row4Keys = [790,727,664,602,539,476,413,351,288,225,162,-99999]
        self._row4Keys = [self._calibX(x) for x in self._row4Keys]
        self._row4Letters = ['S','/','.',',','m','n','b','v','c','x','z','S']
        self._row4Uppers = ['S','?','>','<']
        #self._row5Keys = [710,520,220,125,-99999]
        #self._row5Keys = [640,460,200,110,-99999]
        self._row5Keys = [880,650,280,155,-99999]
        self._row5Keys = [self._calibX(x) for x in self._row5Keys]
        self._row5Letters = ['X','',' ','','\x1b']

    _calibX = lambda self,x: round(x*self._calibXfact) + self._calibXadj
    _calibY = lambda self,y: round(y*self._calibYfact) + self._calibYadj
    _calibKB = lambda self,y: round(y*self._calibKBfact) + self._calibKBadj

    def calibrate(self):

        self._ts_calib = []

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

        pal = displayio.Palette(1)
        pal[0] = 0xFFFFFF
        block = vectorio.Rectangle(pixel_shader=pal, width=10, height=10, x=0, y=0)
        block.x = 0
        block.y = 0

        calib_scr = displayio.Group()
        calib_scr.append(calibTxt1)
        calib_scr.append(calibTxt2)
        calib_scr.append(block)
        calib_scr.append(calibCount)

        self._display.root_group = calib_scr

        smallest_X = self._display.width
        smallest_Y = self._display.height
        largest_X = 1
        largest_Y = 1

        while count > 0:
            if self.virt_touched():
                point = self.touches[0]
                smallest_X = min(smallest_X,point["x"])
                if self._swapYdir:
                    largest_Y = max(largest_Y,point["y"])
                else:
                    smallest_Y = min(smallest_Y,point["y"])
                count -= 1
                calibCount.text=str(count)

                while self.virt_touched():
                    pass

        #smallest_X -= 5
        #smallest_Y -= 5

        block.x = self._display.width - 10
        block.y = self._display.height - 10

        count = 5
        calibCount.text=str(count)

        while count > 0:
            if self.virt_touched():
                point = self.touches[0]
                largest_X = max(largest_X,point["x"])
                if self._swapYdir:
                    smallest_Y = min(smallest_Y,point["y"])
                else:
                    largest_Y = max(largest_Y,point["y"])
                count -= 1
                calibCount.text=str(count)

                while self.virt_touched():
                    pass


        #largest_X += 5
        #largest_Y += 5

        envline = {}
        defaults = True
        try:
            envfile = open('/settings.toml')
        except:
            defaults = False

        if defaults:
            for line in envfile:
                try:
                    envline[line.split('=')[0].strip()] = line.split('=')[1].strip()
                except:
                    pass
            envfile.close()

        with open('/settings.toml','w') as envfile:
            for param in envline:
                if param != 'PYDOS_TS_CALIB':
                    envfile.write(param+"="+envline.get(param,"")+"\n")
            envfile.write('PYDOS_TS_CALIB="(%s,%s,%s,%s)"'%(smallest_X,smallest_Y,largest_X,largest_Y))

        self._display.root_group=displayio.CIRCUITPYTHON_TERMINAL
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
        if not self._touched:
            self._touched = self.virt_touched()
        if self._touched:
            if self.touches[0]['x'] > self._calibX(self._display.width*.925) and self.touches[0]['y'] < self._calibY(85):
                retVal = '\n'
            else:
                retVal = self.read_virtKeyboard(num)
                if retVal == "":
                    retVal = '\n'
        else:
            retVal = stdin.read(num)

        return retVal
    
    def get_screensize(self):
        #return (round(self._display.height*.04),round(self._display.width*.0817))
        return (
            round(self._display.height/(terminalio.FONT.bitmap.height*displayio.CIRCUITPYTHON_TERMINAL.scale))-1,
            round(self._display.width/((terminalio.FONT.bitmap.width/95)*displayio.CIRCUITPYTHON_TERMINAL.scale))-1
        )

    def _identifyLocation(self,xloc,yloc):
        kbd_row = self._calibKB(self._kbd_row)
        if xloc > self._calibX(self._display.width*.925) and yloc < self._calibY(85):
            retKey = "\n"
        elif yloc < kbd_row+self._calibY(11):
            retKey = ""
        elif yloc > kbd_row+self._calibY(255):    # 435
            retKey = self._row5Letters[next(a[0] for a in enumerate(self._row5Keys) if a[1]<=xloc)]
        elif yloc >= kbd_row+self._calibY(197):   # 390
            retKey = self._row4Letters[next(a[0] for a in enumerate(self._row4Keys) if a[1]<=xloc)]
        elif yloc >= kbd_row+self._calibY(132):   # 345
            retKey = self._row3Letters[next(a[0] for a in enumerate(self._row3Keys) if a[1]<=xloc)]
        elif yloc >= kbd_row+self._calibY(75):    # 300
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
            if "touches" in dir(self.ts):
                self.touches = self.ts.touches
            else:
                self.touches = [self.ts.touch]
                if self.touches[0]["pressure"] >= 75:
                    if len(self._ts_calib) == 4:
                        transformedTouch = [{
                            'x': self.touches[0]["y"],
                            'y': (self._ts_calib[3]-self.touches[0]["x"]) + self._ts_calib[1],
                            'pressure': self.touches[0]["pressure"]
                        }]
                    else:
                        transformedTouch = [{
                            'x': self.touches[0]["y"],
                            'y': self.touches[0]["x"],
                            'pressure': self.touches[0]["pressure"]
                        }]
                    self.touches = transformedTouch
                    self._touched = True
                else:
                    self.touches = []
                    self._touched = False
            if self.touches != []:
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
            if Pydos_ui.touches[0]['x'] > Pydos_ui._calibX(Pydos_ui._display.width*.925) and \
                Pydos_ui.touches[0]['y'] < Pydos_ui._calibY(85):
                keys = ''
            else:
                keys = Pydos_ui.read_virtKeyboard()
            print(keys)
            while Pydos_ui.virt_touched():
                pass
            break
        
    return keys
