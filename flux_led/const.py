"""FluxLED Models Database."""

from enum import Enum


class LevelWriteMode(Enum):
    ALL = 0x00
    COLORS = 0xF0
    WHITES = 0x0F


PRESET_MUSIC_MODE = 0x62

ATTR_IPADDR = "ipaddr"
ATTR_ID = "id"
ATTR_MODEL = "model"
ATTR_MODEL_NUM = "model_num"
ATTR_VERSION_NUM = "version_num"
ATTR_FIRMWARE_DATE = "firmware_date"
ATTR_MODEL_INFO = "model_info"
ATTR_MODEL_DESCRIPTION = "model_description"

# Color modes
COLOR_MODE_DIM = "DIM"
COLOR_MODE_CCT = "CCT"
COLOR_MODE_RGB = "RGB"
COLOR_MODE_RGBW = "RGBW"
COLOR_MODE_RGBWW = "RGBWW"
COLOR_MODE_ADDRESSABLE = "ADDRESSABLE"

STATE_CHANGE_LATENCY = 1
ADDRESSABLE_STATE_CHANGE_LATENCY = 5
MIN_TEMP = 2700
MAX_TEMP = 6500

WRITE_ALL_COLORS = (LevelWriteMode.ALL, LevelWriteMode.COLORS)
WRITE_ALL_WHITES = (LevelWriteMode.ALL, LevelWriteMode.WHITES)

# Modes
MODE_SWITCH = "switch"
MODE_COLOR = "color"
MODE_WW = "ww"
MODE_CUSTOM = "custom"
MODE_MUSIC = "music"
MODE_PRESET = "preset"

# Transitions
TRANSITION_JUMP = "jump"
TRANSITION_STROBE = "strobe"
TRANSITION_GRADUAL = "gradual"

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


DEFAULT_MODE = COLOR_MODE_RGB


# States
STATE_HEAD = "head"
STATE_MODEL_NUM = "model_num"
STATE_POWER_STATE = "power_state"
STATE_PRESET_PATTERN = "preset_pattern"
STATE_MODE = "mode"
STATE_SPEED = "speed"
STATE_RED = "red"
STATE_GREEN = "green"
STATE_BLUE = "blue"
STATE_WARM_WHITE = "warm_white"
STATE_VERSION_NUMBER = "version_number"
STATE_COOL_WHITE = "cool_white"
STATE_COLOR_MODE = "color_mode"
STATE_CHECK_SUM = "check_sum"

CHANNEL_STATES = {
    STATE_RED,
    STATE_GREEN,
    STATE_BLUE,
    STATE_WARM_WHITE,
    STATE_COOL_WHITE,
}


EFFECT_RANDOM = "random"
