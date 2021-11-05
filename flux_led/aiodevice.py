import asyncio
import contextlib
import logging
from typing import Callable, Coroutine, Optional

from .aioprotocol import AIOLEDENETProtocol
from .const import (
    STATE_BLUE,
    STATE_COOL_WHITE,
    STATE_GREEN,
    STATE_RED,
    STATE_WARM_WHITE,
)
from .device import LEDENETDevice
from .protocol import ProtocolLEDENET8Byte, ProtocolLEDENETOriginal
from .utils import color_temp_to_white_levels

_LOGGER = logging.getLogger(__name__)


MAX_UPDATES_WITHOUT_RESPONSE = 4
POWER_STATE_TIMEOUT = 1  # number of seconds before declaring on/off failed


class AIOWifiLedBulb(LEDENETDevice):
    """A LEDENET Wifi bulb device."""

    def __init__(self, ipaddr, port=5577, timeout=5):
        """Init and setup the bulb."""
        super().__init__(ipaddr, port, timeout)
        self._lock = asyncio.Lock()
        self._aio_protocol: Optional[AIOLEDENETProtocol] = None
        self._on_futures: list[asyncio.Future] = []
        self._off_futures: list[asyncio.Future] = []
        self._data_future: Optional[asyncio.Future] = None
        self._updated_callback: Optional[Callable] = None
        self._updates_without_response = 0
        self._buffer = b""
        self.loop = asyncio.get_running_loop()

    async def async_setup(self, updated_callback):
        """Setup the connection and fetch initial state."""
        self._updated_callback = updated_callback
        await self._async_determine_protocol()

    async def async_stop(self):
        """Shutdown the connection"""
        if self._aio_protocol:
            self._aio_protocol.close()

    async def _async_execute_and_wait_for(
        self, futures: list[asyncio.Future], coro: Coroutine
    ) -> None:
        future = asyncio.Future()
        futures.append(future)
        await coro()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(future), POWER_STATE_TIMEOUT / 2)
            return True
        await self._async_send_msg(self._protocol.construct_state_query())
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(future, POWER_STATE_TIMEOUT / 2)
            return True
        return False

    async def _async_turn_on(self) -> None:
        await self._async_send_msg(self._protocol.construct_state_change(True))

    async def _async_turn_off_on(self) -> None:
        await self._async_turn_off()
        await self._async_turn_on()

    async def async_turn_on(self) -> None:
        """Turn on the device."""
        await self._async_turn_on_with_retry()
        self._set_power_state_ignore_next_push(self._protocol.on_byte)

    async def _async_turn_on_with_retry(self) -> None:
        calls = (self._async_turn_on, self._async_turn_off_on, self._async_turn_on)
        for idx, call in enumerate(calls):
            if (
                await self._async_execute_and_wait_for(self._on_futures, call)
                or self.is_on
            ):
                return
            _LOGGER.debug("Failed to turn on (%s/%s)", 1 + idx, len(calls))

    async def _async_turn_off(self) -> None:
        await self._async_send_msg(self._protocol.construct_state_change(False))

    async def _async_turn_on_off(self) -> None:
        await self._async_turn_on()
        await self._async_turn_off()

    async def async_turn_off(self) -> None:
        """Turn off the device."""
        await self._async_turn_off_with_retry()
        self._set_power_state_ignore_next_push(self._protocol.off_byte)

    async def _async_turn_off_with_retry(self) -> None:
        calls = (self._async_turn_off, self._async_turn_on_off, self._async_turn_off)
        for idx, call in enumerate(calls):
            if (
                await self._async_execute_and_wait_for(self._off_futures, call)
                or not self.is_on
            ):
                return
            _LOGGER.debug("Failed to turn off (%s/%s)", 1 + idx, len(calls))

    async def async_set_white_temp(self, temperature, brightness, persist=True) -> None:
        """Set the white tempature."""
        cold, warm = color_temp_to_white_levels(temperature, brightness)
        await self.async_set_levels(w=warm, w2=cold, persist=persist)

    async def async_update(self):
        """Request an update.

        The callback will be triggered when the state is recieved.
        """
        if self._updates_without_response == MAX_UPDATES_WITHOUT_RESPONSE:
            if self._aio_protocol:
                self._aio_protocol.close()
            self._updates_without_response = 0
            raise RuntimeError("Bulb stopped responding")
        await self._async_send_msg(self._protocol.construct_state_query())
        self._updates_without_response += 1

    async def async_set_levels(
        self,
        r=None,
        g=None,
        b=None,
        w=None,
        w2=None,
        persist=True,
        brightness=None,
    ):
        """Set any of the levels."""
        msg, updates = self._generate_levels_change(
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
        self._set_transition_complete_time()
        await self._async_send_msg(msg)
        if updates:
            self._replace_raw_state(updates)

    async def async_set_preset_pattern(self, effect, speed):
        """Set a preset pattern on the device."""
        msg = self._generate_preset_pattern(effect, speed)
        await self._async_send_msg(msg)

    async def async_set_custom_pattern(self, rgb_list, speed, transition_type):
        """Set a custom pattern on the device."""
        msg = self._generate_custom_patterm(rgb_list, speed, transition_type)
        await self._async_send_msg(msg)

    async def _async_connect(self):
        """Create connection."""
        _, self._aio_protocol = await asyncio.wait_for(
            self.loop.create_connection(
                lambda: AIOLEDENETProtocol(
                    self._async_data_recieved, self._async_connection_lost
                ),
                self.ipaddr,
                self.port,
            ),
            timeout=self.timeout,
        )

    def _async_connection_lost(self, exc):
        """Called when the connection is lost."""
        self._aio_protocol = None

    def _async_data_recieved(self, data):
        """New data on the socket."""
        start_empty_buffer = not self._buffer
        self._buffer += data
        self._updates_without_response = 0
        # Some of the older bulbs respond to a state request in
        # multiple packets so we have to reassemble.  Currently
        # we only know how to reassemble state responses
        if (
            # if the buffer has the start of a state response
            self._protocol.is_start_of_state_response(self._buffer)
            # If the buffer does not have a full state response
            and not self._protocol.is_valid_state_response(self._buffer)
            # .. and the buffer is not longer than the a valid state response
            and not self._protocol.is_longer_than_state_response(self._buffer)
        ):
            # We wait for more data. Otherwise we process the message
            return
        msg = self._buffer
        self._buffer = b""
        if not start_empty_buffer:
            _LOGGER.debug(
                "%s <= Reassembled (%s) (%d)",
                self._aio_protocol.peername,
                " ".join(f"0x{x:02X}" for x in msg),
                len(msg),
            )
        self._async_process_message(msg)

    def _async_process_message(self, msg):
        """Process a full message (maybe reassembled)."""
        if self._data_future and not self._data_future.done():
            self._data_future.set_result(msg)
            return
        if not self._protocol:
            return
        assert self._updated_callback is not None
        prev_state = self.raw_state
        if self._protocol.is_valid_state_response(msg):
            self.process_state_response(msg)
        elif self._protocol.is_valid_power_state_response(msg):
            self.process_power_state_response(msg)
        else:
            return
        if self.raw_state != prev_state:
            futures = self._on_futures if self.is_on else self._off_futures
            for future in futures:
                if not future.done():
                    future.set_result(True)
            futures.clear()
            self._updated_callback()

    async def _async_send_msg(self, msg):
        """Write a message on the socket."""
        if not self._aio_protocol:
            async with self._lock:
                await self._async_connect()
        self._aio_protocol.write(msg)

    async def _async_determine_protocol(self):
        # determine the type of protocol based of first 2 bytes.
        for protocol_cls in (ProtocolLEDENET8Byte, ProtocolLEDENETOriginal):
            self._protocol = protocol = protocol_cls()
            async with self._lock:
                await self._async_connect()
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
                self._set_protocol_from_msg(full_msg, protocol)
                self.process_state_response(full_msg)
                return
        raise RuntimeError("Cannot determine protocol")
