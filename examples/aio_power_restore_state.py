import asyncio
import logging
import pprint

from flux_led.aio import AIOWifiLedBulb
from flux_led.protocol import PowerRestoreState

logging.basicConfig(level=logging.DEBUG)


async def go():
    socket = AIOWifiLedBulb("192.168.213.66")

    def _async_updated():
        pprint.pprint(["State Changed!", socket.raw_state])

    await socket.async_setup(_async_updated)
    await asyncio.sleep(1)
    pprint.pprint(["Current restore states", socket.power_restore_states])

    pprint.pprint("Setting power restore state to restore on power lost")
    await socket.async_set_power_restore(channel1=PowerRestoreState.LAST_STATE)

    pprint.pprint(["Current restore states", socket.power_restore_states])


asyncio.run(go())
