import asyncio
import logging
import pprint

from flux_led.aio import AIOWifiLedBulb
from flux_led.aioscanner import AIOBulbScanner

logging.basicConfig(level=logging.DEBUG)

IPADDR = "192.168.106.210"


async def go():
    scanner = AIOBulbScanner()
    discovery = await scanner.async_scan(address=IPADDR)
    bulb = AIOWifiLedBulb(IPADDR)
    bulb.discovery = discovery[0]

    def _async_updated():
        pprint.pprint(["State Changed!", bulb.raw_state])

    await bulb.async_setup(_async_updated)
    await bulb.async_update()
    await bulb.async_tasmotize()


asyncio.run(go())
