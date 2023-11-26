import board
import digitalio
# https://github.com/RetiredWizard/PyDOS_virtkeyboard/blob/main/lib/gt911_touch.py
from gt911_touch import GT911_Touch


ts = GT911_Touch(board.I2C(), digitalio.DigitalInOut(board.TOUCH_RESET), debug=False)


while True:
	while not ts.touched:
		pass
		
	print(ts.touches)
	
	while ts.touched:
		pass
	
