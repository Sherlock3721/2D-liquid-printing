from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QPushButton, QLineEdit, QLabel, QWidget)
from PyQt6.QtCore import Qt
from gui.settings import load_settings

class ManualMovementWidget(QWidget):
    """Widget s ovládacími prvky pro manuální posun, určený k vložení do panelu."""
    def __init__(self, printer_worker, parent=None):
        super().__init__(parent)
        self.worker = printer_worker
        self.current_step = 10.0
        
        # Načtení limitů tiskárny
        settings = load_settings()
        self.bed_x = settings.get("bed_max_x", 250.0)
        self.bed_y = settings.get("bed_max_y", 210.0)
        
        self._setup_ui()
        self._apply_styles()
        
        if self.worker:
            self.worker.status_changed.connect(self._handle_status_change)
            self._handle_status_change("") # Počáteční nastavení stavu

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        # --- ABSOLUTNÍ SOUŘADNICE ---
        abs_container = QVBoxLayout()
        abs_label = QLabel("ABSOLUTNÍ POZICE [mm]")
        abs_label.setStyleSheet("color: #aaa; font-weight: bold; font-size: 10px; margin-bottom: 5px;")
        abs_container.addWidget(abs_label)
        
        abs_inputs_layout = QHBoxLayout()
        self.inp_abs_x = QLineEdit("0.0"); self.inp_abs_x.setPlaceholderText("X")
        self.inp_abs_y = QLineEdit("0.0"); self.inp_abs_y.setPlaceholderText("Y")
        self.inp_abs_z = QLineEdit("0.0"); self.inp_abs_z.setPlaceholderText("Z")
        for inp in [self.inp_abs_x, self.inp_abs_y, self.inp_abs_z]:
            inp.setFixedWidth(60)
            inp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inp.setFixedHeight(30)
            
        self.btn_go_abs = QPushButton("PŘEJÍT")
        self.btn_go_abs.setFixedHeight(30)
        self.btn_go_abs.setStyleSheet("background-color: #0d6efd; color: white;")
        self.btn_go_abs.clicked.connect(self._move_to_absolute)
        
        abs_inputs_layout.addWidget(QLabel("X:"))
        abs_inputs_layout.addWidget(self.inp_abs_x)
        abs_inputs_layout.addWidget(QLabel("Y:"))
        abs_inputs_layout.addWidget(self.inp_abs_y)
        abs_inputs_layout.addWidget(QLabel("Z:"))
        abs_inputs_layout.addWidget(self.inp_abs_z)
        abs_inputs_layout.addWidget(self.btn_go_abs)
        abs_container.addLayout(abs_inputs_layout)
        self.main_layout.addLayout(abs_container)

        # --- VOLBA KROKU ---
        step_container = QVBoxLayout()
        step_label = QLabel("KROK POSUNU [mm]")
        step_label.setStyleSheet("color: #aaa; font-weight: bold; font-size: 10px; margin-bottom: 5px;")
        step_container.addWidget(step_label)
        
        self.layout_steps = QHBoxLayout()
        self.step_buttons = {}
        for val in ["0.1", "1", "10", "50"]:
            btn = QPushButton(val)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, v=val: self._update_step(v))
            btn.setFixedHeight(40)
            self.layout_steps.addWidget(btn)
            self.step_buttons[val] = btn
        
        self.step_buttons["10"].setChecked(True)
        step_container.addLayout(self.layout_steps)
        self.main_layout.addLayout(step_container)

        # --- JOG CONTROL ---
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(25)

        # X/Y Mřížka
        xy_container = QVBoxLayout()
        xy_label = QLabel("POHYB X / Y")
        xy_label.setStyleSheet("color: #aaa; font-weight: bold; font-size: 10px;")
        xy_container.addWidget(xy_label)
        
        xy_grid = QGridLayout()
        xy_grid.setSpacing(10)
        self.btn_y_plus = QPushButton("Y+"); self.btn_y_minus = QPushButton("Y-")
        self.btn_x_plus = QPushButton("X+"); self.btn_x_minus = QPushButton("X-")
        self.btn_home_xy = QPushButton("🏠 XY")
        
        xy_grid.addWidget(self.btn_y_plus, 0, 1)
        xy_grid.addWidget(self.btn_x_minus, 1, 0)
        xy_grid.addWidget(self.btn_home_xy, 1, 1)
        xy_grid.addWidget(self.btn_x_plus, 1, 2)
        xy_grid.addWidget(self.btn_y_minus, 2, 1)
        xy_container.addLayout(xy_grid)
        controls_layout.addLayout(xy_container)

        # Z Sloupec
        z_container = QVBoxLayout()
        z_label = QLabel("OSA Z")
        z_label.setStyleSheet("color: #aaa; font-weight: bold; font-size: 10px;")
        z_container.addWidget(z_label)
        
        self.btn_z_plus = QPushButton("Z+")
        self.btn_z_home = QPushButton("🏠 Z")
        self.btn_z_minus = QPushButton("Z-")
        
        z_container.addWidget(self.btn_z_plus)
        z_container.addWidget(self.btn_z_home)
        z_container.addWidget(self.btn_z_minus)
        z_container.addStretch()
        controls_layout.addLayout(z_container)
        self.main_layout.addLayout(controls_layout)

        # --- VLASTNÍ G-CODE ---
        gcode_input_layout = QHBoxLayout()
        self.inp_gcode = QLineEdit(); self.inp_gcode.setPlaceholderText("Vlastní G-code...")
        self.inp_gcode.setFixedHeight(35)
        self.inp_gcode.returnPressed.connect(self._send_custom_gcode)
        self.btn_send_gcode = QPushButton("ODESLAT"); self.btn_send_gcode.setFixedWidth(90)
        self.btn_send_gcode.setFixedHeight(35)
        self.btn_send_gcode.clicked.connect(self._send_custom_gcode)
        gcode_input_layout.addWidget(self.inp_gcode); gcode_input_layout.addWidget(self.btn_send_gcode)
        self.main_layout.addLayout(gcode_input_layout)

        # --- SERVISNÍ ---
        service_layout = QHBoxLayout()
        self.btn_leveling = QPushButton("KALIBRACE (G80)")
        self.btn_leveling.setFixedHeight(40)
        self.btn_leveling.clicked.connect(lambda checked: self.send_gcode("G80"))
        
        self.btn_motors = QPushButton("MOTORY ZAPNUTY")
        self.btn_motors.setCheckable(True)
        self.btn_motors.setChecked(True)
        self.btn_motors.setFixedHeight(40)
        self.btn_motors.clicked.connect(self._toggle_motors)
        
        service_layout.addWidget(self.btn_leveling)
        service_layout.addWidget(self.btn_motors)
        self.main_layout.addLayout(service_layout)

        # Propojení pohybu
        self.btn_x_plus.clicked.connect(lambda checked: self.move("X", 1))
        self.btn_x_minus.clicked.connect(lambda checked: self.move("X", -1))
        self.btn_y_plus.clicked.connect(lambda checked: self.move("Y", 1))
        self.btn_y_minus.clicked.connect(lambda checked: self.move("Y", -1))
        self.btn_z_plus.clicked.connect(lambda checked: self.move("Z", 1))
        self.btn_z_minus.clicked.connect(lambda checked: self.move("Z", -1))
        self.btn_home_xy.clicked.connect(lambda checked: self.send_gcode("G28 X Y"))
        self.btn_z_home.clicked.connect(lambda checked: self.send_gcode("G28 Z"))

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #e0e0e0; }
            QPushButton {
                background-color: #2d2d2d; color: #e0e0e0; border: none;
                border-radius: 4px; padding: 6px; font-weight: bold; font-size: 9pt;
            }
            QPushButton:hover { background-color: #3d3d3d; }
            QPushButton:checked { background-color: #ff9800; color: #000; }
            QPushButton:disabled { background-color: #1a1a1a; color: #555; }
            
            QPushButton[text^="X"] { border-left: 3px solid #ff4444; }
            QPushButton[text^="Y"] { border-left: 3px solid #44ff44; }
            QPushButton[text^="Z"] { border-left: 3px solid #4444ff; }
            
            QLineEdit { background-color: #121212; border: 1px solid #333; border-radius: 4px; color: #fff; padding: 4px; }
            QLineEdit:focus { border: 1px solid #ff9800; }
            QLineEdit:disabled { color: #555; background-color: #1a1a1a; }
            QLabel { font-size: 9pt; }
        """)
        for b in [self.btn_x_plus, self.btn_x_minus, self.btn_y_plus, self.btn_y_minus, self.btn_home_xy]:
            b.setFixedSize(65, 45)
        for b in [self.btn_z_plus, self.btn_z_minus, self.btn_z_home]:
            b.setFixedSize(80, 45)
        self.btn_leveling.setStyleSheet("border-bottom: 2px solid #ffeb3b; color: #ffeb3b;")

    def update_coords(self, x, y, z):
        """Aktualizuje textová pole s absolutními souřadnicemi (voláno zvenčí)."""
        if not self.inp_abs_x.hasFocus(): self.inp_abs_x.setText(f"{x:.2f}")
        if not self.inp_abs_y.hasFocus(): self.inp_abs_y.setText(f"{y:.2f}")
        if not self.inp_abs_z.hasFocus(): self.inp_abs_z.setText(f"{z:.2f}")

    def _handle_status_change(self, status):
        """Deaktivuje ovládání během tisku."""
        printing = False
        if self.worker:
            printing = self.worker.is_printing
        
        # Seznam widgetů, které chceme vypnout
        for btn in self.step_buttons.values(): btn.setEnabled(not printing)
        self.btn_x_plus.setEnabled(not printing); self.btn_x_minus.setEnabled(not printing)
        self.btn_y_plus.setEnabled(not printing); self.btn_y_minus.setEnabled(not printing)
        self.btn_z_plus.setEnabled(not printing); self.btn_z_minus.setEnabled(not printing)
        self.btn_home_xy.setEnabled(not printing); self.btn_z_home.setEnabled(not printing)
        self.btn_go_abs.setEnabled(not printing); self.btn_send_gcode.setEnabled(not printing)
        self.btn_leveling.setEnabled(not printing); self.btn_motors.setEnabled(not printing)
        self.inp_abs_x.setEnabled(not printing); self.inp_abs_y.setEnabled(not printing)
        self.inp_abs_z.setEnabled(not printing); self.inp_gcode.setEnabled(not printing)

    def _update_step(self, val_str):
        self.current_step = float(val_str)
        for v, btn in self.step_buttons.items(): btn.setChecked(v == val_str)

    def _send_custom_gcode(self):
        cmd = self.inp_gcode.text().strip()
        if cmd: self.send_gcode(cmd); self.inp_gcode.clear()

    def _move_to_absolute(self):
        try:
            x = float(self.inp_abs_x.text())
            y = float(self.inp_abs_y.text())
            z = float(self.inp_abs_z.text())
            
            # Kontrola limitů
            x = max(0, min(x, self.bed_x))
            y = max(0, min(y, self.bed_y))
            z = max(0, min(z, 50.0)) # Z limit odhadem 50mm, pokud není v settings
            
            self.send_gcode(f"G90\nG0 X{x:.2f} Y{y:.2f} Z{z:.2f} F3000")
        except ValueError:
            pass

    def _toggle_motors(self):
        if self.btn_motors.isChecked():
            self.send_gcode("M17")
            self.btn_motors.setText("MOTORY ZAPNUTY")
        else:
            self.send_gcode("M84")
            self.btn_motors.setText("MOTORY VYPNUTY")

    def move(self, axis, direction):
        # Marlin doporučení: G91 pro relativní pohyb
        gcode = f"G91\nG0 {axis}{self.current_step * direction:.2f} F3000\nG90"
        self.send_gcode(gcode)

    def send_gcode(self, gcode):
        if self.worker:
            for line in gcode.split('\n'): self.worker.send_command(line)
