import logging
import select
import socket
import time

_LOGGER = logging.getLogger(__name__)


class BulbScanner:

    DISCOVERY_PORT = 48899
    BROADCAST_FREQUENCY = 3
    RESPONSE_SIZE = 64
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

    def scan(self, timeout=10, address=None):
        """Scan for bulbs.

        If an address is provided, the scan will return
        as soon as it gets a response from that address
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", self.DISCOVERY_PORT))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        if address is None:
            address = self.BROADCAST_ADDRESS
        destination = (address, self.DISCOVERY_PORT)

        msg = "HF-A11ASSISTHREAD".encode("ascii")

        # set the time at which we will quit the search
        quit_time = time.monotonic() + timeout
        seen = set()
        response_list = []
        found_all = False
        # outer loop for query send
        while not found_all:
            if time.monotonic() > quit_time:
                break
            # send out a broadcast query
            sock.sendto(msg, destination)
            _LOGGER.debug("discover: %s => %s", destination, msg)

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
                        _LOGGER.debug("discover: %s => %s", destination, msg)
                        sock.sendto(msg, destination)
                    continue

                try:
                    data, addr = sock.recvfrom(self.RESPONSE_SIZE)
                    _LOGGER.debug("discover: %s <= %s", addr, data)
                except socket.timeout:
                    continue
                if data is None:
                    continue
                if data == msg:
                    continue

                data_split = data.decode("ascii").split(",")
                if len(data_split) < 3:
                    continue
                if data_split[0] in seen:
                    continue
                seen.add(data_split[0])
                response_list.append(
                    {
                        "ipaddr": data_split[0],
                        "id": data_split[1],
                        "model": data_split[2],
                    }
                )
                if address == data_split[0]:
                    found_all = True
                    break

        self.found_bulbs = response_list
        return response_list
