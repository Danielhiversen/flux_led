import asyncio
import contextlib
import datetime
import logging
from unittest.mock import MagicMock, patch

import pytest

from flux_led import aiodevice
from flux_led.aio import AIOWifiLedBulb
from flux_led.aioprotocol import AIOLEDENETProtocol
from flux_led.aioscanner import AIOBulbScanner, LEDENETDiscovery
from flux_led.const import COLOR_MODE_CCT, COLOR_MODE_RGBWW
from flux_led.protocol import PROTOCOL_LEDENET_9BYTE


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
    assert light.model == "RGB/WW/CW Controller (0x25)"
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
    with patch.object(aiodevice, "POWER_STATE_TIMEOUT", 0.05):
        await asyncio.create_task(light.async_turn_off())
        assert light.is_on is True
        assert "Failed to turn off (1/3)" in caplog.text
        assert "Failed to turn off (2/3)" in caplog.text
        assert "Failed to turn off (3/3)" in caplog.text

    with patch.object(aiodevice, "POWER_STATE_TIMEOUT", 0.05):
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
    with patch.object(aiodevice, "POWER_STATE_TIMEOUT", 0.05):
        await asyncio.create_task(light.async_turn_on())
        assert light.is_on is False
        assert "Failed to turn on (1/3)" in caplog.text
        assert "Failed to turn on (2/3)" in caplog.text
        assert "Failed to turn on (3/3)" in caplog.text


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
    light._aio_protocol.data_received(
        b"\x81\xA3#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd5"
    )
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
    await task
    assert light.model_num == 0xA3

    transport.reset_mock()
    await light.async_set_effect("random", 50)
    assert transport.mock_calls[0][0] == "write"
    assert transport.mock_calls[0][1][0].startswith(b"\xb0\xb1\xb2\xb3")

    transport.reset_mock()
    await light.async_set_effect("RBM 1", 50)
    assert transport.mock_calls[0][0] == "write"
    assert (
        transport.mock_calls[0][1][0]
        == b"\xb0\xb1\xb2\xb3\x00\x01\x01\x02\x00\x05B\x012d\x00\xa8"
    )


@pytest.mark.asyncio
async def test_async_set_brightness(mock_aio_protocol):
    """Test we can set brightness."""
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
            "model_description": "RGB Controller with MIC",
            "model_info": "ZG-BL",
            "model_num": 8,
            "version_num": 21,
        },
        {
            "firmware_date": datetime.date(2020, 4, 28),
            "id": "F4CFA23E1AAF",
            "ipaddr": "192.168.213.65",
            "model": "AK001-ZJ2104",
            "model_description": "RGB Symphony v2",
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
            "model_description": "RGB Controller with MIC",
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
        "model_description": "RGB Controller with MIC",
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
            "model_description": "RGB Controller with MIC",
            "model_info": "ZG-BL",
            "model_num": 8,
            "version_num": 21,
        }
    ]


@pytest.mark.asyncio
async def test_async_scanner_times_out_with_nothing(mock_discovery_aio_protocol):
    """Test scanner."""
    scanner = AIOBulbScanner()

    task = asyncio.ensure_future(scanner.async_scan(timeout=0.0000001))
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
        scanner.async_scan(timeout=0.0000001, address="192.168.213.252")
    )
    transport, protocol = await mock_discovery_aio_protocol()
    data = await task
    assert data == []
