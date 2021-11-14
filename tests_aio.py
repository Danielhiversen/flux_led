import asyncio
from unittest.mock import MagicMock, patch

import pytest
import contextlib

from flux_led import aiodevice
from flux_led.aio import AIOWifiLedBulb
from flux_led.aioprotocol import AIOLEDENETProtocol
from flux_led.const import COLOR_MODE_CCT, COLOR_MODE_RGBWW
from flux_led.protocol import PROTOCOL_LEDENET_9BYTE


@pytest.fixture
async def mock_aio_protocol():
    """Fixture to mock an asyncio connection."""
    loop = asyncio.get_running_loop()
    future = asyncio.Future()

    async def _wait_for_connection():
        await future
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    async def _mock_create_connection(func, ip, port):
        protocol: AIOLEDENETProtocol = func()
        transport = MagicMock()
        protocol.connection_made(transport)
        with contextlib.suppress(asyncio.InvalidStateError):
            future.set_result(True)
        return transport, protocol

    with patch.object(loop, "create_connection", _mock_create_connection):
        yield _wait_for_connection


@pytest.mark.asyncio
async def test_reassemble(mock_aio_protocol):
    """Test we can reassemble."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xde"
    )
    await task
    assert light.color_modes == {COLOR_MODE_RGBWW, COLOR_MODE_CCT}
    assert light.protocol == PROTOCOL_LEDENET_9BYTE
    assert light.model_num == 0x25
    assert light.model == "WiFi RGBCW Controller (0x25)"
    assert light.is_on is True
    assert len(light.effect_list) == 20

    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xde"
        b"\x81\x25\x24\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xdf"
    )
    await asyncio.sleep(0)
    assert light.is_on is False

    light._aio_protocol.data_received(b"\x81")
    light._aio_protocol.data_received(
        b"\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f"
    )
    light._aio_protocol.data_received(b"\xde")
    await asyncio.sleep(0)
    assert light.is_on is True


@pytest.mark.asyncio
async def test_turn_on_off(mock_aio_protocol):
    """Test we can turn on and off."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xde"
    )
    await task

    task = asyncio.create_task(light.async_turn_off())
    # Wait for the future to get added
    await asyncio.sleep(0)
    light._aio_protocol.data_received(
        b"\x81\x25\x24\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xdf"
    )
    await asyncio.sleep(0)
    assert light.is_on is False
    await task

    task = asyncio.create_task(light.async_turn_on())
    await asyncio.sleep(0)
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xde"
    )
    await asyncio.sleep(0)
    assert light.is_on is True
    await task

    with patch.object(aiodevice, "POWER_STATE_TIMEOUT", 0.05):
        task = asyncio.create_task(light.async_turn_off())
        # Do NOT wait for the future to get added, we know the retry logic works
        light._aio_protocol.data_received(
            b"\x81\x25\x24\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xdf"
        )
        await asyncio.sleep(0)
        assert light.is_on is False
        await task


@pytest.mark.asyncio
async def test_shutdown(mock_aio_protocol):
    """Test we can shutdown."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xde"
    )
    await task

    await light.async_stop()
    await asyncio.sleep(0)  # make sure nothing throws


@pytest.mark.asyncio
async def test_handling_connection_lost(mock_aio_protocol):
    """Test we can reconnect."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xde"
    )
    await task

    light._aio_protocol.connection_lost(None)
    await asyncio.sleep(0)  # make sure nothing throws

    # Test we reconnect and can turn off
    task = asyncio.create_task(light.async_turn_off())
    # Wait for the future to get added
    await asyncio.sleep(0.1)  # wait for reconnect
    light._aio_protocol.data_received(
        b"\x81\x25\x24\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xdf"
    )
    await asyncio.sleep(0)
    assert light.is_on is False
    await task
