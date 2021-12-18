"""FluxLED Models Database."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set

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
    PROTOCOL_LEDENET_8BYTE_AUTO_ON,
    PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS,
    PROTOCOL_LEDENET_9BYTE,
    PROTOCOL_LEDENET_9BYTE_AUTO_ON,
    PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS,
    PROTOCOL_LEDENET_ADDRESSABLE_A1,
    PROTOCOL_LEDENET_ADDRESSABLE_A2,
    PROTOCOL_LEDENET_ADDRESSABLE_A3,
    PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS,
    PROTOCOL_LEDENET_CCT,
    PROTOCOL_LEDENET_ORIGINAL,
)

# BL likely means BL602 chips
MODEL_INFO_NAMES = {
    "ZG-LX-FL": "Flood",  # Seen on 24w Flood light
    "ZG-BL": "",  # unknown
    "CL-BL": "",  # Send on the 0x1C table lamp
    "ZG-BL-IR": "IR",
    "IR": "IR",
    "ZG-BL-EH7W": "7w",
    "ZG-BL-IH9WL": "9w RF",
    "ZG-BL-IH9W": "9w RF",
    "ZG-BL-CB1": "Ceiling",
    "ZG-LX-EJ9W": "9w",  # This might be a ceiling light
    "RF": "RF",
    "LWS-BL": "Ceiling",
    "LWS-LX-IR": "Ceiling IR",
    "ZG-BL-611HZ": "",  # unknown
    "ZG-BL-5V": "5v",
    "ZG-LX": "",  # Seen on floor lamp, v2 addressable, and Single channel controller
    "ZG-LX-UART": "",  # Seen on UK xmas lights 0x33, fairy controller, and lytworx
    "ZG-BL-PWM": "Flood",  # Seen on 40w Flood Light
    "ZG-ZW2": "",  # seen on 0x97 socket
    "ZGIR44": "44 Key IR",
    "IR_ZG": "IR",
}


@dataclass
class MinVersionProtocol:
    min_version: int
    protocol: str


@dataclass
class LEDENETModel:
    model_num: int  # The model number aka byte 1
    models: List[str]  # The model names from discovery
    description: str  # Description of the model ({type} {color_mode})
    always_writes_white_and_colors: bool  # Devices that don't require a separate rgb/w bit aka rgbwprotocol
    protocols: List[
        MinVersionProtocol
    ]  # The device protocols, must be ordered highest version to lowest version
    mode_to_color_mode: Dict[
        int, Set[str]
    ]  # A mapping of mode aka byte 2 to color mode that overrides color_modes
    color_modes: Set[
        str
    ]  # The color modes to use if there is no mode_to_color_mode_mapping
    channel_map: Dict[str, str]  # Used to remap channels
    microphone: bool

    def protocol_for_version_num(self, version_num: int) -> str:
        protocol = self.protocols[-1].protocol
        for min_version_protocol in self.protocols:
            if version_num >= min_version_protocol.min_version:
                protocol = min_version_protocol.protocol
                break
        return protocol


class LEDENETChip(Enum):
    ESP8266 = auto()  # aka ESP8285
    BL602 = auto()  # supports BLE as well
    S82GESNC = auto()
    HFLPB100 = auto()


@dataclass
class LEDENETHardware:
    model: str  # The model string
    chip: LEDENETChip
    rf_remote: bool


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

# Assumed model version scheme
#
# Example AK001-ZJ2149
#
#  0  1  2  3  4  5
#  Z  J  2  1  4  9
#  |  |  |  |  |  |
#  |  |  |  |  |  |
#  |  |  |  |  |  Minor Version
#  |  |  |  |  Major Version
#  |  |  |  Chip
#  |  |  Generation
#  |  Unknown
#  Zengge
#
HARDWARE = [
    LEDENETHardware(
        model="AK001-ZJ100",
        chip=LEDENETChip.ESP8266,
        rf_remote=False,  # verified
    ),
    LEDENETHardware(
        model="AK001-ZJ200",
        chip=LEDENETChip.ESP8266,
        rf_remote=False,  # verified
    ),
    LEDENETHardware(
        model="AK001-ZJ210",  # might also be "AK001-ZJ2100"
        chip=LEDENETChip.ESP8266,  # verified
        rf_remote=False,  # verified
    ),
    LEDENETHardware(
        model="AK001-ZJ2101",
        chip=LEDENETChip.ESP8266,
        rf_remote=False,
    ),
    LEDENETHardware(
        model="AK001-ZJ2104",
        chip=LEDENETChip.ESP8266,
        rf_remote=False,  # verified
    ),
    LEDENETHardware(
        model="AK001-ZJ2134",  # seen in smart plugs only?
        chip=LEDENETChip.S82GESNC,  # couldn't get the device appart
        rf_remote=False,
    ),
    LEDENETHardware(
        model="AK001-ZJ2145",
        chip=LEDENETChip.BL602,
        rf_remote=False,  # verified
    ),
    LEDENETHardware(
        model="AK001-ZJ2146",  # seen in smart plugs & Controller RGBCW, but RF remote isn't supported on plugs
        chip=LEDENETChip.BL602,  # verified
        rf_remote=True,  # verified
    ),
    LEDENETHardware(
        model="AK001-ZJ2147",  # seen on Controller RGBW
        chip=LEDENETChip.BL602,
        rf_remote=True,  # verified
    ),
    LEDENETHardware(
        model="AK001-ZJ2148",  # seen on older Addressable v3
        chip=LEDENETChip.BL602,
        rf_remote=True,  # verified
    ),
    LEDENETHardware(
        model="AK001-ZJ2149",  # seen on newer Addressable v3
        chip=LEDENETChip.BL602,
        rf_remote=True,  # verified
    ),
    LEDENETHardware(
        model="HF-A11-ZJ002",  # reported older large box controllers (may be original proto)
        chip=LEDENETChip.HFLPB100,
        rf_remote=False,  # unverified
    ),
    LEDENETHardware(
        model="HF-LPB100",  # reported on older UFO
        chip=LEDENETChip.HFLPB100,
        rf_remote=False,  # unverified
    ),
    LEDENETHardware(
        model="HF-LPB100-0",  # reported on older UFO
        chip=LEDENETChip.HFLPB100,
        rf_remote=False,  # unverified
    ),
    LEDENETHardware(
        model="HF-LPB100-1",  # reported on older UFO
        chip=LEDENETChip.HFLPB100,
        rf_remote=False,  # unverified
    ),
    LEDENETHardware(
        model="HF-LPB100-ZJ002",  # seen on older UFO
        chip=LEDENETChip.HFLPB100,
        rf_remote=False,  # unverified
    ),
    LEDENETHardware(
        model="HF-LPB100-ZJ200",  # seen on RGBW Downlight
        chip=LEDENETChip.HFLPB100,
        rf_remote=False,  # unverified
    ),
]

MODELS = [
    LEDENETModel(
        model_num=0x01,
        models=[],
        description="Legacy Controller RGB",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_ORIGINAL)],
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB},
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x04,
        models=[
            "HF-LPB100",
            "HF-LPB100-0",
            "HF-LPB100-1",
            "HF-LPB100-ZJ002",
            "AK001-ZJ200",
        ],
        description="UFO Controller RGBW",  # AKA ZJ-WFUF-170F
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x06,
        # "AK001-ZJ2104" == v1 has RF remote support
        # "AK001-ZJ2145" == v2 has IR remote support
        # "AK001-ZJ2147" == v3 has RF remote support
        models=[
            "AK001-ZJ100",
            "AK001-ZJ200",
            "AK001-ZJ2104",
            "AK001-ZJ2145",
            "AK001-ZJ2147",
        ],
        description="Controller RGBW",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[
            MinVersionProtocol(2, PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS),
            MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE),
        ],
        mode_to_color_mode=GENERIC_RGBW_MAP,
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x07,
        # "AK001-ZJ2146" == v2 has RF remote support
        models=["AK001-ZJ2146"],
        description="Controller RGBCW",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[
            MinVersionProtocol(2, PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS),
            MinVersionProtocol(0, PROTOCOL_LEDENET_9BYTE),
        ],
        mode_to_color_mode=GENERIC_RGBWW_MAP,
        color_modes={COLOR_MODE_RGBWW},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x08,
        # AK001-ZJ2101 is v1
        # AK001-ZJ2145 is v2
        models=["AK001-ZJ2101", "AK001-ZJ2145", "AK001-ZJ2147"],
        description="Controller RGB with MIC",
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        protocols=[
            MinVersionProtocol(2, PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS),
            MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE),
        ],
        mode_to_color_mode=GENERIC_RGB_MAP,
        color_modes={COLOR_MODE_RGB},
        channel_map={},
        microphone=True,
    ),
    LEDENETModel(
        model_num=0x09,  # same as 0xE1
        models=[],
        description="High Voltage Ceiling Light CCT",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
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
        description="Switch 1c",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=set(),  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        # 'AK001-ZJ2104' likely supports turning on by effect/levels set
        # 'AK001-ZJ2104' is v7
        model_num=0x0E,
        models=["AK001-ZJ2104"],
        description="Floor Lamp RGBCW",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[
            MinVersionProtocol(7, PROTOCOL_LEDENET_9BYTE_AUTO_ON),
            MinVersionProtocol(0, PROTOCOL_LEDENET_9BYTE),
        ],
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
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS)],
        mode_to_color_mode={},
        color_modes=COLOR_MODES_ADDRESSABLE,
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x1A,
        models=["AK001-ZJ2147"],
        description="Christmas Light",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS)],
        mode_to_color_mode={},
        color_modes=COLOR_MODES_ADDRESSABLE,
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x16,
        models=[],
        description="Magnetic Light CCT",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
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
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
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
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=set(),  # no color modes -- UNVERIFIED
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x1B,
        models=[],
        description="Spray Light",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB},
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x19,
        models=[],
        description="Socket 2 USB",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=set(),  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x1C,
        # AK001-ZJ2149 has RF remote support
        models=["AK001-ZJ2149"],
        description="Table Light CCT",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_CCT)],
        mode_to_color_mode={},
        color_modes={COLOR_MODE_CCT},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x21,
        # 'AK001-ZJ200' is v1 but with new firmware it will change to v2
        # 'AK001-ZJ2104' is v2
        # 'AK001-ZJ2104' likely supports turning on by effect/levels set
        models=["AK001-ZJ200", "AK001-ZJ2101", "AK001-ZJ2104"],
        description="Bulb Dimmable",
        always_writes_white_and_colors=True,  # Verified required with AK001-ZJ200 bulb
        protocols=[
            MinVersionProtocol(2, PROTOCOL_LEDENET_8BYTE_AUTO_ON),
            MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE),
        ],
        mode_to_color_mode={},
        color_modes={COLOR_MODE_DIM},  # Formerly rgbwcapable
        channel_map={STATE_WARM_WHITE: STATE_RED, STATE_RED: STATE_WARM_WHITE},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x25,
        # 'AK001-ZJ200' == v2 - some devices have RF remote support (the mini ones)
        models=["HF-LPB100-ZJ200", "AK001-ZJ200"],
        description="Controller RGB/WW/CW",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_9BYTE)],
        mode_to_color_mode=BASE_MODE_MAP,
        color_modes={COLOR_MODE_RGBWW},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x33,
        # 'AK001-ZJ100' == v3 - WIFI370 version
        # 'AK001-ZJ2104' == v7 supports turning on by effect/levels set
        # 'AK001-ZJ2101' == v8 - no dimmable effects confirmed, confirmed auto on
        # "AK001-ZJ2145" == v9 # no rf support!
        # "AK001-ZJ2146" == v10 # rf support
        # "AK001-ZJ2148" == v10.63 # rf support
        models=[
            "AK001-ZJ210",
            "AK001-ZJ2104",
            "AK001-ZJ2101",
            "AK001-ZJ2145",
            "AK001-ZJ2146",
            "AK001-ZJ2148",
        ],
        description="Controller RGB",
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        protocols=[
            MinVersionProtocol(9, PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS),
            MinVersionProtocol(7, PROTOCOL_LEDENET_8BYTE_AUTO_ON),
            MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE),
        ],
        mode_to_color_mode=GENERIC_RGB_MAP,
        color_modes={COLOR_MODE_RGB},
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x35,
        # 'AK001-ZJ2101' and 'AK001-ZJ2104' is v7
        # 'AK001-ZJ2145' is v8
        # 'AK001-ZJ2146' is v9
        # 'AK001-ZJ2147' is v9.7
        # 'AK001-ZJ2146' 40w flood light, newer smart bulbs (with RF remote control support)
        models=[
            "AK001-ZJ2101",
            "AK001-ZJ2104",
            "AK001-ZJ2145",
            "AK001-ZJ2146",
            "AK001-ZJ2147",
        ],
        description="Bulb RGBCW",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[
            MinVersionProtocol(9, PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS),
            MinVersionProtocol(7, PROTOCOL_LEDENET_9BYTE_AUTO_ON),
            MinVersionProtocol(0, PROTOCOL_LEDENET_9BYTE),
        ],
        mode_to_color_mode={0x01: COLOR_MODES_RGB_CCT, 0x17: COLOR_MODES_RGB_CCT},
        color_modes=COLOR_MODES_RGB_CCT,
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x41,
        # 'AK001-ZJ2104' is v2
        # 'AK001-ZJ2104' likely supports turning on by effect/levels set
        models=["AK001-ZJ2104"],
        description="Controller Dimmable",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[
            MinVersionProtocol(2, PROTOCOL_LEDENET_8BYTE_AUTO_ON),
            MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE),
        ],
        mode_to_color_mode={},  # Only mode should be 0x41
        color_modes={COLOR_MODE_DIM},  # Formerly rgbwcapable
        channel_map={STATE_WARM_WHITE: STATE_RED, STATE_RED: STATE_WARM_WHITE},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x44,
        models=["AK001-ZJ200"],
        description="Bulb RGBW",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=COLOR_MODES_RGB_W,  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x45,
        models=[],
        description=UNKNOWN_MODEL,  # Unknown
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB, COLOR_MODE_DIM},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x52,
        models=[],
        description="Bulb CCT",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
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
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=COLOR_MODES_RGB_W,  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x62,
        models=[],
        description="Controller CCT",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
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
        description=UNKNOWN_MODEL,  # Unknown
        always_writes_white_and_colors=True,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGBW},  # Formerly rgbwcapable
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x93,
        # AK001-ZJ2146 == v3
        models=["AK001-ZJ2146"],
        description="Switch",  # 1 channel
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=set(),  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x94,
        models=[],
        description="Switch Watt",  # 1 channel
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=set(),  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x95,
        models=[],
        description="Switch 2 Channel",  # 2 channels
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=set(),  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x96,
        models=[],
        description="Switch 4 Channel",  # 4 channels
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=set(),  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0x97,  # 0x97
        # AK001-ZJ2146 = v3 (has BLE)
        models=["AK001-ZJ2134", "AK001-ZJ2146"],
        description="Socket",  # 1 channel
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=set(),  # no color modes
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0xA1,
        models=["AK001-ZJ210"],
        description="Addressable v1",
        always_writes_white_and_colors=False,
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_ADDRESSABLE_A1)],
        mode_to_color_mode={},
        color_modes=COLOR_MODES_ADDRESSABLE,
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0xA2,
        # 'AK001-ZJ2104' likely supports turning on by effect/levels set
        models=["AK001-ZJ2104"],
        description="Addressable v2",
        always_writes_white_and_colors=False,
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_ADDRESSABLE_A2)],
        mode_to_color_mode={},
        color_modes=COLOR_MODES_ADDRESSABLE,
        channel_map={},
        microphone=True,
    ),
    LEDENETModel(
        model_num=0xA3,
        # AK001-ZJ2147 has RF remote support
        # AK001-ZJ2148 has RF remote support
        models=["AK001-ZJ2147", "AK001-ZJ2148"],
        description="Addressable v3",
        always_writes_white_and_colors=False,
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_ADDRESSABLE_A3)],
        mode_to_color_mode={},
        color_modes=COLOR_MODES_ADDRESSABLE,
        channel_map={},
        microphone=True,
    ),
    LEDENETModel(
        model_num=0xA4,
        models=["AK001-ZJ2149"],
        description="Addressable v4",
        always_writes_white_and_colors=False,
        protocols=[
            MinVersionProtocol(0, PROTOCOL_LEDENET_ADDRESSABLE_A3)
        ],  # Currently no difference from v3 proto
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
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=set(),  # no color modes -- UNVERIFIED
        channel_map={},
        microphone=False,
    ),
    LEDENETModel(
        model_num=0xE1,
        models=["AK001-ZJ2104"],
        description="Ceiling Light CCT",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
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
        model_num=0xE2,
        models=[],
        description="Ceiling Light Assist",
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, PROTOCOL_LEDENET_8BYTE)],
        mode_to_color_mode={},
        color_modes=set(),  # no color modes -- UNVERIFIED
        channel_map={},
        microphone=False,
    ),
]

MODEL_MAP: Dict[int, LEDENETModel] = {model.model_num: model for model in MODELS}


def get_model(model_num: int, fallback_protocol: Optional[str] = None) -> LEDENETModel:
    """Return the LEDNETModel for the model_num."""
    return MODEL_MAP.get(
        model_num,
        _unknown_ledenet_model(model_num, fallback_protocol or PROTOCOL_LEDENET_8BYTE),
    )


def is_known_model(model_num: int) -> bool:
    """Return true of the model is known."""
    return model_num in MODEL_MAP


def _unknown_ledenet_model(model_num: int, fallback_protocol: str) -> LEDENETModel:
    """Create a LEDNETModel for an unknown model_num."""
    return LEDENETModel(
        model_num=model_num,
        models=[],
        description=UNKNOWN_MODEL,
        always_writes_white_and_colors=False,  # Formerly rgbwprotocol
        protocols=[MinVersionProtocol(0, fallback_protocol)],
        mode_to_color_mode={},
        color_modes={COLOR_MODE_RGB},
        channel_map={},
        microphone=False,
    )


def get_model_description(model_num: int, model_info: Optional[str]) -> str:
    """Return the description for a model."""
    return format_model_description(get_model(model_num).description, model_info)


def format_model_description(description: str, model_info: Optional[str]) -> str:
    """Format the description for a model."""
    if model_info:
        extra = MODEL_INFO_NAMES.get(model_info)
        if extra:
            return f"{description} {extra}"
    return description
