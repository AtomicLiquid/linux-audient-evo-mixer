#!/usr/bin/env python3
"""Sync PipeWire default sink volume ↔ EVO8 hardware output (numid=4, OUT 1+2).

Daemon mode  — bidirectional sync (knob → PipeWire and PipeWire → device):
  python pipewire_sync.py

Set volume   — update both PipeWire and the device immediately, then exit:
  python pipewire_sync.py 0.75      (75%, float)
  python pipewire_sync.py 75%       (75%, percent string)
"""

import re
import select
import subprocess
import sys

_SINK   = "@DEFAULT_AUDIO_SINK@"
_DEVICE = "hw:EVO8"
_NUMID  = 4
_MAX    = 254
_TOTAL  = 6
_OUTS   = (0, 1)   # channels controlled by OUT 1+2 / main hardware knob


# ── PipeWire helpers ──────────────────────────────────────────────────────────

def pw_get() -> float | None:
    r = subprocess.run(["wpctl", "get-volume", _SINK], capture_output=True, text=True)
    m = re.search(r"Volume:\s+([\d.]+)", r.stdout)
    return float(m.group(1)) if m else None


def pw_set(vol: float):
    vol = max(0.0, min(1.5, vol))
    subprocess.run(["wpctl", "set-volume", _SINK, f"{vol:.3f}"], check=True)


# ── ALSA helpers ──────────────────────────────────────────────────────────────

def alsa_get() -> list[int]:
    r = subprocess.run(
        ["amixer", "-D", _DEVICE, "cget", f"numid={_NUMID}"],
        capture_output=True, text=True,
    )
    for line in r.stdout.splitlines():
        if ": values=" in line:
            return [int(v.strip()) for v in line.split("=")[1].split(",")]
    return [0] * _TOTAL


def alsa_set(values: list[int]):
    vals = ",".join(str(max(0, min(_MAX, v))) for v in values)
    subprocess.run(
        ["amixer", "-D", _DEVICE, "cset", f"numid={_NUMID}", vals],
        capture_output=True,
    )


# ── Volume conversion ─────────────────────────────────────────────────────────

def to_raw(vol: float) -> int:
    return round(max(0.0, min(1.0, vol)) * _MAX)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_set(arg: str):
    if arg.endswith("%"):
        vol = float(arg[:-1]) / 100.0
    else:
        vol = float(arg)
    pw_set(vol)
    raw = to_raw(vol)
    channels = alsa_get()
    for i in _OUTS:
        channels[i] = raw
    alsa_set(channels)
    print(f"Set {vol:.1%}  →  EVO8 OUT1+2 = {raw}/{_MAX}")


def cmd_daemon():
    # Device has priority on startup: push current ALSA value into PipeWire.
    channels = alsa_get()
    last_raw = channels[_OUTS[0]]
    pw_set(last_raw / _MAX)
    print(f"Startup: EVO8 OUT1+2 = {last_raw}/{_MAX}  →  PipeWire {last_raw / _MAX:.1%}")
    print("Watching for changes in both directions  (Ctrl-C to stop)")

    proc = subprocess.Popen(
        ["pactl", "subscribe"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        while True:
            # Block up to 100 ms waiting for a PipeWire event.
            ready, _, _ = select.select([proc.stdout], [], [], 0.1)

            # Always read current ALSA state (detects hardware knob turns).
            channels = alsa_get()
            hw_raw = channels[_OUTS[0]]
            if hw_raw != last_raw:
                pw_set(hw_raw / _MAX)
                print(f"EVO8 knob {hw_raw}/{_MAX}  →  PipeWire {hw_raw / _MAX:.1%}")
                last_raw = hw_raw

            # Handle any pending PipeWire sink-change event.
            if ready:
                line = proc.stdout.readline()
                if "change" in line and "sink" in line:
                    vol = pw_get()
                    if vol is not None:
                        pw_raw = to_raw(vol)
                        if pw_raw != last_raw:
                            for i in _OUTS:
                                channels[i] = pw_raw
                            alsa_set(channels)
                            print(f"PipeWire {vol:.1%}  →  EVO8 OUT1+2 = {pw_raw}/{_MAX}")
                            last_raw = pw_raw
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        proc.terminate()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) == 2:
        cmd_set(sys.argv[1])
    elif len(sys.argv) == 1:
        cmd_daemon()
    else:
        print(__doc__)
        sys.exit(1)
