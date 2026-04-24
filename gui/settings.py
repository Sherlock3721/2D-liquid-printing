import json
import os
import sys
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, 
                             QFormLayout, QTextEdit, QPushButton, QHBoxLayout, 
                             QDoubleSpinBox, QSpinBox, QLabel, QMessageBox,
                             QCheckBox, QScrollArea, QFrame, QLineEdit)
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

def get_resource_path(relative_path):
    """Získá absolutní cestu k prostředku, funguje pro vývoj i PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
    SETTINGS_FILE = os.path.join(app_dir, "settings.json")
else:
    SETTINGS_FILE = os.path.join(os.getcwd(), "settings.json")

DEFAULT_SETTINGS_FILE = get_resource_path("settings_default.json")

def load_settings():
    """Načte nastavení ze souborů s prioritou na uživatelské hodnoty."""
    defaults = {}
    if os.path.exists(DEFAULT_SETTINGS_FILE):
        try:
            with open(DEFAULT_SETTINGS_FILE, "r", encoding="utf-8") as f:
                defaults = json.load(f)
        except Exception as e:
            print(f"Chyba při čtení default nastavení: {e}")

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                user_settings = json.load(f)
                for key, value in defaults.items():
                    if key not in user_settings:
                        user_settings[key] = value
                return user_settings
        except json.JSONDecodeError: pass
    return defaults

def save_settings(settings_data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings_data, f, indent=4)

def restore_default_settings():
    if os.path.exists(DEFAULT_SETTINGS_FILE):
        shutil.copy(DEFAULT_SETTINGS_FILE, SETTINGS_FILE)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pokročilé nastavení aplikace")
        self.resize(1000, 750)
        self.settings = load_settings()

        self.slide_rows = []

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # --- ZÁLOŽKA 1: Extruze & Trysky ---
        tab_extruze = QWidget()
        lay_extruze_main = QHBoxLayout(tab_extruze)
        
        # Levá část: Parametry (z GitHubu)
        tab_ext_left = QWidget()
        lay_extruze = QVBoxLayout(tab_ext_left)
        lay_extruze.setContentsMargins(0, 0, 0, 0)
        
        lay_extruze.addWidget(QLabel("<b>Definice trysek:</b>"))
        
        # Hlavička tabulky trysek
        nozzle_header = QWidget()
        nozzle_header_lay = QHBoxLayout(nozzle_header)
        nozzle_header_lay.setContentsMargins(0, 0, 0, 0)
        nozzle_header_lay.setSpacing(5)
        h_n_name = QLabel("Název trysky"); h_n_name.setStyleSheet("font-weight: bold; font-size: 13px;"); h_n_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_n_h = QLabel("Výška [mm]"); h_n_h.setStyleSheet("font-weight: bold; font-size: 13px;"); h_n_h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_n_d = QLabel("Průměr [mm]"); h_n_d.setStyleSheet("font-weight: bold; font-size: 13px;"); h_n_d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_n_s = QLabel("Skrytá d. [mm]"); h_n_s.setStyleSheet("font-weight: bold; font-size: 13px;"); h_n_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        h_n_del = QWidget(); h_n_del.setFixedWidth(30)
        
        nozzle_header_lay.addWidget(h_n_name, 3)
        nozzle_header_lay.addWidget(h_n_h, 2)
        nozzle_header_lay.addWidget(h_n_d, 2)
        nozzle_header_lay.addWidget(h_n_s, 2)
        nozzle_header_lay.addWidget(h_n_del, 0)
        lay_extruze.addWidget(nozzle_header)

        self.nozzle_list_layout = QVBoxLayout()
        self.nozzle_list_layout.setSpacing(0) # Minimální rozestup (gap) jako u sklíček
        self.nozzle_rows = []
        
        nozzle_scroll = QScrollArea()
        nozzle_scroll.setWidgetResizable(True)
        nozzle_scroll_widget = QWidget()
        nozzle_scroll_widget.setLayout(self.nozzle_list_layout)
        nozzle_scroll.setWidget(nozzle_scroll_widget)
        nozzle_scroll.setFixedHeight(130)
        lay_extruze.addWidget(nozzle_scroll)
        
        btn_add_nozzle = QPushButton("+ Přidat novou trysku")
        btn_add_nozzle.clicked.connect(lambda checked: self.add_nozzle_row())
        lay_extruze.addWidget(btn_add_nozzle)
        
        # Načtení stávajících trysek
        nozzle_defs = self.settings.get("nozzle_defs", {})
        for name, params in nozzle_defs.items():
            h = params[0]
            d = params[1]
            s = params[2] if len(params) > 2 else self.settings.get("hidden_nozzle_part", 4.0)
            self.add_nozzle_row(name, h, d, s)
        
        lay_extruze.addWidget(QLabel("<br><b>Globální parametry extruze:</b>"))
        ext_form = QFormLayout()
        self.inp_speed = QSpinBox(); self.inp_speed.setRange(10, 10000); self.inp_speed.setSingleStep(100); self.inp_speed.setSuffix(" mm/min")
        self.inp_speed.setValue(self.settings.get("print_speed", 1500))
        self.inp_retract = QDoubleSpinBox(); self.inp_retract.setRange(0.0, 50.0); self.inp_retract.setSingleStep(0.1); self.inp_retract.setSuffix(" mm")
        self.inp_retract.setValue(self.settings.get("retraction", 1.0))
        
        self.inp_filament_d = QDoubleSpinBox(); self.inp_filament_d.setRange(0.1, 50.0); self.inp_filament_d.setSingleStep(0.01); self.inp_filament_d.setSuffix(" mm")
        self.inp_filament_d.setValue(self.settings.get("filament_diameter", 9.5))
        self.inp_filament_d.valueChanged.connect(lambda: self._sync_schema_to_profile())
        
        self.inp_flow_mult = QDoubleSpinBox(); self.inp_flow_mult.setRange(0.1, 10.0); self.inp_flow_mult.setSingleStep(0.05)
        self.inp_flow_mult.setValue(self.settings.get("flow_multiplier", 1.0))

        self.inp_block_height = QDoubleSpinBox(); self.inp_block_height.setRange(0.0, 500.0); self.inp_block_height.setSingleStep(0.1); self.inp_block_height.setDecimals(2); self.inp_block_height.setSuffix(" mm")
        self.inp_block_height.setValue(self.settings.get("block_height", 34.0))
        self.inp_block_height.valueChanged.connect(lambda: self._sync_schema_to_profile())

        ext_form.addRow("Rychlost tisku:", self.inp_speed); ext_form.addRow("Retrakce:", self.inp_retract)
        ext_form.addRow("Vnitřní průměr stříkačky:", self.inp_filament_d); ext_form.addRow("Flow multiplikátor:", self.inp_flow_mult)
        ext_form.addRow("Výška bloku od podložky:", self.inp_block_height)
        lay_extruze.addLayout(ext_form)
        lay_extruze.addStretch()
        
        lay_extruze_main.addWidget(tab_ext_left, stretch=7)
        
        # Pravá část: Vizuální schéma
        schema_container = QWidget()
        schema_container_lay = QVBoxLayout(schema_container)
        schema_container_lay.setContentsMargins(0, 0, 0, 0)
        schema_container_lay.setSpacing(10)
        
        from gui.vizualizace import InteractiveSvgSchema
        schema_path = get_resource_path("svg/Schéma.svg")
        self.view_schema = InteractiveSvgSchema(schema_path, self)
        # Nový způsob ovládání: kliknutí otevře výběr profilu (pokud je relevantní)
        self.view_schema.groupClicked.connect(self.handle_schema_click)
        # valueUpdated ponecháme pro globální parametry, které nevyžadují výběr profilu
        self.view_schema.valueUpdated.connect(self.update_from_schema)
        
        schema_container_lay.addWidget(self.view_schema)
        schema_container_lay.addStretch()
        
        lay_extruze_main.addWidget(schema_container, stretch=3)
        tabs.addTab(tab_extruze, "Extruze")

        # --- ZÁLOŽKA 2: Podložka & Sklíčka ---
        tab_hw = QWidget()
        lay_hw = QVBoxLayout(tab_hw)
        
        lay_hw.addWidget(QLabel("<b>Definice sklíček:</b>"))
        
        # Hlavička tabulky sklíček
        slide_header = QWidget()
        slide_header_lay = QHBoxLayout(slide_header)
        slide_header_lay.setContentsMargins(0, 0, 0, 0)
        slide_header_lay.setSpacing(5)
        h_s_name = QLabel("Název sklíčka"); h_s_name.setStyleSheet("font-weight: bold; font-size: 13px;"); h_s_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_s_w = QLabel("Šířka (X) [mm]"); h_s_w.setStyleSheet("font-weight: bold; font-size: 13px;"); h_s_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_s_h = QLabel("Výška (Y) [mm]"); h_s_h.setStyleSheet("font-weight: bold; font-size: 13px;"); h_s_h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_s_z = QLabel("Tloušťka [mm]"); h_s_z.setStyleSheet("font-weight: bold; font-size: 13px;"); h_s_z.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        h_s_del = QWidget(); h_s_del.setFixedWidth(30)
        
        slide_header_lay.addWidget(h_s_name, 3)
        slide_header_lay.addWidget(h_s_w, 2)
        slide_header_lay.addWidget(h_s_h, 2)
        slide_header_lay.addWidget(h_s_z, 2)
        slide_header_lay.addWidget(h_s_del, 0)
        lay_hw.addWidget(slide_header)

        self.slide_list_layout = QVBoxLayout()
        self.slide_list_layout.setSpacing(0) # Minimální rozestup (gap)
        
        slide_scroll = QScrollArea()
        slide_scroll.setWidgetResizable(True)
        slide_scroll_widget = QWidget()
        slide_scroll_widget.setLayout(self.slide_list_layout)
        slide_scroll.setWidget(slide_scroll_widget)
        slide_scroll.setFixedHeight(130)
        lay_hw.addWidget(slide_scroll)
        
        btn_add_slide = QPushButton("+ Přidat nové sklíčko")
        btn_add_slide.clicked.connect(lambda checked: self.add_slide_row())
        lay_hw.addWidget(btn_add_slide)
        
        # Načtení stávajících sklíček
        sklo_dims = self.settings.get("sklo_dims", {})
        for name, params in sklo_dims.items():
            self.add_slide_row(name, params[0], params[1], params[2])
            
        lay_hw.addWidget(QLabel("<br><b>Parametry podložky:</b>"))
        hw_form = QFormLayout()
        self.inp_bed_x = QDoubleSpinBox(); self.inp_bed_x.setRange(50, 1000); self.inp_bed_x.setValue(self.settings.get("bed_max_x", 250.0))
        self.inp_bed_y = QDoubleSpinBox(); self.inp_bed_y.setRange(50, 1000); self.inp_bed_y.setValue(self.settings.get("bed_max_y", 210.0))
        self.inp_start_x = QDoubleSpinBox(); self.inp_start_x.setRange(0, 100); self.inp_start_x.setValue(self.settings.get("start_offset_x", 10.0))
        self.inp_start_y = QDoubleSpinBox(); self.inp_start_y.setRange(0, 100); self.inp_start_y.setValue(self.settings.get("start_offset_y", 10.0))
        self.inp_spacing = QDoubleSpinBox(); self.inp_spacing.setRange(0, 50); self.inp_spacing.setValue(self.settings.get("multi_spacing", 5.0))
        
        self.inp_holder_z = QDoubleSpinBox(); self.inp_holder_z.setRange(0, 50); self.inp_holder_z.setDecimals(3); self.inp_holder_z.setSuffix(" mm")
        self.inp_holder_z.setValue(self.settings.get("default_z_offset", 0.2))
        self.inp_holder_z.valueChanged.connect(lambda: self._sync_schema_to_profile())

        self.chk_show_grid = QCheckBox("Zobrazit mřížku u sklíček v náhledu")
        self.chk_show_grid.setChecked(self.settings.get("show_slide_grid", True))
        
        self.chk_show_axes = QCheckBox("Zobrazit hlavní osy (X, Y) tiskárny")
        self.chk_show_axes.setChecked(self.settings.get("show_bed_axes", True))
        
        hw_form.addRow("Max šířka (X) [mm]:", self.inp_bed_x); hw_form.addRow("Max hloubka (Y) [mm]:", self.inp_bed_y)
        hw_form.addRow("Odsazení (X okraj) [mm]:", self.inp_start_x); hw_form.addRow("Odsazení (Y okraj) [mm]:", self.inp_start_y)
        hw_form.addRow("Mezera mezi sklíčky [mm]:", self.inp_spacing)
        hw_form.addRow("Tloušťka držáku / masky [mm]:", self.inp_holder_z)
        hw_form.addRow(self.chk_show_grid)
        hw_form.addRow(self.chk_show_axes)
        
        lay_hw.addLayout(hw_form)
        lay_hw.addStretch()
        tabs.addTab(tab_hw, "Podložka")

        # --- ZÁLOŽKA 3: Převody & Kalibrace ---
        tab_cal = QWidget()
        lay_cal = QVBoxLayout(tab_cal)
        lay_cal.addWidget(QLabel("<b>Kalibrace extruze (Objem -> Kroky):</b>"))
        lay_cal.addWidget(QLabel("Tento koeficient určuje, kolik 'E' jednotek (mm filamentu) odpovídá 1 µl kapaliny."))
        
        cal_form = QFormLayout()
        self.inp_cal_factor = QDoubleSpinBox()
        self.inp_cal_factor.setRange(0.0001, 1000.0)
        self.inp_cal_factor.setDecimals(6)
        self.inp_cal_factor.setSingleStep(0.01)
        
        # Výpočet výchozího faktoru pokud v nastavení chybí
        filament_diam = self.settings.get('filament_diameter', 9.5)
        import math
        default_cal = 1.0 / (math.pi * ((filament_diam / 2.0) ** 2))
        self.inp_cal_factor.setValue(self.settings.get("calibration_factor", default_cal))
        
        cal_form.addRow("Kalibrační faktor [E-jednotka / µl]:", self.inp_cal_factor)
        lay_cal.addLayout(cal_form)
        
        # Informační text
        info_label = QLabel(
            "<br><b>Nápověda pro stříkačku (vnitřní průměr 9.5 mm):</b><br>"
            "Plocha pístu je cca 70.88 mm².<br>"
            "1 mm posunu pístu = cca 70.88 µl kapaliny.<br>"
            "1 µl = cca 0.0141 mm posunu pístu (jednotka E v G-kódu).<br>"
            "<i>Poznámka: Hodnota 1.0 znamená, že 1 µl = 1 mm posunu pístu.</i>"
        )
        info_label.setWordWrap(True)
        lay_cal.addWidget(info_label)
        lay_cal.addStretch()
        tabs.addTab(tab_cal, "Převody")

        # --- ZÁLOŽKA 4: G-code ---
        tab_gcode = QWidget(); lay_gcode = QVBoxLayout(tab_gcode)
        lay_gcode.addWidget(QLabel("<b>Hlavní startovací G-code:</b>"))
        self.txt_start = QTextEdit(); self.txt_start.setPlainText(self.settings.get("start_gcode", "").replace('\\n', '\n')); lay_gcode.addWidget(self.txt_start)
        lay_gcode.addWidget(QLabel("<b>Před každým sklíčkem:</b>"))
        self.txt_loop_start = QTextEdit(); self.txt_loop_start.setPlainText(self.settings.get("loop_start_gcode", "").replace('\\n', '\n')); lay_gcode.addWidget(self.txt_loop_start)
        lay_gcode.addWidget(QLabel("<b>Za každým sklíčkem:</b>"))
        self.txt_loop_end = QTextEdit(); self.txt_loop_end.setPlainText(self.settings.get("loop_end_gcode", "").replace('\\n', '\n')); lay_gcode.addWidget(self.txt_loop_end)
        lay_gcode.addWidget(QLabel("<b>Ukončovací G-code:</b>"))
        self.txt_end = QTextEdit(); self.txt_end.setPlainText(self.settings.get("end_gcode", "").replace('\\n', '\n')); lay_gcode.addWidget(self.txt_end)
        tabs.addTab(tab_gcode, "G-code Skripty")

        layout.addWidget(tabs)

        # Inicializace schématu podle vybraných profilů (výchozí první)
        self._sync_schema_to_profile()

        # --- Tlačítka ---
        btn_layout = QHBoxLayout()
        btn_restore = QPushButton("Obnovit výchozí"); btn_restore.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;"); btn_restore.clicked.connect(self.restore_defaults)
        btn_save = QPushButton("Uložit a zavřít"); btn_save.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold;"); btn_save.clicked.connect(self.save_and_close)
        btn_cancel = QPushButton("Zrušit"); btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_restore); btn_layout.addStretch(); btn_layout.addWidget(btn_cancel); btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _sync_schema_to_profile(self):
        """Aktualizuje interaktivní schéma (zobrazuje první dostupné profily jako reprezentativní)."""
        if not hasattr(self, 'view_schema'): return
        
        # Sestavíme dočasný settings dict pro schéma
        schema_data = self.settings.copy()
        
        # Globální parametry
        schema_data["block_height"] = self.inp_block_height.value()
        schema_data["filament_diameter"] = self.inp_filament_d.value()
        schema_data["z_offset"] = self.inp_holder_z.value()
        schema_data["holder_z"] = self.inp_holder_z.value() # Pro vizualizaci "Výška držáku"
        
        # Pro zobrazení v SVG použijeme PRVNÍ dostupnou trysku a sklo (jako zástupce)
        if self.nozzle_rows:
            row = self.nozzle_rows[0]
            schema_data["nozzle_height_val"] = row['h'].value()
            schema_data["nozzle_diam_val"] = row['d'].value()
            schema_data["nozzle_hidden_val"] = row['s'].value()
        else:
            schema_data["nozzle_height_val"] = 30.0
            schema_data["nozzle_diam_val"] = 0.4
            schema_data["nozzle_hidden_val"] = 4.0
                
        if self.slide_rows:
            row = self.slide_rows[0]
            schema_data["slide_z_val"] = row['z'].value()
        else:
            schema_data["slide_z_val"] = 1.0

        # Aktualizujeme schéma
        self.view_schema.set_initial_values(schema_data, use_explicit=True)

    def handle_schema_click(self, key, label):
        """Zpracuje kliknutí na prvek ve schématu - otevře výběr profilu nebo přímou editaci."""
        # 1. Rozhodneme, zda jde o Nozzle, Glass nebo Globální parametr
        is_nozzle = key in ["nozzle_height", "nozzle_diam", "hidden_nozzle_part"]
        is_glass = key == "slide_z"
        
        if is_nozzle or is_glass:
            # ... existující kód pro trysky a skla ...
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Editovat {label}")
            dlg_lay = QVBoxLayout(dlg)
            form = QFormLayout()
            
            cmb = QComboBox()
            inp = QDoubleSpinBox()
            inp.setRange(0, 1000)
            inp.setDecimals(3)
            inp.setSuffix(" mm")
            
            rows = self.nozzle_rows if is_nozzle else self.slide_rows
            for r in rows: cmb.addItem(r['name'].text())
            
            def on_profile_changed():
                idx = cmb.currentIndex()
                if idx >= 0:
                    r = rows[idx]
                    if is_nozzle:
                        if key == "nozzle_height": inp.setValue(r['h'].value())
                        elif key == "nozzle_diam": inp.setValue(r['d'].value())
                        elif key == "hidden_nozzle_part": inp.setValue(r['s'].value())
                    else: # glass
                        inp.setValue(r['z'].value())
            
            cmb.currentIndexChanged.connect(on_profile_changed)
            on_profile_changed() # Načíst hodnotu prvního profilu
            
            form.addRow("Vybrat profil:", cmb)
            form.addRow(f"Nová hodnota:", inp)
            dlg_lay.addLayout(form)
            
            btns = QHBoxLayout()
            btn_ok = QPushButton("Uložit"); btn_ok.clicked.connect(dlg.accept)
            btn_cancel = QPushButton("Zrušit"); btn_cancel.clicked.connect(dlg.reject)
            btns.addWidget(btn_cancel); btns.addWidget(btn_ok)
            dlg_lay.addLayout(btns)
            
            if dlg.exec():
                idx = cmb.currentIndex()
                val = inp.value()
                if idx >= 0:
                    r = rows[idx]
                    if is_nozzle:
                        if key == "nozzle_height": r['h'].setValue(val)
                        elif key == "nozzle_diam": r['d'].setValue(val)
                        elif key == "hidden_nozzle_part": r['s'].setValue(val)
                    else: # glass
                        r['z'].setValue(val)
                    # Po změně aktualizujeme SVG (pokud je to ten zástupný, co je vidět)
                    # Ale pro jistotu refresheneme celé schéma
                    self._sync_schema_to_profile()
        else:
            # Globální parametr - stačí se zeptat na hodnotu
            from PyQt6.QtWidgets import QInputDialog
            curr_val = 0.0
            if key == "block_height": curr_val = self.inp_block_height.value()
            elif key == "filament_diameter": curr_val = self.inp_filament_d.value()
            elif key in ["z_offset", "holder_z"]: curr_val = self.inp_holder_z.value()
            
            val, ok = QInputDialog.getDouble(self, "Změna", f"{label} [mm]:", value=curr_val, decimals=2)
            if ok:
                self.update_from_schema(key, val)
                # Aktualizujeme všechna relevantní textová pole v SVG
                if key in ["z_offset", "holder_z"]:
                    self.view_schema.update_svg_text("Výška vrstvy", val, refresh=False)
                    self.view_schema.update_svg_text("Výška držáku", val, refresh=True)
                else:
                    self.view_schema.update_svg_text(label, val)

    def update_from_schema(self, key, value):
        """Aktualizuje pouze globální hodnoty v UI na základě interakce se schématem."""
        if key == "block_height": self.inp_block_height.setValue(value)
        elif key == "filament_diameter": self.inp_filament_d.setValue(value)
        elif key in ["z_offset", "holder_z"]: self.inp_holder_z.setValue(value)
        # Ostatní (nozzle/glass) jsou řešeny v handle_schema_click dialogu
        self._sync_schema_to_profile()

    def _refresh_schema_dropdowns(self):
        """Dropdowny nad schématem byly odstraněny."""
        pass

    def add_nozzle_row(self, name="", height=30.0, diam=0.4, hidden=4.0):
        # ... beze změny ...
        row_widget = QWidget()
        row_lay = QHBoxLayout(row_widget)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(5) # Shoda se záložkou sklíček
        
        inp_name = QLineEdit(name); inp_name.setPlaceholderText("Název"); inp_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inp_name.textChanged.connect(self._refresh_schema_dropdowns)
        inp_h = QDoubleSpinBox(); inp_h.setRange(0, 100); inp_h.setValue(height); inp_h.setSuffix(" mm"); inp_h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inp_h.valueChanged.connect(lambda: self._sync_schema_to_profile())
        inp_d = QDoubleSpinBox(); inp_d.setRange(0.01, 10); inp_d.setValue(diam); inp_d.setDecimals(3); inp_d.setSuffix(" mm"); inp_d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inp_d.valueChanged.connect(lambda: self._sync_schema_to_profile())
        inp_s = QDoubleSpinBox(); inp_s.setRange(0, 100); inp_s.setValue(hidden); inp_s.setSuffix(" mm"); inp_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inp_s.valueChanged.connect(lambda: self._sync_schema_to_profile())
        
        btn_del = QPushButton()
        btn_del.setFixedSize(30, 24)
        icon_path = get_resource_path("svg/trash-can.svg")
        if os.path.exists(icon_path):
            btn_del.setIcon(QIcon(icon_path))
        else:
            btn_del.setText("✕")
        btn_del.setStyleSheet("background-color: #dc3545; color: white; border-radius: 4px; padding: 2px;")
        btn_del.clicked.connect(lambda checked: self.remove_nozzle_row(row_widget))
        
        row_lay.addWidget(inp_name, 3)
        row_lay.addWidget(inp_h, 2)
        row_lay.addWidget(inp_d, 2)
        row_lay.addWidget(inp_s, 2)
        row_lay.addWidget(btn_del, 0)
        self.nozzle_list_layout.addWidget(row_widget)
        self.nozzle_rows.append({'widget': row_widget, 'name': inp_name, 'h': inp_h, 'd': inp_d, 's': inp_s})

    def remove_nozzle_row(self, widget):
        for i, row in enumerate(self.nozzle_rows):
            if row['widget'] == widget:
                self.nozzle_rows.pop(i)
                widget.deleteLater()
                self._refresh_schema_dropdowns()
                break

    def add_slide_row(self, name="", w=76.0, h=26.0, z=1.0):
        row_widget = QWidget()
        row_lay = QHBoxLayout(row_widget)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(5) # Zmenšený rozestup mezi políčky
        
        inp_name = QLineEdit(name); inp_name.setPlaceholderText("Název"); inp_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inp_name.textChanged.connect(self._refresh_schema_dropdowns)
        inp_w = QDoubleSpinBox(); inp_w.setRange(1, 500); inp_w.setValue(w); inp_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inp_h = QDoubleSpinBox(); inp_h.setRange(1, 500); inp_h.setValue(h); inp_h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inp_z = QDoubleSpinBox(); inp_z.setRange(0.1, 20); inp_z.setValue(z); inp_z.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inp_z.valueChanged.connect(lambda: self._sync_schema_to_profile())
        
        btn_del = QPushButton()
        btn_del.setFixedSize(30, 24)
        icon_path = get_resource_path("svg/trash-can.svg")
        if os.path.exists(icon_path):
            btn_del.setIcon(QIcon(icon_path))
        else:
            btn_del.setText("✕")
        btn_del.setStyleSheet("background-color: #dc3545; color: white; border-radius: 4px; padding: 2px;")
        btn_del.clicked.connect(lambda checked: self.remove_slide_row(row_widget))
        
        row_lay.addWidget(inp_name, 3)
        row_lay.addWidget(inp_w, 2)
        row_lay.addWidget(inp_h, 2)
        row_lay.addWidget(inp_z, 2)
        row_lay.addWidget(btn_del, 0)
        self.slide_list_layout.addWidget(row_widget)
        self.slide_rows.append({'widget': row_widget, 'name': inp_name, 'w': inp_w, 'h': inp_h, 'z': inp_z})

    def remove_slide_row(self, widget):
        for i, row in enumerate(self.slide_rows):
            if row['widget'] == widget:
                self.slide_rows.pop(i)
                widget.deleteLater()
                self._refresh_schema_dropdowns()
                break

    def restore_defaults(self):
        odp = QMessageBox.question(self, "Obnovit výchozí", "Opravdu přepsat nastavení na výchozí hodnoty?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if odp == QMessageBox.StandardButton.Yes:
            restore_default_settings(); self.settings = load_settings()
            # Zde by bylo nutné překreslit všechny řádky, nejjednodušší je zavřít a otevřít znovu nebo vyčistit
            self.accept() 

    def save_and_close(self):
        # Sestavení nozzle_defs ze seznamu řádků
        new_nozzles = {}
        for row in self.nozzle_rows:
            name = row['name'].text().strip()
            if name:
                new_nozzles[name] = [row['h'].value(), row['d'].value(), row['s'].value()]
        
        # Sestavení sklo_dims ze seznamu řádků
        new_slides = {}
        for row in self.slide_rows:
            name = row['name'].text().strip()
            if name:
                new_slides[name] = [row['w'].value(), row['h'].value(), row['z'].value()]

        self.settings.update({
            "bed_max_x": self.inp_bed_x.value(), "bed_max_y": self.inp_bed_y.value(),
            "start_offset_x": self.inp_start_x.value(), "start_offset_y": self.inp_start_y.value(),
            "multi_spacing": self.inp_spacing.value(),
            "default_z_offset": self.inp_holder_z.value(),
            "show_slide_grid": self.chk_show_grid.isChecked(),
            "show_bed_axes": self.chk_show_axes.isChecked(),
            "print_speed": self.inp_speed.value(), "retraction": self.inp_retract.value(),
            "filament_diameter": self.inp_filament_d.value(),
            "flow_multiplier": self.inp_flow_mult.value(),
            "block_height": self.inp_block_height.value(),
            "calibration_factor": self.inp_cal_factor.value(),
            "start_gcode": self.txt_start.toPlainText(), "end_gcode": self.txt_end.toPlainText(),
            "loop_start_gcode": self.txt_loop_start.toPlainText(), "loop_end_gcode": self.txt_loop_end.toPlainText(),
            "nozzle_defs": new_nozzles,
            "sklo_dims": new_slides
        })
        save_settings(self.settings)
        QMessageBox.information(self, "Uloženo", "Nastavení úspěšně uloženo."); self.accept()
