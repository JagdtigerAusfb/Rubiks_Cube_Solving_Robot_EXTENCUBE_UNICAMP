"""Color calibration page — captures reference color samples for each face."""

import json
import logging

import cv2
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer

from config import COLORS_PATH, COLOR_ORDER
from vision.classifier import extract_color_stats
from vision.camera import bgr_to_qpixmap, draw_roi_grid

logger = logging.getLogger(__name__)


class ColorCalibrationPage(QWidget):
    """Steps through each cube color and captures the reference HSV/LAB/RGB values."""

    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.cap            = None
        self.current_frame  = None
        self.rois           = []
        self.color_index    = 0
        self.results: dict  = {}

        self._timer = QTimer()
        self._timer.timeout.connect(self._update_frame)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.image_label = QLabel()
        self.image_label.setFixedSize(800, 600)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_capture = QPushButton("Capture Color")
        btn_capture.clicked.connect(self._capture_color)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.info_label)
        layout.addWidget(btn_capture)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_rois(self, rois: list):
        self.rois        = rois
        self.color_index = 0
        self.results     = {}
        self._update_label()

    def start_camera(self, cam_index: int):
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

    def _update_label(self):
        self.info_label.setText(f"Place color: {COLOR_ORDER[self.color_index]}")

    def _update_frame(self):
        if not self.cap:
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        self.current_frame = frame.copy()
        self.image_label.setPixmap(bgr_to_qpixmap(draw_roi_grid(frame, self.rois)))

    def _capture_color(self):
        if self.current_frame is None:
            return
        color = COLOR_ORDER[self.color_index]

        for i, roi in enumerate(self.rois):
            x, y, s = roi["x"], roi["y"], roi["size"]
            patch   = self.current_frame[y:y + s, x:x + s]
            mean_hsv, mean_lab, mean_rgb = extract_color_stats(patch)

            roi_key = f"roi_{i + 1}"
            self.results.setdefault(roi_key, {})[color] = {
                "HSV": mean_hsv.tolist(),
                "LAB": mean_lab.tolist(),
                "RGB": mean_rgb.tolist(),
            }

        logger.info("Captured color: %s", color)
        self.color_index += 1

        if self.color_index == len(COLOR_ORDER):
            with open(COLORS_PATH, "w") as f:
                json.dump(self.results, f, indent=4)
            logger.info("Color reference saved to %s", COLORS_PATH)
            self.stop_camera()
            self.stacked_widget.setCurrentIndex(0)
        else:
            self._update_label()
