"""FluxLED Models Database."""

from enum import Enum
import sys

if sys.version_info >= (3, 8):
    from typing import Final  # pylint: disable=no-name-in-module
else:
    from typing_extensions import Final


class LevelWriteMode(Enum):
    ALL = 0x00
    COLORS = 0xF0
    WHITES = 0x0F


class MultiColorEffects(Enum):
    STATIC = 0x01
    RUNNING_WATER = 0x02
    STROBE = 0x03
    JUMP = 0x04
    BREATHING = 0x05


PRESET_MUSIC_MODE: Final = 0x62
PRESET_MUSIC_MODE_LEGACY: Final = 0x5D

ATTR_IPADDR: Final = "ipaddr"
ATTR_ID: Final = "id"
ATTR_MODEL: Final = "model"
ATTR_MODEL_NUM: Final = "model_num"
ATTR_VERSION_NUM: Final = "version_num"
ATTR_FIRMWARE_DATE: Final = "firmware_date"
ATTR_MODEL_INFO: Final = "model_info"
ATTR_MODEL_DESCRIPTION: Final = "model_description"
ATTR_REMOTE_ACCESS_ENABLED: Final = "remote_access_enabled"
ATTR_REMOTE_ACCESS_HOST: Final = "remote_access_host"
ATTR_REMOTE_ACCESS_PORT: Final = "remote_access_port"


# Color modes
COLOR_MODE_DIM: Final = "DIM"
COLOR_MODE_CCT: Final = "CCT"
COLOR_MODE_RGB: Final = "RGB"
COLOR_MODE_RGBW: Final = "RGBW"
COLOR_MODE_RGBWW: Final = "RGBWW"
COLOR_MODE_ADDRESSABLE: Final = "ADDRESSABLE"

STATE_CHANGE_LATENCY: Final = 1
ADDRESSABLE_STATE_CHANGE_LATENCY: Final = 5
MIN_TEMP: Final = 2700
MAX_TEMP: Final = 6500

WRITE_ALL_COLORS = (LevelWriteMode.ALL, LevelWriteMode.COLORS)
WRITE_ALL_WHITES = (LevelWriteMode.ALL, LevelWriteMode.WHITES)

DEFAULT_RETRIES: Final = 2

# Modes
MODE_SWITCH: Final = "switch"
MODE_COLOR: Final = "color"
MODE_WW: Final = "ww"
MODE_CUSTOM: Final = "custom"
MODE_MUSIC: Final = "music"
MODE_PRESET: Final = "preset"

# Transitions
TRANSITION_JUMP: Final = "jump"
TRANSITION_STROBE: Final = "strobe"
TRANSITION_GRADUAL: Final = "gradual"

STATIC_MODES = {MODE_COLOR, MODE_WW}

# Non light device models
MODEL_NUMS_SWITCHS = {0x19, 0x93, 0x0B, 0x93, 0x94, 0x95, 0x96, 0x97}

COLOR_MODES_RGB = {COLOR_MODE_RGB, COLOR_MODE_RGBW, COLOR_MODE_RGBWW}
COLOR_MODES_RGB_CCT = {  # AKA Split RGB & CCT modes used for bulbs/lamps
    COLOR_MODE_RGB,
    COLOR_MODE_CCT,
}
COLOR_MODES_RGB_W = {  # AKA RGB/W in the Magic Home Pro app
    COLOR_MODE_RGB,
    COLOR_MODE_DIM,
}
COLOR_MODES_ADDRESSABLE = {COLOR_MODE_RGB}


DEFAULT_MODE: Final = COLOR_MODE_RGB


# States
STATE_HEAD: Final = "head"
STATE_MODEL_NUM: Final = "model_num"
STATE_POWER_STATE: Final = "power_state"
STATE_PRESET_PATTERN: Final = "preset_pattern"
STATE_MODE: Final = "mode"
STATE_SPEED: Final = "speed"
STATE_RED: Final = "red"
STATE_GREEN: Final = "green"
STATE_BLUE: Final = "blue"
STATE_WARM_WHITE: Final = "warm_white"
STATE_VERSION_NUMBER: Final = "version_number"
STATE_COOL_WHITE: Final = "cool_white"
STATE_COLOR_MODE: Final = "color_mode"
STATE_CHECK_SUM: Final = "check_sum"

CHANNEL_STATES = {
    STATE_RED,
    STATE_GREEN,
    STATE_BLUE,
    STATE_WARM_WHITE,
    STATE_COOL_WHITE,
}


EFFECT_RANDOM = "random"
EFFECT_MUSIC = "music"
