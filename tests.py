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
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b'\x81D')
            if calls == 2:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81E#a!\x10g\xffh\x00\x04\x00\xf0<')

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.166")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.__str__(), "ON  [Color: (103, 255, 104) Brightness: 255 raw state: 129,69,35,97,33,16,103,255,104,0,4,0,240,60,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.getRgb(), (103, 255, 104))
        self.assertEqual(light.rgbwcapable, False)

    @patch('flux_led.WifiLedBulb._send_msg')
    @patch('flux_led.WifiLedBulb._read_msg')


    def test_rgb(self, mock_read, mock_send):
        calls = 0
        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b'\x81D')
            if calls == 2:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81E#a!\x10g\xffh\x00\x04\x00\xf0<')
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81E#a!\x10\x01\x19P\x00\x04\x00\xf0\xd8')

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2) 
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        light.setRgb(1, 25, 80)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'1\x01\x19P\x00\xf0\x0f'))
        )

        light.update_state()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 4)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.__str__(), "ON  [Color: (1, 25, 80) Brightness: 80 raw state: 129,69,35,97,33,16,1,25,80,0,4,0,240,216,]")
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
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b'\x81E')
            if calls == 2:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81E#a!\x10\x00\x00\x00\xa6\x04\x00\x0f3')
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81E$a!\x10\x00\x00\x00\xa6\x04\x00\x0f4')

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(light.__str__(), "ON  [Warm White: 65% raw state: 129,69,35,97,33,16,0,0,0,166,4,0,15,51,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 166)
        self.assertEqual(light.getRgb(), (255, 255, 255))
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        light.turnOff()
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'q$\x0f'))
        )

        light.update_state()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 4)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.__str__(), "OFF  [Warm White: 65% raw state: 129,69,36,97,33,16,0,0,0,166,4,0,15,52,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, False)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 166)
        self.assertEqual(light.getRgb(), (255, 255, 255))
        self.assertEqual(light.rgbwcapable, False)

    @patch('flux_led.WifiLedBulb._send_msg')
    @patch('flux_led.WifiLedBulb._read_msg')
    def test_ww(self, mock_read, mock_send):
        calls = 0
        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b'\x81E')
            if calls == 2:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81E#a!\x10\xb6\x00\x98\x00\x04\x00\xf0\xbc')
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81E#a!\x10\x00\x00\x00\x19\x04\x00\x0f\xa6')

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.__str__(), "ON  [Color: (182, 0, 152) Brightness: 182 raw state: 129,69,35,97,33,16,182,0,152,0,4,0,240,188,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 182)
        self.assertEqual(light.getRgb(), (182, 0, 152))
        self.assertEqual(light.rgbwcapable, False)

        light.setWarmWhite255(25)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'1\x00\x00\x00\x19\x0f\x0f'))
        )

        light.update_state()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 4)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.__str__(), "ON  [Warm White: 9% raw state: 129,69,35,97,33,16,0,0,0,25,4,0,15,166,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 25)
        self.assertEqual(light.getRgb(), (255, 255, 255))
        self.assertEqual(light.rgbwcapable, False)


    @patch('flux_led.WifiLedBulb._send_msg')
    @patch('flux_led.WifiLedBulb._read_msg')
    def test_rgb_brightness(self, mock_read, mock_send):
        calls = 0
        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b'\x81E')
            if calls == 2:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81E$a!\x10\xff[\xd4\x00\x04\x00\xf0\x9d')
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81E#a!\x10\x03M\xf7\x00\x04\x00\xf0\xb5')

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )
        self.assertEqual(light.__str__(), "OFF  [Color: (255, 91, 212) Brightness: 255 raw state: 129,69,36,97,33,16,255,91,212,0,4,0,240,157,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, False)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.getRgb(), (255, 91, 212))

        light.turnOn()
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'q#\x0f'))
        )
        self.assertEqual(light.__str__(), "OFF  [Color: (255, 91, 212) Brightness: 255 raw state: 129,69,36,97,33,16,255,91,212,0,4,0,240,157,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.getRgb(), (255, 91, 212))

        light.setRgb(1, 25, 80, brightness=247)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 4)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'1\x03M\xf7\x00\xf0\x0f'))
        )
        self.assertEqual(light.__str__(), "OFF  [Color: (255, 91, 212) Brightness: 255 raw state: 129,69,36,97,33,16,255,91,212,0,4,0,240,157,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.getRgb(), (255, 91, 212))

        light.update_state()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 5)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )
        self.assertEqual(light.__str__(), "ON  [Color: (3, 77, 247) Brightness: 247 raw state: 129,69,35,97,33,16,3,77,247,0,4,0,240,181,]")
        self.assertEqual(light.protocol, None)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 247)
        self.assertEqual(light.getRgb(), (3, 77, 247))

    @patch('flux_led.WifiLedBulb._send_msg')
    @patch('flux_led.WifiLedBulb._read_msg')
    def test_rgbwwcw(self, mock_read, mock_send):
        calls = 0
        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b'\x81D')
            if calls == 2:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81\x25\x23\x61\x21\x10\xb6\x00\x98\x00\x04\x00\xf0\xbc')
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(b'\x81\x25\x23\x61\x21\x10\xb6\x00\x98\x19\x04\x25\x0f\xa6')

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.protocol, 'LEDENET')
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 182)
        self.assertEqual(light.getRgb(), (182, 0, 152))
        self.assertEqual(light.rgbwcapable, True)
        self.assertEqual(light.__str__(), "ON  [Color: (182, 0, 152) White: 0 raw state: 129,37,35,97,33,16,182,0,152,0,4,0,240,188,]")

        light.setWarmWhite255(25)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'1\x00\x00\x00\x19\x19\x0f\x0f'))
        )

        light.update_state()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 4)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\x81\x8a\x8b'))
        )

        self.assertEqual(light.protocol, 'LEDENET')
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 25)
        self.assertEqual(light.cold_white, 37)
        self.assertEqual(light.brightness, 182)
        self.assertEqual(light.getRgbww(), (182, 0, 152, 25, 37))
        self.assertEqual(light.rgbwcapable, True)
        self.assertEqual(light.__str__(), "ON  [Color: (182, 0, 152) White: 25 raw state: 129,37,35,97,33,16,182,0,152,25,4,37,15,166,]")

    @patch('flux_led.WifiLedBulb._send_msg')
    @patch('flux_led.WifiLedBulb._read_msg')
    def test_original_ledenet(self, mock_read, mock_send):
        calls = 0
        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b'')
            if calls == 2:
                self.assertEqual(expected, 2)
                return bytearray(b'\f\x01')
            if calls == 3:
                self.assertEqual(expected, 11)
                return bytearray(b'f\x01#A!\x08\xff\x80*\x01\x99')
            if calls == 4:
                self.assertEqual(expected, 11)
                return bytearray(b'f\x01#A!\x08\x01\x19P\x01\x99')
            if calls == 5:
                self.assertEqual(expected, 11)
                return bytearray(b'f\x01$A!\x08\x01\x19P\x01\x99')
            if calls == 6:
                self.assertEqual(expected, 11)
                return bytearray(b'f\x01#A!\x08\x01\x19P\x01\x99')


        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 3) 
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\xef\x01w'))
        )

        light.setRgb(1, 25, 80)
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 4)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'V\x01\x19P\xaa'))
        )

        light.update_state()
        self.assertEqual(mock_read.call_count, 4)
        self.assertEqual(mock_send.call_count, 5)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\xef\x01w'))
        )

        self.assertEqual(light.__str__(), "ON  [Color: (1, 25, 80) Brightness: 80 raw state: 102,1,35,65,33,8,1,25,80,1,153,]")
        self.assertEqual(light.protocol, 'LEDENET_ORIGINAL')
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))


        light.turnOff()
        self.assertEqual(mock_read.call_count, 4)
        self.assertEqual(mock_send.call_count, 6)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\xcc$3'))
        )

        light.update_state()
        self.assertEqual(mock_read.call_count, 5)
        self.assertEqual(mock_send.call_count, 7)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\xef\x01w'))
        )

        self.assertEqual(light.__str__(), 'OFF  [Color: (1, 25, 80) Brightness: 80 raw state: 102,1,36,65,33,8,1,25,80,1,153,]')
        self.assertEqual(light.protocol, 'LEDENET_ORIGINAL')
        self.assertEqual(light.is_on, False)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))


        light.turnOn()
        self.assertEqual(mock_read.call_count, 5)
        self.assertEqual(mock_send.call_count, 8)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\xcc#3'))
        )

        light.update_state()
        self.assertEqual(mock_read.call_count, 6)
        self.assertEqual(mock_send.call_count, 9)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b'\xef\x01w'))
        )

        self.assertEqual(light.__str__(), "ON  [Color: (1, 25, 80) Brightness: 80 raw state: 102,1,35,65,33,8,1,25,80,1,153,]")
        self.assertEqual(light.protocol, 'LEDENET_ORIGINAL')
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))
