import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


class AIOLEDENETProtocol(asyncio.Protocol):
    """A asyncio.Protocol implementing a wrapper around the LEDENET protocol."""

    def __init__(self, data_received, connection_lost) -> None:
        self._data_receive_callback = data_received
        self._connection_lost_callback = connection_lost
        self.transport = None

    def connection_lost(self, exc: Exception) -> None:
        """Handle connection lost."""
        _LOGGER.debug("%s: Connection lost: %s", self.peername, exc)
        self.close()
        self._connection_lost_callback(exc)

    def connection_made(self, transport: asyncio.Transport) -> None:
        """Handle connection made."""
        self.transport = transport
        self.peername = transport.get_extra_info("peername")

    def write(self, data: bytes) -> None:
        """Write data to the client."""
        _LOGGER.debug(
            "%s => %s (%d)",
            self.peername,
            " ".join(f"0x{x:02X}" for x in data),
            len(data),
        )
        self.transport.write(data)

    def close(self) -> None:
        """Remove the connection and close the transport."""
        self.transport.write_eof()
        self.transport.close()

    def data_received(self, data: bytes) -> None:
        """Process new data from the socket."""
        _LOGGER.debug(
            "%s <= %s (%d)",
            self.peername,
            " ".join(f"0x{x:02X}" for x in data),
            len(data),
        )
        self._data_receive_callback(data)
