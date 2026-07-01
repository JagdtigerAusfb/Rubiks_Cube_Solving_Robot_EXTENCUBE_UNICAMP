"""Camera frame utilities: OpenCV → Qt conversion."""

import cv2
from PyQt6.QtGui import QImage, QPixmap


def bgr_to_qpixmap(bgr_frame) -> QPixmap:
    """Converts a BGR OpenCV frame to a QPixmap ready for display."""
    rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qt_image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qt_image)


def draw_roi_grid(frame, rois: list, color=(0, 255, 0), thickness=2):
    """Draws ROI rectangles on *frame* in-place and returns the frame."""
    for roi in rois:
        x, y, s = roi["x"], roi["y"], roi["size"]
        cv2.rectangle(frame, (x, y), (x + s, y + s), color, thickness)
    return frame
