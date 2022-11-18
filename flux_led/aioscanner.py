import asyncio
import contextlib
import logging
import time
from typing import Callable, Dict, List, Optional, Tuple, cast

from .scanner import MESSAGE_SEND_INTERLEAVE_DELAY, BulbScanner, FluxLEDDiscovery

_LOGGER = logging.getLogger(__name__)


class LEDENETDiscovery(asyncio.DatagramProtocol):
    def __init__(
        self,
        destination: Tuple[str, int],
        on_response: Callable[[bytes, Tuple[str, int]], None],
    ) -> None:
        """Init the discovery protocol."""
        self.transport = None
        self.destination = destination
        self.on_response = on_response

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Trigger on_response."""
        self.on_response(data, addr)

    def error_received(self, ex: Optional[Exception]) -> None:
        """Handle error."""
        _LOGGER.debug("LEDENETDiscovery error: %s", ex)

    def connection_lost(self, ex: Optional[Exception]) -> None:
        """The connection is lost."""


class AIOBulbScanner(BulbScanner):
    """A LEDENET discovery scanner."""

    def __init__(self) -> None:
        self.loop = asyncio.get_running_loop()
        super().__init__()

    async def _async_send_messages(
        self,
        messages: List[bytes],
        sender: asyncio.DatagramTransport,
        destination: Tuple[str, int],
    ) -> None:
        """Send messages with a short delay between them."""
        last_idx = len(messages) - 1
        for idx, message in enumerate(messages):
            self._send_message(sender, destination, message)
            if idx != last_idx:
                await asyncio.sleep(MESSAGE_SEND_INTERLEAVE_DELAY)

    async def _async_send_and_wait(
        self,
        events: List[asyncio.Event],
        commands: List[bytes],
        transport: asyncio.DatagramTransport,
        destination: Tuple[str, int],
        timeout: int,
    ) -> None:
        """Send a message and wait for a response."""
        event_map: Dict[int, asyncio.Event] = {}
        for idx, _ in enumerate(commands):
            event = asyncio.Event()
            event_map[idx] = event
            events.append(event)
        for idx, command in enumerate(commands):
            self._send_message(transport, destination, command)
            await asyncio.wait_for(event_map[idx].wait(), timeout=timeout)

    async def _async_send_commands_and_reboot(
        self,
        messages: Optional[List[bytes]],
        address: str,
        timeout: int = 5,
    ) -> None:
        """Send a command and reboot."""
        sock = self._create_socket()
        destination = self._destination_from_address(address)
        events: List[asyncio.Event] = []

        def _on_response(data: bytes, addr: Tuple[str, int]) -> None:
            _LOGGER.debug("udp: %s <= %s", addr, data)
            if data.startswith(b"+ok"):
                events.pop(0).set()

        transport_proto = await self.loop.create_datagram_endpoint(
            lambda: LEDENETDiscovery(
                destination=destination,
                on_response=_on_response,
            ),
            sock=sock,
        )
        transport = cast(asyncio.DatagramTransport, transport_proto[0])
        commands: List[bytes] = []
        if messages:
            commands.extend(messages)
        commands.extend(self._get_reboot_messages())
        try:
            await self._async_send_messages(
                self._get_start_messages(), transport, destination
            )
            await self._async_send_and_wait(
                events, commands, transport, destination, timeout
            )
        finally:
            transport.close()

    async def _async_run_scan(
        self,
        transport: asyncio.DatagramTransport,
        destination: Tuple[str, int],
        timeout: int,
        found_all_future: "asyncio.Future[bool]",
    ) -> None:
        """Send the scans."""
        discovery_messages = self.get_discovery_messages()
        await self._async_send_messages(discovery_messages, transport, destination)
        quit_time = time.monotonic() + timeout
        time_out = timeout / self.BROADCAST_FREQUENCY
        while True:
            try:
                await asyncio.wait_for(
                    asyncio.shield(found_all_future), timeout=time_out
                )
            except asyncio.TimeoutError:
                pass
            else:
                return  # found_all
            time_out = min(
                quit_time - time.monotonic(), timeout / self.BROADCAST_FREQUENCY
            )
            if time_out <= 0:
                return
            # No response, send broadcast again in cast it got lost
            await self._async_send_messages(discovery_messages, transport, destination)

    async def async_scan(
        self, timeout: int = 10, address: Optional[str] = None
    ) -> List[FluxLEDDiscovery]:
        """Discover LEDENET."""
        sock = self._create_socket()
        destination = self._destination_from_address(address)
        found_all_future: "asyncio.Future[bool]" = asyncio.Future()

        def _on_response(data: bytes, addr: Tuple[str, int]) -> None:
            _LOGGER.debug("discover: %s <= %s", addr, data)
            if self._process_response(data, addr, address, self._discoveries):
                with contextlib.suppress(asyncio.InvalidStateError):
                    found_all_future.set_result(True)

        transport_proto = await self.loop.create_datagram_endpoint(
            lambda: LEDENETDiscovery(
                destination=destination,
                on_response=_on_response,
            ),
            sock=sock,
        )
        transport = cast(asyncio.DatagramTransport, transport_proto[0])
        try:
            await self._async_run_scan(
                transport, destination, timeout, found_all_future
            )
        finally:
            transport.close()

        return self.found_bulbs

    async def async_disable_remote_access(self, address: str, timeout: int = 5) -> None:
        """Disable remote access."""
        await self._async_send_commands_and_reboot(
            self._get_disable_remote_access_messages(), address, timeout
        )

    async def async_enable_remote_access(
        self,
        address: str,
        remote_access_host: str,
        remote_access_port: int,
        timeout: int = 5,
    ) -> None:
        """Enable remote access."""
        await self._async_send_commands_and_reboot(
            self._get_enable_remote_access_messages(
                remote_access_host, remote_access_port
            ),
            address,
            timeout,
        )

    async def async_reboot(self, address: str, timeout: int = 5) -> None:
        """Reboot the device."""
        await self._async_send_commands_and_reboot(None, address, timeout)
