from cpy_xpt2046 import Touch
import board
import busio

spi = busio.SPI(board.IO25,board.IO32,board.IO39)
c = board.IO33
spi.try_lock()

xpt = Touch(spi,cs=c)

while True:
	while not xpt.touched:
		pass
		
	print(xpt.touches)
	
	while xpt.touched:
		pass
	