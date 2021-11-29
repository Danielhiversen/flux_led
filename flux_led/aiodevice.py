import asyncio
import contextlib
import logging
from typing import Callable, Coroutine, Dict, List, Optional, Tuple

from flux_led.protocol import ProtocolLEDENET8Byte, ProtocolLEDENETOriginal

from .aioprotocol import AIOLEDENETProtocol
from .base_device import PROTOCOL_PROBES, LEDENETDevice
from .const import (
    COLOR_MODE_CCT,
    COLOR_MODE_DIM,
    COLOR_MODE_RGB,
    COLOR_MODE_RGBW,
    COLOR_MODE_RGBWW,
    EFFECT_RANDOM,
    STATE_BLUE,
    STATE_COOL_WHITE,
    STATE_GREEN,
    STATE_RED,
    STATE_WARM_WHITE,
)
from .utils import color_temp_to_white_levels, rgbw_brightness, rgbww_brightness

_LOGGER = logging.getLogger(__name__)


MAX_UPDATES_WITHOUT_RESPONSE = 4
POWER_STATE_TIMEOUT = 1.2  # number of seconds before declaring on/off failed


class AIOWifiLedBulb(LEDENETDevice):
    """A LEDENET Wifi bulb device."""

    def __init__(self, ipaddr: str, port: int = 5577, timeout: int = 5) -> None:
        """Init and setup the bulb."""
        super().__init__(ipaddr, port, timeout)
        self._lock = asyncio.Lock()
        self._aio_protocol: Optional[AIOLEDENETProtocol] = None
        self._on_futures: List["asyncio.Future[bool]"] = []
        self._off_futures: List["asyncio.Future[bool]"] = []
        self._data_future: Optional["asyncio.Future[bytes]"] = None
        self._updated_callback: Optional[Callable[[], None]] = None
        self._updates_without_response = 0
        self._buffer = b""
        self.loop = asyncio.get_running_loop()

    async def async_setup(self, updated_callback: Callable[[], None]) -> None:
        """Setup the connection and fetch initial state."""
        self._updated_callback = updated_callback
        await self._async_determine_protocol()

    async def async_stop(self) -> None:
        """Shutdown the connection"""
        if self._aio_protocol:
            self._aio_protocol.close()

    async def _async_send_state_query(self) -> None:
        assert self._protocol is not None
        await self._async_send_msg(self._protocol.construct_state_query())

    async def _async_execute_and_wait_for(
        self,
        futures: List["asyncio.Future[bool]"],
        coro: Callable[[], Coroutine[None, None, None]],
    ) -> bool:
        future: "asyncio.Future[bool]" = asyncio.Future()
        futures.append(future)
        await coro()
        _LOGGER.debug("%s: Waiting for power state response", self.ipaddr)
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(future), POWER_STATE_TIMEOUT / 2)
            return True
        _LOGGER.debug(
            "%s: Did not get expected power state response, sending state query",
            self.ipaddr,
        )
        await self._async_send_state_query()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(future, POWER_STATE_TIMEOUT / 2)
            return True
        _LOGGER.debug(
            "%s: State query did not return expected power state", self.ipaddr
        )
        return False

    async def _async_turn_on(self) -> None:
        assert self._protocol is not None
        await self._async_send_msg(self._protocol.construct_state_change(True))

    async def _async_turn_off_on(self) -> None:
        await self._async_turn_off()
        await self._async_turn_on()

    async def async_turn_on(self) -> bool:
        """Turn on the device."""
        calls = (self._async_turn_on, self._async_turn_off_on, self._async_turn_on)
        for idx, call in enumerate(calls):
            if (
                await self._async_execute_and_wait_for(self._on_futures, call)
                or self.is_on
            ):
                return True
            _LOGGER.debug(
                "%s: Failed to turn on (%s/%s)", self.ipaddr, 1 + idx, len(calls)
            )
        return False

    async def _async_turn_off(self) -> None:
        assert self._protocol is not None
        await self._async_send_msg(self._protocol.construct_state_change(False))

    async def _async_turn_on_off(self) -> None:
        await self._async_turn_on()
        await self._async_turn_off()

    async def async_turn_off(self) -> bool:
        """Turn off the device."""
        calls = (self._async_turn_off, self._async_turn_on_off, self._async_turn_off)
        for idx, call in enumerate(calls):
            if (
                await self._async_execute_and_wait_for(self._off_futures, call)
                or not self.is_on
            ):
                return True
            _LOGGER.debug(
                "%s: Failed to turn off (%s/%s)", self.ipaddr, 1 + idx, len(calls)
            )
        return False

    async def async_set_white_temp(
        self, temperature: int, brightness: int, persist: bool = True
    ) -> None:
        """Set the white tempature."""
        warm, cold = color_temp_to_white_levels(temperature, brightness)
        await self.async_set_levels(w=warm, w2=cold, persist=persist)

    async def async_update(self) -> None:
        """Request an update.

        The callback will be triggered when the state is recieved.
        """
        if self._updates_without_response == MAX_UPDATES_WITHOUT_RESPONSE:
            if self._aio_protocol:
                self._aio_protocol.close()
            self.set_unavailable()
            self._updates_without_response = 0
            raise RuntimeError("Bulb stopped responding")
        await self._async_send_state_query()
        self._updates_without_response += 1

    async def async_set_levels(
        self,
        r: Optional[int] = None,
        g: Optional[int] = None,
        b: Optional[int] = None,
        w: Optional[int] = None,
        w2: Optional[int] = None,
        persist: bool = True,
        brightness: Optional[int] = None,
    ) -> None:
        """Set any of the levels."""
        await self._async_process_levels_change(
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
            )
        )

    async def _async_process_levels_change(
        self, msg: bytearray, updates: Dict[str, int]
    ) -> None:
        """Process and send a levels change."""
        self._set_transition_complete_time()
        await self._async_send_msg(msg)
        if updates:
            self._replace_raw_state(updates)

    async def async_set_preset_pattern(
        self, effect: int, speed: int, brightness: int = 100
    ) -> None:
        """Set a preset pattern on the device."""
        self._set_transition_complete_time()
        await self._async_send_msg(
            self._generate_preset_pattern(effect, speed, brightness)
        )

    async def async_set_custom_pattern(
        self, rgb_list: List[Tuple[int, int, int]], speed: int, transition_type: str
    ) -> None:
        """Set a custom pattern on the device."""
        await self._async_send_msg(
            self._generate_custom_patterm(rgb_list, speed, transition_type)
        )

    async def async_set_effect(
        self, effect: str, speed: int, brightness: int = 100
    ) -> None:
        """Set an effect."""
        if effect == EFFECT_RANDOM:
            await self.async_set_random()
            return
        await self.async_set_preset_pattern(
            self._effect_to_pattern(effect), speed, brightness
        )

    async def async_set_random(self) -> None:
        """Set levels randomly."""
        await self._async_process_levels_change(*self._generate_random_levels_change())

    async def async_set_brightness(self, brightness: int) -> None:
        """Adjust brightness."""
        effect = self.effect
        if effect:
            effect_brightness = round(brightness / 255 * 100)
            await self.async_set_effect(effect, self.speed, effect_brightness)
            return
        if self.color_mode == COLOR_MODE_CCT:
            await self.async_set_white_temp(self.color_temp, brightness)
            return
        if self.color_mode == COLOR_MODE_RGB:
            await self.async_set_levels(*self.rgb_unscaled, brightness=brightness)
            return
        if self.color_mode == COLOR_MODE_RGBW:
            await self.async_set_levels(*rgbw_brightness(self.rgbw, brightness))
            return
        if self.color_mode == COLOR_MODE_RGBWW:
            await self.async_set_levels(*rgbww_brightness(self.rgbww, brightness))
            return
        if self.color_mode == COLOR_MODE_DIM:
            await self.async_set_levels(w=brightness)
            return

    async def _async_connect(self) -> None:
        """Create connection."""
        _, self._aio_protocol = await asyncio.wait_for(
            self.loop.create_connection(  # type: ignore
                lambda: AIOLEDENETProtocol(
                    self._async_data_recieved, self._async_connection_lost
                ),
                self.ipaddr,
                self.port,
            ),
            timeout=self.timeout,
        )

    def _async_connection_lost(self, exc: Optional[Exception]) -> None:
        """Called when the connection is lost."""
        self._aio_protocol = None
        self.set_unavailable()

    def _async_data_recieved(self, data: bytes) -> None:
        """New data on the socket."""
        assert self._protocol is not None
        assert self._aio_protocol is not None
        start_empty_buffer = not self._buffer
        self._buffer += data
        self._updates_without_response = 0
        msg_length = len(self._buffer)
        while msg_length:
            expected_length = self._protocol.expected_response_length(self._buffer)
            if msg_length < expected_length:
                # need more bytes
                return
            msg = self._buffer[:expected_length]
            self._buffer = self._buffer[expected_length:]
            msg_length = len(self._buffer)
            if not start_empty_buffer:
                _LOGGER.debug(
                    "%s <= Reassembled (%s) (%d)",
                    self._aio_protocol.peername,
                    " ".join(f"0x{x:02X}" for x in msg),
                    len(msg),
                )
            self._async_process_message(msg)

    def _async_process_message(self, msg: bytes) -> None:
        """Process a full message (maybe reassembled)."""
        if self._data_future and not self._data_future.done():
            self._data_future.set_result(msg)
            return
        assert self._protocol is not None
        self.set_available()
        assert self._updated_callback is not None
        prev_state = self.raw_state
        if self._protocol.is_valid_addressable_response(msg):
            self.process_addressable_response(msg)
        if self._protocol.is_valid_state_response(msg):
            self.process_state_response(msg)
        elif self._protocol.is_valid_power_state_response(msg):
            self.process_power_state_response(msg)
        else:
            return
        if self.raw_state == prev_state:
            return
        futures = self._on_futures if self.is_on else self._off_futures
        for future in futures:
            if not future.done():
                future.set_result(True)
        futures.clear()
        self._updated_callback()

    def process_addressable_response(self, msg: bytes) -> bool:
        assert self._aio_protocol is not None
        _LOGGER.debug(
            "%s <= Extracted response (%s) (%d)",
            self._aio_protocol.peername,
            " ".join(f"0x{x:02X}" for x in msg[10:-1]),
            len(msg[10:-1]),
        )
        return self.process_state_response(msg[10:-1])

    async def _async_send_msg(self, msg: bytearray) -> None:
        """Write a message on the socket."""
        if not self._aio_protocol:
            async with self._lock:
                await self._async_connect()
        assert self._aio_protocol is not None
        self._aio_protocol.write(msg)

    async def _async_determine_protocol(self) -> None:
        # determine the type of protocol based of first 2 bytes.
        for protocol_cls in PROTOCOL_PROBES:
            protocol = protocol_cls()
            assert isinstance(protocol, (ProtocolLEDENET8Byte, ProtocolLEDENETOriginal))
            self._protocol = protocol
            async with self._lock:
                await self._async_connect()
                assert self._aio_protocol is not None
                self._data_future = asyncio.Future()
                self._aio_protocol.write(protocol.construct_state_query())
                try:
                    full_msg = await asyncio.wait_for(
                        self._data_future, timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    self._aio_protocol.close()
                    continue
                if not protocol.is_valid_state_response(full_msg):
                    # We just sent a garage query which the old procotol
                    # cannot process, recycle the connection
                    self._aio_protocol.close()
                    continue
                self._set_protocol_from_msg(full_msg, protocol.name)
                self.process_state_response(full_msg)
                return
        raise RuntimeError("Cannot determine protocol")
