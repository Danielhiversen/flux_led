"""FluxLED Protocols."""

from abc import abstractmethod
from collections import namedtuple
import logging
from typing import List, Tuple

from .const import TRANSITION_GRADUAL, TRANSITION_JUMP, TRANSITION_STROBE
from .utils import utils, white_levels_to_scaled_color_temp

_LOGGER = logging.getLogger(__name__)

# Protocol names
PROTOCOL_LEDENET_ORIGINAL = "LEDENET_ORIGINAL"
PROTOCOL_LEDENET_9BYTE = "LEDENET"
PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS = "LEDENET_DIMMABLE_EFFECTS"
PROTOCOL_LEDENET_8BYTE = "LEDENET_8BYTE"  # Previously was called None
PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS = "LEDENET_8BYTE_DIMMABLE_EFFECTS"
PROTOCOL_LEDENET_ADDRESSABLE_A1 = "LEDENET_ADDRESSABLE_A1"
PROTOCOL_LEDENET_ADDRESSABLE_A2 = "LEDENET_ADDRESSABLE_A2"
PROTOCOL_LEDENET_ADDRESSABLE_A3 = "LEDENET_ADDRESSABLE_A3"
PROTOCOL_LEDENET_CCT = "LEDENET_CCT"

TRANSITION_BYTES = {
    TRANSITION_JUMP: 0x3B,
    TRANSITION_STROBE: 0x3C,
    TRANSITION_GRADUAL: 0x3A,
}

LEDENET_ORIGINAL_STATE_RESPONSE_LEN = 11
LEDENET_STATE_RESPONSE_LEN = 14
LEDENET_POWER_RESPONSE_LEN = 4
LEDENET_ADDRESSABLE_STATE_RESPONSE_LEN = 25

MSG_ORIGINAL_POWER_STATE = "original_power_state"
MSG_ORIGINAL_STATE = "original_state"

MSG_POWER_STATE = "power_state"
MSG_STATE = "state"

MSG_ADDRESSABLE_STATE = "addressable_state"

MSG_FIRST_BYTE = {
    0xF0: MSG_POWER_STATE,
    0x00: MSG_POWER_STATE,
    0x0F: MSG_POWER_STATE,
    0x78: MSG_ORIGINAL_POWER_STATE,
    0x66: MSG_ORIGINAL_STATE,
    0x81: MSG_STATE,
    0xB0: MSG_ADDRESSABLE_STATE,
}
MSG_LENGTHS = {
    MSG_POWER_STATE: LEDENET_POWER_RESPONSE_LEN,
    MSG_ORIGINAL_POWER_STATE: LEDENET_POWER_RESPONSE_LEN,
    MSG_ORIGINAL_STATE: LEDENET_ORIGINAL_STATE_RESPONSE_LEN,
    MSG_STATE: LEDENET_STATE_RESPONSE_LEN,
    MSG_ADDRESSABLE_STATE: LEDENET_ADDRESSABLE_STATE_RESPONSE_LEN,
}


LEDENETOriginalRawState = namedtuple(
    "LEDENETOriginalRawState",
    [
        "head",
        "model_num",
        "power_state",
        "preset_pattern",
        "mode",
        "speed",
        "red",
        "green",
        "blue",
        "warm_white",
        "check_sum",
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
        "head",
        "model_num",
        "power_state",
        "preset_pattern",
        "mode",
        "speed",
        "red",
        "green",
        "blue",
        "warm_white",
        "version_number",
        "cool_white",
        "color_mode",
        "check_sum",
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

    power_state_response_length = MSG_LENGTHS[MSG_POWER_STATE]

    def __init__(self):
        self._counter = 0
        super().__init__()

    def _increment_counter(self):
        """Increment the counter byte."""
        self._counter += 1
        if self._counter == 255:
            self._counter = 0
        return self._counter

    def is_start_of_addressable_response(self, data):
        """Check if a message is the start of an addressable state response."""
        return False

    def is_valid_addressable_response(self, data):
        """Check if a message is a valid addressable state response."""
        return False

    def expected_response_length(self, data):
        """Return the number of bytes expected in the response.

        If the response is unknown, we assume the response is
        a complete message since we have no way of knowing otherwise.
        """
        return MSG_LENGTHS.get(MSG_FIRST_BYTE.get(data[0]), len(data))

    @abstractmethod
    def construct_state_query(self):
        """The bytes to send for a query request."""

    @abstractmethod
    def is_valid_state_response(self, raw_state):
        """Check if a state response is valid."""

    @abstractmethod
    def is_start_of_state_response(self, data):
        """Check if a message is the start of a state response."""

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

    @abstractmethod
    def is_start_of_power_state_response(self, data):
        """Check if a message is the start of a power response."""

    @property
    def on_byte(self):
        """The on byte."""
        return 0x23

    @property
    def off_byte(self):
        """The off byte."""
        return 0x24

    @property
    def dimmable_effects(self):
        """Protocol supports dimmable effects."""
        return False

    @abstractmethod
    def construct_state_change(self, turn_on):
        """The bytes to send for a state change request."""

    @abstractmethod
    def construct_levels_change(
        self, persist, red, green, blue, warm_white, cool_white, color_mask
    ):
        """The bytes to send for a level change request."""

    def construct_preset_pattern(self, pattern, speed, brightness):
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
    def name(self):
        """The name of the protocol."""

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
        return len(msg) == self.power_state_response_length and msg[0] == 0x78

    def is_valid_state_response(self, raw_state):
        """Check if a state response is valid."""
        return (
            len(raw_state) == self.state_response_length
            and raw_state[0] == 0x66
            and raw_state[1] == 0x01
        )

    def is_start_of_state_response(self, data):
        """Check if a message is the start of a state response."""
        return data[0] == 0x66

    def is_start_of_power_state_response(self, data):
        """Check if a message is the start of a state response."""
        return data[0] == 0x78

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

    ADDRESSABLE_HEADER = [0xB0, 0xB1, 0xB2, 0xB3, 0x00, 0x01, 0x01]
    addressable_response_length = MSG_LENGTHS[MSG_ADDRESSABLE_STATE]

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
            len(msg) != self.power_state_response_length
            or not self.is_start_of_power_state_response(msg)
            or msg[1] != 0x71
            or msg[2] not in (self.on_byte, self.off_byte)
        ):
            return False
        return self.is_checksum_correct(msg)

    def is_start_of_power_state_response(self, data):
        """Check if a message is the start of a state response."""
        return len(data) >= 1 and MSG_FIRST_BYTE[data[0]] == MSG_POWER_STATE

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
        """The bytes to send for a state change request.

        Alternate messages

        Off 3b 24 00 00 00 00 00 00 00 32 00 00 91
        On  3b 23 00 00 00 00 00 00 00 32 00 00 90
        """
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

    def construct_music_mode(self, sensitivity):
        """The bytes to send for a level change request.

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
        return self.construct_message(bytearray([0x73, 0x01, sensitivity, 0x0F]))

    def is_start_of_addressable_response(self, data):
        """Check if a message is the start of an addressable state response."""
        return data.startswith(bytearray(self.ADDRESSABLE_HEADER))

    def is_valid_addressable_response(self, data):
        """Check if a message is a valid addressable state response."""
        if len(data) != self.addressable_response_length:
            return False
        if not self.is_start_of_addressable_response(data):
            return False
        return self.is_checksum_correct(data)


class ProtocolLEDENET8ByteDimmableEffects(ProtocolLEDENET8Byte):
    @property
    def dimmable_effects(self):
        """Protocol supports dimmable effects."""
        return True

    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS

    def construct_preset_pattern(self, pattern, speed, brightness):
        """The bytes to send for a preset pattern."""
        delay = utils.speedToDelay(speed)
        return self.construct_message(bytearray([0x38, pattern, delay, brightness]))


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


class ProtocolLEDENET9ByteDimmableEffects(ProtocolLEDENET9Byte):
    """The newer LEDENET protocol with checksums that uses 9 bytes to set state."""

    @property
    def dimmable_effects(self):
        """Protocol supports dimmable effects."""
        return True

    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS

    def construct_preset_pattern(self, pattern, speed, brightness):
        """The bytes to send for a preset pattern."""
        delay = utils.speedToDelay(speed)
        return self.construct_message(bytearray([0x38, pattern, delay, brightness]))


class ProtocolLEDENETAddressableA1(ProtocolLEDENET9Byte):
    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ADDRESSABLE_A1

    @property
    def dimmable_effects(self):
        """Protocol supports dimmable effects."""
        return False

    def construct_preset_pattern(self, pattern, speed, brightness):
        """The bytes to send for a preset pattern."""
        effect = pattern + 99
        return self.construct_message(
            bytearray([0x61, effect >> 8, effect & 0xFF, speed, 0x0F])
        )


class ProtocolLEDENETAddressableA2(ProtocolLEDENET9Byte):
    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ADDRESSABLE_A2

    @property
    def dimmable_effects(self):
        """Protocol supports dimmable effects."""
        return True

    def construct_preset_pattern(self, pattern, speed, brightness):
        """The bytes to send for a preset pattern."""
        return self.construct_message(bytearray([0x42, pattern, speed, brightness]))

    def construct_levels_change(
        self, persist, red, green, blue, warm_white, cool_white, write_mode
    ):
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

    def construct_music_mode(self, sensitivity):
        """The bytes to send for a level change request.

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
        red = 0xFF
        green = 0x00
        blue = 0x00

        return self.construct_message(
            bytearray(
                [
                    0x73,
                    0x01,
                    red,
                    green,
                    blue,
                    red,
                    green,
                    blue,
                    sensitivity,
                    0x64,
                    0x64,
                ]
            )
        )


class ProtocolLEDENETAddressableA3(ProtocolLEDENET9Byte):
    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ADDRESSABLE_A3

    @property
    def dimmable_effects(self):
        """Protocol supports dimmable effects."""
        return True

    def construct_preset_pattern(self, pattern, speed, brightness):
        """The bytes to send for a preset pattern."""
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
                    speed,
                    brightness,
                    0x00,
                ]
            )
        )

    def construct_music_mode(self, sensitivity):
        """The bytes to send for a level change request.

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
        """
        counter_byte = self._increment_counter()
        red = 0xFF
        green = 0x00
        blue = 0x00
        inner_message = self.construct_message(
            bytearray(
                [
                    0x73,
                    0x01,
                    red,
                    green,
                    blue,
                    red,
                    green,
                    blue,
                    sensitivity,
                    0x64,
                ]
            )
        )

        return self.construct_message(
            bytearray(
                [*self.ADDRESSABLE_HEADER, counter_byte, 0x00, 0x0D, *inner_message]
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
        inner_message = self.construct_message(
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
                    0x06,
                    0x01,
                    0x00,
                    0x00,
                ]
            )
        )

        return self.construct_message(
            bytearray(
                [*self.ADDRESSABLE_HEADER, counter_byte, 0x00, 0x0D, *inner_message]
            )
        )


class ProtocolLEDENETCCT(ProtocolLEDENET9Byte):

    MIN_BRIGHTNESS = 2

    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_CCT

    @property
    def dimmable_effects(self):
        """Protocol supports dimmable effects."""
        return False

    def construct_levels_change(
        self, persist, red, green, blue, warm_white, cool_white, write_mode
    ):
        """The bytes to send for a level change request.

        b0 b1 b2 b3 00 01 01 52 00 09 35 b1 00 64 00 00 00 03 4d bd - 100% warm
        b0 b1 b2 b3 00 01 01 72 00 09 35 b1 64 64 00 00 00 03 b1 a5 - 100% cool
        b0 b1 b2 b3 00 01 01 9f 00 09 35 b1 64 32 00 00 00 03 7f 6e - 100% cool - dim 50%
        """
        counter_byte = self._increment_counter()
        scaled_temp, brightness = white_levels_to_scaled_color_temp(
            warm_white, cool_white
        )
        inner_message = self.construct_message(
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

        return self.construct_message(
            bytearray(
                [*self.ADDRESSABLE_HEADER, counter_byte, 0x00, 0x09, *inner_message]
            )
        )
