import math

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen


class Knob(QWidget):
    """Circular rotary knob.

    Drag vertically to change value. Double-click to reset to default.
    Arc sweeps 270° clockwise from 7 o'clock to 5 o'clock.
    """

    valueChanged = pyqtSignal(int)

    _START_DEG = 225   # 7 o'clock, degrees CCW from East (Qt convention)
    _SWEEP_DEG = 270   # total sweep, clockwise

    def __init__(self, minimum: int = 0, maximum: int = 1000, value: int = 500,
                 parent=None):
        super().__init__(parent)
        self._min = minimum
        self._max = maximum
        self._value = max(minimum, min(maximum, value))
        self._default = self._value
        self._drag_y: float | None = None
        self._drag_origin: int = 0
        self.setFixedSize(54, 54)
        self.setCursor(Qt.CursorShape.SizeVerCursor)

    # ── Public API ───────────────────────────────────────────────────────────

    @property
    def value(self) -> int:
        return self._value

    def setValue(self, val: int, emit: bool = True):
        val = max(self._min, min(self._max, val))
        if val == self._value:
            return
        self._value = val
        self.update()
        if emit:
            self.valueChanged.emit(val)

    def setDefault(self, val: int):
        self._default = max(self._min, min(self._max, val))

    # ── Mouse interaction ────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_y = event.position().y()
            self._drag_origin = self._value

    def mouseMoveEvent(self, event):
        if self._drag_y is None:
            return
        dy = self._drag_y - event.position().y()
        delta = int(dy * (self._max - self._min) / 120)
        self.setValue(self._drag_origin + delta)

    def mouseReleaseEvent(self, event):
        self._drag_y = None

    def mouseDoubleClickEvent(self, event):
        self.setValue(self._default)

    # ── Painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = 7
        r = min(w, h) // 2 - margin
        cx, cy = w // 2, h // 2

        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        arc_w = 3

        # Background track arc
        track_pen = QPen(QColor("#3a3a3e"), arc_w)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, self._START_DEG * 16, -self._SWEEP_DEG * 16)

        # Active (green) arc
        frac = (self._value - self._min) / (self._max - self._min) if self._max > self._min else 0.0
        active_span = int(-self._SWEEP_DEG * 16 * frac)
        if abs(active_span) >= 1:
            active_pen = QPen(QColor("#30d158"), arc_w)
            active_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(active_pen)
            painter.drawArc(rect, self._START_DEG * 16, active_span)

        # Body circle
        body_r = r - arc_w - 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2a2a2e"))
        painter.drawEllipse(QRectF(cx - body_r, cy - body_r, body_r * 2, body_r * 2))

        # Pointer line
        angle_rad = math.radians(self._START_DEG - self._SWEEP_DEG * frac)
        tip_r = body_r - 3
        px = cx + tip_r * math.cos(angle_rad)
        py = cy - tip_r * math.sin(angle_rad)  # screen y is inverted
        painter.setPen(QPen(QColor("#e0e0e0"), 2, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        inner = 4
        ix = cx + inner * math.cos(angle_rad)
        iy = cy - inner * math.sin(angle_rad)
        painter.drawLine(int(ix), int(iy), int(px), int(py))
