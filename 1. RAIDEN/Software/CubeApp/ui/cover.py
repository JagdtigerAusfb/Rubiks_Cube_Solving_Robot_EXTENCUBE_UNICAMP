"""Cover (home) page — main control panel: solve, send to robot, settings."""

import logging

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QSpinBox, QTextEdit, QMessageBox, QLineEdit, QFrame,
    QSizePolicy, QComboBox,
)
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer

from config import (
    LOGO_PATH, CUBE_STATE_PATH,
    ROBOT_SPEED_RANGE, ROBOT_SPEED_DEFAULT,
    ROBOT_DELAY_RANGE, ROBOT_DELAY_DEFAULT,
    CAMERA_RANGE,
)
from robot.controller import RobotController
import solver.kociemba as kociemba_solver
import solver.m2op    as m2op_solver
from ui.styles import (
    BTN_RED, BTN_ORANGE, BTN_BLUE, BTN_GREEN, BTN_PURPLE,
    SPINBOX, MANUAL_INPUT, PORT_COMBO, TIME_DISPLAY, SEPARATOR,
)

logger = logging.getLogger(__name__)

_BTN_W = 280
_TITLE_FONT  = QFont("Arial", 26, QFont.Weight.Bold)
_COL_FONT    = QFont("Arial", 16, QFont.Weight.Bold)
_RESULT_FONT = QFont("Arial", 10, QFont.Weight.Bold)


def _separator(shape: QFrame.Shape) -> QFrame:
    line = QFrame()
    line.setFrameShape(shape)
    line.setStyleSheet(SEPARATOR)
    if shape == QFrame.Shape.HLine:
        line.setFixedHeight(2)
    else:
        line.setFixedWidth(2)
    return line


class CoverPage(QWidget):
    """Home screen — solve buttons, robot controls, result display."""

    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.setStyleSheet("font-weight: bold;")

        self.robot = RobotController()

        self._serial_timer = QTimer()
        self._serial_timer.timeout.connect(self._poll_robot)
        self._serial_timer.start(50)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        btn_size = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        # --- Title ---
        title = QLabel("Rubik's Cube Robot Solver")
        title.setFont(_TITLE_FONT)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- Logo ---
        logo_label = QLabel()
        pix = QPixmap(LOGO_PATH)
        logo_label.setPixmap(
            pix.scaled(180, 160, Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        )
        logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # --- Time display ---
        self.time_display = QLabel("Time: -- s")
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_display.setFont(QFont("Arial", 58, QFont.Weight.Bold))
        self.time_display.setFixedHeight(160)
        self.time_display.setStyleSheet(TIME_DISPLAY)

        # --- Camera selector (shared, synced with CalibrationPage) ---
        self.camera_spin = QSpinBox()
        self.camera_spin.setRange(*CAMERA_RANGE)
        self.camera_spin.setValue(0)
        self.camera_spin.setStyleSheet("font-weight: bold;")

        # --- Action buttons ---
        self.btn_calib = self._make_btn("Calibration", BTN_RED, self._open_calibration)
        btn_capture    = self._make_btn("Capture Cube State", BTN_ORANGE, self._open_capture)
        btn_kociemba   = self._make_btn("Calculate with Kociemba", BTN_BLUE, self._solve_kociemba)
        btn_m2op       = self._make_btn("Calculate with M2/OP", BTN_BLUE, self._solve_m2op)
        btn_send       = self._make_btn("Send Solve", BTN_GREEN, self._send_to_robot)
        btn_inverted   = self._make_btn("Send Scramble (Reverse)", BTN_GREEN, self._send_inverted_to_robot)

        for b in (self.btn_calib, btn_capture, btn_kociemba, btn_m2op, btn_send, btn_inverted):
            b.setFixedWidth(_BTN_W)
            b.setSizePolicy(btn_size)

        # --- Result area ---
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setMinimumWidth(350)
        self.result_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.result_area.setFont(_RESULT_FONT)

        # --- Manual sequence ---
        self.manual_input = QLineEdit()
        self.manual_input.setStyleSheet(MANUAL_INPUT)
        self.manual_input.setPlaceholderText("e.g.  R U R' U'  R U2 R'")
        btn_manual = QPushButton("Send Manual Sequence")
        btn_manual.clicked.connect(self._send_manual_sequence)
        btn_manual.setStyleSheet(BTN_PURPLE)

        # --- Serial settings ---
        self.port_combo = QComboBox()
        self.port_combo.setStyleSheet(PORT_COMBO)

        btn_refresh = QPushButton("↻ Refresh")
        btn_refresh.setStyleSheet(
            "padding: 6px; font-weight: bold; background-color: #95a5a6; color: white; border-radius: 4px;"
        )
        btn_refresh.clicked.connect(self._refresh_ports)

        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(*ROBOT_SPEED_RANGE)
        self.speed_spin.setValue(ROBOT_SPEED_DEFAULT)
        self.speed_spin.setStyleSheet(SPINBOX)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(*ROBOT_DELAY_RANGE)
        self.delay_spin.setValue(ROBOT_DELAY_DEFAULT)
        self.delay_spin.setStyleSheet(SPINBOX)

        self._refresh_ports()

        # ------------------------------------------------------------------
        # Layout assembly
        # ------------------------------------------------------------------
        root = QVBoxLayout()
        root.addWidget(title)

        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        logo_row.setSpacing(10)
        logo_row.addWidget(logo_label)
        logo_row.addWidget(self.time_display, stretch=1)
        root.addLayout(logo_row)
        root.addWidget(_separator(QFrame.Shape.HLine))

        # Three-column action area
        cols = QHBoxLayout()

        col1 = self._column("Calibration",       [self.btn_calib, btn_capture])
        col2 = self._column("Calculate Solution", [btn_kociemba, btn_m2op])
        col3 = self._column("Send to Robot",      [btn_send, btn_inverted])

        cols.addLayout(col1)
        cols.addWidget(_separator(QFrame.Shape.VLine))
        cols.addLayout(col2)
        cols.addWidget(_separator(QFrame.Shape.VLine))
        cols.addLayout(col3)

        left_panel = QVBoxLayout()
        left_panel.addLayout(cols)
        left_panel.addWidget(_separator(QFrame.Shape.HLine))

        # Serial settings row
        settings_row = QHBoxLayout()
        for label_text, widget in [
            ("Serial Port",            self.port_combo),
            ("Robot Speed",            self.speed_spin),
            ("Delay Between Moves (ms)", self.delay_spin),
        ]:
            col = QVBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: bold;")
            col.addWidget(lbl)
            col.addWidget(widget)
            settings_row.addLayout(col)
        settings_row.addWidget(btn_refresh)

        left_panel.addLayout(settings_row)
        left_panel.addWidget(_separator(QFrame.Shape.HLine))

        lbl_manual = QLabel("Manual Sequence")
        lbl_manual.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(lbl_manual)
        left_panel.addWidget(self.manual_input)
        left_panel.addWidget(btn_manual)

        right_panel = QVBoxLayout()
        lbl_result = QLabel("Result:")
        lbl_result.setStyleSheet("font-weight: bold;")
        right_panel.addWidget(lbl_result)
        right_panel.addWidget(self.result_area)

        split = QHBoxLayout()
        split.addLayout(left_panel)
        split.addWidget(_separator(QFrame.Shape.VLine))
        split.addLayout(right_panel)

        root.addLayout(split)
        self.setLayout(root)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_btn(text: str, style: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(style)
        btn.clicked.connect(slot)
        return btn

    @staticmethod
    def _column(title: str, buttons: list) -> QVBoxLayout:
        col = QVBoxLayout()
        lbl = QLabel(title)
        lbl.setFont(_COL_FONT)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(lbl)
        for btn in buttons:
            col.addWidget(btn)
        return col

    def _refresh_ports(self):
        self.port_combo.clear()
        for port in self.robot.list_ports():
            self.port_combo.addItem(port)

    # ------------------------------------------------------------------
    # Serial polling
    # ------------------------------------------------------------------

    def _poll_robot(self):
        if self.robot.check_for_done():
            self.time_display.setText(f"Time: {self.robot.last_elapsed} s")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _open_calibration(self):
        self.stacked_widget.camera_index = self.camera_spin.value()
        self.stacked_widget.setCurrentIndex(1)
        self.stacked_widget.calibration_page.start_camera(self.stacked_widget.camera_index)

    def _open_capture(self):
        self.stacked_widget.camera_index = self.camera_spin.value()
        self.stacked_widget.setCurrentIndex(3)
        self.stacked_widget.cube_page.load_data()
        self.stacked_widget.cube_page.start_camera(self.stacked_widget.camera_index)

    # ------------------------------------------------------------------
    # Solver actions
    # ------------------------------------------------------------------

    def _display_result(self, result: dict, method: str):
        if "error" in result:
            self.result_area.setText(f"Error:\n{result['error']}")
            return
        self.result_area.setText(
            f"===== SOLUTION ({method}) =====\n\n"
            f"{result['solution']}\n\n"
            f"===== NUMBER OF MOVES =====\n\n"
            f"{result['move_count']}\n\n"
            f"===== SEQUENCE FOR THE ROBOT =====\n\n"
            f"{result['robot_sequence']}\n\n"
            f"===== INVERTED SEQUENCE =====\n\n"
            f"{result['inverted_sequence']}"
        )

    def _solve_kociemba(self):
        self._display_result(kociemba_solver.solve_from_file(CUBE_STATE_PATH), "KOCIEMBA")

    def _solve_m2op(self):
        self._display_result(m2op_solver.solve_from_file(CUBE_STATE_PATH), "M2/OP")

    # ------------------------------------------------------------------
    # Robot dispatch
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> bool:
        if self.robot.is_connected:
            return True
        port = self.port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "Error", "No COM port detected or selected!")
            return False
        if not self.robot.connect(port):
            QMessageBox.warning(self, "Serial Error", f"Failed to connect to {port}.")
            return False
        return True

    def _dispatch(self, sequence: str):
        if not sequence:
            QMessageBox.warning(self, "Error", "Sequence is empty.")
            return
        if self.robot.is_busy:
            QMessageBox.information(self, "Robot Busy", "Wait until current execution finishes.")
            return
        if not self._ensure_connected():
            return
        speed = self.speed_spin.value()
        delay = self.delay_spin.value()
        if not self.robot.send_moves(sequence, speed, delay):
            QMessageBox.warning(self, "Error", "Failed to send sequence.")
            return
        self.time_display.setText("Executing...")

    def _parse_section(self, header: str) -> str | None:
        text = self.result_area.toPlainText()
        if header not in text:
            return None
        parts = text.split(header)
        if len(parts) < 2:
            return None
        after = parts[1]
        # Grab text until the next ===== block or end of string
        next_block = after.find("=====")
        return after[:next_block].strip() if next_block != -1 else after.strip()

    def _send_to_robot(self):
        seq = self._parse_section("===== SEQUENCE FOR THE ROBOT =====\n\n")
        if seq is None:
            QMessageBox.warning(self, "Error", "No robot sequence found. Solve the cube first.")
            return
        self._dispatch(seq)

    def _send_inverted_to_robot(self):
        seq = self._parse_section("===== INVERTED SEQUENCE =====\n\n")
        if seq is None:
            QMessageBox.warning(self, "Error", "No inverted sequence found. Solve the cube first.")
            return
        self._dispatch(seq)

    def _send_manual_sequence(self):
        raw = self.manual_input.text().strip()
        if not raw:
            QMessageBox.warning(self, "Error", "Manual sequence is empty.")
            return
        try:
            converted = RobotController.notation_to_robot(raw)
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return
        self._dispatch(converted)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close_serial(self):
        self.robot.disconnect()
