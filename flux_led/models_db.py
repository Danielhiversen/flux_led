"""FluxLED Models Database."""

from collections import namedtuple

from .const import (
    COLOR_MODE_CCT,
    COLOR_MODE_DIM,
    COLOR_MODE_RGB,
    COLOR_MODE_RGBW,
    COLOR_MODE_RGBWW,
    COLOR_MODES_ADDRESSABLE,
    COLOR_MODES_RGB_CCT,
    COLOR_MODES_RGB_W,
    STATE_COOL_WHITE,
    STATE_GREEN,
    STATE_RED,
    STATE_WARM_WHITE,
)
from .protocol import (
    PROTOCOL_LEDENET_8BYTE,
    PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS,
    PROTOCOL_LEDENET_9BYTE,
    PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS,
    PROTOCOL_LEDENET_ADDRESSABLE_A1,
    PROTOCOL_LEDENET_ADDRESSABLE_A2,
    PROTOCOL_LEDENET_ADDRESSABLE_A3,
    PROTOCOL_LEDENET_CCT,
    PROTOCOL_LEDENET_ORIGINAL,
)

LEDENETModel = namedtuple(
    "LEDENETModel",
    [
        "model_num",  # The model number aka byte 1
        "models",  # The model names from discovery
        "description",  # Description of the model
        "always_writes_white_and_colors",  # Devices that don't require a separate rgb/w bit aka rgbwprotocol
        "protocol",  # The device protocol
        "mode_to_color_mode",  # A mapping of mode aka byte 2 to color mode that overrides color_modes
        "color_modes",  # The color modes to use if there is no mode_to_color_mode_mapping
        "channel_map",  # Used to remap channels
        "microphone",  # Device has a built in microphone
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
        protocol=PROTOCOL_LEDENET_ORIGINAL,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB},
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x04,
        models=["AK001-ZJ200"],
        description="UFO LED WiFi Controller",  # AKA ZJ-WFUF-170F
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x06,
        models=["AK001-ZJ2147"],
        description="RGBW Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS,
        mode_to_color_mode=GENERIC_RGBW_MAP,
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x07,
        models=[],
        description="RGBCW Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS,
        mode_to_color_mode=GENERIC_RGBWW_MAP,
        color_modes={COLOR_MODE_RGBWW},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x08,
        models=[],
        description="RGB Controller with MIC",
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS,
        mode_to_color_mode=GENERIC_RGB_MAP,
        color_modes={COLOR_MODE_RGB},
        channel_map={},
        microphone=True,
    ),
    LEDENETModel(
        model_num=0x09,
        models=[],
        description="CCT Ceiling Light",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_CCT},  # Formerly rgbwcapable
        channel_map={
            STATE_WARM_WHITE: STATE_RED,
            STATE_RED: STATE_WARM_WHITE,
            STATE_COOL_WHITE: STATE_GREEN,
            STATE_GREEN: STATE_COOL_WHITE,
        },
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x0B,
        models=[],
        description="Smart Switch 1c",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={},  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x0E,
        models=["AK001-ZJ2104"],
        description="Floor Lamp",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_9BYTE,
        mode_to_color_mode={0x01: COLOR_MODES_RGB_CCT},
        color_modes=COLOR_MODES_RGB_CCT,
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x10,
        models=[],
        description="Christmas Light",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x1A,
        models=[],
        description="Christmas Light",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x16,
        models=[],
        description="Magnetic Light CCT",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_CCT},  # Formerly rgbwcapable
        channel_map={
            STATE_WARM_WHITE: STATE_RED,
            STATE_RED: STATE_WARM_WHITE,
            STATE_COOL_WHITE: STATE_GREEN,
            STATE_GREEN: STATE_COOL_WHITE,
        },
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x17,
        models=[],
        description="Magnetic Light Dimable",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_DIM},  # Formerly rgbwcapable
        channel_map={STATE_WARM_WHITE: STATE_RED, STATE_RED: STATE_WARM_WHITE},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x18,
        models=[],
        description="Plant Light",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS,
        mode_to_color_mode={},
        color_modes={},  # no color modes -- UNVERIFIED
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x1B,
        models=[],
        description="Spray Light",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB},
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x19,
        models=[],
        description="Smart Socket 2 USB",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={},  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x1C,
        models=[],
        description="Table Light CCT",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_CCT,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_CCT},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x21,
        models=["AK001-ZJ2101", "AK001-ZJ2104"],
        description="Smart Bulb Dimmable",
        always_writes_white_and_colors=True,  # Verified required with AK001-ZJ200 bulb
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_DIM},  # Formerly rgbwcapable
        channel_map={STATE_WARM_WHITE: STATE_RED, STATE_RED: STATE_WARM_WHITE},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x25,
        models=["AK001-ZJ200"],
        description="RGB/WW/CW Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_9BYTE,
        mode_to_color_mode=BASE_MODE_MAP,
        color_modes={COLOR_MODE_RGBWW},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x33,
        models=["AK001-ZJ2145", "AK001-ZJ2146"],
        description="RGB Controller",
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode=GENERIC_RGB_MAP,
        color_modes={COLOR_MODE_RGB},
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x35,
        models=["AK001-ZJ2145", "AK001-ZJ2101", "AK001-ZJ2104"],
        description="Smart Bulb RGBCW",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS,
        mode_to_color_mode={0x01: COLOR_MODES_RGB_CCT, 0x17: COLOR_MODES_RGB_CCT},
        color_modes=COLOR_MODES_RGB_CCT,
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x41,
        models=[],
        description="Single Channel Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},  # Only mode should be 0x41
        color_modes={COLOR_MODE_DIM},  # Formerly rgbwcapable
        channel_map={STATE_WARM_WHITE: STATE_RED, STATE_RED: STATE_WARM_WHITE},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x44,
        models=[],
        description="Smart Bulb RGBW",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes=COLOR_MODES_RGB_W,  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x45,
        models=[],
        description=None,  # Unknown
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB, COLOR_MODE_DIM},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x52,
        models=[],
        description="Smart Bulb CCT",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_CCT},  # Formerly rgbwcapable
        channel_map={
            STATE_WARM_WHITE: STATE_RED,
            STATE_RED: STATE_WARM_WHITE,
            STATE_COOL_WHITE: STATE_GREEN,
            STATE_GREEN: STATE_COOL_WHITE,
        },
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x54,
        models=["HF-LPB100-ZJ200"],
        description="Downlight RGBW",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes=COLOR_MODES_RGB_W,  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x62,
        models=[],
        description="CCT Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_CCT},  # Formerly rgbwcapable
        channel_map={
            STATE_WARM_WHITE: STATE_RED,
            STATE_RED: STATE_WARM_WHITE,
            STATE_COOL_WHITE: STATE_GREEN,
            STATE_GREEN: STATE_COOL_WHITE,
        },
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x81,
        models=[],
        description=None,  # Unknown
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x93,
        models=[],
        description="Smart Switch 1C",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={},  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x94,
        models=[],
        description="Smart Switch 1c Watt",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={},  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x95,
        models=[],
        description="Smart Switch 2c",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={},  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x96,
        models=[],
        description="Smart Switch 4c",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={},  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x97,  # 0x97
        models=["AK001-ZJ2134"],
        description="Smart Socket 1c",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={},  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0xA1,
        models=[],
        description="RGB Symphony v1",
        always_writes_white_and_colors=False,
        protocol=PROTOCOL_LEDENET_ADDRESSABLE_A1,
        mode_to_color_mode={},
        color_modes=COLOR_MODES_ADDRESSABLE,
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0xA2,
        models=["AK001-ZJ2104"],
        description="RGB Symphony v2",
        always_writes_white_and_colors=False,
        protocol=PROTOCOL_LEDENET_ADDRESSABLE_A2,
        mode_to_color_mode={},
        color_modes=COLOR_MODES_ADDRESSABLE,
        channel_map={},
        microphone=True,
    ),
    LEDENETModel(
        model_num=0xA3,
        models=["K001-ZJ2148"],
        description="RGB Symphony v3",
        always_writes_white_and_colors=False,
        protocol=PROTOCOL_LEDENET_ADDRESSABLE_A3,
        mode_to_color_mode={},
        color_modes=COLOR_MODES_ADDRESSABLE,
        channel_map={},
        microphone=True,
    ),
    LEDENETModel(
        model_num=0xD1,
        models=[],
        description="Digital Light",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={},  # no color modes -- UNVERIFIED
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0xE1,
        models=[],
        description="Ceiling Light",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={},  # no color modes -- UNVERIFIED
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0xE2,
        models=[],
        description="Ceiling Light Assist",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocol=PROTOCOL_LEDENET_8BYTE,
        mode_to_color_mode={},
        color_modes={},  # no color modes -- UNVERIFIED
        channel_map={},
        microphone=False,
    ),
]

MODEL_MAP = {model.model_num: model for model in MODELS}
MODEL_DESCRIPTIONS = {model.model_num: model.description for model in MODELS}
CHANNEL_REMAP = {model.model_num: model.channel_map for model in MODELS}
RGBW_PROTOCOL_MODELS = {
    model.model_num for model in MODELS if model.always_writes_white_and_colors
}
USE_9BYTE_PROTOCOL_MODELS = {
    model.model_num for model in MODELS if model.protocol == PROTOCOL_LEDENET_9BYTE
}
MICROPHONE_MODELS = {model.model_num for model in MODELS if model.microphone}
MODEL_NUM_PROTOCOL = {model.model_num: model.protocol for model in MODELS}
WHITE_ARE_TEMP_BRIGHTNESS = {
    model.model_num for model in MODELS if model.protocol == PROTOCOL_LEDENET_CCT
}


def get_model_description(model_num):
    """Return the description for a model."""
    return MODEL_DESCRIPTIONS.get(model_num, f"Unknown Model {hex(model_num)}")
