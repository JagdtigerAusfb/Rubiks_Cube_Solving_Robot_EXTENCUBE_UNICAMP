"""Cube state capture page — scans all 6 faces and writes cube_state.json."""

import json
import logging

import cv2
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, QTimer

from config import ROIS_PATH, COLORS_PATH, CUBE_STATE_PATH, COLOR_TO_FACE
from vision.classifier import extract_color_stats, classify
from vision.camera import bgr_to_qpixmap, draw_roi_grid

logger = logging.getLogger(__name__)

FACE_ORDER = ["U", "R", "F", "D", "L", "B"]


class CubeStateCapturePage(QWidget):
    """Guides the user through showing each face, classifying colors, and saving state."""

    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.cap            = None
        self.current_frame  = None
        self.rois: list     = []
        self.colors_ref: dict = {}
        self.face_index     = 0
        self.cube_string    = ""

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

        btn_capture = QPushButton("Capture Face")
        btn_capture.clicked.connect(self._capture_face)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.info_label)
        layout.addWidget(btn_capture)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_data(self):
        with open(ROIS_PATH) as f:
            self.rois = json.load(f)
        with open(COLORS_PATH) as f:
            self.colors_ref = json.load(f)
        self.face_index  = 0
        self.cube_string = ""
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
        self.info_label.setText(f"Show face {self.face_index + 1} / 6  ({FACE_ORDER[self.face_index]})")

    def _update_frame(self):
        if not self.cap:
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        self.current_frame = frame.copy()
        self.image_label.setPixmap(bgr_to_qpixmap(draw_roi_grid(frame, self.rois)))

    def _capture_face(self):
        if self.current_frame is None:
            return

        # Sort ROIs top-to-bottom, right-to-left (mirror-flipped camera)
        sorted_rois = sorted(self.rois, key=lambda r: (r["y"], -r["x"]))
        face_string = ""

        for roi in sorted_rois:
            x, y, s = roi["x"], roi["y"], roi["size"]
            patch   = self.current_frame[y:y + s, x:x + s]
            mean_hsv, mean_lab, mean_rgb = extract_color_stats(patch)
            roi_key  = f"roi_{self.rois.index(roi) + 1}"
            color    = classify(mean_hsv, mean_lab, mean_rgb, self.colors_ref[roi_key])
            face_string += COLOR_TO_FACE[color]

        self.cube_string += face_string
        self.face_index  += 1
        logger.info("Captured face %d: %s", self.face_index, face_string)

        if self.face_index == 6:
            with open(CUBE_STATE_PATH, "w") as f:
                json.dump({"cube_string": self.cube_string}, f, indent=4)
            logger.info("Cube state saved: %s", self.cube_string)
            QMessageBox.information(self, "Success", "Cube state saved!")
            self.stop_camera()
            self.stacked_widget.setCurrentIndex(0)
        else:
            self._update_label()
