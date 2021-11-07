import colorsys
from enum import Enum
import logging
import time

from .const import (  # imported for back compat, remove once Home Assistant no longer uses
    ADDRESSABLE_STATE_CHANGE_LATENCY,
    CHANNEL_STATES,
    COLOR_MODE_ADDRESSABLE,
    COLOR_MODE_CCT,
    COLOR_MODE_DIM,
    COLOR_MODE_RGB,
    COLOR_MODE_RGBW,
    COLOR_MODE_RGBWW,
    COLOR_MODES_RGB,
    COLOR_MODES_RGB_CCT,
    COLOR_MODES_RGB_W,
    DEFAULT_MODE,
    MAX_TEMP,
    MIN_TEMP,
    MODE_COLOR,
    MODE_CUSTOM,
    MODE_MUSIC,
    MODE_PRESET,
    MODE_SWITCH,
    MODE_WW,
    MODEL_NUMS_SWITCHS,
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
from .models_db import (
    ADDRESSABLE_MODELS,
    BASE_MODE_MAP,
    CHANNEL_REMAP,
    MODEL_DESCRIPTIONS,
    MODEL_MAP,
    RGBW_PROTOCOL_MODELS,
    UNKNOWN_MODEL,
    USE_9BYTE_PROTOCOL_MODELS,
)
from .pattern import (
    ADDRESSABLE_EFFECT_ID_NAME,
    ADDRESSABLE_EFFECT_NAME_ID,
    ASSESSABLE_MULTI_COLOR_ID_NAME,
    EFFECT_CUSTOM,
    EFFECT_CUSTOM_CODE,
    EFFECT_ID_NAME,
    EFFECT_LIST,
    PresetPattern,
)
from .protocol import (
    PROTOCOL_LEDENET_8BYTE,
    PROTOCOL_LEDENET_9BYTE,
    PROTOCOL_LEDENET_ADDRESSABLE,
    PROTOCOL_LEDENET_ORIGINAL,
    ProtocolLEDENET8Byte,
    ProtocolLEDENET9Byte,
    ProtocolLEDENETAddressable,
    ProtocolLEDENETOriginal,
)
from .timer import BuiltInTimer
from .utils import utils, white_levels_to_color_temp

_LOGGER = logging.getLogger(__name__)


class DeviceType(Enum):
    Bulb = 0
    Switch = 1


class LEDENETDevice:
    """An LEDENET Device."""

    def __init__(self, ipaddr, port=5577, timeout=5):
        """Init the LEDENEt Device."""
        self.ipaddr = ipaddr
        self.port = port
        self.timeout = timeout
        self.raw_state = None
        self.available = None
        self._ignore_next_power_state_update = False

        self._protocol = None
        self._mode = None
        self._transition_complete_time = 0

    @property
    def model_num(self):
        """Return the model number."""
        return self.raw_state.model_num if self.raw_state else None

    @property
    def model(self):
        """Return the human readable model description."""
        model_num = self.model_num
        description = MODEL_DESCRIPTIONS.get(model_num) or UNKNOWN_MODEL
        return f"{description} (0x{model_num:02X})"

    @property
    def version_num(self):
        """Return the version number."""
        raw_state = self.raw_state
        return raw_state.version_number if hasattr(raw_state, "version_number") else 1

    @property
    def preset_pattern_num(self):
        """Return the preset pattern number."""
        return self.raw_state.preset_pattern

    @property
    def rgbwprotocol(self):
        """Devices that don't require a separate rgb/w bit."""
        return self.model_num in RGBW_PROTOCOL_MODELS

    @property
    def addressable(self):
        """Devices that have addressable leds."""
        return self._is_addressable(self.model_num)

    def _is_addressable(self, model_num):
        """Devices that have addressable leds."""
        return model_num in ADDRESSABLE_MODELS

    @property
    def rgbwcapable(self):
        """Devices that actually support rgbw."""
        color_modes = self.color_modes
        return COLOR_MODE_RGBW in color_modes or COLOR_MODE_RGBWW in color_modes

    @property
    def device_type(self):
        """Return the device type."""
        is_switch = self.model_num in MODEL_NUMS_SWITCHS
        return DeviceType.Switch if is_switch else DeviceType.Bulb

    @property
    def color_temp(self):
        """Return the current color temp in kelvin."""
        return (self.getWhiteTemperature())[0]

    @property
    def min_temp(self):
        """Returns the minimum color temp in kelvin."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Returns the maximum color temp in kelvin."""
        return MAX_TEMP

    @property
    def _rgbwwprotocol(self):
        """Device that uses the 9-byte protocol."""
        return self._uses_9byte_protocol(self.model_num)

    def _uses_9byte_protocol(self, model_num):
        """Devices that use a 9-byte protocol."""
        return model_num in USE_9BYTE_PROTOCOL_MODELS

    @property
    def white_active(self):
        """Any white channel is active."""
        return bool(self.raw_state.warm_white or self.raw_state.cool_white)

    @property
    def color_active(self):
        """Any color channel is active."""
        raw_state = self.raw_state
        return bool(raw_state.red or raw_state.green or raw_state.blue)

    @property
    def multi_color_mode(self):
        """The device supports multiple color modes."""
        return len(self.color_modes) > 1

    @property
    def color_modes(self):
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
    def _internal_color_modes(self):
        """The internal available color modes."""
        model_db_entry = MODEL_MAP.get(self.model_num)
        if not model_db_entry:
            # Default mode is RGB
            return BASE_MODE_MAP.get(self.raw_state.mode & 0x0F, {DEFAULT_MODE})
        return model_db_entry.mode_to_color_mode.get(
            self.raw_state.mode, model_db_entry.color_modes
        )

    @property
    def color_mode(self):
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
    def protocol(self):
        """Returns the name of the protocol in use."""
        if not self._protocol:
            return None
        return self._protocol.name

    @property
    def is_on(self):
        return self.raw_state.power_state == self._protocol.on_byte

    @property
    def mode(self):
        return self._mode

    @property
    def warm_white(self):
        return self.raw_state.warm_white if self._rgbwwprotocol else 0

    @property
    def effect_list(self):
        """Return the list of available effects."""
        if self.addressable:
            return ADDRESSABLE_EFFECT_ID_NAME.values()
        return EFFECT_LIST

    @property
    def effect(self):
        """Return the current effect."""
        pattern_code = self.preset_pattern_num
        if pattern_code == EFFECT_CUSTOM_CODE:
            return EFFECT_CUSTOM
        if not self.addressable:
            return EFFECT_ID_NAME.get(pattern_code)
        if pattern_code == 0x25:
            return ADDRESSABLE_EFFECT_ID_NAME.get(self.raw_state.mode)
        if pattern_code == 0x24:
            return ASSESSABLE_MULTI_COLOR_ID_NAME.get(self.raw_state.mode)
        return None

    @property
    def cool_white(self):
        return self.raw_state.cool_white if self._rgbwwprotocol else 0

    # Old name is deprecated
    @property
    def cold_white(self):
        return self.cool_white

    @property
    def brightness(self):
        """Return current brightness 0-255.

        For warm white return current led level. For RGB
        calculate the HSV and return the 'value'.
        for CCT calculate the brightness.
        for ww send led level
        """
        color_mode = self.color_mode
        raw_state = self.raw_state

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
            return round((v_255 + raw_state.warm_white + raw_state.cool_white) / 3)

        # Default color mode (RGB)
        return int(v_255)

    def _determineMode(self):
        pattern_code = self.raw_state.preset_pattern
        if self.device_type == DeviceType.Switch:
            return MODE_SWITCH
        if pattern_code in (0x41, 0x61):
            if self.color_mode in {COLOR_MODE_DIM, COLOR_MODE_CCT}:
                return MODE_WW
            return MODE_COLOR
        elif pattern_code == EFFECT_CUSTOM_CODE:
            return MODE_CUSTOM
        elif pattern_code == 0x62:
            return MODE_MUSIC
        elif PresetPattern.valid(pattern_code):
            return MODE_PRESET
        elif BuiltInTimer.valid(pattern_code):
            return BuiltInTimer.valtostr(pattern_code)
        elif self.addressable:
            return MODE_PRESET
        return None

    def set_unavailable(self):
        self.available = False

    def set_available(self):
        self.available = True

    def process_state_response(self, rx):
        if not self._protocol.is_valid_state_response(rx):
            _LOGGER.warning(
                "%s: Recieved invalid response: %s",
                self.ipaddr,
                utils.raw_state_to_dec(rx),
            )
            return False

        raw_state = self._protocol.named_raw_state(rx)
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

    def process_power_state_response(self, msg):
        """Process a power state change message."""
        if self._ignore_next_power_state_update:
            # These devices frequently push an incorrect power
            # state right after changing state.
            self._ignore_next_power_state_update = False
            return

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

    def _set_raw_state(self, raw_state, updated=None):
        """Set the raw state remapping channels as needed."""
        channel_map = CHANNEL_REMAP.get(raw_state.model_num)
        if not channel_map:  # Remap channels
            self.raw_state = raw_state
            return
        # Only remap updated states as we do not want to switch any
        # state that have not changed since they will already be in
        # the correct slot
        #
        # If updated is None than all raw_state values have been sent
        #
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
        _LOGGER.debug(
            "%s: remapped raw state: %s",
            self.ipaddr,
            utils.raw_state_to_dec(self.raw_state),
        )

    def __str__(self):  # noqa: C901
        rx = self.raw_state
        if not rx:
            return "No state data"
        mode = self.mode
        color_mode = self.color_mode
        pattern = rx.preset_pattern
        ww_level = rx.warm_white
        power_state = rx.power_state
        power_str = "Unknown power state"
        if power_state == self._protocol.on_byte:
            power_str = "ON "
        elif power_state == self._protocol.off_byte:
            power_str = "OFF "

        delay = rx.speed
        speed = utils.delayToSpeed(delay)
        if mode in STATIC_MODES:
            if color_mode in COLOR_MODES_RGB:
                red = rx.red
                green = rx.green
                blue = rx.blue
                mode_str = f"Color: {(red, green, blue)}"
                # Should add ability to get CCT from rgbwcapable*
                if self.rgbwcapable:
                    mode_str += f" White: {ww_level}"
                else:
                    mode_str += f" Brightness: {self.brightness}"
            elif color_mode == COLOR_MODE_DIM:
                mode_str = f"Warm White: {utils.byteToPercent(ww_level)}%"
            elif color_mode == COLOR_MODE_CCT:
                cct_value = self.getWhiteTemperature()
                mode_str = "CCT: {}K Brightness: {}%".format(
                    cct_value[0], cct_value[1] / 255
                )
            elif color_mode == COLOR_MODE_ADDRESSABLE:
                mode_str = "Addressable"
        elif mode == MODE_PRESET:
            pat = PresetPattern.valtostr(pattern)
            mode_str = f"Pattern: {pat} (Speed {speed}%)"
        elif mode == MODE_CUSTOM:
            mode_str = f"Custom pattern (Speed {speed}%)"
        elif BuiltInTimer.valid(pattern):
            mode_str = BuiltInTimer.valtostr(pattern)
        elif mode == MODE_MUSIC:
            mode_str = "Music"
        elif mode == MODE_SWITCH:
            mode_str = "Switch"
        else:
            mode_str = f"Unknown mode 0x{pattern:x}"
        mode_str += " raw state: "
        mode_str += utils.raw_state_to_dec(rx)
        return f"{power_str} [{mode_str}]"

    def _set_power_state_ignore_next_push(self, new_power_state):
        """Set the power state in the raw state, and ignore next push update."""
        self._set_power_state(new_power_state)
        self._ignore_next_power_state_update = True

    def _set_power_state(self, new_power_state):
        """Set the power state in the raw state."""
        self._replace_raw_state({"power_state": new_power_state})
        self._set_transition_complete_time()

    def _replace_raw_state(self, new_states):
        _LOGGER.debug("%s: _replace_raw_state: %s", self.ipaddr, new_states)
        self._set_raw_state(
            self.raw_state._replace(**new_states), set(new_states.keys())
        )

    def isOn(self):
        return self.is_on

    def getWarmWhite255(self):
        if self.color_mode not in {COLOR_MODE_CCT, COLOR_MODE_DIM}:
            return 255
        return self.brightness

    def getWhiteTemperature(self):
        # Assume input temperature of between 2700 and 6500 Kelvin, and scale
        # the warm and cold LEDs linearly to provide that
        raw_state = self.raw_state
        temp, brightness = white_levels_to_color_temp(
            raw_state.warm_white, raw_state.cool_white
        )
        return temp, brightness

    def getRgbw(self):
        """Returns red,green,blue,white (usually warm)."""
        if self.color_mode not in COLOR_MODES_RGB:
            return (255, 255, 255, 255)
        return self.rgbw

    @property
    def rgbw(self):
        """Returns red,green,blue,white (usually warm)."""
        return (
            self.raw_state.red,
            self.raw_state.green,
            self.raw_state.blue,
            self.raw_state.warm_white,
        )

    def getRgbww(self):
        """Returns red,green,blue,warm,cool."""
        if self.color_mode not in COLOR_MODES_RGB:
            return (255, 255, 255, 255, 255)
        return self.rgbww

    @property
    def rgbww(self):
        """Returns red,green,blue,warm,cool."""
        return (
            self.raw_state.red,
            self.raw_state.green,
            self.raw_state.blue,
            self.raw_state.warm_white,
            self.raw_state.cool_white,
        )

    def getRgbcw(self):
        """Returns red,green,blue,cool,warm."""
        if self.color_mode not in COLOR_MODES_RGB:
            return (255, 255, 255, 255, 255)
        return self.rgbcw

    @property
    def rgbcw(self):
        """Returns red,green,blue,cool,warm."""
        return (
            self.raw_state.red,
            self.raw_state.green,
            self.raw_state.blue,
            self.raw_state.cool_white,
            self.raw_state.warm_white,
        )

    def getCCT(self):
        if self.color_mode != COLOR_MODE_CCT:
            return (255, 255)
        return (self.raw_state.warm_white, self.raw_state.cool_white)

    def getSpeed(self):
        delay = self.raw_state.speed
        speed = utils.delayToSpeed(delay)
        return speed

    def _generate_levels_change(
        self,
        channels,
        persist=True,
        brightness=None,
    ):
        """Generate the levels change request."""
        channel_map = CHANNEL_REMAP.get(self.model_num)
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
            print("RGBW command sent to non-RGBW device")
            raise ValueError("RGBW command sent to non-RGBW device")

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

    def _set_transition_complete_time(self):
        """Set the time we expect the transition will be completed.

        Devices fade to a specific state so we want to avoid
        consuming state updates into self.raw_state while a transition
        is in progress as this will provide unexpected results
        and the brightness values will be wrong until
        the transition completes.
        """
        latency = STATE_CHANGE_LATENCY
        if self.addressable:
            latency = ADDRESSABLE_STATE_CHANGE_LATENCY
        transition_time = latency + utils.speedToDelay(self.raw_state.speed) / 100
        self._transition_complete_time = time.monotonic() + transition_time
        _LOGGER.debug(
            "%s: Transition time is %s, set _transition_complete_time to %s",
            self.ipaddr,
            transition_time,
            self._transition_complete_time,
        )

    def getRgb(self):
        if self.color_mode not in COLOR_MODES_RGB:
            return (255, 255, 255)
        return self.rgb

    @property
    def rgb(self):
        return (self.raw_state.red, self.raw_state.green, self.raw_state.blue)

    def _calculateBrightness(self, rgb, level):
        hsv = colorsys.rgb_to_hsv(*rgb)
        return colorsys.hsv_to_rgb(hsv[0], hsv[1], level)

    def setProtocol(self, protocol):
        if protocol == PROTOCOL_LEDENET_ORIGINAL:
            self._protocol = ProtocolLEDENETOriginal()
        elif protocol == PROTOCOL_LEDENET_8BYTE:
            self._protocol = ProtocolLEDENET8Byte()
        elif protocol == PROTOCOL_LEDENET_9BYTE:
            self._protocol = ProtocolLEDENET9Byte()
        elif protocol == PROTOCOL_LEDENET_ADDRESSABLE:
            self._protocol = ProtocolLEDENETAddressable()
        else:
            raise ValueError(f"Invalid protocol: {protocol}")

    def _set_protocol_from_msg(self, full_msg, fallback_protocol):
        if self._is_addressable(full_msg[1]):
            self._protocol = ProtocolLEDENETAddressable()
        # Devices that use an 9-byte protocol
        elif self._uses_9byte_protocol(full_msg[1]):
            self._protocol = ProtocolLEDENET9Byte()
        else:
            self._protocol = fallback_protocol

    def _generate_preset_pattern(self, pattern, speed):
        """Generate the preset pattern protocol bytes."""
        if self.addressable:
            if pattern not in ADDRESSABLE_EFFECT_ID_NAME:
                raise ValueError("Pattern must be between 1 and 300")
        else:
            PresetPattern.valtostr(pattern)
            if not PresetPattern.valid(pattern):
                raise ValueError("Pattern must be between 0x25 and 0x38")
        return self._protocol.construct_preset_pattern(pattern, speed)

    def _generate_custom_patterm(self, rgb_list, speed, transition_type):
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

        return self._protocol.construct_custom_effect(rgb_list, speed, transition_type)

    def _effect_to_pattern(self, effect):
        """Convert an effect to a pattern code."""
        if self.addressable:
            return ADDRESSABLE_EFFECT_NAME_ID[effect]
        return PresetPattern.str_to_val(effect)
