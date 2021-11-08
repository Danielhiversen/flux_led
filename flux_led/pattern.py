EFFECT_RANDOM = "random"
EFFECT_COLORLOOP = "colorloop"
EFFECT_RED_FADE = "red_fade"
EFFECT_GREEN_FADE = "green_fade"
EFFECT_BLUE_FADE = "blue_fade"
EFFECT_YELLOW_FADE = "yellow_fade"
EFFECT_CYAN_FADE = "cyan_fade"
EFFECT_PURPLE_FADE = "purple_fade"
EFFECT_WHITE_FADE = "white_fade"
EFFECT_RED_GREEN_CROSS_FADE = "rg_cross_fade"
EFFECT_RED_BLUE_CROSS_FADE = "rb_cross_fade"
EFFECT_GREEN_BLUE_CROSS_FADE = "gb_cross_fade"
EFFECT_COLORSTROBE = "colorstrobe"
EFFECT_RED_STROBE = "red_strobe"
EFFECT_GREEN_STROBE = "green_strobe"
EFFECT_BLUE_STROBE = "blue_strobe"
EFFECT_YELLOW_STROBE = "yellow_strobe"
EFFECT_CYAN_STROBE = "cyan_strobe"
EFFECT_PURPLE_STROBE = "purple_strobe"
EFFECT_WHITE_STROBE = "white_strobe"
EFFECT_COLORJUMP = "colorjump"
EFFECT_CUSTOM = "custom"

EFFECT_MAP = {
    EFFECT_COLORLOOP: 0x25,
    EFFECT_RED_FADE: 0x26,
    EFFECT_GREEN_FADE: 0x27,
    EFFECT_BLUE_FADE: 0x28,
    EFFECT_YELLOW_FADE: 0x29,
    EFFECT_CYAN_FADE: 0x2A,
    EFFECT_PURPLE_FADE: 0x2B,
    EFFECT_WHITE_FADE: 0x2C,
    EFFECT_RED_GREEN_CROSS_FADE: 0x2D,
    EFFECT_RED_BLUE_CROSS_FADE: 0x2E,
    EFFECT_GREEN_BLUE_CROSS_FADE: 0x2F,
    EFFECT_COLORSTROBE: 0x30,
    EFFECT_RED_STROBE: 0x31,
    EFFECT_GREEN_STROBE: 0x32,
    EFFECT_BLUE_STROBE: 0x33,
    EFFECT_YELLOW_STROBE: 0x34,
    EFFECT_CYAN_STROBE: 0x35,
    EFFECT_PURPLE_STROBE: 0x36,
    EFFECT_WHITE_STROBE: 0x37,
    EFFECT_COLORJUMP: 0x38,
}

EFFECT_ID_NAME = {v: k for k, v in EFFECT_MAP.items()}
EFFECT_CUSTOM_CODE = 0x60

EFFECT_LIST = sorted(EFFECT_MAP)

ADDRESSABLE_EFFECT_ID_NAME = {
    1: "RBM 1",
    2: "RBM 2",
    3: "RBM 3",
    4: "RBM 4",
    5: "RBM 5",
    6: "RBM 6",
    7: "RBM 7",
    8: "RBM 8",
    9: "RBM 9",
    10: "RBM 10",
    11: "RBM 11",
    12: "RBM 12",
    13: "RBM 13",
    14: "RBM 14",
    15: "RBM 15",
    16: "RBM 16",
    17: "RBM 17",
    18: "RBM 18",
    19: "RBM 19",
    20: "RBM 20",
    21: "RBM 21",
    22: "RBM 22",
    23: "RBM 23",
    24: "RBM 24",
    25: "RBM 25",
    26: "RBM 26",
    27: "RBM 27",
    28: "RBM 28",
    29: "RBM 29",
    30: "RBM 30",
    31: "RBM 31",
    32: "RBM 32",
    33: "RBM 33",
    34: "RBM 34",
    35: "RBM 35",
    36: "RBM 36",
    37: "RBM 37",
    38: "RBM 38",
    39: "RBM 39",
    40: "RBM 40",
    41: "RBM 41",
    42: "RBM 42",
    43: "RBM 43",
    44: "RBM 44",
    45: "RBM 45",
    46: "RBM 46",
    47: "RBM 47",
    48: "RBM 48",
    49: "RBM 49",
    50: "RBM 50",
    51: "RBM 51",
    52: "RBM 52",
    53: "RBM 53",
    54: "RBM 54",
    55: "RBM 55",
    56: "RBM 56",
    57: "RBM 57",
    58: "RBM 58",
    59: "RBM 59",
    60: "RBM 60",
    61: "RBM 61",
    62: "RBM 62",
    63: "RBM 63",
    64: "RBM 64",
    65: "RBM 65",
    66: "RBM 66",
    67: "RBM 67",
    68: "RBM 68",
    69: "RBM 69",
    70: "RBM 70",
    71: "RBM 71",
    72: "RBM 72",
    73: "RBM 73",
    74: "RBM 74",
    75: "RBM 75",
    76: "RBM 76",
    77: "RBM 77",
    78: "RBM 78",
    79: "RBM 79",
    80: "RBM 80",
    81: "RBM 81",
    82: "RBM 82",
    83: "RBM 83",
    84: "RBM 84",
    85: "RBM 85",
    86: "RBM 86",
    87: "RBM 87",
    88: "RBM 88",
    89: "RBM 89",
    90: "RBM 90",
    91: "RBM 91",
    92: "RBM 92",
    93: "RBM 93",
    94: "RBM 94",
    95: "RBM 95",
    96: "RBM 96",
    97: "RBM 97",
    98: "RBM 98",
    99: "RBM 99",
    100: "RBM 100",
}
ADDRESSABLE_EFFECT_NAME_ID = {v: k for k, v in ADDRESSABLE_EFFECT_ID_NAME.items()}

ASSESSABLE_MULTI_COLOR_ID_NAME = {
    1: "Multi Color Static",
    2: "Multi Color Running Water",
    3: "Multi Color Strobe",
    4: "Multi Color Jump",
    5: "Multi Color Breathing",
}

ASSESSABLE_MULTI_COLOR_NAME_ID = {
    v: k for k, v in ASSESSABLE_MULTI_COLOR_ID_NAME.items()
}


class PresetPattern:

    _instance = None
    seven_color_cross_fade = 0x25
    red_gradual_change = 0x26
    green_gradual_change = 0x27
    blue_gradual_change = 0x28
    yellow_gradual_change = 0x29
    cyan_gradual_change = 0x2A
    purple_gradual_change = 0x2B
    white_gradual_change = 0x2C
    red_green_cross_fade = 0x2D
    red_blue_cross_fade = 0x2E
    green_blue_cross_fade = 0x2F
    seven_color_strobe_flash = 0x30
    red_strobe_flash = 0x31
    green_strobe_flash = 0x32
    blue_strobe_flash = 0x33
    yellow_strobe_flash = 0x34
    cyan_strobe_flash = 0x35
    purple_strobe_flash = 0x36
    white_strobe_flash = 0x37
    seven_color_jumping = 0x38

    def __init__(self):
        self._value_to_str = {
            v: k.replace("_", " ").title()
            for k, v in PresetPattern.__dict__.items()
            if type(v) is int
        }

    @classmethod
    def instance(cls):
        """Get preset pattern instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def valid(pattern):
        if pattern >= 0x25 and pattern <= 0x38 or pattern >= 0x61 and pattern <= 0x63:
            return True
        return False

    @staticmethod
    def valtostr(pattern):
        instance = PresetPattern.instance()
        return instance._value_to_str.get(pattern)

    @staticmethod
    def str_to_val(effect):
        if effect in EFFECT_MAP:
            return EFFECT_MAP[effect]
        if hasattr(PresetPattern, effect):
            return getattr(PresetPattern, effect)
        raise ValueError(f"{effect} is not a known effect name.")
