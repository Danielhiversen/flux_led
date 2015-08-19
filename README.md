### led_flux.py 

This is a utility for controlling stand-alone Flux WiFi LED light bulbs.
The protocol was reverse-engineered by studying packet captures between a 
bulb and the controlling "Magic Home" mobile app.  The code here dealing 
with the network protocol is littered with magic numbers, and ain't so pretty.
But it does seem to work!

So far most of the functionality of the apps is available here via the CLI
and/or programmatically.

The classes in this project could very easily be incorporated in a GUI app written 
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
* The CLI interface for setting timers is still in-progress.
* Music-relating pulsing. This feature isn't so impressive on the Magic Home app, 
and looks like it might be a bit of work.
	  
##### Cool feature:
* Specify colors with names or web hex values.  Requires that python "webcolors" 
package is installed.  (Easily done via pip, easy_install, or apt-get, etc.)
 See the following for valid color names: http://www.w3schools.com/html/html_colornames.asp

