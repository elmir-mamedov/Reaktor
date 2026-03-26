import matplotlib
matplotlib.use("QtAgg")  # Must be set before any other matplotlib import

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow
from ui.styles import APP_STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Reaktor")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
