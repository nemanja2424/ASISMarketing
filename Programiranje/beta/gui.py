#gui.py
import sys
import os
import json
import multiprocessing
import zoneinfo
from datetime import datetime
from pathlib import Path
import subprocess
import threading
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
    QLineEdit,
    QPlainTextEdit,
    QComboBox,
)

from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QIcon
from BW_Controller.create_profile import create_profile
from BW_Controller.run_profile import run_profile_process


class WarmupWorker(QThread):
    """Worker thread za async warmup execution sa live output"""
    output_signal = Signal(str)
    finished_signal = Signal(bool, str)  # success, message
    
    def __init__(self, profile_ids):
        super().__init__()
        self.profile_ids = profile_ids
        self.process = None
        
    def run(self):
        try:
            cmd = [sys.executable, "instagram_warmup.py"] + self.profile_ids
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(Path.cwd())
            )
            
            # Čitaj output liniju po liniju
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.output_signal.emit(line.rstrip('\n'))
            
            # Čekaj da se proces završi
            returncode = self.process.wait()
            
            if returncode == 0:
                self.finished_signal.emit(True, f"✅ Warmup završen sa {len(self.profile_ids)} profila!")
            else:
                self.finished_signal.emit(False, f"❌ Greška pri izvršavanju warmup-a (exit code: {returncode})")
        except Exception as e:
            self.finished_signal.emit(False, f"❌ Greška: {str(e)}")


class ExecuteWorker(QThread):
    """Worker thread za async warmup batch execution"""
    output_signal = Signal(str)
    finished_signal = Signal(bool, str)
    
    def __init__(self, batch_id):
        super().__init__()
        self.batch_id = batch_id
        self.process = None
        
    def run(self):
        try:
            import os
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            cmd = [sys.executable, "instagram_execute.py", str(self.batch_id)]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(Path.cwd()),
                env=env
            )
            
            # Čitaj output liniju po liniju
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.output_signal.emit(line.rstrip('\n'))
            
            # Čekaj da se proces završi
            returncode = self.process.wait()
            
            if returncode == 0:
                self.finished_signal.emit(True, f"✅ Batch #{self.batch_id} je uspešno izvršen!")
            else:
                self.finished_signal.emit(False, f"❌ Greška pri izvršavanju batch-a (exit code: {returncode})")
        except Exception as e:
            self.finished_signal.emit(False, f"❌ Greška: {str(e)}")


class MainGUI(QWidget):
    PROFILES_DIR = "profiles"
    DEFAULT_PROXY_TEMPLATE = "http://dd6cd6b022130450c8cc__cr.rs;sessid.{id profila koji se pokrece}:3a783e2aede450db@gw.dataimpulse.com:823"
    DIALOG_STYLE = """
        QDialog {
            background-color: #1e1e1e;
        }
        QLabel {
            color: #fff;
        }
        QTextEdit {
            background-color: #2a2a2a;
            color: #aaa;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 5px;
        }
        QPushButton {
            background-color: #0d7377;
            border: none;
            border-radius: 3px;
            color: white;
            padding: 8px 15px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #14919b;
        }
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASIS Marketing Browser")
        self.resize(1800, 900)
        self.setWindowIcon(QIcon("Media/logo.png"))
        self._ensure_config()
        self.init_ui()

    def _ensure_config(self):
        """Ensure config.json exists with default proxy template"""
        config_path = Path(self.PROFILES_DIR) / "config.json"
        Path(self.PROFILES_DIR).mkdir(exist_ok=True)
        
        if not config_path.exists():
            config = {
                "proxy_template": self.DEFAULT_PROXY_TEMPLATE
            }
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

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
        btn_warmup = QPushButton("🔥 Warmup")

        btn_profiles.clicked.connect(self.show_profiles_page)
        btn_logs.clicked.connect(self.show_logs_page)
        btn_campaigns.clicked.connect(self.show_campaigns_page)
        btn_warmup.clicked.connect(self.show_warmup_page)

        sidebar_layout.addStretch()
        sidebar_layout.addWidget(btn_profiles)
        sidebar_layout.addWidget(btn_logs)
        sidebar_layout.addWidget(btn_campaigns)
        sidebar_layout.addWidget(btn_warmup)

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
                        category = data.get("metadata", {}).get("category", "Bez kategorije")
                        
                        profiles.append({
                            "profile_id": data.get("profile_id"),
                            "id": data.get("profile_id"),  # Za kompatibilnost sa campaigns
                            "display_name": display_name,
                            "category": category,
                            "path": path
                        })
                    except Exception as e:
                        print(f"Greška pri učitavanju {path}: {e}")
        return profiles

    def load_campaigns(self):
        """Učitava sve dostupne kampanje (.py fajlove) iz campaigns foldera"""
        campaigns = []
        campaigns_dir = Path("campaigns")
        if not campaigns_dir.exists():
            return campaigns

        for filename in campaigns_dir.glob("*.py"):
            # Skip __init__.py, base.py i test fajlove
            if filename.name in ["__init__.py", "base.py", "test_campaigns.py"]:
                continue
            
            try:
                # Čitaj prvi deo fajla da pronađeš docstring i klasu
                with filename.open("r", encoding="utf-8") as f:
                    content = f.read(1000)  # Čitaj samo početak
                
                # Ekstrakcija docstring-a za opis
                import re
                match = re.search(r'"""(.+?)"""', content, re.DOTALL)
                description = match.group(1).strip() if match else f"Campaign from {filename.stem}"
                description = description.split('\n')[0]  # Samo prvi red
                
                campaigns.append({
                    "name": filename.stem.replace("_", " ").title(),
                    "file": filename.stem,
                    "path": str(filename),
                    "description": description
                })
            except Exception as e:
                print(f"Greška pri učitavanju kampanje {filename}: {e}")
        
        return campaigns
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
        
        self.build_header("Dostupne Kampanje")

        # Učitaj kampanje
        campaigns = self.load_campaigns()

        if not campaigns:
            placeholder = QLabel("Nema dostupnih kampanja")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #888; font-style: italic;")
            self.content_layout.addStretch()
            self.content_layout.addWidget(placeholder)
            self.content_layout.addStretch()
        else:
            # Prikaži svaku kampanju
            for campaign in campaigns:
                campaign_frame = self.create_campaign_widget(campaign)
                self.content_layout.addWidget(campaign_frame)
            
            self.content_layout.addStretch()


    def create_campaign_widget(self, campaign):
        """Kreira widget za prikaz kampanje"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(10)

        # Naslov kampanje
        title = QLabel(campaign["name"])
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Opis kampanje
        desc = QLabel(campaign.get("description", "No description"))
        desc.setStyleSheet("color: #aaa; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Putanja do fajla
        file_label = QLabel(f"📄 {campaign['file']}.py")
        file_label.setStyleSheet("color: #888; font-size: 10px; margin-top: 5px;")
        layout.addWidget(file_label)

        # Dugmići
        buttons_layout = QHBoxLayout()

        btn_run = QPushButton("▶ Pokreni")
        btn_run.setStyleSheet("QPushButton { background-color: #0d7377; border: none; border-radius: 3px; padding: 8px 20px; color: white; font-weight: bold; } QPushButton:hover { background-color: #14919b; }")
        btn_run.clicked.connect(lambda: self.on_run_campaign(campaign))

        btn_details = QPushButton("📋 Detalji")
        btn_details.setStyleSheet("QPushButton { background-color: #3e4458; border: none; border-radius: 3px; padding: 8px 15px; } QPushButton:hover { background-color: #4a5164; }")
        btn_details.clicked.connect(lambda: self.on_campaign_details(campaign))

        buttons_layout.addWidget(btn_run)
        buttons_layout.addWidget(btn_details)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        return frame



    def on_run_campaign(self, campaign):
        """Prikazuje dijalog za izbor profila, pa tek onda pokreće kampanju"""
        self.on_select_profiles_for_campaign(campaign)

    def on_select_profiles_for_campaign(self, campaign):
        """Dijalog za izbor profila za kampanju"""
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Odaberi Profila - {campaign['name']}")
        dlg.resize(600, 500)
        dlg.setStyleSheet(self.DIALOG_STYLE)

        layout = QVBoxLayout(dlg)

        # Scroll area za profile
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)

        profiles = self.load_profiles()
        
        # Grupiraj profile po kategorijama
        categories = {}
        for profile in profiles:
            category = profile.get("category", "Bez kategorije")
            if category not in categories:
                categories[category] = []
            categories[category].append(profile)

        # Kreiraj checkbox-ove grupirane po kategorijama
        checkboxes = {}
        category_checkboxes = {}

        for category in sorted(categories.keys()):
            # Checkbox za celu kategoriju
            category_checkbox = QCheckBox(f"★ {category} (SVE)")
            category_checkbox.setStyleSheet("font-weight: bold; font-size: 12px; color: #0d7377;")
            
            content_layout.addWidget(category_checkbox)
            category_checkboxes[category] = (category_checkbox, [p["profile_id"] for p in categories[category]])

            # Profili u kategoriji
            for profile in categories[category]:
                profile_checkbox = QCheckBox(f"  {profile.get('display_name', profile['profile_id'][:8])}")
                profile_checkbox.setStyleSheet("margin-left: 20px;")
                
                checkboxes[profile["profile_id"]] = profile_checkbox
                content_layout.addWidget(profile_checkbox)

                # Callback za promenu profila
                def make_profile_callback(pprofile_id, ccategory):
                    def on_profile_toggled():
                        category_pprofiles = category_checkboxes[ccategory][1]
                        all_checked = all(checkboxes[pid].isChecked() for pid in category_pprofiles if pid in checkboxes)
                        category_checkboxes[ccategory][0].blockSignals(True)
                        category_checkboxes[ccategory][0].setChecked(all_checked)
                        category_checkboxes[ccategory][0].blockSignals(False)
                    return on_profile_toggled

                profile_checkbox.stateChanged.connect(make_profile_callback(profile["profile_id"], category))

            # Callback za kategoriju checkbox
            def make_category_callback(cat, profs):
                def on_category_toggled():
                    for pid in profs:
                        if pid in checkboxes:
                            checkboxes[pid].blockSignals(True)
                            checkboxes[pid].setChecked(category_checkboxes[cat][0].isChecked())
                            checkboxes[pid].blockSignals(False)
                return on_category_toggled

            category_checkbox.stateChanged.connect(make_category_callback(category, category_checkboxes[category][1]))

        content_layout.addStretch()
        content.setLayout(content_layout)
        scroll.setWidget(content)

        layout.addWidget(scroll)

        # Dugmice za potvrdu
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Pokreni Kampanju")
        btn_all = QPushButton("Svi Profili")
        btn_cancel = QPushButton("Otkaži")

        def run_with_selection():
            selected_profiles = [pid for pid, checkbox in checkboxes.items() if checkbox.isChecked()]
            
            if not selected_profiles:
                QMessageBox.warning(dlg, "Greška", "Moraš odabrati bar jedan profil!")
                return

            dlg.accept()
            self._run_campaign_with_profiles(campaign, selected_profiles)

        def run_all_profiles():
            all_profile_ids = [p["profile_id"] for p in profiles]
            dlg.accept()
            self._run_campaign_with_profiles(campaign, all_profile_ids)

        btn_save.clicked.connect(run_with_selection)
        btn_all.clicked.connect(run_all_profiles)
        btn_cancel.clicked.connect(dlg.reject)

        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        dlg.exec()

    def _run_campaign_with_profiles(self, campaign, profile_ids):
        """Pokreće kampanju sa odabranim profilima"""
        campaign_file = campaign['file']
        campaign_path = Path("campaigns") / f"{campaign_file}.py"
        
        if not campaign_path.exists():
            QMessageBox.critical(self, "Greška", f"Kampanja {campaign_path} nije pronađena!")
            return
        
        reply = QMessageBox.information(
            self,
            "Potvrda",
            f"Pokrenuti kampanju: {campaign['name']} sa {len(profile_ids)} profila?\n\n"
            f"Profili: {', '.join([p[:8] for p in profile_ids])}\n\n"
            f"Kampanja će se pokrenuti u novom prozoru.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        
        if reply != QMessageBox.StandardButton.Ok:
            return
        
        # Pokreni kampanju u subprocess-u sa profilima kao argumenti
        import subprocess
        try:
            # Koristi trenutni Python interpreter (iz venv-a)
            # Prosledi profile_ids kao command-line argumente
            cmd = [sys.executable, str(campaign_path)] + profile_ids
            subprocess.Popen(
                cmd,
                cwd=str(Path.cwd()),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            QMessageBox.information(self, "Uspeh", f"Kampanja '{campaign['name']}' je pokrenuta sa {len(profile_ids)} profila!")
        except Exception as e:
            QMessageBox.critical(self, "Greška", f"Nije moguće pokrenuti kampanju: {e}")

    def on_campaign_details(self, campaign):
        """Prikazuje detalje kampanje"""
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detalji: {campaign['name']}")
        dlg.resize(600, 400)
        dlg.setStyleSheet(self.DIALOG_STYLE)
        
        layout = QVBoxLayout(dlg)
        
        # Naziv
        title = QLabel(campaign["name"])
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Info
        info_text = f"""
Fajl: {campaign['file']}.py
Putanja: {campaign['path']}

Opis:
{campaign.get('description', 'N/A')}

Komande za pokretanje iz terminala:

# Pokrenuti sa svim dostupnim profilima:
python3 campaigns/{campaign['file']}.py

# Pokrenuti sa specifičnim profilima:
python3 campaigns/{campaign['file']}.py profile_e2b9eaff profile_731f08c5

# Pokrenuti sa konkretnom URL-om (ako je kampanja to podržava):
python3 campaigns/{campaign['file']}.py https://example.com
        """
        
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(info_text.strip())
        layout.addWidget(text)
        
        # OK dugme
        btn_ok = QPushButton("Zatvori")
        btn_ok.clicked.connect(dlg.accept)
        layout.addWidget(btn_ok)
        
        dlg.exec()

    def show_warmup_page(self):
        """Prikazuje stranicu za Instagram Warmup"""
        self.clear_content()
        self.build_header("Instagram Warmup 🔥")
        
        desc = QLabel("Zagrevanje profila sa humanoid ponašanjem i inter-profil komunikacijama.\n\nSistem generiše personality-je, prirodne poruke, raspored i izveštaje.")
        desc.setStyleSheet("color: #aaa; background-color: #2a2a2a; padding: 15px; border-radius: 5px;")
        desc.setWordWrap(True)
        self.content_layout.addWidget(desc)
        
        # Output log
        log_label = QLabel("📋 Live Log:")
        log_label.setStyleSheet("color: #0d7377; font-weight: bold; font-size: 12px; margin-top: 15px;")
        self.content_layout.addWidget(log_label)
        
        self.warmup_output = QPlainTextEdit()
        self.warmup_output.setReadOnly(True)
        self.warmup_output.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1a1a1a;
                color: #0d7377;
                border: 1px solid #0d7377;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        self.warmup_output.setFixedHeight(250)
        self.content_layout.addWidget(self.warmup_output)
        
        # Buttons layout
        btn_layout = QHBoxLayout()
        
        btn_run = QPushButton("▶ Pokreni Warmup Plan")
        btn_run.setFixedHeight(50)
        btn_run.setStyleSheet("QPushButton { background-color: #0d7377; color: white; font-size: 14px; font-weight: bold; border: none; border-radius: 5px; } QPushButton:hover { background-color: #14919b; }")
        btn_run.clicked.connect(self.on_run_warmup)
        btn_layout.addWidget(btn_run)
        
        btn_execute = QPushButton("🤖 Izvrši Plan (Human-like)")
        btn_execute.setFixedHeight(50)
        btn_execute.setStyleSheet("QPushButton { background-color: #d9534f; color: white; font-size: 14px; font-weight: bold; border: none; border-radius: 5px; } QPushButton:hover { background-color: #e74c3c; }")
        btn_execute.clicked.connect(self.on_execute_warmup)
        btn_layout.addWidget(btn_execute)
        
        self.content_layout.addLayout(btn_layout)
        
        self.warmup_worker = None
        self.content_layout.addStretch()
    
    def on_run_warmup(self):
        """Pokreće warmup sa odabranim profilima"""
        dlg = QDialog(self)
        dlg.setWindowTitle("Pokreni Warmup")
        dlg.resize(600, 500)
        dlg.setStyleSheet(self.DIALOG_STYLE)

        layout = QVBoxLayout(dlg)
        info = QLabel("Odaberi profile za warmup:")
        info.setWordWrap(True)
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)

        profiles = self.load_profiles()
        categories = {}
        for profile in profiles:
            category = profile.get("category", "Bez kategorije")
            if category not in categories:
                categories[category] = []
            categories[category].append(profile)

        checkboxes = {}
        category_checkboxes = {}

        for category in sorted(categories.keys()):
            cat_cb = QCheckBox(f"★ {category} (SVE)")
            cat_cb.setStyleSheet("font-weight: bold; font-size: 12px; color: #0d7377;")
            content_layout.addWidget(cat_cb)
            category_checkboxes[category] = (cat_cb, [p["profile_id"] for p in categories[category]])

            for profile in categories[category]:
                pcb = QCheckBox(f"  {profile.get('display_name', profile['profile_id'][:8])}")
                pcb.setStyleSheet("margin-left: 20px;")
                checkboxes[profile["profile_id"]] = pcb
                content_layout.addWidget(pcb)

        content_layout.addStretch()
        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_run = QPushButton("Pokreni Warmup")
        btn_all = QPushButton("Svi Profili")
        btn_cancel = QPushButton("Otkaži")

        def run_with_selection():
            selected = [pid for pid, cb in checkboxes.items() if cb.isChecked()]
            if not selected:
                QMessageBox.warning(dlg, "Greška", "Odaberi bar jedan profil!")
                return
            dlg.accept()
            self._run_warmup_with_profiles(selected)

        def run_all():
            dlg.accept()
            self._run_warmup_with_profiles([p["profile_id"] for p in profiles])

        btn_run.clicked.connect(run_with_selection)
        btn_all.clicked.connect(run_all)
        btn_cancel.clicked.connect(dlg.reject)

        btn_layout.addWidget(btn_run)
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        dlg.exec()
    
    def _run_warmup_with_profiles(self, profile_ids):
        """Pokreće warmup sa odabranim profilima u async thread-u"""
        # Očisti prethodni log
        self.warmup_output.clear()
        self.warmup_output.appendPlainText("⏳ Pokretanje warmup-a...\n")
        
        # Kreiraj i pokreni worker thread
        self.warmup_worker = WarmupWorker(profile_ids)
        self.warmup_worker.output_signal.connect(self._on_warmup_output)
        self.warmup_worker.finished_signal.connect(self._on_warmup_finished)
        self.warmup_worker.start()
    
    def _on_warmup_output(self, line):
        """Prikaži output liniju u log widget-u"""
        self.warmup_output.appendPlainText(line)
        # Auto scroll to bottom
        self.warmup_output.verticalScrollBar().setValue(
            self.warmup_output.verticalScrollBar().maximum()
        )
    
    def _on_warmup_finished(self, success, message):
        """Pozvan kada se warmup završi"""
        self.warmup_output.appendPlainText("\n" + "="*50)
        self.warmup_output.appendPlainText(message)
        self.warmup_output.appendPlainText("="*50)
        
        if success:
            self.warmup_output.appendPlainText("\n✨ Izveštaji su dostupni u warmup/reports/ direktorijumu")
        
        # Auto scroll to bottom
        self.warmup_output.verticalScrollBar().setValue(
            self.warmup_output.verticalScrollBar().maximum()
        )
    
    def on_execute_warmup(self):
        """Pokreće izvršavanje warmup plana na human-like način"""
        dlg = QDialog(self)
        dlg.setWindowTitle("Izvrši Warmup Plan")
        dlg.resize(500, 400)
        dlg.setStyleSheet(self.DIALOG_STYLE)

        layout = QVBoxLayout(dlg)
        info = QLabel("Odaberi warmup batch koji želiš da izvrišš:")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Učitaj sve batch-eve iz baze
        from warmup import WarmupDatabase
        db = WarmupDatabase()
        cursor = db.connection.cursor()
        cursor.execute("""
            SELECT id, batch_name, status, total_duration_minutes
            FROM warmup_batches 
            ORDER BY id DESC 
            LIMIT 10
        """)
        batches = cursor.fetchall()
        
        if not batches:
            QMessageBox.warning(dlg, "Nema Batch-eva", "Nema dostupnih warmup batch-eva!")
            return
        
        # Combo box za izbor
        combo = QComboBox()
        combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #fff;
                border: 1px solid #0d7377;
                padding: 5px;
            }
        """)
        
        for batch_id, batch_name, status, duration in batches:
            combo.addItem(
                f"Batch #{batch_id}: {batch_name} ({status}) - {duration}min",
                batch_id
            )
        
        layout.addWidget(combo)
        
        info2 = QLabel("⚠️ Ovo će otvoriti profile u browser-u i simulirati human-like ponašanje.")
        info2.setStyleSheet("color: #ff6b6b; font-size: 11px;")
        info2.setWordWrap(True)
        layout.addWidget(info2)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_execute = QPushButton("🤖 Pokreni Execution")
        btn_cancel = QPushButton("Otkaži")

        def execute():
            batch_id = combo.currentData()
            dlg.accept()
            self._execute_warmup_batch(batch_id)

        btn_execute.clicked.connect(execute)
        btn_cancel.clicked.connect(dlg.reject)

        btn_layout.addWidget(btn_execute)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        dlg.exec()
    
    def _execute_warmup_batch(self, batch_id):
        """Pokreće execution warmup batch-a u posebnom thread-u"""
        self.warmup_output.clear()
        self.warmup_output.appendPlainText(f"🤖 Pokretanje izvršavanja Batch #{batch_id}...\n")
        
        # Kreiraj worker thread
        self.execute_worker = ExecuteWorker(batch_id)
        self.execute_worker.output_signal.connect(self._on_execute_output)
        self.execute_worker.finished_signal.connect(self._on_execute_finished)
        self.execute_worker.start()
    
    def _on_execute_output(self, line):
        """Prikaži output iz execution-a"""
        self.warmup_output.appendPlainText(line)
        self.warmup_output.verticalScrollBar().setValue(
            self.warmup_output.verticalScrollBar().maximum()
        )
    
    def _on_execute_finished(self, success, message):
        """Pozvan kada se execution završi"""
        self.warmup_output.appendPlainText("\n" + "="*60)
        self.warmup_output.appendPlainText(message)
        self.warmup_output.appendPlainText("="*60)
        
        if success:
            self.warmup_output.appendPlainText("\n✅ Batch je uspešno izvršen!")
            self.warmup_output.appendPlainText("📊 Proverite izveštaje u warmup/reports/")
        else:
            self.warmup_output.appendPlainText("\n❌ Došlo je do greške pri izvršavanju.")
        
        self.warmup_output.verticalScrollBar().setValue(
            self.warmup_output.verticalScrollBar().maximum()
        )






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

        # Load default proxy template from config
        config_path = Path(self.PROFILES_DIR) / "config.json"
        proxy_template = None
        if config_path.exists():
            try:
                config = json.load(config_path.open("r", encoding="utf-8"))
                proxy_template = config.get("proxy_template")
            except Exception:
                pass

        process = multiprocessing.Process(
            target=create_profile,
            kwargs={
                "display_name": name,
                "namespace": "default",
                "category": category,
                "proxy_template": proxy_template,
            },
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

            # Privacy toggles
            chk_block_webrtc = QCheckBox("Block WebRTC (prevent STUN/ICE IP leaks)")
            chk_block_webrtc.setChecked(bool(ns_meta.get('privacy', {}).get('block_webrtc', True)))
            dlg_layout.addWidget(chk_block_webrtc)

            chk_disable_ipv6 = QCheckBox("Disable IPv6 for browser (network.dns.disableIPv6)")
            chk_disable_ipv6.setChecked(bool(ns_meta.get('privacy', {}).get('disable_ipv6', True)))
            dlg_layout.addWidget(chk_disable_ipv6)

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
                    nm.setdefault('privacy', {})['block_webrtc'] = bool(chk_block_webrtc.isChecked())
                    nm.setdefault('privacy', {})['disable_ipv6'] = bool(chk_disable_ipv6.isChecked())
                    open(namespace_path, 'w', encoding='utf-8').write(json.dumps(nm, indent=2, ensure_ascii=False))
                    # trigger recheck (re-normalize and run consistency checks)
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
