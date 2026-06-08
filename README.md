# linux-audient-evo-mixer

Native Linux mixer GUI and volume sync daemon for the **Audient EVO 8** USB audio interface. Replaces the official Windows/Mac mixer app using ALSA controls exposed by the `snd-usb-audio` kernel driver.

## Features

- Vertical channel faders for MIC 1–4 preamp volume
- Output panel with independent level control for OUTPUTS 1+2 and OUTPUTS 3+4
- Hardware knob turns update the GUI sliders in real time (100 ms poll)
- Clock lock indicator and EXT UNIT toggle
- `pipewire_sync.py` daemon: bidirectional sync between the hardware knob and PipeWire's default sink volume
- Systemd user service for the sync daemon (starts automatically at login)

## Requirements

- Linux with `snd-usb-audio` and PipeWire
- `amixer` (`alsa-utils`)
- `wpctl` and `pactl` (`pipewire-pulse` / `wireplumber`)
- Python ≥ 3.10
- PyQt6

```
pip install PyQt6
```

`pyusb` is listed in `requirements.txt` but is no longer used — the mixer communicates exclusively over ALSA.

## Usage

### GUI mixer

```bash
python main.py
```

### PipeWire sync daemon

Bidirectional sync: turning the hardware knob updates PipeWire, and changing the PipeWire sink volume updates the device.

```bash
# Run manually
python pipewire_sync.py

# Set a specific volume and exit
python pipewire_sync.py 75%
python pipewire_sync.py 0.75
```

### Systemd service (auto-start at login)

```bash
# Install and enable
cp ~/.config/systemd/user/pipewire-sync.service  # already done if you cloned this repo
systemctl --user daemon-reload
systemctl --user enable --now pipewire-sync.service

# Check logs
journalctl --user -u pipewire-sync.service -f
```

The service file is at `~/.config/systemd/user/pipewire-sync.service` — see [installation](#installation) below.

## Installation

```bash
git clone git@github.com:AtomicLiquid/linux-audient-evo-mixer.git
cd linux-audient-evo-mixer
pip install PyQt6

# Optional: install the PipeWire sync daemon as a systemd user service
cp pipewire-sync.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now pipewire-sync.service
```

## ALSA controls

| numid | Name | Channels | Range | Purpose |
|-------|------|----------|-------|---------|
| 3 | Mic Playback Volume | 4 | 0–116 (−8 to +50 dB) | Mic preamp gain |
| 4 | EVO8 Playback Volume | 6 | 0–254 (−127 to 0 dB) | Per-output playback level |
| 5 | Extension Unit Switch | 1 | on/off | EXT UNIT toggle |
| 6 | Audient Internal Clock Validity | 1 | on/off | Clock lock indicator (read-only) |

> **Note:** `amixer -D hw:EVO8` is required. The shorter `-c EVO8` form fails for `iface=CARD` controls (numid 5 and 6).

## Architecture

```
main.py                     entry point, logging setup
evo8/
  alsa_mixer.py             thin wrapper around amixer subprocesses
  gui/
    main_window.py          QMainWindow, 2-second device availability poll
    alsa_panel.py           main widget: channel strips + output panel,
                            100 ms hardware poll for knob changes
    styles.py               Qt stylesheet
pipewire_sync.py            bidirectional PipeWire ↔ ALSA daemon
```
