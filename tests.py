import unittest
import unittest.mock as mock
from unittest.mock import patch

import pytest

import flux_led
from flux_led.const import (
    COLOR_MODE_CCT,
    COLOR_MODE_DIM,
    COLOR_MODE_RGB,
    COLOR_MODE_RGBW,
    COLOR_MODE_RGBWW,
    STATE_BLUE,
    STATE_GREEN,
    STATE_RED,
    STATE_WARM_WHITE,
)
from flux_led.protocol import (
    PROTOCOL_LEDENET_8BYTE,
    PROTOCOL_LEDENET_9BYTE,
    PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS,
    PROTOCOL_LEDENET_ADDRESSABLE_A1,
    PROTOCOL_LEDENET_ADDRESSABLE_A2,
    PROTOCOL_LEDENET_ADDRESSABLE_A3,
    PROTOCOL_LEDENET_ORIGINAL,
)
from flux_led.utils import rgbw_brightness, rgbww_brightness

LEDENET_STATE_QUERY = b"\x81\x8a\x8b\x96"


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
        assert light.color_modes == {COLOR_MODE_RGB, COLOR_MODE_DIM}

        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (103, 255, 104) Brightness: 100% raw state: 129,69,35,97,33,16,103,255,104,0,4,0,240,61,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.model_num, 0x45)
        self.assertEqual(light.model, "Unknown Model (0x45)")
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.getRgb(), (103, 255, 104))
        self.assertEqual(light.rgb, (103, 255, 104))
        self.assertEqual(light.rgb_unscaled, (103, 255, 104))
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
        self.assertEqual(light.model_num, 0x45)
        self.assertEqual(light.model, "Unknown Model (0x45)")
        assert light.color_modes == {COLOR_MODE_RGB, COLOR_MODE_DIM}

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
        self.assertEqual(light.rgb, (1, 25, 80))
        self.assertEqual(light.rgb_unscaled, (3, 80, 255))

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 3)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (1, 25, 80) Brightness: 31% raw state: 129,69,35,97,33,16,1,25,80,0,4,0,240,217,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)
        self.assertEqual(light.version_num, 4)

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
        assert light.color_modes == {COLOR_MODE_RGB, COLOR_MODE_DIM}

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
        assert light.color_modes == {COLOR_MODE_RGB, COLOR_MODE_DIM}

        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (182, 0, 152) Brightness: 71% raw state: 129,69,35,97,33,16,182,0,152,0,4,0,240,189,]",
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
        assert switch.color_modes == {}

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
        assert light.color_modes == {COLOR_MODE_RGB, COLOR_MODE_DIM}

        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))
        self.assertEqual(
            light.__str__(),
            "OFF  [Color: (255, 91, 212) Brightness: 100% raw state: 129,69,36,97,33,16,255,91,212,0,4,0,240,158,]",
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
            "ON  [Color: (255, 91, 212) Brightness: 100% raw state: 129,69,35,97,33,16,255,91,212,0,4,0,240,158,]",
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
            "ON  [Color: (3, 77, 247) Brightness: 97% raw state: 129,69,35,97,33,16,3,77,247,0,4,0,240,158,]",
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
            "ON  [Color: (3, 77, 247) Brightness: 97% raw state: 129,69,35,97,33,16,3,77,247,0,4,0,240,182,]",
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
                return bytearray(b"\x23\x61\x05\x10\xb6\x00\x98\x00\x04\x00\xf0\x81")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(
                    b"\x81\x25\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xde"
                )
            if calls == 4:
                self.assertEqual(expected, 14)
                return bytearray(
                    b"\x81\x25\x23\x38\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xb5"
                )

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        assert light.color_modes == {COLOR_MODE_RGBWW, COLOR_MODE_CCT}
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_9BYTE)
        self.assertEqual(light.model_num, 0x25)
        self.assertEqual(light.microphone, False)
        self.assertEqual(light.model, "RGB/WW/CW Controller (0x25)")
        self.assertEqual(
            light.effect_list,
            [
                "blue_fade",
                "blue_strobe",
                "colorjump",
                "colorloop",
                "colorstrobe",
                "cyan_fade",
                "cyan_strobe",
                "gb_cross_fade",
                "green_fade",
                "green_strobe",
                "purple_fade",
                "purple_strobe",
                "rb_cross_fade",
                "red_fade",
                "red_strobe",
                "rg_cross_fade",
                "white_fade",
                "white_strobe",
                "yellow_fade",
                "yellow_strobe",
                "random",
            ],
        )

        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(light.protocol, PROTOCOL_LEDENET_9BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.min_temp, 2700)
        self.assertEqual(light.max_temp, 6500)

        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 61)  # RGBWW brightness
        self.assertEqual(light.getRgb(), (182, 0, 152))
        self.assertEqual(light.getRgbw(), (182, 0, 152, 0))
        self.assertEqual(light.getRgbww(), (182, 0, 152, 0, 0))

        self.assertEqual(light.rgbwcapable, True)
        self.assertEqual(
            light.__str__(),
            "ON  [Color: (182, 0, 152) White: 0 raw state: 129,37,35,97,5,16,182,0,152,0,4,0,240,129,]",
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
        self.assertEqual(light.brightness, 81)  # RGBWW brighness
        self.assertEqual(light.rgbw, (182, 0, 152, 25))
        self.assertEqual(light.getRgbw(), (182, 0, 152, 25))
        self.assertEqual(light.rgbww, (182, 0, 152, 25, 37))
        self.assertEqual(light.getRgbww(), (182, 0, 152, 25, 37))
        self.assertEqual(light.rgbcw, (182, 0, 152, 37, 25))
        self.assertEqual(light.getRgbcw(), (182, 0, 152, 37, 25))
        self.assertEqual(light.rgbwcapable, True)
        self.assertEqual(light.dimmable_effects, False)
        self.assertEqual(
            light.__str__(),
            "ON  [Color: (182, 0, 152) White: 25 raw state: 129,37,35,97,5,16,182,0,152,25,4,37,15,222,]",
        )

        # Home Assistant legacy names
        light.set_effect("colorjump", 50, 100)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"a8\x10\x0f\xb8")))

        # Library names
        light.set_effect("seven_color_jumping", 50, 60)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"a8\x10\x0f\xb8")))

        with pytest.raises(ValueError):
            light.set_effect("unknown", 50)

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 4)
        self.assertEqual(mock_send.call_count, 6)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))
        self.assertEqual(light.mode, "preset")
        self.assertEqual(light.effect, "colorjump")
        self.assertEqual(light.brightness, 81)

        self.assertEqual(light.preset_pattern_num, 0x38)
        self.assertEqual(
            light.__str__(),
            "ON  [Pattern: colorjump (Speed 50%) raw state: 129,37,35,56,5,16,182,0,152,25,4,37,15,181,]",
        )

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_rgbcw_bulb(self, mock_connect, mock_read, mock_send):

        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81\x35")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"\x23\x61\x05\x10\xb6\x00\x98\x00\x04\x00\xf0\x91")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(
                    b"\x81\x35\x23\x61\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xee"
                )
            if calls == 4:
                self.assertEqual(expected, 14)
                return bytearray(
                    b"\x81\x35\x23\x38\x05\x10\xb6\x00\x98\x19\x04\x25\x0f\xc5"
                )

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        assert light.color_modes == {COLOR_MODE_RGB, COLOR_MODE_CCT}
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS)
        self.assertEqual(light.model_num, 0x35)
        self.assertEqual(light.microphone, False)
        self.assertEqual(light.model, "Smart Bulb RGBCW (0x35)")
        self.assertEqual(
            light.effect_list,
            [
                "blue_fade",
                "blue_strobe",
                "colorjump",
                "colorloop",
                "colorstrobe",
                "cyan_fade",
                "cyan_strobe",
                "gb_cross_fade",
                "green_fade",
                "green_strobe",
                "purple_fade",
                "purple_strobe",
                "rb_cross_fade",
                "red_fade",
                "red_strobe",
                "rg_cross_fade",
                "white_fade",
                "white_strobe",
                "yellow_fade",
                "yellow_strobe",
                "random",
            ],
        )

        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(light.protocol, PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.min_temp, 2700)
        self.assertEqual(light.max_temp, 6500)

        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 182)
        self.assertEqual(light.getRgb(), (182, 0, 152))
        self.assertEqual(light.getRgbw(), (182, 0, 152, 0))
        self.assertEqual(light.getRgbww(), (182, 0, 152, 0, 0))

        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(
            light.__str__(),
            (
                "ON  [Color: (182, 0, 152) Brightness: 71% raw state: "
                "129,53,35,97,5,16,182,0,152,0,4,0,240,145,]"
            ),
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

        self.assertEqual(light.protocol, PROTOCOL_LEDENET_9BYTE_DIMMABLE_EFFECTS)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.cold_white, 0)
        self.assertEqual(light.brightness, 62)
        self.assertEqual(light.rgbw, (182, 0, 152, 25))
        self.assertEqual(light.getRgbw(), (255, 255, 255, 255))
        self.assertEqual(light.rgbww, (182, 0, 152, 25, 37))
        self.assertEqual(light.getRgbww(), (255, 255, 255, 255, 255))
        self.assertEqual(light.rgbcw, (182, 0, 152, 37, 25))
        self.assertEqual(light.getRgbcw(), (255, 255, 255, 255, 255))
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(light.dimmable_effects, True)
        self.assertEqual(
            light.__str__(),
            (
                "ON  [CCT: 4968K Brightness: 24% raw state: "
                "129,53,35,97,5,16,182,0,152,25,4,37,15,238,]"
            ),
        )

        # Home Assistant legacy names
        light.set_effect("colorjump", 50, 100)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"88\x10d\xe4")))

        # Library names
        light.set_effect("seven_color_jumping", 50, 60)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"88\x10<\xbc")))

        with pytest.raises(ValueError):
            light.set_effect("unknown", 50)

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 4)
        self.assertEqual(mock_send.call_count, 6)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))
        self.assertEqual(light.mode, "preset")
        self.assertEqual(light.effect, "colorjump")
        self.assertEqual(light.brightness, 153)

        self.assertEqual(light.preset_pattern_num, 0x38)
        self.assertEqual(
            light.__str__(),
            (
                "ON  [Pattern: colorjump (Speed 50%) raw state: "
                "129,53,35,56,5,16,182,0,152,25,4,37,15,197,]"
            ),
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
                return bytearray(b"f\x01")
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
        assert light.color_modes == {COLOR_MODE_RGB}
        self.assertEqual(light.model_num, 0x01)
        self.assertEqual(light.model, "Original LEDENET (0x01)")
        self.assertEqual(light.dimmable_effects, False)

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
            "ON  [Color: (1, 25, 80) Brightness: 31% raw state: 102,1,35,65,33,8,1,25,80,1,153,]",
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
            "OFF  [Color: (1, 25, 80) Brightness: 31% raw state: 102,1,36,65,33,8,1,25,80,1,153,]",
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
            "ON  [Color: (1, 25, 80) Brightness: 31% raw state: 102,1,35,65,33,8,1,25,80,1,153,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_ORIGINAL)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))
        self.assertEqual(light.version_num, 1)

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
        assert light.color_modes == {COLOR_MODE_RGB, COLOR_MODE_DIM}

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
            "ON  [Color: (1, 25, 80) Brightness: 31% raw state: 129,69,35,97,33,16,1,25,80,0,4,0,240,217,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 80)
        self.assertEqual(light.getRgb(), (1, 25, 80))
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)

    def test_rgbww_brightness(self):
        assert rgbww_brightness((128, 128, 128, 128, 128), 255) == (
            255,
            255,
            255,
            255,
            255,
        )
        assert rgbww_brightness((128, 128, 128, 128, 128), 128) == (
            128,
            128,
            128,
            128,
            128,
        )
        assert rgbww_brightness((255, 255, 255, 255, 255), 128) == (
            128,
            128,
            128,
            128,
            128,
        )
        assert rgbww_brightness((0, 255, 0, 0, 0), 255) == (0, 255, 0, 255, 255)
        assert rgbww_brightness((0, 255, 0, 0, 0), 128) == (0, 255, 0, 64, 64)

    def test_rgbw_brightness(self):
        assert rgbw_brightness((128, 128, 128, 128), 255) == (255, 255, 255, 255)
        assert rgbw_brightness((128, 128, 128, 128), 128) == (128, 128, 128, 128)
        assert rgbw_brightness((255, 255, 255, 255), 128) == (128, 128, 128, 128)
        assert rgbw_brightness((0, 255, 0, 0), 255) == (0, 255, 0, 255)
        assert rgbw_brightness((0, 255, 0, 0), 128) == (0, 255, 0, 0)

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_unknown_model_detection_rgbw_cct(self, mock_connect, mock_read, mock_send):
        calls = 0
        model_not_in_db = 222

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray([129, model_not_in_db])
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"$$\x47\x00\x00\x00\x00\x00\x02\x00\x00\xf0")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(
                    b"\x81\xde\x23\x41\x47\x00\x00\x00\x00\x00\x02\xFF\x00\x0b"
                )

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        assert light.color_modes == {COLOR_MODE_RGB, COLOR_MODE_CCT}
        self.assertEqual(light.model_num, 0xDE)
        self.assertEqual(light.model, "Unknown Model (0xDE)")
        assert light.color_mode == COLOR_MODE_RGB
        light.update_state()
        assert light.color_mode == COLOR_MODE_CCT
        self.assertEqual(light.color_temp, 6500)
        self.assertEqual(light.isOn(), True)
        self.assertEqual(light.getCCT(), (0, 255))
        self.assertEqual(light.getWarmWhite255(), 255)
        self.assertEqual(light.getWhiteTemperature(), (6500, 255))
        self.assertEqual(
            light.__str__(),
            "ON  [CCT: 6500K Brightness: 100% raw state: 129,222,35,65,71,0,0,0,0,0,2,255,0,11,]",
        )

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_unknown_model_detection_rgb_dim(self, mock_connect, mock_read, mock_send):
        calls = 0
        model_not_in_db = 222

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray([129, model_not_in_db])
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"$$\x46\x00\x00\x00\x00\x00\x02\x00\x00\xef")

        mock_read.side_effect = read_data
        switch = flux_led.WifiLedBulb("192.168.1.164")
        assert switch.color_modes == {COLOR_MODE_RGB, COLOR_MODE_DIM}

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_unknown_model_detection_rgbww(self, mock_connect, mock_read, mock_send):
        calls = 0
        model_not_in_db = 222

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray([129, model_not_in_db])
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"$$\x45\x00\x00\x00\x00\x00\x02\x00\x00\xee")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        assert light.color_modes == {COLOR_MODE_RGBWW, COLOR_MODE_CCT}

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_unknown_model_detection_rgbw(self, mock_connect, mock_read, mock_send):
        calls = 0
        model_not_in_db = 222

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray([129, model_not_in_db])
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"$$\x44\x00\x00\x00\x00\x00\x02\x00\x00\xed")

        mock_read.side_effect = read_data
        switch = flux_led.WifiLedBulb("192.168.1.164")
        assert switch.color_modes == {COLOR_MODE_RGBW}

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_single_channel_remapping(self, mock_connect, mock_read, mock_send):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81\x41")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"#a\x41\x10\xff\x00\x00\x00\x04\x00\xf0\x8a")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(b"\x81\x41#a\x41\x10\x64\x00\x00\x00\x04\x00\xf0\xef")
            raise ValueError("Too many calls")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(light.model_num, 0x41)
        self.assertEqual(light.model, "Single Channel Controller (0x41)")
        assert light.color_modes == {COLOR_MODE_DIM}

        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Warm White: 100% raw state: 129,65,35,97,65,16,0,0,0,255,4,0,240,138,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_8BYTE)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "ww")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)

        light.setRgbw(0, 0, 0, w=0x80)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args, mock.call(bytearray(b"1\x80\x00\x00\x00\x00\x0f\xc0"))
        )
        assert light.raw_state.warm_white == 0x80
        self.assertEqual(
            light.__str__(),
            "ON  [Warm White: 50% raw state: 129,65,35,97,65,16,0,0,0,128,4,0,240,138,]",
        )

        # Update state now assumes its externally set to 100
        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(mock_read.call_count, 3)
        assert light.raw_state.warm_white == 100
        self.assertEqual(light.getWarmWhite255(), 100)
        self.assertEqual(light.brightness, 100)
        self.assertEqual(
            light.__str__(),
            "ON  [Warm White: 39% raw state: 129,65,35,97,65,16,0,0,0,100,4,0,240,239,]",
        )

        light._set_power_state(light._protocol.off_byte)
        self.assertEqual(
            light.__str__(),
            "OFF  [Warm White: 39% raw state: 129,65,36,97,65,16,0,0,0,100,4,0,240,239,]",
        )
        light._set_power_state(light._protocol.on_byte)
        self.assertEqual(
            light.__str__(),
            "ON  [Warm White: 39% raw state: 129,65,35,97,65,16,0,0,0,100,4,0,240,239,]",
        )
        light._replace_raw_state(
            {STATE_RED: 255, STATE_GREEN: 0, STATE_BLUE: 0, STATE_WARM_WHITE: 0}
        )
        self.assertEqual(
            light.__str__(),
            "ON  [Warm White: 100% raw state: 129,65,35,97,65,16,0,0,0,255,4,0,240,239,]",
        )
        # Verify we do not remap states that have not changed
        light._replace_raw_state({STATE_BLUE: 0})
        self.assertEqual(
            light.__str__(),
            "ON  [Warm White: 100% raw state: 129,65,35,97,65,16,0,0,0,255,4,0,240,239,]",
        )
        # Verify we do not remap states that have not changed
        light._replace_raw_state({STATE_GREEN: 255, STATE_BLUE: 255})
        self.assertEqual(
            light.__str__(),
            "ON  [Warm White: 100% raw state: 129,65,35,97,65,16,0,255,255,255,4,0,240,239,]",
        )
        self.assertEqual(light.dimmable_effects, False)

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_addressable_strip_effects_a2(self, mock_connect, mock_read, mock_send):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81\xA2")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"#a\x41\x10\xff\x00\x00\x00\x04\x00\xf0\xeb")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(
                    b"\x81\xA2#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd4"
                )
            raise ValueError("Too many calls")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(light.model_num, 0xA2)
        self.assertEqual(light.microphone, True)
        self.assertEqual(light.model, "RGB Symphony v2 (0xA2)")
        assert len(light.effect_list) == 104
        assert light.color_modes == {COLOR_MODE_RGB}

        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (255, 0, 0) Brightness: 100% raw state: 129,162,35,97,65,16,255,0,0,0,4,0,240,235,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_ADDRESSABLE_A2)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)
        self.assertEqual(light.dimmable_effects, True)

        light.setRgbw(0, 255, 0)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b"A\x01\x00\xff\x00\x00\x00\x00`\xff\x00\x00\xa0")),
        )

        light.set_effect("RBM 1", 50)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b"B\x012d\xd9")),
        )
        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(
            light.__str__(),
            "ON  [Pattern: RBM 1 (Speed 16%) raw state: 129,162,35,37,1,16,100,0,0,0,4,0,240,212,]",
        )
        assert light.effect == "RBM 1"
        assert light.brightness == 255
        assert light.getSpeed() == 16

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_addressable_strip_effects_a3(self, mock_connect, mock_read, mock_send):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81\xA3")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"#a\x41\x10\xff\x00\x00\x00\x04\x00\xf0\xec")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(
                    b"\x81\xA3#\x25\x01\x10\x64\x00\x00\x00\x04\x00\xf0\xd5"
                )
            raise ValueError("Too many calls")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(light.model_num, 0xA3)
        self.assertEqual(light.microphone, True)
        self.assertEqual(light.model, "RGB Symphony v3 (0xA3)")
        assert len(light.effect_list) == 104
        assert light.color_modes == {COLOR_MODE_RGB}

        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (255, 0, 0) Brightness: 100% raw state: 129,163,35,97,65,16,255,0,0,0,4,0,240,236,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_ADDRESSABLE_A3)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)
        self.assertEqual(light.dimmable_effects, True)

        light.setRgbw(0, 255, 0)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(
                bytearray(
                    b"\xb0\xb1\xb2\xb3\x00\x01\x01\x01\x00\rA\x01\x00\xff\x00\x00\x00\x00\x06\x01\x00\x00Hf"
                )
            ),
        )

        light.set_effect("RBM 1", 50)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(
            mock_send.call_args,
            mock.call(
                bytearray(b"\xb0\xb1\xb2\xb3\x00\x01\x01\x02\x00\x05B\x012d\x00\xa8")
            ),
        )
        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(
            light.__str__(),
            "ON  [Pattern: RBM 1 (Speed 16%) raw state: 129,163,35,37,1,16,100,0,0,0,4,0,240,213,]",
        )
        assert light.effect == "RBM 1"
        assert light.brightness == 255
        assert light.getSpeed() == 16

    @patch("flux_led.WifiLedBulb._send_msg")
    @patch("flux_led.WifiLedBulb._read_msg")
    @patch("flux_led.WifiLedBulb.connect")
    def test_original_addressable_strip_effects(
        self, mock_connect, mock_read, mock_send
    ):
        calls = 0

        def read_data(expected):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.assertEqual(expected, 2)
                return bytearray(b"\x81\xA1")
            if calls == 2:
                self.assertEqual(expected, 12)
                return bytearray(b"#a\x41\x10\xff\x00\x00\x00\x04\x00\xf0\xea")
            if calls == 3:
                self.assertEqual(expected, 14)
                return bytearray(
                    b"\x81\xA1#\x00\xa1\x01\x64\x00\x00\x00\x04\x00\xf0\x3f"
                )
            raise ValueError("Too many calls")

        mock_read.side_effect = read_data
        light = flux_led.WifiLedBulb("192.168.1.164")
        self.assertEqual(light.dimmable_effects, False)
        self.assertEqual(light.model_num, 0xA1)
        self.assertEqual(light.model, "RGB Symphony v1 (0xA1)")
        assert len(light.effect_list) == 301
        assert light.color_modes == {COLOR_MODE_RGB}

        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(LEDENET_STATE_QUERY)))

        self.assertEqual(
            light.__str__(),
            "ON  [Color: (255, 0, 0) Brightness: 100% raw state: 129,161,35,97,65,16,255,0,0,0,4,0,240,234,]",
        )
        self.assertEqual(light.protocol, PROTOCOL_LEDENET_ADDRESSABLE_A1)
        self.assertEqual(light.is_on, True)
        self.assertEqual(light.mode, "color")
        self.assertEqual(light.warm_white, 0)
        self.assertEqual(light.brightness, 255)
        self.assertEqual(light.rgbwcapable, False)
        self.assertEqual(light.device_type, flux_led.DeviceType.Bulb)

        light.setRgbw(0, 255, 0)
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args,
            mock.call(bytearray(b"1\x00\xff\x00\x00\x00\xf0\x0f/")),
        )

        light.set_effect(
            "Overlay circularly, 7 colors with black background from start to end", 50
        )
        self.assertEqual(mock_read.call_count, 2)
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(mock_send.call_args, mock.call(bytearray(b"a\x00\xa12\x0fC")))
        assert light.brightness == 255

        light._transition_complete_time = 0
        light.update_state()
        self.assertEqual(
            light.__str__(),
            "ON  [Pattern: Overlay circularly, 7 colors with black background from start to end (Speed 1%) raw state: 129,161,35,0,161,1,100,0,0,0,4,0,240,63,]",
        )
        assert (
            light.effect
            == "Overlay circularly, 7 colors with black background from start to end"
        )
        assert light.getSpeed() == 1
        light.set_effect("random", 50)
        self.assertEqual(mock_send.call_count, 5)
