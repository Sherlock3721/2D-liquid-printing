from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QPushButton, QLineEdit, QLabel, QWidget)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from gui.settings import load_settings
import os

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
        
        self._load_svg_icons()
        self._setup_ui()
        self._apply_styles()
        
        if self.worker:
            self.worker.status_changed.connect(self._handle_status_change)
            self._handle_status_change("") # Počáteční nastavení stavu

    def _load_svg_icons(self):
        """Načte ikony ze souboru manual_movement.svg a opraví barvy pro QSvgRenderer."""
        self.icons = {}
        svg_path = os.path.join(os.getcwd(), "svg", "manual_movement.svg")
        if not os.path.exists(svg_path):
            print(f"Varování: Soubor {svg_path} nebyl nalezen.")
            return

        try:
            import re
            from PyQt6.QtCore import QRectF
            
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_data = f.read()
            
            # 1. Vynucení viditelnosti (odstranění display:none)
            svg_data = re.sub(r'display\s*:\s*none', 'display:inline', svg_data)
            
            # 2. Fix barev: QSvgRenderer lépe zvládá atributy fill/stroke než inline styly
            # Najdeme všechny style="..." a zkusíme z nich vytáhnout barvy do samostatných atributů
            def fix_style(match):
                style_str = match.group(1)
                new_attrs = []
                for prop in ['fill', 'stroke', 'stroke-width', 'fill-opacity', 'stroke-opacity', 'opacity']:
                    m = re.search(f'{prop}:([^;]+)', style_str)
                    if m:
                        new_attrs.append(f'{prop}="{m.group(1).strip()}"')
                return " ".join(new_attrs)

            svg_data = re.sub(r'style="([^"]+)"', fix_style, svg_data)
            
            renderer = QSvgRenderer(svg_data.encode('utf-8'))
            icon_size = 128
            
            mapping = {
                "g4": "plus_x", "g3": "minus_x",
                "g9": "plus_y", "g5": "minus_y",
                "g13": "plus_z", "g7": "minus_z",
                "g17": "home_xy", "g11": "home_z"
            }
            
            for group_id, key in mapping.items():
                pixmap = QPixmap(icon_size, icon_size)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                # Použijeme explicitní QRectF pro zachování měřítka a barev
                renderer.render(painter, group_id, QRectF(0, 0, icon_size, icon_size))
                painter.end()
                self.icons[key] = QIcon(pixmap)
                
        except Exception as e:
            print(f"Chyba při renderování SVG ikon: {e}")

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
        self.btn_y_plus = QPushButton(); self.btn_y_minus = QPushButton()
        self.btn_x_plus = QPushButton(); self.btn_x_minus = QPushButton()
        self.btn_home_xy = QPushButton()
        
        # Aplikace ikon
        if "plus_x" in self.icons: self.btn_x_plus.setIcon(self.icons["plus_x"])
        if "minus_x" in self.icons: self.btn_x_minus.setIcon(self.icons["minus_x"])
        if "plus_y" in self.icons: self.btn_y_plus.setIcon(self.icons["plus_y"])
        if "minus_y" in self.icons: self.btn_y_minus.setIcon(self.icons["minus_y"])
        if "home_xy" in self.icons: self.btn_home_xy.setIcon(self.icons["home_xy"])
        
        for b in [self.btn_x_plus, self.btn_x_minus, self.btn_y_plus, self.btn_y_minus, self.btn_home_xy]:
            b.setFixedSize(65, 45)
            b.setIconSize(QSize(40, 40))

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
        
        self.btn_z_plus = QPushButton()
        self.btn_z_home = QPushButton()
        self.btn_z_minus = QPushButton()
        
        if "plus_z" in self.icons: self.btn_z_plus.setIcon(self.icons["plus_z"])
        if "minus_z" in self.icons: self.btn_z_minus.setIcon(self.icons["minus_z"])
        if "home_z" in self.icons: self.btn_z_home.setIcon(self.icons["home_z"])
        
        for b in [self.btn_z_plus, self.btn_z_minus, self.btn_z_home]:
            b.setFixedSize(80, 45)
            b.setIconSize(QSize(40, 40))
        
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
        """Deaktivuje ovládání během tisku nebo při odpojení."""
        printing = False
        connected = False
        if self.worker:
            printing = self.worker.is_printing
            connected = self.worker.serial_conn is not None and self.worker.serial_conn.is_open
        
        can_control = connected and not printing
        
        # Seznam widgetů, které chceme vypnout
        for btn in self.step_buttons.values(): btn.setEnabled(can_control)
        self.btn_x_plus.setEnabled(can_control); self.btn_x_minus.setEnabled(can_control)
        self.btn_y_plus.setEnabled(can_control); self.btn_y_minus.setEnabled(can_control)
        self.btn_z_plus.setEnabled(can_control); self.btn_z_minus.setEnabled(can_control)
        self.btn_home_xy.setEnabled(can_control); self.btn_z_home.setEnabled(can_control)
        self.btn_go_abs.setEnabled(can_control); self.btn_send_gcode.setEnabled(can_control)
        self.btn_leveling.setEnabled(can_control); self.btn_motors.setEnabled(can_control)
        self.inp_abs_x.setEnabled(can_control); self.inp_abs_y.setEnabled(can_control)
        self.inp_abs_z.setEnabled(can_control); self.inp_gcode.setEnabled(can_control)

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
