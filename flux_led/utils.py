import ast
import colorsys
import contextlib
import datetime
from typing import Iterable, List, Optional, Tuple, cast

import webcolors  # type: ignore

from .const import MAX_TEMP, MIN_TEMP


class utils:
    @staticmethod
    def color_object_to_tuple(color) -> Optional[Tuple[int, ...]]:

        # see if it's already a color tuple
        if type(color) is tuple and len(color) in [3, 4, 5]:
            return color

        # can't convert non-string
        if type(color) is not str:
            return None
        color = color.strip()

        # try to convert from an english name
        with contextlib.suppress(Exception):
            return cast(Tuple[int, int, int], webcolors.name_to_rgb(color))

        # try to convert an web hex code
        with contextlib.suppress(Exception):
            return cast(
                Tuple[int, int, int],
                webcolors.hex_to_rgb(webcolors.normalize_hex(color)),
            )

        # try to convert a string RGB tuple
        with contextlib.suppress(Exception):
            val = ast.literal_eval(color)
            if type(val) is not tuple or len(val) not in [3, 4, 5]:
                raise Exception
            return val

        return None

    @staticmethod
    def color_tuple_to_string(rgb) -> str:
        # try to convert to an english name
        try:
            return webcolors.rgb_to_name(rgb)
        except Exception:
            # print e
            pass
        return str(rgb)

    @staticmethod
    def get_color_names_list() -> List[str]:
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
    def date_has_passed(dt) -> bool:
        delta = dt - datetime.datetime.now()
        return delta.total_seconds() < 0

    @staticmethod
    def dump_bytes(bytes) -> None:
        print("".join(f"{x:02x} " for x in bytearray(bytes)))

    @staticmethod
    def raw_state_to_dec(rx: Iterable[int]) -> str:
        raw_state_str = ""
        for _r in rx:
            raw_state_str += str(_r) + ","
        return raw_state_str

    max_delay = 0x1F

    @staticmethod
    def delayToSpeed(delay: int) -> int:
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
    def speedToDelay(speed: int) -> int:
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
    def byteToPercent(byte: int) -> int:
        if byte > 255:
            byte = 255
        if byte < 0:
            byte = 0
        return int((byte * 100) / 255)

    @staticmethod
    def percentToByte(percent: int) -> int:
        if percent > 100:
            percent = 100
        if percent < 0:
            percent = 0
        return int((percent * 255) / 100)


def rgbwc_to_rgbcw(
    rgbwc_data: Tuple[int, int, int, int, int]
) -> Tuple[int, int, int, int, int]:
    r, g, b, w, c = rgbwc_data
    return r, g, b, c, w


def rgbcw_to_rgbwc(
    rgbcw_data: Tuple[int, int, int, int, int]
) -> Tuple[int, int, int, int, int]:
    r, g, b, c, w = rgbcw_data
    return r, g, b, w, c


def _adjust_brightness(
    current_brightness: int,
    new_brightness: int,
    color_brightness: int,
    cw_brightness: int,
    ww_brightness: int,
) -> Tuple[int, int, int]:
    if new_brightness < current_brightness:
        change_brightness_pct = (
            current_brightness - new_brightness
        ) / current_brightness
        ww_brightness = round(ww_brightness * (1 - change_brightness_pct))
        color_brightness = round(color_brightness * (1 - change_brightness_pct))
        cw_brightness = round(cw_brightness * (1 - change_brightness_pct))
    else:
        change_brightness_pct = (new_brightness - current_brightness) / (
            255 - current_brightness
        )
        ww_brightness = round(
            (255 - ww_brightness) * change_brightness_pct + ww_brightness
        )
        color_brightness = round(
            (255 - color_brightness) * change_brightness_pct + color_brightness
        )
        cw_brightness = round(
            (255 - cw_brightness) * change_brightness_pct + cw_brightness
        )

    return color_brightness, cw_brightness, ww_brightness


def rgbw_brightness(
    rgbw_data: Tuple[int, int, int, int],
    brightness: Optional[int] = None,
) -> Tuple[int, int, int, int]:
    """Convert rgbw to brightness."""
    original_r, original_g, original_b = rgbw_data[0:3]
    h, s, v = colorsys.rgb_to_hsv(original_r / 255, original_g / 255, original_b / 255)
    color_brightness = round(v * 255)
    ww_brightness = rgbw_data[3]
    current_brightness = round((color_brightness + ww_brightness) / 2)

    if not brightness or brightness == current_brightness:
        return rgbw_data

    if brightness < current_brightness:
        change_brightness_pct = (current_brightness - brightness) / current_brightness
        ww_brightness = round(ww_brightness * (1 - change_brightness_pct))
        color_brightness = round(color_brightness * (1 - change_brightness_pct))

    else:
        change_brightness_pct = (brightness - current_brightness) / (
            255 - current_brightness
        )
        ww_brightness = round(
            (255 - ww_brightness) * change_brightness_pct + ww_brightness
        )
        color_brightness = round(
            (255 - color_brightness) * change_brightness_pct + color_brightness
        )

    r, g, b = colorsys.hsv_to_rgb(h, s, color_brightness / 255)
    return (round(r * 255), round(g * 255), round(b * 255), ww_brightness)


def rgbww_brightness(
    rgbww_data: Tuple[int, int, int, int, int],
    brightness: Optional[int] = None,
) -> Tuple[int, int, int, int, int]:
    """Convert rgbww to brightness."""
    original_r, original_g, original_b = rgbww_data[0:3]
    h, s, v = colorsys.rgb_to_hsv(original_r / 255, original_g / 255, original_b / 255)
    color_brightness = round(v * 255)
    ww_brightness = rgbww_data[3]
    cw_brightness = rgbww_data[4]
    current_brightness = round((color_brightness + ww_brightness + cw_brightness) / 3)

    if not brightness or brightness == current_brightness:
        return rgbww_data

    color_brightness, cw_brightness, ww_brightness = _adjust_brightness(
        current_brightness, brightness, color_brightness, cw_brightness, ww_brightness
    )
    r, g, b = colorsys.hsv_to_rgb(h, s, color_brightness / 255)
    return (
        round(r * 255),
        round(g * 255),
        round(b * 255),
        ww_brightness,
        cw_brightness,
    )


def rgbcw_brightness(
    rgbcw_data: Tuple[int, int, int, int, int],
    brightness: Optional[int] = None,
) -> Tuple[int, int, int, int, int]:
    """Convert rgbww to brightness."""
    original_r, original_g, original_b = rgbcw_data[0:3]
    h, s, v = colorsys.rgb_to_hsv(original_r / 255, original_g / 255, original_b / 255)
    color_brightness = round(v * 255)
    cw_brightness = rgbcw_data[3]
    ww_brightness = rgbcw_data[4]
    current_brightness = round((color_brightness + ww_brightness + cw_brightness) / 3)

    if not brightness or brightness == current_brightness:
        return rgbcw_data

    color_brightness, cw_brightness, ww_brightness = _adjust_brightness(
        current_brightness, brightness, color_brightness, cw_brightness, ww_brightness
    )
    r, g, b = colorsys.hsv_to_rgb(h, s, color_brightness / 255)
    return (
        round(r * 255),
        round(g * 255),
        round(b * 255),
        cw_brightness,
        ww_brightness,
    )


def color_temp_to_white_levels(temperature: int, brightness: float) -> Tuple[int, int]:
    # Assume output temperature of between 2700 and 6500 Kelvin, and scale
    # the warm and cold LEDs linearly to provide that
    if not (MIN_TEMP <= temperature <= MAX_TEMP):
        raise ValueError(
            f"Temperature of {temperature} is not valid and must be between {MIN_TEMP} and {MAX_TEMP}"
        )
    if not (0 <= brightness <= 255):
        raise ValueError(
            f"Brightness of {brightness} is not valid and must be between 0 and 255"
        )
    brightness = round(brightness / 255, 2)
    warm = ((MAX_TEMP - temperature) / (MAX_TEMP - MIN_TEMP)) * (brightness)
    cold = (brightness) - warm
    return round(255 * cold), round(255 * warm)


def white_levels_to_color_temp(warm_white: int, cool_white: int) -> Tuple[int, int]:
    if not (0 <= warm_white <= 255):
        raise ValueError(
            f"Warm White of {warm_white} is not valid and must be between 0 and 255"
        )
    if not (0 <= cool_white <= 255):
        raise ValueError(
            f"Cool White of {cool_white} is not valid and must be between 0 and 255"
        )
    warm = warm_white / 255
    cold = cool_white / 255
    brightness = warm + cold
    if brightness == 0:
        temperature: float = MIN_TEMP
    else:
        temperature = ((cold / brightness) * (MAX_TEMP - MIN_TEMP)) + MIN_TEMP
    return round(temperature), min(255, round(brightness * 255))
