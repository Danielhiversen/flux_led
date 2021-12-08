import asyncio
from datetime import date
import logging
import select
import socket
import sys
import time
from typing import Dict, List, Optional, Tuple, Union

if sys.version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from typing_extensions import TypedDict

from .models_db import get_model_description

_LOGGER = logging.getLogger(__name__)


class FluxLEDDiscovery(TypedDict):
    """A flux led device."""

    ipaddr: str
    id: Optional[str]  # aka mac
    model: Optional[str]
    model_num: Optional[int]
    version_num: Optional[int]
    firmware_date: Optional[date]
    model_info: Optional[str]  # contains if IR (and maybe BL) if the device supports IR
    model_description: Optional[str]


def merge_discoveries(target: FluxLEDDiscovery, source: FluxLEDDiscovery) -> None:
    """Merge keys from a second discovery that may be missing from the first one."""
    for k, v in source.items():
        if target.get(k) is None:
            target[k] = v  # type: ignore[misc]


def _process_discovery_message(data: FluxLEDDiscovery, decoded_data: str) -> None:
    """Process response from b'HF-A11ASSISTHREAD'

    b'192.168.214.252,B4E842E10588,AK001-ZJ2145'
    """
    data_split = decoded_data.split(",")
    if len(data_split) < 3:
        return
    ipaddr = data_split[0]
    data.update(
        {
            "ipaddr": ipaddr,
            "id": data_split[1],
            "model": data_split[2],
        }
    )


def _process_version_message(data: FluxLEDDiscovery, decoded_data: str) -> None:
    """Process response from b'AT+LVER\r'

    b'+ok=07_06_20210106_ZG-BL\r'
    """
    version_data = decoded_data[4:].replace("\r", "")
    data_split = version_data.split("_")
    if len(data_split) < 2:
        return
    try:
        data["model_num"] = int(data_split[0], 16)
        data["version_num"] = int(data_split[1], 16)
    except ValueError:
        return
    assert data["model_num"] is not None
    data["model_description"] = get_model_description(data["model_num"])
    if len(data_split) < 3:
        return
    firmware_date = data_split[2]
    try:
        data["firmware_date"] = date(
            int(firmware_date[:4]),
            int(firmware_date[4:6]),
            int(firmware_date[6:8]),
        )
    except (TypeError, ValueError):
        return
    if len(data_split) < 4:
        return
    data["model_info"] = data_split[3]


class BulbScanner:

    DISCOVERY_PORT = 48899
    BROADCAST_FREQUENCY = 6  # At least 6 for 0xA1 models
    RESPONSE_SIZE = 64
    DISCOVER_MESSAGE = b"HF-A11ASSISTHREAD"
    VERSION_MESSAGE = b"AT+LVER\r"
    BROADCAST_ADDRESS = "<broadcast>"

    def __init__(self) -> None:
        self._discoveries: Dict[str, FluxLEDDiscovery] = {}

    @property
    def found_bulbs(self) -> List[FluxLEDDiscovery]:
        """Return only complete bulb discoveries."""
        return [info for info in self._discoveries.values() if info["id"]]

    def getBulbInfoByID(self, id: str) -> FluxLEDDiscovery:
        for b in self.found_bulbs:
            if b["id"] == id:
                return b
        return b

    def getBulbInfo(self) -> List[FluxLEDDiscovery]:
        return self.found_bulbs

    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", 0))
        sock.setblocking(False)
        return sock

    def _destination_from_address(self, address: Optional[str]) -> Tuple[str, int]:
        if address is None:
            address = self.BROADCAST_ADDRESS
        return (address, self.DISCOVERY_PORT)

    def _process_response(
        self,
        data: Optional[bytes],
        from_address: Tuple[str, int],
        address: Optional[str],
        response_list: Dict[str, FluxLEDDiscovery],
    ) -> bool:
        """Process a response.

        Returns True if processing should stop
        """
        if data is None:
            return False
        if data in (self.DISCOVER_MESSAGE, self.VERSION_MESSAGE):
            return False
        decoded_data = data.decode("ascii")
        self._process_data(from_address, decoded_data, response_list)
        if address is None or address not in response_list:
            return False
        return response_list[address]["model_num"] is not None

    def _process_data(
        self,
        from_address: Tuple[str, int],
        decoded_data: str,
        response_list: Dict[str, FluxLEDDiscovery],
    ) -> None:
        """Process data."""
        from_ipaddr = from_address[0]
        data = response_list.setdefault(
            from_ipaddr,
            FluxLEDDiscovery(
                ipaddr=from_ipaddr,
                id=None,
                model=None,
                model_num=None,
                version_num=None,
                firmware_date=None,
                model_info=None,
                model_description=None,
            ),
        )
        if decoded_data.startswith("+ok="):
            _process_version_message(data, decoded_data)
        elif "," in decoded_data:
            _process_discovery_message(data, decoded_data)

    def send_discovery_messages(
        self,
        sender: Union[socket.socket, asyncio.DatagramTransport],
        destination: Tuple[str, int],
    ) -> None:
        _LOGGER.debug("discover: %s => %s", destination, self.DISCOVER_MESSAGE)
        sender.sendto(self.DISCOVER_MESSAGE, destination)
        _LOGGER.debug("discover: %s => %s", destination, self.VERSION_MESSAGE)
        sender.sendto(self.VERSION_MESSAGE, destination)

    def scan(
        self, timeout: int = 10, address: Optional[str] = None
    ) -> List[FluxLEDDiscovery]:
        """Scan for bulbs.

        If an address is provided, the scan will return
        as soon as it gets a response from that address
        """
        sock = self._create_socket()
        destination = self._destination_from_address(address)
        # set the time at which we will quit the search
        quit_time = time.monotonic() + timeout
        found_all = False
        # outer loop for query send
        while not found_all:
            if time.monotonic() > quit_time:
                break
            # send out a broadcast query
            self.send_discovery_messages(sock, destination)
            # inner loop waiting for responses
            while True:
                sock.settimeout(1)
                remain_time = quit_time - time.monotonic()
                time_out = min(remain_time, timeout / self.BROADCAST_FREQUENCY)
                if time_out <= 0:
                    break
                read_ready, _, _ = select.select([sock], [], [], time_out)
                if not read_ready:
                    if time.monotonic() < quit_time:
                        # No response, send broadcast again in cast it got lost
                        self.send_discovery_messages(sock, destination)
                    continue

                try:
                    data, addr = sock.recvfrom(self.RESPONSE_SIZE)
                    _LOGGER.debug("discover: %s <= %s", addr, data)
                except socket.timeout:
                    continue

                if self._process_response(data, addr, address, self._discoveries):
                    found_all = True
                    break

        return self.found_bulbs
