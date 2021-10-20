import asyncio
import logging
import pprint

from flux_led.aioscanner import AIOBulbScanner

logging.basicConfig(level=logging.DEBUG)


async def go():
    scanner = AIOBulbScanner()
    pprint.pprint(await scanner.async_scan())


asyncio.run(go())
