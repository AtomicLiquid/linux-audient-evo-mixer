import logging
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QWidget, QButtonGroup,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from ..alsa_mixer import AlsaMixer, MIC_VOL_MAX, EVO8_VOL_MAX, mic_db_str, evo8_db_str

log = logging.getLogger(__name__)

_DEBOUNCE_MS = 80
_REFRESH_MS  = 3000
_POLL_MS     = 100   # hardware knob / physical control polling interval
_MIC_LABELS  = ["MIC 1", "MIC 2", "MIC 3", "MIC 4"]


class _ChannelStrip(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, label: str, max_val: int, db_fn, parent=None):
        super().__init__(parent)
        self._db_fn = db_fn
        self.setFixedWidth(60)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(4)

        lbl = QLabel(label)
        lbl.setObjectName("stripLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(lbl)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setMinimum(0)
        self.slider.setMaximum(max_val)
        lay.addWidget(self.slider, stretch=1, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._db_lbl = QLabel("—")
        self._db_lbl.setObjectName("dbLabel")
        self._db_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self._db_lbl)

        self.slider.valueChanged.connect(self._on_move)

    def _on_move(self, raw: int):
        self._db_lbl.setText(self._db_fn(raw))
        self.valueChanged.emit(raw)

    def set_raw(self, raw: int):
        self.slider.blockSignals(True)
        self.slider.setValue(raw)
        self.slider.blockSignals(False)
        self._db_lbl.setText(self._db_fn(raw))


def _vdiv() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setObjectName("divider")
    return f


def _hdiv() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setObjectName("divider")
    return f


class AlsaPanel(QFrame):
    def __init__(self, mixer: AlsaMixer, parent=None):
        super().__init__(parent)
        self.setObjectName("alsaPanel")
        self._mixer = mixer
        self._mic_vals: list[int] = [0] * 4
        self._evo8_vals: list[int] = [0] * 6
        self._pending_mic_idxs: set[int] = set()
        self._pending_evo8_idxs: set[int] = set()
        self._mic_strips: list[_ChannelStrip] = []
        self._out_strips: list[_ChannelStrip] = []  # index i → EVO8 vol channel i

        self._write_timer = QTimer(self)
        self._write_timer.setSingleShot(True)
        self._write_timer.setInterval(_DEBOUNCE_MS)
        self._write_timer.timeout.connect(self._flush)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(_REFRESH_MS)
        self._refresh_timer.timeout.connect(self._refresh_clock)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POLL_MS)
        self._poll_timer.timeout.connect(self._poll_device)

        self._build()
        self._load_initial()
        self._refresh_timer.start()
        self._poll_timer.start()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(_hdiv())

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        content.addWidget(self._build_mic_strips())
        content.addWidget(_vdiv())
        content.addWidget(self._build_output_panel())
        root.addLayout(content, stretch=1)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("mixerHeader")
        header.setFixedHeight(36)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)

        self._clock_led = QLabel("●")
        self._clock_led.setObjectName("clockOff")
        lay.addWidget(self._clock_led)

        title = QLabel("EVO")
        title.setObjectName("headerTitle")
        lay.addWidget(title)
        lay.addStretch()

        self._ext_btn = QPushButton("EXT UNIT")
        self._ext_btn.setObjectName("extUnitBtn")
        self._ext_btn.setCheckable(True)
        self._ext_btn.setFixedHeight(22)
        self._ext_btn.clicked.connect(self._on_ext)
        lay.addWidget(self._ext_btn)

        return header

    def _build_mic_strips(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        for i, name in enumerate(_MIC_LABELS):
            strip = _ChannelStrip(name, MIC_VOL_MAX, mic_db_str)
            strip.valueChanged.connect(lambda v, idx=i: self._on_mic(idx, v))
            self._mic_strips.append(strip)
            lay.addWidget(strip)

        return w

    def _build_output_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("outputPanel")
        panel.setFixedWidth(180)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._out_btn_grp = QButtonGroup(self)
        self._out_btn_grp.setExclusive(True)

        for sec_i, (label, start_idx) in enumerate([
            ("OUTPUTS 1+2", 0),
            ("OUTPUTS 3+4", 2),
        ]):
            if sec_i > 0:
                lay.addWidget(_hdiv())

            sec = QWidget()
            sec_lay = QVBoxLayout(sec)
            sec_lay.setContentsMargins(10, 8, 10, 8)
            sec_lay.setSpacing(6)

            btn = QPushButton(label)
            btn.setObjectName("outputTabBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(26)
            self._out_btn_grp.addButton(btn, sec_i)
            sec_lay.addWidget(btn)

            faders = QHBoxLayout()
            faders.setSpacing(4)
            faders.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            for out_i in range(start_idx, start_idx + 2):
                strip = _ChannelStrip(f"OUT {out_i + 1}", EVO8_VOL_MAX, evo8_db_str)
                strip.valueChanged.connect(lambda v, idx=out_i: self._on_evo8(idx, v))
                self._out_strips.append(strip)
                faders.addWidget(strip)

            sec_lay.addLayout(faders)
            lay.addWidget(sec)

        lay.addStretch()
        self._out_btn_grp.button(0).setChecked(True)
        return panel

    # ── Initial load ─────────────────────────────────────────────────────────

    def _load_initial(self):
        self._mic_vals = self._mixer.get_mic_volumes()
        for i, strip in enumerate(self._mic_strips):
            if i < len(self._mic_vals):
                strip.set_raw(self._mic_vals[i])

        self._evo8_vals = self._mixer.get_evo8_volumes()
        for i, strip in enumerate(self._out_strips):
            if i < len(self._evo8_vals):
                strip.set_raw(self._evo8_vals[i])

        self._ext_btn.blockSignals(True)
        self._ext_btn.setChecked(self._mixer.get_ext_unit())
        self._ext_btn.blockSignals(False)
        self._update_clock(self._mixer.get_clock_valid())

    # ── Clock refresh ─────────────────────────────────────────────────────────

    def _refresh_clock(self):
        self._update_clock(self._mixer.get_clock_valid())

    def _update_clock(self, valid: bool):
        obj = "clockOn" if valid else "clockOff"
        if self._clock_led.objectName() != obj:
            self._clock_led.setObjectName(obj)
            self._clock_led.style().unpolish(self._clock_led)
            self._clock_led.style().polish(self._clock_led)

    # ── Hardware poll ─────────────────────────────────────────────────────────

    def _poll_device(self):
        mic_vals = self._mixer.get_mic_volumes()
        for i, val in enumerate(mic_vals):
            if i < len(self._mic_strips) and i not in self._pending_mic_idxs:
                if val != self._mic_vals[i]:
                    self._mic_vals[i] = val
                    self._mic_strips[i].set_raw(val)

        evo8_vals = self._mixer.get_evo8_volumes()
        for i, val in enumerate(evo8_vals):
            if i < len(self._out_strips) and i not in self._pending_evo8_idxs:
                if val != self._evo8_vals[i]:
                    self._evo8_vals[i] = val
                    self._out_strips[i].set_raw(val)

    # ── Slot handlers ─────────────────────────────────────────────────────────

    def _on_ext(self, checked: bool):
        self._mixer.set_ext_unit(checked)

    def _on_mic(self, idx: int, raw: int):
        self._mic_vals[idx] = raw
        self._pending_mic_idxs.add(idx)
        self._write_timer.start()

    def _on_evo8(self, idx: int, raw: int):
        self._evo8_vals[idx] = raw
        self._pending_evo8_idxs.add(idx)
        self._write_timer.start()

    def _flush(self):
        if self._pending_mic_idxs:
            current = self._mixer.get_mic_volumes()
            for idx in self._pending_mic_idxs:
                if idx < len(current):
                    current[idx] = self._mic_vals[idx]
            self._mixer.set_mic_volumes(current)
            self._pending_mic_idxs.clear()

        if self._pending_evo8_idxs:
            current = self._mixer.get_evo8_volumes()
            for idx in self._pending_evo8_idxs:
                if idx < len(current):
                    current[idx] = self._evo8_vals[idx]
            self._mixer.set_evo8_volumes(current)
            self._pending_evo8_idxs.clear()
