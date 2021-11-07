"""FluxLED Protocols."""

from abc import abstractmethod
from collections import namedtuple
import logging

from .const import (
    STATE_BLUE,
    STATE_CHECK_SUM,
    STATE_COLOR_MODE,
    STATE_COOL_WHITE,
    STATE_GREEN,
    STATE_HEAD,
    STATE_MODE,
    STATE_MODEL_NUM,
    STATE_POWER_STATE,
    STATE_PRESET_PATTERN,
    STATE_RED,
    STATE_SPEED,
    STATE_VERSION_NUMBER,
    STATE_WARM_WHITE,
    TRANSITION_GRADUAL,
    TRANSITION_JUMP,
    TRANSITION_STROBE,
)
from .utils import utils

_LOGGER = logging.getLogger(__name__)

# Protocol names
PROTOCOL_LEDENET_ORIGINAL = "LEDENET_ORIGINAL"
PROTOCOL_LEDENET_9BYTE = "LEDENET"
PROTOCOL_LEDENET_8BYTE = "LEDENET_8BYTE"  # Previously was called None
PROTOCOL_LEDENET_ADDRESSABLE = "LEDENET_ADDRESSABLE"

TRANSITION_BYTES = {
    TRANSITION_JUMP: 0x3B,
    TRANSITION_STROBE: 0x3C,
    TRANSITION_GRADUAL: 0x3A,
}

LEDENET_ORIGINAL_STATE_RESPONSE_LEN = 11
LEDENET_STATE_RESPONSE_LEN = 14

LEDENET_BASE_STATE = [
    STATE_HEAD,
    STATE_MODEL_NUM,
    STATE_POWER_STATE,
    STATE_PRESET_PATTERN,
    STATE_MODE,
    STATE_SPEED,
    STATE_RED,
    STATE_GREEN,
    STATE_BLUE,
    STATE_WARM_WHITE,
]


LEDENETOriginalRawState = namedtuple(
    "LEDENETOriginalRawState",
    [
        *LEDENET_BASE_STATE,
        STATE_CHECK_SUM,
    ],
)
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


LEDENETRawState = namedtuple(
    "LEDENETRawState",
    [
        *LEDENET_BASE_STATE,
        STATE_VERSION_NUMBER,
        STATE_COOL_WHITE,
        STATE_COLOR_MODE,
        STATE_CHECK_SUM,
    ],
)
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

    @abstractmethod
    def construct_state_query(self):
        """The bytes to send for a query request."""

    @abstractmethod
    def is_valid_state_response(self, raw_state):
        """Check if a state response is valid."""

    @abstractmethod
    def is_start_of_state_response(self, data):
        """Check if a message is the start of a state response."""

    def is_longer_than_state_response(self, data):
        """Check if a message is longer than a valid state response."""
        return len(data) > self.state_response_length

    def is_checksum_correct(self, msg):
        """Check a checksum of a message."""
        expected_sum = sum(msg[0:-1]) & 0xFF
        if expected_sum != msg[-1]:
            _LOGGER.warning(
                "Checksum mismatch: Expected %s, got %s", expected_sum, msg[-1]
            )
            return False
        return True

    @abstractmethod
    def is_valid_power_state_response(self, msg):
        """Check if a power state response is valid."""

    @property
    def on_byte(self):
        """The on byte."""
        return 0x23

    @property
    def off_byte(self):
        """The off byte."""
        return 0x24

    @abstractmethod
    def construct_state_change(self, turn_on):
        """The bytes to send for a state change request."""

    @abstractmethod
    def construct_levels_change(
        self, persist, red, green, blue, warm_white, cool_white, color_mask
    ):
        """The bytes to send for a level change request."""

    def construct_preset_pattern(self, pattern, speed):
        """The bytes to send for a preset pattern."""
        delay = utils.speedToDelay(speed)
        return self.construct_message(bytearray([0x61, pattern, delay, 0x0F]))

    def construct_custom_effect(self, rgb_list, speed, transition_type):
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
    def name(self):
        """The name of the protocol."""

    @property
    @abstractmethod
    def state_response_names(self):
        """The names of the values in the state response."""

    @property
    @abstractmethod
    def set_command_names(self):
        """The names of the values in the set command."""

    @property
    @abstractmethod
    def state_response_length(self):
        """The length of the query response."""

    @abstractmethod
    def construct_message(self, raw_bytes):
        """Original protocol uses no checksum."""

    @abstractmethod
    def named_raw_state(self, raw_state):
        """Convert raw_state to a namedtuple."""


class ProtocolLEDENETOriginal(ProtocolBase):
    """The original LEDENET protocol with no checksums."""

    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ORIGINAL

    @property
    def state_response_length(self):
        """The length of the query response."""
        return LEDENET_ORIGINAL_STATE_RESPONSE_LEN

    def is_valid_power_state_response(self, msg):
        """Check if a power state response is valid."""
        # We do not have dumps of the original ledenet
        # protocol (these devices are no longer made).
        # If we get them in the future, we can
        # implement push updates for these devices by
        # matching how is_valid_power_state_response works
        # for the newer protocol
        return False

    def is_valid_state_response(self, raw_state):
        """Check if a state response is valid."""
        return len(raw_state) == self.state_response_length and raw_state[1] == 0x01

    def is_start_of_state_response(self, data):
        """Check if a message is the start of a state response."""
        return False

    def construct_state_query(self):
        """The bytes to send for a query request."""
        return self.construct_message(bytearray([0xEF, 0x01, 0x77]))

    def construct_state_change(self, turn_on):
        """The bytes to send for a state change request."""
        return self.construct_message(
            bytearray([0xCC, self.on_byte if turn_on else self.off_byte, 0x33])
        )

    def construct_levels_change(
        self, persist, red, green, blue, warm_white, cool_white, color_mask
    ):
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

    def construct_message(self, raw_bytes):
        """Original protocol uses no checksum."""
        return raw_bytes

    def named_raw_state(self, raw_state):
        """Convert raw_state to a namedtuple."""
        return LEDENETOriginalRawState(*raw_state)


class ProtocolLEDENET8Byte(ProtocolBase):
    """The newer LEDENET protocol with checksums that uses 8 bytes to set state."""

    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_8BYTE

    @property
    def state_response_length(self):
        """The length of the query response."""
        return LEDENET_STATE_RESPONSE_LEN

    def is_valid_power_state_response(self, msg):
        """Check if a power state response is valid."""
        if (
            len(msg) != 4
            or msg[0] not in (0xF0, 0x00, 0x0F)
            or msg[1] != 0x71
            or msg[2] not in (self.on_byte, self.off_byte)
        ):
            return False
        return self.is_checksum_correct(msg)

    def is_start_of_state_response(self, data):
        """Check if a message is the start of a state response."""
        return data[0] == 0x81

    def is_valid_state_response(self, raw_state):
        """Check if a state response is valid."""
        if len(raw_state) != self.state_response_length:
            return False
        if not self.is_start_of_state_response(raw_state):
            return False
        return self.is_checksum_correct(raw_state)

    def construct_state_change(self, turn_on):
        """The bytes to send for a state change request."""
        return self.construct_message(
            bytearray([0x71, self.on_byte if turn_on else self.off_byte, 0x0F])
        )

    def construct_levels_change(
        self, persist, red, green, blue, warm_white, cool_white, write_mode
    ):
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

    def construct_message(self, raw_bytes):
        """Calculate checksum of byte array and add to end."""
        csum = sum(raw_bytes) & 0xFF
        raw_bytes.append(csum)
        return raw_bytes

    def construct_state_query(self):
        """The bytes to send for a query request."""
        return self.construct_message(bytearray([0x81, 0x8A, 0x8B]))

    def named_raw_state(self, raw_state):
        """Convert raw_state to a namedtuple."""
        return LEDENETRawState(*raw_state)


class ProtocolLEDENET9Byte(ProtocolLEDENET8Byte):
    """The newer LEDENET protocol with checksums that uses 9 bytes to set state."""

    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_9BYTE

    def construct_levels_change(
        self, persist, red, green, blue, warm_white, cool_white, write_mode
    ):
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


class ProtocolLEDENETAddressable(ProtocolLEDENET9Byte):

    ADDRESSABLE_HEADER = [0xB0, 0xB1, 0xB2, 0xB3, 0x00, 0x01, 0x01]

    def __init__(self):
        self._counter = 0
        super().__init__()

    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ADDRESSABLE

    def _increment_counter(self):
        """Increment the counter byte."""
        self._counter += 1
        if self._counter == 255:
            self._counter = 0
        return self._counter

    def construct_preset_pattern(self, pattern, speed):
        """The bytes to send for a preset pattern."""
        delay = utils.speedToDelay(speed)
        counter_byte = self._increment_counter()
        return self.construct_message(
            bytearray(
                [
                    *self.ADDRESSABLE_HEADER,
                    counter_byte,
                    0x00,
                    0x05,
                    0x42,
                    pattern,
                    delay,
                    0x64,
                    0x00,
                ]
            )
        )

    def construct_levels_change(
        self, persist, red, green, blue, warm_white, cool_white, write_mode
    ):
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
        counter_byte = self._increment_counter()
        preset_number = 0x01  # aka fixed color

        return self.construct_message(
            bytearray(
                [
                    *self.ADDRESSABLE_HEADER,
                    counter_byte,
                    0x00,
                    0x0D,
                    0x41,
                    preset_number,
                    red,
                    green,
                    blue,
                    0x00,
                    0x00,
                    0x00,
                    0x06,
                    0x01,
                    0x00,
                    0x00,
                    0x48,
                ]
            )
        )
