[![Python package][python-package-shield]][python-package]
[![codecov][code-cover-shield]][code-coverage] \
[![Python Versions][python-ver-shield]][python-ver]
[![PyPi Project][pypi-shield]][pypi]\
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)\
[![GitHub Top Language][language-shield]][language]




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

#### Minimum python version

3.7

##### Available:
* Discovering bulbs on LAN
* Turning on/off bulb
* Get state information
* Setting "warm white" mode
* Setting single color mode
* Setting preset pattern mode
* Setting custom pattern mode
* Reading timers (sync version only)
* Setting timers (sync version only)
* Sync clock (sync version only)
* Music Mode for devices with a built-in microphone (asyncio version only)
* Remote access administration (asyncio version only)
	
##### Some missing pieces:
* Initial administration to set up WiFi SSID and passphrase/key.
	  
##### Cool feature:
* Specify colors with names or web hex values.  Requires that python "webcolors" 
package is installed.  (Easily done via pip, easy_install, or apt-get, etc.) Use --listcolors to show valid color names.

##### Installation:
* Flux_led package available at https://pypi.python.org/pypi/flux-led/
```
pip install flux_led

easy_install flux_led
```

##### Examples:
```
Scan network:
	flux_led -s

Scan network and show info about all:
	flux_led -sSti

Turn on:
	flux_led 192.168.1.100 --on
	flux_led 192.168.1.100 -192.168.1.101 -1

Turn on all bulbs on LAN:
	flux_led -sS --on

Turn off:
	flux_led 192.168.1.100 --off
	flux_led 192.168.1.100 --0
	flux_led -sS --off
	
Set warm white, 75%
	flux_led 192.168.1.100 -w 75 -1

Set fixed color red :
	flux_led 192.168.1.100 -c Red
	flux_led 192.168.1.100 -c 255,0,0
	flux_led 192.168.1.100 -c "#FF0000"
	
Set preset pattern #35 with 40% speed:	
	flux_led 192.168.1.100 -p 35 40
	
Set custom pattern 25% speed, red/green/blue, gradual change:
	flux_led 192.168.1.100 -C gradual 25 "red green (0,0,255)"

Sync all bulb's clocks with this computer's:
	flux_led -sS --setclock
		
Set timer #1 to turn on red at 5:30pm on weekdays:
	flux_led 192.168.1.100 -T 1 color "time:1730;repeat:12345;color:red"
	
Deactivate timer #4:
	flux_led 192.168.1.100 -T 4 inactive ""

Use --timerhelp for more details on setting timers
```
	
##### Show help:
```	
$ flux_led -h
Usage: usage: __main__.py [-sS10cwpCiltThe] [addr1 [addr2 [addr3] ...].

A utility to control Flux WiFi LED Bulbs.

Options:
  -h, --help            show this help message and exit
  -s, --scan            Search for bulbs on local network
  -S, --scanresults     Operate on scan results instead of arg list
  -i, --info            Info about bulb(s) state
  --getclock            Get clock
  --setclock            Set clock to same as current time on this computer
  -t, --timers          Show timers
  -T NUM MODE SETTINGS, --settimer=NUM MODE SETTINGS
                        Set timer. NUM: number of the timer (1-6). MODE:
                        inactive, poweroff, default, color, preset, or
                        warmwhite. SETTINGS: a string of settings including
                        time, repeatdays or date, and other mode specific
                        settings.   Use --timerhelp for more details.

  Program help and information option:
    -e, --examples      Show usage examples
    --timerhelp         Show detailed help for setting timers
    -l, --listpresets   List preset codes
    --listcolors        List color names

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
                        or strobe. SPEED is percent. COLORLIST is a space-
                        separated list of color names, web hex values, or
                        comma-separated RGB triples


```

### Supported Models

The following models have been tested with library.

| Model | Description                 | Notes                           |
| ----- | --------------------------- | ------------------------------- |
| 0x04  | UFO Controller RGBW         |                                 |
| 0x06  | Controller RGBW             |                                 |
| 0x07  | Controller RGBCW            |                                 |
| 0x08  | Controller RGB with MIC     |                                 |
| 0x0E  | Floor Lamp RGBCW            |                                 |
| 0x10  | Christmas Light             |                                 |
| 0x1A  | Christmas Light             |                                 |
| 0x1C  | Table Light CCT             |                                 |
| 0x21  | Bulb Dimmable               |                                 |
| 0x25  | Controller RGB/WW/CW        | Supports RGB,RGBW,RGBWW,CW,DIM  |
| 0x33  | Controller RGB              |                                 |
| 0x35  | Bulb RGBCW                  |                                 |
| 0x41  | Controller Dimmable         |                                 |
| 0x44  | Bulb RGBW                   |                                 |
| 0x54  | Downlight RGBW              |                                 |
| 0x93  | Switch 1c                   |                                 |
| 0x94  | Switch 1c Watt              |                                 |
| 0x97  | Socket 1c                   |                                 |
| 0xA1  | Addressable v1              |                                 |
| 0xA2  | Addressable v2              |                                 |
| 0xA3  | Addressable v3              |                                 |

### Unsupported Models

The following models have not been tested with library but may work.

| Model | Description                 | Notes                           |
| ----- | --------------------------- | ------------------------------- |
| 0x09  | Ceiling Light CCT           |                                 |
| 0x16  | Magnetic Light CCT          |                                 |
| 0x17  | Magnetic Light Dimmable     |                                 |
| 0x19  | Socket 2 USB                |                                 |
| 0x18  | Plant Light                 |                                 |
| 0x1B  | Spray Light                 |                                 |
| 0x62  | Controller CCT              | May be discontinued             |
| 0x52  | Bulb CCT                    | May be discontinued             |
| 0x95  | Switch 2c                   |                                 |
| 0x96  | Switch 4c                   |                                 |
| 0xD1  | Digital Light               |                                 |
| 0xE1  | Ceiling Light               |                                 |
| 0xE2  | Ceiling Light Assist        |                                 |
| 0xA4  | Addressable v4              |                                 |

### File Structure 

device.py -> contains code to manipulate device as well as get any information from device that's needed.\
fluxled.py -> command line code for flux_led.\
pattern.py -> contains code to identify pattern as well as set patterns.\
protocol.py -> contains communication protocol to communicate with differnt devices.\
scanner.py -> contins scanner to scan network and identify devices on network.\
sock.py -> contains code to communicate on network.\
timer.py -> contains code to support setting timers on devices and getting timer information from devices.\
utils.py -> contains helpers to calculate differnt parameters such as color, cct, brightness etc.\


[code-coverage]: https://codecov.io/gh/Danielhiversen/flux_led
[code-cover-shield]: https://codecov.io/gh/Danielhiversen/flux_led/branch/master/graph/badge.svg
[commits-shield]: https://img.shields.io/github/commit-activity/y/Danielhiversen/flux_led.svg
[commits]: https://github.com/Danielhiversen/flux_led/commits/main
[language]: https://github.com/Danielhiversen/flux_led/search?l=python
[language-shield]: https://img.shields.io/github/languages/top/Danielhiversen/flux_led
[license-shield]: https://img.shields.io/github/license/Danielhiversen/flux_led.svg
[pypi]: https://pypi.org/project/flux_led/
[pypi-shield]: https://img.shields.io/pypi/v/flux_led
[python-package]: https://github.com/Danielhiversen/flux_led/actions/workflows/python-package.yml
[python-package-shield]: https://github.com/Danielhiversen/flux_led/actions/workflows/python-package.yml/badge.svg?branch=master
[python-ver]: https://pypi.python.org/pypi/flux_led/
[python-ver-shield]: https://img.shields.io/pypi/pyversions/flux_led.svg

