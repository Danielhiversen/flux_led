EFFECT_RANDOM = "random"
EFFECT_COLORLOOP = "colorloop"
EFFECT_RED_FADE = "red_fade"
EFFECT_GREEN_FADE = "green_fade"
EFFECT_BLUE_FADE = "blue_fade"
EFFECT_YELLOW_FADE = "yellow_fade"
EFFECT_CYAN_FADE = "cyan_fade"
EFFECT_PURPLE_FADE = "purple_fade"
EFFECT_WHITE_FADE = "white_fade"
EFFECT_RED_GREEN_CROSS_FADE = "rg_cross_fade"
EFFECT_RED_BLUE_CROSS_FADE = "rb_cross_fade"
EFFECT_GREEN_BLUE_CROSS_FADE = "gb_cross_fade"
EFFECT_COLORSTROBE = "colorstrobe"
EFFECT_RED_STROBE = "red_strobe"
EFFECT_GREEN_STROBE = "green_strobe"
EFFECT_BLUE_STROBE = "blue_strobe"
EFFECT_YELLOW_STROBE = "yellow_strobe"
EFFECT_CYAN_STROBE = "cyan_strobe"
EFFECT_PURPLE_STROBE = "purple_strobe"
EFFECT_WHITE_STROBE = "white_strobe"
EFFECT_COLORJUMP = "colorjump"
EFFECT_CUSTOM = "custom"

EFFECT_MAP = {
    EFFECT_COLORLOOP: 0x25,
    EFFECT_RED_FADE: 0x26,
    EFFECT_GREEN_FADE: 0x27,
    EFFECT_BLUE_FADE: 0x28,
    EFFECT_YELLOW_FADE: 0x29,
    EFFECT_CYAN_FADE: 0x2A,
    EFFECT_PURPLE_FADE: 0x2B,
    EFFECT_WHITE_FADE: 0x2C,
    EFFECT_RED_GREEN_CROSS_FADE: 0x2D,
    EFFECT_RED_BLUE_CROSS_FADE: 0x2E,
    EFFECT_GREEN_BLUE_CROSS_FADE: 0x2F,
    EFFECT_COLORSTROBE: 0x30,
    EFFECT_RED_STROBE: 0x31,
    EFFECT_GREEN_STROBE: 0x32,
    EFFECT_BLUE_STROBE: 0x33,
    EFFECT_YELLOW_STROBE: 0x34,
    EFFECT_CYAN_STROBE: 0x35,
    EFFECT_PURPLE_STROBE: 0x36,
    EFFECT_WHITE_STROBE: 0x37,
    EFFECT_COLORJUMP: 0x38,
}

EFFECT_ID_NAME = {v: k for k, v in EFFECT_MAP.items()}
EFFECT_CUSTOM_CODE = 0x60

EFFECT_LIST = sorted(EFFECT_MAP)

ADDRESSABLE_EFFECT_ID_NAME = {
    1: "Circulate all modes",
    2: "7 colors change gradually",
    3: "7 colors run in olivary",
    4: "7 colors change quickly",
    5: "7 colors strobe-flash",
    6: "7 colors running, 1 point from start to end and return back",
    7: "7 colors running, multi points from start to end and return back",
    8: "7 colors overlay, multi points from start to end and return back",
    9: "7 colors overlay, multi points from the middle to the both ends and return back",
    10: "7 colors flow gradually, from start to end and return back",
    11: "Fading out run, 7 colors from start to end and return back",
    12: "Runs in olivary, 7 colors from start to end and return back",
    13: "Fading out run, 7 colors start with white color from start to end and return back",
    14: "Run circularly, 7 colors with black background, 1point from start to end",
    15: "Run circularly, 7 colors with red background, 1point from start to end",
    16: "Run circularly, 7 colors with green background, 1point from start to end",
    17: "Run circularly, 7 colors with blue background, 1point from start to end",
    18: "Run circularly, 7 colors with yellow background, 1point from start to end",
    19: "Run circularly, 7 colors with purple background, 1point from start to end",
    20: "Run circularly, 7 colors with cyan background, 1point from start to end",
    21: "Run circularly, 7 colors with white background, 1point from start to end",
    22: "Run circularly, 7 colors with black background, 1point from end to start",
    23: "Run circularly, 7 colors with red background, 1point from end to start",
    24: "Run circularly, 7 colors with green background, 1point from end to start",
    25: "Run circularly, 7 colors with blue background, 1point from end to start",
    26: "Run circularly, 7 colors with yellow background, 1point from end to start",
    27: "Run circularly, 7 colors with purple background, 1point from end to start",
    28: "Run circularly, 7 colors with cyan background, 1point from end to start",
    29: "Run circularly, 7 colors with white background, 1point from end to start",
    30: "Run circularly, 7 colors with black background, 1point from start to end and return back",
    31: "Run circularly, 7 colors with red background, 1point from start to end and return back",
    32: "Run circularly, 7 colors with green background, 1point from start to end and return back",
    33: "Run circularly, 7 colors with blue background, 1point from start to end and return back",
    34: "Run circularly, 7 colors with yellow background, 1point from start to end and return back",
    35: "Run circularly, 7 colors with purple background, 1point from start to end and return back",
    36: "Run circularly, 7 colors with cyan background, 1point from start to end and return back",
    37: "Run circularly, 7 colors with white background, 1point from start to end and return back",
    38: "Run circularly, 7 colors with black background, 1point from middle to both ends",
    39: "Run circularly, 7 colors with red background, 1point from middle to both ends",
    40: "Run circularly, 7 colors with green background, 1point from middle to both ends",
    41: "Run circularly, 7 colors with blue background, 1point from middle to both ends",
    42: "Run circularly, 7 colors with yellow background, 1point from middle to both ends",
    43: "Run circularly, 7 colors with purple background, 1point from middle to both ends",
    44: "Run circularly, 7 colors with cyan background, 1point from middle to both ends",
    45: "Run circularly, 7 colors with white background, 1point from middle to both ends",
    46: "Run circularly, 7 colors with black background, 1point from both ends to middle",
    47: "Run circularly, 7 colors with red background, 1point from both ends to middle",
    48: "Run circularly, 7 colors with green background, 1point from both ends to middle",
    49: "Run circularly, 7 colors with blue background, 1point from both ends to middle",
    50: "Run circularly, 7 colors with yellow background, 1point from both ends to middle",
    51: "Run circularly, 7 colors with purple background, 1point from both ends to middle",
    52: "Run circularly, 7 colors with cyan background, 1point from both ends to middle",
    53: "Run circularly, 7 colors with white background, 1point from both ends to middle",
    54: "Run circularly, 7 colors with black background, 1point from middle to both ends and return back",
    55: "Run circularly, 7 colors with red background, 1point from middle to both ends and return back",
    56: "Run circularly, 7 colors with green background, 1point from middle to both ends and return back",
    57: "Run circularly, 7 colors with blue background, 1point from middle to both ends and return back",
    58: "Run circularly, 7 colors with yellow background, 1point from middle to both ends and return back",
    59: "Run circularly, 7 colors with purple background, 1point from middle to both ends and return back",
    60: "Run circularly, 7 colors with cyan background, 1point from middle to both ends and return back",
    61: "Run circularly, 7 colors with white background, 1point from middle to both ends and return back",
    62: "Overlay circularly, 7 colors with black background from start to end",
    63: "Overlay circularly, 7 colors with red background from start to end",
    64: "Overlay circularly, 7 colors with green background from start to end",
    65: "Overlay circularly, 7 colors with blue background from start to end",
    66: "Overlay circularly, 7 colors with yellow background from start to end",
    67: "Overlay circularly, 7 colors with purple background from start to end",
    68: "Overlay circularly, 7 colors with cyan background from start to end",
    69: "Overlay circularly, 7 colors with white background from start to end",
    70: "Overlay circularly, 7 colors with black background from end to start",
    71: "Overlay circularly, 7 colors with red background from end to start",
    72: "Overlay circularly, 7 colors with green background from end to start",
    73: "Overlay circularly, 7 colors with blue background from end to start",
    74: "Overlay circularly, 7 colors with yellow background from end to start",
    75: "Overlay circularly, 7 colors with purple background from end to start",
    76: "Overlay circularly, 7 colors with cyan background from end to start",
    77: "Overlay circularly, 7 colors with white background from end to start",
    78: "Overlay circularly, 7 colors with black background from start to end and return back",
    79: "Overlay circularly, 7 colors with red background from start to end and return back",
    80: "Overlay circularly, 7 colors with green background from start to end and return back",
    81: "Overlay circularly, 7 colors with blue background from start to end and return back",
    82: "Overlay circularly, 7 colors with yellow background from start to end and return back",
    83: "Overlay circularly, 7 colors with purple background from start to end and return back",
    84: "Overlay circularly, 7 colors with cyan background from start to end and return back",
    85: "Overlay circularly, 7 colors with white background from start to end and return back",
    86: "Overlay circularly, 7 colors with black background from middle to both ends",
    87: "Overlay circularly, 7 colors with red background from middle to both ends",
    88: "Overlay circularly, 7 colors with green background from middle to both ends",
    89: "Overlay circularly, 7 colors with blue background from middle to both ends",
    90: "Overlay circularly, 7 colors with yellow background from middle to both ends",
    91: "Overlay circularly, 7 colors with purple background from middle to both ends",
    92: "Overlay circularly, 7 colors with cyan background from middle to both ends",
    93: "Overlay circularly, 7 colors with white background from middle to both ends",
    94: "Overlay circularly, 7 colors with black background from both ends to middle",
    95: "Overlay circularly, 7 colors with red background from both ends to middle",
    96: "Overlay circularly, 7 colors with green background from both ends to middle",
    97: "Overlay circularly, 7 colors with blue background from both ends to middle",
    98: "Overlay circularly, 7 colors with yellow background from both ends to middle",
    99: "Overlay circularly, 7 colors with purple background from both ends to middle",
    100: "Overlay circularly, 7 colors with cyan background from both ends to middle",
    101: "Overlay circularly, 7 colors with white background from both ends to middle",
    102: "Overlay circularly, 7 colors with black background from middle to both sides and return back",
    103: "Overlay circularly, 7 colors with red background from middle to both sides and return back",
    104: "Overlay circularly, 7 colors with green background from middle to both sides and return back",
    105: "Overlay circularly, 7 colors with blue background from middle to both sides and return back",
    106: "Overlay circularly, 7 colors with yellow background from middle to both sides and return back",
    107: "Overlay circularly, 7 colors with purple background from middle to both sides and return back",
    108: "Overlay circularly, 7 colors with cyan background from middle to both sides and return back",
    109: "Overlay circularly, 7 colors with white background from middle to both sides and return back",
    110: "Fading out run circularly, 1point with black background from start to end",
    111: "Fading out run circularly, 1point with red background from start to end",
    112: "Fading out run circularly, 1point with green background from start to end",
    113: "Fading out run circularly, 1point with blue background from start to end",
    114: "Fading out run circularly, 1point with yellow background from start to end",
    115: "Fading out run circularly, 1point with purple background from start to end",
    116: "Fading out run circularly, 1point with cyan background from start to end",
    117: "Fading out run circularly, 1point with white background from start to end",
    118: "Fading out run circularly, 1point with black background from end to start",
    119: "Fading out run circularly, 1point with red background from end to start",
    120: "Fading out run circularly, 1point with green background from end to start",
    121: "Fading out run circularly, 1point with blue background from end to start",
    122: "Fading out run circularly, 1point with yellow background from end to start",
    123: "Fading out run circularly, 1point with purple background from end to start",
    124: "Fading out run circularly, 1point with cyan background from end to start",
    125: "Fading out run circularly, 1point with white background from end to start",
    126: "Fading out run circularly, 1point with black background from start to end and return back",
    127: "Fading out run circularly, 1point with red background from start to end and return back",
    128: "Fading out run circularly, 1point with green background from start to end and return back",
    129: "Fading out run circularly, 1point with blue background from start to end and return back",
    130: "Fading out run circularly, 1point with yellow background from start to end and return back",
    131: "Fading out run circularly, 1point with purple background from start to end and return back",
    132: "Fading out run circularly, 1point with cyan background from start to end and return back",
    133: "Fading out run circularly, 1point with white background from start to end and return back",
    134: "Flows in olivary circularly, 7 colors with black background from start to end",
    135: "Flows in olivary circularly, 7 colors with red background from start to end",
    136: "Flows in olivary circularly, 7 colors with green background from start to end",
    137: "Flows in olivary circularly, 7 colors with blue background from start to end",
    138: "Flows in olivary circularly, 7 colors with yellow background from start to end",
    139: "Flows in olivary circularly, 7 colors with purple background from start to end",
    140: "Flows in olivary circularly, 7 colors with cyan background from start to end",
    141: "Flows in olivary circularly, 7 colors with white background from start to end",
    142: "Flows in olivary circularly, 7 colors with black background from end to start",
    143: "Flows in olivary circularly, 7 colors with red background from end to start",
    144: "Flows in olivary circularly, 7 colors with green background from end to start",
    145: "Flows in olivary circularly, 7 colors with blue background from end to start",
    146: "Flows in olivary circularly, 7 colors with yellow background from end to start",
    147: "Flows in olivary circularly, 7 colors with purple background from end to start",
    148: "Flows in olivary circularly, 7 colors with cyan background from end to start",
    149: "Flows in olivary circularly, 7 colors with white background from end to start",
    150: "Flows in olivary circularly, 7 colors with black background from start to end and return back",
    151: "Flows in olivary circularly, 7 colors with red background from start to end and return back",
    152: "Flows in olivary circularly, 7 colors with green background from start to end and return back",
    153: "Flows in olivary circularly, 7 colors with blue background from start to end and return back",
    154: "Flows in olivary circularly, 7 colors with yellow background from start to end and return back",
    155: "Flows in olivary circularly, 7 colors with purple background from start to end and return back",
    156: "Flows in olivary circularly, 7 colors with cyan background from start to end and return back",
    157: "Flows in olivary circularly, 7 colors with white background from start to end and return back",
    158: "7 colors run circularly, each color in every 1 point with black background from start to end",
    159: "7 colors run circularly, each color in every 1 point with red background from start to end",
    160: "7 colors run circularly, each color in every 1 point with green background from start to end",
    161: "7 colors run circularly, each color in every 1 point with blue background from start to end",
    162: "7 colors run circularly, each color in every 1 point with yellow background from start to end",
    163: "7 colors run circularly, each color in every 1 point with purple background from start to end",
    164: "7 colors run circularly, each color in every 1 point with cyan background from start to end",
    165: "7 colors run circularly, each color in every 1 point with white background from start to end",
    166: "7 colors run circularly, each color in every 1 point with black background from end to start",
    167: "7 colors run circularly, each color in every 1 point with red background from end to start",
    168: "7 colors run circularly, each color in every 1 point with green background from end to start",
    169: "7 colors run circularly, each color in every 1 point with blue background from end to start",
    170: "7 colors run circularly, each color in every 1 point with yellow background from end to start",
    171: "7 colors run circularly, each color in every 1 point with purple background from end to start",
    172: "7 colors run circularly, each color in every 1 point with cyan background from end to start",
    173: "7 colors run circularly, each color in every 1 point with white background from end to start",
    174: "7 colors run circularly, each color in every 1 point with black background from start to end and return back",
    175: "7 colors run circularly, each color in every 1 point with red background from start to end and return back",
    176: "7 colors run circularly, each color in every 1 point with green background from start to end and return back",
    177: "7 colors run circularly, each color in every 1 point with blue background from start to end and return back",
    178: "7 colors run circularly, each color in every 1 point with yellow background from start to end and return back",
    179: "7 colors run circularly, each color in every 1 point with purple background from start to end and return back",
    180: "7 colors run circularly, each color in every 1 point with cyan background from start to end and return back",
    181: "7 colors run circularly, each color in every 1 point with white background from start to end and return back",
    182: "7 colors run circularly, each color in multi points with red background from start to end",
    183: "7 colors run circularly, each color in multi points with green background from start to end",
    184: "7 colors run circularly, each color in multi points with blue background from start to end",
    185: "7 colors run circularly, each color in multi points with yellow background from start to end",
    186: "7 colors run circularly, each color in multi points with purple background from start to end",
    187: "7 colors run circularly, each color in multi points with cyan background from start to end",
    188: "7 colors run circularly, each color in multi points with white background from start to end",
    189: "7 colors run circularly, each color in multi points with red background from end to start",
    190: "7 colors run circularly, each color in multi points with green background from end to start",
    191: "7 colors run circularly, each color in multi points with blue background from end to start",
    192: "7 colors run circularly, each color in multi points with yellow background from end to start",
    193: "7 colors run circularly, each color in multi points with purple background from end to start",
    194: "7 colors run circularly, each color in multi points with cyan background from end to start",
    195: "7 colors run circularly, each color in multi points with white background from end to start",
    196: "7 colors run circularly, each color in multi points with red background from start to end and return back",
    197: "7 colors run circularly, each color in multi points with green background from start to end and return back",
    198: "7 colors run circularly, each color in multi points with blue background from start to end and return back",
    199: "7 colors run circularly, each color in multi points with yellow background from start to end and return back",
    200: "7 colors run circularly, each color in multi points with purple background from start to end and return back",
    201: "7 colors run circularly, each color in multi points with cyan background from start to end and return back",
    202: "7 colors run circularly, each color in multi points with white background from start to end and return back",
    203: "Fading out run circularly, 7 colors each in red fading from start to end",
    204: "Fading out run circularly, 7 colors each in green fading from start to end",
    205: "Fading out run circularly, 7 colors each in blue fading from start to end",
    206: "Fading out run circularly, 7 colors each in yellow fading from start to end",
    207: "Fading out run circularly, 7 colors each in purple fading from start to end",
    208: "Fading out run circularly, 7 colors each in cyan fading from start to end",
    209: "Fading out run circularly, 7 colors each in white fading from start to end",
    210: "Fading out run circularly, 7 colors each in red fading from end to start",
    211: "Fading out run circularly, 7 colors each in green fading from end to start",
    212: "Fading out run circularly, 7 colors each in blue fading from end to start",
    213: "Fading out run circularly, 7 colors each in yellow fading from end to start",
    214: "Fading out run circularly, 7 colors each in purple fading from end to start",
    215: "Fading out run circularly, 7 colors each in cyan fading from end to start",
    216: "Fading out run circularly, 7 colors each in white fading from end to start",
    217: "Fading out run circularly, 7 colors each in red fading from start to end and return back",
    218: "Fading out run circularly, 7 colors each in green fading from start to end and return back",
    219: "Fading out run circularly, 7 colors each in blue fading from start to end and return back",
    220: "Fading out run circularly, 7 colors each in yellow fading from start to end and return back",
    221: "Fading out run circularly, 7 colors each in purple fading from start to end and return back",
    222: "Fading out run circularly, 7 colors each in cyan fading from start to end and return back",
    223: "Fading out run circularly, 7 colors each in white fading from start to end and return back",
    224: "7 colors each in red run circularly, multi points from start to end",
    225: "7 colors each in green run circularly, multi points from start to end",
    226: "7 colors each in blue run circularly, multi points from start to end",
    227: "7 colors each in yellow run circularly, multi points from start to end",
    228: "7 colors each in purple run circularly, multi points from start to end",
    229: "7 colors each in cyan run circularly, multi points from start to end",
    230: "7 colors each in white run circularly, multi points from start to end",
    231: "7 colors each in red run circularly, multi points from end to start",
    232: "7 colors each in green run circularly, multi points from end to start",
    233: "7 colors each in blue run circularly, multi points from end to start",
    234: "7 colors each in yellow run circularly, multi points from end to start",
    235: "7 colors each in purple run circularly, multi points from end to start",
    236: "7 colors each in cyan run circularly, multi points from end to start",
    237: "7 colors each in white run circularly, multi points from end to start",
    238: "7 colors each in red run circularly, multi points from start to end and return back",
    239: "7 colors each in green run circularly, multi points from start to end and return back",
    240: "and return back7 colors each in blue run circularly, multi points from start to end",
    241: "7 colors each in yellow run circularly, multi points from start to end and return back",
    242: "7 colors each in purple run circularly, multi points from start to end and return back",
    243: "7 colors each in cyan run circularly, multi points from start to end and return back",
    244: "7 colors each in white run circularly, multi points from start to end and return back",
    245: "Flows gradually and circularly, 6 colors with red background from start to end",
    246: "Flows gradually and circularly, 6 colors with green background from start to end",
    247: "Flows gradually and circularly, 6 colors with blue background from start to end",
    248: "Flows gradually and circularly, 6 colors with yellow background from start to end",
    249: "Flows gradually and circularly, 6 colors with purple background from start to end",
    250: "Flows gradually and circularly, 6 colors with cyan background from start to end",
    251: "Flows gradually and circularly, 6 colors with white background from start to end",
    252: "Flows gradually and circularly, 6 colors with red background from end to start",
    253: "Flows gradually and circularly, 6 colors with green background from end to start",
    254: "Flows gradually and circularly, 6 colors with blue background from end to start",
    255: "Flows gradually and circularly, 6 colors with yellow background from end to start",
    256: "Flows gradually and circularly, 6 colors with purple background from end to start",
    257: "Flows gradually and circularly, 6 colors with cyan background from end to start",
    258: "Flows gradually and circularly, 6 colors with white background from end to start",
    259: "Flows gradually and circularly, 6 colors with red background from start to end and return back",
    260: "Flows gradually and circularly, 6 colors with green background from start to end and return back",
    261: "Flows gradually and circularly, 6 colors with blue background from start to end and return back",
    262: "Flows gradually and circularly, 6 colors with yellow background from start to end and return back",
    263: "Flows gradually and circularly, 6 colors with purple background from start to end and return back",
    264: "Flows gradually and circularly, 6 colors with cyan background from start to end and return back",
    265: "Flows gradually and circularly, 6 colors with white background from start to end and return back",
    266: "7 colors run with black background from start to end",
    267: "7 colors run with red background from start to end",
    268: "7 colors run with green background from start to end",
    269: "7 colors run with blue background from start to end",
    270: "7 colors run with yellow background from start to end",
    271: "7 colors run with purple background from start to end",
    272: "7 colors run with cyan background from start to end",
    273: "7 colors run with white background from start to end",
    274: "7 colors run with black background from end to start",
    275: "7 colors run with red background from end to start",
    276: "7 colors run with green background from end to start",
    277: "7 colors run with blue background from end to start",
    278: "7 colors run with yellow background from end to start",
    279: "7 colors run with purple background from end to start",
    280: "7 colors run with cyan background from end to start",
    281: "7 colors run with white background from end to start",
    282: "7 colors run with black background from start to end and return back",
    283: "7 colors run with red background from start to end and return back",
    284: "7 colors run with green background from start to end and return back",
    285: "7 colors run with blue background from start to end and return back",
    286: "7 colors run with yellow background from start to end and return back",
    287: "7 colors run with purple background from start to end and return back",
    288: "7 colors run with cyan background from start to end and return back",
    289: "7 colors run with white background from start to end and return back",
    290: "7 colors run gradually + 7 colors run in olivary",
    291: "7 colors run gradually + 7 colors change quickly",
    292: "7 colors run gradually + 7 colors flash",
    293: "7 colors run in olivary + 7 colors change quickly",
    294: "7 colors run in olivary + 7 colors flash",
    295: "7 colors change quickly + 7 colors flash",
    296: "7 colors run gradually + 7 colors run in olivary + 7 colors change quickly",
    297: "7 colors run gradually + 7 colors run in olivary + 7 colors flash",
    298: "7 colors run gradually + 7 colors change quickly + 7 colors flash",
    299: "7 colors run in olivary + 7 colors change quickly + 7 colors flash",
    300: "7 colors run gradually + 7 colors run in olivary + 7 colors change quickly + 7 color flash",
}


class PresetPattern:

    _instance = None
    seven_color_cross_fade = 0x25
    red_gradual_change = 0x26
    green_gradual_change = 0x27
    blue_gradual_change = 0x28
    yellow_gradual_change = 0x29
    cyan_gradual_change = 0x2A
    purple_gradual_change = 0x2B
    white_gradual_change = 0x2C
    red_green_cross_fade = 0x2D
    red_blue_cross_fade = 0x2E
    green_blue_cross_fade = 0x2F
    seven_color_strobe_flash = 0x30
    red_strobe_flash = 0x31
    green_strobe_flash = 0x32
    blue_strobe_flash = 0x33
    yellow_strobe_flash = 0x34
    cyan_strobe_flash = 0x35
    purple_strobe_flash = 0x36
    white_strobe_flash = 0x37
    seven_color_jumping = 0x38

    def __init__(self):
        self._value_to_str = {
            v: k.replace("_", " ").title()
            for k, v in PresetPattern.__dict__.items()
            if type(v) is int
        }

    @classmethod
    def instance(cls):
        """Get preset pattern instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def valid(pattern):
        if pattern >= 0x25 and pattern <= 0x38 or pattern >= 0x61 and pattern <= 0x63:
            return True
        return False

    @staticmethod
    def valtostr(pattern):
        instance = PresetPattern.instance()
        return instance._value_to_str.get(pattern)

    @staticmethod
    def str_to_val(effect):
        if effect in EFFECT_MAP:
            return EFFECT_MAP[effect]
        if hasattr(PresetPattern, effect):
            return getattr(PresetPattern, effect)
        raise ValueError(f"{effect} is not a known effect name.")
