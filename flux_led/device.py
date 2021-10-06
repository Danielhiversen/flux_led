from __future__ import print_function
from enum import Enum
import logging
import colorsys
import socket
import threading
import time
import select
import datetime

from .sock import _socket_retry
from .pattern import presetpattern
from .timer import (builtintimer, ledtimer)
from .utils import utils

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

_LOGGER = logging.getLogger(__name__)


class devicetype(Enum):
    Bulb = 0
    Switch = 1


class wifiledbulb:
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
        return devicetype.Switch if self.model_num == 0x97 else devicetype.Bulb

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
        if self.device_type == devicetype.Switch:
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


