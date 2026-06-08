import logging
import re
import subprocess

log = logging.getLogger(__name__)

_DEVICE = "hw:EVO8"   # -D hw:EVO8 required; -c EVO8 fails for iface=CARD controls
_NUMID_MIC_VOL = 3    # Mic Playback Volume:        4 values, 0–116, −8 to +50 dB
_NUMID_EVO8_VOL = 4   # EVO8 Playback Volume:       6 values, 0–254, −127 to 0 dB
_NUMID_EXT_SW = 5     # Extension Unit Switch:       boolean rw
_NUMID_CLOCK = 6      # Audient Internal Clock Validity: boolean read-only

MIC_VOL_MIN = 0
MIC_VOL_MAX = 116
MIC_DB_MIN = -8.0
MIC_DB_MAX = 50.0

EVO8_VOL_MIN = 0
EVO8_VOL_MAX = 254
EVO8_DB_MIN = -127.0
EVO8_DB_MAX = 0.0


def _amixer(*args: str) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["amixer", "-D", _DEVICE, *args],
            capture_output=True, text=True, timeout=2,
        )
        if r.returncode != 0:
            log.warning("amixer %s returned %d: %s", args, r.returncode, r.stderr.strip())
        return r.returncode == 0, r.stdout
    except Exception as exc:
        log.error("amixer subprocess error: %s", exc)
        return False, ""


def _parse_values(output: str) -> list[str]:
    m = re.search(r':\s+values=([^\n]+)', output)
    return [v.strip() for v in m.group(1).split(',')] if m else []


class AlsaMixer:
    def get_mic_volumes(self) -> list[int]:
        ok, out = _amixer("cget", f"numid={_NUMID_MIC_VOL}")
        if not ok:
            return [0] * 4
        try:
            return [int(v) for v in _parse_values(out)][:4]
        except ValueError:
            return [0] * 4

    def set_mic_volumes(self, values: list[int]) -> bool:
        clamped = [max(MIC_VOL_MIN, min(MIC_VOL_MAX, v)) for v in values]
        ok, _ = _amixer("cset", f"numid={_NUMID_MIC_VOL}", ",".join(str(v) for v in clamped))
        return ok

    def get_evo8_volumes(self) -> list[int]:
        ok, out = _amixer("cget", f"numid={_NUMID_EVO8_VOL}")
        if not ok:
            return [0] * 6
        try:
            return [int(v) for v in _parse_values(out)][:6]
        except ValueError:
            return [0] * 6

    def set_evo8_volumes(self, values: list[int]) -> bool:
        clamped = [max(EVO8_VOL_MIN, min(EVO8_VOL_MAX, v)) for v in values]
        ok, _ = _amixer("cset", f"numid={_NUMID_EVO8_VOL}", ",".join(str(v) for v in clamped))
        return ok

    def get_ext_unit(self) -> bool:
        ok, out = _amixer("cget", f"numid={_NUMID_EXT_SW}")
        vals = _parse_values(out)
        return bool(vals and vals[0] == "on")

    def set_ext_unit(self, enabled: bool) -> bool:
        ok, _ = _amixer("cset", f"numid={_NUMID_EXT_SW}", "on" if enabled else "off")
        return ok

    def get_clock_valid(self) -> bool:
        ok, out = _amixer("cget", f"numid={_NUMID_CLOCK}")
        vals = _parse_values(out)
        return bool(vals and vals[0] == "on")

    def is_available(self) -> bool:
        ok, _ = _amixer("info")
        return ok


def mic_raw_to_db(raw: int) -> float:
    return MIC_DB_MIN + (raw / MIC_VOL_MAX) * (MIC_DB_MAX - MIC_DB_MIN)


def evo8_raw_to_db(raw: int) -> float:
    return EVO8_DB_MIN + (raw / EVO8_VOL_MAX) * (EVO8_DB_MAX - EVO8_DB_MIN)


def mic_db_str(raw: int) -> str:
    db = mic_raw_to_db(raw)
    return f"{db:+.0f} dB"


def evo8_db_str(raw: int) -> str:
    if raw == 0:
        return "−∞"
    db = evo8_raw_to_db(raw)
    return f"{db:.0f} dB"
