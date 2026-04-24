import sys
import os
import json
import traceback as tb
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                             QHBoxLayout, QMessageBox, QFileDialog, QProgressDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

APP_VERSION = "1.3.3"
APP_NAME = "Droplet Printing Interface (DPI)"
APP_ID = f"cz.vut.droplet_printer.{APP_VERSION}" # Jedinečné ID aplikace pro Windows Taskbar

if sys.platform.startswith("win"):
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception as e:
        print("Failed to set AppUserModelID:", e)

from gui.settings import load_settings
from gui.menu_bar import create_main_menu
from gui.left_panel import LeftPanel
from gui.graphics_view import InteractiveGraphicsView
from gui.right_panel import RightPanel
from core.logic import GCodeLogic, get_layout_positions
from core.vector_slicer import NeedsScalingError
from core.csv_exporter import export_protocol_csv
from core.updater import AutoUpdater

class GCodeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 800)
        
        # Nastavení ikony okna
        icon_path = os.path.join(os.getcwd(), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.user_scales = {} 
        self.loaded_transforms = None

        self.logic = GCodeLogic()
        self.menu_actions = create_main_menu(self)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        self.left_panel = LeftPanel()
        main_layout.addWidget(self.left_panel, stretch=1)

        self.graphics_view = InteractiveGraphicsView()
        main_layout.addWidget(self.graphics_view, stretch=4)

        self.right_panel = RightPanel(self)
        main_layout.addWidget(self.right_panel, stretch=1)

        self.left_panel.btn_start_print.clicked.connect(self.start_print)
        self.left_panel.btn_load.clicked.connect(self.load_file)
        self.left_panel.btn_save.clicked.connect(self.save_file)
        self.left_panel.btn_csv.clicked.connect(self.export_csv)
        self.left_panel.worker.pos_changed.connect(self.graphics_view.update_nozzle_position)
        self.left_panel.worker.pos_changed.connect(self._update_manual_pos)
        
        # Propojení stavu tiskárny s menu
        self.left_panel.worker.status_changed.connect(self._update_menu_status)

        self.left_panel.values_changed.connect(self.update_preview)
        self.right_panel.values_changed.connect(self.update_preview) 
        
        # --- Inicializace Updateru ---
        self._init_updater()

    def _init_updater(self):
        # Pokus o získání tokenu z .git/config (pro interní/vývojové účely)
        github_token = None
        git_config_path = os.path.join(os.getcwd(), ".git", "config")
        if os.path.exists(git_config_path):
            try:
                with open(git_config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    import re
                    # Hledáme token ve formátu https://user:token@github.com...
                    match = re.search(r"https://[^:]+:([^@]+)@github\.com", content)
                    if match:
                        github_token = match.group(1)
            except Exception: pass

        self.updater = AutoUpdater(APP_VERSION, repo_owner="Sherlock3721", repo_name="2D-liquid-printing", github_token=github_token)
        self.updater.update_available.connect(self.on_update_available)
        self.updater.update_ready.connect(self.on_update_ready)
        self.updater.error.connect(lambda msg: print(f"Updater info: {msg}"))
        
        if getattr(sys, 'frozen', False):
            self.updater.check_for_updates()
            
        self.showMaximized()

    def check_updates_manually(self):
        # Pro debugging povolíme kontrolu i mimo frozen, ale s varováním
        if not getattr(sys, 'frozen', False):
            res = QMessageBox.question(
                self, "Vývojářský režim",
                "Spouštíte aplikaci ze zdrojových kódů. Aktualizace by mohla přepsat vaše soubory. Chcete přesto pokračovat v kontrole?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.No: return
            
        self.updater.error.disconnect()
        self.updater.error.connect(lambda msg: QMessageBox.warning(self, "Aktualizace", msg))
        self.updater.check_for_updates()
        
    def on_update_available(self, version, url):
        odpoved = QMessageBox.question(
            self, "Nová aktualizace k dispozici",
            f"Byla nalezena nová verze aplikace: <b>{version}</b><br>Chcete ji nyní stáhnout a nainstalovat?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if odpoved == QMessageBox.StandardButton.Yes:
            self.progress_dialog = QProgressDialog("Stahuji aktualizaci...", "Zrušit", 0, 100, self)
            self.progress_dialog.setWindowTitle("Aktualizace")
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setAutoClose(True)
            
            self.updater.progress.connect(self.progress_dialog.setValue)
            self.progress_dialog.canceled.connect(self.updater.terminate)
            
            self.updater.download_and_prepare(url)
            self.progress_dialog.show()

    def on_update_ready(self, script_path):
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
            
        QMessageBox.information(self, "Aktualizace připravena", "Aplikace se nyní ukončí a bude aktualizována. Proces zabere několik sekund.")
        
        import subprocess
        try:
            if sys.platform.startswith("win"):
                # shell=True je nutné pro spuštění .bat souboru
                subprocess.Popen([script_path], shell=True, creationflags=0x00000008)
            else:
                subprocess.Popen([script_path])
        except Exception as e:
            print("Chyba spuštění aktualizátoru:", e)
            
        QApplication.quit()

    def _update_manual_pos(self, x, y, z, is_extruding):
        if hasattr(self, 'right_panel') and hasattr(self.right_panel, 'manual_widget'):
            self.right_panel.manual_widget.update_coords(x, y, z)

    def _update_menu_status(self, status):
        # Pro debugging necháváme manual control vždy povolený
        if hasattr(self, 'menu_actions') and 'manual' in self.menu_actions:
            self.menu_actions['manual'].setEnabled(True)

    def open_manual_control(self):
        if hasattr(self, 'right_panel'):
            self.right_panel.manual_box.toggle_button.setChecked(True)
            self.right_panel.manual_box.on_pressed()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_preview()

    def load_file(self):
        default_dir = os.path.join(os.getcwd(), "gcodes")
        if not os.path.exists(default_dir): os.makedirs(default_dir)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Otevřít vzorek", default_dir, 
            "Podporované soubory (*.gcode *.svg *.dxf);;G-code (*.gcode);;Vektory (*.svg *.dxf)"
        )
        
        if file_path:
            self.user_scales = {} 
            metadata = self._extract_metadata(file_path)
            
            target_file = file_path
            # Inteligentní načtení původního zdrojového souboru, pokud existuje
            if metadata and 'original_source_file' in metadata:
                orig_file = metadata['original_source_file']
                if os.path.exists(orig_file):
                    target_file = orig_file
                else:
                    QMessageBox.warning(self, "Chybějící zdroj", 
                                        f"Tento G-code byl vygenerován ze souboru:\n{orig_file}\n\n"
                                        "Tento zdrojový soubor již neexistuje. Vzorek se načte jako čistá trasa, "
                                        "což způsobí, že uvidíte již jednou rozkopírované objekty.")
            
            self._zpracovat_soubor(target_file, auto_scale=False, metadata=metadata)
            
    def _extract_metadata(self, file_path):
        if not file_path.lower().endswith('.gcode'):
            return None
        try:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = []
                    for _ in range(30): # Kontroluje jen hlavičku
                        line = f.readline()
                        if not line: break
                        content.append(line)
                        if "; --- END METADATA ---" in line:
                            break
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='cp1250') as f:
                    content = []
                    for _ in range(30):
                        line = f.readline()
                        if not line: break
                        content.append(line)
                        if "; --- END METADATA ---" in line:
                            break
                        
            header_text = "".join(content)
            import re
            match = re.search(r'; --- EDITOR METADATA ---\n; (\{.*?\})\n; --- END METADATA ---', header_text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except Exception as e:
            print("Chyba čtení metadat:", e)
        return None

    def _apply_metadata_to_ui(self, metadata):
        lp = self.left_panel
        lp.blockSignals(True) # Zabráníme smršti událostí při nastavování GUI
        
        if 'glass_type' in metadata: lp.cmb_glass.setCurrentText(metadata['glass_type'])
        if metadata.get('glass_type') == 'Vlastní':
            if 'slide_w' in metadata: lp.inp_glass_x.setText(str(metadata['slide_w']))
            if 'slide_h' in metadata: lp.inp_glass_y.setText(str(metadata['slide_h']))
            if 'slide_z' in metadata: lp.inp_glass_z.setText(str(metadata['slide_z']))
            
        if 'sample_count' in metadata: lp.inp_count.setValue(metadata['sample_count'])
        if 'bed_temp' in metadata: lp.inp_bed_temp.setValue(metadata['bed_temp'])
        if 'z_offset' in metadata: lp.inp_z_offset.setValue(metadata['z_offset'])
        if 'extrusion_rate' in metadata: lp.inp_extrusion.setValue(metadata['extrusion_rate'])
        
        # Trysky: Pokud máme typ, nastavíme ho, jinak zkusíme průměr do 'Vlastní'
        if 'nozzle_type' in metadata:
            lp.cmb_nozzle.setCurrentText(metadata['nozzle_type'])
        elif 'nozzle_diam' in metadata:
            lp.cmb_nozzle.setCurrentText('Vlastní')
            lp.inp_nozzle_d.setValue(metadata['nozzle_diam'])
            if 'nozzle_height' in metadata:
                lp.inp_nozzle_h.setValue(metadata['nozzle_height'])
        
        if 'infill_style' in metadata: lp.cmb_infill_style.setCurrentText(metadata['infill_style'])
        if 'infill_val' in metadata: lp.inp_infill_val.setValue(metadata['infill_val'])
        if 'infill_type' in metadata: lp.cmb_infill_type.setCurrentText(metadata['infill_type'])
        if 'infill_angle' in metadata: lp.inp_infill_angle.setValue(metadata.get('infill_angle', 0))

        lp.blockSignals(False)
        lp._toggle_custom_glass()

    def _apply_metadata_to_overrides_and_transforms(self, metadata):
        # 1. Transformace plátna
        self.loaded_transforms = metadata.get('transforms', [])
        
        # OPRAVA: Obnova skutečného zapečeného měřítka
        self.user_scales.clear()
        for i, t in enumerate(self.loaded_transforms):
            self.user_scales[i] = t.get('user_scale', t.get('scale', 1.0))
                
        # 2. Lokální parametry pravého panelu
        overrides = metadata.get('slide_overrides', {})
        count = metadata.get('sample_count', 1)
        
        self.right_panel.blockSignals(True)
        self.right_panel.update_slides(count, self.left_panel.get_all_params())
        
        for i_str, slide_data in overrides.items():
            i = int(i_str)
            if i in self.right_panel.slide_widgets:
                w = self.right_panel.slide_widgets[i]
                if 'name' in slide_data: w['name'].setText(slide_data['name'])
                if 'note' in slide_data: w['note'].setText(slide_data['note'])
                if 'z_offset' in slide_data: 
                    w['z_offset'].setValue(slide_data['z_offset'])
                    self.right_panel.local_modifications[i]['z_offset'] = True
                if 'extrusion_rate' in slide_data: 
                    w['extrusion_rate'].setValue(slide_data['extrusion_rate'])
                    self.right_panel.local_modifications[i]['extrusion_rate'] = True
                if 'print_speed' in slide_data: 
                    w['print_speed'].setValue(slide_data['print_speed'])
                    self.right_panel.local_modifications[i]['print_speed'] = True
                if 'infill_val' in slide_data: 
                    w['infill_val'].setValue(slide_data['infill_val'])
                    self.right_panel.local_modifications[i]['infill_val'] = True
                if 'infill_type' in slide_data: 
                    w['infill_type'].setCurrentText(slide_data['infill_type'])
                    self.right_panel.local_modifications[i]['infill_type'] = True
                    
        self.right_panel.blockSignals(False)


    def save_file(self):
        if not getattr(self.logic, 'filepath', None):
            QMessageBox.warning(self, "Upozornění", "Nejprve načtěte vzorek!")
            return
            
        params = self.left_panel.get_all_params()
        transforms = self.graphics_view.get_transforms()
        
        # OPRAVA: Obohacení transformací o skutečné matematické měřítko
        for i in range(len(transforms)):
            transforms[i]['user_scale'] = self.user_scales.get(i, 1.0)
            
        params['transforms'] = transforms
        params['slide_overrides'] = self.right_panel.get_overrides() 
        params['original_source_file'] = self.logic.filepath # Uložení cesty k surovému originálu
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportovat G-code", "", "G-code soubory (*.gcode)")
        if file_path:
            if not file_path.lower().endswith('.gcode'): file_path += '.gcode'
            metadata_str = json.dumps(params)
            header = f"; --- EDITOR METADATA ---\n; {metadata_str}\n; --- END METADATA ---\n\n"
            
            try:
                gcode_text, _, _ = self.logic.generate_gcode(params)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(header + gcode_text)
                QMessageBox.information(self, "Uloženo", f"Soubor uložen do:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Chyba při ukládání", str(e))

    def _zpracovat_soubor(self, file_path, auto_scale=False, metadata=None):
        try:
            if metadata:
                self._apply_metadata_to_ui(metadata)

            vector_params = self.left_panel.get_vector_params()
            self.logic.load_file(file_path, vector_params=vector_params, auto_scale=auto_scale)
            
            if metadata:
                self._apply_metadata_to_overrides_and_transforms(metadata)

            self.first_load_pending = True
            self.update_preview()
        except NeedsScalingError as e:
            odpoved = QMessageBox.question(
                self,
                "Příliš velký vzorek",
                f"Tvar ({e.w:.1f} x {e.h:.1f} mm) je větší než fyzické sklíčko.\n"
                f"Maximální povolený prostor je {e.max_w:.1f} x {e.max_h:.1f} mm.\n\n"
                "Chcete vzorek automaticky zmenšit, aby se vešel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if odpoved == QMessageBox.StandardButton.Yes:
                self._zpracovat_soubor(file_path, auto_scale=True, metadata=metadata)
        except Exception as e:
            QMessageBox.critical(self, "Chyba načítání", str(e))
            
    def export_csv(self):
        params = self.left_panel.get_all_params()
        params['slide_overrides'] = self.right_panel.get_overrides()
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportovat CSV protokol", "", "CSV soubory (*.csv)")
        if file_path:
            if not file_path.lower().endswith('.csv'): file_path += '.csv'
            try:
                export_protocol_csv(file_path, params)
                QMessageBox.information(self, "Uloženo", f"Protokol uložen do:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Chyba", str(e))

    def update_preview(self):
        if not hasattr(self, 'graphics_view'): return
        
        settings = load_settings()
        bed_x = settings["bed_max_x"]
        bed_y = settings["bed_max_y"]
        spacing = settings["multi_spacing"]

        params = self.left_panel.get_all_params()
        slide_w = params.get('slide_w', 25.0)
        slide_h = params.get('slide_h', 75.0)
        count = params.get('sample_count', 1)
        holder_type = "Multiplex (více sklíček)"

        self.right_panel.update_slides(count, params)
        slide_overrides = self.right_panel.get_overrides()
        params['slide_overrides'] = slide_overrides
        prime_active = params.get('prime_active', True)

        if getattr(self.logic, 'is_vector', False) and getattr(self.logic, 'filepath', None):
            vector_params = self.left_panel.get_vector_params()
            try:
                self.logic.load_file(
                    self.logic.filepath, 
                    vector_params=vector_params, 
                    auto_scale=True,
                    user_scales=self.user_scales,
                    sample_count=count,
                    slide_overrides=slide_overrides
                )
            except Exception:
                pass
                
        positions = get_layout_positions(count, slide_w, slide_h, spacing, holder_type, bed_x, bed_y, prime_active=prime_active)
        
        # PŘEDÁVÁME NAČTENÉ TRANSFORMACE A PŘÍZNAK PRVNÍHO NAČTENÍ
        loaded_t = getattr(self, 'loaded_transforms', None)
        first_load = getattr(self, 'first_load_pending', False)
        
        self.graphics_view.redraw_scene(
            self.logic, params, (slide_w, slide_h), positions, bed_x, bed_y, 
            loaded_transforms=loaded_t, 
            first_load=first_load
        )
        
        self.loaded_transforms = None 
        self.first_load_pending = False # Resetujeme po prvním úspěšném překreslení

    def apply_visual_scale(self, updates):
        if not getattr(self.logic, 'is_vector', False): return
        
        for index, visual_scale in updates:
            self.user_scales[index] = self.user_scales.get(index, 1.0) * visual_scale
            
        if hasattr(self.graphics_view, 'gcode_items'):
            for item in self.graphics_view.gcode_items:
                item.setScale(1.0)
        self.update_preview()
        
    def start_print(self):
        if not getattr(self.logic, 'filepath', None):
            QMessageBox.warning(self, "Upozornění", "Nejprve načtěte vzorek!")
            return

        params = self.left_panel.get_all_params()
        params['transforms'] = self.graphics_view.get_transforms()
        params['slide_overrides'] = self.right_panel.get_overrides()

        temp_file = os.path.join(os.getcwd(), "temp_print.gcode")
        try:
            gcode_text, total_dist, total_time = self.logic.generate_gcode(params)
            
            # FILTRACE BED LEVELINGU (pouze pro přímý tisk)
            if not params.get('bed_leveling', True):
                import re
                # Odstraníme pouze příkaz G80 (Mesh Bed Leveling), pokud existuje.
                # Ponecháme M1 (zprávy pro PINDA) i G28 (Homing).
                gcode_text = re.sub(r'^G80\b.*?\n', '; --- G80 (BED LEVELING) SKIPNUT ---\n', gcode_text, flags=re.MULTILINE | re.IGNORECASE)

            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(gcode_text)
                
            self.left_panel.worker.print_file(temp_file, total_dist=total_dist, total_time=total_time)
            
            # OPRAVA: Voláme pouze naši novou metodu, která se postará o UI
            self.left_panel.set_ui_printing()
            
        except Exception as e:
            QMessageBox.critical(self, "Chyba tisku", str(e))

def global_exception_hook(exctype, value, traceback):
    """Globální zachytávání chyb pro automatické hlášení."""
    error_msg = "".join(tb.format_exception(exctype, value, traceback))
    print("FATAL ERROR:", error_msg)
    
    # Zkusíme otevřít feedback dialog, pokud existuje instance QApplication
    app = QApplication.instance()
    if app:
        try:
            # Vytvoříme zprávu pro Matrix
            formatted_message = f"[AUTO-BUG-REPORT]\nVerze: {APP_VERSION}\nOS: {sys.platform}\n\n{error_msg}"
            
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Neočekávaná chyba")
            msg_box.setText("V aplikaci došlo k neočekávané chybě.")
            msg_box.setInformativeText("Chcete odeslat hlášení o chybě vývojářům?")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
            
            if msg_box.exec() == QMessageBox.StandardButton.Yes:
                from gui.feedback_dialog import MatrixSenderThread
                # Spustíme odesílání na pozadí
                sender = MatrixSenderThread(formatted_message)
                # Musíme udržet referenci, aby se vlákno neukončilo předčasně
                if not hasattr(app, '_error_senders'): app._error_senders = []
                app._error_senders.append(sender)
                sender.finished.connect(lambda s, m: print(f"Auto-report sent: {s}, {m}"))
                sender.start()
                QMessageBox.information(None, "Odesláno", "Hlášení bylo odesláno. Děkujeme.")
        except Exception as e:
            print("Chyba při pokusu o auto-report:", e)
            
    # Původní chování (vypis na stderr)
    sys.__excepthook__(exctype, value, traceback)
            
if __name__ == "__main__":
    sys.excepthook = global_exception_hook
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    
    # Nastavení globální ikony aplikace
    icon_path = os.path.join(os.getcwd(), "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    app.setStyleSheet("""
        QWidget { background-color: #2b2b2b; color: #e0e0e0; font-family: 'FiraSans', sans-serif; font-size: 10pt; }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #3c3c3c; border: 1px solid #555; padding: 5px; border-radius: 4px;
        }
        QLineEdit:focus, QComboBox:focus { border: 1px solid #0d6efd; }
        QPushButton {
            background-color: #0d6efd; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold;
        }
        QPushButton:hover { background-color: #0b5ed7; }
        QDockWidget { border: 1px solid #444; }
        QDockWidget::title { background: #1e1e1e; padding: 8px; text-align: center; }
        QGroupBox { border: 1px solid #555; border-radius: 5px; margin-top: 1ex; padding-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; color: #aaa; }
        QMenuBar { background-color: #1e1e1e; padding: 2px; }
        QMenuBar::item:selected { background-color: #3c3c3c; border-radius: 4px; }
        QMenu { background-color: #2b2b2b; border: 1px solid #444; }
        QMenu::item:selected { background-color: #0d6efd; }
    """)
    window = GCodeApp()
    window.show()
    sys.exit(app.exec())

