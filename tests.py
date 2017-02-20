import unittest
import unittest.mock as mock
from unittest.mock import Mock, MagicMock, patch

import flux_led   


class TestLight(unittest.TestCase):
    @patch('flux_led.WifiLedBulb._send_msg')
    @patch('flux_led.WifiLedBulb._read_msg')
    def test_connect(self, mock_read, mock_send):
        """Test setup with minimum configuration."""
        calls = 0
        def read_data(expected):
            self.assertEqual(expected, 14)
            nonlocal calls
            calls += 1
            if calls == 1:
                return bytearray(b'\x81D#a!\x10g\xffh\x00\x04\x00\xf0<')

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.166")
        self.assertEqual(mock_read.call_count, 1)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.__str__(), "ON  [Color: (103, 255, 104) Brightness: 255 raw state: 129,68,35,97,33,16,103,255,104,0,4,0,240,60,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.getRgb(), (103, 255, 104))

    @patch('flux_led.WifiLedBulb._send_msg')
    @patch('flux_led.WifiLedBulb._read_msg')
    def test_rgb(self, mock_read, mock_send):
        calls = 0
        def read_data(expected):
            self.assertEqual(expected, 14)
            nonlocal calls
            calls += 1
            if calls == 1:
                return bytearray(b'\x81D#a!\x10g\xffh\x00\x04\x00\xf0<')
            if calls == 2:
                return bytearray(b'\x81D#a!\x10\x01\x19P\x00\x04\x00\xf0\xd8')

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 1)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        light.setRgb(1, 25, 80)
        self.assertEqual(mock_read.call_count, 1)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'1\x01\x19P\x00\xf0\x0f'))
        )

        light.update_state()
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.__str__(), "ON  [Color: (1, 25, 80) Brightness: 80 raw state: 129,68,35,97,33,16,1,25,80,0,4,0,240,216,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))

    @patch('flux_led.WifiLedBulb._send_msg')
    @patch('flux_led.WifiLedBulb._read_msg')
    def test_off_on(self, mock_read, mock_send):
        calls = 0
        def read_data(expected):
            self.assertEqual(expected, 14)
            nonlocal calls
            calls += 1
            if calls == 1:
                return bytearray(b'\x81D#a!\x10\x00\x00\x00\xa6\x04\x00\x0f3')
            if calls == 2:
                return bytearray(b'\x81D$a!\x10\x00\x00\x00\xa6\x04\x00\x0f4')

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(light.__str__(), "ON  [Warm White: 65% raw state: 129,68,35,97,33,16,0,0,0,166,4,0,15,51,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 166)
        self.assertEqual(light.getRgb(), (255, 255, 255))
        self.assertEqual(mock_read.call_count, 1)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        light.turnOff()
        self.assertEqual(mock_read.call_count, 1)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'q$\x0f'))
        )

        light.update_state()
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.__str__(), "False [Warm White: 65% raw state: 129,68,36,97,33,16,0,0,0,166,4,0,15,52,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, False)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 166)
        self.assertEqual(light.getRgb(), (255, 255, 255))


    @patch('flux_led.WifiLedBulb._send_msg')
    @patch('flux_led.WifiLedBulb._read_msg')
    def test_ww(self, mock_read, mock_send):
        calls = 0
        def read_data(expected):
            self.assertEqual(expected, 14)
            nonlocal calls
            calls += 1
            if calls == 1:
                return bytearray(b'\x81D#a!\x10\xb6\x00\x98\x00\x04\x00\xf0\xbc')
            if calls == 2:
                return bytearray(b'\x81D#a!\x10\x00\x00\x00\x19\x04\x00\x0f\xa6')

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 1)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        light.setWarmWhite255(25)
        self.assertEqual(mock_read.call_count, 1)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'1\x00\x00\x00\x19\x0f\x0f'))
        )

        light.update_state()
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.__str__(), "ON  [Warm White: 9% raw state: 129,68,35,97,33,16,0,0,0,25,4,0,15,166,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 25)
        self.assertEqual(light.getRgb(), (255, 255, 255))