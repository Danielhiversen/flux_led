import asyncio
import logging
import pprint

from flux_led.aio import AIOWifiLedBulb
from flux_led.const import MultiColorEffects

logging.basicConfig(level=logging.DEBUG)


async def go():
    bulb = AIOWifiLedBulb("192.168.106.118")

    def _async_updated():
        pprint.pprint(["State Changed!", bulb.raw_state])

    await bulb.async_setup(_async_updated)
    while True:

        pprint.pprint("Setting to red/orange/yellow/green/blue/indigo/violet - static")
        await bulb.async_set_zones(
            [
                (0xFF, 0x00, 0x00),  # red
                (0xFF, 0xA5, 0x00),  # orange
                (0xFF, 0xFF, 0x00),  # yellow
                (0x00, 0xFF, 0x00),  # green
                (0x00, 0x00, 0xFF),  # blue
                (0x4B, 0x00, 0x82),  # indigo
                (0xEE, 0x82, 0xEE),  # violet
            ],
            100,
            MultiColorEffects.STATIC,
        )
        await asyncio.sleep(5)

        pprint.pprint("Setting to white/green - static")
        await bulb.async_set_zones(
            [(255, 255, 255), (0, 255, 0)], 100, MultiColorEffects.STATIC
        )
        await asyncio.sleep(5)

        pprint.pprint("Setting to red/blue - static")
        await bulb.async_set_zones(
            [(255, 0, 0), (0, 0, 255)], 100, MultiColorEffects.STATIC
        )
        await asyncio.sleep(5)

        pprint.pprint("Setting to white/blue - running water")
        await bulb.async_set_zones(
            [(255, 255, 255), (0, 0, 255)], 100, MultiColorEffects.RUNNING_WATER
        )
        await asyncio.sleep(5)

        pprint.pprint("Setting to white/blue - breathing")
        await bulb.async_set_zones(
            [(255, 255, 255), (0, 0, 255)], 100, MultiColorEffects.BREATHING
        )
        await asyncio.sleep(5)

        pprint.pprint("Setting to white/green - jump")
        await bulb.async_set_zones(
            [(255, 255, 255), (0, 255, 0)], 100, MultiColorEffects.JUMP
        )
        await asyncio.sleep(5)

        pprint.pprint("Setting to red/blue - strobe")
        await bulb.async_set_zones(
            [(255, 0, 0), (0, 0, 255)], 100, MultiColorEffects.STROBE
        )
        await asyncio.sleep(5)

        pprint.pprint(
            "Setting to red/orange/yellow/green/blue/indigo/violet - running water"
        )
        await bulb.async_set_zones(
            [
                (0xFF, 0x00, 0x00),  # red
                (0xFF, 0xA5, 0x00),  # orange
                (0xFF, 0xFF, 0x00),  # yellow
                (0x00, 0xFF, 0x00),  # green
                (0x00, 0x00, 0xFF),  # blue
                (0x4B, 0x00, 0x82),  # indigo
                (0xEE, 0x82, 0xEE),  # violet
            ],
            100,
            MultiColorEffects.RUNNING_WATER,
        )
        await asyncio.sleep(5)


asyncio.run(go())
