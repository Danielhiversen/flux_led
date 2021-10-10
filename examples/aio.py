import logging
import pprint
import asyncio

logging.basicConfig(level=logging.DEBUG)
from flux_led.aio import AIOWifiLedBulb


async def go():
    bulb = AIOWifiLedBulb("192.168.107.91")

    def _async_updated():
        pprint.pprint(["State Changed!", bulb.raw_state])

    await bulb.async_setup(_async_updated)
    while True:
        await bulb.async_turn_on()
        await asyncio.sleep(2)
        await bulb.async_update()
        await asyncio.sleep(2)
        await bulb.async_set_levels(255, 0, 0)
        await asyncio.sleep(2)
        await bulb.async_set_white_temp(2700, 255)
        await asyncio.sleep(2)
        await bulb.async_turn_off()
        await asyncio.sleep(2)


asyncio.run(go())
