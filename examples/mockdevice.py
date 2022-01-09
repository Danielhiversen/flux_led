import asyncio
import logging
import pprint
import socket

from typing import Tuple, Optional
from flux_led.aio import AIOWifiLedBulb
from flux_led.aioscanner import AIOBulbScanner

logging.basicConfig(level=logging.DEBUG)

_LOGGER = logging.getLogger(__name__)

DEVICE_ID = 0x25


def get_local_ip():
    """Find the local ip address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setblocking(False)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


class MagicHomeDiscoveryProtocol(asyncio.Protocol):
    """A asyncio.Protocol implementing the MagicHome discovery protocol."""

    def __init__(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.local_ip = get_local_ip()
        self.transport: Optional[asyncio.BaseTransport] = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Trigger on data."""
        _LOGGER.debug(
            "%s <= %s (%d)",
            addr,
            " ".join(f"0x{x:02X}" for x in data),
            len(data),
        )
        assert self.transport is not None
        if data.startswith(AIOBulbScanner.DISCOVER_MESSAGE):
            self.transport.sendto(
                f"{self.local_ip},B4E842123456,AK001-ZJ2149".encode(), addr
            )
        if data.startswith(AIOBulbScanner.VERSION_MESSAGE):
            model_str = hex(DEVICE_ID)[2:].zfill(2)
            self.transport.sendto(f"+ok={model_str}_33_20200428_ZG-LX\r", addr)

    def error_received(self, ex: Optional[Exception]) -> None:
        """Handle error."""
        _LOGGER.debug("LEDENETDiscovery error: %s", ex)

    def connection_lost(self, ex: Optional[Exception]) -> None:
        """The connection is lost."""


class MagichomeServerProtocol(asyncio.Protocol):
    """A asyncio.Protocol implementing the MagicHome protocol."""

    def __init__(self, loop) -> None:
        self.loop = asyncio.get_running_loop()
        self.handler = None
        self.peername = None
        self.transport: Optional[asyncio.BaseTransport] = None

    def connection_lost(self, exc: Exception) -> None:
        """Handle connection lost."""

    def connection_made(self, transport: asyncio.Transport) -> None:
        """Handle incoming connection."""
        self.peername = transport.get_extra_info("peername")
        self.transport = transport
        _LOGGER.debug("%s: Connection made", self.peername)

    def data_received(self, data: bytes) -> None:
        """Process new data from the socket."""
        _LOGGER.debug(
            "%s <= %s (%d)",
            self.peername,
            " ".join(f"0x{x:02X}" for x in data),
            len(data),
        )


async def go():
    loop = asyncio.get_running_loop()
    bulb_server = await loop.create_server(
        lambda: MagichomeServerProtocol(),
        port=5577,
    )
    bulb_discovery_server = await loop.create_datagram_endpoint(
        lambda: MagicHomeDiscoveryProtocol(),
        local_addr=("", AIOBulbScanner.DISCOVERY_PORT),
    )
    await asyncio.sleep(500)


asyncio.run(go())
