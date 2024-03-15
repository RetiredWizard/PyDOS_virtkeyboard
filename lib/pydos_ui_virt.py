from sys import stdin
from os import getenv
from storage import getmount

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
elif board.board_id == "adafruit_huzzah32_breakout":
    # Using Huzzah32 Breakout firmware for Cheap Yellow Display boards
    import adafruit_ili9341
    import fourwire
    from pydos_xpt2046 import Touch as Touch_Screen
else:
    try:
        import adafruit_ili9341
        import fourwire
        from adafruit_tsc2007 import TSC2007 as Touch_Screen
    except:
        raise RuntimeError("Unknown/Unsupported Touchscreen")

import digitalio
from microcontroller import pin

class PyDOS_UI:
    
    def __init__(self):
        self.scrollable = False
        # Setup Touch detection
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

        i2c = None
        if 'I2C' in dir(board):
            i2c = board.I2C()
        elif 'SCL' in dir(board):
            i2c = busio.I2C(board.SCL, board.SDA)
        else:
            ts_spi = busio.SPI(board.IO25,board.IO32,board.IO39)
            ts_cs = board.IO33
        if RES_pin is not None:
            self.ts = Touch_Screen(i2c, RES_pin, debug=False)
        else:
            if i2c is not None:
                try:
                    self.ts = Touch_Screen(i2c, debug=False)
                except:
                    self.ts = Touch_Screen(i2c)
            else:
                self.ts = Touch_Screen(ts_spi,cs=ts_cs)

        self.commandHistory = [""]
        self.touches = []
        self._touched = False

        self.SHIFTED = False
        self.CAPLOCK = False

# Adafruit 2.4" TFT FeatherWing using TSC2007 touch Y dimension is reversed
        self._swapYdir = False

        displayio.release_displays()

        if 'TFT_PINS' in dir(board):
            sWdth = getenv('PYDOS_TS_WIDTH')
            if sWdth == None:
                if board.board_id == "makerfabs_tft7":
                    sWdth = int(input("What is the resolution Width of the touch screen? (1024/800/...): "))
                else:
                    sWdth = board.TFT_TIMINGS['width']
                self.updateTOML("PYDOS_TS_WIDTH",str(sWdth))

            if sWdth == 1024 and "TFT_TIMINGS1024" in dir(board):
                disp_bus=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS1024)
            else:
                disp_bus=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS)
            self.display=framebufferio.FramebufferDisplay(disp_bus)
        else:
            self._swapYdir = True  # TSC2007
            if 'D10' in dir(board):
                cmd = board.D10
                cs = board.D9
                rst = board.D6
                bl = None
            if 'SPI' in dir(board):
                spi = board.SPI()
            elif 'SCK' in dir(board):
                spi = busio.SPI(clock=board.SCK,MOSI=board.MOSI,MISO=board.MISO)
            else:
                spi = busio.SPI(board.IO14,board.IO13,board.IO12)
                cmd = board.IO2
                cs = board.IO15
                rst = None
                bl = board.IO21
                self._swapYdir = False
            disp_bus=fourwire.FourWire(spi,command=cmd,chip_select=cs,reset=rst)
            self.display=adafruit_ili9341.ILI9341(disp_bus,width=320,height=240,backlight_pin=bl)

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
        self._calibKBfact = (self._ts_calib[3]-self._ts_calib[1]+1)/self.display.height
        self._calibKBadj = self._ts_calib[1] - 1
        scrCalibX = self.display.width/1024
        scrCalibY = self.display.height/600

        self._kbd_row = self.display.height - round(scrCalibY*330)
        keyboard_bitmap,keyboard_palette = adafruit_imageload.load \
            ("/lib/keyboard"+str(self.display.width)+".bmp", \
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
        self._keyedTxt.y = self.display.height - round(scrCalibY*355)
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

        self._row1Keys = [980,843,780,718,655,593,530,467,404,342,279,216,154,92,-99999]
        self._row1Keys = [self._calibX(x) for x in self._row1Keys]
        self._row1Letters = ['D','\x08','=','-','0','9','8','7','6','5','4','3','2','1','`']
        self._row1Uppers = ['\x04','\x08','+','_',')','(','*','&','^','%','$','#','@','!','~']
        self._row2Keys = [880,818,755,692,629,567,504,441,378,316,253,190,127,-99999]
        self._row2Keys = [self._calibX(x) for x in self._row2Keys]
        self._row2Letters = ['\\',']','[','p','o','i','u','y','t','r','e','w','q','\x09']
        self._row2Uppers = ['|','}','{']
        self._row3Keys = [980,825,763,700,637,574,511,448,385,323,260,197,134,-99999]
        self._row3Keys = [self._calibX(x) for x in self._row3Keys]
        self._row3Letters = ['A','\n',"'",';','l','k','j','h','g','f','d','s',"a",'L']
        self._row3Uppers = ['\x01','\n','"',':']
        self._row4Keys = [790,727,664,602,539,476,413,351,288,225,162,-99999]
        self._row4Keys = [self._calibX(x) for x in self._row4Keys]
        self._row4Letters = ['S','/','.',',','m','n','b','v','c','x','z','S']
        self._row4Uppers = ['S','?','>','<']
        self._row5Keys = [980,880,650,280,155,-99999]
        self._row5Keys = [self._calibX(x) for x in self._row5Keys]
        self._row5Letters = ['B','X','',' ','','\x1b']

    _calibX = lambda self,x: round(x*self._calibXfact) + self._calibXadj
    _calibY = lambda self,y: round(y*self._calibYfact) + self._calibYadj
    _calibKB = lambda self,y: round(y*self._calibKBfact) + self._calibKBadj

    def updateTOML(self,tomlvar,tomlval):
        if getmount('/').readonly:
            print("***READONLY*** filesystem")
            print(tomlvar+" not set to",tomlval)
        else:
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

            try:
                intval = (type(int(tomlval)) == int)
            except:
                intval = False

            with open('/settings.toml','w') as envfile:
                for param in envline:
                    if param != tomlvar:
                        envfile.write(param+"="+envline.get(param,"")+"\n")
                if intval:
                    envfile.write(tomlvar+'='+str(tomlval))
                else:
                    envfile.write(tomlvar+'="'+tomlval+'"')

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

        self.display.root_group = calib_scr

        smallest_X = self.display.width
        smallest_Y = self.display.height
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

        block.x = self.display.width - 10
        block.y = self.display.height - 10

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

        self.updateTOML('PYDOS_TS_CALIB',"(%s,%s,%s,%s)"%(smallest_X,smallest_Y,largest_X,largest_Y))

        self.display.root_group=displayio.CIRCUITPYTHON_TERMINAL
        print("Screen Calibrated: (%s,%s) (%s,%s)" % (smallest_X,smallest_Y,largest_X,largest_Y))
        return (smallest_X,smallest_Y,largest_X,largest_Y)

    def get_screensize(self):
        return (
            round(self.display.height/(terminalio.FONT.bitmap.height*displayio.CIRCUITPYTHON_TERMINAL.scale))-1,
            round(self.display.width/((terminalio.FONT.bitmap.width/95)*displayio.CIRCUITPYTHON_TERMINAL.scale))-2
        )

    def _identifyLocation(self,xloc,yloc):
        kbd_row = self._calibKB(self._kbd_row)
        if xloc > self._calibX(980) and yloc < self._calibY(85):
            retKey = "\n"
        elif yloc < kbd_row+self._calibY(11):
            if xloc > self._calibX(980):
                retKey = "C"
            else:
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
        elif retKey == 'L':
            self.CAPLOCK = not self.CAPLOCK
            self.SHIFTED = self.CAPLOCK
            retKey = ''
        elif retKey in 'XABCD' and retKey != "":
            retKey = '\x00\x01\x02\x03\x04'['XABCD'.find(retKey)]

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

    def virt_touched(self):
        # Maximum multi-touch = 10 (focaltouch) greater values invalid==False
        if self.ts.touched and self.ts.touched<=10:
            if "touches" in dir(self.ts):
                self.touches = self.ts.touches
                self._touched = True
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

        self._touched = False
        self.touches = []
        return False

    def read_keyboard(self,num,holdkeyb=False,keys="",ec=None):
        # holdkeyb = True keeps the virtual keyboard displayed between calls
        #            Until an enter or termination key is entered in read_virtKeyboard
        if not self._touched:
            self._touched = self.virt_touched()
        if self._touched:
            if self.touches[0]['x'] > self._calibX(980) and self.touches[0]['y'] < self._calibY(85):
                if self.display.root_group == self._kbd_group:
                    self._keyedTxt.text = ""
                    self.display.root_group = displayio.CIRCUITPYTHON_TERMINAL
                retVal = '\n'
            else:
                retVal = self.read_virtKeyboard(num,keys,ec)
                if not holdkeyb:
                    self._keyedTxt.text = ""
                    self.display.root_group = displayio.CIRCUITPYTHON_TERMINAL
                if retVal == "":
                    retVal = '\n'
        else:
            retVal = stdin.read(num)

        return retVal
    
    def read_virtKeyboard(self,num=0,keys="",ec=None):

        loop = True

        if self.display.root_group != self._kbd_group:
            self.display.root_group=self._kbd_group
            while self.virt_touched():
                pass
            self._touched = False
            #if num == 1:
            #    loop = False

        self.SHIFTED = self.CAPLOCK
        self._shftIndicator.text = ('SHIFT' if self.SHIFTED else '')
        self._capsIndicator.text = ('LOCK' if self.CAPLOCK else '')

        keyString = ""
        keysPressed = 0
        while loop:
            if not self._touched:
                self._touched = self.virt_touched()
            if self._touched:
                point = self.touches[0]
                pressedKey = self._identifyLocation(point["x"],point["y"])
                
                if pressedKey == '\x08':
                    keyString = keyString[:-1]
                    self._keyedTxt.text = keyString
                    if num != 1:
                        pressedKey = ''
                elif pressedKey == '\n':
                    if num == 0:
                        pressedKey = ''
                    loop = False
                elif pressedKey == '\x00':
                    keyString = ""
                    loop = False

                keyString += pressedKey
                    
                self._shftIndicator.text = ('SHIFT' if self.SHIFTED else '')
                self._capsIndicator.text = ('LOCK' if self.CAPLOCK else '')
                if len(pressedKey) != 0:
                    if num != 0 and keys != "" and ec != None:
                        txt = keys[:ec]+keyString+keys[ec:]
                        if pressedKey == '\x08':
                            txt = txt[:ec-1]+txt[ec:]
                    else:
                        txt = keyString

                    for i in range(8):
                        txt = txt.replace('\x1b\n\x00\x01\x02\x03\x04\x08'[i],"E"[i:])

                    self._keyedTxt.text = txt

                    keysPressed += 1
                    if num > 0 and keysPressed >= num:
                        loop = False
                    
                while self.virt_touched():
                    pass
                self._touched = False

            time.sleep(0.0001)

        if num == 0 or keyString== "" or keyString[-1:] == '\n' or keyString == '\x00':
            self._keyedTxt.text = ""
            self.display.root_group = displayio.CIRCUITPYTHON_TERMINAL
        return keyString

Pydos_ui = PyDOS_UI()

def input(disp_text=None):

    if disp_text != None:
        print(disp_text,end="")

    histPntr = len(Pydos_ui.commandHistory)

    keys = ''
    editCol = 0
    loop = True
    arrow = ''
    onLast = True
    onFirst = True
    blink = True
    timer = time.time()
    saved = timer-1

    while loop:
        #print(editCol,keys)
        if arrow == 'A' or arrow == 'B':
            if len(Pydos_ui.commandHistory) > 0:
                print(('\x08'*(editCol))+(" "*(len(keys)+1))+('\x08'*(len(keys)+1)),end="")

                if arrow == 'A':
                    histPntr -= 1
                else:
                    histPntr += 1

                histPntr = histPntr % len(Pydos_ui.commandHistory)
                print(Pydos_ui.commandHistory[histPntr],end="")
                keys = Pydos_ui.commandHistory[histPntr]
                editCol = len(keys)
                if editCol == 0:
                    onFirst = True
                else:
                    onFirst = False
        elif arrow == 'D':
            if len(keys) > editCol:
                print(keys[editCol:editCol+1]+"\x08",end="")
            elif editCol == len(keys):
                print(" \x08",end="")

            editCol = max(0,editCol-1)
            if editCol > 0:
                print('\x08',end="")
                onLast = False
            elif editCol == 0:
                if not onFirst:
                    print('\x08',end="")
                    onFirst = True
        elif arrow == 'C':
            if len(keys) > editCol:
                print(keys[editCol:editCol+1]+"\x08",end="")

            editCol += 1
            editCol = min(len(keys),editCol)
            if editCol < len(keys):
                print(keys[editCol-1:editCol],end="")
                onFirst = False
            elif editCol == len(keys):
                if not onLast:
                    print(keys[editCol-1:],end="")
                    onLast = True

        arrow = ""

        if Pydos_ui.serial_bytes_available():
            if Pydos_ui.uart_bytes_available():
                keys = keys[:editCol]+stdin.read(1)+keys[editCol:]
                editCol += 1
                if keys[editCol-1:editCol] == '\x1b':
                    keys = keys[:editCol-1]+keys[editCol:]
                    arrow = stdin.read(2)[1]
                    # arrow keys = up:[A down:[B right:[C left:[D
            else:
                keys = keys[:editCol]+Pydos_ui.read_keyboard(1,True,keys,editCol)+keys[editCol:]
                editCol += 1
                if keys[editCol-1:editCol] in '\x01\x02\x03\x04':
                    arrow = 'ABCD'['\x01\x02\x03\x04'.find(keys[editCol-1:editCol])]
                    keys = keys[:editCol-1]+keys[editCol:]

            if arrow != "":
                editCol -= 1
            elif keys[editCol-1:editCol] in ['\x08','\x7f']:
                keys = keys[:max(0,editCol-2)]+keys[editCol:]
                if editCol > 1:
                    print(('\x08'*(editCol-1))+keys+'  \x08\x08',end="")
                    editCol = max(0,editCol-2)
                    if editCol < len(keys):
                        print("\x08"*(len(keys)-editCol),end="")
                else:
                    editCol -= 1
                    onFirst = True
            elif keys[editCol-1:editCol] == '\x00':
                if editCol > 1:
                    print(('\x08'*(editCol-1))+(' '*(len(keys)+2))+('\x08'*(len(keys)+2)),end="")
                keys = ''
                loop = False
            elif len(keys[editCol-1:editCol]) > 0 and keys[editCol-1:editCol] in '\n\r':
                if len(keys) > editCol:
                    print(keys[editCol:editCol+1]+"\x08",end="")
                elif editCol == len(keys):
                    print(" \x08",end="")
                keys = keys[:editCol-1]+keys[editCol:]
                if keys.strip() != "":
                    Pydos_ui.commandHistory.append(keys)
                    if len(Pydos_ui.commandHistory) > 10:
                        Pydos_ui.commandHistory.pop(1)
                    histPntr = len(Pydos_ui.commandHistory)
                print()
                loop = False
            else:
                onFirst = False
                print(keys[editCol-1:],end="")
                if len(keys[editCol-1:]) > 1:
                    print(" \x08",end="")
                if editCol < len(keys):
                    print("\x08"*(len(keys)-editCol),end="")

        if loop and Pydos_ui.display.root_group != displayio.CIRCUITPYTHON_TERMINAL:
            if time.time() != timer:
                blink = not blink
                timer = time.time()

            if timer != saved:
                saved = timer
                if blink:
                    Pydos_ui._keyedTxt.text = keys[:editCol]+"_"+keys[editCol+1:]
                else:
                    Pydos_ui._keyedTxt.text = keys

    return keys
