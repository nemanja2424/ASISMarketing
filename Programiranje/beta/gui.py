# gui.py
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
import sys

class MainGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASIS Marketing Browser")
        self.resize(800, 600)
        self.setWindowIcon(QIcon("Media/logo.png"))
        self.init_ui()

    def init_ui(self):
        # Glavni horizontalni layout
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # Sidebar
        sidebar = QFrame(objectName="sidebar")
        sidebar.setFixedWidth(150)
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setAlignment(Qt.AlignBottom)
        sidebar.setLayout(sidebar_layout)

        # Dugmad
        btn_profiles = QPushButton("Profili")
        btn_logs = QPushButton("Logovi")
        btn_campaigns = QPushButton("Kampanje")
        sidebar_layout.addWidget(btn_profiles)
        sidebar_layout.addWidget(btn_logs)
        sidebar_layout.addWidget(btn_campaigns)

        # Glavni content
        content = QFrame()
        content.setFrameShape(QFrame.StyledPanel)
        content_layout = QVBoxLayout()
        content.setLayout(content_layout)
        label = QLabel("Ovde ide glavni sadržaj aplikacije")
        label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(label)

        # Dodavanje u glavni layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content, stretch=1)

        # Stilizacija
        self.setStyleSheet("""
            QWidget {
                background-color: #2e2e2e;
                color: #ffffff;
                font-family: Arial;
                font-size: 14px;
            }
            QFrame#sidebar {
                background-color: #1f1f1f;
            }
            QPushButton {
                background-color: #3c3c3c;
                border: none;
                padding: 12px;
                margin: 5px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #686868;
            }
        """)

# Funkcija koja pokreće GUI
def run_gui():
    app = QApplication(sys.argv)
    gui = MainGUI()
    gui.show()
    sys.exit(app.exec())
