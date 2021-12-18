import colorsys
from enum import Enum
import logging
import random
import time
from typing import Dict, Iterable, List, Optional, Set, Tuple, Type, Union

from .const import (  # imported for back compat, remove once Home Assistant no longer uses
    ADDRESSABLE_STATE_CHANGE_LATENCY,
    ATTR_MODEL_DESCRIPTION,
    CHANNEL_STATES,
    COLOR_MODE_CCT,
    COLOR_MODE_DIM,
    COLOR_MODE_RGB,
    COLOR_MODE_RGBW,
    COLOR_MODE_RGBWW,
    COLOR_MODES_RGB,
    COLOR_MODES_RGB_CCT,
    COLOR_MODES_RGB_W,
    DEFAULT_MODE,
    EFFECT_MUSIC,
    EFFECT_RANDOM,
    MAX_TEMP,
    MIN_TEMP,
    MODE_COLOR,
    MODE_CUSTOM,
    MODE_MUSIC,
    MODE_PRESET,
    MODE_SWITCH,
    MODE_WW,
    MODEL_NUMS_SWITCHS,
    PRESET_MUSIC_MODE,
    PRESET_MUSIC_MODE_LEGACY,
    STATE_BLUE,
    STATE_CHANGE_LATENCY,
    STATE_COOL_WHITE,
    STATE_GREEN,
    STATE_RED,
    STATE_WARM_WHITE,
    STATIC_MODES,
    WRITE_ALL_COLORS,
    WRITE_ALL_WHITES,
    LevelWriteMode,
)
from .models_db import BASE_MODE_MAP, LEDENETModel, get_model, is_known_model
from .pattern import (
    ADDRESSABLE_EFFECT_ID_NAME,
    ADDRESSABLE_EFFECT_NAME_ID,
    ASSESSABLE_MULTI_COLOR_ID_NAME,
    CHRISTMAS_ADDRESSABLE_EFFECT_ID_NAME,
    CHRISTMAS_ADDRESSABLE_EFFECT_NAME_ID,
    EFFECT_CUSTOM,
    EFFECT_CUSTOM_CODE,
    EFFECT_ID_NAME,
    EFFECT_LIST,
    EFFECT_LIST_AUTO_ON,
    ORIGINAL_ADDRESSABLE_EFFECT_ID_NAME,
    ORIGINAL_ADDRESSABLE_EFFECT_NAME_ID,
    PresetPattern,
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
    LEDENETOriginalRawState,
    LEDENETRawState,
    ProtocolLEDENET8Byte,
    ProtocolLEDENET8ByteAutoOn,
    ProtocolLEDENET8ByteDimmableEffects,
    ProtocolLEDENET9Byte,
    ProtocolLEDENET9ByteAutoOn,
    ProtocolLEDENET9ByteDimmableEffects,
    ProtocolLEDENETAddressableA1,
    ProtocolLEDENETAddressableA2,
    ProtocolLEDENETAddressableA3,
    ProtocolLEDENETAddressableChristmas,
    ProtocolLEDENETCCT,
    ProtocolLEDENETOriginal,
)
from .scanner import FluxLEDDiscovery
from .timer import BuiltInTimer
from .utils import scaled_color_temp_to_white_levels, utils, white_levels_to_color_temp

_LOGGER = logging.getLogger(__name__)


PROTOCOL_PROBES: Tuple[Type[ProtocolLEDENET8Byte], Type[ProtocolLEDENETOriginal]] = (
    ProtocolLEDENET8Byte,
    ProtocolLEDENETOriginal,
)

PROTOCOL_TYPES = Union[
    ProtocolLEDENET8Byte,
    ProtocolLEDENET8ByteAutoOn,
    ProtocolLEDENET8ByteDimmableEffects,
    ProtocolLEDENET9Byte,
    ProtocolLEDENET9ByteAutoOn,
    ProtocolLEDENET9ByteDimmableEffects,
    ProtocolLEDENETAddressableA1,
    ProtocolLEDENETAddressableA2,
    ProtocolLEDENETAddressableA3,
    ProtocolLEDENETOriginal,
    ProtocolLEDENETCCT,
    ProtocolLEDENETAddressableChristmas,
]

ADDRESSABLE_PROTOCOLS = {
    PROTOCOL_LEDENET_ADDRESSABLE_A1,
    PROTOCOL_LEDENET_ADDRESSABLE_A2,
    PROTOCOL_LEDENET_ADDRESSABLE_A3,
}
CHRISTMAS_EFFECTS_PROTOCOLS = {PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS}
OLD_EFFECTS_PROTOCOLS = {PROTOCOL_LEDENET_ADDRESSABLE_A1}
NEW_EFFECTS_PROTOCOLS = {
    PROTOCOL_LEDENET_ADDRESSABLE_A2,
    PROTOCOL_LEDENET_ADDRESSABLE_A3,
}
SPEED_ADJUST_WILL_TURN_ON = {
    PROTOCOL_LEDENET_ADDRESSABLE_A1,
    PROTOCOL_LEDENET_ADDRESSABLE_A2,
}
PROTOCOL_NAME_TO_CLS = {
    PROTOCOL_LEDENET_ORIGINAL: ProtocolLEDENETOriginal,
    PROTOCOL_LEDENET_8BYTE: ProtocolLEDENET8Byte,
    PROTOCOL_LEDENET_8BYTE_AUTO_ON: ProtocolLEDENET8ByteAutoOn,
    PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS: ProtocolLEDENET8ByteDimmableEffects,
    PROTOCOL_LEDENET_9BYTE: ProtocolLEDENET9Byte,
    PROTOCOL_LEDENET_9BYTE_AUTO_ON: ProtocolLEDENET9ByteAutoOn,
    PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS: ProtocolLEDENET9ByteDimmableEffects,
    PROTOCOL_LEDENET_ADDRESSABLE_A3: ProtocolLEDENETAddressableA3,
    PROTOCOL_LEDENET_ADDRESSABLE_A2: ProtocolLEDENETAddressableA2,
    PROTOCOL_LEDENET_ADDRESSABLE_A1: ProtocolLEDENETAddressableA1,
    PROTOCOL_LEDENET_CCT: ProtocolLEDENETCCT,
    PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS: ProtocolLEDENETAddressableChristmas,
}


PATTERN_CODE_TO_EFFECT = {
    PRESET_MUSIC_MODE: MODE_MUSIC,
    PRESET_MUSIC_MODE_LEGACY: MODE_MUSIC,
    EFFECT_CUSTOM_CODE: EFFECT_CUSTOM,
}


class DeviceType(Enum):
    Bulb = 0
    Switch = 1


class LEDENETDevice:
    """An LEDENET Device."""

    def __init__(self, ipaddr: str, port: int = 5577, timeout: float = 5) -> None:
        """Init the LEDENEt Device."""
        self.ipaddr: str = ipaddr
        self.port: int = port
        self.timeout: float = timeout
        self.raw_state: Optional[Union[LEDENETOriginalRawState, LEDENETRawState]] = None
        self.available: Optional[bool] = None
        self._model_num: Optional[int] = None
        self._model_data: Optional[LEDENETModel] = None
        self._discovery: Optional[FluxLEDDiscovery] = None
        self._protocol: Optional[PROTOCOL_TYPES] = None
        self._mode: Optional[str] = None
        self._transition_complete_time: float = 0
        self._last_effect_brightness: int = 100

    @property
    def model_num(self) -> int:
        """Return the model number."""
        assert self._model_num is not None
        return self._model_num

    @property
    def model_data(self) -> LEDENETModel:
        """Return the model data."""
        assert self._model_data is not None
        return self._model_data

    @property
    def discovery(self) -> Optional[FluxLEDDiscovery]:
        """Return the discovery data."""
        return self._discovery

    @discovery.setter
    def discovery(self, value: FluxLEDDiscovery) -> None:
        """Set the discovery data."""
        self._discovery = value

    @property
    def speed_adjust_off(self) -> int:
        """Return true if the speed of an effect can be adjusted while off."""
        return self.protocol not in SPEED_ADJUST_WILL_TURN_ON

    @property
    def _whites_are_temp_brightness(self) -> bool:
        """Return true if warm_white and cool_white are scaled temp values and not raw 0-255."""
        return self.protocol == PROTOCOL_LEDENET_CCT

    @property
    def model(self) -> str:
        """Return the human readable model description."""
        if self._discovery and self._discovery[ATTR_MODEL_DESCRIPTION]:
            return f"{self._discovery[ATTR_MODEL_DESCRIPTION]} (0x{self.model_num:02X})"
        return f"{self.model_data.description} (0x{self.model_num:02X})"

    @property
    def version_num(self) -> int:
        """Return the version number."""
        assert self.raw_state is not None
        raw_state = self.raw_state
        if hasattr(raw_state, "version_number"):
            assert isinstance(raw_state, LEDENETRawState)
            return raw_state.version_number
        return 1

    @property
    def preset_pattern_num(self) -> int:
        """Return the preset pattern number."""
        assert self.raw_state is not None
        return self.raw_state.preset_pattern

    @property
    def rgbwprotocol(self) -> bool:
        """Devices that don't require a separate rgb/w bit."""
        return self.model_data.always_writes_white_and_colors

    @property
    def microphone(self) -> bool:
        """Devices that have a microphone built in."""
        return self.model_data.microphone

    @property
    def rgbwcapable(self) -> bool:
        """Devices that actually support rgbw."""
        color_modes = self.color_modes
        return COLOR_MODE_RGBW in color_modes or COLOR_MODE_RGBWW in color_modes

    @property
    def device_type(self) -> DeviceType:
        """Return the device type."""
        is_switch = self.model_num in MODEL_NUMS_SWITCHS
        return DeviceType.Switch if is_switch else DeviceType.Bulb

    @property
    def color_temp(self) -> int:
        """Return the current color temp in kelvin."""
        return (self.getWhiteTemperature())[0]

    @property
    def min_temp(self) -> int:
        """Returns the minimum color temp in kelvin."""
        return MIN_TEMP

    @property
    def max_temp(self) -> int:
        """Returns the maximum color temp in kelvin."""
        return MAX_TEMP

    @property
    def _rgbwwprotocol(self) -> bool:
        """Device that uses the 9-byte protocol."""
        return self.protocol in (
            PROTOCOL_LEDENET_9BYTE,
            PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS,
        )

    @property
    def white_active(self) -> bool:
        """Any white channel is active."""
        assert self.raw_state is not None
        raw_state = self.raw_state
        if hasattr(raw_state, "cool_white"):
            assert isinstance(raw_state, LEDENETRawState)
            return bool(raw_state.warm_white or raw_state.cool_white)
        return bool(raw_state.warm_white)

    @property
    def color_active(self) -> bool:
        """Any color channel is active."""
        assert self.raw_state is not None
        raw_state = self.raw_state
        return bool(raw_state.red or raw_state.green or raw_state.blue)

    @property
    def multi_color_mode(self) -> bool:
        """The device supports multiple color modes."""
        return len(self.color_modes) > 1

    @property
    def color_modes(self) -> Set[str]:
        """The available color modes."""
        color_modes = self._internal_color_modes
        # We support CCT mode if the device supports RGBWW
        # but we do not add it to internal color modes as
        # we need to distingush between devices that are RGB/CCT
        # and ones that are RGB&CCT
        if COLOR_MODE_RGBWW in color_modes and COLOR_MODE_CCT not in color_modes:
            return {COLOR_MODE_CCT, *color_modes}
        return color_modes

    @property
    def _internal_color_modes(self) -> Set[str]:
        """The internal available color modes."""
        assert self.raw_state is not None
        if not is_known_model(self.model_num):
            # Default mode is RGB
            return BASE_MODE_MAP.get(self.raw_state.mode & 0x0F, {DEFAULT_MODE})
        model_data = self.model_data
        return model_data.mode_to_color_mode.get(
            self.raw_state.mode, model_data.color_modes
        )

    @property
    def color_mode(self) -> Optional[str]:
        """The current color mode."""
        color_modes = self._internal_color_modes
        if COLOR_MODE_RGBWW in color_modes:
            # We support CCT mode if the device supports RGBWW
            return COLOR_MODE_RGBWW if self.color_active else COLOR_MODE_CCT
        if (
            color_modes == COLOR_MODES_RGB_CCT
        ):  # RGB/CCT split, only one active at a time
            return COLOR_MODE_CCT if self.white_active else COLOR_MODE_RGB
        if color_modes == COLOR_MODES_RGB_W:  # RGB/W split, only one active at a time
            return COLOR_MODE_DIM if self.white_active else COLOR_MODE_RGB
        if color_modes:
            return list(color_modes)[0]
        return None  # Usually a switch or non-light device

    @property
    def protocol(self) -> Optional[str]:
        """Returns the name of the protocol in use."""
        if self._protocol is None:
            return None
        return self._protocol.name

    @property
    def dimmable_effects(self) -> bool:
        """Return true of the device supports dimmable effects."""
        assert self._protocol is not None
        return self._protocol.dimmable_effects

    @property
    def requires_turn_on(self) -> bool:
        """Return true of the device requires a power on command before setting levels/effects."""
        assert self._protocol is not None
        return self._protocol.requires_turn_on

    @property
    def is_on(self) -> bool:
        assert self.raw_state is not None
        assert self._protocol is not None
        return self.raw_state.power_state == self._protocol.on_byte

    @property
    def mode(self) -> Optional[str]:
        return self._mode

    @property
    def warm_white(self) -> int:
        assert self.raw_state is not None
        return self.raw_state.warm_white if self._rgbwwprotocol else 0

    @property
    def effect_list(self) -> List[str]:
        """Return the list of available effects."""
        effects: Iterable[str] = []
        protocol = self.protocol
        if protocol in OLD_EFFECTS_PROTOCOLS:
            effects = ORIGINAL_ADDRESSABLE_EFFECT_ID_NAME.values()
        elif protocol in NEW_EFFECTS_PROTOCOLS:
            effects = ADDRESSABLE_EFFECT_ID_NAME.values()
        elif protocol in CHRISTMAS_EFFECTS_PROTOCOLS:
            effects = CHRISTMAS_ADDRESSABLE_EFFECT_ID_NAME.values()
        elif COLOR_MODES_RGB.intersection(self.color_modes):
            effects = EFFECT_LIST if self.requires_turn_on else EFFECT_LIST_AUTO_ON
        if self.microphone:
            return [*effects, EFFECT_RANDOM, EFFECT_MUSIC]
        return [*effects, EFFECT_RANDOM]

    @property
    def effect(self) -> Optional[str]:
        """Return the current effect."""
        if self.protocol in CHRISTMAS_EFFECTS_PROTOCOLS:
            return self._named_effect
        return PATTERN_CODE_TO_EFFECT.get(self.preset_pattern_num, self._named_effect)

    @property
    def _named_effect(self) -> Optional[str]:
        """Returns the named effect."""
        assert self.raw_state is not None
        mode = self.raw_state.mode
        pattern_code = self.preset_pattern_num
        protocol = self.protocol
        if protocol in OLD_EFFECTS_PROTOCOLS:
            effect_id = (pattern_code << 8) + mode - 99
            return ORIGINAL_ADDRESSABLE_EFFECT_ID_NAME.get(effect_id)
        if protocol in NEW_EFFECTS_PROTOCOLS:
            if pattern_code == 0x25:
                return ADDRESSABLE_EFFECT_ID_NAME.get(mode)
            if pattern_code == 0x24:
                return ASSESSABLE_MULTI_COLOR_ID_NAME.get(mode)
        if protocol in CHRISTMAS_EFFECTS_PROTOCOLS:
            if pattern_code == 0x60:
                return CHRISTMAS_ADDRESSABLE_EFFECT_ID_NAME.get(mode)
        return EFFECT_ID_NAME.get(pattern_code)

    @property
    def cool_white(self) -> int:
        assert self.raw_state is not None
        if self._rgbwwprotocol:
            assert isinstance(self.raw_state, LEDENETRawState)
            return self.raw_state.cool_white
        return 0

    # Old name is deprecated
    @property
    def cold_white(self) -> int:
        return self.cool_white

    @property
    def brightness(self) -> int:
        """Return current brightness 0-255.

        For warm white return current led level. For RGB
        calculate the HSV and return the 'value'.
        for CCT calculate the brightness.
        for ww send led level
        """
        color_mode = self.color_mode
        raw_state = self.raw_state
        assert raw_state is not None

        if self._named_effect:
            if self.dimmable_effects:
                if (
                    self.protocol in NEW_EFFECTS_PROTOCOLS
                    and time.monotonic() > self._transition_complete_time
                ):
                    # the red byte holds the brightness during an effect
                    return min(255, round(raw_state.red * 255 / 100))
                return round(self._last_effect_brightness * 255 / 100)
            return 255
        if color_mode == COLOR_MODE_DIM:
            return int(raw_state.warm_white)
        elif color_mode == COLOR_MODE_CCT:
            _, b = self.getWhiteTemperature()
            return b

        r, g, b = self.getRgb()
        _, _, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        v_255 = v * 255
        if color_mode == COLOR_MODE_RGBW:
            return round((v_255 + raw_state.warm_white) / 2)
        if color_mode == COLOR_MODE_RGBWW:
            assert isinstance(raw_state, LEDENETRawState)
            return round((v_255 + raw_state.warm_white + raw_state.cool_white) / 3)

        # Default color mode (RGB)
        return int(v_255)

    def _determineMode(self) -> Optional[str]:
        assert self.raw_state is not None
        pattern_code = self.raw_state.preset_pattern
        if self.device_type == DeviceType.Switch:
            return MODE_SWITCH
        if pattern_code in (0x41, 0x61):
            if self.color_mode in {COLOR_MODE_DIM, COLOR_MODE_CCT}:
                return MODE_WW
            return MODE_COLOR
        elif pattern_code == EFFECT_CUSTOM_CODE:
            return (
                MODE_PRESET
                if self.protocol in CHRISTMAS_EFFECTS_PROTOCOLS
                else MODE_CUSTOM
            )
        elif pattern_code in (PRESET_MUSIC_MODE, PRESET_MUSIC_MODE_LEGACY):
            return MODE_MUSIC
        elif PresetPattern.valid(pattern_code):
            return MODE_PRESET
        elif BuiltInTimer.valid(pattern_code):
            return BuiltInTimer.valtostr(pattern_code)
        elif self.protocol in ADDRESSABLE_PROTOCOLS:
            return MODE_PRESET
        return None

    def set_unavailable(self) -> None:
        self.available = False

    def set_available(self) -> None:
        self.available = True

    def process_state_response(self, rx: bytes) -> bool:
        assert self._protocol is not None

        if not self._protocol.is_valid_state_response(rx):
            _LOGGER.warning(
                "%s: Recieved invalid response: %s",
                self.ipaddr,
                utils.raw_state_to_dec(rx),
            )
            return False

        raw_state: Union[
            LEDENETOriginalRawState, LEDENETRawState
        ] = self._protocol.named_raw_state(rx)
        _LOGGER.debug("%s: State: %s", self.ipaddr, raw_state)

        if raw_state != self.raw_state:
            _LOGGER.debug(
                "%s: unmapped raw state: %s",
                self.ipaddr,
                utils.raw_state_to_dec(raw_state),
            )

        if time.monotonic() < self._transition_complete_time:
            # Do not update the channel states if a transition is
            # in progress as the state will not be correct
            # until the transition is completed since devices
            # "FADE" into the state requested.
            self._replace_raw_state(
                {
                    name: value
                    for name, value in raw_state._asdict().items()
                    if name not in CHANNEL_STATES
                }
            )
        else:
            self._set_raw_state(raw_state)

        _LOGGER.debug("%s: Mapped State: %s", self.ipaddr, self.raw_state)

        mode = self._determineMode()

        if mode is None:
            _LOGGER.debug(
                "%s: Unable to determine mode from raw state: %s",
                self.ipaddr,
                utils.raw_state_to_dec(rx),
            )
            return False

        self._mode = mode
        return True

    def process_power_state_response(self, msg: bytes) -> bool:
        """Process a power state change message."""
        assert self._protocol is not None
        if not self._protocol.is_valid_power_state_response(msg):
            _LOGGER.warning(
                "%s: Recieved invalid power state response: %s",
                self.ipaddr,
                utils.raw_state_to_dec(msg),
            )
            return False
        _LOGGER.debug("%s: Setting power state to: %s", self.ipaddr, f"0x{msg[2]:02X}")
        self._set_power_state(msg[2])
        return True

    def _set_raw_state(
        self,
        raw_state: Union[LEDENETOriginalRawState, LEDENETRawState],
        updated: Optional[Set[str]] = None,
    ) -> None:
        """Set the raw state remapping channels as needed.

        The goal is to normalize the data so the raw state
        is always in the same format reguardless of the protocol

        Some devices need to have channels remapped

        Other devices uses color_temp/brightness format
        which needs to be converted back to 0-255 values for
        warm_white and cool_white
        """
        channel_map = self.model_data.channel_map
        # Only remap updated states as we do not want to switch any
        # state that have not changed since they will already be in
        # the correct slot
        #
        # If updated is None than all raw_state values have been sent
        #
        if self._whites_are_temp_brightness:
            assert isinstance(raw_state, LEDENETRawState)
            # Only convert on a full update since we still use 0-255 internally
            if updated is not None:
                self.raw_state = raw_state
                return
            # warm_white is the color temp from 1-100
            temp = raw_state.warm_white
            # cold_white is the brightness from 1-100
            brightness = raw_state.cool_white
            warm_white, cool_white = scaled_color_temp_to_white_levels(temp, brightness)
            self.raw_state = raw_state._replace(
                warm_white=warm_white, cool_white=cool_white
            )
            return

        if channel_map:
            if updated is None:
                updated = set(channel_map.keys())
            self.raw_state = raw_state._replace(
                **{
                    name: getattr(raw_state, source)
                    if source in updated
                    else getattr(raw_state, name)
                    for name, source in channel_map.items()
                }
            )
            return

        self.raw_state = raw_state

    def __str__(self) -> str:  # noqa: C901
        assert self.raw_state is not None
        assert self._protocol is not None

        rx = self.raw_state
        if not rx:
            return "No state data"
        mode = self.mode
        color_mode = self.color_mode
        power_str = "Unknown power state"
        if rx.power_state == self._protocol.on_byte:
            power_str = "ON "
        elif rx.power_state == self._protocol.off_byte:
            power_str = "OFF "

        if mode in STATIC_MODES:
            if color_mode in COLOR_MODES_RGB:
                mode_str = f"Color: {(rx.red, rx.green, rx.blue)}"
                # Should add ability to get CCT from rgbwcapable*
                if self.rgbwcapable:
                    mode_str += f" White: {rx.warm_white}"
                else:
                    mode_str += f" Brightness: {round(self.brightness * 100 / 255)}%"
            elif color_mode == COLOR_MODE_DIM:
                mode_str = f"Warm White: {utils.byteToPercent(rx.warm_white)}%"
            elif color_mode == COLOR_MODE_CCT:
                cct_value = self.getWhiteTemperature()
                mode_str = "CCT: {}K Brightness: {}%".format(
                    cct_value[0], round(cct_value[1] * 100 / 255)
                )
        elif mode == MODE_PRESET:
            mode_str = f"Pattern: {self.effect} (Speed {self.speed}%)"
        elif mode == MODE_CUSTOM:
            mode_str = f"Custom pattern (Speed {self.speed}%)"
        elif BuiltInTimer.valid(rx.preset_pattern):
            mode_str = BuiltInTimer.valtostr(rx.preset_pattern)
        elif mode == MODE_MUSIC:
            mode_str = "Music"
        elif mode == MODE_SWITCH:
            mode_str = "Switch"
        else:
            mode_str = f"Unknown mode 0x{rx.preset_pattern:x}"
        mode_str += " raw state: "
        mode_str += utils.raw_state_to_dec(rx)
        return f"{power_str} [{mode_str}]"

    def _set_power_state(self, new_power_state: int) -> None:
        """Set the power state in the raw state."""
        self._replace_raw_state({"power_state": new_power_state})
        self._set_transition_complete_time()

    def _replace_raw_state(self, new_states: Dict[str, int]) -> None:
        assert self.raw_state is not None
        _LOGGER.debug("%s: _replace_raw_state: %s", self.ipaddr, new_states)
        self._set_raw_state(
            self.raw_state._replace(**new_states), set(new_states.keys())
        )

    def isOn(self) -> bool:
        return self.is_on

    def getWarmWhite255(self) -> int:
        if self.color_mode not in {COLOR_MODE_CCT, COLOR_MODE_DIM}:
            return 255
        return self.brightness

    def getWhiteTemperature(self) -> Tuple[int, int]:
        """Returns the color temp and brightness"""
        # Assume input temperature of between 2700 and 6500 Kelvin, and scale
        # the warm and cold LEDs linearly to provide that
        assert self.raw_state is not None
        assert isinstance(self.raw_state, LEDENETRawState)
        raw_state = self.raw_state
        temp, brightness = white_levels_to_color_temp(
            raw_state.warm_white, raw_state.cool_white
        )
        return temp, brightness

    def getRgbw(self) -> Tuple[int, int, int, int]:
        """Returns red,green,blue,white (usually warm)."""
        if self.color_mode not in COLOR_MODES_RGB:
            return (255, 255, 255, 255)
        return self.rgbw

    @property
    def rgbw(self) -> Tuple[int, int, int, int]:
        """Returns red,green,blue,white (usually warm)."""
        assert self.raw_state is not None
        raw_state = self.raw_state
        return (
            raw_state.red,
            raw_state.green,
            raw_state.blue,
            raw_state.warm_white,
        )

    def getRgbww(self) -> Tuple[int, int, int, int, int]:
        """Returns red,green,blue,warm,cool."""
        if self.color_mode not in COLOR_MODES_RGB:
            return (255, 255, 255, 255, 255)
        return self.rgbww

    @property
    def rgbww(self) -> Tuple[int, int, int, int, int]:
        """Returns red,green,blue,warm,cool."""
        assert isinstance(self.raw_state, LEDENETRawState)
        raw_state = self.raw_state
        return (
            raw_state.red,
            raw_state.green,
            raw_state.blue,
            raw_state.warm_white,
            raw_state.cool_white,
        )

    def getRgbcw(self) -> Tuple[int, int, int, int, int]:
        """Returns red,green,blue,cool,warm."""
        if self.color_mode not in COLOR_MODES_RGB:
            return (255, 255, 255, 255, 255)
        return self.rgbcw

    @property
    def rgbcw(self) -> Tuple[int, int, int, int, int]:
        """Returns red,green,blue,cool,warm."""
        assert isinstance(self.raw_state, LEDENETRawState)
        raw_state = self.raw_state
        return (
            raw_state.red,
            raw_state.green,
            raw_state.blue,
            raw_state.cool_white,
            raw_state.warm_white,
        )

    def getCCT(self) -> Tuple[int, int]:
        if self.color_mode != COLOR_MODE_CCT:
            return (255, 255)
        assert isinstance(self.raw_state, LEDENETRawState)
        raw_state = self.raw_state
        return (raw_state.warm_white, raw_state.cool_white)

    @property
    def speed(self) -> int:
        assert self.raw_state is not None
        if self.protocol in ADDRESSABLE_PROTOCOLS:
            return self.raw_state.speed
        if self.protocol in CHRISTMAS_EFFECTS_PROTOCOLS:
            return utils.delayToSpeed(self.raw_state.green)
        return utils.delayToSpeed(self.raw_state.speed)

    def getSpeed(self) -> int:
        return self.speed

    def _generate_random_levels_change(self) -> Tuple[bytearray, Dict[str, int]]:
        """Generate a random levels change."""
        channels = {STATE_WARM_WHITE}
        if COLOR_MODES_RGB.intersection(self.color_modes):
            channels = {STATE_RED, STATE_GREEN, STATE_BLUE}
        elif COLOR_MODE_CCT in self.color_modes:
            channels = {STATE_WARM_WHITE, STATE_COOL_WHITE}
        return self._generate_levels_change(
            {
                channel: random.randint(0, 255) if channel in channels else None
                for channel in CHANNEL_STATES
            }
        )

    def _generate_levels_change(
        self,
        channels: Dict[str, Optional[int]],
        persist: bool = True,
        brightness: Optional[int] = None,
    ) -> Tuple[bytearray, Dict[str, int]]:
        """Generate the levels change request."""
        channel_map = self.model_data.channel_map
        if channel_map:
            mapped_channels = {
                channel: channels[channel_map.get(channel, channel)]
                for channel in channels
            }
        else:
            mapped_channels = channels

        r = mapped_channels[STATE_RED]
        g = mapped_channels[STATE_GREEN]
        b = mapped_channels[STATE_BLUE]
        w = mapped_channels[STATE_WARM_WHITE]
        w2 = mapped_channels[STATE_COOL_WHITE]

        if (r or g or b) and (w or w2) and not self.rgbwcapable:
            raise ValueError("RGB&CW command sent to non-RGB&CW device")

        if brightness is not None and r is not None and g is not None and b is not None:
            (r, g, b) = self._calculateBrightness((r, g, b), brightness)

        r_value = 0 if r is None else int(r)
        g_value = 0 if g is None else int(g)
        b_value = 0 if b is None else int(b)
        w_value = 0 if w is None else int(w)
        # ProtocolLEDENET9Byte devices support two white outputs for cold and warm.
        if w2 is None:
            # If we're only setting a single white value,
            # we set the second output to be the same as the first
            w2_value = (
                int(w) if w is not None and self.color_mode != COLOR_MODE_CCT else 0
            )
        else:
            w2_value = int(w2)

        write_mode = LevelWriteMode.ALL
        # rgbwprotocol always overwrite both color & whites
        if not self.rgbwprotocol:
            if w is None and w2 is None:
                write_mode = LevelWriteMode.COLORS
            elif r is None and g is None and b is None:
                write_mode = LevelWriteMode.WHITES

        _LOGGER.debug(
            "%s: _generate_levels_change using %s: persist=%s r=%s/%s, g=%s/%s b=%s/%s, w=%s/%s w2=%s/%s write_mode=%s/%s",
            self.ipaddr,
            self.protocol,
            persist,
            r_value,
            f"0x{r_value:02X}",
            g_value,
            f"0x{g_value:02X}",
            b_value,
            f"0x{b_value:02X}",
            w_value,
            f"0x{w_value:02X}",
            w2_value,
            f"0x{w2_value:02X}",
            write_mode,
            f"0x{write_mode.value:02X}",
        )

        assert self._protocol is not None
        msg = self._protocol.construct_levels_change(
            persist, r_value, g_value, b_value, w_value, w2_value, write_mode
        )
        updates = {}
        multi_mode = self.multi_color_mode
        if multi_mode or write_mode in WRITE_ALL_COLORS:
            updates.update({"red": r_value, "green": g_value, "blue": b_value})
        if multi_mode or write_mode in WRITE_ALL_WHITES:
            updates.update({"warm_white": w_value, "cool_white": w2_value})
        return msg, updates

    def _set_transition_complete_time(self) -> None:
        """Set the time we expect the transition will be completed.

        Devices fade to a specific state so we want to avoid
        consuming state updates into self.raw_state while a transition
        is in progress as this will provide unexpected results
        and the brightness values will be wrong until
        the transition completes.
        """
        assert self.raw_state is not None
        latency = STATE_CHANGE_LATENCY
        if self.protocol in ADDRESSABLE_PROTOCOLS:
            latency = ADDRESSABLE_STATE_CHANGE_LATENCY
        transition_time = latency + utils.speedToDelay(self.raw_state.speed) / 100
        self._transition_complete_time = time.monotonic() + transition_time
        _LOGGER.debug(
            "%s: Transition time is %s, set _transition_complete_time to %s",
            self.ipaddr,
            transition_time,
            self._transition_complete_time,
        )

    def getRgb(self) -> Tuple[int, int, int]:
        if self.color_mode not in COLOR_MODES_RGB:
            return (255, 255, 255)
        return self.rgb

    @property
    def rgb(self) -> Tuple[int, int, int]:
        assert self.raw_state is not None
        raw_state = self.raw_state
        return (raw_state.red, raw_state.green, raw_state.blue)

    @property
    def rgb_unscaled(self) -> Tuple[int, int, int]:
        """Return the unscaled RGB."""
        r, g, b = self.rgb
        hsv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        r_p, g_p, b_p = colorsys.hsv_to_rgb(hsv[0], hsv[1], 1)
        return round(r_p * 255), round(g_p * 255), round(b_p * 255)

    def _calculateBrightness(
        self, rgb: Tuple[int, int, int], level: int
    ) -> Tuple[int, int, int]:
        hsv = colorsys.rgb_to_hsv(*rgb)
        r, g, b = colorsys.hsv_to_rgb(hsv[0], hsv[1], level)
        return int(r), int(g), int(b)

    def setProtocol(self, protocol: str) -> None:
        cls = PROTOCOL_NAME_TO_CLS.get(protocol)
        if cls is None:
            raise ValueError(f"Invalid protocol: {protocol}")
        self._protocol = cls()  # type: ignore

    def _set_protocol_from_msg(
        self,
        full_msg: bytes,
        fallback_protocol: str,
    ) -> None:
        self._model_num = full_msg[1]
        self._model_data = get_model(self._model_num, fallback_protocol)
        version_num = full_msg[10] if len(full_msg) > 10 else 1
        self.setProtocol(self._model_data.protocol_for_version_num(version_num))

    def _generate_preset_pattern(
        self, pattern: int, speed: int, brightness: int
    ) -> bytearray:
        """Generate the preset pattern protocol bytes."""
        protocol = self.protocol
        if protocol in OLD_EFFECTS_PROTOCOLS:
            if pattern not in ORIGINAL_ADDRESSABLE_EFFECT_ID_NAME:
                raise ValueError("Pattern must be between 1 and 302")
        elif protocol in NEW_EFFECTS_PROTOCOLS:
            if pattern not in ADDRESSABLE_EFFECT_ID_NAME:
                raise ValueError("Pattern must be between 1 and 100")
        elif protocol in CHRISTMAS_EFFECTS_PROTOCOLS:
            if pattern not in CHRISTMAS_ADDRESSABLE_EFFECT_ID_NAME:
                raise ValueError("Pattern must be between 1 and 100")
        else:
            PresetPattern.valtostr(pattern)
            if not PresetPattern.valid(pattern):
                raise ValueError("Pattern must be between 0x24 and 0x3a")
        if not (1 <= brightness <= 100):
            raise ValueError("Brightness must be between 1 and 100")
        self._last_effect_brightness = brightness
        assert self._protocol is not None
        return self._protocol.construct_preset_pattern(pattern, speed, brightness)

    def _generate_custom_patterm(
        self, rgb_list: List[Tuple[int, int, int]], speed: int, transition_type: str
    ) -> bytearray:
        """Generate the custom pattern protocol bytes."""
        # truncate if more than 16
        if len(rgb_list) > 16:
            _LOGGER.warning(
                "Too many colors in %s, truncating list to %s", len(rgb_list), 16
            )
            del rgb_list[16:]
        # quit if too few
        if len(rgb_list) == 0:
            raise ValueError("setCustomPattern requires at least one color tuples")

        assert self._protocol is not None
        return self._protocol.construct_custom_effect(rgb_list, speed, transition_type)

    def _effect_to_pattern(self, effect: str) -> int:
        """Convert an effect to a pattern code."""
        protocol = self.protocol
        if protocol in CHRISTMAS_EFFECTS_PROTOCOLS:
            return CHRISTMAS_ADDRESSABLE_EFFECT_NAME_ID[effect]
        if protocol in NEW_EFFECTS_PROTOCOLS:
            return ADDRESSABLE_EFFECT_NAME_ID[effect]
        if protocol in OLD_EFFECTS_PROTOCOLS:
            return ORIGINAL_ADDRESSABLE_EFFECT_NAME_ID[effect]
        return PresetPattern.str_to_val(effect)
