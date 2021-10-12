import contextlib
import logging
import select
import socket
import time

_LOGGER = logging.getLogger(__name__)


class BulbScanner:

    DISCOVERY_PORT = 48899
    BROADCAST_FREQUENCY = 3
    RESPONSE_SIZE = 64
    DISCOVER_MESSAGE = b"HF-A11ASSISTHREAD"
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

    def _process_response(self, data, from_address, address, response_list):
        """Process a response.

        Returns True if processing should stop
        """
        if data is None:
            return
        if data == self.DISCOVER_MESSAGE:
            return
        data_split = data.decode("ascii").split(",")
        if len(data_split) < 3:
            return
        ipaddr = data_split[0]
        if ipaddr in response_list:
            return
        response_list[ipaddr] = {
            "ipaddr": ipaddr,
            "id": data_split[1],
            "model": data_split[2],
        }
        return ipaddr in (from_address, address)

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
            sock.sendto(self.DISCOVER_MESSAGE, destination)
            _LOGGER.debug("discover: %s => %s", destination, self.DISCOVER_MESSAGE)
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
                        _LOGGER.debug(
                            "discover: %s => %s", destination, self.DISCOVER_MESSAGE
                        )
                        sock.sendto(self.DISCOVER_MESSAGE, destination)
                    continue

                try:
                    data, addr = sock.recvfrom(self.RESPONSE_SIZE)
                    _LOGGER.debug("discover: %s <= %s", addr, data)
                except socket.timeout:
                    continue

                if self._process_response(data, addr, address, response_list):
                    found_all = True
                    break

        self.found_bulbs = response_list.values()
        return self.found_bulbs
