"""
CAD Studio 2026 - Desktop Application Entry Point
"""

import sys
import os

# Ensure current directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from cad_ui.main_window import CadMainWindow


def main():
    # Set high DPI policy
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("AutoCAD 2026 Engine")
    app.setOrganizationName("CAD Studio")

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "autocad.ico")
    if os.path.exists(icon_path):
        from PyQt6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))

    window = CadMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

