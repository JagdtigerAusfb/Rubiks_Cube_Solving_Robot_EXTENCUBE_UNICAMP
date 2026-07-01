import os

BASE_DIR = os.path.dirname(__file__)

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR   = os.path.join(BASE_DIR, "data")

LOGO_PATH        = os.path.join(ASSETS_DIR, "logo_pro.jpg")
CUBE_STATE_PATH  = os.path.join(DATA_DIR, "cube_state.json")
COLORS_PATH      = os.path.join(DATA_DIR, "colors.json")
ROIS_PATH        = os.path.join(DATA_DIR, "rois.json")

# Scanning order used in ColorCalibrationPage
COLOR_ORDER = ["White", "Red", "Green", "Yellow", "Orange", "Blue"]

# Maps color name to cube-face letter (Kociemba notation)
COLOR_TO_FACE = {
    "White":  "U",
    "Yellow": "D",
    "Green":  "F",
    "Red":    "R",
    "Orange": "L",
    "Blue":   "B",
}

# Converts a standard Kociemba move to the robot's single-character serial code
MOVE_TABLE = {
    "U":  "A", "U'": "B", "U2": "C",
    "R":  "D", "R'": "E", "R2": "F",
    "F":  "G", "F'": "H", "F2": "I",
    "D":  "J", "D'": "K", "D2": "L",
    "L":  "M", "L'": "N", "L2": "O",
    "B":  "P", "B'": "Q", "B2": "R",
}

# Serial communication defaults
SERIAL_BAUDRATE = 9600
SERIAL_TIMEOUT  = 1
SERIAL_INIT_DELAY = 3  # seconds — do not reduce below 3 s (Arduino reset guard)

# UI defaults
CAMERA_RANGE   = (0, 5)
ROI_DEFAULT_SIZE = 60
ROI_DEFAULT_GAP  = 20
ROBOT_SPEED_RANGE  = (1, 10000)
ROBOT_SPEED_DEFAULT = 1000
ROBOT_DELAY_RANGE   = (0, 2000)
ROBOT_DELAY_DEFAULT = 10
