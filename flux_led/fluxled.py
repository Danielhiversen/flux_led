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

from __future__ import print_function
from enum import Enum
import logging
import select
import socket
import time
import select
import sys
import datetime
import colorsys
from optparse import OptionParser, OptionGroup
import ast
import threading
from .scanner import bulbscanner
from .utils import utils
from .timer import(builtintimer, ledtimer)
from .pattern import presetpattern
from .sock import _socket_retry

try:
    import webcolors

    webcolors_available = True
except:
    webcolors_available = False

_LOGGER = logging.getLogger(__name__)


from .protocol import (
    PROTOCOL_LEDENET_8BYTE,
    PROTOCOL_LEDENET_ORIGINAL,
    PROTOCOL_LEDENET_9BYTE,
)
from .protocol import (
    ProtocolLEDENET9Byte,
    ProtocolLEDENET8Byte,
    ProtocolLEDENETOriginal,
)
from .protocol import LevelWriteMode

STATE_CHANGE_LATENCY = 0.3
MIN_TEMP = 2700
MAX_TEMP = 6500


class DeviceType(Enum):
    Bulb = 0
    Switch = 1


class WifiLedBulb:
    def __init__(self, ipaddr, port=5577, timeout=5):
        self.ipaddr = ipaddr
        self.port = port
        self.timeout = timeout
        self.raw_state = None

        self._protocol = None

        self.available = None
        self._is_on = False
        self._mode = None
        self._socket = None

        self._transition_complete_time = 0

        self._lock = threading.Lock()

        self.connect(retry=2)
        self.update_state()

    @property
    def model_num(self):
        """Return the model number."""
        return self.raw_state.model_num if self.raw_state else None

    @property
    def rgbwprotocol(self):
        """Devices that don't require a separate rgb/w bit."""
        return self.model_num in (0x04, 0x33, 0x81)

    @property
    def rgbwcapable(self):
        """Devices that actually support rgbw."""
        return self.model_num in (0x04, 0x25, 0x81, 0x44, 0x06, 0x35)

    @property
    def device_type(self):
        """Return the device type."""
        return DeviceType.Switch if self.model_num == 0x97 else DeviceType.Bulb

    @property
    def _rgbwwprotocol(self):
        """Device that uses the 9-byte protocol."""
        return self._uses_9byte_protocol(self.model_num)

    def _uses_9byte_protocol(self, model_num):
        """Devices that use a 9-byte protocol."""
        return model_num in (0x25, 0x27, 0x35)

    @property
    def protocol(self):
        """Returns the name of the protocol in use."""
        if not self._protocol:
            return None
        return self._protocol.name

    @property
    def is_on(self):
        return self._is_on

    @property
    def mode(self):
        return self._mode

    @property
    def warm_white(self):
        return self.raw_state.warm_white if self._rgbwwprotocol else 0

    @property
    def cool_white(self):
        return self.raw_state.cool_white if self._rgbwwprotocol else 0

    # Old name is deprecated
    @property
    def cold_white(self):
        return self.cool_white

    @property
    def brightness(self):
        """Return current brightness 0-255.
        For warm white return current led level. For RGB
        calculate the HSV and return the 'value'.
        for CCT calculate the brightness.
        for ww send led level
        """
        if self.mode in ["DIM", "ww"]:
            return int(self.raw_state.warm_white)
        elif self.mode == "CCT":
            _, b = self.getWhiteTemperature()
            return b
        else:
            _, _, v = colorsys.rgb_to_hsv(*self.getRgb())
            return v

    def _connect_if_disconnected(self):
        """Connect only if not already connected."""
        if self._socket is None:
            self.connect()

    @_socket_retry(attempts=0)
    def connect(self):
        self.close()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self.timeout)
        _LOGGER.debug("%s: connect", self.ipaddr)
        self._socket.connect((self.ipaddr, self.port))

    def close(self):
        if self._socket is None:
            return
        try:
            self._socket.close()
        except socket.error:
            pass
        finally:
            self._socket = None

    def _determineMode(self, ww_level, pattern_code, mode_code):
        mode = "unknown"
        if self.device_type == DeviceType.Switch:
            return "switch"
        if pattern_code == 0x61:
            if mode_code == 0x01:
                mode = "DIM"
            elif mode_code == 0x02:
                mode = "CCT"
            elif mode_code == 0x03:
                mode = "RGB"
            elif mode_code == 0x04:
                mode = "RGBW"
            elif mode_code == 0x05 or mode_code == 0x17:
                mode = "RGBWW"
            elif self.rgbwcapable:
                mode = "color"
            elif ww_level != 0:
                mode = "ww"
            else:
                mode = "color"
        elif pattern_code == 0x60:
            mode = "custom"
        elif pattern_code == 0x62:
            mode = "music"
        elif pattern_code == 0x41:
            mode = "color"
        elif presetpattern.valid(pattern_code):
            mode = "preset"
        elif builtintimer.valid(pattern_code):
            mode = builtintimer.valtostr(pattern_code)
        return mode

    def _determine_protocol(self):
        # determine the type of protocol based of first 2 bytes.
        read_bytes = 2

        protocol = ProtocolLEDENET8Byte()
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(protocol.construct_state_query())
            rx = self._read_msg(read_bytes)
            # if any response is recieved, use the default protocol
            if len(rx) == read_bytes:
                # Devices that use an 9-byte protocol
                if self._uses_9byte_protocol(rx[1]):
                    self._protocol = ProtocolLEDENET9Byte()
                else:
                    self._protocol = protocol
                return rx + self._read_msg(
                    self._protocol.state_response_length - read_bytes
                )

        # We just sent a garage query which the old procotol
        # cannot process, recycle the connection
        protocol = ProtocolLEDENETOriginal()
        self.connect()
        with self._lock:
            # if no response from default received, next try the original protocol
            self._send_msg(protocol.construct_state_query())
            rx = self._read_msg(read_bytes)
            if len(rx) == read_bytes and rx[1] == 0x01:
                self._protocol = protocol
                return rx + self._read_msg(
                    self._protocol.state_response_length - read_bytes
                )

        raise Exception("Cannot determine protocol")

    @_socket_retry(attempts=2)
    def query_state(self, led_type=None):
        if led_type:
            self.setProtocol(led_type)
        elif not self._protocol:
            return self._determine_protocol()

        with self._lock:
            self.connect()
            self._send_msg(self._protocol.construct_state_query())
            return self._read_msg(self._protocol.state_response_length)

    def update_state(self, retry=2):
        rx = self.query_state(retry=retry)
        if rx and self.process_state_response(rx):
            self.available = True
            return
        self.set_unavailable()

    def set_unavailable(self):
        self._is_on = False
        self.available = False

    def set_available(self):
        self.available = True

    def process_state_response(self, rx):
        if rx is None or len(rx) < self._protocol.state_response_length:
            self.set_unavailable()
            return False

        if not self._protocol.is_valid_state_response(rx):
            _LOGGER.warning(
                "%s: Recieved invalid response: %s",
                self.ipaddr,
                utils.raw_state_to_dec(rx),
            )
            return False

        raw_state = self._protocol.named_raw_state(rx)
        _LOGGER.debug("%s: State: %s", self.ipaddr, raw_state)

        if raw_state != self.raw_state:
            _LOGGER.debug("%s: new_state: %s", self.ipaddr, utils.raw_state_to_dec(rx))

        if time.monotonic() < self._transition_complete_time:
            # Do not update the raw state if a transition is
            # in progress as the state will not be correct
            # until the transition is completed since devices
            # "FADE" into the state requested.
            return True

        self.raw_state = raw_state
        self._set_power_state_from_raw_state()
        mode = self._determineMode(
            raw_state.warm_white, raw_state.preset_pattern, raw_state.mode
        )
        if mode == "unknown":
            _LOGGER.debug(
                "%s: Unable to determine mode from raw state: %s",
                self.ipaddr,
                utils.raw_state_to_dec(rx),
            )
            return False

        self._mode = mode
        return True

    def _set_power_state_from_raw_state(self):
        """Set the power state from the raw state."""
        power_state = self.raw_state.power_state
        if power_state == self._protocol.on_byte:
            self._is_on = True
        elif power_state == self._protocol.off_byte:
            self._is_on = False

    def __str__(self):
        rx = self.raw_state
        if not rx:
            return "No state data"
        mode = self.mode
        pattern = rx.preset_pattern
        ww_level = rx.warm_white
        power_state = rx.power_state
        power_str = "Unknown power state"
        if power_state == self._protocol.on_byte:
            power_str = "ON "
        elif power_state == self._protocol.off_byte:
            power_str = "OFF "

        delay = rx.speed
        speed = utils.delayToSpeed(delay)
        if mode in ["RGB", "RGBW", "RGBWW", "color"]:
            red = rx.red
            green = rx.green
            blue = rx.blue
            mode_str = "Color: {}".format((red, green, blue))
            # Should add ability to get CCT from rgbwcapable*
            if self.rgbwcapable:
                mode_str += " White: {}".format(ww_level)
            else:
                mode_str += " Brightness: {}".format(self.brightness)
        elif mode in ["DIM", "ww"]:
            mode_str = "Warm White: {}%".format(utils.byteToPercent(ww_level))
        elif mode == "CCT":
            cct_value = self.getWhiteTemperature()
            mode_str = "CCT: {}K Brightness: {}%".format(
                cct_value[0], cct_value[1] / 255
            )
        elif mode == "preset":
            pat = presetpattern.valtostr(pattern)
            mode_str = "Pattern: {} (Speed {}%)".format(pat, speed)
        elif mode == "custom":
            mode_str = "Custom pattern (Speed {}%)".format(speed)
        elif builtintimer.valid(pattern):
            mode_str = builtintimer.valtostr(pattern)
        elif mode == "music":
            mode_str = "Music"
        elif mode == "switch":
            mode_str = "Switch"
        else:
            mode_str = "Unknown mode 0x{:x}".format(pattern)
        mode_str += " raw state: "
        mode_str += utils.raw_state_to_dec(rx)
        return "{} [{}]".format(power_str, mode_str)

    @_socket_retry(attempts=2)
    def _change_state(self, turn_on=True):
        _LOGGER.debug("%s: Changing state to %s", self.ipaddr, turn_on)
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(self._protocol.construct_state_change(turn_on))
            # After changing state, the device replies with
            expected_response_len = 4
            # - 0x0F 0x71 [0x23|0x24] [CHECK DIGIT]
            rx = self._read_msg(expected_response_len)
            _LOGGER.debug("%s: state response %s", self.ipaddr, rx)
            if len(rx) == expected_response_len:
                new_power_state = (
                    self._protocol.on_byte if turn_on else self._protocol.off_byte
                )
                self._replace_raw_state({"power_state": new_power_state})
                self._set_power_state_from_raw_state()
            self._set_transition_complete_time()
            # The device will send back a state change here
            # but it will likely be stale so we want to recycle
            # the connetion so we do not have to wait as sometimes
            # it stalls
            self.close()

    def _replace_raw_state(self, new_state):
        self.raw_state = self.raw_state._replace(**new_state)

    def turnOn(self, retry=2):
        self._change_state(retry=retry, turn_on=True)

    def turnOff(self, retry=2):
        self._change_state(retry=retry, turn_on=False)

    def isOn(self):
        return self.is_on

    def getWarmWhite255(self):
        if self.mode not in ["ww", "CCT", "DIM"]:
            return 255
        return self.brightness

    def setWarmWhite(self, level, persist=True, retry=2):
        self.setWarmWhite255(utils.percentToByte(level), persist, retry)

    def setWarmWhite255(self, level, persist=True, retry=2):
        self.setRgbw(w=level, persist=persist, brightness=None, retry=retry)

    def setColdWhite(self, level, persist=True, retry=2):
        self.setColdWhite255(utils.percentToByte(level), persist, retry)

    def setColdWhite255(self, level, persist=True, retry=2):
        self.setRgbw(persist=persist, brightness=None, retry=retry, w2=level)

    def setWhiteTemperature(self, temperature, brightness, persist=True, retry=2):
        # Assume output temperature of between 2700 and 6500 Kelvin, and scale
        # the warm and cold LEDs linearly to provide that
        if not (MIN_TEMP <= temperature <= MAX_TEMP):
            raise ValueError(
                f"Temperature of {temperature} is not valid and must be between {MIN_TEMP} and {MAX_TEMP}"
            )
        brightness = round(brightness / 255, 2)
        cold = ((6500 - temperature) / (MAX_TEMP - MIN_TEMP)) * (brightness)
        warm = (brightness) - cold
        cold = round(255 * cold)
        warm = round(255 * warm)
        self.setRgbw(w=cold, w2=warm, persist=persist, retry=retry)

    def getWhiteTemperature(self):
        # Assume input temperature of between 2700 and 6500 Kelvin, and scale
        # the warm and cold LEDs linearly to provide that
        warm = self.raw_state.warm_white / 255
        cold = self.raw_state.cool_white / 255
        brightness = warm + cold
        temperature = ((cold / brightness) * (6493 - 2703)) + 2703
        brightness = round(brightness * 255)
        temperature = round(temperature)
        return (temperature, brightness)

    def getRgbw(self):
        if self.mode not in ["RGBW", "color"]:
            return (255, 255, 255, 255)
        return (
            self.raw_state.red,
            self.raw_state.green,
            self.raw_state.blue,
            self.raw_state.warm_white,
        )

    def getRgbww(self):
        if self.mode not in ["RGBWW", "color"]:
            return (255, 255, 255, 255, 255)
        return (
            self.raw_state.red,
            self.raw_state.green,
            self.raw_state.blue,
            self.raw_state.warm_white,
            self.raw_state.cool_white,
        )

    def getCCT(self):
        if self.mode != "CCT":
            return (255, 255)
        return (self.raw_state.warm_white, self.raw_state.cool_white)

    def getSpeed(self):
        delay = self.raw_state.speed
        speed = utils.delayToSpeed(delay)
        return speed

    @_socket_retry(attempts=2)
    def setRgbw(
        self,
        r=None,
        g=None,
        b=None,
        w=None,
        persist=True,
        brightness=None,
        w2=None,
    ):
        if (r or g or b) and (w or w2) and not self.rgbwcapable:
            print("RGBW command sent to non-RGBW device")
            raise Exception

        if brightness != None:
            (r, g, b) = self._calculateBrightness((r, g, b), brightness)

        r_value = 0 if r is None else int(r)
        g_value = 0 if g is None else int(g)
        b_value = 0 if b is None else int(b)
        w_value = 0 if w is None else int(w)
        # ProtocolLEDENET9Byte devices support two white outputs for cold and warm.
        if w2 is None:
            # If we're only setting a single white value,
            # we set the second output to be the same as the first
            w2_value = int(w) if w is not None and self.mode != "CCT" else 0
        else:
            w2_value = int(w2)

        write_mode = LevelWriteMode.ALL
        # rgbwprotocol devices always overwrite both color & whites
        if not self.rgbwprotocol:
            if w is None and w2 is None:
                write_mode = LevelWriteMode.COLORS
            elif r is None and g is None and b is None:
                write_mode = LevelWriteMode.WHITES

        _LOGGER.debug(
            "%s: setRgbw using %s: persist=%s r=%s, g=%s b=%s, w=%s w2=%s write_mode=%s",
            self.ipaddr,
            self.protocol,
            persist,
            r_value,
            g_value,
            b_value,
            w_value,
            w2_value,
            write_mode,
        )
        msg = self._protocol.construct_levels_change(
            persist, r_value, g_value, b_value, w_value, w2_value, write_mode
        )

        # send the message
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(msg)
            updates = {}
            if write_mode in (LevelWriteMode.ALL, LevelWriteMode.COLORS):
                updates.update({"red": r_value, "green": g_value, "blue": b_value})
            if write_mode in (LevelWriteMode.ALL, LevelWriteMode.WHITES):
                updates.update({"warm_white": w_value, "cool_white": w2_value})
            if updates:
                self._replace_raw_state(updates)
            self._set_transition_complete_time()

    def _set_transition_complete_time(self):
        """Set the time we expect the transition will be completed.

        Devices fade to a specific state so we want to avoid
        consuming state updates into self.raw_state while a transition
        is in progress as this will provide unexpected results
        and the brightness values will be wrong until
        the transition completes.
        """
        transition_time = (
            STATE_CHANGE_LATENCY + utils.speedToDelay(self.raw_state.speed) / 100
        )
        self._transition_complete_time = time.monotonic() + transition_time
        _LOGGER.debug(
            "Transition time is %s, set _transition_complete_time to %s",
            transition_time,
            self._transition_complete_time,
        )

    def getRgb(self):
        if self.mode not in ["RGB", "color"]:
            return (255, 255, 255)
        return (self.raw_state.red, self.raw_state.green, self.raw_state.blue)

    def setRgb(self, r, g, b, persist=True, brightness=None, retry=2):
        self.setRgbw(r, g, b, persist=persist, brightness=brightness, retry=retry)

    def _calculateBrightness(self, rgb, level):
        hsv = colorsys.rgb_to_hsv(*rgb)
        return colorsys.hsv_to_rgb(hsv[0], hsv[1], level)

    def _send_msg(self, bytes):
        _LOGGER.debug(
            "%s => %s (%d)",
            self.ipaddr,
            " ".join("0x{:02X}".format(x) for x in bytes),
            len(bytes),
        )
        self._socket.send(bytes)

    def _read_msg(self, expected):
        remaining = expected
        rx = bytearray()
        begin = time.monotonic()
        while remaining > 0:
            timeout_left = self.timeout - (time.monotonic() - begin)
            if timeout_left <= 0:
                break
            try:
                self._socket.setblocking(0)
                read_ready, _, _ = select.select([self._socket], [], [], timeout_left)
                if not read_ready:
                    _LOGGER.debug(
                        "%s: timed out reading %d bytes", self.ipaddr, expected
                    )
                    break
                chunk = self._socket.recv(remaining)
                _LOGGER.debug(
                    "%s <= %s (%d)",
                    self.ipaddr,
                    " ".join("0x{:02X}".format(x) for x in chunk),
                    len(chunk),
                )
                if chunk:
                    begin = time.monotonic()
                remaining -= len(chunk)
                rx.extend(chunk)
            except socket.error as ex:
                _LOGGER.debug("%s: socket error: %s", self.ipaddr, ex)
                pass
            finally:
                self._socket.setblocking(1)
        return rx

    def getClock(self):
        msg = bytearray([0x11, 0x1A, 0x1B, 0x0F])
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(self._protocol.construct_message(msg))
            rx = self._read_msg(12)
        if len(rx) != 12:
            return
        year = rx[3] + 2000
        month = rx[4]
        date = rx[5]
        hour = rx[6]
        minute = rx[7]
        second = rx[8]
        # dayofweek = rx[9]
        try:
            dt = datetime.datetime(year, month, date, hour, minute, second)
        except:
            dt = None
        return dt

    def setClock(self):
        msg = bytearray([0x10, 0x14])
        now = datetime.datetime.now()
        msg.append(now.year - 2000)
        msg.append(now.month)
        msg.append(now.day)
        msg.append(now.hour)
        msg.append(now.minute)
        msg.append(now.second)
        msg.append(now.isoweekday())  # day of week
        msg.append(0x00)
        msg.append(0x0F)
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(self._protocol.construct_message(msg))
            # Setting the clock does not always respond so we
            # cycle the connection
            self.close()

    def setProtocol(self, protocol):
        if protocol == PROTOCOL_LEDENET_ORIGINAL:
            self._protocol = ProtocolLEDENETOriginal()
        elif protocol == PROTOCOL_LEDENET_8BYTE:
            self._protocol = ProtocolLEDENET8Byte()
        elif protocol == PROTOCOL_LEDENET_9BYTE:
            self._protocol = ProtocolLEDENET9Byte()
        else:
            raise ValueError(f"Invalid protocol: {protocol}")

    def setpresetpattern(self, pattern, speed):

        presetpattern.valtostr(pattern)
        if not presetpattern.valid(pattern):
            # print "Pattern must be between 0x25 and 0x38"
            raise Exception

        delay = utils.speedToDelay(speed)
        # print "speed {}, delay 0x{:02x}".format(speed,delay)
        pattern_set_msg = bytearray([0x61])
        pattern_set_msg.append(pattern)
        pattern_set_msg.append(delay)
        pattern_set_msg.append(0x0F)

        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(self._protocol.construct_message(pattern_set_msg))

    def getTimers(self):
        msg = bytearray([0x22, 0x2A, 0x2B, 0x0F])
        resp_len = 88
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(self._protocol.construct_message(msg))
            rx = self._read_msg(resp_len)
        if len(rx) != resp_len:
            print("response too short!")
            raise Exception

        # utils.dump_data(rx)
        start = 2
        timer_list = []
        # pass in the 14-byte timer structs
        for i in range(6):
            timer_bytes = rx[start:][:14]
            timer = ledtimer(timer_bytes)
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
            print("too many timers, truncating list")
            del timer_list[6:]

        # pad list to 6 with inactive timers
        if len(timer_list) != 6:
            for i in range(6 - len(timer_list)):
                timer_list.append(ledtimer())

        msg_start = bytearray([0x21])
        msg_end = bytearray([0x00, 0xF0])
        msg = bytearray()

        # build message
        msg.extend(msg_start)
        for t in timer_list:
            msg.extend(t.toBytes())
        msg.extend(msg_end)
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(self._protocol.construct_message(msg))
            # not sure what the resp is, prob some sort of ack?
            rx = self._read_msg(4)

    def setCustomPattern(self, rgb_list, speed, transition_type):
        # truncate if more than 16
        if len(rgb_list) > 16:
            print("too many colors, truncating list")
            del rgb_list[16:]

        # quit if too few
        if len(rgb_list) == 0:
            print("no colors, aborting")
            return

        msg = bytearray()

        first_color = True
        for rgb in rgb_list:
            if first_color:
                lead_byte = 0x51
                first_color = False
            else:
                lead_byte = 0
            r, g, b = rgb
            msg.extend(bytearray([lead_byte, r, g, b]))

        # pad out empty slots
        if len(rgb_list) != 16:
            for i in range(16 - len(rgb_list)):
                msg.extend(bytearray([0, 1, 2, 3]))

        msg.append(0x00)
        msg.append(utils.speedToDelay(speed))

        if transition_type == "gradual":
            msg.append(0x3A)
        elif transition_type == "jump":
            msg.append(0x3B)
        elif transition_type == "strobe":
            msg.append(0x3C)
        else:
            # unknown transition string: using 'gradual'
            msg.append(0x3A)
        msg.append(0xFF)
        msg.append(0x0F)

        with self._lock:
            self._connect_if_disconnected
            self._send_msg(self._protocol.construct_message(msg))

    def refreshState(self):
        return self.update_state()




# =======================================================================
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

    print(example_text.replace("%prog%", sys.argv[0]))


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
    sunrise:    time, (repeat | date), startBrightness, endBrightness, duration
    sunset:     time, (repeat | date), startBrightness, endBrightness, duration

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

    speed: Speed of the preset pattern transitions (0-100)

    startBrightness: starting brightness of warmlight (0-100)

    endBrightness: ending brightness of warmlight (0-100)

    duration: transition time in minutes

Example setting strings:
    "time:2130;repeat:0123456"
    "time:2130;date:2015-08-11"
    "time:1245;repeat:12345;color:123,345,23"
    "time:1245;repeat:12345;color:green"
    "time:1245;repeat:06;code:50;speed:30"
    "time:0345;date:2015-08-11;level:100"
    """

    print(timerhelp_text)


def processSetTimerArgs(parser, args):
    mode = args[1]
    num = args[0]
    settings = args[2]

    if not num.isdigit() or int(num) > 6 or int(num) < 1:
        parser.error("Timer number must be between 1 and 6")

    # create a dict from the settings string
    settings_list = settings.split(";")
    settings_dict = {}
    for s in settings_list:
        pair = s.split(":")
        key = pair[0].strip().lower()
        val = ""
        if len(pair) > 1:
            val = pair[1].strip().lower()
        settings_dict[key] = val

    keys = list(settings_dict.keys())
    timer = ledtimer()

    if mode == "inactive":
        # no setting needed
        timer.setActive(False)

    elif mode in [
        "poweroff",
        "default",
        "color",
        "preset",
        "warmwhite",
        "sunrise",
        "sunset",
    ]:
        timer.setActive(True)

        if "time" not in keys:
            parser.error("This mode needs a time: {}".format(mode))
        if "repeat" in keys and "date" in keys:
            parser.error("This mode only a repeat or a date, not both: {}".format(mode))

        # validate time format
        if len(settings_dict["time"]) != 4 or not settings_dict["time"].isdigit():
            parser.error("time must be a 4 digits")
        hour = int(settings_dict["time"][0:2:])
        minute = int(settings_dict["time"][2:4:])
        if hour > 23:
            parser.error("timer hour can't be greater than 23")
        if minute > 59:
            parser.error("timer minute can't be greater than 59")

        timer.setTime(hour, minute)

        # validate date format
        if "repeat" not in keys and "date" not in keys:
            # Generate date for next occurance of time
            print("No time or repeat given. Defaulting to next occurance of time")
            now = datetime.datetime.now()
            dt = now.replace(hour=hour, minute=minute)
            if utils.date_has_passed(dt):
                dt = dt + datetime.timedelta(days=1)
            # settings_dict["date"] = date
            timer.setDate(dt.year, dt.month, dt.day)
        elif "date" in keys:
            try:
                dt = datetime.datetime.strptime(settings_dict["date"], "%Y-%m-%d")
                timer.setDate(dt.year, dt.month, dt.day)
            except ValueError:
                parser.error("date is not properly formatted: YYYY-MM-DD")

        # validate repeat format
        if "repeat" in keys:
            if len(settings_dict["repeat"]) == 0:
                parser.error("Must specify days to repeat")
            days = set()
            for c in list(settings_dict["repeat"]):
                if c not in ["0", "1", "2", "3", "4", "5", "6"]:
                    parser.error("repeat can only contain digits 0-6")
                days.add(int(c))

            repeat = 0
            if 0 in days:
                repeat |= ledtimer.Su
            if 1 in days:
                repeat |= ledtimer.Mo
            if 2 in days:
                repeat |= ledtimer.Tu
            if 3 in days:
                repeat |= ledtimer.We
            if 4 in days:
                repeat |= ledtimer.Th
            if 5 in days:
                repeat |= ledtimer.Fr
            if 6 in days:
                repeat |= ledtimer.Sa
            timer.setRepeatMask(repeat)

        if mode == "default":
            timer.setModeDefault()

        if mode == "poweroff":
            timer.setModeTurnOff()

        if mode == "color":
            if "color" not in keys:
                parser.error("color mode needs a color setting")
            # validate color val
            c = utils.color_object_to_tuple(settings_dict["color"])
            if c is None:
                parser.error("Invalid color value: {}".format(settings_dict["color"]))
            timer.setModeColor(c[0], c[1], c[2])

        if mode == "preset":
            if "code" not in keys:
                parser.error("preset mode needs a code: {}".format(mode))
            if "speed" not in keys:
                parser.error("preset mode needs a speed: {}".format(mode))
            code = settings_dict["code"]
            speed = settings_dict["speed"]
            if not speed.isdigit() or int(speed) > 100:
                parser.error("preset speed must be a percentage (0-100)")
            if not code.isdigit() or not presetpattern.valid(int(code)):
                parser.error("preset code must be in valid range")
            timer.setModePresetPattern(int(code), int(speed))

        if mode == "warmwhite":
            if "level" not in keys:
                parser.error("warmwhite mode needs a level: {}".format(mode))
            level = settings_dict["level"]
            if not level.isdigit() or int(level) > 100:
                parser.error("warmwhite level must be a percentage (0-100)")
            timer.setModeWarmWhite(int(level))

        if mode == "sunrise" or mode == "sunset":
            if "startbrightness" not in keys:
                parser.error(
                    "{} mode needs a startBrightness (0% -> 100%)".format(mode)
                )
            startBrightness = int(settings_dict["startbrightness"])

            if "endbrightness" not in keys:
                parser.error("{} mode needs an endBrightness (0% -> 100%)".format(mode))
            endBrightness = int(settings_dict["endbrightness"])

            if "duration" not in keys:
                parser.error("{} mode needs a duration (minutes)".format(mode))
            duration = int(settings_dict["duration"])

            if mode == "sunrise":
                timer.setModeSunrise(startBrightness, endBrightness, duration)

            elif mode == "sunset":
                timer.setModeSunset(startBrightness, endBrightness, duration)

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
        str_list = color_list_str.split(" ")
        color_list = []
        for s in str_list:
            c = utils.color_object_to_tuple(s)
            if c is not None:
                color_list.append(c)
            else:
                raise Exception

    except:
        parser.error(
            "COLORLIST isn't formatted right.  It should be a space separated list of RGB tuples, color names or web hex values"
        )

    return args[0], speed, color_list


def parseArgs():

    parser = OptionParser()

    parser.description = "A utility to control Flux WiFi LED Bulbs. "
    # parser.description += ""
    # parser.description += "."
    power_group = OptionGroup(parser, "Power options (mutually exclusive)")
    mode_group = OptionGroup(parser, "Mode options (mutually exclusive)")
    info_group = OptionGroup(parser, "Program help and information option")
    other_group = OptionGroup(parser, "Other options")

    parser.add_option_group(info_group)
    info_group.add_option(
        "-e",
        "--examples",
        action="store_true",
        dest="showexamples",
        default=False,
        help="Show usage examples",
    )
    info_group.add_option(
        "",
        "--timerhelp",
        action="store_true",
        dest="timerhelp",
        default=False,
        help="Show detailed help for setting timers",
    )
    info_group.add_option(
        "-l",
        "--listpresets",
        action="store_true",
        dest="listpresets",
        default=False,
        help="List preset codes",
    )
    info_group.add_option(
        "--listcolors",
        action="store_true",
        dest="listcolors",
        default=False,
        help="List color names",
    )

    parser.add_option(
        "-s",
        "--scan",
        action="store_true",
        dest="scan",
        default=False,
        help="Search for bulbs on local network",
    )
    parser.add_option(
        "-S",
        "--scanresults",
        action="store_true",
        dest="scanresults",
        default=False,
        help="Operate on scan results instead of arg list",
    )
    power_group.add_option(
        "-1",
        "--on",
        action="store_true",
        dest="on",
        default=False,
        help="Turn on specified bulb(s)",
    )
    power_group.add_option(
        "-0",
        "--off",
        action="store_true",
        dest="off",
        default=False,
        help="Turn off specified bulb(s)",
    )
    parser.add_option_group(power_group)

    mode_group.add_option(
        "-c",
        "--color",
        dest="color",
        default=None,
        help="Set single color mode.  Can be either color name, web hex, or comma-separated RGB triple",
        metavar="COLOR",
    )
    mode_group.add_option(
        "-w",
        "--warmwhite",
        dest="ww",
        default=None,
        help="Set warm white mode (LEVELWW is percent)",
        metavar="LEVELWW",
        type="int",
    )
    mode_group.add_option(
        "",
        "--coldwhite",
        dest="cw",
        default=None,
        help="Set cold white mode (LEVELCW is percent)",
        metavar="LEVELCW",
        type="int",
    )
    mode_group.add_option(
        "",
        "--CCT",
        dest="cct",
        default=None,
        help="Temperture and brightness (CCT is percent, brightness percent)",
        metavar="LEVELCCT",
        type="int",
        nargs=2,
    )
    mode_group.add_option(
        "-p",
        "--preset",
        dest="preset",
        default=None,
        help="Set preset pattern mode (SPEED is percent)",
        metavar="CODE SPEED",
        type="int",
        nargs=2,
    )
    mode_group.add_option(
        "-C",
        "--custom",
        dest="custom",
        metavar="TYPE SPEED COLORLIST",
        default=None,
        nargs=3,
        help="Set custom pattern mode. "
        + "TYPE should be jump, gradual, or strobe. SPEED is percent. "
        + "COLORLIST is a space-separated list of color names, web hex values, or comma-separated RGB triples",
    )
    parser.add_option_group(mode_group)

    parser.add_option(
        "-i",
        "--info",
        action="store_true",
        dest="info",
        default=False,
        help="Info about bulb(s) state",
    )
    parser.add_option(
        "",
        "--getclock",
        action="store_true",
        dest="getclock",
        default=False,
        help="Get clock",
    )
    parser.add_option(
        "",
        "--setclock",
        action="store_true",
        dest="setclock",
        default=False,
        help="Set clock to same as current time on this computer",
    )
    parser.add_option(
        "-t",
        "--timers",
        action="store_true",
        dest="showtimers",
        default=False,
        help="Show timers",
    )
    parser.add_option(
        "-T",
        "--settimer",
        dest="settimer",
        metavar="NUM MODE SETTINGS",
        default=None,
        nargs=3,
        help="Set timer. "
        + "NUM: number of the timer (1-6). "
        + "MODE: inactive, poweroff, default, color, preset, or warmwhite. "
        + "SETTINGS: a string of settings including time, repeatdays or date, "
        + "and other mode specific settings.   Use --timerhelp for more details.",
    )

    parser.add_option(
        "--protocol",
        dest="protocol",
        default=None,
        metavar="PROTOCOL",
        help="Set the device protocol. Currently only supports LEDENET",
    )

    other_group.add_option(
        "-v",
        "--volatile",
        action="store_true",
        dest="volatile",
        default=False,
        help="Don't persist mode setting with hard power cycle (RGB and WW modes only).",
    )
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
        for c in range(
            presetpattern.seven_color_cross_fade, presetpattern.seven_color_jumping + 1
        ):
            print("{:2} {}".format(c, presetpattern.valtostr(c)))
        sys.exit(0)

    global webcolors_available
    if options.listcolors:
        if webcolors_available:
            for c in utils.get_color_names_list():
                print("{}, ".format(c))
            print("")
        else:
            print(
                "webcolors package doesn't seem to be installed. No color names available"
            )
        sys.exit(0)

    if options.settimer:
        new_timer = processSetTimerArgs(parser, options.settimer)
        options.new_timer = new_timer
    else:
        options.new_timer = None

    mode_count = 0
    if options.color:
        mode_count += 1
    if options.ww:
        mode_count += 1
    if options.cw:
        mode_count += 1
    if options.cct:
        mode_count += 1
    if options.preset:
        mode_count += 1
    if options.custom:
        mode_count += 1
    if mode_count > 1:
        parser.error(
            "options --color, --*white, --preset, --CCT, and --custom are mutually exclusive"
        )

    if options.on and options.off:
        parser.error("options --on and --off are mutually exclusive")

    if options.custom:
        options.custom = processCustomArgs(parser, options.custom)

    if options.color:
        options.color = utils.color_object_to_tuple(options.color)
        if options.color is None:
            parser.error("bad color specification")

    if options.preset:
        if not presetpattern.valid(options.preset[0]):
            parser.error("Preset code is not in range")

    # asking for timer info, implicitly gets the state
    if options.showtimers:
        options.info = True

    op_count = mode_count
    if options.on:
        op_count += 1
    if options.off:
        op_count += 1
    if options.info:
        op_count += 1
    if options.getclock:
        op_count += 1
    if options.setclock:
        op_count += 1
    if options.listpresets:
        op_count += 1
    if options.settimer:
        op_count += 1

    if (not options.scan or options.scanresults) and (op_count == 0):
        parser.error("An operation must be specified")

    # if we're not scanning, IP addresses must be specified as positional args
    if not options.scan and not options.scanresults and not options.listpresets:
        if len(args) == 0:
            parser.error(
                "You must specify at least one IP address as an argument, or use scan results"
            )

    return (options, args)


# -------------------------------------------
def main():

    (options, args) = parseArgs()

    if options.scan:
        scanner = bulbscanner()
        scanner.scan(timeout=2)
        bulb_info_list = scanner.getBulbInfo()
        # we have a list of buld info dicts
        addrs = []
        if options.scanresults and len(bulb_info_list) > 0:
            for b in bulb_info_list:
                addrs.append(b["ipaddr"])
        else:
            print("{} bulbs found".format(len(bulb_info_list)))
            for b in bulb_info_list:
                print("  {} {}".format(b["id"], b["ipaddr"]))
            sys.exit(0)

    else:
        addrs = args
        bulb_info_list = []
        for addr in args:
            info = dict()
            info["ipaddr"] = addr
            info["id"] = "Unknown ID"

            bulb_info_list.append(info)

    # now we have our bulb list, perform same operation on all of them
    for info in bulb_info_list:
        try:
            bulb = WifiLedBulb(info["ipaddr"])
        except Exception as e:
            print("Unable to connect to bulb at [{}]: {}".format(info["ipaddr"], e))
            continue

        if options.getclock:
            print("{} [{}] {}".format(info["id"], info["ipaddr"], bulb.getClock()))

        if options.setclock:
            bulb.setClock()

        if options.protocol:
            bulb.setProtocol(options.protocol)

        if options.ww is not None:
            print("Setting warm white mode, level: {}%".format(options.ww))
            bulb.setWarmWhite(options.ww, not options.volatile)

        if options.cw is not None:
            print("Setting cold white mode, level: {}%".format(options.cw))
            bulb.setColdWhite(options.cw, not options.volatile)

        if options.cct is not None:
            print(
                "Setting LED temperature {}K and brightness: {}%".format(
                    options.cct[0], options.cct[1]
                )
            )
            bulb.setWhiteTemperature(
                options.cct[0], options.cct[1], not options.volatile
            )

        if options.color is not None:
            print(
                "Setting color RGB:{}".format(options.color),
            )
            name = utils.color_tuple_to_string(options.color)
            if name is None:
                print()
            else:
                print("[{}]".format(name))
            if len(options.color) == 3:
                bulb.setRgb(
                    options.color[0],
                    options.color[1],
                    options.color[2],
                    not options.volatile,
                )
            elif len(options.color) == 4:
                bulb.setRgbw(
                    options.color[0],
                    options.color[1],
                    options.color[2],
                    options.color[3],
                    not options.volatile,
                )
            elif len(options.color) == 5:
                bulb.setRgbw(
                    options.color[0],
                    options.color[1],
                    options.color[2],
                    options.color[3],
                    not options.volatile,
                    None,
                    options.color[4],
                )

        elif options.custom is not None:
            bulb.setCustomPattern(
                options.custom[2], options.custom[1], options.custom[0]
            )
            print(
                "Setting custom pattern: {}, Speed={}%, {}".format(
                    options.custom[0], options.custom[1], options.custom[2]
                )
            )

        elif options.preset is not None:
            print(
                "Setting preset pattern: {}, Speed={}%".format(
                    presetpattern.valtostr(options.preset[0]), options.preset[1]
                )
            )
            bulb.setpresetpattern(options.preset[0], options.preset[1])

        if options.on:
            print("Turning on bulb at {}".format(bulb.ipaddr))
            bulb.turnOn()
        elif options.off:
            print("Turning off bulb at {}".format(bulb.ipaddr))
            bulb.turnOff()

        if options.info:
            bulb.update_state()
            print("{} [{}] {}".format(info["id"], info["ipaddr"], bulb))

        if options.settimer:
            timers = bulb.getTimers()
            num = int(options.settimer[0])
            print("New Timer ---- #{}: {}".format(num, options.new_timer))
            if options.new_timer.isExpired():
                print("[timer is already expired, will be deactivated]")
            timers[num - 1] = options.new_timer
            bulb.sendTimers(timers)

        if options.showtimers:
            timers = bulb.getTimers()
            num = 0
            for t in timers:
                num += 1
                print("  Timer #{}: {}".format(num, t))
            print("")

    sys.exit(0)


if __name__ == "__main__":
    main()