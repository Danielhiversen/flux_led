import asyncio
import contextlib
import datetime
import logging
from unittest.mock import MagicMock, call, patch

import pytest

from flux_led import aiodevice, aioscanner
from flux_led.aio import AIOWifiLedBulb
from flux_led.aioprotocol import AIOLEDENETProtocol
from flux_led.aioscanner import AIOBulbScanner, LEDENETDiscovery
from flux_led.const import (
    COLOR_MODE_CCT,
    COLOR_MODE_RGB,
    COLOR_MODE_RGBWW,
    EFFECT_MUSIC,
    MultiColorEffects,
)
from flux_led.protocol import (
    PROTOCOL_LEDENET_8BYTE,
    PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS,
    PROTOCOL_LEDENET_9BYTE,
    PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS,
    PROTOCOL_LEDENET_ORIGINAL,
    PowerRestoreState,
    PowerRestoreStates,
)
from flux_led.scanner import (
    FluxLEDDiscovery,
    create_udp_socket,
    is_legacy_device,
    merge_discoveries,
)

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


def mock_coro(return_value=None, exception=None):
    """Return a coro that returns a value or raise an exception."""
    fut = asyncio.Future()
    if exception is not None:
        fut.set_exception(exception)
    else:
        fut.set_result(return_value)
    return fut


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

    with patch.object(
        loop, "create_datagram_endpoint", _mock_create_datagram_endpoint
    ), patch.object(aioscanner, "MESSAGE_SEND_INTERLEAVE_DELAY", 0):
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
    light = AIOWifiLedBulb("192.168.1.166", timeout=0.01)
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
    light = AIOWifiLedBulb("192.168.1.166", timeout=0.01)

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
    light = AIOWifiLedBulb("192.168.1.166", timeout=0.01)

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
async def test_setting_discovery(mock_aio_protocol):
    """Test we can pass discovery to AIOWifiLedBulb."""
    light = AIOWifiLedBulb("192.168.1.166", timeout=0.01)

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    await mock_aio_protocol()
    # protocol state
    light._aio_protocol.data_received(
        b"\x81\x35\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xee"
    )
    discovery = FluxLEDDiscovery(
        {
            "firmware_date": datetime.date(2021, 1, 9),
            "id": "B4E842E10586",
            "ipaddr": "192.168.213.259",
            "model": "AK001-ZJ2145",
            "model_description": "Bulb RGBCW Flood",
            "model_info": "ZG-BL-PWM",
            "model_num": 53,
            "remote_access_enabled": False,
            "remote_access_host": None,
            "remote_access_port": None,
            "version_num": 98,
        }
    )

    await task
    assert light.available
    assert light.model == "Bulb RGBCW (0x35)"
    light.discovery = discovery
    assert light.model == "Bulb RGBCW Flood (0x35)"
    assert light.discovery == discovery


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
async def test_extract_from_outer_message(mock_aio_protocol):
    """Test we can can extract a message wrapped with an outer message."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\xb0\xb1\xb2\xb3\x00\x01\x01\x81\x00\x0e\x81\x1a\x23\x61\x07\x00\xff\x00\x00\x00\x01\x00\x06\x2c\xaf"
        b"\xb0\xb1\xb2\xb3\x00\x01\x01\x81\x00\x0e\x81\x1a\x23\x61\x07\x00\xff\x00\x00\x00\x01\x00\x06\x2c\xaf"
    )
    await task
    assert light.color_modes == {COLOR_MODE_RGB}
    assert light.protocol == PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS
    assert light.model_num == 0x1A
    assert light.model == "Christmas Light (0x1A)"
    assert light.is_on is True
    assert len(light.effect_list) == 101
    assert light.rgb == (255, 0, 0)


@pytest.mark.asyncio
async def test_extract_from_outer_message_and_reassemble(mock_aio_protocol):
    """Test we can can extract a message wrapped with an outer message."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    await mock_aio_protocol()
    for (
        byte
    ) in b"\xb0\xb1\xb2\xb3\x00\x01\x01\x81\x00\x0e\x81\x1a\x23\x61\x07\x00\xff\x00\x00\x00\x01\x00\x06\x2c\xaf":
        light._aio_protocol.data_received(bytearray([byte]))
    await task
    assert light.color_modes == {COLOR_MODE_RGB}
    assert light.protocol == PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS
    assert light.model_num == 0x1A
    assert light.model == "Christmas Light (0x1A)"
    assert light.is_on is True
    assert len(light.effect_list) == 101
    assert light.rgb == (255, 0, 0)


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
    assert light.version_num == 4
    assert light.dimmable_effects is False
    assert light.requires_turn_on is True
    assert light._protocol.power_push_updates is False
    assert light._protocol.state_push_updates is False

    transport.reset_mock()
    with pytest.raises(ValueError):
        # ValueError: RGBW command sent to non-RGBW devic
        await light.async_set_levels(255, 255, 255, 255, 255)

    await light.async_set_levels(255, 0, 0)

    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\xff\x00\x00\x00\x00\x0f?"

    # light is on
    light._aio_protocol.data_received(
        b"\x81\x33\x23\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x65"
    )
    transport.reset_mock()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await asyncio.sleep(0)
    assert len(transport.mock_calls) == 4

    # light is off
    light._aio_protocol.data_received(
        b"\x81\x33\x24\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x66"
    )
    transport.reset_mock()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await asyncio.sleep(0)
    assert len(transport.mock_calls) == 4


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
    assert light._protocol.power_push_updates is True
    assert light._protocol.state_push_updates is False

    transport.reset_mock()
    await light.async_set_effect("random", 50)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0].startswith(b"\xb0\xb1\xb2\xb3")

    transport.reset_mock()
    await light.async_set_effect("RBM 1", 50)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x02\x00\x05B\x012d\xd9\x81"
    )
    assert light.effect == "RBM 1"

    transport.reset_mock()
    await light.async_set_brightness(255)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x03\x00\x05B\x01\x10d\xb7>"
    )

    transport.reset_mock()
    await light.async_set_brightness(128)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x04\x00\x05B\x01\x102\x85\xdb"
    )


@pytest.mark.asyncio
async def test_SK6812RGBW(mock_aio_protocol, caplog: pytest.LogCaptureFixture):
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
    light._aio_protocol.data_received(
        b"\xB0\xB1\xB2\xB3\x00\x01\x01\x00\x00\x0B\x00\x63\x00\x90\x00\x01\x07\x08\x90\x01\x94\xFB"
    )

    await task
    assert light.pixels_per_segment == 144
    assert light.segments == 1
    assert light.music_pixels_per_segment == 144
    assert light.music_segments == 1
    assert light.strip_protocols == [
        "WS2812B",
        "SM16703",
        "SM16704",
        "WS2811",
        "UCS1903",
        "SK6812",
        "SK6812RGBW",
        "INK1003",
        "UCS2904B",
    ]
    assert light.strip_protocol == "SK6812RGBW"
    assert light.operating_mode is None
    assert light.operating_modes is None
    assert light.wiring == "WGRB"
    assert light.wirings == [
        "RGBW",
        "RBGW",
        "GRBW",
        "GBRW",
        "BRGW",
        "BGRW",
        "WRGB",
        "WRBG",
        "WGRB",
        "WGBR",
        "WBRG",
        "WBGR",
    ]
    assert light.model_num == 0xA3
    assert light.dimmable_effects is True
    assert light.requires_turn_on is False


@pytest.mark.asyncio
async def test_ws2812b_a1(mock_aio_protocol, caplog: pytest.LogCaptureFixture):
    """Test we can determine ws2812b configuration."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\xA1#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd3"
    )
    # ic state
    light._aio_protocol.data_received(
        b"\x63\x00\x32\x04\x00\x00\x00\x00\x00\x00\x02\x9B"
    )

    await task
    assert light.pixels_per_segment == 50
    assert light.segments == 0
    assert light.music_pixels_per_segment == 0
    assert light.music_segments == 0
    assert light.strip_protocols == [
        "UCS1903",
        "SM16703",
        "WS2811",
        "WS2812B",
        "SK6812",
        "INK1003",
        "WS2801",
        "LB1914",
    ]
    assert light.strip_protocol == "WS2812B"
    assert light.operating_mode is None
    assert light.operating_modes is None
    assert light.wiring == "GRB"
    assert light.wirings == ["RGB", "RBG", "GRB", "GBR", "BRG", "BGR"]
    assert light.model_num == 0xA1
    assert light.dimmable_effects is False
    assert light.requires_turn_on is False


@pytest.mark.asyncio
async def test_ws2811_a2(mock_aio_protocol, caplog: pytest.LogCaptureFixture):
    """Test we can determine ws2811 configuration."""
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
    assert light.pixels_per_segment == 25
    assert light.segments == 2
    assert light.music_pixels_per_segment == 25
    assert light.music_segments == 2
    assert light.strip_protocol == "WS2811"
    assert light.operating_mode is None
    assert light.operating_modes is None
    assert light.wiring == "GBR"
    assert light.wirings == ["RGB", "RBG", "GRB", "GBR", "BRG", "BGR"]
    assert light.model_num == 0xA2
    assert light.dimmable_effects is True
    assert light.requires_turn_on is False


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
    # sometimes the devices responds 2x
    light._aio_protocol.data_received(b"\x00\x63\x00\x19\x00\x02\x04\x03\x19\x02\xA0")

    await task
    assert light.pixels_per_segment == 25
    assert light.segments == 2
    assert light.music_pixels_per_segment == 25
    assert light.music_segments == 2
    assert light.strip_protocols == [
        "WS2812B",
        "SM16703",
        "SM16704",
        "WS2811",
        "UCS1903",
        "SK6812",
        "SK6812RGBW",
        "INK1003",
        "UCS2904B",
    ]
    assert light.strip_protocol == "WS2811"
    assert light.operating_mode is None
    assert light.operating_modes is None
    assert light.wiring == "GBR"
    assert light.wirings == ["RGB", "RBG", "GRB", "GBR", "BRG", "BGR"]
    assert light.model_num == 0xA3
    assert light.dimmable_effects is True
    assert light.requires_turn_on is False

    transport.reset_mock()
    await light.async_set_zones(
        [(255, 0, 0), (0, 0, 255)], 100, MultiColorEffects.STROBE
    )
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == bytearray(
        b"\xb0\xb1\xb2\xb3\x00\x01\x01\x01\x00TY\x00T\xff\x00\x00"
        b"\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff"
        b"\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00"
        b"\x00\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff"
        b"\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00"
        b"\x00\xff\x00\x00\xff\x00\x00\xff\x00\x1e\x03d\x00\x19O"
    )

    with pytest.raises(ValueError):
        await light.async_set_zones(
            [(255, 0, 0) for _ in range(30)],
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
            b"\x81\x08#\x5d\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x72"
        )
        await task
        assert light.model_num == 0x08
        assert light.version_num == 4
        assert light.effect == EFFECT_MUSIC
        assert light.microphone is True
        assert light.protocol == PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS

        transport.reset_mock()
        await light.async_set_music_mode()
        assert transport.mock_calls[0][0] == "write"
        assert transport.mock_calls[0][1][0] == b"s\x01d\x0f\xe7"
        assert transport.mock_calls[1][0] == "write"
        assert transport.mock_calls[1][1][0] == b"7\x00\x007"

        with pytest.raises(ValueError):
            await light.async_set_music_mode(mode=0x08)


@pytest.mark.asyncio
async def test_async_set_music_mode_0x08_v1_firmware(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can set music mode on an 0x08 with v1 firmware."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    with patch.object(aiodevice, "COMMAND_SPACING_DELAY", 0):
        task = asyncio.create_task(light.async_setup(_updated_callback))
        transport, protocol = await mock_aio_protocol()
        light._aio_protocol.data_received(
            b"\x81\x08\x23\x62\x23\x01\x80\x00\xFF\x00\x01\x00\x00\xB2"
        )
        await task
        assert light.model_num == 0x08
        assert light.version_num == 1
        assert light.effect == EFFECT_MUSIC
        assert light.microphone is True
        assert light.protocol == PROTOCOL_LEDENET_8BYTE

        transport.reset_mock()
        await light.async_set_music_mode()
        assert len(transport.mock_calls) == 1
        assert transport.mock_calls[0][0] == "write"
        assert transport.mock_calls[0][1][0] == b"s\x01d\x0f\xe7"


@pytest.mark.asyncio
async def test_async_set_music_mode_0x08_v2_firmware(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can set music mode on an 0x08 with v2 firmware."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    with patch.object(aiodevice, "COMMAND_SPACING_DELAY", 0):
        task = asyncio.create_task(light.async_setup(_updated_callback))
        transport, protocol = await mock_aio_protocol()
        light._aio_protocol.data_received(
            b"\x81\x08\x23\x62\x23\x01\x80\x00\xFF\x00\x02\x00\x00\xB3"
        )
        await task
        assert light.model_num == 0x08
        assert light.version_num == 2
        assert light.effect == EFFECT_MUSIC
        assert light.microphone is True
        assert light.protocol == PROTOCOL_LEDENET_8BYTE_DIMMABLE_EFFECTS

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
        b"\x81\xA2#\x62\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x11"
    )
    # ic state
    light._aio_protocol.data_received(b"\x00\x63\x00\x19\x00\x02\x04\x03\x19\x02\xA0")
    await task
    assert light.model_num == 0xA2
    assert light.effect == EFFECT_MUSIC
    assert light.microphone is True
    assert light._protocol.state_push_updates is False
    assert light._protocol.power_push_updates is False

    transport.reset_mock()
    await light.async_set_music_mode()
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"s\x01&\x01d\x00\x00\x00\x00\x00dd\xc7"

    transport.reset_mock()
    await light.async_set_effect(EFFECT_MUSIC, 100, 100)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"s\x01&\x01d\x00\x00\x00\x00\x00dd\xc7"

    # light is on
    light._aio_protocol.data_received(
        b"\x81\xA2\x23\x62\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x11"
    )
    transport.reset_mock()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await asyncio.sleep(0)
    assert len(transport.mock_calls) == 4

    # light is off
    light._aio_protocol.data_received(
        b"\x81\xA2\x24\x62\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x12"
    )
    transport.reset_mock()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await asyncio.sleep(0)
    assert len(transport.mock_calls) == 4


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
        b"\x81\xA3#\x62\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x12"
    )
    # ic state
    light._aio_protocol.data_received(b"\x00\x63\x00\x19\x00\x02\x04\x03\x19\x02\xA0")
    await task
    assert light.model_num == 0xA3
    assert light.effect == EFFECT_MUSIC
    assert light.microphone is True

    transport.reset_mock()
    await light.async_set_music_mode()
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0].startswith(b"\xb0\xb1\xb2\xb3")

    with pytest.raises(ValueError):
        await light.async_set_music_mode(mode=0x08)

    with pytest.raises(ValueError):
        await light.async_set_music_mode(effect=0x99)


@pytest.mark.asyncio
async def test_async_set_music_mode_device_without_mic_0x07(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can set music mode on an 0x08."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x07#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\x39"
    )
    await task
    assert light.model_num == 0x07
    assert light.microphone is False

    transport.reset_mock()
    with pytest.raises(ValueError):
        await light.async_set_music_mode()


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
    assert light.dimmable_effects is False
    assert light.requires_turn_on is False
    assert light._protocol.power_push_updates is True
    assert light._protocol.state_push_updates is True

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

    # light is on
    light._aio_protocol.data_received(
        b"\x81\x1C\x23\x61\x00\x05\x00\x64\x64\x64\x03\x64\x0F\xC8"
    )
    assert light._last_update_time == aiodevice.NEVER_TIME
    transport.reset_mock()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await asyncio.sleep(0)
    assert len(transport.mock_calls) == 1

    # light is off
    light._aio_protocol.data_received(
        b"\x81\x1C\x24\x61\x00\x05\x00\x64\x64\x64\x03\x64\x0F\xC9"
    )
    transport.reset_mock()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await light.async_update()
    await asyncio.sleep(0)
    assert len(transport.mock_calls) == 0

    transport.reset_mock()
    for _ in range(4):
        light._last_update_time = aiodevice.NEVER_TIME
        await light.async_update()
    await asyncio.sleep(0)
    assert len(transport.mock_calls) == 4

    light._last_update_time = aiodevice.NEVER_TIME
    for _ in range(4):
        # First failure should keep the device in
        # a failure state until we get to an update
        # time
        with pytest.raises(RuntimeError):
            await light.async_update()

    # Should not raise now that bulb has recovered
    light._last_update_time = aiodevice.NEVER_TIME
    await light.async_update()


@pytest.mark.asyncio
async def test_christmas_protocol_device(mock_aio_protocol):
    """Test a christmas protocol device."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x1a\x23\x61\x00\x00\x00\xff\x00\x00\x01\x00\x06\x25"
    )
    await task
    assert light.rgb == (0, 255, 0)
    assert light.brightness == 255
    assert len(light.effect_list) == 101
    assert light.protocol == PROTOCOL_LEDENET_ADDRESSABLE_CHRISTMAS
    assert light.dimmable_effects is False
    assert light.requires_turn_on is False
    assert light._protocol.power_push_updates is True
    assert light._protocol.state_push_updates is False

    transport.reset_mock()
    await light.async_set_brightness(255)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x00\x00\x0d\x3b\xa1<dd\x00\x00\x00\x00\x00\x00\x00\xe0\x95"
    )
    assert light.brightness == 255

    transport.reset_mock()
    await light.async_set_brightness(128)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x01\x00\r;\xa1<d2\x00\x00\x00\x00\x00\x00\x00\xae2"
    )
    assert light.brightness == 128

    transport.reset_mock()
    await light.async_set_levels(r=255, g=255, b=255)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x02\x00\r;\xa1\x00\x00\x64\x00\x00\x00\x00\x00\x00\x00@W"
    )
    assert light.brightness == 255

    transport.reset_mock()
    await light.async_set_effect("Random Jump Async", 50)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x03\x00\x07\xa3\x01\x10\x00\x00\x00\xb4:"
    )
    light._transition_complete_time = 0
    light._aio_protocol.data_received(
        b"\x81\x1a\x23\x60\x01\x00\x64\x10\x00\x00\x01\x00\x06\x9a"
    )
    assert light.effect == "Random Jump Async"
    assert light.speed == 50

    transport.reset_mock()
    await light.async_set_effect("Random Jump Async", 100)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x04\x00\x07\xa3\x01\x01\x00\x00\x00\xa5\x1d"
    )

    light._transition_complete_time = 0
    light._aio_protocol.data_received(
        b"\x81\x1a\x23\x60\x02\x00\x64\x01\x00\x00\x01\x00\x06\x8c"
    )
    assert light.effect == "Random Gradient Async"
    assert light.speed == 100

    with pytest.raises(ValueError):
        await light.async_set_preset_pattern(101, 50, 100)

    light._transition_complete_time = 0
    light._aio_protocol.data_received(
        b"\x81\x1a\x23\x61\x07\x00\x66\x00\x66\x00\x01\x00\x06\xf9"
    )
    assert light.effect is None
    assert light.rgb == (102, 0, 102)
    assert light.speed == 100

    transport.reset_mock()
    await light.async_set_zones([(255, 0, 0), (0, 0, 255)])
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == (
        b"\xb0\xb1\xb2\xb3\x00\x01\x01\x05\x004\xa0\x00`\x00\x01\xff\x00\x00\x00\x00\xff\x00\x02\xff\x00\x00\x00\x00\xff\x00\x03\xff\x00\x00\x00\x00\xff\x00\x04\x00\x00\xff\x00\x00\xff\x00\x05\x00\x00\xff\x00\x00\xff\x00\x06\x00\x00\xff\x00\x00\xff\t\x13"
    )

    transport.reset_mock()
    await light.async_set_zones(
        [(255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 255, 255)]
    )
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == (
        b"\xb0\xb1\xb2\xb3\x00\x01\x01\x06\x004\xa0\x00`\x00\x01\xff\x00\x00\x00\x00\xff\x00\x02\x00\x00\xff\x00\x00\xff\x00\x03\x00\xff\x00\x00\x00\xff\x00\x04\xff\xff\xff\x00\x00\xff\x00\x05\xff\xff\xff\x00\x00\xff\x00\x06\xff\xff\xff\x00\x00\xff\x03\x08"
    )

    with pytest.raises(ValueError):
        await light.async_set_zones(
            [
                (255, 0, 0),
                (0, 0, 255),
                (0, 255, 0),
                (255, 255, 255),
                (255, 255, 255),
                (255, 255, 255),
                (255, 255, 255),
            ]
        )


@pytest.mark.asyncio
async def test_async_enable_remote_access(mock_aio_protocol):
    """Test we can enable remote access."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x04\x10\xb6\x00\x98\x19\x04\x25\x0f\xdd"
    )
    await task

    with patch(
        "flux_led.aiodevice.AIOBulbScanner.async_enable_remote_access",
        return_value=mock_coro(True),
    ) as mock_async_enable_remote_access:
        await light.async_enable_remote_access("host", 1234)

    assert mock_async_enable_remote_access.mock_calls == [
        call("192.168.1.166", "host", 1234)
    ]


@pytest.mark.asyncio
async def test_async_disable_remote_access(mock_aio_protocol):
    """Test we can disable remote access."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x04\x10\xb6\x00\x98\x19\x04\x25\x0f\xdd"
    )
    await task

    with patch(
        "flux_led.aiodevice.AIOBulbScanner.async_disable_remote_access",
        return_value=mock_coro(True),
    ) as mock_async_disable_remote_access:
        await light.async_disable_remote_access()

    assert mock_async_disable_remote_access.mock_calls == [call("192.168.1.166")]


@pytest.mark.asyncio
async def test_async_reboot(mock_aio_protocol):
    """Test we can reboot."""
    light = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(light.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    light._aio_protocol.data_received(
        b"\x81\x25\x23\x61\x04\x10\xb6\x00\x98\x19\x04\x25\x0f\xdd"
    )
    await task

    with patch(
        "flux_led.aiodevice.AIOBulbScanner.async_reboot",
        return_value=mock_coro(True),
    ) as mock_async_reboot:
        await light.async_reboot()

    assert mock_async_reboot.mock_calls == [call("192.168.1.166")]


@pytest.mark.asyncio
async def test_power_state_response_processing(
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
    light._aio_protocol.data_received(b"\xf0\x32\xf0\xf0\xf0\xf0\xe2")
    assert light.power_restore_states == PowerRestoreStates(
        channel1=PowerRestoreState.LAST_STATE,
        channel2=PowerRestoreState.LAST_STATE,
        channel3=PowerRestoreState.LAST_STATE,
        channel4=PowerRestoreState.LAST_STATE,
    )
    light._aio_protocol.data_received(b"\xf0\x32\x0f\xf0\xf0\xf0\x01")
    assert light.power_restore_states == PowerRestoreStates(
        channel1=PowerRestoreState.ALWAYS_ON,
        channel2=PowerRestoreState.LAST_STATE,
        channel3=PowerRestoreState.LAST_STATE,
        channel4=PowerRestoreState.LAST_STATE,
    )
    light._aio_protocol.data_received(b"\xf0\x32\xff\xf0\xf0\xf0\xf1")
    assert light.power_restore_states == PowerRestoreStates(
        channel1=PowerRestoreState.ALWAYS_OFF,
        channel2=PowerRestoreState.LAST_STATE,
        channel3=PowerRestoreState.LAST_STATE,
        channel4=PowerRestoreState.LAST_STATE,
    )


@pytest.mark.asyncio
async def test_async_set_power_restore_state(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we can set power restore state and report it."""
    socket = AIOWifiLedBulb("192.168.1.166")

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(socket.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    socket._aio_protocol.data_received(
        b"\x81\x97\x24\x24\x00\x00\x00\x00\x00\x00\x02\x00\x00\x62"
    )
    # power restore state
    socket._aio_protocol.data_received(b"\x0F\x32\xF0\xF0\xF0\xF0\x01")
    await task
    assert socket.model_num == 0x97
    assert socket.power_restore_states == PowerRestoreStates(
        channel1=PowerRestoreState.LAST_STATE,
        channel2=PowerRestoreState.LAST_STATE,
        channel3=PowerRestoreState.LAST_STATE,
        channel4=PowerRestoreState.LAST_STATE,
    )

    transport.reset_mock()
    await socket.async_set_power_restore(
        channel1=PowerRestoreState.ALWAYS_ON,
        channel2=PowerRestoreState.ALWAYS_ON,
        channel3=PowerRestoreState.ALWAYS_ON,
        channel4=PowerRestoreState.ALWAYS_ON,
    )
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0] == b"1\x0f\x0f\x0f\x0f\xf0]"


@pytest.mark.asyncio
async def test_async_set_power_restore_state_fails(
    mock_aio_protocol, caplog: pytest.LogCaptureFixture
):
    """Test we raise if we do not get a power restore state."""
    socket = AIOWifiLedBulb("192.168.1.166", timeout=0.01)

    def _updated_callback(*args, **kwargs):
        pass

    task = asyncio.create_task(socket.async_setup(_updated_callback))
    transport, protocol = await mock_aio_protocol()
    socket._aio_protocol.data_received(
        b"\x81\x97\x24\x24\x00\x00\x00\x00\x00\x00\x02\x00\x00\x62"
    )
    # power restore state not sent
    with pytest.raises(RuntimeError):
        await task


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
    protocol.datagram_received(
        b"192.168.198.198,B4E842E10522,AK001-ZJ2149", ("192.168.198.198", 48899)
    )
    protocol.datagram_received(
        b"192.168.198.197,B4E842E10521,AK001-ZJ2146", ("192.168.198.197", 48899)
    )
    protocol.datagram_received(
        b"192.168.198.196,B4E842E10520,AK001-ZJ2144", ("192.168.198.196", 48899)
    )
    protocol.datagram_received(
        b"+ok=TCP,GARBAGE,ra8816us02.magichue.net\r", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(
        b"192.168.213.259,B4E842E10586,AK001-ZJ2145", ("192.168.213.259", 48899)
    )
    protocol.datagram_received(
        b"+ok=TCP,8816,ra8816us02.magichue.net\r", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(b"AT+LVER\r", ("127.0.0.1", 48899))
    protocol.datagram_received(
        b"+ok=GARBAGE_GARBAGE_GARBAGE_ZG-BL\r", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(
        b"+ok=08_15_20210204_ZG-BL\r", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(b"+ok=52_3_20210204\r", ("192.168.198.198", 48899))
    protocol.datagram_received(b"+ok=62_3\r", ("192.168.198.197", 48899))
    protocol.datagram_received(b"+ok=41_3_202\r", ("192.168.198.196", 48899))

    protocol.datagram_received(
        b"+ok=35_62_20210109_ZG-BL-PWM\r", ("192.168.213.259", 48899)
    )
    protocol.datagram_received(
        b"192.168.213.65,F4CFA23E1AAF,AK001-ZJ2104", ("192.168.213.65", 48899)
    )
    protocol.datagram_received(b"+ok=", ("192.168.213.65", 48899))
    protocol.datagram_received(b"+ok=A2_33_20200428_ZG-LX\r", ("192.168.213.65", 48899))
    protocol.datagram_received(b"+ok=", ("192.168.213.259", 48899))
    protocol.datagram_received(
        b"+ok=TCP,8816,ra8816us02.magichue.net\r", ("192.168.198.196", 48899)
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
            "remote_access_enabled": True,
            "remote_access_host": "ra8816us02.magichue.net",
            "remote_access_port": 8816,
            "version_num": 21,
        },
        {
            "firmware_date": datetime.date(2021, 2, 4),
            "id": "B4E842E10522",
            "ipaddr": "192.168.198.198",
            "model": "AK001-ZJ2149",
            "model_description": "Bulb CCT",
            "model_info": None,
            "model_num": 82,
            "remote_access_enabled": None,
            "remote_access_host": None,
            "remote_access_port": None,
            "version_num": 3,
        },
        {
            "firmware_date": None,
            "id": "B4E842E10521",
            "ipaddr": "192.168.198.197",
            "model": "AK001-ZJ2146",
            "model_description": "Controller CCT",
            "model_info": None,
            "model_num": 98,
            "remote_access_enabled": None,
            "remote_access_host": None,
            "remote_access_port": None,
            "version_num": 3,
        },
        {
            "firmware_date": None,
            "id": "B4E842E10520",
            "ipaddr": "192.168.198.196",
            "model": "AK001-ZJ2144",
            "model_description": "Controller Dimmable",
            "model_info": None,
            "model_num": 65,
            "remote_access_enabled": True,
            "remote_access_host": "ra8816us02.magichue.net",
            "remote_access_port": 8816,
            "version_num": 3,
        },
        {
            "firmware_date": datetime.date(2021, 1, 9),
            "id": "B4E842E10586",
            "ipaddr": "192.168.213.259",
            "model": "AK001-ZJ2145",
            "model_description": "Bulb RGBCW Flood",
            "model_info": "ZG-BL-PWM",
            "model_num": 53,
            "remote_access_enabled": False,
            "remote_access_host": None,
            "remote_access_port": None,
            "version_num": 98,
        },
        {
            "firmware_date": datetime.date(2020, 4, 28),
            "id": "F4CFA23E1AAF",
            "ipaddr": "192.168.213.65",
            "model": "AK001-ZJ2104",
            "model_description": "Addressable v2",
            "model_info": "ZG-LX",
            "model_num": 162,
            "remote_access_enabled": False,
            "remote_access_host": None,
            "remote_access_port": None,
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
    protocol.datagram_received(
        b"+ok=TCP,8816,ra8816us02.magichue.net\r", ("192.168.213.252", 48899)
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
            "remote_access_enabled": True,
            "remote_access_host": "ra8816us02.magichue.net",
            "remote_access_port": 8816,
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
        "remote_access_enabled": True,
        "remote_access_host": "ra8816us02.magichue.net",
        "remote_access_port": 8816,
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
            "remote_access_enabled": True,
            "remote_access_host": "ra8816us02.magichue.net",
            "remote_access_port": 8816,
        }
    ]


@pytest.mark.asyncio
async def test_async_scanner_specific_address_legacy_device(
    mock_discovery_aio_protocol,
):
    """Test scanner with a specific address of a legacy device."""
    scanner = AIOBulbScanner()

    task = asyncio.ensure_future(
        scanner.async_scan(timeout=10, address="192.168.213.252")
    )
    transport, protocol = await mock_discovery_aio_protocol()
    protocol.datagram_received(
        b"192.168.213.252,ACCF232E5124,HF-A11-ZJ002", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(b"+ok=15\r\n\r\n", ("192.168.213.252", 48899))
    protocol.datagram_received(b"+ERR=-2\r\n\r\n", ("192.168.213.252", 48899))
    data = await task
    assert data == [
        {
            "firmware_date": None,
            "id": "ACCF232E5124",
            "ipaddr": "192.168.213.252",
            "model": "HF-A11-ZJ002",
            "model_description": None,
            "model_info": None,
            "model_num": None,
            "remote_access_enabled": None,
            "remote_access_host": None,
            "remote_access_port": None,
            "version_num": 21,
        }
    ]
    assert is_legacy_device(data[0]) is True


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


@pytest.mark.asyncio
async def test_async_scanner_falls_back_to_any_source_port_if_socket_in_use():
    """Test port fallback."""
    hold_socket = create_udp_socket(AIOBulbScanner.DISCOVERY_PORT)
    assert hold_socket.getsockname() == ("0.0.0.0", 48899)
    random_socket = create_udp_socket(AIOBulbScanner.DISCOVERY_PORT)
    assert random_socket.getsockname() != ("0.0.0.0", 48899)


@pytest.mark.asyncio
async def test_async_scanner_enable_remote_access(mock_discovery_aio_protocol):
    """Test scanner enabling remote access with a specific address."""
    scanner = AIOBulbScanner()

    task = asyncio.ensure_future(
        scanner.async_enable_remote_access(
            timeout=10,
            address="192.168.213.252",
            remote_access_host="ra8815us02.magichue.net",
            remote_access_port=8815,
        )
    )
    transport, protocol = await mock_discovery_aio_protocol()
    protocol.datagram_received(
        b"192.168.213.252,B4E842E10588,AK001-ZJ2145", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(b"+ok\r", ("192.168.213.252", 48899))
    protocol.datagram_received(b"+ok\r", ("192.168.213.252", 48899))
    await task
    assert transport.mock_calls == [
        call.sendto(b"HF-A11ASSISTHREAD", ("192.168.213.252", 48899)),
        call.sendto(
            b"AT+SOCKB=TCP,8815,ra8815us02.magichue.net\r", ("192.168.213.252", 48899)
        ),
        call.sendto(b"AT+Z\r", ("192.168.213.252", 48899)),
        call.close(),
    ]


@pytest.mark.asyncio
async def test_async_scanner_disable_remote_access(mock_discovery_aio_protocol):
    """Test scanner disable remote access with a specific address."""
    scanner = AIOBulbScanner()

    task = asyncio.ensure_future(
        scanner.async_disable_remote_access(
            timeout=10,
            address="192.168.213.252",
        )
    )
    transport, protocol = await mock_discovery_aio_protocol()
    protocol.datagram_received(
        b"192.168.213.252,B4E842E10588,AK001-ZJ2145", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(b"+ok\r", ("192.168.213.252", 48899))
    protocol.datagram_received(b"+ok\r", ("192.168.213.252", 48899))
    await task
    assert transport.mock_calls == [
        call.sendto(b"HF-A11ASSISTHREAD", ("192.168.213.252", 48899)),
        call.sendto(b"AT+SOCKB=NONE\r", ("192.168.213.252", 48899)),
        call.sendto(b"AT+Z\r", ("192.168.213.252", 48899)),
        call.close(),
    ]


@pytest.mark.asyncio
async def test_async_scanner_reboot(mock_discovery_aio_protocol):
    """Test scanner reboot with a specific address."""
    scanner = AIOBulbScanner()

    task = asyncio.ensure_future(
        scanner.async_reboot(
            timeout=10,
            address="192.168.213.252",
        )
    )
    transport, protocol = await mock_discovery_aio_protocol()
    protocol.datagram_received(
        b"192.168.213.252,B4E842E10588,AK001-ZJ2145", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(b"+ok\r", ("192.168.213.252", 48899))
    await task
    assert transport.mock_calls == [
        call.sendto(b"HF-A11ASSISTHREAD", ("192.168.213.252", 48899)),
        call.sendto(b"AT+Z\r", ("192.168.213.252", 48899)),
        call.close(),
    ]


@pytest.mark.asyncio
async def test_async_scanner_disable_remote_access_timeout(mock_discovery_aio_protocol):
    """Test scanner disable remote access with a specific address failure."""
    scanner = AIOBulbScanner()
    task = asyncio.ensure_future(
        scanner.async_disable_remote_access(
            timeout=0.02,
            address="192.168.213.252",
        )
    )
    transport, protocol = await mock_discovery_aio_protocol()
    protocol.datagram_received(
        b"192.168.213.252,B4E842E10588,AK001-ZJ2145", ("192.168.213.252", 48899)
    )
    protocol.datagram_received(b"+ok\r", ("192.168.213.252", 48899))
    with pytest.raises(asyncio.TimeoutError):
        await task
    assert transport.mock_calls == [
        call.sendto(b"HF-A11ASSISTHREAD", ("192.168.213.252", 48899)),
        call.sendto(b"AT+SOCKB=NONE\r", ("192.168.213.252", 48899)),
        call.sendto(b"AT+Z\r", ("192.168.213.252", 48899)),
        call.close(),
    ]


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
