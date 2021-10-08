import logging
import pprint
import asyncio

logging.basicConfig(level=logging.DEBUG)
from flux_led.aioscanner import AIOBulbScanner


async def go():
    scanner = AIOBulbScanner()
    pprint.pprint(await scanner.async_scan())


asyncio.run(go())
