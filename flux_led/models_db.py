"""FluxLED Models Database."""

from collections import namedtuple

from .const import (
    COLOR_MODE_ADDRESSABLE,
    COLOR_MODE_CCT,
    COLOR_MODE_DIM,
    COLOR_MODE_RGB,
    COLOR_MODE_RGBW,
    COLOR_MODE_RGBWW,
    COLOR_MODES_RGB_CCT,
    COLOR_MODES_RGB_W,
    MODEL_NUM_SWITCH,
    STATE_RED,
    STATE_WARM_WHITE,
)

LEDENETModel = namedtuple(
    "LEDENETModel",
    [
        "model_num",  # The model number aka byte 1
        "models",  # The model names from discovery
        "description",  # Description of the model
        "always_writes_white_and_colors",  # Devices that don't require a separate rgb/w bit aka rgbwprotocol
        "nine_byte_read_protocol",  # Devices that use the 9 byte protocol to read state
        "mode_to_color_mode",  # A mapping of mode aka byte 2 to color mode that overrides color_modes
        "color_modes",  # The color modes to use if there is no mode_to_color_mode_mapping
        "channel_map",  # Used to remap channels
    ],
)

BASE_MODE_MAP = {
    0x01: {COLOR_MODE_DIM},
    0x02: {COLOR_MODE_CCT},
    0x03: {COLOR_MODE_RGB},
    0x04: {COLOR_MODE_RGBW},
    0x05: {COLOR_MODE_RGBWW},
    0x06: COLOR_MODES_RGB_W,
    0x07: COLOR_MODES_RGB_CCT,
}

GENERIC_RGB_MAP = {
    0x13: {COLOR_MODE_RGB},  # RGB (RGB) verified on model 0x33
    0x23: {COLOR_MODE_RGB},  # RGB (GRB) verified on model 0x33
    0x33: {COLOR_MODE_RGB},  # RGB (BRG) verified on model 0x33
}

GENERIC_RGBW_MAP = {
    0x14: {COLOR_MODE_RGBW},  # RGB&W (RGBW) verified on model 0x06
    0x24: {COLOR_MODE_RGBW},  # RGB&W (GRBW) verified on model 0x06
    0x34: {COLOR_MODE_RGBW},  # RGB&W (BRGW) verified on model 0x06
    0x16: COLOR_MODES_RGB_W,  # RGB/W (RGBW) verified on model 0x06
    0x26: COLOR_MODES_RGB_W,  # RGB/W (GRBW) verified on model 0x06
    0x36: COLOR_MODES_RGB_W,  # RGB/W (BRGW) verified on model 0x06
}

GENERIC_RGBWW_MAP = {
    0x17: COLOR_MODES_RGB_CCT,  # RGB/CCT (RGBCW) verified on model 0x07
    0x27: COLOR_MODES_RGB_CCT,  # RGB/CCT (GRBCW) verified on model 0x07
    0x37: COLOR_MODES_RGB_CCT,  # RGB/CCT (BRGCW) verified on model 0x07
    0x47: COLOR_MODES_RGB_CCT,  # RGB/CCT (RGBWC) verified on model 0x07
    0x57: COLOR_MODES_RGB_CCT,  # RGB/CCT (GRBWC) verified on model 0x07
    0x67: COLOR_MODES_RGB_CCT,  # RGB/CCT (BRGWC) verified on model 0x07
    0x77: COLOR_MODES_RGB_CCT,  # RGB/CCT (WRGBC) verified on model 0x07
    0x87: COLOR_MODES_RGB_CCT,  # RGB/CCT (WGRBC) verified on model 0x07
    0x97: COLOR_MODES_RGB_CCT,  # RGB/CCT (WBRGC) verified on model 0x07
    0xA7: COLOR_MODES_RGB_CCT,  # RGB/CCT (CRGBW) verified on model 0x07
    0xB7: COLOR_MODES_RGB_CCT,  # RGB/CCT (CBRBW) verified on model 0x07
    0xC7: COLOR_MODES_RGB_CCT,  # RGB/CCT (CBRGW) verified on model 0x07
    0xD7: COLOR_MODES_RGB_CCT,  # RGB/CCT (WCRGB) verified on model 0x07
    0xE7: COLOR_MODES_RGB_CCT,  # RGB/CCT (WCGRB) verified on model 0x07
    0xF7: COLOR_MODES_RGB_CCT,  # RGB/CCT (WCBRG) verified on model 0x07
    0x15: {COLOR_MODE_RGBWW},  # RGB&CCT (RGBCW) verified on model 0x07
    0x25: {COLOR_MODE_RGBWW},  # RGB&CCT (GRBCW) verified on model 0x07
    0x35: {COLOR_MODE_RGBWW},  # RGB&CCT (BRGCW) verified on model 0x07
    0x45: {COLOR_MODE_RGBWW},  # RGB&CCT (RGBWC) verified on model 0x07
    0x55: {COLOR_MODE_RGBWW},  # RGB&CCT (GRBWC) verified on model 0x07
    0x65: {COLOR_MODE_RGBWW},  # RGB&CCT (BRGWC) verified on model 0x07
    0x75: {COLOR_MODE_RGBWW},  # RGB&CCT (WRGBC) verified on model 0x07
    0x85: {COLOR_MODE_RGBWW},  # RGB&CCT (WGRBC) verified on model 0x07
    0x95: {COLOR_MODE_RGBWW},  # RGB&CCT (WBRGC) verified on model 0x07
    0xA5: {COLOR_MODE_RGBWW},  # RGB&CCT (CRGBW) verified on model 0x07
    0xB5: {COLOR_MODE_RGBWW},  # RGB&CCT (CBRBW) verified on model 0x07
    0xC5: {COLOR_MODE_RGBWW},  # RGB&CCT (CBRGW) verified on model 0x07
    0xD5: {COLOR_MODE_RGBWW},  # RGB&CCT (WCRGB) verified on model 0x07
    0xE5: {COLOR_MODE_RGBWW},  # RGB&CCT (WCGRB) verified on model 0x07
    0xF5: {COLOR_MODE_RGBWW},  # RGB&CCT (WCBRG) verified on model 0x07
}

UNKNOWN_MODEL = "Unknown Model"

MODELS = [
    LEDENETModel(
        model_num=0x01,
        models=[],
        description="Original LEDENET",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB},
        channel_map={},
    ),
    LEDENETModel(
        model_num=0x04,
        models=["AK001-ZJ200"],
        description="UFO LED WiFi Controller",  # AKA ZJ-WFUF-170F
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
        channel_map={},
    ),
    LEDENETModel(
        model_num=0x06,
        models=["AK001-ZJ2147"],
        description="Magic Home Branded RGBW Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode=GENERIC_RGBW_MAP,
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
        channel_map={},
    ),
    LEDENETModel(
        model_num=0x07,
        models=[],
        description="Magic Home Branded RGBWW Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=True,
        mode_to_color_mode=GENERIC_RGBWW_MAP,
        color_modes={COLOR_MODE_RGBWW},  # Formerly rgbwcapable
        channel_map={},
    ),
    LEDENETModel(
        model_num=0x0E,
        models=["AK001-ZJ2104"],
        description="Floor Lamp",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=True,
        mode_to_color_mode={0x01: COLOR_MODES_RGB_CCT},
        color_modes=COLOR_MODES_RGB_CCT,
        channel_map={},
    ),
    LEDENETModel(
        model_num=0x21,
        models=[],
        description="Magic Home Branded Single Channel Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_DIM},  # Formerly rgbwcapable
        channel_map={STATE_WARM_WHITE: STATE_RED, STATE_RED: STATE_WARM_WHITE},
    ),
    LEDENETModel(
        model_num=0x25,
        models=["AK001-ZJ200"],
        description="WiFi RGBWW Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=True,
        mode_to_color_mode=BASE_MODE_MAP,
        color_modes={COLOR_MODE_RGBWW},  # Formerly rgbwcapable
        channel_map={},
    ),
    LEDENETModel(
        model_num=0x33,
        models=["AK001-ZJ2145", "AK001-ZJ2146"],
        description="Magic Home Branded RGB Controller",
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode=GENERIC_RGB_MAP,
        color_modes={COLOR_MODE_RGB},
        channel_map={},
    ),
    LEDENETModel(
        model_num=0x35,
        models=["AK001-ZJ2145", "AK001-ZJ2101", "AK001-ZJ2104"],
        description="Smart Bulb",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=True,
        mode_to_color_mode={0x01: COLOR_MODES_RGB_CCT, 0x17: COLOR_MODES_RGB_CCT},
        color_modes=COLOR_MODES_RGB_CCT,
        channel_map={},
    ),
    LEDENETModel(
        model_num=0x41,
        models=[],
        description="Magic Home Branded Single Channel Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},  # Only mode should be 0x41
        color_modes={COLOR_MODE_DIM},  # Formerly rgbwcapable
        channel_map={STATE_WARM_WHITE: STATE_RED, STATE_RED: STATE_WARM_WHITE},
    ),
    LEDENETModel(
        model_num=0x44,
        models=[],
        description=None,  # Unknown
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
        channel_map={},
    ),
    LEDENETModel(
        model_num=0x45,
        models=[],
        description=None,  # Unknown
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB, COLOR_MODE_DIM},  # Formerly rgbwcapable
        channel_map={},
    ),
    LEDENETModel(
        model_num=0x81,
        models=[],
        description=None,  # Unknown
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
        channel_map={},
    ),
    LEDENETModel(
        model_num=MODEL_NUM_SWITCH,  # 0x97
        models=["AK001-ZJ2134"],
        description="Smart Switch",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={},  # no color modes
        channel_map={},
    ),
    LEDENETModel(
        model_num=0xA1,
        models=[],
        description="Unknown Addressable",  # https://github.com/Danielhiversen/flux_led/pull/59/files#diff-09e60df19b61f5ceb8d2aef0ade582c2b84979cab660baa27c1ec65725144d76R776
        always_writes_white_and_colors=False,
        nine_byte_read_protocol=False,  # unverified
        mode_to_color_mode={},
        color_modes={COLOR_MODE_ADDRESSABLE},
        channel_map={},
    ),
    LEDENETModel(
        model_num=0xA2,
        models=["AK001-ZJ2104"],
        description="Generic Addressable",
        always_writes_white_and_colors=False,
        nine_byte_read_protocol=False,  # unverified
        mode_to_color_mode={},
        color_modes={COLOR_MODE_ADDRESSABLE},
        channel_map={},
    ),
    LEDENETModel(
        model_num=0xA3,
        models=["K001-ZJ2148"],
        description="Magic Home Branded Addressable",
        always_writes_white_and_colors=False,
        nine_byte_read_protocol=False,  # unverified
        mode_to_color_mode={},
        color_modes={COLOR_MODE_ADDRESSABLE},
        channel_map={},
    ),
]

MODEL_MAP = {model.model_num: model for model in MODELS}
MODEL_DESCRIPTIONS = {model.model_num: model.description for model in MODELS}
CHANNEL_REMAP = {model.model_num: model.channel_map for model in MODELS}
RGBW_PROTOCOL_MODELS = {
    model.model_num for model in MODELS if model.always_writes_white_and_colors
}
USE_9BYTE_PROTOCOL_MODELS = {
    model.model_num for model in MODELS if model.nine_byte_read_protocol
}
