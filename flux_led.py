#!/usr/bin/env python

"""
This is a utility for controlling stand-alone Flux WiFi LED light bulbs.
The protocol was reverse-engineered by studying packet captures between a 
bulb and the controlling "Magic Home" mobile app.  The code here dealing 
with the network protocol is littered with magic numbers, and ain't so pretty.
But it does seem to work!

So far most of the functionality of the apps is available here via the CLI
and/or programmatically.

The classes in this project could very easily be used as an API, and incorporated into a GUI app written 
in PyQt, Kivy, or some other framework.

##### Available:
* Discovering bulbs on LAN
* Turning on/off bulb
* Get state information
* Setting "warm white" mode
* Setting single color mode
* Setting preset pattern mode
* Setting custom pattern mode
* Reading timers
* Setting timers
	
##### Some missing pieces:
* Initial administration to set up WiFi SSID and passphrase/key.
* Remote access administration
* Music-relating pulsing. This feature isn't so impressive on the Magic Home app, 
and looks like it might be a bit of work.
	  
##### Cool feature:
* Specify colors with names or web hex values.  Requires that python "webcolors" 
package is installed.  (Easily done via pip, easy_install, or apt-get, etc.)
 See the following for valid color names: http://www.w3schools.com/html/html_colornames.asp

"""
import socket
import time
import sys
import datetime
from optparse import OptionParser,OptionGroup
import ast
try:
	import webcolors
	webcolors_available = True
except:
	webcolors_available = False

class utils:
	@staticmethod
	def color_object_to_tuple(color):	
		global webcolors_available

		# see if it's already a color tuple
		if type(color) is tuple and len(color) == 3:
			return color
		
		# can't convert non-string
		if type(color) is not str:
			return None
		color = color.strip()

		if webcolors_available:
			# try to convert from an english name
			try:
				return webcolors.name_to_rgb(color)
			except ValueError:
				pass
			except:
				pass
		
			# try to convert an web hex code
			try:
				return webcolors.hex_to_rgb(webcolors.normalize_hex(color))
			except ValueError:
				pass
			except:
				pass

		# try to convert a string RGB tuple
		try:
			val = ast.literal_eval(color)
			if type(val) is not tuple or len(val) != 3:
				raise Exception
			return val
		except:
			pass
		return None
	
	@staticmethod
	def color_tuple_to_string(rgb):
		# try to convert to an english name
		try:
			return webcolors.rgb_to_name(rgb)
		except Exception as e:
			#print e
			pass
		return str(rgb)
	
	@staticmethod
	def get_color_names_list():
		names = set()
		for key in webcolors.css2_hex_to_names.keys():
			names.add(webcolors.css2_hex_to_names[key])
		for key in webcolors.css21_hex_to_names.keys():
			names.add(webcolors.css21_hex_to_names[key])
		for key in webcolors.css3_hex_to_names.keys():
			names.add(webcolors.css3_hex_to_names[key])
		for key in webcolors.html4_hex_to_names.keys():
			names.add(webcolors.html4_hex_to_names[key])			
		return sorted(names)
		
	@staticmethod
	def date_has_passed(dt):
		delta = dt - datetime.datetime.now()
		return delta.total_seconds() < 0

	@staticmethod
	def dump_bytes(bytes):
		print ''.join('{:02x} '.format(x) for x in bytearray(bytes))
	
	max_delay = 0x1f
	
	@staticmethod
	def delayToSpeed(delay):
		# speed is 0-100, delay is 1-31
		# 1st translate delay to 0-30
		delay = delay -1
		if delay > utils.max_delay - 1 :
			delay = utils.max_delay - 1
		if delay < 0: 
			delay = 0
		inv_speed = int((delay * 100)/(utils.max_delay - 1))
		speed =  100-inv_speed
		return speed
	
	@staticmethod
	def speedToDelay(speed):
		# speed is 0-100, delay is 1-31		
		if speed > 100:
			speed = 100
		if speed < 0:
			speed = 0
		inv_speed = 100-speed
		delay = int((inv_speed * (utils.max_delay-1))/100)
		# translate from 0-30 to 1-31
		delay = delay + 1
		return delay
	
	@staticmethod
	def byteToPercent(byte):
		if byte > 255:
			byte = 255
		if byte < 0:
			byte = 0
		return int((byte * 100)/255)

	@staticmethod
	def percentToByte(percent):
		if percent > 100:
			percent = 100
		if percent < 0:
			percent = 0
		return int((percent * 255)/100)
	
class PresetPattern:
	seven_color_cross_fade =   0x25
	red_gradual_change =       0x26
	green_gradual_change =     0x27
	blue_gradual_change =      0x28
	yellow_gradual_change =    0x29
	cyan_gradual_change =      0x2a
	purple_gradual_change =    0x2b
	white_gradual_change =     0x2c
	red_green_cross_fade =     0x2d
	red_blue_cross_fade =      0x2e
	green_blue_cross_fade =    0x2f
	seven_color_strobe_flash = 0x30
	red_strobe_flash =         0x31
	green_strobe_flash =       0x32
	blue_stobe_flash =         0x33
	yellow_strobe_flash =      0x34
	cyan_strobe_flash =        0x35
	purple_strobe_flash =      0x36
	white_strobe_flash =       0x37
	seven_color_jumping =      0x38
	
	@staticmethod
	def valid(pattern):
		if pattern < 0x25 or pattern > 0x38:
			return False
		return True
	
	@staticmethod
	def valtostr(pattern):
		for key, value in PresetPattern.__dict__.iteritems():
			if type(value) is int and value == pattern:
				return key.replace("_", " ").title()
		return None
	

		
class LedTimer():
	Mo = 0x02
	Tu = 0x04
	We = 0x08  
	Th = 0x10 
	Fr = 0x20
	Sa = 0x40 
	Su = 0x80
	Everyday = Mo|Tu|We|Th|Fr|Sa|Su
	Weekdays = Mo|Tu|We|Th|Fr
	Weekend = Sa|Su

	@staticmethod
	def dayMaskToStr(mask):
		for key, value in LedTimer.__dict__.iteritems():
			if type(value) is int and value == mask:
				return key
		return None  

	def __init__(self, bytes=None):
		if bytes is not None:
			self.fromBytes(bytes)
			return
			
		the_time = datetime.datetime.now() + datetime.timedelta(hours=1)  
		self.setTime(the_time.hour, the_time.minute)
		self.setDate(the_time.year, the_time.month, the_time.day)
		self.setModeTurnOff()
		self.setActive(False)
		
	def setActive(self, active=True):
		self.active = active
		
	def isActive(self):
		return self.active

	def isExpired(self):
		# if no repeat mask and datetime is in past, return True
		if self.repeat_mask != 0:
			return False
		elif self.year!=0 and self.month!=0 and self.day!=0:
			dt = datetime.datetime(self.year, self.month, self.day, self.hour, self.minute)
			if  utils.date_has_passed(dt):
				return True
		return False
		
	def setTime(self, hour, minute):
		self.hour = hour
		self.minute = minute

	def setDate(self, year, month, day):
		self.year = year
		self.month = month		
		self.day = day
		self.repeat_mask = 0

	def setRepeatMask(self, repeat_mask):
		self.year = 0		
		self.month = 0		
		self.day = 0
		self.repeat_mask = repeat_mask

	def setModeDefault(self):
		self.mode = "default"
		self.pattern_code = 0
		self.turn_on = True
		self.red = 0
		self.green = 0
		self.blue = 0
		self.warmth_level = 0
		
	def setModePresetPattern(self, pattern, speed):
		self.mode = "preset"
		self.warmth_level = 0
		self.pattern_code = pattern
		self.delay = utils.speedToDelay(speed)
		self.turn_on = True
		
	def setModeColor(self, r, g, b):
		self.mode = "color"
		self.warmth_level = 0
		self.red = r
		self.green = g
		self.blue = b		
		self.pattern_code = 0x61
		self.turn_on = True

	def setModeWarmWhite(self, level):
		self.mode = "ww"
		self.warmth_level = utils.percentToByte(level)
		self.pattern_code = 0x61
		self.red = 0
		self.green = 0
		self.blue = 0
		self.turn_on = True

	def setModeTurnOff(self):
		self.mode = "off"
		self.turn_on = False
		self.pattern_code = 0
	
	"""

	timer are in six 14-byte structs
		f0 0f 08 10 10 15 00 00 25 1f 00 00 00 f0 0f
		 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14

		0: f0 when active entry/ 0f when not active
		1: (0f=15) year when no repeat, else 0
		2:  month when no repeat, else 0
		3:  dayofmonth when no repeat, else 0
		4: hour
		5: min
		6: 0
		7: repeat mask, Mo=0x2,Tu=0x04, We 0x8, Th=0x10 Fr=0x20, Sa=0x40, Su=0x80
		8:  61 for solid color or warm, or preset pattern code
		9:  r (or delay for preset pattern)
		10: g
		11: b
		12: warm white level
		13: 0f = off, f0 = on ?
	"""		
	def fromBytes(self, bytes):
		#utils.dump_bytes(bytes)
		self.red = 0
		self.green = 0
		self.blue = 0		
		if bytes[0] == 0xf0:
			self.active = True
		else:
			self.active = False
		self.year = bytes[1]+2000
		self.month = bytes[2]
		self.day = bytes[3]
		self.hour = bytes[4]
		self.minute = bytes[5]
		self.repeat_mask = bytes[7]
		self.pattern_code = bytes[8]
	
		if self.pattern_code == 0x61:
			self.mode = "color"
			self.red = bytes[9]
			self.green = bytes[10]
			self.blue = bytes[11]
		elif self.pattern_code == 0x00:
			self.mode ="default"
		else:
			self.mode = "preset"
			self.delay = bytes[9] #same byte as red

		self.warmth_level = bytes[12]
		if self.warmth_level != 0:
			self.mode = "ww"
			
		if bytes[13] == 0xf0:
			self.turn_on = True
		else:
			self.turn_on = False
			self.mode = "off"

	def toBytes(self):
		bytes = bytearray(14)
		if not self.active:
			bytes[0] = 0x0f
			# quit since all other zeros is good
			return bytes
				
		bytes[0] = 0xf0
		
		if self.year >= 2000:
			bytes[1] =  self.year - 2000
		else:
			bytes[1] = self.year			
		bytes[2] = self.month
		bytes[3] = self.day
		bytes[4] = self.hour
		bytes[5] = self.minute
		# what is 6?
		bytes[7] = self.repeat_mask
		
		if not self.turn_on:
			bytes[13] = 0x0f
			return bytes		
		bytes[13] = 0xf0
		
		bytes[8] = self.pattern_code
		if self.mode == "preset":	
			bytes[9] = self.delay
			bytes[10] = 0
			bytes[11] = 0
		else:
			bytes[9] = self.red
			bytes[10] = self.green
			bytes[11] = self.blue
		bytes[12] = self.warmth_level

		return bytes
			
	def __str__(self):
		txt = ""
		if not self.active:
		  return "Unset"
		
		if self.turn_on:
			txt += "[ON ]"
		else:
			txt += "[OFF]"

		txt += " "

		txt += "{:02}:{:02}  ".format(self.hour,self.minute)
	
		if self.repeat_mask == 0:
			txt += "Once: {:04}-{:02}-{:02}".format(self.year,self.month,self.day)
		else:
			bits = [LedTimer.Su,LedTimer.Mo,LedTimer.Tu,LedTimer.We,LedTimer.Th,LedTimer.Fr,LedTimer.Sa]
			for b in bits:
				if self.repeat_mask & b:
					txt += LedTimer.dayMaskToStr(b)
				else:
					txt += "--"
			txt += "  "
				
		txt += "  "
		if self.pattern_code == 0x61:
			if self.warmth_level != 0:
				txt += "Warm White: {}%".format(utils.byteToPercent(self.warmth_level))
			else:
				color_str = utils.color_tuple_to_string((self.red,self.green,self.blue))
				txt += "Color: {}".format(color_str)

		elif PresetPattern.valid(self.pattern_code):
			pat = PresetPattern.valtostr(self.pattern_code)
			speed = utils.delayToSpeed(self.delay)
			txt += "{} (Speed:{}%)".format(pat, speed)
			
		return txt

class WifiLedBulb():
	def __init__(self, ipaddr, port=5577):
		self.ipaddr = ipaddr
		self.port = port
		self.__is_on = False
		
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.connect((self.ipaddr, self.port))
		
		self.__state_str = ""
		#self.refreshState()

	def __determineMode(self, ww_level, pattern_code):
		mode = "unknown"
		if pattern_code in [ 0x61, 0x62]:
			if ww_level != 0:
				mode = "ww"
			else:
				mode = "color"
		elif pattern_code == 0x60:
			mode = "custom"
		elif PresetPattern.valid(pattern_code):
			mode = "preset"
		return mode

	def refreshState(self):
		msg = bytearray([0x81, 0x8a, 0x8b])
		self.__write(msg)
		rx = self.__readResponse(14)

		power_state = rx[2]
		power_str = "Unknown power state"

		if power_state == 0x23:
			self.__is_on = True
			power_str = "ON "
		elif power_state == 0x24:
			self.__is_on = False
			power_str = "OFF"
			
		pattern = rx[3]
		ww_level = rx[9]
		mode = self.__determineMode(ww_level, pattern)
		delay = rx[5]
		speed = utils.delayToSpeed(delay)
		
		if mode == "color":
			red = rx[6]
			green = rx[7]
			blue = rx[8]
			color_str = utils.color_tuple_to_string((red, green, blue))
			mode_str = "Color: {}".format(color_str)
		elif mode == "ww":
			mode_str = "Warm White: {}%".format(utils.byteToPercent(ww_level))
		elif mode == "preset":
			pat = PresetPattern.valtostr(pattern)
			mode_str = "Pattern: {} (Speed {}%)".format(pat, speed)
		elif mode == "custom":
			mode_str = "Custom pattern (Speed {}%)".format(speed)
		else:
			mode_str = "Unknown mode 0x{:x}".format(pattern)
		if pattern == 0x62:
			mode_str += " (tmp)"
		self.__state_str = "{} [{}]".format(power_str, mode_str)

	def __str__(self):
		return self.__state_str

			
	def getClock(self):
		msg = bytearray([0x11, 0x1a, 0x1b, 0x0f])
		self.__write(msg)
		rx = self.__readResponse(12)
		#self.dump_data(rx)
		year =  rx[3] + 2000
		month = rx[4]
		date = rx[5]
		hour = rx[6]
		minute = rx[7]
		second = rx[8]
		#dayofweek = rx[9]
		try:
			dt = datetime.datetime(year,month,date,hour,minute,second)
		except:
			dt = None
		return dt

	def setClock(self):
		msg = bytearray([0x10, 0x14])
		now = datetime.datetime.now()
		msg.append(now.year-2000)
		msg.append(now.month)
		msg.append(now.day)
		msg.append(now.hour)
		msg.append(now.minute)
		msg.append(now.second)
		msg.append(now.isoweekday()) # day of week
		msg.append(0x00)
		msg.append(0x0f)
		self.__write(msg)

	def turnOn(self, on=True):
		if on:
			msg = bytearray([0x71, 0x23, 0x0f])
		else:
			msg = bytearray([0x71, 0x24, 0x0f])
			
		self.__write(msg)
		#print "set bulb {}".format(on)
		#time.sleep(.5)
		#x = self.__readResponse(4)
		self.__is_on = on
		
	def isOn(self):
		return self.__is_on
	
	def turnOff(self):
		self.turnOn(False)
	
	def setWarmWhite(self, level, persist=True):
		if persist:
			msg = bytearray([0x31])
		else:
			msg = bytearray([0x41])
		msg.append(0x00)
		msg.append(0x00)
		msg.append(0x00)
		msg.append(utils.percentToByte(level))
		msg.append(0x0f)
		msg.append(0x0f)
		self.__write(msg)
		
	def setRgb(self, r,g,b, persist=True):
		if persist:
			msg = bytearray([0x31])
		else:
			msg = bytearray([0x41])
		msg.append(r)
		msg.append(g)
		msg.append(b)
		msg.append(0x00)
		msg.append(0xf0)
		msg.append(0x0f)
		self.__write(msg)

	def setPresetPattern(self, pattern, speed):

		PresetPattern.valtostr(pattern)
		if not PresetPattern.valid(pattern):
			#print "Pattern must be between 0x25 and 0x38"
			raise Exception

		delay = utils.speedToDelay(speed)
		#print "speed {}, delay 0x{:02x}".format(speed,delay)
		pattern_set_msg = bytearray([0x61])
		pattern_set_msg.append(pattern)
		pattern_set_msg.append(delay)
		pattern_set_msg.append(0x0f)

		self.__write(pattern_set_msg)

	def getTimers(self):
		msg = bytearray([0x22, 0x2a, 0x2b, 0x0f])
		self.__write(msg)
		resp_len = 88
		rx = self.__readResponse(resp_len)
		if len(rx) != resp_len:
			print "response too short!"
			raise Exception
			
		#utils.dump_data(rx)
		start = 2
		timer_list = []
		#pass in the 14-byte timer structs 
		for i in range(6):
		  timer_bytes = rx[start:][:14]
		  timer = LedTimer(timer_bytes)
		  timer_list.append(timer)
		  start += 14
		  
		return timer_list
				
	def sendTimers(self, timer_list):
		# remove inactive or expired timers from list
		for t in timer_list:
			if not t.isActive() or t.isExpired():
				timer_list.remove(t)
				
		# truncate if more than 6
		if len(timer_list) > 6:
			print "too many timers, truncating list"
			del timer_list[6:]
			
		# pad list to 6 with inactive timers
		if len(timer_list) != 6:
			for i in range(6-len(timer_list)):
				timer_list.append(LedTimer())
		
		msg_start = bytearray([0x21])
		msg_end = bytearray([0x00, 0xf0])
		msg = bytearray()
		
		# build message
		msg.extend(msg_start)
		for t in timer_list:
			msg.extend(t.toBytes())
		msg.extend(msg_end)
		self.__write(msg)
		
		# not sure what the resp is, prob some sort of ack?
		rx = self.__readResponse(1)
		rx = self.__readResponse(3)
		
	def setCustomPattern(self, rgb_list, speed, transition_type):
				
		# truncate if more than 16
		if len(rgb_list) > 16:
			print "too many colors, truncating list"
			del rgb_list[16:]
			
		# quit if too few
		if len(rgb_list) == 0:
			print "no colors, aborting"
			return
		
		msg = bytearray()
		
		first_color = True
		for rgb in rgb_list:
			if first_color:
				lead_byte = 0x51
				first_color = False
			else:
				lead_byte = 0
			r,g,b = rgb
			msg.extend(bytearray([lead_byte, r,g,b]))
		
		# pad out empty slots
		if len(rgb_list) != 16:
			for i in range(16-len(rgb_list)):
				msg.extend(bytearray([0, 1, 2, 3]))
				
		msg.append(0x00)
		msg.append(utils.speedToDelay(speed))
		
		if transition_type =="gradual":
			msg.append(0x3a)
		elif transition_type =="jump":
			msg.append(0x3b)
		elif transition_type =="strobe":
			msg.append(0x3c)
		else:
			#unknown transition string: using 'gradual'
			msg.append(0x3a)
		msg.append(0xff)
		msg.append(0x0f)

		self.__write(msg)	

	def __writeRaw(self, bytes):
		self.socket.send(bytes)

	def __write(self, bytes):
		# calculate checksum of byte array and add to end
		csum = sum(bytes) & 0xFF
		bytes.append(csum)
		#print "-------------",utils.dump_bytes(bytes)
		self.__writeRaw(bytes)
		#time.sleep(.4)		
		
	def __readResponse(self, expected):
		remaining = expected
		rx = bytearray()
		while remaining > 0:
			chunk = self.__readRaw(remaining)
			remaining -= len(chunk)
			rx.extend(chunk)
		return rx
			
	def __readRaw(self, byte_count=1024):
		rx = self.socket.recv(byte_count)
		return rx
	
class  BulbScanner():
	def __init__(self):
		self.found_bulbs = []
	
	def getBulbInfoByID(self, id):
		bulb_info = None
		for b in self.found_bulbs:
			if b['id'] == id:
				return b
		return b		

	def getBulbInfo(self):
		return self.found_bulbs	
	
	def scan(self, timeout=10):
		
		DISCOVERY_PORT = 48899
	
		sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		sock.bind(('', DISCOVERY_PORT))
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		
		msg = "HF-A11ASSISTHREAD"
		
		# set the time at which we will quit the search
		quit_time = time.time() + timeout

		response_list = []
		# outer loop for query send
		while True:
			if time.time() > quit_time:
				break			
			# send out a broadcast query
			sock.sendto(msg, ('<broadcast>', DISCOVERY_PORT))
			
			# inner loop waiting for responses
			while True:
				
				sock.settimeout(1)
				try:
					data, addr = sock.recvfrom(64)
				except socket.timeout:
					data = None
					if time.time() > quit_time:
						break
	
				if data is not None and data != msg:
					# tuples of IDs and IP addresses
					item = dict()
					item['ipaddr'] = data.split(',')[0]
					item['id'] = data.split(',')[1]
					item['model'] = data.split(',')[2]
					response_list.append(item)

		self.found_bulbs = response_list
		return response_list
#=========================================================================
def showUsageExamples():
	example_text = """
Examples:

Scan network:
	%prog% -s

Scan network and show info about all:
	%prog% -sSti

Turn on:
	%prog% 192.168.1.100 --on
	%prog% 192.168.1.100 -192.168.1.101 -1

Turn on all bulbs on LAN:
	%prog% -sS --on

Turn off:
	%prog% 192.168.1.100 --off
	%prog% 192.168.1.100 --0
	%prog% -sS --off
	
Set warm white, 75%
	%prog% 192.168.1.100 -w 75 -0	

Set fixed color red :
	%prog% 192.168.1.100 -c Red
	%prog% 192.168.1.100 -c 255,0,0
	%prog% 192.168.1.100 -c "#FF0000"
	
Set preset pattern #35 with 40% speed:	
	%prog% 192.168.1.100 -p 35 40
	
Set custom pattern 25% speed, red/green/blue, gradual change:
	%prog% 192.168.1.100 -C gradual 25 "red green (0,0,255)"
	
Sync all bulb's clocks with this computer's:
	%prog% -sS --setclock
	
Set timer #1 to turn on red at 5:30pm on weekdays:
	%prog% 192.168.1.100 -T 1 color "time:1730;repeat:12345;color:red"

Deactivate timer #4:
	%prog% 192.168.1.100 -T 4 inactive ""

Use --timerhelp for more details on setting timers
	"""
	
	print example_text.replace("%prog%",sys.argv[0])

def showTimerHelp():
	timerhelp_text = """
There are 6 timers available for each bulb.

Mode Details:
	inactive:   timer is inactive and unused
	poweroff:   turns off the light 
	default:    turns on the light in default mode
	color:      turns on the light with specified color
	preset:     turns on the light with specified preset and speed
	warmwhite:  turns on the light with warm white at specified brightness

Settings available for each mode:
	Timer Mode | Settings
	--------------------------------------------
	inactive:   [none]
	poweroff:   time, (repeat | date)
	default:    time, (repeat | date)
	color:      time, (repeat | date), color
	preset:     time, (repeat | date), code, speed
	warmwhite:  time, (repeat | date), level
	
Setting Details:

	time: 4 digit string with zeros, no colons
		e.g:
		"1000"  - for 10:00am
		"2312"  - for 11:23pm
		"0315"  - for 3:15am
		
	repeat: Days of the week that the timer should repeat
			(Mutually exclusive with date)
			0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
		e.g:
		"0123456"  - everyday
		"06"       - weekends
		"12345"    - weekdays
		"2"        - only Tuesday
		
	date: Date that the one-time timer should fire
			(Mutually exclusive with repeat)
		e.g:
		"2015-09-13" 
		"2016-12-03" 	

	color: Color name, hex code, or rgb triple
	
	level: Level of the warm while light (0-100)
	
	code:  Code of the preset pattern (use -l to list them)
	
	speed: Speed of the preset pattern transions (0-100)
		
Example setting strings:
	"time:2130;repeat:0123456"
	"time:2130;date:2015-08-11"
	"time:1245;repeat:12345;color:123,345,23"
	"time:1245;repeat:12345;color:green"
	"time:1245;repeat:06;code:50;speed:30"
	"time:0345;date:2015-08-11;level:100"
	"""
	
	print timerhelp_text
	
def processSetTimerArgs(parser, args):
	mode = args[1]
	num = args[0]
	settings = args[2]
	
	if not num.isdigit() or int(num) > 6 or int(num) < 1:
		parser.error("Timer number must be between 1 and 6")

	# create a dict from the settings string
	settings_list=settings.split(";")
	settings_dict = {}
	for s in settings_list:
		pair = s.split(":")
		key = pair[0].strip().lower()
		val = ""
		if len(pair) > 1:
			val = pair[1].strip().lower()
		settings_dict[key] = val
		
	keys = settings_dict.keys()
	timer = LedTimer()
	
	if mode == "inactive":
		#no setting needed
		timer.setActive(False)

	elif mode in ["poweroff", "default","color","preset","warmwhite"]:
		timer.setActive(True)

		if "time" not in keys:
			parser.error("This mode needs a time: {}".format(mode))
		if  "repeat" in keys and "date" in keys:
			parser.error("This mode only a repeat or a date, not both: {}".format(mode))
			
		# validate time format
		if len(settings_dict["time"]) != 4 or not settings_dict["time"].isdigit() :
			parser.error("time must be a 4 digits")
		hour = int(settings_dict["time"][0:2:])
		minute = int(settings_dict["time"][2:4:])
		if hour > 23: 
			parser.error("timer hour can't be greater than 23")
		if minute > 59:
			parser.error("timer minute can't be greater than 59")

		timer.setTime(hour, minute)

		# validate date format
		if  "repeat" not in keys and "date" not in keys:
			# Generate date for next occurance of time
			print("No time or repeat given. Defaulting to next occurance of time")
			now = datetime.datetime.now()
			dt = now.replace(hour=hour, minute=minute)
			if utils.date_has_passed(dt):
				dt = dt + datetime.timedelta(days=1)
			#settings_dict["date"] = date
			timer.setDate(dt.year, dt.month, dt.day)
		elif "date" in keys:
			try:
				dt = datetime.datetime.strptime(settings_dict["date"], '%Y-%m-%d')
				timer.setDate(dt.year, dt.month, dt.day)
			except ValueError:
				parser.error("date is not properly formatted: YYYY-MM-DD")
		
		# validate repeat format
		if "repeat" in keys:
			if len(settings_dict["repeat"]) == 0:
				parser.error("Must specify days to repeat")
			days = set()
			for c in list(settings_dict["repeat"]):
				if c not in ['0', '1', '2', '3', '4', '5', '6']:
					parser.error("repeat can only contain digits 0-6")
				days.add(int(c))

			repeat = 0
			if 0 in days: repeat |= LedTimer.Su
			if 1 in days: repeat |= LedTimer.Mo
			if 2 in days: repeat |= LedTimer.Tu
			if 3 in days: repeat |= LedTimer.We
			if 4 in days: repeat |= LedTimer.Th
			if 5 in days: repeat |= LedTimer.Fr
			if 6 in days: repeat |= LedTimer.Sa
			timer.setRepeatMask(repeat)

		if  mode == "default":
			timer.setModeDefault()
			
		if  mode == "poweroff":
			timer.setModeTurnOff()			
			
		if  mode == "color":
			if  "color" not in keys:
				parser.error("color mode needs a color setting")
			#validate color val
			c = utils.color_object_to_tuple(settings_dict["color"])
			if c is None:
				parser.error("Invalid color value: {}".format(settings_dict["color"]))
			timer.setModeColor(c[0],c[1],c[2])
				
		if  mode == "preset":
			if  "code" not in keys:
				parser.error("preset mode needs a code: {}".format(mode))
			if  "speed" not in keys:
				parser.error("preset mode needs a speed: {}".format(mode))
			code = settings_dict["code"]
			speed = settings_dict["speed"]			
			if not speed.isdigit() or int(speed) > 100:
				parser.error("preset speed must be a percentage (0-100)")
			if not code.isdigit() or not PresetPattern.valid(int(code)):
				parser.error("preset code must be in valid range")
			timer.setModePresetPattern(int(code),int(speed))
				
		if  mode == "warmwhite":
			if  "level" not in keys:
				parser.error("warmwhite mode needs a level: {}".format(mode))
			level = settings_dict["level"]
			if not level.isdigit() or int(level) > 100:
				parser.error("warmwhite level must be a percentage (0-100)")
			timer.setModeWarmWhite(int(level))
	else:
		parser.error("Not a valid timer mode: {}".format(mode))
	
	return timer

def processCustomArgs(parser, args):
	if args[0] not in ["gradual", "jump", "strobe"]:
		parser.error("bad pattern type: {}".format(args[0]))
		return None
	
	speed = int(args[1])
	
	# convert the string to a list of RGB tuples
	# it should have space separated items of either
	# color names, hex values, or byte triples
	try:
		color_list_str = args[2].strip()
		str_list = color_list_str.split(' ')
		color_list = []
		for s in str_list:
			c = utils.color_object_to_tuple(s)
			if c is not None:
				color_list.append(c)
			else:
				raise Exception

	except:
		parser.error("COLORLIST isn't formatted right.  It should be a space separated list of RGB tuples, color names or web hex values")
		
	return args[0], speed, color_list
	
def parseArgs():
	
	parser = OptionParser()

	parser.description = "A utility to control Flux WiFi LED Bulbs. "
	#parser.description += ""
	#parser.description += "."
	power_group = OptionGroup(parser, 'Power options (mutually exclusive)')
	mode_group = OptionGroup(parser, 'Mode options (mutually exclusive)')
	info_group = OptionGroup(parser, 'Program help and information option')
	other_group = OptionGroup(parser, 'Other options')

	parser.add_option_group(info_group)
	info_group.add_option("-e", "--examples",
					  action="store_true", dest="showexamples", default=False,
					  help="Show usage examples")
	info_group.add_option("", "--timerhelp",
					  action="store_true", dest="timerhelp", default=False,
					  help="Show detailed help for setting timers")	
	info_group.add_option("-l", "--listpresets",
					  action="store_true", dest="listpresets", default=False,
					  help="List preset codes")
	info_group.add_option("--listcolors",
					  action="store_true", dest="listcolors", default=False,
					  help="List color names")
	
	parser.add_option("-s", "--scan",
					  action="store_true", dest="scan", default=False,
					  help="Search for bulbs on local network")
	parser.add_option("-S", "--scanresults",
					  action="store_true", dest="scanresults", default=False,
					  help="Operate on scan results instead of arg list")	
	power_group.add_option("-1", "--on",
					  action="store_true", dest="on", default=False,
					  help="Turn on specified bulb(s)")
	power_group.add_option("-0", "--off",
					  action="store_true", dest="off", default=False,
					  help="Turn off specified bulb(s)")
	parser.add_option_group(power_group)

	mode_group.add_option("-c", "--color", dest="color", default=None,
				  help="Set single color mode.  Can be either color name, web hex, or comma-separated RGB triple",
				  metavar='COLOR')
	mode_group.add_option("-w", "--warmwhite", dest="ww", default=None,
				  help="Set warm white mode (LEVEL is percent)",
				  metavar='LEVEL', type="int")
	mode_group.add_option("-p", "--preset", dest="preset", default=None,
				  help="Set preset pattern mode (SPEED is percent)",
				  metavar='CODE SPEED', type="int", nargs=2)
	mode_group.add_option("-C", "--custom", dest="custom", metavar='TYPE SPEED COLORLIST',
							default=None, nargs=3, 
							help="Set custom pattern mode. " +
							  "TYPE should be jump, gradual, or strobe. SPEED is percent. " +
							  "COLORLIST is a should be a space-separated list of color names, web hex values, or comma-separated RGB triples")
	parser.add_option_group(mode_group)
	
	parser.add_option("-i", "--info",
					  action="store_true", dest="info", default=False,
					  help="Info about bulb(s) state")
	parser.add_option("", "--getclock",
					  action="store_true", dest="getclock", default=False,
					  help="Get clock")	
	parser.add_option("", "--setclock",
					  action="store_true", dest="setclock", default=False,
					  help="Set clock to same as current time on this computer")
	parser.add_option("-t", "--timers",
					  action="store_true", dest="showtimers", default=False,
					  help="Show timers")
	parser.add_option("-T", "--settimer", dest="settimer", metavar='NUM MODE SETTINGS',
							default=None, nargs=3, 
							help="Set timer. " +
							  "NUM: number of the timer (1-6). " +
							  "MODE: inactive, poweroff, default, color, preset, or warmwhite. " +
							  "SETTINGS: a string of settings including time, repeatdays or date, " +
							  "and other mode specific settings.   Use --timerhelp for more details.")

	
	other_group.add_option("-v", "--volatile",
					  action="store_true", dest="volatile", default=False,
					  help="Don't persist mode setting with hard power cycle (RGB and WW modes only).")
	parser.add_option_group(other_group)
		
	parser.usage = "usage: %prog [-sS10cwpCiltThe] [addr1 [addr2 [addr3] ...]."
	(options, args) = parser.parse_args()

	if options.showexamples:
		showUsageExamples()
		sys.exit(0)

	if options.timerhelp:
		showTimerHelp()
		sys.exit(0)
	
	if options.listpresets:
		for c in range(PresetPattern.seven_color_cross_fade, PresetPattern.seven_color_jumping+1):
			print "{:2} {}".format(c, PresetPattern.valtostr(c))
		sys.exit(0)

	global webcolors_available
	if options.listcolors:
		if webcolors_available:
			for c in utils.get_color_names_list():
				print "{}, ".format(c),
			print
		else:
			print "webcolors package doesn't seem to be installed. No color names available"
		sys.exit(0)		
		
	if options.settimer:
		new_timer = processSetTimerArgs(parser, options.settimer)
		options.new_timer = new_timer
	else:
		options.new_timer = None
		
	mode_count = 0
	if options.color:  mode_count += 1
	if options.ww:     mode_count += 1
	if options.preset: mode_count += 1
	if options.custom: mode_count += 1
	if mode_count > 1:
		parser.error("options --color, --warmwhite, --preset, and --custom are mutually exclusive")
		
	if options.on and options.off:
		parser.error("options --on and --off are mutually exclusive")

	if options.custom:
		options.custom = processCustomArgs(parser, options.custom)
		
	if options.color:
		options.color = utils.color_object_to_tuple(options.color)
		if options.color is None:
			parser.error("bad color specification")
		
	if options.preset:
		if not PresetPattern.valid(options.preset[0]):
			parser.error("Preset code is not in range")
		
	# asking for timer info, implicitly gets the state
	if options.showtimers:
		options.info = True
		
	op_count = mode_count
	if options.on:   op_count += 1
	if options.off:  op_count += 1
	if options.info: op_count += 1
	if options.getclock: op_count += 1
	if options.setclock: op_count += 1
	if options.listpresets: op_count += 1
	if options.settimer: op_count += 1
	
	if (not options.scan or options.scanresults) and (op_count == 0):
		parser.error("An operation must be specified")

	# if we're not scanning, IP addresses must be specified as positional args
	if  not options.scan and not options.scanresults and not options.listpresets:
		if len(args) == 0:
			parser.error("You must specify at least one IP address as an argument, or use scan results")
			

	return (options, args)
#-------------------------------------------
def main():
	
	(options, args) = parseArgs()
	
	if options.scan:
		scanner = BulbScanner()
		scanner.scan(timeout=2)
		bulb_info_list = scanner.getBulbInfo()
		# we have a list of buld info dicts
		addrs = []
		if options.scanresults and len(bulb_info_list) > 0 :
			for b in bulb_info_list:
				addrs.append(b['ipaddr'])
		else:
			print "{} bulbs found".format(len(bulb_info_list))
			for b in bulb_info_list:
				print "  {} {}".format(b['id'], b['ipaddr'])
			sys.exit(0)
		
	else:
		addrs = args
		bulb_info_list = []
		for addr in args:
			info = dict()
			info['ipaddr'] = addr
			info['id'] = 'Unknown ID'
			bulb_info_list.append(info)
			
	
	# now we have our bulb list, perform same operation on all of them
	for info in bulb_info_list:
		a = info['ipaddr']
		try:
			bulb = WifiLedBulb(info['ipaddr'])
		except Exception as e:
			print "Unable to connect to bulb at [{}]: {}".format(info['ipaddr'],e)
			continue

		if options.getclock:
			print "{} [{}] {}".format(info['id'], info['ipaddr'],bulb.getClock())

		if options.setclock:
			bulb.setClock()
			
		if options.ww is not None:
			print "Setting warm white mode, level: {}%".format(options.ww)
			bulb.setWarmWhite(options.ww, not options.volatile)
			
		elif options.color is not None:
			print "Setting color RGB:{}".format(options.color),
			name = utils.color_tuple_to_string(options.color)
			if name is None:
				print 
			else:
				print "[{}]".format(name)	
			bulb.setRgb(options.color[0],options.color[1],options.color[2], not options.volatile)
			
		elif options.custom is not None:
			bulb.setCustomPattern(options.custom[2], options.custom[1], options.custom[0])
			print "Setting custom pattern: {}, Speed={}%, {}".format(
				options.custom[0], options.custom[1], options.custom[2])
			
		elif options.preset is not None:
			print "Setting preset pattern: {}, Speed={}%".format(PresetPattern.valtostr(options.preset[0]), options.preset[1])
			bulb.setPresetPattern(options.preset[0], options.preset[1])

		if options.on:
			print "Turning on bulb at {}".format(bulb.ipaddr)
			bulb.turnOn()
		elif options.off:
			print "Turning off bulb at {}".format(bulb.ipaddr)
			bulb.turnOff()
			
		if options.info:
			bulb.refreshState()
			print "{} [{}] {}".format(info['id'], info['ipaddr'],bulb)

		if options.settimer:
			timers = bulb.getTimers()
			num = int(options.settimer[0])
			print "New Timer ---- #{}: {}".format(num,options.new_timer)
			if options.new_timer.isExpired():
				print "[timer is already expired, will be deactivated]"
			timers[num-1] = options.new_timer 
			bulb.sendTimers(timers)
			
		if options.showtimers:
			timers = bulb.getTimers()
			num = 0
			for t in timers:
				num += 1
				print "  Timer #{}: {}".format(num,t)
			print ""
			

	sys.exit(0)


if __name__ == '__main__':
	main()


