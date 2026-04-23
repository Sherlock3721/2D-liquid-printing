import json
import os
import sys
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, 
                             QFormLayout, QTextEdit, QPushButton, QHBoxLayout, 
                             QDoubleSpinBox, QSpinBox, QLabel, QMessageBox,
                             QCheckBox, QScrollArea, QFrame, QLineEdit)
from PyQt6.QtCore import Qt

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
        self.resize(600, 700)
        self.settings = load_settings()

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # --- ZÁLOŽKA 1: Extruze & Trysky ---
        tab_extruze = QWidget()
        lay_extruze = QVBoxLayout(tab_extruze)
        
        lay_extruze.addWidget(QLabel("<b>Definice trysek (Název | Výška | Průměr):</b>"))
        
        self.nozzle_list_layout = QVBoxLayout()
        self.nozzle_list_layout.setSpacing(5)
        self.nozzle_rows = []
        
        nozzle_scroll = QScrollArea()
        nozzle_scroll.setWidgetResizable(True)
        nozzle_scroll_widget = QWidget()
        nozzle_scroll_widget.setLayout(self.nozzle_list_layout)
        nozzle_scroll.setWidget(nozzle_scroll_widget)
        nozzle_scroll.setFixedHeight(200)
        lay_extruze.addWidget(nozzle_scroll)
        
        btn_add_nozzle = QPushButton("+ Přidat novou trysku")
        btn_add_nozzle.clicked.connect(lambda checked: self.add_nozzle_row())
        lay_extruze.addWidget(btn_add_nozzle)
        
        # Načtení stávajících trysek
        nozzle_defs = self.settings.get("nozzle_defs", {})
        for name, params in nozzle_defs.items():
            self.add_nozzle_row(name, params[0], params[1])
        
        lay_extruze.addWidget(QLabel("<br><b>Globální parametry extruze:</b>"))
        ext_form = QFormLayout()
        self.inp_speed = QSpinBox(); self.inp_speed.setRange(10, 10000); self.inp_speed.setSingleStep(100); self.inp_speed.setSuffix(" mm/min")
        self.inp_speed.setValue(self.settings.get("print_speed", 1500))
        self.inp_retract = QDoubleSpinBox(); self.inp_retract.setRange(0.0, 50.0); self.inp_retract.setSingleStep(0.1); self.inp_retract.setSuffix(" mm")
        self.inp_retract.setValue(self.settings.get("retraction", 1.0))
        
        self.inp_filament_d = QDoubleSpinBox(); self.inp_filament_d.setRange(0.1, 50.0); self.inp_filament_d.setSingleStep(0.01); self.inp_filament_d.setSuffix(" mm")
        self.inp_filament_d.setValue(self.settings.get("filament_diameter", 9.5))
        
        self.inp_flow_mult = QDoubleSpinBox(); self.inp_flow_mult.setRange(0.1, 10.0); self.inp_flow_mult.setSingleStep(0.05)
        self.inp_flow_mult.setValue(self.settings.get("flow_multiplier", 1.0))

        ext_form.addRow("Rychlost tisku:", self.inp_speed); ext_form.addRow("Retrakce:", self.inp_retract)
        ext_form.addRow("Vnitřní průměr stříkačky:", self.inp_filament_d); ext_form.addRow("Flow multiplikátor:", self.inp_flow_mult)
        lay_extruze.addLayout(ext_form)
        lay_extruze.addStretch()
        tabs.addTab(tab_extruze, "Extruze")

        # --- ZÁLOŽKA 2: Podložka & Sklíčka ---
        tab_hw = QWidget()
        lay_hw = QVBoxLayout(tab_hw)
        
        lay_hw.addWidget(QLabel("<b>Definice sklíček (Název | Šířka | Výška | Tloušťka):</b>"))
        
        self.slide_list_layout = QVBoxLayout()
        self.slide_list_layout.setSpacing(5)
        self.slide_rows = []
        
        slide_scroll = QScrollArea()
        slide_scroll.setWidgetResizable(True)
        slide_scroll_widget = QWidget()
        slide_scroll_widget.setLayout(self.slide_list_layout)
        slide_scroll.setWidget(slide_scroll_widget)
        slide_scroll.setFixedHeight(200)
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
        self.inp_correction_z = QDoubleSpinBox(); self.inp_correction_z.setRange(-10.0, 10.0); self.inp_correction_z.setSingleStep(0.01); self.inp_correction_z.setDecimals(3); self.inp_correction_z.setSuffix(" mm")
        self.inp_correction_z.setValue(self.settings.get("correction_z", 0.0))
        
        self.chk_show_grid = QCheckBox("Zobrazit mřížku u sklíček v náhledu")
        self.chk_show_grid.setChecked(self.settings.get("show_slide_grid", True))
        
        self.chk_show_axes = QCheckBox("Zobrazit hlavní osy (X, Y) tiskárny")
        self.chk_show_axes.setChecked(self.settings.get("show_bed_axes", True))
        
        hw_form.addRow("Max šířka (X) [mm]:", self.inp_bed_x); hw_form.addRow("Max hloubka (Y) [mm]:", self.inp_bed_y)
        hw_form.addRow("Odsazení (X okraj) [mm]:", self.inp_start_x); hw_form.addRow("Odsazení (Y okraj) [mm]:", self.inp_start_y)
        hw_form.addRow("Mezera mezi sklíčky [mm]:", self.inp_spacing); hw_form.addRow("<b>Korekce Z [mm]:</b>", self.inp_correction_z)
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

        # --- Tlačítka ---
        btn_layout = QHBoxLayout()
        btn_restore = QPushButton("Obnovit výchozí"); btn_restore.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;"); btn_restore.clicked.connect(self.restore_defaults)
        btn_save = QPushButton("Uložit a zavřít"); btn_save.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold;"); btn_save.clicked.connect(self.save_and_close)
        btn_cancel = QPushButton("Zrušit"); btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_restore); btn_layout.addStretch(); btn_layout.addWidget(btn_cancel); btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def add_nozzle_row(self, name="", height=30.0, diam=0.4):
        row_widget = QWidget()
        row_lay = QHBoxLayout(row_widget)
        row_lay.setContentsMargins(0, 0, 0, 0)
        
        inp_name = QLineEdit(name); inp_name.setPlaceholderText("Název")
        inp_h = QDoubleSpinBox(); inp_h.setRange(0, 100); inp_h.setValue(height); inp_h.setSuffix(" mm")
        inp_d = QDoubleSpinBox(); inp_d.setRange(0.01, 10); inp_d.setValue(diam); inp_d.setDecimals(3); inp_d.setSuffix(" mm")
        
        btn_del = QPushButton("✕")
        btn_del.setFixedWidth(30)
        btn_del.setStyleSheet("color: #ff4444; font-weight: bold;")
        btn_del.clicked.connect(lambda checked: self.remove_nozzle_row(row_widget))
        
        row_lay.addWidget(inp_name); row_lay.addWidget(inp_h); row_lay.addWidget(inp_d); row_lay.addWidget(btn_del)
        self.nozzle_list_layout.addWidget(row_widget)
        self.nozzle_rows.append({'widget': row_widget, 'name': inp_name, 'h': inp_h, 'd': inp_d})

    def remove_nozzle_row(self, widget):
        for i, row in enumerate(self.nozzle_rows):
            if row['widget'] == widget:
                self.nozzle_rows.pop(i)
                widget.deleteLater()
                break

    def add_slide_row(self, name="", w=76.0, h=26.0, z=1.0):
        row_widget = QWidget()
        row_lay = QHBoxLayout(row_widget)
        row_lay.setContentsMargins(0, 0, 0, 0)
        
        inp_name = QLineEdit(name); inp_name.setPlaceholderText("Název")
        inp_w = QDoubleSpinBox(); inp_w.setRange(1, 500); inp_w.setValue(w)
        inp_h = QDoubleSpinBox(); inp_h.setRange(1, 500); inp_h.setValue(h)
        inp_z = QDoubleSpinBox(); inp_z.setRange(0.1, 20); inp_z.setValue(z)
        
        btn_del = QPushButton("✕")
        btn_del.setFixedWidth(30)
        btn_del.setStyleSheet("color: #ff4444; font-weight: bold;")
        btn_del.clicked.connect(lambda checked: self.remove_slide_row(row_widget))
        
        row_lay.addWidget(inp_name); row_lay.addWidget(inp_w); row_lay.addWidget(inp_h); row_lay.addWidget(inp_z); row_lay.addWidget(btn_del)
        self.slide_list_layout.addWidget(row_widget)
        self.slide_rows.append({'widget': row_widget, 'name': inp_name, 'w': inp_w, 'h': inp_h, 'z': inp_z})

    def remove_slide_row(self, widget):
        for i, row in enumerate(self.slide_rows):
            if row['widget'] == widget:
                self.slide_rows.pop(i)
                widget.deleteLater()
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
                new_nozzles[name] = [row['h'].value(), row['d'].value()]
        
        # Sestavení sklo_dims ze seznamu řádků
        new_slides = {}
        for row in self.slide_rows:
            name = row['name'].text().strip()
            if name:
                new_slides[name] = [row['w'].value(), row['h'].value(), row['z'].value()]

        self.settings.update({
            "bed_max_x": self.inp_bed_x.value(), "bed_max_y": self.inp_bed_y.value(),
            "start_offset_x": self.inp_start_x.value(), "start_offset_y": self.inp_start_y.value(),
            "multi_spacing": self.inp_spacing.value(), "correction_z": self.inp_correction_z.value(),
            "show_slide_grid": self.chk_show_grid.isChecked(),
            "show_bed_axes": self.chk_show_axes.isChecked(),
            "print_speed": self.inp_speed.value(), "retraction": self.inp_retract.value(),
            "filament_diameter": self.inp_filament_d.value(),
            "flow_multiplier": self.inp_flow_mult.value(),
            "calibration_factor": self.inp_cal_factor.value(),
            "start_gcode": self.txt_start.toPlainText(), "end_gcode": self.txt_end.toPlainText(),
            "loop_start_gcode": self.txt_loop_start.toPlainText(), "loop_end_gcode": self.txt_loop_end.toPlainText(),
            "nozzle_defs": new_nozzles,
            "sklo_dims": new_slides
        })
        save_settings(self.settings)
        QMessageBox.information(self, "Uloženo", "Nastavení úspěšně uloženo."); self.accept()
