from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, pyqtSignal

from ..constants import fader_to_mix_usb, mix_usb_to_fader, knob_to_gain_usb
from .knob import Knob
from .fader import Fader

_LABEL_STYLE = "color: #aaaaaa; font-size: 10px; font-weight: bold;"
_SUBLABEL_STYLE = "color: #666666; font-size: 9px;"


class MicChannelStrip(QWidget):
    """Channel strip for a hardware mic/line input (channels 0–3)."""

    gainChanged = pyqtSignal(int, int)     # (channel_idx, usb_gain_value)
    phantomChanged = pyqtSignal(int, bool) # (channel_idx, enabled)
    mixChanged = pyqtSignal(int, int)      # (src_index, usb_mix_value)

    def __init__(self, channel: int, src_index: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.src_index = src_index
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 10, 4, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        lbl = QLabel(f"MIC {self.channel + 1}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(_LABEL_STYLE)
        layout.addWidget(lbl)

        self.gain_knob = Knob(0, 1000, 0)
        self.gain_knob.setDefault(0)
        self.gain_knob.setToolTip("Preamp gain")
        self.gain_knob.valueChanged.connect(self._on_gain)
        layout.addWidget(self.gain_knob, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.phantom_btn = QPushButton("48V")
        self.phantom_btn.setObjectName("phantomBtn")
        self.phantom_btn.setFixedSize(36, 18)
        self.phantom_btn.setCheckable(True)
        self.phantom_btn.setToolTip("Phantom power (+48 V)")
        self.phantom_btn.clicked.connect(self._on_phantom)
        layout.addWidget(self.phantom_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()

        self.fader = Fader(0, 1000, 750)
        self.fader.valueChanged.connect(self._on_fader)
        layout.addWidget(self.fader, alignment=Qt.AlignmentFlag.AlignHCenter)

        db_lbl = QLabel("0 dB")
        db_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        db_lbl.setStyleSheet(_SUBLABEL_STYLE)
        self._db_label = db_lbl
        layout.addWidget(db_lbl)

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_gain(self, knob_val: int):
        self.gainChanged.emit(self.channel, knob_to_gain_usb(knob_val))

    def _on_phantom(self, checked: bool):
        self.phantomChanged.emit(self.channel, checked)

    def _on_fader(self, fader_val: int):
        usb_val = fader_to_mix_usb(fader_val)
        self._update_db_label(usb_val)
        self.mixChanged.emit(self.src_index, usb_val)

    def _update_db_label(self, usb_val: int):
        if usb_val <= -32768:
            self._db_label.setText("−∞")
        else:
            db = usb_val / 256.0
            self._db_label.setText(f"{db:.1f} dB" if db < 0 else "0 dB")

    # ── State refresh (no USB emit) ──────────────────────────────────────────

    def set_fader_usb(self, usb_val: int):
        self.fader.setValue(mix_usb_to_fader(usb_val), emit=False)
        self._update_db_label(usb_val)


class StereoChannelStrip(QWidget):
    """Channel strip for a stereo DAW return or loopback source."""

    mixChanged = pyqtSignal(int, int, int)  # (src_l_index, src_r_index, usb_mix_value)

    def __init__(self, label: str, src_l: int, src_r: int, parent=None):
        super().__init__(parent)
        self.src_l = src_l
        self.src_r = src_r
        self._build(label)

    def _build(self, label: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 10, 4, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(_LABEL_STYLE)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        layout.addStretch()

        self.fader = Fader(0, 1000, 750)
        self.fader.valueChanged.connect(self._on_fader)
        layout.addWidget(self.fader, alignment=Qt.AlignmentFlag.AlignHCenter)

        db_lbl = QLabel("0 dB")
        db_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        db_lbl.setStyleSheet(_SUBLABEL_STYLE)
        self._db_label = db_lbl
        layout.addWidget(db_lbl)

    def _on_fader(self, fader_val: int):
        usb_val = fader_to_mix_usb(fader_val)
        self._update_db_label(usb_val)
        self.mixChanged.emit(self.src_l, self.src_r, usb_val)

    def _update_db_label(self, usb_val: int):
        if usb_val <= -32768:
            self._db_label.setText("−∞")
        else:
            db = usb_val / 256.0
            self._db_label.setText(f"{db:.1f} dB" if db < 0 else "0 dB")

    def set_fader_usb(self, usb_val: int):
        self.fader.setValue(mix_usb_to_fader(usb_val), emit=False)
        self._update_db_label(usb_val)
