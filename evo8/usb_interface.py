import logging
import struct

import usb.core

from .constants import (
    VENDOR_ID, PRODUCT_ID,
    WINDEX_HW_CTRL, WINDEX_MASTER_VOL, WINDEX_MIX_VOL,
    W48V_BASE, WGAIN_BASE, WOUT12_VOL, WOUT34_VOL,
    GAIN_MIN, GAIN_MAX, MASTER_MIN, MASTER_MAX, MIX_MUTE, MIX_UNITY,
    mix_wvalue,
    SRC_DAW1, SRC_DAW2, SRC_DAW3, SRC_DAW4, SRC_LB1, SRC_LB2,
)

log = logging.getLogger(__name__)

_WINDEX_NAMES = {
    WINDEX_HW_CTRL:    "HW_CTRL",
    WINDEX_MASTER_VOL: "MASTER_VOL",
    WINDEX_MIX_VOL:    "MIX_VOL",
}
_SRC_NAMES = ["MIC1", "MIC2", "MIC3", "MIC4",
              "DAW1", "DAW2", "DAW3", "DAW4",
              "LB1",  "LB2"]
_OUT_NAMES = ["OUT1", "OUT2", "OUT3", "OUT4"]


class EvoUSB:
    _BMREQ_WRITE = 0x21   # UAC2 class, host-to-device, interface
    _BREQ_SET_CUR = 0x01

    def __init__(self):
        self._dev = None

    # ── Connection ───────────────────────────────────────────────────────────

    def connect(self) -> bool:
        dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if dev is None:
            log.warning("EVO 8 not found (VID=%04x PID=%04x)", VENDOR_ID, PRODUCT_ID)
            return False
        self._dev = dev
        log.info("EVO 8 found: bus %d device %d", dev.bus, dev.address)
        return True

    def disconnect(self):
        self._dev = None
        log.info("EVO 8 released")

    @property
    def connected(self) -> bool:
        return self._dev is not None

    # ── Batched send ─────────────────────────────────────────────────────────

    def batch_send(self):
        """No-op context manager kept for call-site compatibility.

        ctrl_transfer targets EP0, which is always accessible without claiming
        or detaching any interface. Detaching snd-usb-audio from interface 0
        causes PipeWire to drop the device, so we no longer do it.
        """
        from contextlib import nullcontext
        return nullcontext()

    # ── Low-level transfer ───────────────────────────────────────────────────

    def _ctrl(self, wValue: int, wIndex: int, data: bytes) -> bool:
        if self._dev is None:
            log.debug("ctrl skipped — not connected")
            return False

        index_name = _WINDEX_NAMES.get(wIndex, f"0x{wIndex:04x}")
        log.debug(
            "ctrl  bmReqType=0x%02x bReq=0x%02x  wValue=0x%04x  wIndex=%s  data=%s",
            self._BMREQ_WRITE, self._BREQ_SET_CUR, wValue, index_name, data.hex(),
        )

        try:
            self._dev.ctrl_transfer(
                self._BMREQ_WRITE,
                self._BREQ_SET_CUR,
                wValue,
                wIndex,
                data,
            )
            log.debug("  → OK")
            return True

        except usb.core.USBError as e:
            log.error(
                "  → USBError errno=%s: %s  (wValue=0x%04x wIndex=%s data=%s)",
                e.errno, e, wValue, index_name, data.hex(),
            )
            if e.errno in (5, 19):
                self._dev = None
                log.warning("Device disconnected")
            return False

    # ── Hardware controls ────────────────────────────────────────────────────

    def set_48v(self, channel: int, enabled: bool) -> bool:
        log.info("48V  ch=%d  %s", channel, "ON" if enabled else "OFF")
        return self._ctrl(W48V_BASE + channel, WINDEX_HW_CTRL,
                          struct.pack('<I', 1 if enabled else 0))

    def set_mic_gain(self, channel: int, value: int) -> bool:
        value = max(GAIN_MIN, min(GAIN_MAX, value))
        log.info("GAIN ch=%d  value=0x%06x  (%.1f%%)", channel, value, value / 0xFFFFFF * 100)
        return self._ctrl(WGAIN_BASE + channel, WINDEX_HW_CTRL, struct.pack('<I', value))

    # ── Master output volume ─────────────────────────────────────────────────

    def set_master_volume(self, output_pair: int, value: int) -> bool:
        value = max(MASTER_MIN, min(MASTER_MAX, value))
        wv = WOUT12_VOL if output_pair == 0 else WOUT34_VOL
        log.info("MASTER  pair=%d (OUT%d+%d)  value=0x%06x  (%.1f%%)",
                 output_pair, output_pair * 2 + 1, output_pair * 2 + 2,
                 value, value / 0xFFFFFF * 100)
        return self._ctrl(wv, WINDEX_MASTER_VOL, struct.pack('<I', value))

    # ── Monitor mix volumes ──────────────────────────────────────────────────

    def set_mix_volume(self, src_index: int, out_index: int, value: int) -> bool:
        value = max(MIX_MUTE, min(MIX_UNITY, value))
        db = value / 256.0 if value > MIX_MUTE else float('-inf')
        src = _SRC_NAMES[src_index] if src_index < len(_SRC_NAMES) else str(src_index)
        out = _OUT_NAMES[out_index] if out_index < len(_OUT_NAMES) else str(out_index)
        log.info("MIX  %s → %s  value=%d (0x%04x)  %.2f dB",
                 src, out, value, value & 0xFFFF,
                 db if db != float('-inf') else -999)
        return self._ctrl(mix_wvalue(src_index, out_index), WINDEX_MIX_VOL,
                          struct.pack('<h', value))

    def silence_cross_routes(self, output_pair: int):
        """Mute stereo cross-routes so L sources don't bleed to R and vice versa."""
        log.info("Silencing cross-routes for output pair %d", output_pair)
        l_out = output_pair * 2
        r_out = output_pair * 2 + 1
        for src_l, src_r in ((SRC_DAW1, SRC_DAW2), (SRC_DAW3, SRC_DAW4), (SRC_LB1, SRC_LB2)):
            self.set_mix_volume(src_l, r_out, MIX_MUTE)
            self.set_mix_volume(src_r, l_out, MIX_MUTE)
