from typing import Final

EFFECT_RANDOM: Final = "random"
EFFECT_COLORLOOP: Final = "colorloop"
EFFECT_RED_FADE: Final = "red_fade"
EFFECT_GREEN_FADE: Final = "green_fade"
EFFECT_BLUE_FADE: Final = "blue_fade"
EFFECT_YELLOW_FADE: Final = "yellow_fade"
EFFECT_CYAN_FADE: Final = "cyan_fade"
EFFECT_PURPLE_FADE: Final = "purple_fade"
EFFECT_WHITE_FADE: Final = "white_fade"
EFFECT_RED_GREEN_CROSS_FADE: Final = "rg_cross_fade"
EFFECT_RED_BLUE_CROSS_FADE: Final = "rb_cross_fade"
EFFECT_GREEN_BLUE_CROSS_FADE: Final = "gb_cross_fade"
EFFECT_COLORSTROBE: Final = "colorstrobe"
EFFECT_RED_STROBE: Final = "red_strobe"
EFFECT_GREEN_STROBE: Final = "green_strobe"
EFFECT_BLUE_STROBE: Final = "blue_strobe"
EFFECT_YELLOW_STROBE: Final = "yellow_strobe"
EFFECT_CYAN_STROBE: Final = "cyan_strobe"
EFFECT_PURPLE_STROBE: Final = "purple_strobe"
EFFECT_WHITE_STROBE: Final = "white_strobe"
EFFECT_COLORJUMP: Final = "colorjump"
EFFECT_CUSTOM: Final = "custom"

EFFECT_MAP: Final = {
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

EFFECT_ID_NAME: Final = {v: k for k, v in EFFECT_MAP.items()}
EFFECT_CUSTOM_CODE: Final = 0x60

EFFECT_LIST: Final = sorted(EFFECT_MAP)


class PresetPattern:
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
