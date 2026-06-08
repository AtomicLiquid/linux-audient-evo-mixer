#!/usr/bin/env python3
import logging
import sys

from PyQt6.QtWidgets import QApplication

from evo8.gui.main_window import MainWindow


def _setup_logging():
    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(fmt)

    file_handler = logging.FileHandler("evo8.log", encoding="utf-8")
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(stderr_handler)
    root.addHandler(file_handler)

    # Suppress noisy library loggers
    logging.getLogger("usb").setLevel(logging.WARNING)


def main():
    _setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("EVO 8 Mixer")
    app.setOrganizationName("Audient")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
