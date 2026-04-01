from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QPushButton, QLineEdit, QLabel, QWidget)
from PyQt6.QtCore import Qt

class ManualMovementWidget(QWidget):
    """Widget s ovládacími prvky pro manuální posun, určený k vložení do panelu."""
    def __init__(self, printer_worker, parent=None):
        super().__init__(parent)
        self.worker = printer_worker
        self.current_step = 10.0
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

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
        self.btn_home_xy = QPushButton("XY")
        
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
        self.btn_z_home = QPushButton("Z")
        self.btn_z_minus = QPushButton("Z-")
        
        z_container.addWidget(self.btn_z_plus)
        z_container.addWidget(self.btn_z_home)
        z_container.addWidget(self.btn_z_minus)
        z_container.addStretch()
        controls_layout.addLayout(z_container)
        self.main_layout.addLayout(controls_layout)

        # --- VLASTNÍ G-CODE ---
        gcode_input_layout = QHBoxLayout()
        self.inp_gcode = QLineEdit(); self.inp_gcode.setPlaceholderText("G-code...")
        self.inp_gcode.setFixedHeight(35)
        self.inp_gcode.returnPressed.connect(self._send_custom_gcode)
        self.btn_send_gcode = QPushButton("ODESLAT"); self.btn_send_gcode.setFixedWidth(90)
        self.btn_send_gcode.setFixedHeight(35)
        self.btn_send_gcode.clicked.connect(self._send_custom_gcode)
        gcode_input_layout.addWidget(self.inp_gcode); gcode_input_layout.addWidget(self.btn_send_gcode)
        self.main_layout.addLayout(gcode_input_layout)

        # --- SERVISNÍ ---
        service_layout = QHBoxLayout()
        self.btn_leveling = QPushButton("MĚŘENÍ PODLOŽKY (G80)")
        self.btn_leveling.setFixedHeight(40)
        self.btn_leveling.clicked.connect(lambda checked: self.send_gcode("G80"))
        self.btn_motors_off = QPushButton("VYPNOUT MOTORY")
        self.btn_motors_off.setFixedHeight(40)
        self.btn_motors_off.clicked.connect(lambda checked: self.send_gcode("M84"))
        service_layout.addWidget(self.btn_leveling)
        service_layout.addWidget(self.btn_motors_off)
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
            
            QPushButton[text^="X"] { border-left: 3px solid #ff4444; }
            QPushButton[text^="Y"] { border-left: 3px solid #44ff44; }
            QPushButton[text^="Z"] { border-left: 3px solid #4444ff; }
            
            QLineEdit { background-color: #121212; border: 1px solid #333; border-radius: 4px; color: #fff; padding: 4px; }
            QLineEdit:focus { border: 1px solid #ff9800; }
        """)
        for b in [self.btn_x_plus, self.btn_x_minus, self.btn_y_plus, self.btn_y_minus, self.btn_home_xy]:
            b.setFixedSize(65, 45)
        for b in [self.btn_z_plus, self.btn_z_minus, self.btn_z_home]:
            b.setFixedSize(80, 45)
        self.btn_leveling.setStyleSheet("border-bottom: 2px solid #ffeb3b; color: #ffeb3b;")

    def _update_step(self, val_str):
        self.current_step = float(val_str)
        for v, btn in self.step_buttons.items(): btn.setChecked(v == val_str)

    def _send_custom_gcode(self):
        cmd = self.inp_gcode.text().strip()
        if cmd: self.send_gcode(cmd); self.inp_gcode.clear()

    def move(self, axis, direction):
        gcode = f"G91\nG0 {axis}{self.current_step * direction:.2f} F3000\nG90"
        self.send_gcode(gcode)

    def send_gcode(self, gcode):
        if self.worker:
            for line in gcode.split('\n'): self.worker.send_command(line)
