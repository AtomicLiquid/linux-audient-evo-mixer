from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient

_HANDLE_H = 20
_HANDLE_W = 24
_TRACK_W = 4
_PAD = _HANDLE_H // 2 + 4


class Fader(QWidget):
    """Vertical fader widget.

    Drag the handle to change value, or click anywhere on the track to jump.
    """

    valueChanged = pyqtSignal(int)

    def __init__(self, minimum: int = 0, maximum: int = 1000, value: int = 750,
                 parent=None):
        super().__init__(parent)
        self._min = minimum
        self._max = maximum
        self._value = max(minimum, min(maximum, value))
        self._drag_y: float | None = None
        self._drag_origin: int = 0
        self.setFixedWidth(36)
        self.setMinimumHeight(130)
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

    # ── Geometry helpers ─────────────────────────────────────────────────────

    def _usable_height(self) -> float:
        return self.height() - 2 * _PAD

    def _value_to_y(self, val: int) -> float:
        frac = (val - self._min) / (self._max - self._min)
        return _PAD + self._usable_height() * (1.0 - frac)

    def _y_to_value(self, y: float) -> int:
        usable = self._usable_height()
        frac = 1.0 - (y - _PAD) / usable
        frac = max(0.0, min(1.0, frac))
        return int(self._min + frac * (self._max - self._min))

    # ── Mouse interaction ────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_y = event.position().y()
            self._drag_origin = self._value
            # Jump-to-click if not near handle
            hy = self._value_to_y(self._value)
            if abs(event.position().y() - hy) > _HANDLE_H:
                self.setValue(self._y_to_value(event.position().y()))
                self._drag_origin = self._value

    def mouseMoveEvent(self, event):
        if self._drag_y is None:
            return
        dy = self._drag_y - event.position().y()
        usable = self._usable_height()
        delta = int(dy * (self._max - self._min) / usable)
        self.setValue(self._drag_origin + delta)

    def mouseReleaseEvent(self, event):
        self._drag_y = None

    # ── Painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        cx = w // 2
        track_top = _PAD
        track_bot = self.height() - _PAD

        # Track
        track_rect = QRectF(cx - _TRACK_W / 2, track_top, _TRACK_W, track_bot - track_top)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2e2e34"))
        painter.drawRoundedRect(track_rect, 2, 2)

        # Filled portion (below handle = quieter)
        hy = self._value_to_y(self._value)
        active_rect = QRectF(cx - _TRACK_W / 2, hy, _TRACK_W, track_bot - hy)
        painter.setBrush(QColor("#3a5a44"))
        painter.drawRoundedRect(active_rect, 2, 2)

        # Handle
        hx = cx - _HANDLE_W / 2
        handle_rect = QRectF(hx, hy - _HANDLE_H / 2, _HANDLE_W, _HANDLE_H)
        grad = QLinearGradient(handle_rect.topLeft(), handle_rect.bottomLeft())
        grad.setColorAt(0.0, QColor("#72727a"))
        grad.setColorAt(1.0, QColor("#4a4a52"))
        painter.setBrush(grad)
        painter.setPen(QPen(QColor("#909098"), 1))
        painter.drawRoundedRect(handle_rect, 3, 3)

        # Grip lines on handle
        painter.setPen(QPen(QColor("#b0b0b8"), 1))
        for offset in (-4, 0, 4):
            y_line = hy + offset
            painter.drawLine(int(cx - 7), int(y_line), int(cx + 7), int(y_line))
