import contextlib
from datetime import date
import logging
import select
import socket
import sys
import time
from typing import cast

if sys.version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from typing_extensions import TypedDict

from .const import (
    ATTR_FIRMWARE_DATE,
    ATTR_ID,
    ATTR_IPADDR,
    ATTR_MODEL,
    ATTR_MODEL_DESCRIPTION,
    ATTR_MODEL_INFO,
    ATTR_MODEL_NUM,
    ATTR_VERSION_NUM,
)
from .models_db import get_model_description

_LOGGER = logging.getLogger(__name__)


def _process_discovery_message(data, decoded_data):
    """Process response from b'HF-A11ASSISTHREAD'

    b'192.168.214.252,B4E842E10588,AK001-ZJ2145'
    """
    data_split = decoded_data.split(",")
    if len(data_split) < 3:
        return
    ipaddr = data_split[0]
    data.update(
        {
            ATTR_IPADDR: ipaddr,
            ATTR_ID: data_split[1],
            ATTR_MODEL: data_split[2],
        }
    )


def _process_version_message(data, decoded_data):
    """Process response from b'AT+LVER\r'

    b'+ok=07_06_20210106_ZG-BL\r'
    """
    version_data = decoded_data[4:].replace("\r", "")
    data_split = version_data.split("_")
    if len(data_split) < 2:
        return
    try:
        data[ATTR_MODEL_NUM] = int(data_split[0], 16)
        data[ATTR_VERSION_NUM] = int(data_split[1], 16)
    except ValueError:
        return
    data[ATTR_MODEL_DESCRIPTION] = get_model_description(data[ATTR_MODEL_NUM])
    if len(data_split) < 3:
        return
    firmware_date = data_split[2]
    try:
        data[ATTR_FIRMWARE_DATE] = date(
            int(firmware_date[:4]),
            int(firmware_date[4:6]),
            int(firmware_date[6:8]),
        )
    except (TypeError, ValueError):
        return
    if len(data_split) < 4:
        return
    data[ATTR_MODEL_INFO] = data_split[3]


class FluxLEDDiscovery(TypedDict):
    """A flux led device."""

    ipaddr: str
    id: str  # aka mac
    model: str
    model_num: int
    version_num: int
    firmware_date: date
    model_info: str
    model_description: str


class BulbScanner:

    DISCOVERY_PORT = 48899
    BROADCAST_FREQUENCY = (
        5  # At least 5 for A1 models (Magic Home Branded RGB Symphony [Addressable])
    )
    RESPONSE_SIZE = 64
    DISCOVER_MESSAGE = b"HF-A11ASSISTHREAD"
    VERSION_MESSAGE = b"AT+LVER\r"
    BROADCAST_ADDRESS = "<broadcast>"

    def __init__(self):
        self.found_bulbs = []

    def getBulbInfoByID(self, id):
        for b in self.found_bulbs:
            if b["id"] == id:
                return b
        return b

    def getBulbInfo(self):
        return self.found_bulbs

    def _create_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with contextlib.suppress(Exception):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind(("", self.DISCOVERY_PORT))
        sock.setblocking(0)
        return sock

    def _destination_from_address(self, address):
        if address is None:
            address = self.BROADCAST_ADDRESS
        return (address, self.DISCOVERY_PORT)

    def _process_response(self, data, from_address, address, response_list) -> bool:
        """Process a response.

        Returns True if processing should stop
        """
        if data is None:
            return False
        if data in (self.DISCOVER_MESSAGE, self.VERSION_MESSAGE):
            return False
        decoded_data = data.decode("ascii")
        self._process_data(from_address, decoded_data, response_list)
        if address is None:
            return False
        return response_list.get(address, {}).get(ATTR_MODEL_NUM) is not None

    def _process_data(self, from_address, decoded_data, response_list):
        """Process data."""
        from_ipaddr = from_address[0]
        data = response_list.setdefault(from_ipaddr, {})
        if decoded_data.startswith("+ok="):
            _process_version_message(data, decoded_data)
        elif "," in decoded_data:
            _process_discovery_message(data, decoded_data)

    def _found_bulbs(self, response_list):
        """Return only complete bulb discoveries."""

        return [
            cast(FluxLEDDiscovery, info)
            for info in response_list.values()
            if info.get(ATTR_IPADDR)
        ]

    def send_discovery_messages(self, sender, destination):
        _LOGGER.debug("discover: %s => %s", destination, self.DISCOVER_MESSAGE)
        sender.sendto(self.DISCOVER_MESSAGE, destination)
        _LOGGER.debug("discover: %s => %s", destination, self.VERSION_MESSAGE)
        sender.sendto(self.VERSION_MESSAGE, destination)

    def scan(self, timeout=10, address=None):
        """Scan for bulbs.

        If an address is provided, the scan will return
        as soon as it gets a response from that address
        """
        sock = self._create_socket()
        destination = self._destination_from_address(address)
        # set the time at which we will quit the search
        quit_time = time.monotonic() + timeout
        response_list = {}
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

                if self._process_response(data, addr, address, response_list):
                    found_all = True
                    break

        self.found_bulbs = self._found_bulbs(response_list)
        return self.found_bulbs
