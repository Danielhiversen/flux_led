import asyncio
import contextlib
import datetime
import logging
from unittest.mock import MagicMock, call, patch

import pytest

from flux_led import aiodevice
from flux_led.aio import AIOWifiLedBulb
from flux_led.aioprotocol import AIOLEDENETProtocol
from flux_led.aioscanner import AIOBulbScanner, LEDENETDiscovery
from flux_led.const import (
    COLOR_MODE_CCT,
    COLOR_MODE_RGBWW,
    EFFECT_MUSIC,
    MultiColorEffects,
)
from flux_led.protocol import PROTOCOL_LEDENET_9BYTE, PROTOCOL_LEDENET_ORIGINAL
from flux_led.scanner import FluxLEDDiscovery, merge_discoveries

IP_ADDRESS = "127.0.0.1"
MODEL_NUM_HEX = "0x35"
MODEL = "AZ120444"
MODEL_DESCRIPTION = "Bulb RGBCW"
FLUX_MAC_ADDRESS = "aabbccddeeff"

FLUX_DISCOVERY_PARTIAL = FluxLEDDiscovery(
    ipaddr=IP_ADDRESS,
    model=MODEL,
    id=FLUX_MAC_ADDRESS,
    model_num=None,
    version_num=None,
    firmware_date=None,
    model_info=None,
    model_description=None,
)
FLUX_DISCOVERY = FluxLEDDiscovery(
    ipaddr=IP_ADDRESS,
    model=MODEL,
    id=FLUX_MAC_ADDRESS,
    model_num=0x25,
    version_num=0x04,
    firmware_date=datetime.date(2021, 5, 5),
    model_info=MODEL,
    model_description=MODEL_DESCRIPTION,
)


@pytest.fixture
async def mock_discovery_aio_protocol():
    """Fixture to mock an asyncio connection."""
    loop = asyncio.get_running_loop()
    future = asyncio.Future()

    async def _wait_for_connection():
        transport, protocol = await future
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return transport, protocol

    async def _mock_create_datagram_endpoint(func, sock=None):
        protocol: LEDENETDiscovery = func()
        transport = MagicMock()
        protocol.connection_made(transport)
        with contextlib.suppress(asyncio.InvalidStateError):
            future.set_result((transport, protocol))
        return transport, protocol

    with patch.object(loop, "create_datagram_endpoint", _mock_create_datagram_endpoint):
        yield _wait_for_connection


@pytest.fixture
async def mock_aio_protocol():
    """Fixture to mock an asyncio connection."""
    loop = asyncio.get_running_loop()
    future = asyncio.Future()

    async def _wait_for_connection():
        transport, protocol = await future
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return transport, protocol

    async def _mock_create_connection(func, ip, port):
        protocol: AIOLEDENETProtocol = func()
        transport = MagicMock()
        protocol.connection_made(transport)
        with contextlib.suppress(asyncio.InvalidStateError):
            future.set_result((transport, protocol))
        return transport, protocol

    with patch.object(loop, "create_connection", _mock_create_connection):
        yield _wait_for_connection


@pytest.mark.asyncio
async def test_no_initial_response(mock_aio_protocol):
    """Test we try switching protocol if we get no initial response."""
    light = AIOWifiLedBulb("192.168.1.166", timeout=0.1)
    assert light.protocol is None

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    with pytest.raises(RuntimeError):
        await task

    assert transport.mock_calls == [
        call.get_extra_info("peername"),
        call.write(bytearray(b"\x81\x8a\x8b\x96")),
        call.write_eof(),
        call.close(),
    ]
    assert not light.available
    assert light.protocol is PROTOCOL_LEDENET_ORIGINAL


@pytest.mark.asyncio
async def test_invalid_initial_response(mock_aio_protocol):
    """Test we try switching protocol if we an unexpected response."""
    light = AIOWifiLedBulb("192.168.1.166", timeout=0.1)

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(b"\x31\x25")
    with pytest.raises(RuntimeError):
        await task

    assert transport.mock_calls == [
        call.get_extra_info("peername"),
        call.write(bytearray(b"\x81\x8a\x8b\x96")),
        call.write_eof(),
        call.close(),
    ]
    assert not light.available


@pytest.mark.asyncio
async def test_cannot_determine_strip_type(mock_aio_protocol):
    """Test we raise RuntimeError when we cannot determine the strip type."""
    light = AIOWifiLedBulb("192.168.1.166", timeout=0.1)

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    await mock_aio_protocol()
    # protocol state
    light._aio_protocol.data_received(
        b"\x81\xA3#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd5"
    )
    with pytest.raises(RuntimeError):
        await task
    assert not light.available


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
    assert light.model == "Controller RGB/WW/CW (0x25)"
    assert light.is_on is True
    assert len(light.effect_list) == 21

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
async def test_turn_on_off(mock_aio_protocol, caplog: pytest.LogCaptureFixture):
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

    await asyncio.sleep(0)
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    # Handle the failure case
    with patch.object(aiodevice, "POWER_STATE_TIMEOUT", 0.025):
        await asyncio.create_task(light.async_turn_off())
        assert light.is_on is True
        assert "Failed to turn off (1/4)" in caplog.text
        assert "Failed to turn off (2/4)" in caplog.text
        assert "Failed to turn off (3/4)" in caplog.text
        assert "Failed to turn off (4/4)" in caplog.text

    with patch.object(aiodevice, "POWER_STATE_TIMEOUT", 0.025):
        task = asyncio.create_task(light.async_turn_off())
        # Do NOT wait for the future to get added, we know the retry logic works
        light._aio_protocol.data_received(
            b"\x81\x25\x24\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xdf"
        )
        await asyncio.sleep(0)
        assert light.is_on is False
        await task

    await asyncio.sleep(0)
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    # Handle the failure case
    with patch.object(aiodevice, "POWER_STATE_TIMEOUT", 0.025):
        await asyncio.create_task(light.async_turn_on())
        assert light.is_on is False
        assert "Failed to turn on (1/4)" in caplog.text
        assert "Failed to turn on (2/4)" in caplog.text
        assert "Failed to turn on (3/4)" in caplog.text
        assert "Failed to turn on (4/4)" in caplog.text


@pytest.mark.asyncio
async def test_turn_on_off_via_power_state_message(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can turn on and off via power state message."""
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
    light._ignore_next_power_state_update = False
    light._aio_protocol.data_received(b"\x0F\x71\x24\xA4")
    await asyncio.sleep(0)
    assert light.is_on is False
    await task

    task = asyncio.create_task(light.async_turn_on())
    await asyncio.sleep(0)
    light._ignore_next_power_state_update = False
    light._aio_protocol.data_received(b"\x0F\x71\x23\xA3")
    await asyncio.sleep(0)
    assert light.is_on is True
    await task


@pytest.mark.asyncio
async def test_turn_on_off_via_assessable_state_message(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can turn on and off via addressable state message."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    await mock_aio_protocol()
    # protocol state
    light._aio_protocol.data_received(
        b"\x81\xA3#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd5"
    )
    # ic sorting
    light._aio_protocol.data_received(b"\x00\x63\x00\x19\x00\x02\x04\x03\x19\x02\xA0")
    await task

    task = asyncio.create_task(light.async_turn_off())
    # Wait for the future to get added
    await asyncio.sleep(0)
    light._ignore_next_power_state_update = False
    light._aio_protocol.data_received(
        b"\xB0\xB1\xB2\xB3\x00\x01\x01\x23\x00\x0E\x81\xA3\x24\x25\xFF\x47\x64\xFF\xFF\x00\x01\x00\x1E\x34\x61"
    )
    await asyncio.sleep(0)
    assert light.is_on is False
    await task

    task = asyncio.create_task(light.async_turn_on())
    await asyncio.sleep(0)
    light._ignore_next_power_state_update = False
    light._aio_protocol.data_received(
        b"\xB0\xB1\xB2\xB3\x00\x01\x01\x24\x00\x0E\x81\xA3\x23\x25\x5F\x21\x64\xFF\xFF\x00\x01\x00\x1E\x6D\xD4"
    )
    await asyncio.sleep(0)
    assert light.is_on is True
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


@pytest.mark.asyncio
async def test_handling_unavailable_after_no_response(mock_aio_protocol):
    """Test we handle the bulb not responding."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xde"
    )
    await task

    await light.async_update()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    with pytest.raises(RuntimeError):
        await light.async_update()
    assert light.available is False


@pytest.mark.asyncio
async def test_async_set_levels(mock_aio_protocol, caplog: pytest.LogCaptureFixture):
    """Test we can set levels."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x33#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x65"
    )
    await task
    assert light.model_num == 0x33
    assert light.dimmable_effects is False
    assert light.requires_turn_on is True

    transport.reset_mock()
    with pytest.raises(ValueError):
        # ValueError: RGBW command sent to non-RGBW devic
        await light.async_set_levels(255, 255, 255, 255, 255)

    await light.async_set_levels(255, 0, 0)

    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\xff\x00\x00\x00\x00\x0f?"


@pytest.mark.asyncio
async def test_async_set_effect(mock_aio_protocol, caplog: pytest.LogCaptureFixture):
    """Test we can set an effect."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\xA3#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd5"
    )
    # ic state
    light._aio_protocol.data_received(b"\x00\x63\x00\x19\x00\x02\x04\x03\x19\x02\xA0")
    await task
    assert light.model_num == 0xA3
    assert light.dimmable_effects is True
    assert light.requires_turn_on is False

    transport.reset_mock()
    await light.async_set_effect("random", 50)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0].startswith(b"\xb0\xb1\xb2\xb3")

    transport.reset_mock()
    await light.async_set_effect("RBM 1", 50)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x01\x00\x05B\x012d\x00\xa7"
    )
    assert light.effect == "RBM 1"

    transport.reset_mock()
    await light.async_set_brightness(255)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x02\x00\x05B\x01\x10d\x00\x86"
    )

    transport.reset_mock()
    await light.async_set_brightness(128)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x03\x00\x05B\x01\x102\x00U"
    )


@pytest.mark.asyncio
async def test_async_set_zones(mock_aio_protocol, caplog: pytest.LogCaptureFixture):
    """Test we can set set zone colors."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\xA3#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd5"
    )
    # ic state
    light._aio_protocol.data_received(b"\x00\x63\x00\x19\x00\x02\x04\x03\x19\x02\xA0")
    await task
    assert light.model_num == 0xA3
    assert light.dimmable_effects is True
    assert light.requires_turn_on is False

    transport.reset_mock()
    await light.async_set_zones(
        [(255, 0, 0), (0, 0, 255)], 100, MultiColorEffects.STROBE
    )
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == (
        b"\xb0\xb1\xb2\xb3\x00\x01\x01\x00\x00TY\x00T\xff\x00\x00"
        b"\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff"
        b"\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00"
        b"\x00\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff"
        b"\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00"
        b"\x00\xff\x00\x00\xff\x00\x00\xff\x00\x1e\x03d\x00\x19N"
    )


@pytest.mark.asyncio
async def test_async_set_zones_unsupported_device(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can set set zone colors raises valueerror on unsupported."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x57"
    )
    await task
    assert light.model_num == 0x25

    transport.reset_mock()
    with pytest.raises(ValueError):
        await light.async_set_zones(
            [(255, 0, 0), (0, 0, 255)], 100, MultiColorEffects.STROBE
        )


@pytest.mark.asyncio
async def test_async_set_music_mode_0x08(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can set music mode on an 0x08."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    with patch.object(aiodevice, "COMMAND_SPACING_DELAY", 0):
        task = asyncio.create_task(light.async_setup(_updated_callback))
        transport, protocol = await mock_aio_protocol()
        light._aio_protocol.data_received(
            b"\x81\x08#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x3a"
        )
        await task
        assert light.model_num == 0x08
        assert light.microphone is True

        transport.reset_mock()
        await light.async_set_music_mode()
        assert transport.mock_calls[0][0] == "write"
        assert transport.mock_calls[0][1][0] == b"s\x01d\x0f\xe7"
        assert transport.mock_calls[1][0] == "write"
        assert transport.mock_calls[1][1][0] == b"7\x00\x007"


@pytest.mark.asyncio
async def test_async_set_music_mode_a2(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can set music mode on an 0xA2."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\xA2#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd4"
    )
    # ic state
    light._aio_protocol.data_received(b"\x00\x63\x00\x19\x00\x02\x04\x03\x19\x02\xA0")
    await task
    assert light.model_num == 0xA2
    assert light.microphone is True

    transport.reset_mock()
    await light.async_set_music_mode()
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"s\x01&\x01d\x00\x00\x00\x00\x00dd\xc7"

    transport.reset_mock()
    await light.async_set_effect(EFFECT_MUSIC, 100, 100)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"s\x01&\x01d\x00\x00\x00\x00\x00dd\xc7"


@pytest.mark.asyncio
async def test_async_set_music_mode_a3(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can set music mode on an 0xA3."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\xA3#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd5"
    )
    # ic state
    light._aio_protocol.data_received(b"\x00\x63\x00\x19\x00\x02\x04\x03\x19\x02\xA0")
    await task
    assert light.model_num == 0xA3
    assert light.microphone is True

    transport.reset_mock()
    await light.async_set_music_mode()
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0].startswith(b"\xb0\xb1\xb2\xb3")


@pytest.mark.asyncio
async def test_async_failed_callback(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we log on failed callback."""
    light = AIOWifiLedBulb("192.168.1.166")
    caplog.set_level(logging.DEBUG)

    def _updated_callback(*args, **kwargs):
        raise ValueError("something went wrong")

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\xA3#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd5"
    )
    # ic state
    light._aio_protocol.data_received(b"\x00\x63\x00\x19\x00\x02\x04\x03\x19\x02\xA0")
    await task
    assert light.model_num == 0xA3
    assert light.dimmable_effects is True
    assert light.requires_turn_on is False
    assert "something went wrong" in caplog.text


@pytest.mark.asyncio
async def test_async_set_custom_effect(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can set a custom effect."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xde"
    )
    await task
    assert light.model_num == 0x25

    transport.reset_mock()

    # no values
    with pytest.raises(ValueError):
        await light.async_set_custom_pattern([], 50, "jump")

    await light.async_set_custom_pattern(
        [
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 0),
            (255, 0, 255),
            (255, 0, 0),
            (255, 0, 0),
        ],
        50,
        "jump",
    )
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"Q\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\xff\x00\xff\x00\x00\x00\x10;\xff\x0f\x99"
    )


@pytest.mark.asyncio
async def test_async_set_brightness_rgbww(mock_aio_protocol):
    """Test we can set brightness rgbww."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xde"
    )
    await task

    await light.async_stop()
    await asyncio.sleep(0)  # make sure nothing throws

    transport.reset_mock()
    await light.async_set_brightness(255)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\xff\x00\xd5\xff\xff\x00\x0f\x12"

    transport.reset_mock()
    await light.async_set_brightness(128)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\x80\x00k\x80\x80\x00\x0f+"


@pytest.mark.asyncio
async def test_async_set_brightness_cct(mock_aio_protocol):
    """Test we can set brightness with a cct device."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x02\x10\xb6\x00\x98\x19\x04\x25\x0f\xdb"
    )
    await task

    await light.async_stop()
    await asyncio.sleep(0)  # make sure nothing throws

    transport.reset_mock()
    await light.async_set_brightness(255)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\x00\x00\x00g\x98\x0f\x0fN"
    assert light.brightness == 255

    transport.reset_mock()
    await light.async_set_brightness(128)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\x00\x00\x004L\x0f\x0f\xcf"
    assert light.brightness == 128


@pytest.mark.asyncio
async def test_async_set_brightness_dim(mock_aio_protocol):
    """Test we can set brightness with a dim only device."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x01\x10\xb6\x00\x98\x19\x04\x25\x0f\xda"
    )
    await task

    await light.async_stop()
    await asyncio.sleep(0)  # make sure nothing throws

    transport.reset_mock()
    await light.async_set_brightness(255)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\x00\x00\x00\xff\xff\x0f\x0fM"
    assert light.brightness == 255

    transport.reset_mock()
    await light.async_set_brightness(128)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\x00\x00\x00\x80\x80\x0f\x0fO"
    assert light.brightness == 128


@pytest.mark.asyncio
async def test_async_set_brightness_rgb(mock_aio_protocol):
    """Test we can set brightness with a rgb only device."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x03\x10\xb6\x00\x98\x19\x04\x25\x0f\xdc"
    )
    await task

    await light.async_stop()
    await asyncio.sleep(0)  # make sure nothing throws

    transport.reset_mock()
    await light.async_set_brightness(255)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\xff\x00\xd4\x00\x00\xf0\x0f\x03"
    assert light.brightness == 255

    transport.reset_mock()
    await light.async_set_brightness(128)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\x80\x00j\x00\x00\xf0\x0f\x1a"
    assert light.brightness == 128


@pytest.mark.asyncio
async def test_async_set_brightness_rgbw(mock_aio_protocol):
    """Test we can set brightness with a rgbw only device."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x04\x10\xb6\x00\x98\x19\x04\x25\x0f\xdd"
    )
    await task

    await light.async_stop()
    await asyncio.sleep(0)  # make sure nothing throws

    transport.reset_mock()
    await light.async_set_brightness(255)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\xff\x00\xd5\xff\xff\x00\x0f\x12"
    assert light.brightness == 255

    transport.reset_mock()
    await light.async_set_brightness(128)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\x80\x00k\x80\x80\x00\x0f+"
    assert light.brightness == 128


@pytest.mark.asyncio
async def test_cct_protocol_device(mock_aio_protocol):
    """Test a cct protocol device."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x1C\x23\x61\x00\x05\x00\x64\x64\x64\x03\x64\x0F\xC8"
    )
    await task
    assert light.getCCT() == (0, 255)
    assert light.color_temp == 6500
    assert light.brightness == 255

    light._aio_protocol.data_received(
        b"\x81\x1C\x23\x61\x00\x05\x00\x00\x00\x00\x03\x64\x00\x8D"
    )
    assert light.getCCT() == (255, 0)
    assert light.color_temp == 2700
    assert light.brightness == 255

    transport.reset_mock()
    await light.async_set_brightness(32)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x00\x00\t5\xb1\x00\r\x00\x00\x00\x03\xf6\xbd"
    )
    assert light.brightness == 33

    transport.reset_mock()
    await light.async_set_brightness(128)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x01\x00\t5\xb1\x002\x00\x00\x00\x03\x1b\x08"
    )
    assert light.brightness == 128

    transport.reset_mock()
    await light.async_set_brightness(1)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x02\x00\t5\xb1\x00\x02\x00\x00\x00\x03\xeb\xa9"
    )
    assert light.brightness == 0

    transport.reset_mock()
    await light.async_set_levels(w=0, w2=255)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x03\x00\t5\xb1dd\x00\x00\x00\x03\xb16"
    )
    assert light.getCCT() == (0, 255)
    assert light.color_temp == 6500
    assert light.brightness == 255

    transport.reset_mock()
    await light.async_set_effect("random", 50)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0].startswith(b"\xb0\xb1\xb2\xb3\x00")


@pytest.mark.asyncio
async def test_async_scanner(mock_discovery_aio_protocol):
    """Test scanner."""
    scanner = AIOBulbScanner()

    task = asyncio.ensure_future(
        scanner.async_scan(timeout=0.1, address="192.168.213.252")
    )
    transport, protocol = await mock_discovery_aio_protocol()
    protocol.datagram_received(b"HF-A11ASSISTHREAD", ("127.0.0.1", 48899))
    protocol.datagram_received(
        b"192.168.213.252,B4E842E10588,AK001-ZJ2145", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(b"AT+LVER\r", ("127.0.0.1", 48899))
    protocol.datagram_received(
        b"+ok=08_15_20210204_ZG-BL\r", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(
        b"192.168.213.65,F4CFA23E1AAF,AK001-ZJ2104", ("192.168.213.65", 48899)
    )
    protocol.datagram_received(b"+ok=A2_33_20200428_ZG-LX\r", ("192.168.213.65", 48899))
    data = await task
    assert data == [
        {
            "firmware_date": datetime.date(2021, 2, 4),
            "id": "B4E842E10588",
            "ipaddr": "192.168.213.252",
            "model": "AK001-ZJ2145",
            "model_description": "Controller RGB with MIC",
            "model_info": "ZG-BL",
            "model_num": 8,
            "version_num": 21,
        },
        {
            "firmware_date": datetime.date(2020, 4, 28),
            "id": "F4CFA23E1AAF",
            "ipaddr": "192.168.213.65",
            "model": "AK001-ZJ2104",
            "model_description": "Addressable v2",
            "model_info": "ZG-LX",
            "model_num": 162,
            "version_num": 51,
        },
    ]


@pytest.mark.asyncio
async def test_async_scanner_specific_address(mock_discovery_aio_protocol):
    """Test scanner with a specific address."""
    scanner = AIOBulbScanner()

    task = asyncio.ensure_future(
        scanner.async_scan(timeout=10, address="192.168.213.252")
    )
    transport, protocol = await mock_discovery_aio_protocol()
    protocol.datagram_received(
        b"192.168.213.252,B4E842E10588,AK001-ZJ2145", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(
        b"+ok=08_15_20210204_ZG-BL\r", ("192.168.213.252", 48899)
    )
    data = await task
    assert data == [
        {
            "firmware_date": datetime.date(2021, 2, 4),
            "id": "B4E842E10588",
            "ipaddr": "192.168.213.252",
            "model": "AK001-ZJ2145",
            "model_description": "Controller RGB with MIC",
            "model_info": "ZG-BL",
            "model_num": 8,
            "version_num": 21,
        }
    ]
    assert scanner.getBulbInfoByID("B4E842E10588") == {
        "firmware_date": datetime.date(2021, 2, 4),
        "id": "B4E842E10588",
        "ipaddr": "192.168.213.252",
        "model": "AK001-ZJ2145",
        "model_description": "Controller RGB with MIC",
        "model_info": "ZG-BL",
        "model_num": 8,
        "version_num": 21,
    }
    assert scanner.getBulbInfo() == [
        {
            "firmware_date": datetime.date(2021, 2, 4),
            "id": "B4E842E10588",
            "ipaddr": "192.168.213.252",
            "model": "AK001-ZJ2145",
            "model_description": "Controller RGB with MIC",
            "model_info": "ZG-BL",
            "model_num": 8,
            "version_num": 21,
        }
    ]


@pytest.mark.asyncio
async def test_async_scanner_times_out_with_nothing(mock_discovery_aio_protocol):
    """Test scanner."""
    scanner = AIOBulbScanner()

    task = asyncio.ensure_future(scanner.async_scan(timeout=0.025))
    transport, protocol = await mock_discovery_aio_protocol()
    data = await task
    assert data == []


@pytest.mark.asyncio
async def test_async_scanner_times_out_with_nothing_specific_address(
    mock_discovery_aio_protocol,
):
    """Test scanner."""
    scanner = AIOBulbScanner()

    task = asyncio.ensure_future(
        scanner.async_scan(timeout=0.025, address="192.168.213.252")
    )
    transport, protocol = await mock_discovery_aio_protocol()
    data = await task
    assert data == []


def test_merge_discoveries() -> None:
    """Unit test to make sure we can merge two discoveries."""
    full = FLUX_DISCOVERY.copy()
    partial = FLUX_DISCOVERY_PARTIAL.copy()
    merge_discoveries(partial, full)
    assert partial == FLUX_DISCOVERY
    assert full == FLUX_DISCOVERY

    full = FLUX_DISCOVERY.copy()
    partial = FLUX_DISCOVERY_PARTIAL.copy()
    merge_discoveries(full, partial)
    assert full == FLUX_DISCOVERY
