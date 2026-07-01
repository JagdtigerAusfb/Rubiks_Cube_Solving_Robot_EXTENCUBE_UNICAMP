"""Entry point — initialises the Qt application and launches the main window."""

import logging
import sys

from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtGui import QIcon

from config import LOGO_PATH
from ui.cover       import CoverPage
from ui.calibration import CalibrationPage
from ui.color_calib import ColorCalibrationPage
from ui.capture     import CubeStateCapturePage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class MainApp(QStackedWidget):
    """Root stacked widget — owns every page and shared state."""

    def __init__(self):
        super().__init__()
        self.camera_index = 0

        # Pages — order matters: index 0–3 used for navigation
        self.cover_page        = CoverPage(self)
        self.calibration_page  = CalibrationPage(self)
        self.color_page        = ColorCalibrationPage(self)
        self.cube_page         = CubeStateCapturePage(self)

        self.addWidget(self.cover_page)       # 0
        self.addWidget(self.calibration_page) # 1
        self.addWidget(self.color_page)       # 2
        self.addWidget(self.cube_page)        # 3

    def closeEvent(self, event):
        self.cover_page.close_serial()
        logger.info("Application closing")
        event.accept()


def main():
    app = QApplication(sys.argv)

    window = MainApp()
    window.setWindowTitle("Rubik's Cube Robot Solver")
    window.setWindowIcon(QIcon(LOGO_PATH))
    window.resize(900, 750)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
