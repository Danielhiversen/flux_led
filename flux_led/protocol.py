"""FluxLED Protocols."""

from abc import abstractmethod
import colorsys
from dataclasses import dataclass
from enum import Enum
import logging
from typing import List, NamedTuple, Optional, Tuple, Union

from .const import (
    TRANSITION_GRADUAL,
    TRANSITION_JUMP,
    TRANSITION_STROBE,
    LevelWriteMode,
    MultiColorEffects,
)
from .utils import utils, white_levels_to_scaled_color_temp


class PowerRestoreState(Enum):
    ALWAYS_OFF = 0xFF
    ALWAYS_ON = 0x0F
    LAST_STATE = 0xF0


class MusicMode(Enum):
    STRIP = 0x26
    LIGHT_SCREEN = 0x27


@dataclass
class PowerRestoreStates:
    channel1: Optional[PowerRestoreState]
    channel2: Optional[PowerRestoreState]
    channel3: Optional[PowerRestoreState]
    channel4: Optional[PowerRestoreState]


_LOGGER = logging.getLogger(__name__)

# Protocol names
PROTOCOL_LEDENET_ORIGINAL = "LEDENET_ORIGINAL"
PROTOCOL_LEDENET_9BYTE = "LEDENET"
PROTOCOL_LEDENET_9BYTE_AUTO_ON = "LEDENET_AUTO_ON"
PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS = "LEDENET_DIMMABLE_EFFECTS"
PROTOCOL_LEDENET_8BYTE = "LEDENET_8BYTE"  # Previously was called None
PROTOCOL_LEDENET_8BYTE_AUTO_ON = "LEDENET_8BYTES_AUTO_ON"
PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS = "LEDENET_8BYTE_DIMMABLE_EFFECTS"
PROTOCOL_LEDENET_ADDRESSABLE_A1 = "LEDENET_ADDRESSABLE_A1"
PROTOCOL_LEDENET_ADDRESSABLE_A2 = "LEDENET_ADDRESSABLE_A2"
PROTOCOL_LEDENET_ADDRESSABLE_A3 = "LEDENET_ADDRESSABLE_A3"
PROTOCOL_LEDENET_CCT = "LEDENET_CCT"
PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS = "LEDENET_CHRISTMAS"

TRANSITION_BYTES = {
    TRANSITION_JUMP: 0x3B,
    TRANSITION_STROBE: 0x3C,
    TRANSITION_GRADUAL: 0x3A,
}


LEDNET_MUSIC_MODE_RESPONSE_LEN = 13  # 72 01 26 01 00 00 00 00 00 00 64 64 62
LEDENET_POWER_RESTORE_RESPONSE_LEN = 7
LEDENET_ORIGINAL_STATE_RESPONSE_LEN = 11
LEDENET_STATE_RESPONSE_LEN = 14
LEDENET_POWER_RESPONSE_LEN = 4
LEDENET_ADDRESSABLE_STATE_RESPONSE_LEN = 25
LEDENET_IC_STATE_RESPONSE_LEN = 11
# pos  0  1  2  3  4  5  6  7  8  9 10
#    00 63 00 3c 04 00 00 00 00 00 02
#     |  |  |  |  |  |  |  |  |  |  checksum
#     |  |  |  |  |  |  |  |  |  ??
#     |  |  |  |  |  |  |  |  ??
#     |  |  |  |  |  |  |  ??
#     |  |  |  |  |  |  ??
#     |  |  |  |  |  ???
#     |  |  |  |  ????
#     |  |  |  ic
#     |  |  num pixels (16 bit, low byte)
#     |  num pixels (16 bit, high byte)
#     msg head

MSG_ORIGINAL_POWER_STATE = "original_power_state"
MSG_ORIGINAL_STATE = "original_state"

MSG_POWER_RESTORE_STATE = "power_restore_state"
MSG_POWER_STATE = "power_state"
MSG_STATE = "state"

MSG_MUSIC_MODE_STATE = "music_mode_state"
MSG_ADDRESSABLE_STATE = "addressable_state"

MSG_IC_CONFIG = "ic_config"


OUTER_MESSAGE_FIRST_BYTE = 0xB0

MSG_UNIQUE_START = {
    (0xF0, 0x71): MSG_POWER_STATE,
    (0x0F, 0x71): MSG_POWER_STATE,
    (0x00, 0x71): MSG_POWER_STATE,
    (0xF0, 0x32): MSG_POWER_RESTORE_STATE,
    (0x0F, 0x32): MSG_POWER_RESTORE_STATE,
    (0x00, 0x32): MSG_POWER_RESTORE_STATE,
    (0x78,): MSG_ORIGINAL_POWER_STATE,
    (0x66,): MSG_ORIGINAL_STATE,
    (0x81,): MSG_STATE,
    (0x00, 0x63): MSG_IC_CONFIG,
    (0x72,): MSG_MUSIC_MODE_STATE,
}

MSG_LENGTHS = {
    MSG_MUSIC_MODE_STATE: LEDNET_MUSIC_MODE_RESPONSE_LEN,
    MSG_POWER_STATE: LEDENET_POWER_RESPONSE_LEN,
    MSG_POWER_RESTORE_STATE: LEDENET_POWER_RESTORE_RESPONSE_LEN,
    MSG_ORIGINAL_POWER_STATE: LEDENET_POWER_RESPONSE_LEN,
    MSG_ORIGINAL_STATE: LEDENET_ORIGINAL_STATE_RESPONSE_LEN,
    MSG_STATE: LEDENET_STATE_RESPONSE_LEN,
    MSG_ADDRESSABLE_STATE: LEDENET_ADDRESSABLE_STATE_RESPONSE_LEN,
    MSG_IC_CONFIG: LEDENET_IC_STATE_RESPONSE_LEN,
}

OUTER_MESSAGE_WRAPPER = [OUTER_MESSAGE_FIRST_BYTE, 0xB1, 0xB2, 0xB3, 0x00, 0x01, 0x01]
OUTER_MESSAGE_WRAPPER_START_LEN = 10
CHECKSUM_LEN = 1


POWER_RESTORE_BYTES_TO_POWER_RESTORE = {
    restore_state.value: restore_state for restore_state in PowerRestoreState
}


def _message_type_from_start_of_msg(data: bytes) -> Optional[str]:
    if len(data) > 1:
        return MSG_UNIQUE_START.get(
            (data[0], data[1]), MSG_UNIQUE_START.get((data[0],))
        )
    return MSG_UNIQUE_START.get((data[0],))


class LEDENETOriginalRawState(NamedTuple):
    head: int
    model_num: int
    power_state: int
    preset_pattern: int
    mode: int
    speed: int
    red: int
    green: int
    blue: int
    warm_white: int
    check_sum: int


# typical response:
# pos  0  1  2  3  4  5  6  7  8  9 10
#    66 01 24 39 21 0a ff 00 00 01 99
#     |  |  |  |  |  |  |  |  |  |  |
#     |  |  |  |  |  |  |  |  |  |  checksum
#     |  |  |  |  |  |  |  |  |  warmwhite
#     |  |  |  |  |  |  |  |  blue
#     |  |  |  |  |  |  |  green
#     |  |  |  |  |  |  red
#     |  |  |  |  |  speed: 0f = highest f0 is lowest
#     |  |  |  |  <don't know yet>
#     |  |  |  preset pattern
#     |  |  off(24)/on(23)
#     |  model_num (type)
#     msg head
#


class LEDENETRawState(NamedTuple):
    head: int
    model_num: int
    power_state: int
    preset_pattern: int
    mode: int
    speed: int
    red: int
    green: int
    blue: int
    warm_white: int
    version_number: int
    cool_white: int
    color_mode: int
    check_sum: int


# response from a 5-channel LEDENET controller:
# pos  0  1  2  3  4  5  6  7  8  9 10 11 12 13
#    81 25 23 61 21 06 38 05 06 f9 01 00 0f 9d
#     |  |  |  |  |  |  |  |  |  |  |  |  |  |
#     |  |  |  |  |  |  |  |  |  |  |  |  |  checksum
#     |  |  |  |  |  |  |  |  |  |  |  |  color mode (f0 colors were set, 0f whites, 00 all were set)
#     |  |  |  |  |  |  |  |  |  |  |  cool-white  0x00 to 0xFF
#     |  |  |  |  |  |  |  |  |  |  version number
#     |  |  |  |  |  |  |  |  |  warmwhite  0x00 to 0xFF
#     |  |  |  |  |  |  |  |  blue  0x00 to 0xFF
#     |  |  |  |  |  |  |  green  0x00 to 0xFF
#     |  |  |  |  |  |  red 0x00 to 0xFF
#     |  |  |  |  |  speed: 0x01 = highest 0x1f is lowest
#     |  |  |  |  Mode WW(01), WW+CW(02), RGB(03), RGBW(04), RGBWW(05)
#     |  |  |  preset pattern
#     |  |  off(24)/on(23)
#     |  model_num (type)
#     msg head
#


class ProtocolBase:
    """The base protocol."""

    power_state_response_length = MSG_LENGTHS[MSG_POWER_STATE]

    def __init__(self) -> None:
        self._counter = -1
        super().__init__()

    @property
    def requires_turn_on(self) -> bool:
        """If True the device must be turned on before setting level/patterns/modes."""
        return True

    @property
    def power_push_updates(self) -> bool:
        """If True the protocol pushes power state updates when controlled via ir/rf/app."""
        return False

    @property
    def state_push_updates(self) -> bool:
        """If True the protocol pushes state updates when controlled via ir/rf/app."""
        return False

    @property
    def zones(self) -> bool:
        """If the protocol supports zones."""
        return False

    def _increment_counter(self) -> int:
        """Increment the counter byte."""
        self._counter += 1
        if self._counter == 255:
            self._counter = 0
        return self._counter

    def is_valid_power_restore_state_response(self, msg: bytes) -> bool:
        """Check if a power state response is valid."""
        return (
            _message_type_from_start_of_msg(msg) == MSG_POWER_RESTORE_STATE
            and len(msg) == LEDENET_POWER_RESTORE_RESPONSE_LEN
            and self.is_checksum_correct(msg)
        )

    def is_valid_outer_message(self, data: bytes) -> bool:
        """Check if a message is a valid outer message."""
        if not data.startswith(bytearray(OUTER_MESSAGE_WRAPPER)):
            return False
        return self.is_checksum_correct(data)

    def extract_inner_message(self, msg: bytes) -> bytes:
        """Extract the inner message from a wrapped message."""
        return msg[10:-1]

    def is_valid_ic_response(self, data: bytes) -> bool:
        """Check if a message is a valid ic state response."""
        return False

    def expected_response_length(self, data: bytes) -> int:
        """Return the number of bytes expected in the response.

        If the response is unknown, we assume the response is
        a complete message since we have no way of knowing otherwise.
        """
        if data[0] == OUTER_MESSAGE_FIRST_BYTE:  # This is a wrapper message
            if len(data) < OUTER_MESSAGE_WRAPPER_START_LEN:
                return OUTER_MESSAGE_WRAPPER_START_LEN
            inner_msg_len = (data[8] << 8) + data[9]
            return (
                OUTER_MESSAGE_WRAPPER_START_LEN  # Includes the two bytes that are the size of the inner message
                + inner_msg_len  # The inner message itself (with checksum)
                + CHECKSUM_LEN  # The checksum of the full message
            )

        msg_type = _message_type_from_start_of_msg(data)
        if msg_type is None:
            return len(data)
        return MSG_LENGTHS[msg_type]

    @abstractmethod
    def construct_state_query(self) -> bytearray:
        """The bytes to send for a query request."""

    @abstractmethod
    def is_valid_state_response(self, raw_state: bytes) -> bool:
        """Check if a state response is valid."""

    def is_checksum_correct(self, msg: bytes) -> bool:
        """Check a checksum of a message."""
        expected_sum = sum(msg[0:-1]) & 0xFF
        if expected_sum != msg[-1]:
            _LOGGER.warning(
                "Checksum mismatch: Expected %s, got %s", expected_sum, msg[-1]
            )
            return False
        return True

    @abstractmethod
    def is_valid_power_state_response(self, msg: bytes) -> bool:
        """Check if a power state response is valid."""

    @property
    def on_byte(self) -> int:
        """The on byte."""
        return 0x23

    @property
    def off_byte(self) -> int:
        """The off byte."""
        return 0x24

    @property
    def dimmable_effects(self) -> bool:
        """Protocol supports dimmable effects."""
        return False

    @abstractmethod
    def construct_state_change(self, turn_on: int) -> bytearray:
        """The bytes to send for a state change request."""

    def construct_power_restore_state_query(self) -> bytearray:
        """The bytes to send for a query power restore state."""
        return self.construct_message(bytearray([0x32, 0x3A, 0x3B, 0x0F]))

    def construct_power_restore_state_change(
        self, restore_state: PowerRestoreStates
    ) -> bytearray:
        """The bytes to send for a power restore state change.

        Set power on state to keep last state
        31f0f0f0f0f0e1
        Set power on state to always on
        310ff0f0f0f000
        Set power on state to always off
        31fff0f0f0f0f0
        """
        return self.construct_message(
            bytearray(
                [
                    0x31,
                    restore_state.channel1.value if restore_state.channel1 else 0x00,
                    restore_state.channel2.value if restore_state.channel2 else 0x00,
                    restore_state.channel3.value if restore_state.channel3 else 0x00,
                    restore_state.channel4.value if restore_state.channel4 else 0x00,
                    0xF0,
                ]
            )
        )

    @abstractmethod
    def construct_music_mode(
        self,
        sensitivity: int,
        brightness: int,
        mode: Optional[int],
        effect: Optional[int],
        foreground_color: Optional[Tuple[int, int, int]] = None,
        background_color: Optional[Tuple[int, int, int]] = None,
    ) -> List[bytearray]:
        """The bytes to send to set music mode."""

    @abstractmethod
    def construct_levels_change(
        self,
        persist: int,
        red: int,
        green: int,
        blue: int,
        warm_white: int,
        cool_white: int,
        write_mode: LevelWriteMode,
    ) -> bytearray:
        """The bytes to send for a level change request."""

    def construct_preset_pattern(
        self, pattern: int, speed: int, brightness: int
    ) -> bytearray:
        """The bytes to send for a preset pattern."""
        delay = utils.speedToDelay(speed)
        return self.construct_message(bytearray([0x61, pattern, delay, 0x0F]))

    def construct_custom_effect(
        self, rgb_list: List[Tuple[int, int, int]], speed: int, transition_type: str
    ) -> bytearray:
        """The bytes to send for a custom effect."""
        msg = bytearray()
        first_color = True
        for rgb in rgb_list:
            if first_color:
                lead_byte = 0x51
                first_color = False
            else:
                lead_byte = 0
            r, g, b = rgb
            msg.extend(bytearray([lead_byte, r, g, b]))
        # pad out empty slots
        if len(rgb_list) != 16:
            for i in range(16 - len(rgb_list)):
                msg.extend(bytearray([0, 1, 2, 3]))
        msg.append(0x00)
        msg.append(utils.speedToDelay(speed))
        msg.append(
            TRANSITION_BYTES.get(transition_type, TRANSITION_BYTES[TRANSITION_GRADUAL])
        )  # default to "gradual"
        msg.append(0xFF)
        msg.append(0x0F)
        return self.construct_message(msg)

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the protocol."""

    @property
    @abstractmethod
    def state_response_length(self) -> int:
        """The length of the query response."""

    @abstractmethod
    def construct_message(self, raw_bytes: bytearray) -> bytearray:
        """Original protocol uses no checksum."""

    def construct_wrapped_message(
        self, msg: bytearray, inner_pre_constructed: bool = False
    ) -> bytearray:
        """Construct a wrapped message."""
        if inner_pre_constructed:  # msg has already been inner_pre_constructed
            inner_msg = msg
        else:
            inner_msg = self.construct_message(msg)
        inner_msg_len = len(inner_msg)
        return self.construct_message(
            bytearray(
                [
                    *OUTER_MESSAGE_WRAPPER,
                    self._increment_counter(),
                    inner_msg_len >> 8,
                    inner_msg_len & 0xFF,
                    *inner_msg,
                ]
            )
        )

    @abstractmethod
    def named_raw_state(
        self, raw_state: bytes
    ) -> Union[LEDENETOriginalRawState, LEDENETRawState]:
        """Convert raw_state to a namedtuple."""


class ProtocolLEDENETOriginal(ProtocolBase):
    """The original LEDENET protocol with no checksums."""

    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ORIGINAL

    @property
    def state_response_length(self) -> int:
        """The length of the query response."""
        return LEDENET_ORIGINAL_STATE_RESPONSE_LEN

    def is_valid_power_state_response(self, msg: bytes) -> bool:
        """Check if a power state response is valid."""
        return len(msg) == self.power_state_response_length and msg[0] == 0x78

    def is_valid_state_response(self, raw_state: bytes) -> bool:
        """Check if a state response is valid."""
        return (
            len(raw_state) == self.state_response_length
            and raw_state[0] == 0x66
            and raw_state[1] == 0x01
        )

    def construct_state_query(self) -> bytearray:
        """The bytes to send for a query request."""
        return self.construct_message(bytearray([0xEF, 0x01, 0x77]))

    def construct_state_change(self, turn_on: int) -> bytearray:
        """The bytes to send for a state change request."""
        return self.construct_message(
            bytearray([0xCC, self.on_byte if turn_on else self.off_byte, 0x33])
        )

    def construct_levels_change(
        self,
        persist: int,
        red: int,
        green: int,
        blue: int,
        warm_white: int,
        cool_white: int,
        write_mode: LevelWriteMode,
    ) -> bytearray:
        """The bytes to send for a level change request."""
        # sample message for original LEDENET protocol (w/o checksum at end)
        #  0  1  2  3  4
        # 56 90 fa 77 aa
        #  |  |  |  |  |
        #  |  |  |  |  terminator
        #  |  |  |  blue
        #  |  |  green
        #  |  red
        #  head
        return self.construct_message(bytearray([0x56, red, green, blue, 0xAA]))

    def construct_message(self, raw_bytes: bytearray) -> bytearray:
        """Original protocol uses no checksum."""
        return raw_bytes

    def named_raw_state(self, raw_state: bytes) -> LEDENETOriginalRawState:
        """Convert raw_state to a namedtuple."""
        return LEDENETOriginalRawState(*raw_state)


class ProtocolLEDENET8Byte(ProtocolBase):
    """The newer LEDENET protocol with checksums that uses 8 bytes to set state."""

    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_8BYTE

    @property
    def state_response_length(self) -> int:
        """The length of the query response."""
        return LEDENET_STATE_RESPONSE_LEN

    def is_valid_power_state_response(self, msg: bytes) -> bool:
        """Check if a power state response is valid."""
        if (
            len(msg) != self.power_state_response_length
            or not self._is_start_of_power_state_response(msg)
            or msg[1] != 0x71
            or msg[2] not in (self.on_byte, self.off_byte)
        ):
            return False
        return self.is_checksum_correct(msg)

    def _is_start_of_power_state_response(self, data: bytes) -> bool:
        """Check if a message is the start of a state response."""
        return _message_type_from_start_of_msg(data) == MSG_POWER_STATE

    def is_valid_state_response(self, raw_state: bytes) -> bool:
        """Check if a state response is valid."""
        if len(raw_state) != self.state_response_length:
            return False
        if not raw_state[0] == 0x81:
            return False
        return self.is_checksum_correct(raw_state)

    def construct_state_change(self, turn_on: int) -> bytearray:
        """The bytes to send for a state change request.

        Alternate messages

        Off 3b 24 00 00 00 00 00 00 00 32 00 00 91
        On  3b 23 00 00 00 00 00 00 00 32 00 00 90
        """
        return self.construct_message(
            bytearray([0x71, self.on_byte if turn_on else self.off_byte, 0x0F])
        )

    def construct_levels_change(
        self,
        persist: int,
        red: int,
        green: int,
        blue: int,
        warm_white: int,
        cool_white: int,
        write_mode: LevelWriteMode,
    ) -> bytearray:
        """The bytes to send for a level change request."""
        # sample message for 8-byte protocols (w/ checksum at end)
        #  0  1  2  3  4  5  6
        # 31 90 fa 77 00 00 0f
        #  |  |  |  |  |  |  |
        #  |  |  |  |  |  |  terminator
        #  |  |  |  |  |  write mask / white2 (see below)
        #  |  |  |  |  white
        #  |  |  |  blue
        #  |  |  green
        #  |  red
        #  persistence (31 for true / 41 for false)
        #
        # byte 5 can have different values depending on the type
        # of device:
        # For devices that support 2 types of white value (warm and cold
        # white) this value is the cold white value. These use the LEDENET
        # protocol. If a second value is not given, reuse the first white value.
        #
        # For devices that cannot set both rbg and white values at the same time
        # (including devices that only support white) this value
        # specifies if this command is to set white value (0f) or the rgb
        # value (f0).
        #
        # For all other rgb and rgbw devices, the value is 00
        return self.construct_message(
            bytearray(
                [
                    0x31 if persist else 0x41,
                    red,
                    green,
                    blue,
                    warm_white,
                    write_mode.value,
                    0x0F,
                ]
            )
        )

    def construct_message(self, raw_bytes: bytearray) -> bytearray:
        """Calculate checksum of byte array and add to end."""
        csum = sum(raw_bytes) & 0xFF
        raw_bytes.append(csum)
        return raw_bytes

    def construct_state_query(self) -> bytearray:
        """The bytes to send for a query request."""
        return self.construct_message(bytearray([0x81, 0x8A, 0x8B]))

    def named_raw_state(self, raw_state: bytes) -> LEDENETRawState:
        """Convert raw_state to a namedtuple."""
        return LEDENETRawState(*raw_state)

    def construct_music_mode(
        self,
        sensitivity: int,
        brightness: int,
        mode: Optional[int],
        effect: Optional[int],
        foreground_color: Optional[Tuple[int, int, int]] = None,
        background_color: Optional[Tuple[int, int, int]] = None,
    ) -> List[bytearray]:
        """The bytes to send for music mode.

        Known messages
        73 01 4d 0f d0
              ^^
              Likely sensitivity from 0-100 (0x64)
        73 01 64 0f e7
        73 01 4a 0f cd
        73 01 4b 0f ce
        73 01 00 0f 83
        73 01 1b 0f 9e
        73 01 05 0f 88
        73 01 02 0f 85
        73 01 06 0f 89
        73 01 05 0f 88
        73 01 10 0f 93
        73 01 4d 0f d0
        73 01 64 0f e7

        Pause music mode
        73 00 59 0f db
           ^^
           On/off byte

        Mic
        37 00 00 37  Fade In
           ^^
           Mic effect
        37 01 00 38  Gradual
        37 02 00 39  Jump
        37 03 00 3a  Strobe
        """
        # Valid modes for old protocol
        # 0x01 - Gradual
        return [self.construct_message(bytearray([0x73, 0x01, sensitivity, 0x0F]))]


class ProtocolLEDENET8ByteAutoOn(ProtocolLEDENET8Byte):
    """Protocol that uses 8 bytes, and turns on by changing levels or effects."""

    @property
    def requires_turn_on(self) -> bool:
        """If True the device must be turned on before setting level/patterns/modes."""
        return False

    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_8BYTE_AUTO_ON


# This protocol also supports Candle mode but its not currently implemented here
class ProtocolLEDENET8ByteDimmableEffects(ProtocolLEDENET8ByteAutoOn):
    """Protocol that uses 8 bytes, and supports dimmable effects and auto on by changing levels or effects."""

    @property
    def dimmable_effects(self) -> bool:
        """Protocol supports dimmable effects."""
        return True

    @property
    def power_push_updates(self) -> bool:
        """If True the protocol pushes power state updates when controlled via ir/rf/app."""
        return True

    @property
    def state_push_updates(self) -> bool:
        """If True the protocol pushes state updates when controlled via ir/rf/app."""
        return True

    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS

    def construct_preset_pattern(
        self, pattern: int, speed: int, brightness: int
    ) -> bytearray:
        """The bytes to send for a preset pattern."""
        delay = utils.speedToDelay(speed)
        return self.construct_message(bytearray([0x38, pattern, delay, brightness]))

    def construct_music_mode(
        self,
        sensitivity: int,
        brightness: int,
        mode: Optional[int],
        effect: Optional[int],
        foreground_color: Optional[Tuple[int, int, int]] = None,
        background_color: Optional[Tuple[int, int, int]] = None,
    ) -> List[bytearray]:
        """The bytes to send for music mode.

        Known messages
        73 01 4d 0f d0
              ^^
              Likely sensitivity from 0-100 (0x64)
        73 01 64 0f e7
        73 01 4a 0f cd
        73 01 4b 0f ce
        73 01 00 0f 83
        73 01 1b 0f 9e
        73 01 05 0f 88
        73 01 02 0f 85
        73 01 06 0f 89
        73 01 05 0f 88
        73 01 10 0f 93
        73 01 4d 0f d0
        73 01 64 0f e7

        Pause music mode
        73 00 59 0f db
           ^^
           On/off byte

        Mic
        37 00 00 37  Fade In
           ^^
           Mic effect
        37 01 00 38  Gradual
        37 02 00 39  Jump
        37 03 00 3a  Strobe
        """
        # Valid modes
        # 0x00 - Fade In
        # 0x01 - Gradual
        # 0x02 - Jump
        # 0x03 - Strobe
        if mode and not (0x00 <= mode <= 0x03):
            raise ValueError(
                "Mode must be one of (0x00 - Fade In, 0x01 - Gradual, 0x02 - Jump, 0x03 - Strobe)"
            )
        return [
            self.construct_message(bytearray([0x73, 0x01, sensitivity, 0x0F])),
            self.construct_message(bytearray([0x37, mode or 0x00, 0x00])),
        ]


class ProtocolLEDENET9Byte(ProtocolLEDENET8Byte):
    """The newer LEDENET protocol with checksums that uses 9 bytes to set state."""

    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_9BYTE

    def construct_levels_change(
        self,
        persist: int,
        red: int,
        green: int,
        blue: int,
        warm_white: int,
        cool_white: int,
        write_mode: LevelWriteMode,
    ) -> bytearray:
        """The bytes to send for a level change request."""
        # sample message for 9-byte LEDENET protocol (w/ checksum at end)
        #  0  1  2  3  4  5  6  7
        # 31 bc c1 ff 00 00 f0 0f
        #  |  |  |  |  |  |  |  |
        #  |  |  |  |  |  |  |  terminator
        #  |  |  |  |  |  |  write mode (f0 colors, 0f whites, 00 colors & whites)
        #  |  |  |  |  |  cold white
        #  |  |  |  |  warm white
        #  |  |  |  blue
        #  |  |  green
        #  |  red
        #  persistence (31 for true / 41 for false)
        #
        return self.construct_message(
            bytearray(
                [
                    0x31 if persist else 0x41,
                    red,
                    green,
                    blue,
                    warm_white,
                    cool_white,
                    write_mode.value,
                    0x0F,
                ]
            )
        )


class ProtocolLEDENET9ByteAutoOn(ProtocolLEDENET9Byte):
    """Protocol that uses 9 bytes, and turns on by changing levels or effects."""

    @property
    def requires_turn_on(self) -> bool:
        """If True the device must be turned on before setting level/patterns/modes."""
        return False

    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_9BYTE_AUTO_ON


# This protocol also supports Candle mode but its not currently implemented here
class ProtocolLEDENET9ByteDimmableEffects(ProtocolLEDENET9ByteAutoOn):
    """The newer LEDENET protocol with checksums that uses 9 bytes to set state."""

    @property
    def dimmable_effects(self) -> bool:
        """Protocol supports dimmable effects."""
        return True

    @property
    def power_push_updates(self) -> bool:
        """If True the protocol pushes power state updates when controlled via ir/rf/app."""
        return True

    @property
    def state_push_updates(self) -> bool:
        """If True the protocol pushes state updates when controlled via ir/rf/app."""
        return True

    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS

    def construct_preset_pattern(
        self, pattern: int, speed: int, brightness: int
    ) -> bytearray:
        """The bytes to send for a preset pattern."""
        delay = utils.speedToDelay(speed)
        return self.construct_message(bytearray([0x38, pattern, delay, brightness]))


class ProtocolLEDENETAddressableBase(ProtocolLEDENET9Byte):
    def construct_request_strip_setting(self) -> bytearray:
        return self.construct_message(bytearray([0x63, 0x12, 0x21]))


class ProtocolLEDENETAddressableA1(ProtocolLEDENETAddressableBase):
    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ADDRESSABLE_A1

    @property
    def power_push_updates(self) -> bool:
        """If True the protocol pushes power state updates when controlled via ir/rf/app."""
        return True

    @property
    def dimmable_effects(self) -> bool:
        """Protocol supports dimmable effects."""
        return False

    @property
    def requires_turn_on(self) -> bool:
        """If True the device must be turned on before setting level/patterns/modes."""
        return False

    def construct_preset_pattern(
        self, pattern: int, speed: int, brightness: int
    ) -> bytearray:
        """The bytes to send for a preset pattern."""
        effect = pattern + 99
        return self.construct_message(
            bytearray([0x61, effect >> 8, effect & 0xFF, speed, 0x0F])
        )


class ProtocolLEDENETAddressableA2(ProtocolLEDENETAddressableBase):

    # ic response
    # 0x96 0x63 0x00 0x32 0x00 0x01 0x01 0x04 0x32 0x01 0x64 (11)

    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ADDRESSABLE_A2

    @property
    def power_push_updates(self) -> bool:
        """If True the protocol pushes power state updates when controlled via ir/rf/app."""
        # This is likely due to buggy firmware
        return False

    @property
    def dimmable_effects(self) -> bool:
        """Protocol supports dimmable effects."""
        return True

    @property
    def requires_turn_on(self) -> bool:
        """If True the device must be turned on before setting level/patterns/modes."""
        return False

    def construct_preset_pattern(
        self, pattern: int, speed: int, brightness: int
    ) -> bytearray:
        """The bytes to send for a preset pattern."""
        return self.construct_message(bytearray([0x42, pattern, speed, brightness]))

    def construct_levels_change(
        self,
        persist: int,
        red: int,
        green: int,
        blue: int,
        warm_white: int,
        cool_white: int,
        write_mode: LevelWriteMode,
    ) -> bytearray:
        """The bytes to send for a level change request.

        white  41 01 ff ff ff 00 00 00 60 ff 00 00 9e
        """
        preset_number = 0x01  # aka fixed color
        return self.construct_message(
            bytearray(
                [
                    0x41,
                    preset_number,
                    red,
                    green,
                    blue,
                    0x00,
                    0x00,
                    0x00,
                    0x60,
                    0xFF,
                    0x00,
                    0x00,
                ]
            )
        )

    def construct_music_mode(
        self,
        sensitivity: int,
        brightness: int,
        mode: Optional[int],
        effect: Optional[int],
        foreground_color: Optional[Tuple[int, int, int]] = None,
        background_color: Optional[Tuple[int, int, int]] = None,
    ) -> List[bytearray]:
        """The bytes to send for music mode.

        Known messages
        73 01 27 01 00 00 00 00 ff ff 64 64 62 - lowest brightness music
        73 01 27 01 ff ff ff 00 ff ff 64 64 5f - highest brightness music
                    ^R ^G ^B <-- failling color
        73 01 27 01 ff 00 00 00 ff ff 64 64 61
                    ^R ^G ^B <-- failling color


        73 01 27 01 ff ff ff 00 ff ff 00 64 fb - lowest sensitivity
        73 01 27 01 ff ff ff 00 ff ff 64 64 5f - highest sensitivity
                                      ^ sensitivity


        73 01 27 13 00 ff 19 ff 00 00 64 64 8d
                    ^R ^G ^B <-- failling color (light screen mode)
        73 01 27 13 00 ff 19 ff 00 00 64 64 8d
                             ^R ^G ^B <-- column color (light screen mode)

        73 01 27 14 00 ff 19 ff 00 00 64 64 8e
                 ^ effect
        73 01 27 15 00 ff 19 ff 00 00 64 64 8f
                 ^ effect

        73 01 27 15 00 ff 19 ff 00 00 64 64 8f
              ^ mode - light screen mode
        73 01 26 01 00 00 00 00 ff ff 64 64 61
              ^ mode - led strip mode

        73 01 26 0e 00 00 00 ff 00 00 64 64 6f
                             ^R ^G ^B <-- led strip mode color

        73 01 26 0e 00 00 00 ff 00 00 64 06 11
                                         ^brightness <-- led strip mode color

        """
        if foreground_color is None:
            foreground_color = (0xFF, 0x00, 0x00)
        if background_color is None:
            background_color = (0x00, 0x00, 0x00)
        if effect and not (1 <= effect <= 16):
            raise ValueError("Effect must be between 1 and 16")
        if mode and not (0x26 <= mode <= 0x27):
            raise ValueError("Mode must be between 0x26 and 0x27")

        return [
            self.construct_message(
                bytearray(
                    [
                        0x73,
                        0x01,
                        mode
                        or MusicMode.STRIP.value,  # strip mode 0x26, light screen mode 0x27
                        effect or 0x01,
                        *foreground_color,
                        *background_color,
                        sensitivity,
                        brightness,
                    ]
                )
            )
        ]


class ProtocolLEDENETAddressableA3(ProtocolLEDENETAddressableA2):

    # ic response
    # 0x00 0x63 0x00 0x32 0x00 0x01 0x04 0x03 0x32 0x01 0xD0 (11)
    # b0 b1 b2 b3 00 01 01 37 00 0b 00 63 00 32 00 01 04 03 32 01 d0 aa
    @property
    def power_push_updates(self) -> bool:
        """If True the protocol pushes power state updates when controlled via ir/rf/app."""
        return True

    @property
    def zones(self) -> bool:
        """If the protocol supports zones."""
        return True

    def is_valid_ic_response(self, data: bytes) -> bool:
        """Check if a message is a valid ic state response."""
        if len(data) != LEDENET_IC_STATE_RESPONSE_LEN:
            return False
        if not data.startswith(bytearray([0x00, 0x63])):
            return False
        return self.is_checksum_correct(data)

    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ADDRESSABLE_A3

    @property
    def dimmable_effects(self) -> bool:
        """Protocol supports dimmable effects."""
        return True

    @property
    def requires_turn_on(self) -> bool:
        """If True the device must be turned on before setting level/patterns/modes."""
        return False

    def construct_preset_pattern(
        self, pattern: int, speed: int, brightness: int
    ) -> bytearray:
        """The bytes to send for a preset pattern."""
        return self.construct_wrapped_message(
            super().construct_preset_pattern(pattern, speed, brightness),
            inner_pre_constructed=True,
        )

    # To query music mode
    # Send     -> b0 b1 b2 b3 00 01 01 1c 00 03 72 00 72 cb
    # Responds <- b0 b1 b2 b3 00 01 01 1c 00 0d 72 01 26 01 00 00 00 00 00 00 64 64 62 b5

    def construct_music_mode(
        self,
        sensitivity: int,
        brightness: int,
        mode: Optional[int],
        effect: Optional[int],
        foreground_color: Optional[Tuple[int, int, int]] = None,
        background_color: Optional[Tuple[int, int, int]] = None,
    ) -> List[bytearray]:
        """The bytes to send for music mode.

        Known messages
        b0 b1 b2 b3 00 01 01 1f 00 0d 73 01 27 01 ff 00 00 ff 00 00 64 64 62 b8 - Music mode
        b0 b1 b2 b3 00 01 01 20 00 0d 73 01 27 01 00 ff 44 ff 00 00 64 64 a6 41 - Music mode
        b0 b1 b2 b3 00 01 01 21 00 0d 73 01 27 01 ff a6 00 ff 00 00 64 64 08 06 - Music mode
        b0 b1 b2 b3 00 01 01 22 00 0d 73 01 27 01 ff a6 00 ff 00 00 2e 64 d2 9b - Music mode

        b0 b1 b2 b3 00 01 01 2d 00 0d 73 01 27 01 ff a6 00 ff 00 00 4e 64 f2 e6 - Music mode (various sensitivity)
        b0 b1 b2 b3 00 01 01 2e 00 0d 73 01 27 01 ff a6 00 ff 00 00 5f 64 03 09 - Music mode (various sensitivity)
        b0 b1 b2 b3 00 01 01 2f 00 0d 73 01 27 01 ff a6 00 ff 00 00 64 64 08 14 - Music mode (various sensitivity)
        b0 b1 b2 b3 00 01 01 30 00 0d 73 01 27 01 ff a6 00 ff 00 00 37 64 db bb - Music mode (various sensitivity)
                                                                    ^^
                                                                    Likely sensitivity from 0-100 (0x64)
        b0 b1 b2 b3 00 01 01 60 00 0d 73 01 27 01 ff a6 00 ff 00 00 64 64 08 45 - Music mode (various sensitivity)
        b0 b1 b2 b3 00 01 01 5f 00 0d 73 01 27 01 ff a6 00 ff 00 00 64 64 08 44 - Music mode (various sensitivity)
        b0 b1 b2 b3 00 01 01 69 00 0d 73 01 26 01 ff 00 00 ff 00 00 00 64 fd 38 - Music mode (various sensitivity)
        b0 b1 b2 b3 00 01 01 68 00 0d 73 01 26 01 ff 00 00 ff 00 00 64 64 61 ff - Music mode (various sensitivity)


        b0 b1 b2 b3 00 01 01 08 00 0d 73 01 26 02 00 00 00 00 ff ff 64 60 5e 99 -- red lines
        b0 b1 b2 b3 00 01 01 16 00 0d 73 01 26 02 00 00 00 00 ff ff 64 64 62 af -- red lines
        b0 b1 b2 b3 00 01 01 17 00 0d 73 01 26 01 00 00 00 00 ff ff 64 64 61 ae -- rainbow lines
                                                                       ^^
                                                                       Likely brightness from 0-100 (0x64)
        """
        return [
            self.construct_wrapped_message(msg, inner_pre_constructed=True)
            for msg in super().construct_music_mode(
                sensitivity,
                brightness,
                mode,
                effect,
                foreground_color,
                background_color,
            )
        ]

    def construct_levels_change(
        self,
        persist: int,
        red: int,
        green: int,
        blue: int,
        warm_white: int,
        cool_white: int,
        write_mode: LevelWriteMode,
    ) -> bytearray:
        """The bytes to send for a level change request.

        b0 [unknown static?] b1 [unknown static?] b2 [unknown static?] b3 [unknown static?] 00 [unknown static?] 01 [unknown static?] 01 [unknown static?] 6a [incrementing sequence number] 00 [unknown static?] 0d [unknown, sometimes 0c] 41 [unknown static?] 02 [preset number] ff [foreground r] 00 [foreground g] 00 [foreground b] 00 [background red] ff [background green] 00 [background blue] 06 [speed or direction?] 00 [unknown static?] 00 [unknown static?] 00 [unknown static?] 47 [speed or direction?] cd [check sum]

        Known messages


        b0 b1 b2 b3 00 01 01 01 00 0c 10 14 15 0a 0b 0e 12 06 01 00 0f 84 dd - preset 1
        b0 b1 b2 b3 00 01 01 03 00 0d 41 02 00 ff ff 00 00 00 06 00 00 00 47 66 - preset 2
        b0 b1 b2 b3 00 01 01 04 00 0d 41 03 00 ff ff 00 00 00 06 00 00 00 48 69 - preset 3
        b0 b1 b2 b3 00 01 01 02 00 0d 41 01 00 ff ff 00 00 00 06 ff 00 00 45 61 - preset 4
        b0 b1 b2 b3 00 01 01 1f 00 0d 41 01 ff 00 00 00 00 00 06 ff 00 00 46 80 - preset 1 red or green
        b0 b1 b2 b3 00 01 01 27 00 0d 41 01 00 ff 00 00 00 00 06 ff 00 00 46 88 - preset 1 red or green
        b0 b1 b2 b3 00 01 01 2e 00 0d 41 01 ff 00 00 00 00 00 06 ff 00 00 46 8f - preset 1 red (foreground)
        b0 b1 b2 b3 00 01 01 27 00 0d 41 01 00 ff 00 00 00 00 06 ff 00 00 46 88 - preset 1 green (foreground)
        b0 b1 b2 b3 00 01 01 3e 00 0d 41 01 00 00 ff 00 00 00 06 ff 00 00 46 9f - preset 1 blue (foreground)
        b0 b1 b2 b3 00 01 01 54 00 0d 41 02 00 ff 00 00 00 00 06 00 00 00 48 b9 - preset 2 green (foreground)
        b0 b1 b2 b3 00 01 01 55 00 0d 41 02 ff 00 00 00 00 00 06 00 00 00 48 ba - preset 2 red (foreground)
        b0 b1 b2 b3 00 01 01 67 00 0d 41 02 ff 00 00 ff 00 00 06 00 00 00 47 ca - preset 2 red (foreground), red (background)
        b0 b1 b2 b3 00 01 01 67 00 0d 41 02 ff 00 00 ff 00 00 06 00 00 00 47 ca - preset 2 red (foreground), red (background)
        b0 b1 b2 b3 00 01 01 69 00 0d 41 02 ff 00 00 ff 00 00 06 00 00 00 47 cc - preset 2 red (foreground), red (background)
        b0 b1 b2 b3 00 01 01 6a 00 0d 41 02 ff 00 00 00 ff 00 06 00 00 00 47 cd - preset 2 red (foreground), green (background)
        b0 b1 b2 b3 00 01 01 77 00 0d 41 02 ff 00 00 00 ff 00 06 00 00 00 47 da - preset 2 red (foreground), green (background) - direction RTL
        b0 b1 b2 b3 00 01 01 7d 00 0d 41 02 ff 00 00 00 ff 00 06 00 00 00 47 e0 - preset 2 red (foreground), green (background) - direction RTL
        b0 b1 b2 b3 00 01 01 7d 00 0d 41 02 ff 00 00 00 ff 00 06 00 00 00 47 e0 - preset 2 red (foreground), green (background) - direction RTL
        b0 b1 b2 b3 00 01 01 7c 00 0d 41 02 ff 00 00 00 ff 00 06 01 00 00 48 e1 - preset 2 red (foreground), green (background) - direction LTR
        b0 b1 b2 b3 00 01 01 89 00 0d 41 02 ff 00 00 00 ff 00 00 00 00 00 41 e0 - preset 2 red (foreground), green (background) - direction LTR - speed 0
        b0 b1 b2 b3 00 01 01 8a 00 0d 41 02 ff 00 00 00 ff 00 64 00 00 00 a5 a9 - preset 2 red (foreground), green (background) - direction LTR - speed 64
        b0 b1 b2 b3 00 01 01 8b 00 0d 41 02 ff 00 00 00 ff 00 00 00 00 00 41 e2 - preset 2 red (foreground), green (background) - direction LTR - speed 0?
        b0 b1 b2 b3 00 01 01 8c 00 0d 41 02 ff 00 00 00 ff 00 64 00 00 00 a5 ab - preset 2 red (foreground), green (background) - direction LTR - speed 64?

        Set Blue
        b0b1b2b30001010b0034a0000600010000ff0000ff0002ffff000000ff00030000ff0000ff0004ffff000000ff00050000ff0000ff0006ffff000000ffac5f

        Query
        b0b1b2b30001010c0004818a8b9604
        b0b1b2b30001010c000e811a23280000640f000001000660a2

        Set Red
        b0b1b2b30001010d0034a0000600010000ff0000ff0002ff00000000ff00030000ff0000ff0004ff00000000ff00050000ff0000ff0006ff00000000ffaf67
        """
        return self.construct_wrapped_message(
            super().construct_levels_change(
                persist, red, green, blue, warm_white, cool_white, write_mode
            ),
            inner_pre_constructed=True,
        )

    def construct_zone_change(
        self,
        points: int,  # the number of points on the strip
        rgb_list: List[Tuple[int, int, int]],
        speed: int,
        effect: MultiColorEffects,
    ) -> bytearray:
        """The bytes to send for multiple zones.

        Blue/Green - Static
        590063ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff00000000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff001e04640024

        Red/Blue - Jump
        5900630000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff00ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff00001e01640021

        White/Green - Static
        590063ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff00ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff00001e01640003
            11111 22222 33333 44444 55555 66666 77777 88888 99999 00000 11111 22222 33333 44444 55555

        White - Static
        590063ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff001e016400e5

        White - Running Water - Full speed
        590063ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff001e026400e6

        White - Running Water - 50% speed
        590063ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff001e023200b4

        Red - Blue - Gradient
        590063ff0000f60008ed0011e4001adb0023d3002bca0034c1003db80046af004fa700579e00609500698c007283007b7b008372008c69009560009e5700a74f00af4600b83d00c13400ca2b00d32300db1a00e41100ed0800f60000ff001e01640005

        Red - Brething
        590063ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000ff0000001e05640025
        """
        sent_zones = len(rgb_list)
        if sent_zones > points:
            raise ValueError(f"Device supports a maximum of {points} zones")
        pixel_bits = 9 + (points * 3)
        pixels = bytearray([pixel_bits >> 8, pixel_bits & 0xFF])
        msg = bytearray([0x59])
        msg.extend(pixels)
        zone_size = points // sent_zones
        remaining = points
        for rgb in rgb_list:
            for _ in range(zone_size):
                remaining -= 1
                msg.extend(bytearray([*rgb]))
        while remaining:
            remaining -= 1
            msg.extend(bytearray([*rgb]))
        msg.extend(bytearray([0x00, 0x1E]))
        msg.extend(bytearray([effect.value, speed]))
        msg.append(0x00)
        return self.construct_wrapped_message(msg)


class ProtocolLEDENETCCT(ProtocolLEDENET9Byte):

    MIN_BRIGHTNESS = 2

    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_CCT

    @property
    def dimmable_effects(self) -> bool:
        """Protocol supports dimmable effects."""
        return False

    @property
    def power_push_updates(self) -> bool:
        """If True the protocol pushes power state updates when controlled via ir/rf/app."""
        return True

    @property
    def state_push_updates(self) -> bool:
        """If True the protocol pushes state updates when controlled via ir/rf/app."""
        return True

    @property
    def requires_turn_on(self) -> bool:
        """If True the device must be turned on before setting level/patterns/modes."""
        return False

    def construct_levels_change(
        self,
        persist: int,
        red: int,
        green: int,
        blue: int,
        warm_white: int,
        cool_white: int,
        write_mode: LevelWriteMode,
    ) -> bytearray:
        """The bytes to send for a level change request.

        b0 b1 b2 b3 00 01 01 52 00 09 35 b1 00 64 00 00 00 03 4d bd - 100% warm
        b0 b1 b2 b3 00 01 01 72 00 09 35 b1 64 64 00 00 00 03 b1 a5 - 100% cool
        b0 b1 b2 b3 00 01 01 9f 00 09 35 b1 64 32 00 00 00 03 7f 6e - 100% cool - dim 50%
        """
        scaled_temp, brightness = white_levels_to_scaled_color_temp(
            warm_white, cool_white
        )
        return self.construct_wrapped_message(
            bytearray(
                [
                    0x35,
                    0xB1,
                    scaled_temp,
                    # If the brightness goes below the precision the device
                    # will flip from cold to warm
                    max(self.MIN_BRIGHTNESS, brightness),
                    0x00,
                    0x00,
                    0x00,
                    0x03,
                ]
            )
        )


class ProtocolLEDENETAddressableChristmas(ProtocolLEDENETAddressableBase):
    @property
    def name(self) -> str:
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS

    @property
    def zones(self) -> bool:
        """If the protocol supports zones."""
        return True

    @property
    def power_push_updates(self) -> bool:
        """If True the protocol pushes power state updates when controlled via ir/rf/app."""
        return True

    @property
    def dimmable_effects(self) -> bool:
        """Protocol supports dimmable effects."""
        return False

    @property
    def requires_turn_on(self) -> bool:
        """If True the device must be turned on before setting level/patterns/modes."""
        return False

    def construct_preset_pattern(
        self, pattern: int, speed: int, brightness: int
    ) -> bytearray:
        """The bytes to send for a preset pattern.

        OUTER_MESSAGE_WRAPPER = [0xB0, 0xB1, 0xB2, 0xB3, 0x00, 0x01, 0x01]

        b0 b1 b2 b3 00 01 01 2b 00 07 a3 01 10 00 00 00 b4 62

          inner = a3 01 10 00 00 00 b4
        """
        return self.construct_wrapped_message(
            bytearray(
                [
                    0xA3,
                    pattern,
                    utils.speedToDelay(speed),
                    0x00,
                    0x00,
                    0x00,
                ]
            )
        )

    def construct_levels_change(
        self,
        persist: int,
        red: int,
        green: int,
        blue: int,
        warm_white: int,
        cool_white: int,
        write_mode: LevelWriteMode,
    ) -> bytearray:
        """The bytes to send for a level change request.


        Green 100%:
        b0b1b2b300010180000d3ba100646400000000000000a49d

        Blue 50%
        b0b1b2b300010110000d3ba176e4320000000000000068b5

        Red & green 255 and 25% bright
        b0b1b2b300010133000d3ba11e64190000000000000077f6

        Red & Blue 255 and 40%
        b0b1b2b30001014e000d3ba196642800000000000000fe1f

        Inner messages

        Single - Green - Brightness 100%
        3b a1 3c 64 64 00 00 00 00 00 00 00 e0

        Single - Green - Brightness 50%
        3b a1 3c 64 32 00 00 00 00 00 00 00 ae

        Single - Blue - Brightness 100%
        3b a1 78 64 64 00 00 00 00 00 00 00 1c

        Single - Red - Brightness 100%
        3b a1 00 64 64 00 00 00 00 00 00 00 a4

        Single - Pink (100% Red, 100% Blue) - Brightness 100%
        3b a1 96 64 64 00 00 00 00 00 00 00 3a

        Single - White (100% Red, 100% Green, 100% Blue) - Brightness 100%
        3b a1 00 00 64 00 00 00 00 00 00 00 40

        Single - Yellow (100% Red, 100% Green) - Brightness 100%
        3b a1 1e 64 64 00 00 00 00 00 00 00 c2

        Single - Light Blue (100% Blue, 100% Green) - Brightness 100%
        3b a1 5a 64 64 00 00 00 00 00 00 00 fe

        Single - Red - Brightness 0%
        3b a1 00 64 00 00 00 00 00 00 00 00 40

        Single - Red - Brightness 50%
        3b a1 00 64 32 00 00 00 00 00 00 00 72

        Single - Blue - Brightness 50%
        3b a1 78 64 32 00 00 00 00 00 00 00 ea
        """
        h, s, v = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        return self.construct_wrapped_message(
            bytearray(
                [
                    0x3B,
                    0xA1,
                    int(h * 180),
                    int(s * 100),
                    int(v * 100),
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                ]
            )
        )

    def construct_zone_change(
        self,
        points: int,  # the number of points on the strip
        rgb_list: List[Tuple[int, int, int]],
        speed: int,
        effect: MultiColorEffects,
    ) -> bytearray:
        """The bytes to send for multiple zones.

        6 Zone All red
        a000060001ff00000000ff0002ff00000000ff0003ff00000000ff0004ff00000000ff0005ff00000000ff0006ff00000000ffaf
        6 Zone All Yellow
        a000060001ffff000000ff0002ffff000000ff0003ffff000000ff0004ffff000000ff0005ffff000000ff0006ffff000000ffa9
        6 Zone All Green
        a00006000100ff000000ff000200ff000000ff000300ff000000ff000400ff000000ff000500ff000000ff000600ff000000ffaf
        6 Zone All Green
        a00006000100ff000000ff000200ff000000ff000300ff000000ff000400ff000000ff000500ff000000ff000600ff000000ffaf
        6 Zone All Cyan
        a00006000100ffff0000ff000200ffff0000ff000300ffff0000ff000400ffff0000ff000500ffff0000ff000600ffff0000ffa9
        6 Zone All White
        a000060001ffffff0000ff0002ffffff0000ff0003ffffff0000ff0004ffffff0000ff0005ffffff0000ff0006ffffff0000ffa3
        """
        sent_zones = len(rgb_list)
        if sent_zones > points:
            raise ValueError(f"Device supports a maximum of {points} zones")
        msg = bytearray([0xA0, 0x00, 0x60])
        zone_size = points // sent_zones
        remaining = points
        for rgb in rgb_list:
            for _ in range(zone_size):
                remaining -= 1
                msg.extend(
                    bytearray([0x00, points - remaining, *rgb, 0x00, 0x00, 0xFF])
                )
        while remaining:
            remaining -= 1
            msg.extend(
                bytearray([0x00, points - remaining, *rgb_list[-1], 0x00, 0x00, 0xFF])
            )
        return self.construct_wrapped_message(msg)
