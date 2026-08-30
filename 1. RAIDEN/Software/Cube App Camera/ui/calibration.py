"""ROI calibration page — the user positions the 3×3 grid over the cube face."""

import json
import logging

import cv2
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpinBox,
)
from PyQt6.QtCore import QTimer

from config import ROIS_PATH, CAMERA_RANGE, ROI_DEFAULT_SIZE, ROI_DEFAULT_GAP
from vision.camera import bgr_to_qpixmap

logger = logging.getLogger(__name__)


class CalibrationPage(QWidget):
    """Lets the user align a 3×3 ROI grid and save the positions."""

    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.cap            = None
        self.current_frame  = None

        self.center_x = 400
        self.center_y = 300
        self.roi_size = ROI_DEFAULT_SIZE
        self.gap      = ROI_DEFAULT_GAP

        self._timer = QTimer()
        self._timer.timeout.connect(self._update_frame)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Camera selector
        self.camera_spin = QSpinBox()
        self.camera_spin.setRange(*CAMERA_RANGE)
        self.camera_spin.setValue(self.stacked_widget.camera_index)
        self.camera_spin.valueChanged.connect(self._on_camera_changed)

        cam_row = QHBoxLayout()
        cam_row.addWidget(QLabel("Camera"))
        cam_row.addWidget(self.camera_spin)
        cam_row.addStretch()

        # Live preview
        self.image_label = QLabel()
        self.image_label.setFixedSize(800, 600)

        # ROI settings
        self.size_spin = QSpinBox()
        self.size_spin.setRange(20, 200)
        self.size_spin.setValue(self.roi_size)
        self.size_spin.valueChanged.connect(lambda v: setattr(self, "roi_size", v))

        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(0, 100)
        self.gap_spin.setValue(self.gap)
        self.gap_spin.valueChanged.connect(lambda v: setattr(self, "gap", v))

        settings_row = QHBoxLayout()
        settings_row.addWidget(QLabel("ROI Size"))
        settings_row.addWidget(self.size_spin)
        settings_row.addWidget(QLabel("Gap"))
        settings_row.addWidget(self.gap_spin)

        # Directional controls
        btn_up    = QPushButton("Up")
        btn_down  = QPushButton("Down")
        btn_left  = QPushButton("Left")
        btn_right = QPushButton("Right")
        btn_up.clicked.connect(lambda: self._move(0, -10))
        btn_down.clicked.connect(lambda: self._move(0, 10))
        btn_left.clicked.connect(lambda: self._move(-10, 0))
        btn_right.clicked.connect(lambda: self._move(10, 0))

        controls_row = QHBoxLayout()
        for btn in (btn_left, btn_up, btn_down, btn_right):
            controls_row.addWidget(btn)

        btn_save = QPushButton("Save ROIs")
        btn_save.clicked.connect(self._save_rois)
        btn_back = QPushButton("Back")
        btn_back.clicked.connect(self._go_home)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(cam_row)
        layout.addWidget(self.image_label)
        layout.addLayout(controls_row)
        layout.addLayout(settings_row)
        layout.addWidget(btn_save)
        layout.addWidget(btn_back)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Camera management
    # ------------------------------------------------------------------

    def start_camera(self, cam_index: int):
        self.stop_camera()
        self.cap = cv2.VideoCapture(cam_index)
        self._timer.start(30)

    def stop_camera(self):
        self._timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_camera_changed(self, value: int):
        self.stacked_widget.camera_index = value
        self.stacked_widget.cover_page.camera_spin.setValue(value)
        self.start_camera(value)

    def _move(self, dx: int, dy: int):
        self.center_x += dx
        self.center_y += dy

    def _draw_grid(self, frame):
        rois  = []
        total = 3 * self.roi_size + 2 * self.gap
        sx    = self.center_x - total // 2
        sy    = self.center_y - total // 2
        for row in range(3):
            for col in range(3):
                x = sx + col * (self.roi_size + self.gap)
                y = sy + row * (self.roi_size + self.gap)
                cv2.rectangle(frame, (x, y), (x + self.roi_size, y + self.roi_size), (0, 255, 0), 2)
                rois.append({"x": x, "y": y, "size": self.roi_size})
        return frame, rois

    def _save_rois(self):
        if self.current_frame is None:
            return
        _, rois = self._draw_grid(self.current_frame.copy())
        with open(ROIS_PATH, "w") as f:
            json.dump(rois, f, indent=4)
        logger.info("ROIs saved to %s", ROIS_PATH)

        self.stop_camera()
        self.stacked_widget.color_page.load_rois(rois)
        self.stacked_widget.setCurrentIndex(2)
        self.stacked_widget.color_page.start_camera(self.stacked_widget.camera_index)

    def _update_frame(self):
        if not self.cap:
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        self.current_frame = frame.copy()
        frame, _ = self._draw_grid(frame)
        self.image_label.setPixmap(bgr_to_qpixmap(frame))

    def _go_home(self):
        self.stop_camera()
        self.stacked_widget.setCurrentIndex(0)
