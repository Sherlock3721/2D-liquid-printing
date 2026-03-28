import json
import os
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, 
                             QFormLayout, QTextEdit, QPushButton, QHBoxLayout, 
                             QDoubleSpinBox, QSpinBox, QLabel, QMessageBox)

SETTINGS_FILE = os.path.join(os.getcwd(), "settings.json")
DEFAULT_SETTINGS_FILE = os.path.join(os.getcwd(), "settings_default.json")

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
        except json.JSONDecodeError:
            pass

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
        self.resize(550, 650)
        self.settings = load_settings()

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # --- ZÁLOŽKA 1: Extruze (Původně Trysky) ---
        tab_extruze = QWidget()
        lay_extruze = QVBoxLayout(tab_extruze)
        
        # Sekce trysky
        lay_extruze.addWidget(QLabel("<b>Parametry trysek (Výška x Průměr ústí):</b>"))
        self.nozzle_widgets = {}
        nozzle_form = QFormLayout()
        nozzle_defs = self.settings.get("nozzle_defs", {})
        for name, params in nozzle_defs.items():
            if name == "Vlastní": continue
            w_box = QWidget()
            w_lay = QHBoxLayout(w_box)
            w_lay.setContentsMargins(0,0,0,0)
            inp_h = QDoubleSpinBox(); inp_h.setRange(0, 100); inp_h.setDecimals(2); inp_h.setValue(params[0]); inp_h.setSuffix(" mm")
            inp_d = QDoubleSpinBox(); inp_d.setRange(0.01, 10); inp_d.setDecimals(3); inp_d.setValue(params[1]); inp_d.setSuffix(" mm")
            w_lay.addWidget(QLabel("Výška:")); w_lay.addWidget(inp_h); w_lay.addWidget(QLabel("Průměr:")); w_lay.addWidget(inp_d)
            nozzle_form.addRow(f"{name}:", w_box)
            self.nozzle_widgets[name] = (inp_h, inp_d)
        lay_extruze.addLayout(nozzle_form)
        
        lay_extruze.addWidget(QLabel("<br><b>Globální parametry extruze:</b>"))
        ext_form = QFormLayout()
        self.inp_speed = QSpinBox()
        self.inp_speed.setRange(10, 10000); self.inp_speed.setSingleStep(100); self.inp_speed.setSuffix(" mm/min")
        self.inp_speed.setValue(self.settings.get("print_speed", 1500))
        
        self.inp_retract = QDoubleSpinBox()
        self.inp_retract.setRange(0.0, 50.0); self.inp_retract.setSingleStep(0.1); self.inp_retract.setSuffix(" mm")
        self.inp_retract.setValue(self.settings.get("retraction", 1.0))
        
        ext_form.addRow("Rychlost tisku:", self.inp_speed)
        ext_form.addRow("Retrakce:", self.inp_retract)
        lay_extruze.addLayout(ext_form)
        lay_extruze.addStretch()
        tabs.addTab(tab_extruze, "Extruze")

        # --- ZÁLOŽKA 2: Podložka (Původně Hardware) ---
        tab_hw = QWidget()
        lay_hw = QFormLayout(tab_hw)

        self.inp_bed_x = QDoubleSpinBox(); self.inp_bed_x.setRange(50, 1000); self.inp_bed_x.setValue(self.settings.get("bed_max_x", 250.0))
        self.inp_bed_y = QDoubleSpinBox(); self.inp_bed_y.setRange(50, 1000); self.inp_bed_y.setValue(self.settings.get("bed_max_y", 210.0))
        self.inp_start_x = QDoubleSpinBox(); self.inp_start_x.setRange(0, 100); self.inp_start_x.setValue(self.settings.get("start_offset_x", 10.0))
        self.inp_start_y = QDoubleSpinBox(); self.inp_start_y.setRange(0, 100); self.inp_start_y.setValue(self.settings.get("start_offset_y", 10.0))
        self.inp_spacing = QDoubleSpinBox(); self.inp_spacing.setRange(0, 50); self.inp_spacing.setValue(self.settings.get("multi_spacing", 5.0))
        
        self.inp_correction_z = QDoubleSpinBox()
        self.inp_correction_z.setRange(-10.0, 10.0); self.inp_correction_z.setSingleStep(0.01); self.inp_correction_z.setDecimals(3); self.inp_correction_z.setSuffix(" mm")
        self.inp_correction_z.setValue(self.settings.get("correction_z", 0.0))

        lay_hw.addRow("Max šířka podložky (X) [mm]:", self.inp_bed_x)
        lay_hw.addRow("Max hloubka podložky (Y) [mm]:", self.inp_bed_y)
        lay_hw.addRow("Odsazení vzorku (X okraj) [mm]:", self.inp_start_x)
        lay_hw.addRow("Odsazení vzorku (Y okraj) [mm]:", self.inp_start_y)
        lay_hw.addRow("Mezera mezi sklíčky [mm]:", self.inp_spacing)
        lay_hw.addRow("<b>Korekce Z (Calibration Z) [mm]:</b>", self.inp_correction_z)
        tabs.addTab(tab_hw, "Podložka")

        # --- ZÁLOŽKA 3: Vlastní G-code ---
        tab_gcode = QWidget()
        lay_gcode = QVBoxLayout(tab_gcode)
        lay_gcode.addWidget(QLabel("<b>Hlavní startovací G-code:</b>"))
        self.txt_start = QTextEdit(); self.txt_start.setPlainText(self.settings.get("start_gcode", "").replace('\\n', '\n')); lay_gcode.addWidget(self.txt_start)
        lay_gcode.addWidget(QLabel("<b>Před každým sklíčkem (Smyčka Start):</b>"))
        self.txt_loop_start = QTextEdit(); self.txt_loop_start.setPlainText(self.settings.get("loop_start_gcode", "").replace('\\n', '\n')); lay_gcode.addWidget(self.txt_loop_start)
        lay_gcode.addWidget(QLabel("<b>Za každým sklíčkem (Smyčka Konec):</b>"))
        self.txt_loop_end = QTextEdit(); self.txt_loop_end.setPlainText(self.settings.get("loop_end_gcode", "").replace('\\n', '\n')); lay_gcode.addWidget(self.txt_loop_end)
        lay_gcode.addWidget(QLabel("<b>Ukončovací G-code (Úplný konec):</b>"))
        self.txt_end = QTextEdit(); self.txt_end.setPlainText(self.settings.get("end_gcode", "").replace('\\n', '\n')); lay_gcode.addWidget(self.txt_end)
        tabs.addTab(tab_gcode, "G-code Skripty")

        layout.addWidget(tabs)

        # --- Tlačítka uložení ---
        btn_layout = QHBoxLayout()
        btn_restore = QPushButton("Obnovit výchozí"); btn_restore.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; }"); btn_restore.clicked.connect(self.restore_defaults)
        btn_save = QPushButton("Uložit a zavřít"); btn_save.setStyleSheet("QPushButton { background-color: #0d6efd; color: white; font-weight: bold; }"); btn_save.clicked.connect(self.save_and_close)
        btn_cancel = QPushButton("Zrušit"); btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_restore); btn_layout.addStretch(); btn_layout.addWidget(btn_cancel); btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def restore_defaults(self):
        odpoved = QMessageBox.question(self, "Obnovit výchozí", "Opravdu chcete přepsat všechna nastavení na výchozí hodnoty?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if odpoved == QMessageBox.StandardButton.Yes:
            restore_default_settings()
            self.settings = load_settings()
            self.inp_bed_x.setValue(self.settings.get("bed_max_x", 250.0))
            self.inp_bed_y.setValue(self.settings.get("bed_max_y", 210.0))
            self.inp_start_x.setValue(self.settings.get("start_offset_x", 10.0))
            self.inp_start_y.setValue(self.settings.get("start_offset_y", 10.0))
            self.inp_spacing.setValue(self.settings.get("multi_spacing", 5.0))
            self.inp_correction_z.setValue(self.settings.get("correction_z", 0.0))
            self.inp_speed.setValue(self.settings.get("print_speed", 1500))
            self.inp_retract.setValue(self.settings.get("retraction", 1.0))
            self.txt_start.setPlainText(self.settings.get("start_gcode", "").replace('\\n', '\n'))
            self.txt_loop_start.setPlainText(self.settings.get("loop_start_gcode", "").replace('\\n', '\n'))
            self.txt_loop_end.setPlainText(self.settings.get("loop_end_gcode", "").replace('\\n', '\n'))
            self.txt_end.setPlainText(self.settings.get("end_gcode", "").replace('\\n', '\n'))
            nozzle_defs = self.settings.get("nozzle_defs", {})
            for name, (inp_h, inp_d) in self.nozzle_widgets.items():
                if name in nozzle_defs:
                    inp_h.setValue(nozzle_defs[name][0])
                    inp_d.setValue(nozzle_defs[name][1])

    def save_and_close(self):
        self.settings["bed_max_x"] = self.inp_bed_x.value()
        self.settings["bed_max_y"] = self.inp_bed_y.value()
        self.settings["start_offset_x"] = self.inp_start_x.value()
        self.settings["start_offset_y"] = self.inp_start_y.value()
        self.settings["multi_spacing"] = self.inp_spacing.value()
        self.settings["correction_z"] = self.inp_correction_z.value()
        self.settings["print_speed"] = self.inp_speed.value()
        self.settings["retraction"] = self.inp_retract.value()
        self.settings["start_gcode"] = self.txt_start.toPlainText()
        self.settings["end_gcode"] = self.txt_end.toPlainText()
        self.settings["loop_start_gcode"] = self.txt_loop_start.toPlainText()
        self.settings["loop_end_gcode"] = self.txt_loop_end.toPlainText()
        if "nozzle_defs" not in self.settings: self.settings["nozzle_defs"] = {}
        for name, (inp_h, inp_d) in self.nozzle_widgets.items():
            self.settings["nozzle_defs"][name] = [inp_h.value(), inp_d.value()]
        save_settings(self.settings)
        QMessageBox.information(self, "Uloženo", "Nastavení bylo úspěšně uloženo.")
        self.accept()
