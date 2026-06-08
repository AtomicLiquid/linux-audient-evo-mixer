VENDOR_ID = 0x2708
PRODUCT_ID = 0x0007

# wIndex groups
WINDEX_HW_CTRL = 0x3A00    # phantom power + mic gain
WINDEX_MASTER_VOL = 0x3B00  # master output volume
WINDEX_MIX_VOL = 0x3C00    # per-channel monitor mix volumes

# wValue bases for hardware controls
W48V_BASE = 0x0000    # + channel (0–3) → phantom power
WGAIN_BASE = 0x0100   # + channel (0–3) → preamp gain

# wValue for master output volume
WOUT12_VOL = 0x0000
WOUT34_VOL = 0x0002

# Source indices (used in mix wValue calculation)
SRC_MIC1, SRC_MIC2, SRC_MIC3, SRC_MIC4 = 0, 1, 2, 3
SRC_DAW1, SRC_DAW2, SRC_DAW3, SRC_DAW4 = 4, 5, 6, 7
SRC_LB1, SRC_LB2 = 8, 9

# Output indices
OUT1, OUT2, OUT3, OUT4 = 0, 1, 2, 3

# Value ranges
GAIN_MIN = 0x000000
GAIN_MAX = 0xFFFFFF
MASTER_MIN = 0x000000
MASTER_MAX = 0xFFFFFF
# Mix volume is signed int16, Q7.8 dB encoding (1 LSB = 1/256 dB)
MIX_MUTE = -32768   # 0x8000 → −128 dB
MIX_UNITY = 0       # 0x0000 → 0 dB

_DB_FLOOR = -80.0   # practical fader minimum (dB)


def mix_wvalue(src_index: int, out_index: int) -> int:
    return 0x0100 + (src_index * 4) + out_index


# Fader value is 0–1000 (integer), mapping to dB_FLOOR..0 dB linearly
def fader_to_mix_usb(fader_val: int) -> int:
    """Convert fader position 0–1000 → USB int16 mix volume."""
    if fader_val <= 0:
        return MIX_MUTE
    db = _DB_FLOOR * (1.0 - fader_val / 1000.0)
    return max(MIX_MUTE, min(MIX_UNITY, int(db * 256)))


def mix_usb_to_fader(usb_val: int) -> int:
    """Convert USB int16 mix volume → fader position 0–1000."""
    if usb_val <= MIX_MUTE:
        return 0
    db = max(_DB_FLOOR, min(0.0, usb_val / 256.0))
    return max(0, min(1000, int((1.0 - db / _DB_FLOOR) * 1000)))


def knob_to_gain_usb(knob_val: int) -> int:
    return int(knob_val * GAIN_MAX / 1000)


def knob_to_master_usb(knob_val: int) -> int:
    return int(knob_val * MASTER_MAX / 1000)
