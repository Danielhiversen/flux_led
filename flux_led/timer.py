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
from utils import utils
from pattern import presetpattern


class builtintimer:
    sunrise = 0xA1
    sunset = 0xA2

    @staticmethod
    def valid(byte_value):
        return byte_value == builtintimer.sunrise or byte_value == builtintimer.sunset

    @staticmethod
    def valtostr(pattern):
        for key, value in list(builtintimer.__dict__.items()):
            if type(value) is int and value == pattern:
                return key.replace("_", " ").title()
        return None


class ledtimer:
    Mo = 0x02
    Tu = 0x04
    We = 0x08
    Th = 0x10
    Fr = 0x20
    Sa = 0x40
    Su = 0x80
    Everyday = Mo | Tu | We | Th | Fr | Sa | Su
    Weekdays = Mo | Tu | We | Th | Fr
    Weekend = Sa | Su

    @staticmethod
    def dayMaskToStr(mask):
        for key, value in ledtimer.__dict__.items():
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
        elif self.year != 0 and self.month != 0 and self.day != 0:
            dt = datetime.datetime(
                self.year, self.month, self.day, self.hour, self.minute
            )
            if utils.date_has_passed(dt):
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

    def setModeSunrise(self, startBrightness, endBrightness, duration):
        self.mode = "sunrise"
        self.turn_on = True
        self.pattern_code = builtintimer.sunrise
        self.brightness_start = utils.percentToByte(startBrightness)
        self.brightness_end = utils.percentToByte(endBrightness)
        self.warmth_level = utils.percentToByte(endBrightness)
        self.duration = int(duration)

    def setModeSunset(self, startBrightness, endBrightness, duration):
        self.mode = "sunrise"
        self.turn_on = True
        self.pattern_code = builtintimer.sunset
        self.brightness_start = utils.percentToByte(startBrightness)
        self.brightness_end = utils.percentToByte(endBrightness)
        self.warmth_level = utils.percentToByte(endBrightness)
        self.duration = int(duration)

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
        13: 0f = turn off, f0 = turn on
    """

    def fromBytes(self, bytes):
        # utils.dump_bytes(bytes)
        self.red = 0
        self.green = 0
        self.blue = 0
        if bytes[0] == 0xF0:
            self.active = True
        else:
            self.active = False
        self.year = bytes[1] + 2000
        self.month = bytes[2]
        self.day = bytes[3]
        self.hour = bytes[4]
        self.minute = bytes[5]
        self.repeat_mask = bytes[7]
        self.pattern_code = bytes[8]

        if self.pattern_code == 0x00:
            self.mode = "default"
        elif self.pattern_code == 0x61:
            self.mode = "color"
            self.red = bytes[9]
            self.green = bytes[10]
            self.blue = bytes[11]
        elif builtintimer.valid(self.pattern_code):
            self.mode = builtintimer.valtostr(self.pattern_code)
            self.duration = bytes[9]  # same byte as red
            self.brightness_start = bytes[10]  # same byte as green
            self.brightness_end = bytes[11]  # same byte as blue
        elif presetpattern.valid(self.pattern_code):
            self.mode = "preset"
            self.delay = bytes[9]  # same byte as red
        else:
            self.mode = "unknown"

        self.warmth_level = bytes[12]
        if self.warmth_level != 0:
            self.mode = "ww"

        if bytes[13] == 0xF0:
            self.turn_on = True
        else:
            self.turn_on = False
            self.mode = "off"

    def toBytes(self):
        bytes = bytearray(14)
        if not self.active:
            bytes[0] = 0x0F
            # quit since all other zeros is good
            return bytes

        bytes[0] = 0xF0

        if self.year >= 2000:
            bytes[1] = self.year - 2000
        else:
            bytes[1] = self.year
        bytes[2] = self.month
        bytes[3] = self.day
        bytes[4] = self.hour
        bytes[5] = self.minute
        # what is 6?
        bytes[7] = self.repeat_mask

        if not self.turn_on:
            bytes[13] = 0x0F
            return bytes
        bytes[13] = 0xF0

        bytes[8] = self.pattern_code
        if presetpattern.valid(self.pattern_code):
            bytes[9] = self.delay
            bytes[10] = 0
            bytes[11] = 0
        elif builtintimer.valid(self.pattern_code):
            bytes[9] = self.duration
            bytes[10] = self.brightness_start
            bytes[11] = self.brightness_end
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

        txt += "{:02}:{:02}  ".format(self.hour, self.minute)

        if self.repeat_mask == 0:
            txt += "Once: {:04}-{:02}-{:02}".format(self.year, self.month, self.day)
        else:
            bits = [
                ledtimer.Su,
                ledtimer.Mo,
                ledtimer.Tu,
                ledtimer.We,
                ledtimer.Th,
                ledtimer.Fr,
                ledtimer.Sa,
            ]
            for b in bits:
                if self.repeat_mask & b:
                    txt += ledtimer.dayMaskToStr(b)
                else:
                    txt += "--"
            txt += "  "

        txt += "  "
        if self.pattern_code == 0x61:
            if self.warmth_level != 0:
                txt += "Warm White: {}%".format(utils.byteToPercent(self.warmth_level))
            else:
                color_str = utils.color_tuple_to_string(
                    (self.red, self.green, self.blue)
                )
                txt += "Color: {}".format(color_str)

        elif presetpattern.valid(self.pattern_code):
            pat = presetpattern.valtostr(self.pattern_code)
            speed = utils.delayToSpeed(self.delay)
            txt += "{} (Speed:{}%)".format(pat, speed)

        elif builtintimer.valid(self.pattern_code):
            type = builtintimer.valtostr(self.pattern_code)

            txt += "{} (Duration:{} minutes, Brightness: {}% -> {}%)".format(
                type,
                self.duration,
                utils.byteToPercent(self.brightness_start),
                utils.byteToPercent(self.brightness_end),
            )

        return txt

