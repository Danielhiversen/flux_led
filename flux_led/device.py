import datetime
import logging
import select
import socket
import threading
import time
from typing import Dict, List, Optional, Tuple

from .base_device import PROTOCOL_PROBES, LEDENETDevice
from .const import (
    DEFAULT_RETRIES,
    EFFECT_RANDOM,
    STATE_BLUE,
    STATE_COOL_WHITE,
    STATE_GREEN,
    STATE_RED,
    STATE_WARM_WHITE,
)
from .sock import _socket_retry
from .timer import LedTimer
from .utils import color_temp_to_white_levels, utils

_LOGGER = logging.getLogger(__name__)


class WifiLedBulb(LEDENETDevice):
    """A LEDENET Wifi bulb device."""

    def __init__(self, ipaddr: str, port: int = 5577, timeout: int = 5) -> None:
        """Init and setup the bulb."""
        super().__init__(ipaddr, port, timeout)
        self._socket: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self.setup()

    def setup(self) -> None:
        """Setup the connection and fetch initial state."""
        self.connect(retry=DEFAULT_RETRIES)
        self.update_state()

    def _connect_if_disconnected(self) -> None:
        """Connect only if not already connected."""
        if self._socket is None:
            self.connect()

    @_socket_retry(attempts=0)  # type: ignore
    def connect(self) -> None:
        self.close()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self.timeout)
        _LOGGER.debug("%s: connect", self.ipaddr)
        self._socket.connect((self.ipaddr, self.port))

    def close(self) -> None:
        if self._socket is None:
            return
        try:
            self._socket.close()
        except OSError:
            pass
        finally:
            self._socket = None

    def turnOn(self, retry: int = DEFAULT_RETRIES) -> None:
        self._change_state(retry=retry, turn_on=True)

    def turnOff(self, retry: int = DEFAULT_RETRIES) -> None:
        self._change_state(retry=retry, turn_on=False)

    @_socket_retry(attempts=DEFAULT_RETRIES)  # type: ignore
    def _change_state(self, turn_on: bool = True) -> None:
        assert self._protocol is not None
        _LOGGER.debug("%s: Changing state to %s", self.ipaddr, turn_on)
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(self._protocol.construct_state_change(turn_on))
            # After changing state, the device replies with
            expected_response_len = 4
            # - 0x0F 0x71 [0x23|0x24] [CHECK DIGIT]
            rx = self._read_msg(expected_response_len)
            _LOGGER.debug("%s: state response %s", self.ipaddr, rx)
            if len(rx) == expected_response_len:
                # We cannot use the power state workaround here
                # since we are not listening for power state changes
                # like the aio version
                new_power_state = (
                    self._protocol.on_byte if turn_on else self._protocol.off_byte
                )
                self._set_power_state(new_power_state)
            # The device will send back a state change here
            # but it will likely be stale so we want to recycle
            # the connetion so we do not have to wait as sometimes
            # it stalls
            self.close()

    def setWarmWhite(
        self, level: int, persist: bool = True, retry: int = DEFAULT_RETRIES
    ) -> None:
        self.set_levels(w=utils.percentToByte(level), persist=persist, retry=retry)

    def setWarmWhite255(
        self, level: int, persist: bool = True, retry: int = DEFAULT_RETRIES
    ) -> None:
        self.set_levels(w=level, persist=persist, retry=retry)

    def setColdWhite(
        self, level: int, persist: bool = True, retry: int = DEFAULT_RETRIES
    ) -> None:
        self.set_levels(w2=utils.percentToByte(level), persist=persist, retry=retry)

    def setColdWhite255(
        self, level: int, persist: bool = True, retry: int = DEFAULT_RETRIES
    ) -> None:
        self.set_levels(w2=level, persist=persist, retry=retry)

    def setWhiteTemperature(
        self,
        temperature: int,
        brightness: int,
        persist: bool = True,
        retry: int = DEFAULT_RETRIES,
    ) -> None:
        warm, cold = color_temp_to_white_levels(temperature, brightness)
        self.set_levels(w=warm, w2=cold, persist=persist, retry=retry)

    def setRgb(
        self,
        r: int,
        g: int,
        b: int,
        persist: bool = True,
        brightness: Optional[int] = None,
        retry: int = DEFAULT_RETRIES,
    ) -> None:
        self.set_levels(r, g, b, persist=persist, brightness=brightness, retry=retry)

    def setRgbw(
        self,
        r: Optional[int] = None,
        g: Optional[int] = None,
        b: Optional[int] = None,
        w: Optional[int] = None,
        persist: bool = True,
        brightness: Optional[int] = None,
        w2: Optional[int] = None,
        retry: int = DEFAULT_RETRIES,
    ) -> None:
        self.set_levels(r, g, b, w, w2, persist, brightness, retry=retry)

    def set_levels(
        self,
        r: Optional[int] = None,
        g: Optional[int] = None,
        b: Optional[int] = None,
        w: Optional[int] = None,
        w2: Optional[int] = None,
        persist: bool = True,
        brightness: Optional[int] = None,
        retry: int = DEFAULT_RETRIES,
    ) -> None:
        self._process_levels_change(
            *self._generate_levels_change(
                {
                    STATE_RED: r,
                    STATE_GREEN: g,
                    STATE_BLUE: b,
                    STATE_WARM_WHITE: w,
                    STATE_COOL_WHITE: w2,
                },
                persist,
                brightness,
            ),
            retry=retry,
        )

    @_socket_retry(attempts=2)  # type: ignore
    def _process_levels_change(self, msg: bytearray, updates: Dict[str, int]) -> None:
        # send the message
        with self._lock:
            self._connect_if_disconnected()
            self._set_transition_complete_time()
            self._send_msg(msg)
            if updates:
                self._replace_raw_state(updates)

    def _send_msg(self, bytes: bytearray) -> None:
        assert self._socket is not None
        _LOGGER.debug(
            "%s => %s (%d)",
            self.ipaddr,
            " ".join(f"0x{x:02X}" for x in bytes),
            len(bytes),
        )
        self._socket.send(bytes)

    def _read_msg(self, expected: int) -> bytearray:
        assert self._socket is not None
        remaining = expected
        rx = bytearray()
        begin = time.monotonic()
        while remaining > 0:
            timeout_left = self.timeout - (time.monotonic() - begin)
            if timeout_left <= 0:
                break
            try:
                self._socket.setblocking(False)
                read_ready, _, _ = select.select([self._socket], [], [], timeout_left)
                if not read_ready:
                    _LOGGER.debug(
                        "%s: timed out reading %d bytes", self.ipaddr, expected
                    )
                    break
                chunk = self._socket.recv(remaining)
                _LOGGER.debug(
                    "%s <= %s (%d)",
                    self.ipaddr,
                    " ".join(f"0x{x:02X}" for x in chunk),
                    len(chunk),
                )
                if chunk:
                    begin = time.monotonic()
                remaining -= len(chunk)
                rx.extend(chunk)
            except OSError as ex:
                _LOGGER.debug("%s: socket error: %s", self.ipaddr, ex)
                pass
            finally:
                self._socket.setblocking(True)
        return rx

    def getClock(self) -> Optional[datetime.datetime]:
        msg = bytearray([0x11, 0x1A, 0x1B, 0x0F])
        with self._lock:
            self._connect_if_disconnected()
            assert self._protocol is not None
            self._send_msg(self._protocol.construct_message(msg))
            rx = self._read_msg(12)
        if len(rx) != 12:
            return None
        year = rx[3] + 2000
        month = rx[4]
        date = rx[5]
        hour = rx[6]
        minute = rx[7]
        second = rx[8]
        # dayofweek = rx[9]
        try:
            dt: Optional[datetime.datetime] = datetime.datetime(
                year, month, date, hour, minute, second
            )
        except Exception:
            dt = None
        return dt

    def setClock(self) -> None:
        assert self._protocol is not None
        msg = bytearray([0x10, 0x14])
        now = datetime.datetime.now()
        msg.append(now.year - 2000)
        msg.append(now.month)
        msg.append(now.day)
        msg.append(now.hour)
        msg.append(now.minute)
        msg.append(now.second)
        msg.append(now.isoweekday())  # day of week
        msg.append(0x00)
        msg.append(0x0F)
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(self._protocol.construct_message(msg))
            # Setting the clock does not always respond so we
            # cycle the connection
            self.close()

    def _determine_protocol(self) -> bytearray:
        """Determine the type of protocol based of first 2 bytes."""
        read_bytes = 2
        for protocol_cls in PROTOCOL_PROBES:
            protocol = protocol_cls()
            with self._lock:
                self._connect_if_disconnected()
                self._send_msg(protocol.construct_state_query())
                rx = self._read_msg(read_bytes)
                # if any response is recieved, use the protocol
                if len(rx) != read_bytes:
                    # We just sent a garage query which the old procotol
                    # cannot process, recycle the connection
                    self.close()
                    continue
                full_msg = rx + self._read_msg(
                    protocol.state_response_length - read_bytes
                )
                if protocol.is_valid_state_response(full_msg):
                    self._set_protocol_from_msg(full_msg, protocol.name)
                return full_msg
        raise Exception("Cannot determine protocol")

    def setPresetPattern(
        self,
        pattern: int,
        speed: int,
        brightness: int = 100,
        retry: int = DEFAULT_RETRIES,
    ) -> None:
        self._set_transition_complete_time()
        self._send_with_retry(
            self._generate_preset_pattern(pattern, speed, brightness), retry=retry
        )

    def set_effect(
        self,
        effect: str,
        speed: int,
        brightness: int = 100,
        retry: int = DEFAULT_RETRIES,
    ) -> None:
        """Set an effect."""
        if effect == EFFECT_RANDOM:
            self.set_random()
            return
        self.setPresetPattern(
            self._effect_to_pattern(effect), speed, brightness, retry=retry
        )

    def set_random(self, retry: int = DEFAULT_RETRIES) -> None:
        """Set levels randomly."""
        self._process_levels_change(*self._generate_random_levels_change(), retry=retry)

    @_socket_retry(attempts=2)  # type: ignore
    def _send_with_retry(self, msg: bytearray) -> None:
        """Send a message under the lock."""
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(msg)

    def getTimers(self) -> List[LedTimer]:
        assert self._protocol is not None
        msg = bytearray([0x22, 0x2A, 0x2B, 0x0F])
        resp_len = 88
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(self._protocol.construct_message(msg))
            rx = self._read_msg(resp_len)
        if len(rx) != resp_len:
            print("response too short!")
            raise Exception

        # utils.dump_data(rx)
        start = 2
        timer_list = []
        # pass in the 14-byte timer structs
        for i in range(6):
            timer_bytes = rx[start:][:14]
            timer = LedTimer(timer_bytes)
            timer_list.append(timer)
            start += 14

        return timer_list

    def sendTimers(self, timer_list: List[LedTimer]) -> None:
        assert self._protocol is not None
        # remove inactive or expired timers from list
        for t in timer_list:
            if not t.isActive() or t.isExpired():
                timer_list.remove(t)

        # truncate if more than 6
        if len(timer_list) > 6:
            print("too many timers, truncating list")
            del timer_list[6:]

        # pad list to 6 with inactive timers
        if len(timer_list) != 6:
            for i in range(6 - len(timer_list)):
                timer_list.append(LedTimer())

        msg_start = bytearray([0x21])
        msg_end = bytearray([0x00, 0xF0])
        msg = bytearray()

        # build message
        msg.extend(msg_start)
        for t in timer_list:
            msg.extend(t.toBytes())
        msg.extend(msg_end)
        with self._lock:
            self._connect_if_disconnected()
            self._send_msg(self._protocol.construct_message(msg))
            # not sure what the resp is, prob some sort of ack?
            self._read_msg(4)

    @_socket_retry(attempts=2)  # type: ignore
    def query_state(self, led_type: Optional[str] = None) -> bytearray:
        if led_type:
            self.setProtocol(led_type)
        elif not self._protocol:
            return self._determine_protocol()

        assert self._protocol is not None
        with self._lock:
            self.connect()
            self._send_msg(self._protocol.construct_state_query())
            return self._read_msg(self._protocol.state_response_length)

    def update_state(self, retry: int = 2) -> None:
        rx = self.query_state(retry=retry)
        if rx and self.process_state_response(rx):
            self.available = True
            return
        self.set_unavailable()

    def setCustomPattern(
        self,
        rgb_list: List[Tuple[int, int, int]],
        speed: int,
        transition_type: str,
        retry: int = DEFAULT_RETRIES,
    ) -> None:
        """Set a custom pattern on the device."""
        self._send_with_retry(
            self._generate_custom_patterm(rgb_list, speed, transition_type), retry=retry
        )

    def refreshState(self) -> None:
        return self.update_state()
