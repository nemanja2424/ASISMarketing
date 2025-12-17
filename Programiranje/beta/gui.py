# gui.py
import sys
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QSpacerItem,
    QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from BW_Controller.create_profile import create_profile


class MainGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASIS Marketing Browser")
        self.resize(1800, 900)
        self.setWindowIcon(QIcon("Media/logo.png"))
        self.init_ui()

    def init_ui(self):
        # ===== Glavni layout =====
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== Sidebar =====
        sidebar = QFrame()
        sidebar.setFixedWidth(180)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)

        btn_profiles = QPushButton("Profili")
        btn_logs = QPushButton("Logovi")
        btn_campaigns = QPushButton("Kampanje")

        btn_profiles.clicked.connect(self.show_profiles_page)
        btn_logs.clicked.connect(self.show_logs_page)
        btn_campaigns.clicked.connect(self.show_campaigns_page)

        sidebar_layout.addStretch()
        sidebar_layout.addWidget(btn_profiles)
        sidebar_layout.addWidget(btn_logs)
        sidebar_layout.addWidget(btn_campaigns)

        # ===== Content =====
        self.content = QFrame()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(20)

        self.show_profiles_page()

        # ===== Layout add =====
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content, stretch=1)

    # ==========================
    # Helpers
    # ==========================

    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())

    def build_header(self, title_text, right_widget=None):
        header_layout = QHBoxLayout()

        title = QLabel(title_text)
        title.setAlignment(Qt.AlignVCenter)

        header_layout.addWidget(title)
        header_layout.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        if right_widget:
            header_layout.addWidget(right_widget)

        self.content_layout.addLayout(header_layout)

    # ==========================
    # Pages
    # ==========================

    def show_profiles_page(self):
        self.clear_content()

        btn_create_profile = QPushButton("Napravi profil")
        btn_create_profile.clicked.connect(create_profile)
        self.build_header("Profili", btn_create_profile)

        placeholder = QLabel("Ovde će se prikazivati lista profila")
        placeholder.setAlignment(Qt.AlignCenter)

        self.content_layout.addStretch()
        self.content_layout.addWidget(placeholder)
        self.content_layout.addStretch()

    def show_logs_page(self):
        self.clear_content()

        self.build_header("Logovi")

        placeholder = QLabel("Ovde će se prikazivati logovi")
        placeholder.setAlignment(Qt.AlignCenter)

        self.content_layout.addStretch()
        self.content_layout.addWidget(placeholder)
        self.content_layout.addStretch()

    def show_campaigns_page(self):
        self.clear_content()

        self.build_header("Kampanje")

        placeholder = QLabel("Ovde će se prikazivati kampanje")
        placeholder.setAlignment(Qt.AlignCenter)

        self.content_layout.addStretch()
        self.content_layout.addWidget(placeholder)
        self.content_layout.addStretch()


def run_gui():
    app = QApplication(sys.argv)
    gui = MainGUI()
    gui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
