from __future__ import print_function

import ast
import datetime

import webcolors

from .scanner import BulbScanner


class utils:
    @staticmethod
    def color_object_to_tuple(color):

        # see if it's already a color tuple
        if type(color) is tuple and len(color) in [3, 4, 5]:
            return color

        # can't convert non-string
        if type(color) is not str:
            return None
        color = color.strip()

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
            if type(val) is not tuple or len(val) not in [3, 4, 5]:
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
        except Exception:
            # print e
            pass
        return str(rgb)

    @staticmethod
    def get_color_names_list():
        names = set()
        for key in list(webcolors.CSS2_HEX_TO_NAMES.keys()):
            names.add(webcolors.CSS2_HEX_TO_NAMES[key])
        for key in list(webcolors.CSS21_HEX_TO_NAMES.keys()):
            names.add(webcolors.CSS21_HEX_TO_NAMES[key])
        for key in list(webcolors.CSS3_HEX_TO_NAMES.keys()):
            names.add(webcolors.CSS3_HEX_TO_NAMES[key])
        for key in list(webcolors.HTML4_HEX_TO_NAMES.keys()):
            names.add(webcolors.HTML4_HEX_TO_NAMES[key])
        return sorted(names)

    @staticmethod
    def date_has_passed(dt):
        delta = dt - datetime.datetime.now()
        return delta.total_seconds() < 0

    @staticmethod
    def dump_bytes(bytes):
        print("".join("{:02x} ".format(x) for x in bytearray(bytes)))

    @staticmethod
    def raw_state_to_dec(rx):
        raw_state_str = ""
        for _r in rx:
            raw_state_str += str(_r) + ","
        return raw_state_str

    max_delay = 0x1F

    @staticmethod
    def delayToSpeed(delay):
        # speed is 0-100, delay is 1-31
        # 1st translate delay to 0-30
        delay = delay - 1
        if delay > utils.max_delay - 1:
            delay = utils.max_delay - 1
        if delay < 0:
            delay = 0
        inv_speed = int((delay * 100) / (utils.max_delay - 1))
        speed = 100 - inv_speed
        return speed

    @staticmethod
    def speedToDelay(speed):
        # speed is 0-100, delay is 1-31
        if speed > 100:
            speed = 100
        if speed < 0:
            speed = 0
        inv_speed = 100 - speed
        delay = int((inv_speed * (utils.max_delay - 1)) / 100)
        # translate from 0-30 to 1-31
        delay = delay + 1
        return delay

    @staticmethod
    def byteToPercent(byte):
        if byte > 255:
            byte = 255
        if byte < 0:
            byte = 0
        return int((byte * 100) / 255)

    @staticmethod
    def percentToByte(percent):
        if percent > 100:
            percent = 100
        if percent < 0:
            percent = 0
        return int((percent * 255) / 100)
