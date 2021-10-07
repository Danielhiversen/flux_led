"""FluxLED Models Database."""

from collections import namedtuple

from .const import (
    COLOR_MODE_CCT,
    COLOR_MODE_DIM,
    COLOR_MODE_RGB,
    COLOR_MODE_RGBW,
    COLOR_MODE_RGBWW,
    COLOR_MODE_ADDRESSABLE,
    COLOR_MODES_RGB_CCT,
    COLOR_MODES_RGB_W,
    MODEL_NUM_SWITCH,
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

MODELS = [
    LEDENETModel(
        model_num=0x01,
        models=[],
        description="Original LEDENET",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB},
    ),
    LEDENETModel(
        model_num=0x04,
        models=[],
        description="Unknown",
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
    ),
    LEDENETModel(
        model_num=0x06,
        models=["AK001-ZJ2147"],
        description="Magic Home Branded RGBW Strip Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={
            0x14: {COLOR_MODE_RGBW},  # 0x14 (RGB&W) verified on model 0x06
            0x16: COLOR_MODES_RGB_W,  # 0x16 (RGB/W) verified on model 0x06
        },
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
    ),
    LEDENETModel(
        model_num=0x07,
        models=[],
        description="Magic Home Branded RGBWW Strip Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=True,
        mode_to_color_mode={
            0x47: {
                COLOR_MODE_RGB,
                COLOR_MODE_CCT,
            },  # 0x47 (RGB/WW) verified on model 0x07
            0x45: COLOR_MODE_RGBWW,  # 0x45 (RGB&WW) verified on model 0x07
        },
        color_modes={COLOR_MODE_RGBWW},  # Formerly rgbwcapable
    ),
    LEDENETModel(
        model_num=0xE,
        models=["AK001-ZJ2104"],
        description="Floor Lamp",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=True,
        mode_to_color_mode={},
        color_modes=COLOR_MODES_RGB_CCT,
    ),
    LEDENETModel(
        model_num=0x25,
        models=["AK001-ZJ200"],
        description="WiFi RGBWW Strip Controller",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=True,
        mode_to_color_mode=BASE_MODE_MAP,
        color_modes={COLOR_MODE_RGBWW},  # Formerly rgbwcapable
    ),
    LEDENETModel(
        model_num=0x33,
        models=["AK001-ZJ2145", "AK001-ZJ2146"],
        description="Magic Home Branded RGB Strip Controller",
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB},
    ),
    LEDENETModel(
        model_num=0x35,
        models=["AK001-ZJ2145", "AK001-ZJ2101", "AK001-ZJ2104"],
        description="Smart Bulbs",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=True,
        mode_to_color_mode={},
        color_modes=COLOR_MODES_RGB_CCT,
    ),
    LEDENETModel(
        model_num=0x44,
        models=[],
        description="Unknown",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
    ),
    LEDENETModel(
        model_num=0x45,
        models=[],
        description="Unknown, was in tests",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB, COLOR_MODE_DIM},  # Formerly rgbwcapable
    ),
    LEDENETModel(
        model_num=0x81,
        models=[],
        description="Unknown",
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
    ),
    LEDENETModel(
        model_num=MODEL_NUM_SWITCH,  # 0x97
        models=["AK001-ZJ2134"],
        description="Smart Switch",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={},  # no color modes
    ),
    LEDENETModel(
        model_num=0xA2,
        models=["AK001-ZJ2104"],
        description="Generic Addressable",
        always_writes_white_and_colors=False,
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_ADDRESSABLE},
    ),
    LEDENETModel(
        model_num=0xA3,
        models=["K001-ZJ2148"],
        description="Magic Home Branded Addressable",
        always_writes_white_and_colors=False,
        nine_byte_read_protocol=False,
        mode_to_color_mode={},
        color_modes={COLOR_MODE_ADDRESSABLE},
    ),
]

MODEL_MAP = {model.model_num: model for model in MODELS}
RGBW_PROTOCOL_MODELS = {
    model.model_num for model in MODELS if model.always_writes_white_and_colors
}
USE_9BYTE_PROTOCOL_MODELS = {
    model.model_num for model in MODELS if model.nine_byte_read_protocol
}
