import asyncio
import logging
import time

from .scanner import BulbScanner

_LOGGER = logging.getLogger(__name__)


MAX_UPDATES_WITHOUT_RESPONSE = 4


class LEDENETDiscovery(asyncio.DatagramProtocol):
    def __init__(self, destination, on_response):
        self.transport = None
        self.destination = destination
        self.on_response = on_response

    def datagram_received(self, data, addr) -> None:
        """Trigger on_response."""
        self.on_response(data, addr)

    def error_received(self, ex):
        """Handle error."""
        _LOGGER.error("LEDENETDiscovery error: %s", ex)

    def connection_lost(self, ex):
        pass


class AIOBulbScanner(BulbScanner):
    """A LEDENET discovery scanner."""

    def __init__(self):
        self.loop = asyncio.get_running_loop()
        super().__init__()

    async def _async_run_scan(self, transport, destination, timeout, found_all_future):
        """Send the scans."""
        _LOGGER.debug("discover: %s => %s", destination, self.DISCOVER_MESSAGE)
        transport.sendto(self.DISCOVER_MESSAGE, destination)
        transport.sendto(self.VERSION_MESSAGE, destination)
        quit_time = time.monotonic() + timeout
        remain_time = timeout
        while True:
            time_out = min(remain_time, timeout / self.BROADCAST_FREQUENCY)
            if time_out <= 0:
                return
            try:
                await asyncio.wait_for(
                    asyncio.shield(found_all_future), timeout=time_out
                )
            except asyncio.TimeoutError:
                if time.monotonic() >= quit_time:
                    return
                # No response, send broadcast again in cast it got lost
                _LOGGER.debug("discover: %s => %s", destination, self.DISCOVER_MESSAGE)
                transport.sendto(self.DISCOVER_MESSAGE, destination)
                transport.sendto(self.VERSION_MESSAGE, destination)
            else:
                return  # found_all
            remain_time = quit_time - time.monotonic()

    async def async_scan(self, timeout=10, address=None):
        """Discover LEDENET."""
        sock = self._create_socket()
        destination = self._destination_from_address(address)
        found_all_future = asyncio.Future()
        response_list = {}

        def _on_response(data, addr):
            _LOGGER.debug("discover: %s <= %s", addr, data)
            if self._process_response(data, addr, address, response_list):
                found_all_future.set_result(True)

        transport, _ = await self.loop.create_datagram_endpoint(
            lambda: LEDENETDiscovery(
                destination=destination,
                on_response=_on_response,
            ),
            sock=sock,
        )
        try:
            await self._async_run_scan(
                transport, destination, timeout, found_all_future
            )
        finally:
            transport.close()

        self.found_bulbs = self._found_bulbs(response_list)
        return list(self.found_bulbs)
