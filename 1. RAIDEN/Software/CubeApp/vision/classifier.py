"""Computer-vision helpers: color space extraction and classification."""

import cv2
import numpy as np


def euclidean(a, b) -> float:
    return float(np.linalg.norm(np.array(a) - np.array(b)))


def extract_color_stats(bgr_patch: np.ndarray) -> tuple:
    """Returns (mean_hsv, mean_lab, mean_rgb) for a BGR image patch."""
    hsv = cv2.cvtColor(bgr_patch, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr_patch, cv2.COLOR_BGR2LAB)
    mean_hsv = np.mean(hsv.reshape(-1, 3), axis=0)
    mean_lab = np.mean(lab.reshape(-1, 3), axis=0)
    mean_rgb = np.mean(bgr_patch.reshape(-1, 3), axis=0)[::-1]
    return mean_hsv, mean_lab, mean_rgb


def classify(mean_hsv, mean_lab, mean_rgb, colors_ref_roi: dict) -> str:
    """Classifies a color patch against a reference dict using a weighted distance."""
    W_HSV = 0.4
    W_LAB = 0.6
    W_RGB = 0.0
    return min(
        colors_ref_roi.keys(),
        key=lambda c: (
            W_HSV * euclidean(mean_hsv, colors_ref_roi[c]["HSV"])
            + W_LAB * euclidean(mean_lab, colors_ref_roi[c]["LAB"])
            + W_RGB * euclidean(mean_rgb, colors_ref_roi[c]["RGB"])
        ),
    )
