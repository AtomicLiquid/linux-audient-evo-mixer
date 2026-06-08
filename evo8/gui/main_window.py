from PyQt6.QtWidgets import QMainWindow, QStatusBar
from PyQt6.QtCore import QTimer

from ..alsa_mixer import AlsaMixer
from .alsa_panel import AlsaPanel
from .styles import STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EVO 8 Mixer")
        self.setStyleSheet(STYLESHEET)

        self._alsa = AlsaMixer()

        self._panel = AlsaPanel(self._alsa)
        self.setCentralWidget(self._panel)

        self._status = QStatusBar()
        self.setStatusBar(self._status)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2000)
        self._poll_timer.timeout.connect(self._poll_device)
        self._poll_timer.start()

        self._poll_device()
        self.resize(500, 480)

    def _poll_device(self):
        if self._alsa.is_available():
            self._status.showMessage("EVO 8 connected")
        else:
            self._status.showMessage("EVO 8 not found — retrying…")

    def closeEvent(self, event):
        self._poll_timer.stop()
        super().closeEvent(event)
