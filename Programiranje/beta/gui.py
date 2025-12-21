#gui.py
import sys
import os
import json
import multiprocessing
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QSpacerItem,
    QSizePolicy,
    QInputDialog,
    QScrollArea,
    QDialog,
    QTextEdit,
    QMessageBox,
    QCheckBox,
)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from BW_Controller.create_profile import create_profile
from BW_Controller.run_profile import run_profile_process


class MainGUI(QWidget):
    PROFILES_DIR = "profiles"

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

        # ===== Content (scrollable) =====
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(12)
        self.scroll.setWidget(self.content_widget)

        self.show_profiles_page()

        # ===== Layout add =====
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.scroll, stretch=1)

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
    # Profile loader
    # ==========================

    def load_profiles(self):
        """Učitava sve profile iz foldera (rekurzivno) i vraća listu dict-ova"""
        profiles = []
        if not os.path.exists(self.PROFILES_DIR):
            return profiles

        for root, dirs, files in os.walk(self.PROFILES_DIR):
            for filename in files:
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        # Only include files that look like profile meta or contain profile_id
                        if not data.get("profile_id"):
                            continue

                        display_name = data.get("metadata", {}).get("display_name") or data.get("profile_id")
                        profiles.append({
                            "profile_id": data.get("profile_id"),
                            "display_name": display_name,
                            "path": path
                        })
                    except Exception as e:
                        print(f"Greška pri učitavanju {path}: {e}")
        return profiles

    # ==========================
    # Pages
    # ==========================

    def show_profiles_page(self):
        self.clear_content()

        # Right-side header widgets: create + refresh
        btn_create_profile = QPushButton("Napravi profil")
        btn_create_profile.clicked.connect(self.on_create_profile_clicked)
        btn_refresh = QPushButton("Osvezi")
        btn_refresh.setFixedWidth(100)
        btn_refresh.setStyleSheet("padding:6px;")
        btn_refresh.clicked.connect(self.show_profiles_page)
        # container widget to hold multiple right-side buttons
        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        right_layout.addWidget(btn_refresh)
        right_layout.addWidget(btn_create_profile)
        self.build_header("Profili", right_container)

        # Učitavanje svih profila
        profiles = self.load_profiles()

        for profile in profiles:
            # Load profile.json to get namespaces
            try:
                with open(profile['path'], 'r', encoding='utf-8') as f:
                    pdata = json.load(f)
            except Exception:
                pdata = {}

            display_name = profile["display_name"]

            namespaces = pdata.get('namespaces', {})

            # If profile has a top-level category, prefer to show it when no namespace category exists
            top_cat = pdata.get('metadata', {}).get('category')

            if not namespaces:
                # Show a single styled row for profile with no namespaces
                row_frame = QFrame()
                row_frame.setFrameShape(QFrame.StyledPanel)
                row_frame.setStyleSheet("QFrame { background: #f6f8fa; border: 1px solid #e1e4e8; border-radius:6px; padding:8px; }")
                row_layout = QHBoxLayout(row_frame)
                lbl_name = QLabel(display_name)
                lbl_name.setStyleSheet("font-weight:600; font-size:14px;")
                btn_add_ns = QPushButton("Dodaj namespace")
                btn_add_ns.setFixedWidth(120)
                btn_add_ns.setStyleSheet("padding:6px;")
                btn_add_ns.clicked.connect(lambda _, p=profile['path']: self.on_add_namespace_clicked(p))

                row_layout.addWidget(lbl_name)
                row_layout.addSpacerItem(
                    QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
                )
                row_layout.addWidget(btn_add_ns)
                self.content_layout.addWidget(row_frame)
                continue

            # Otherwise show a styled card per namespace
            for ns_name, ns_path in namespaces.items():
                row_frame = QFrame()
                row_frame.setFrameShape(QFrame.StyledPanel)
                row_frame.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e6eef3; border-radius:6px; padding:8px; }")
                row_layout = QHBoxLayout(row_frame)

                lbl_name = QLabel(f"{display_name} / {ns_name}")
                lbl_name.setStyleSheet("font-weight:600; font-size:13px;")
                # show category if present
                try:
                    ns_meta = json.load(open(ns_path, 'r', encoding='utf-8'))
                    cat = ns_meta.get('category') or pdata.get('metadata', {}).get('category') or ''
                    if cat:
                        lbl_name.setText(f"{display_name} / {ns_name} ({cat})")
                    # Show consistency score if present
                    cons = ns_meta.get('consistency')
                    if cons:
                        score = cons.get('score')
                        verdict = cons.get('verdict', '')
                        lbl_cons = QLabel(f"Consistency: {score} ({verdict})")
                        # color by verdict
                        if verdict == 'OK':
                            lbl_cons.setStyleSheet('color: #0b6623; font-weight:600;')
                        elif verdict == 'WARN':
                            lbl_cons.setStyleSheet('color: #b66a00; font-weight:600;')
                        else:
                            lbl_cons.setStyleSheet('color: #b00020; font-weight:600;')
                        lbl_cons.setFixedWidth(160)
                        row_layout.addWidget(lbl_cons)
                except Exception:
                    pass

                btn_run = QPushButton("Run")
                btn_run.setFixedWidth(80)
                btn_run.setStyleSheet("padding:6px;")
                btn_run.clicked.connect(
                    lambda _, p=ns_path: self.run_profile_mp(p)
                )
                btn_add_ns = QPushButton("Dodaj namespace")
                btn_add_ns.setFixedWidth(120)
                btn_add_ns.setStyleSheet("padding:6px;")
                btn_add_ns.clicked.connect(lambda _, p=profile['path']: self.on_add_namespace_clicked(p))

                row_layout.addWidget(lbl_name)
                row_layout.addSpacerItem(
                    QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
                )
                row_layout.addWidget(btn_run)
                # Re-check consistency button
                btn_recheck = QPushButton("Recheck")
                btn_recheck.setFixedWidth(100)
                btn_recheck.setStyleSheet("padding:6px;")
                btn_recheck.clicked.connect(lambda _, p=ns_path: self.on_recheck_clicked(p))
                row_layout.addWidget(btn_recheck)

                # Show full consistency details
                btn_details = QPushButton("Detalji")
                btn_details.setFixedWidth(90)
                btn_details.setStyleSheet("padding:6px;")
                btn_details.clicked.connect(lambda _, p=ns_path: self.on_show_details_clicked(p))
                row_layout.addWidget(btn_details)

                # Repair (normalize) fingerprint heuristics
                #btn_repair = QPushButton("Popravi")
                #btn_repair.setFixedWidth(90)
                #btn_repair.setStyleSheet("padding:6px;")
                #btn_repair.clicked.connect(lambda _, p=ns_path: self.on_repair_clicked(p))
                #row_layout.addWidget(btn_repair)

                row_layout.addWidget(btn_add_ns)

                self.content_layout.addWidget(row_frame)

        # keep a stretch at the bottom so items stick to the top
        self.content_layout.addStretch()

        # Ako nema profila
        if not profiles:
            placeholder = QLabel("Nema profila")
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

    # ==========================
    # Create profile button
    # ==========================

    def on_create_profile_clicked(self):
        # Ask for display name
        name, ok = QInputDialog.getText(self, "Display name", "Enter display name:")
        if not ok or not name:
            return

        # Load categories from profiles/categories.txt (create defaults if missing)
        categories_path = Path(self.PROFILES_DIR) / "categories.txt"
        if not categories_path.exists():
            categories = ["General", "Marketing", "Dev"]
            categories_path.parent.mkdir(parents=True, exist_ok=True)
            categories_path.write_text("\n".join(categories), encoding="utf-8")
        else:
            categories = [line.strip() for line in categories_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not categories:
                categories = ["General"]

        category, ok = QInputDialog.getItem(self, "Category", "Choose category:", categories, editable=False)
        if not ok or not category:
            return

        process = multiprocessing.Process(
            target=create_profile,
            kwargs={"display_name": name, "namespace": "default", "category": category},
            daemon=False,
        )
        process.start()

        # Refresh profiles shortly after starting the process so new profile appears
        QTimer.singleShot(1000, self.show_profiles_page)

    def on_add_namespace_clicked(self, profile_path):
        # Ask the user for a namespace name
        ns, ok = QInputDialog.getText(self, "Namespace name", "Enter namespace name:")
        if not ok or not ns:
            return

        # Spawn worker to add namespace to the profile
        process = multiprocessing.Process(
            target=create_profile,
            kwargs={"namespace": ns, "profile_path": profile_path},
            daemon=False,
        )
        process.start()

        # Refresh profiles shortly after starting the process so new namespace appears
        QTimer.singleShot(1000, self.show_profiles_page)

    def run_profile_mp(self, profile_path):
        process = multiprocessing.Process(
            target=run_profile_process,
            args=(profile_path,),
            daemon=False
        )
        process.start()

    def on_recheck_clicked(self, namespace_path):
        # Spawn background process to re-run the consistency check for this namespace
        try:
            from BW_Controller.consistency import run_consistency_and_save
            # read namespace file to pick up any per-namespace consistency options
            try:
                ns_meta = json.load(open(namespace_path, 'r', encoding='utf-8'))
                cons_opts = ns_meta.get('consistency_options', {}) or {}
            except Exception:
                cons_opts = {}

            process = multiprocessing.Process(target=run_consistency_and_save, kwargs={'namespace_path': namespace_path, 'consistency_options': cons_opts}, daemon=True)
            process.start()
            # Refresh display shortly after starting recheck
            QTimer.singleShot(1200, self.show_profiles_page)
        except Exception as e:
            print("Could not start recheck:", e)
            QTimer.singleShot(1200, self.show_profiles_page)

    def on_repair_clicked(self, namespace_path):
        # Spawn process to normalize namespace and then run consistency
        try:
            from BW_Controller.consistency import normalize_namespace, run_consistency_and_save
            def _job(pth):
                normalize_namespace(pth)
                run_consistency_and_save(pth)
            p = multiprocessing.Process(target=_job, args=(namespace_path,), daemon=True)
            p.start()
            QTimer.singleShot(2000, self.show_profiles_page)
        except Exception as e:
            print("Could not start repair:", e)
            QTimer.singleShot(2000, self.show_profiles_page)

    def on_show_details_clicked(self, namespace_path):
        # Read namespace and show full consistency details in a dialog
        try:
            ns_meta = json.load(open(namespace_path, 'r', encoding='utf-8'))
        except Exception as e:
            QMessageBox.warning(self, "Greška", f"Ne mogu da učitam namespace: {e}")
            return

        cons = ns_meta.get('consistency')
        raw_llm = ns_meta.get('consistency', {}).get('details', {}).get('llm', {}).get('raw') or ''
        reasoning = ns_meta.get('consistency', {}).get('details', {}).get('llm', {}).get('reasoning')

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detalji: {Path(namespace_path).parent.name}")
        dlg.resize(900, 640)
        dlg_layout = QVBoxLayout(dlg)

        if not cons:
            lbl = QLabel("Nema dostupnih podataka o konzistentnosti za ovaj namespace.")
            dlg_layout.addWidget(lbl)
        else:
            # Tabs: Parsed JSON and Raw LLM output + Reasoning
            text = QTextEdit()
            text.setReadOnly(True)
            text.setPlainText(json.dumps(cons, indent=2, ensure_ascii=False))
            dlg_layout.addWidget(text)

            if raw_llm:
                raw_lbl = QLabel("Raw LLM output (may be truncated):")
                raw_lbl.setStyleSheet('font-weight:600; margin-top:8px;')
                dlg_layout.addWidget(raw_lbl)
                raw_text = QTextEdit()
                raw_text.setReadOnly(True)
                raw_text.setPlainText(raw_llm)
                raw_text.setMinimumHeight(150)
                dlg_layout.addWidget(raw_text)

            if reasoning:
                reason_lbl = QLabel("LLM reasoning:")
                reason_lbl.setStyleSheet('font-weight:600; margin-top:8px;')
                dlg_layout.addWidget(reason_lbl)
                reason_text = QTextEdit()
                reason_text.setReadOnly(True)
                reason_text.setPlainText(reasoning)
                reason_text.setMinimumHeight(120)
                dlg_layout.addWidget(reason_text)

            # Option to ignore IP-country mismatches (per-namespace)
            chk_ignore = QCheckBox("Ignore IP-country mismatch")
            # Default to True if option is not present
            chk_ignore.setChecked(bool(ns_meta.get('consistency_options', {}).get('ignore_geo_country', True)))
            dlg_layout.addWidget(chk_ignore)

            btns = QHBoxLayout()
            btn_copy = QPushButton("Kopiraj u clipboard")
            btn_copy.setFixedWidth(160)
            btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(text.toPlainText()))

            btn_save_recheck = QPushButton("Sačuvaj i Recheck")
            btn_save_recheck.setFixedWidth(180)

            def _save_and_recheck():
                try:
                    # update namespace file with the choice
                    nm = json.loads(open(namespace_path, 'r', encoding='utf-8').read())
                    nm.setdefault('consistency_options', {})['ignore_geo_country'] = bool(chk_ignore.isChecked())
                    open(namespace_path, 'w', encoding='utf-8').write(json.dumps(nm, indent=2, ensure_ascii=False))
                    # trigger recheck
                    self.on_recheck_clicked(namespace_path)
                    QMessageBox.information(self, "Saved", "Settings saved and recheck started.")
                    dlg.accept()
                except Exception as exc:
                    QMessageBox.warning(self, "Greška", f"Ne mogu sačuvati postavku: {exc}")

            btn_save_recheck.clicked.connect(_save_and_recheck)

            btn_close = QPushButton("Zatvori")
            btn_close.clicked.connect(dlg.accept)
            btns.addWidget(btn_copy)
            btns.addWidget(btn_save_recheck)
            btns.addStretch()
            btns.addWidget(btn_close)
            dlg_layout.addLayout(btns)

        dlg.exec()



def run_gui():
    app = QApplication(sys.argv)
    gui = MainGUI()
    gui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    run_gui()
