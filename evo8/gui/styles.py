STYLESHEET = """
/* ── Base ──────────────────────────────────────────────────────────── */
QMainWindow, QWidget {
    background-color: #1a1a1e;
    color: #ffffff;
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 11px;
}

/* ── Status bar ──────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #111114;
    color: #555555;
    font-size: 10px;
    border-top: 1px solid #2a2a2e;
}

/* ── Mixer header bar ────────────────────────────────────────────────── */
QFrame#mixerHeader {
    background-color: #111114;
}

QLabel#headerTitle {
    color: #ffffff;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 3px;
}

QLabel#clockOn {
    color: #30d158;
    font-size: 14px;
}

QLabel#clockOff {
    color: #333338;
    font-size: 14px;
}

/* ── Dividers ────────────────────────────────────────────────────────── */
QFrame#divider {
    color: #2a2a30;
}

/* ── Channel strip labels ────────────────────────────────────────────── */
QLabel#stripLabel {
    color: #888888;
    font-size: 9px;
    letter-spacing: 1px;
}

QLabel#dbLabel {
    color: #555555;
    font-size: 9px;
}

/* ── Output panel background ─────────────────────────────────────────── */
QWidget#outputPanel {
    background-color: #161618;
}

/* ── Output tab buttons ──────────────────────────────────────────────── */
QPushButton#outputTabBtn {
    background-color: #222226;
    color: #606068;
    border: 1px solid #333338;
    border-radius: 3px;
    font-size: 9px;
    font-weight: bold;
    letter-spacing: 1px;
    padding: 3px 8px;
    text-align: left;
}
QPushButton#outputTabBtn:checked {
    background-color: #1a2e20;
    color: #e0e0e0;
    border: 1px solid #30d158;
}
QPushButton#outputTabBtn:hover:!checked {
    background-color: #2a2a30;
    color: #888888;
}

/* ── EXT UNIT toggle ─────────────────────────────────────────────────── */
QPushButton#extUnitBtn {
    background-color: #2c2c32;
    color: #888888;
    border: 1px solid #48484c;
    border-radius: 3px;
    font-size: 9px;
    font-weight: bold;
    padding: 2px 8px;
}
QPushButton#extUnitBtn:checked {
    background-color: #1a3a28;
    color: #30d158;
    border: 1px solid #30d158;
}
QPushButton#extUnitBtn:hover:!checked {
    background-color: #3a3a40;
}

/* ── Vertical faders ─────────────────────────────────────────────────── */
QSlider::groove:vertical {
    width: 4px;
    background: #252528;
    border-radius: 2px;
}
QSlider::handle:vertical {
    width: 22px;
    height: 10px;
    background: #525258;
    border: 1px solid #747480;
    border-radius: 2px;
    margin: 0 -9px;
}
QSlider::handle:vertical:hover {
    background: #727280;
    border-color: #a0a0a8;
}
QSlider::sub-page:vertical {
    background: #1e4a2a;
    border-radius: 2px;
}
"""
