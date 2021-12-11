import asyncio
import logging
import pprint

from flux_led.aioscanner import AIOBulbScanner

logging.basicConfig(level=logging.DEBUG)


async def go():
    scanner = AIOBulbScanner()
    pprint.pprint(await scanner.async_disable_remote_access("192.168.106.198"))


asyncio.run(go())
