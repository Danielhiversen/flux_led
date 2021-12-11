import asyncio
import contextlib
import logging
import time
from typing import Callable, List, Optional, Tuple, cast

from .scanner import BulbScanner, FluxLEDDiscovery

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

    async def _async_run_scan(
        self,
        transport: asyncio.DatagramTransport,
        destination: Tuple[str, int],
        timeout: int,
        found_all_future: "asyncio.Future[bool]",
    ) -> None:
        """Send the scans."""
        self.send_discovery_messages(transport, destination)
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
            self.send_discovery_messages(transport, destination)

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
        await self._send_command_and_reboot(
            self.send_disable_remote_access_message, address, timeout
        )

    async def async_enable_remote_access(
        self,
        address: str,
        remote_access_host: str,
        remote_access_port: int,
        timeout: int = 5,
    ) -> None:
        """Enable remote access."""

        def _enable_remote_access_message(
            sender: asyncio.DatagramTransport, destination: Tuple[str, int]
        ) -> None:
            self.send_enable_remote_access_message(
                sender, destination, remote_access_host, remote_access_port
            )

        await self._send_command_and_reboot(
            _enable_remote_access_message, address, timeout
        )

    async def _send_command_and_reboot(
        self,
        msg_sender: Callable[[asyncio.DatagramTransport, Tuple[str, int]], None],
        address: str,
        timeout: int = 5,
    ) -> None:
        """Send a command and reboot."""
        sock = self._create_socket()
        destination = self._destination_from_address(address)
        response1 = asyncio.Event()
        response2 = asyncio.Event()

        def _on_response(data: bytes, addr: Tuple[str, int]) -> None:
            _LOGGER.debug("udp: %s <= %s", addr, data)
            if data.startswith(b"+ok"):
                if response1.is_set():
                    response2.set()
                else:
                    response1.set()

        transport_proto = await self.loop.create_datagram_endpoint(
            lambda: LEDENETDiscovery(
                destination=destination,
                on_response=_on_response,
            ),
            sock=sock,
        )
        transport = cast(asyncio.DatagramTransport, transport_proto[0])
        try:
            self.send_start_message(transport, destination)
            msg_sender(transport, destination)
            await asyncio.wait_for(response1.wait(), timeout=timeout)
            self.send_reboot_message(transport, destination)
            await asyncio.wait_for(response2.wait(), timeout=timeout)
        finally:
            transport.close()
