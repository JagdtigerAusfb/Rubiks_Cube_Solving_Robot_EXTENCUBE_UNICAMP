"""Centralised Qt stylesheet definitions."""

# --- Base tokens ---
_BTN_BASE = (
    "font-size: 16px; font-weight: bold; border-radius: 8px; "
    "padding: 10px; min-height: 40px; color: white;"
)
_SPINBOX = """
QSpinBox {
    padding: 6px;
    font-weight: bold;
}
QSpinBox::up-button   { width: 35px; }
QSpinBox::down-button { width: 35px; }
"""


def btn_style(bg: str, hover: str) -> str:
    return (
        f"QPushButton {{ background-color: {bg}; {_BTN_BASE} }}"
        f"QPushButton:hover {{ background-color: {hover}; }}"
    )


# Pre-defined button palettes
BTN_RED    = btn_style("#e74c3c", "#c0392b")
BTN_ORANGE = btn_style("#f39c12", "#e67e22")
BTN_BLUE   = btn_style("#3498db", "#2980b9")
BTN_GREEN  = btn_style("#2ecc71", "#27ae60")
BTN_PURPLE = btn_style("#B027F5", "#27ae60")

SPINBOX = _SPINBOX

MANUAL_INPUT = """
QLineEdit {
    background-color: #6527F5;
    color: white;
    border-radius: 6px;
    padding: 8px;
    font-weight: bold;
}
"""

PORT_COMBO = """
QComboBox {
    padding: 6px;
    font-weight: bold;
}
QComboBox QAbstractItemView {
    background-color: black;
    color: white;
    selection-background-color: #3498db;
}
"""

TIME_DISPLAY = """
QLabel {
    background-color: #4A6D70;
    color: white;
    border-radius: 10px;
    padding: 10px;
    font-weight: bold;
}
"""

SEPARATOR = "border: 1px solid rgba(255,255,255,128); background-color: rgba(255,255,255,128);"
