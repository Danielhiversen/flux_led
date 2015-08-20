### led_flux.py 

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
* Setting timers (Programmatically only)
	
##### Some missing pieces:
* Initial administration to set up WiFi SSID and passphrase/key.
* The CLI interface for setting timers is still in-progress.
* Music-relating pulsing. This feature isn't so impressive on the Magic Home app, 
and looks like it might be a bit of work.
	  
##### Cool feature:
* Specify colors with names or web hex values.  Requires that python "webcolors" 
package is installed.  (Easily done via pip, easy_install, or apt-get, etc.)
 See the following for valid color names: http://www.w3schools.com/html/html_colornames.asp

##### Examples:
Scan network:

	flux_led.py -s
	
Scan network and show info about all bulbs:

	flux_led.py -sSti

Turn on:

	flux_led.py 192.168.1.100 --on
	flux_led.py 192.168.1.100 -192.168.1.101 -1
	
Turn on all bulbs on LAN:

	flux_led.py -sS --on
	
Turn off:

	flux_led.py 192.168.1.100 --off
	flux_led.py 192.168.1.100 --0
	flux_led.py -sS --off
	
Set warm white, 75%

	flux_led.py 192.168.1.100 -w 75 -0	
	
Set fixed color red :

	flux_led.py 192.168.1.100 -c Red
	flux_led.py 192.168.1.100 -c 255,0,0
	flux_led.py 192.168.1.100 -c "#FF0000"
	
	
Set preset pattern #35 with 40% speed:	

	flux_led.py 192.168.1.100 -p 35 40
	
Set custom pattern 25% speed, red/green/blue, gradual change:

	flux_led.py 192.168.1.100 -C gradual 25 "red green (0,0,255)"
	
Show help:
```	
$ ./flux_led.py -h
Usage: usage: flux_led.py [-sS10cwpCiltThe] [addr1 [addr2 [addr3] ...].

A utility to control Flux WiFi LED Bulbs.

Options:
  -h, --help            show this help message and exit
  -e, --examples        Show usage examples
  -s, --scan            Search for bulbs on local network
  -S, --scanresults     Operate on scan results instead of arg list
  -i, --info            Info about bulb(s) state
  -l, --listpresets     List preset codes
  -t, --timers          Show timers

  Power options (mutually exclusive):
    -1, --on            Turn on specified bulb(s)
    -0, --off           Turn off specified bulb(s)

  Mode options (mutually exclusive):
    -c COLOR, --color=COLOR
                        Set single color mode.  Can be either color name, web
                        hex, or comma-separated RGB triple
    -w LEVEL, --warmwhite=LEVEL
                        Set warm white mode (LEVEL is percent)
    -p CODE SPEED, --preset=CODE SPEED
                        Set preset pattern mode (SPEED is percent)
    -C TYPE SPEED COLORLIST, --custom=TYPE SPEED COLORLIST
                        Set custom pattern mode. TYPE should be jump, gradual,
                        or strobe. SPEED is percent. COLORLIST is a should be
                        a space-separated list of color names, web hex values,
                        or comma-separated RGB triples,
```
