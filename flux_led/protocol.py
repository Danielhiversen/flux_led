"""FluxLED Protocols."""

from abc import abstractmethod
import logging

# Protocol names
PROTOCOL_LEDENET_ORIGINAL = "LEDENET_ORIGINAL"
PROTOCOL_LEDENET_9BYTE = "LEDENET"
PROTOCOL_LEDENET_8BYTE = "LEDENET_8BYTE"  # Previously was called None

_LOGGER = logging.getLogger(__name__)


class ProtocolBase:
    """The base protocol."""

    @abstractmethod
    def construct_state_query(self):
        """The bytes to send for a query request."""

    @abstractmethod
    def is_valid_state_response(self, raw_state):
        """Check if a state response is valid."""

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
    def state_response_length(self):
        """The length of the query response."""
        return len(self.state_response_names)

    @abstractmethod
    def construct_message(self, raw_bytes):
        """Original protocol uses no checksum."""


class ProtocolLEDENETOriginal(ProtocolBase):
    """The original LEDENET protocol with no checksums."""

    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_ORIGINAL

    def is_valid_state_response(self, raw_state):
        """Check if a state response is valid."""
        return len(raw_state) == self.state_response_length and raw_state[1] == 0x01

    def construct_state_query(self):
        """The bytes to send for a query request."""
        return self.construct_message(bytearray([0xEF, 0x01, 0x77]))

    def construct_state_change(self, turn_on):
        """The bytes to send for a state change request."""
        return self.construct_message(
            bytearray([0xCC, self.on_byte if turn_on else self.off_byte, 0x33])
        )

    def construct_message(self, raw_bytes):
        """Original protocol uses no checksum."""
        return raw_bytes

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
    #     |  type
    #     msg head
    #
    @property
    def state_response_names(self):
        """The names of the values in the state response."""
        return [
            "head",
            "type",
            "power_state",
            "preset_pattern",
            "mode",
            "speed",
            "red",
            "green",
            "blue",
            "warm_white",
            "check_sum",
        ]

    @property
    def set_command_names(self):
        """The names of the values in the set command."""
        return [
            "head",
            "red",
            "green",
            "blue",
            "terminator",
        ]


class ProtocolLEDENET8Byte(ProtocolBase):
    """The newer LEDENET protocol with checksums that uses 8 bytes to set state."""

    def is_valid_state_response(self, raw_state):
        """Check if a state response is valid."""
        if len(raw_state) != self.state_response_length:
            return False
        if raw_state[0] != 0x81:
            return False
        expected_sum = sum(raw_state[0:-1]) & 0xFF
        if expected_sum != raw_state[-1]:
            _LOGGER.warning(
                "Checksum mismatch: Expected %s, got %s", expected_sum, raw_state[-1]
            )
            return False
        return True

    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_8BYTE

    def construct_state_change(self, turn_on):
        """The bytes to send for a state change request."""
        return self.construct_message(
            bytearray([0x71, self.on_byte if turn_on else self.off_byte, 0x0F])
        )

    def construct_message(self, raw_bytes):
        """Calculate checksum of byte array and add to end."""
        csum = sum(raw_bytes) & 0xFF
        raw_bytes.append(csum)
        return raw_bytes

    def construct_state_query(self):
        """The bytes to send for a query request."""
        return self.construct_message(bytearray([0x81, 0x8A, 0x8B]))

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
    #     |  type
    #     msg head
    #
    @property
    def state_response_names(self):
        """The names of the values in the state response."""
        return [
            "head",
            "type",
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
        ]

    @property
    def set_command_names(self):
        """The names of the values in the set command."""
        return [
            "head",
            "red",
            "green",
            "blue",
            "white",
            "write_mask_white2",
            "terminator",
        ]


class ProtocolLEDENET9Byte(ProtocolLEDENET8Byte):
    """The newer LEDENET protocol with checksums that uses 9 bytes to set state."""

    @property
    def name(self):
        """The name of the protocol."""
        return PROTOCOL_LEDENET_9BYTE

    @property
    def set_command_names(self):
        """The names of the values in the set command."""
        return [
            "head",
            "red",
            "green",
            "blue",
            "warm_white",
            "cold_write",
            "write_mode",
            "terminator",
        ]
