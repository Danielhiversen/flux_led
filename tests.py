import unittest
import unittest.mock as mock
from unittest.mock import MagicMock, Mock, patch

import flux_led

LEDENET_STATE_QUERY = b"\x81\x8a\x8b\x96"

from flux_led.protocol import (
    PROTOCOL_LEDENET_ORIGINAL,
    PROTOCOL_LEDENET_9BYTE,
    PROTOCOL_LEDENET_8BYTE,
)


class TestLight(unittest.TestCase):
    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_connect(self, mock_connect, mock_read, mock_send):
        """Test setup with minimum configuration."""
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81E")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"#a!\x10g\xffh\x00\x04\x00\xf0\x3d")
            raise Exception

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.166")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (103, 255, 104) Brightness: 255 raw state: 129,69,35,97,33,16,103,255,104,0,4,0,240,61,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.getRgb(), (103, 255, 104))
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_rgb(self, mock_connect, mock_read, mock_send):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81E")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"#a!\x10g\xffh\x00\x04\x00\xf0\x3d")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(b"\x81E#a!\x10\x01\x19P\x00\x04\x00\xf0\xd9")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        light.setRgb(1, 25, 80)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args, mock.call(bytearray(b"1\x01\x19P\x00\xf0\x0f\x9a"))
        )
        self.assertEqual(light.getRgb(), (1, 25, 80))

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (1, 25, 80) Brightness: 80 raw state: 129,69,35,97,33,16,1,25,80,0,4,0,240,217,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_off_on(self, mock_connect, mock_read, mock_send):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81E")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"#a!\x10\x00\x00\x00\xa6\x04\x00\x0f\x34")
            if calls == 3:  # turn off response
                self.assertEqual(expected, 4)
                return bytearray(b"\x0fq#\xa3")
            if calls == 4:
                self.assertEqual(expected, 14)
                return bytearray(b"\x81E$a!\x10\x00\x00\x00\xa6\x04\x00\x0f4")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(
            light.__str__(),
            "ON  [Warm White: 65% raw state: 129,69,35,97,33,16,0,0,0,166,4,0,15,52,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 166)
        self.assertEqual(light.getRgb(), (255, 255, 255))
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        light.turnOff()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"q$\x0f\xa4")))

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 4)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"\x81\x8a\x8b\x96")))

        self.assertEqual(
            light.__str__(),
            "OFF  [Warm White: 65% raw state: 129,69,36,97,33,16,0,0,0,166,4,0,15,52,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, False)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 166)
        self.assertEqual(light.getRgb(), (255, 255, 255))
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_ww(self, mock_connect, mock_read, mock_send):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81E")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"#a!\x10\xb6\x00\x98\x00\x04\x00\xf0\xbd")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(b"\x81E#a!\x10\x00\x00\x00\x19\x04\x00\x0f\xa7")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (182, 0, 152) Brightness: 182 raw state: 129,69,35,97,33,16,182,0,152,0,4,0,240,189,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 182)
        self.assertEqual(light.getRgb(), (182, 0, 152))
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)

        light.setWarmWhite255(25)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args, mock.call(bytearray(b"1\x00\x00\x00\x19\x0f\x0fh"))
        )

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"\x81\x8a\x8b\x96")))

        self.assertEqual(
            light.__str__(),
            "ON  [Warm White: 9% raw state: 129,69,35,97,33,16,0,0,0,25,4,0,15,167,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 25)
        self.assertEqual(light.getRgb(), (255, 255, 255))
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_switch(self, mock_connect, mock_read, mock_send):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81\x97")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"$$\x00\x00\x00\x00\x00\x00\x02\x00\x00b")
            if calls == 3:  # turn on response
                self.assertEqual(expected, 4)
                return bytearray(b"\x0fq#\xa3")
            if calls == 4:
                self.assertEqual(expected, 14)
                return bytearray(b"\x81\x97##\x00\x00\x00\x00\x00\x00\x02\x00\x00`")

        mock_read.side_effect = read_data
        switch = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"\x81\x8a\x8b\x96")))

        self.assertEqual(
            switch.__str__(),
            "OFF  [Switch raw state: 129,151,36,36,0,0,0,0,0,0,2,0,0,98,]",
        )
        self.assertEqual(switch.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(switch.is_on, False)
        self.assertEqual(switch.mode, "switch")
        self.assertEqual(switch.device_type, flux_led.DeviceType.Switch)

        switch.turnOn()
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"q#\x0f\xa3")))
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 2)

        switch._transition_complete_time = 0
        switch.update_state()
        self.assertEqual(mock_read.call_count, 4)
        self.assertEqual(mock_send.call_count, 3)

        self.assertEqual(
            switch.__str__(),
            "ON  [Switch raw state: 129,151,35,35,0,0,0,0,0,0,2,0,0,96,]",
        )
        self.assertEqual(switch.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(switch.is_on, True)
        self.assertEqual(switch.device_type, flux_led.DeviceType.Switch)

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_rgb_brightness(self, mock_connect, mock_read, mock_send):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:  # first part of state response
                self.assertEqual(expected, 2)
                return bytearray(b"\x81E")
            if calls == 2:  # second part of state response
                self.assertEqual(expected, 12)
                return bytearray(b"$a!\x10\xff[\xd4\x00\x04\x00\xf0\x9e")
            if calls == 3:  # turn on response
                self.assertEqual(expected, 4)
                return bytearray(b"\x0fq#\xa3")
            if calls == 4:
                self.assertEqual(expected, 14)
                return bytearray(b"\x81E#a!\x10\x03M\xf7\x00\x04\x00\xf0\xb6")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))
        self.assertEqual(
            light.__str__(),
            "OFF  [Color: (255, 91, 212) Brightness: 255 raw state: 129,69,36,97,33,16,255,91,212,0,4,0,240,158,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, False)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.getRgb(), (255, 91, 212))
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)

        light.turnOn()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"q#\x0f\xa3")))
        self.assertEqual(
            light.__str__(),
            "ON  [Color: (255, 91, 212) Brightness: 255 raw state: 129,69,35,97,33,16,255,91,212,0,4,0,240,158,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.getRgb(), (255, 91, 212))

        light.setRgb(1, 25, 80, brightness=247)
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args, mock.call(bytearray(b"1\x03M\xf7\x00\xf0\x0fw"))
        )
        self.assertEqual(
            light.__str__(),
            "ON  [Color: (3, 77, 247) Brightness: 247 raw state: 129,69,35,97,33,16,3,77,247,0,4,0,240,158,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 247)
        self.assertEqual(light.getRgb(), (3, 77, 247))

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 4)
        self.assertEqual(mock_send.call_count, 4)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))
        self.assertEqual(
            light.__str__(),
            "ON  [Color: (3, 77, 247) Brightness: 247 raw state: 129,69,35,97,33,16,3,77,247,0,4,0,240,182,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 247)
        self.assertEqual(light.getRgb(), (3, 77, 247))

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_rgbww(self, mock_connect, mock_read, mock_send):

        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81\x25")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"\x23\x61\x21\x10\xb6\x00\x98\x00\x04\x00\xf0\x9d")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(
                    b"\x81\x25\x23\x61\x21\x10\xb6\x00\x98\x19\x04\x25\x0f\xfa"
                )

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(light.protocol, PROTOCOL_LEDENET_9BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 182)
        self.assertEqual(light.getRgb(), (182, 0, 152))
        self.assertEqual(light.rgbwcapable, True)
        self.assertEqual(
            light.__str__(),
            "ON  [Color: (182, 0, 152) White: 0 raw state: 129,37,35,97,33,16,182,0,152,0,4,0,240,157,]",
        )

        light.setWarmWhite255(25)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b"1\x00\x00\x00\x19\x19\x0f\x0f\x81")),
        )

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(light.protocol, PROTOCOL_LEDENET_9BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 25)
        self.assertEqual(light.cold_white, 37)
        self.assertEqual(light.brightness, 182)
        self.assertEqual(light.getRgbww(), (182, 0, 152, 25, 37))
        self.assertEqual(light.rgbwcapable, True)
        self.assertEqual(
            light.__str__(),
            "ON  [Color: (182, 0, 152) White: 25 raw state: 129,37,35,97,33,16,182,0,152,25,4,37,15,250,]",
        )

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_original_ledenet(self, mock_connect, mock_read, mock_send):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"")
            if calls == 2:
                self.assertEqual(expected, 2)
                return bytearray(b"\f\x01")
            if calls == 3:
                self.assertEqual(expected, 9)
                return bytearray(b"#A!\x08\xff\x80*\x01\x99")
            if calls == 4:
                self.assertEqual(expected, 11)
                return bytearray(b"f\x01#A!\x08\x01\x19P\x01\x99")
            if calls == 5:  # ready turn off response
                self.assertEqual(expected, 4)
                return bytearray(b"\x0fq#\xa3")
            if calls == 6:
                self.assertEqual(expected, 11)
                return bytearray(b"f\x01$A!\x08\x01\x19P\x01\x99")
            if calls == 7:  # ready turn on response
                self.assertEqual(expected, 4)
                return bytearray(b"\x0fq#\xa3")
            if calls == 8:
                self.assertEqual(expected, 11)
                return bytearray(b"f\x01#A!\x08\x01\x19P\x01\x99")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"\xef\x01w")))

        light.setRgb(1, 25, 80)
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"V\x01\x19P\xaa")))

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 4)
        self.assertEqual(mock_send.call_count, 4)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"\xef\x01w")))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (1, 25, 80) Brightness: 80 raw state: 102,1,35,65,33,8,1,25,80,1,153,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_ORIGINAL)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))

        light.turnOff()
        self.assertEqual(mock_read.call_count, 5)
        self.assertEqual(mock_send.call_count, 5)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"\xcc$3")))

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 6)
        self.assertEqual(mock_send.call_count, 6)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"\xef\x01w")))

        self.assertEqual(
            light.__str__(),
            "OFF  [Color: (1, 25, 80) Brightness: 80 raw state: 102,1,36,65,33,8,1,25,80,1,153,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_ORIGINAL)
        self.assertEqual(light.is_on, False)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))

        light.turnOn()
        self.assertEqual(mock_read.call_count, 7)
        self.assertEqual(mock_send.call_count, 7)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"\xcc#3")))

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 8)
        self.assertEqual(mock_send.call_count, 8)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"\xef\x01w")))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (1, 25, 80) Brightness: 80 raw state: 102,1,35,65,33,8,1,25,80,1,153,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_ORIGINAL)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_state_transition(self, mock_connect, mock_read, mock_send):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81E")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"#a!\x10g\xffh\x00\x04\x00\xf0=")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(b"\x81E#a!\x10\x01\x19P\x00\x04\x00\xf0\xd9")
            if calls == 4:
                self.assertEqual(expected, 14)
                return bytearray(b"\x81E#a!\x10\x01\x19P\x00\x04\x00\xf0\xd9")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        light.setRgb(50, 100, 50)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args, mock.call(bytearray(b"12d2\x00\xf0\x0f\xf8"))
        )
        self.assertEqual(light.getRgb(), (50, 100, 50))

        # While a transition is in progress we do not update
        # internal state
        light.update_state()
        self.assertEqual(light.getRgb(), (50, 100, 50))

        # Now that the transition has completed state should
        # be updated, we mock the bulb to replay with an
        # RGB state of (1, 25, 80)
        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 4)
        self.assertEqual(mock_send.call_count, 4)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (1, 25, 80) Brightness: 80 raw state: 129,69,35,97,33,16,1,25,80,0,4,0,240,217,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)
