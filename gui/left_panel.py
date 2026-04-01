import serial.tools.list_ports
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QComboBox, 
                             QSpinBox, QDoubleSpinBox, QLineEdit, QLabel, 
                             QPushButton, QFrame, QProgressBar)
from PyQt6.QtCore import pyqtSignal
from printer_com import SerialPrinterWorker
from gui.settings import load_settings
from gui.feedback_dialog import FeedbackDialog

class LeftPanel(QWidget):
    values_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(350)
        
        self.settings = load_settings()
        self.sklo_dims = self.settings.get("sklo_dims", {})
        self.nozzle_defs = self.settings.get("nozzle_defs", {})

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # --- Tlačítko Načíst ---
        self.btn_load = QPushButton("Načíst vzorek (G-code/SVG/DXF)")
        main_layout.addWidget(self.btn_load)
        
        # --- Exportní tlačítka vedle sebe ---
        layout_export = QHBoxLayout()
        self.btn_save = QPushButton("Uložit G-code")
        self.btn_csv = QPushButton("Uložit CSV")
        self.btn_csv.setStyleSheet("QPushButton { background-color: #198754; } QPushButton:hover { background-color: #157347; }")
        
        layout_export.addWidget(self.btn_save)
        layout_export.addWidget(self.btn_csv)
        main_layout.addLayout(layout_export)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(line)
        
        # HLAVNÍ FORMULÁŘ
        self.form_layout = QFormLayout()
        
        # --- Podložka ---
        self.form_layout.addRow(QLabel("<b>--- Podložka ---</b>"))
        
        self.cmb_holder = QComboBox()
        self.cmb_holder.addItems(["Na jeden vzorek", "Multiplex (více sklíček)"])
        self.form_layout.addRow("Typ držáku:", self.cmb_holder)
        
        self.cmb_glass = QComboBox()
        self.cmb_glass.addItems(list(self.sklo_dims.keys()))
        self.form_layout.addRow("Sklíčko:", self.cmb_glass)
        
        # --- Skrytý řádek pro vlastní rozměry ---
        self.widget_vlastni_sklo = QWidget()
        layout_vlastni_sklo = QHBoxLayout(self.widget_vlastni_sklo)
        layout_vlastni_sklo.setContentsMargins(0, 0, 0, 0)
        self.inp_glass_x = QLineEdit("25.0")
        self.inp_glass_y = QLineEdit("75.0")
        self.inp_glass_z = QLineEdit("2.0")
        layout_vlastni_sklo.addWidget(QLabel("Šířka:")); layout_vlastni_sklo.addWidget(self.inp_glass_x)
        layout_vlastni_sklo.addWidget(QLabel("Výška:")); layout_vlastni_sklo.addWidget(self.inp_glass_y)
        layout_vlastni_sklo.addWidget(QLabel("Tloušťka:")); layout_vlastni_sklo.addWidget(self.inp_glass_z)
        layout_vlastni_sklo.addWidget(QLabel("mm"))
        self.form_layout.addRow(self.widget_vlastni_sklo)
        self.widget_vlastni_sklo.setVisible(False)

        self.inp_count = QSpinBox()
        self.inp_count.setRange(1, 50); self.inp_count.setValue(1)
        self.form_layout.addRow("Počet vzorků:", self.inp_count)
        
        self.inp_bed_temp = QSpinBox()
        self.inp_bed_temp.setRange(0, 100); self.inp_bed_temp.setSingleStep(1); self.inp_bed_temp.setValue(0)
        self._last_bed_temp = 0
        self.inp_bed_temp.setSpecialValueText("vypnuto"); self.inp_bed_temp.setSuffix(" °C")
        self.inp_bed_temp.valueChanged.connect(self._handle_bed_temp_change)
        self.form_layout.addRow("Výhřev podložky:", self.inp_bed_temp)

        # --- ODPLIV (PRIMING) ---
        self.btn_prime = QPushButton("Odpliv AKTIVNÍ")
        self.btn_prime.setCheckable(True); self.btn_prime.setChecked(True)
        self.btn_prime.clicked.connect(self._update_prime_style)
        self.form_layout.addRow("Příprava trysky:", self.btn_prime)
        # Poznámka: _update_prime_style() zavoláme po inicializaci všech widgetů

        # --- Parametry tisku ---
        self.form_layout.addRow(QLabel("<b>--- Tiskové parametry ---</b>"))
        self.lbl_total_z = QLabel("0.00 mm"); self.lbl_total_z.setStyleSheet("color: #17a2b8; font-weight: bold;")
        self.form_layout.addRow("Absolutní Z tiskárny:", self.lbl_total_z)

        self.inp_z_offset = QDoubleSpinBox()
        self.inp_z_offset.setRange(0.0, 5.0); self.inp_z_offset.setSingleStep(0.05); self.inp_z_offset.setValue(0.2)
        self.form_layout.addRow("Z-offset vrstvy [mm]:", self.inp_z_offset)
        
        self.inp_extrusion = QDoubleSpinBox()
        self.inp_extrusion.setRange(0.001, 100.0); self.inp_extrusion.setSingleStep(0.1); self.inp_extrusion.setDecimals(3); self.inp_extrusion.setValue(1.0)
        self.form_layout.addRow("Extruze [µl/mm]:", self.inp_extrusion)
        
        self.cmb_nozzle = QComboBox()
        self.cmb_nozzle.addItems(list(self.nozzle_defs.keys()))
        self.form_layout.addRow("Typ trysky:", self.cmb_nozzle)

        self.widget_vlastni_tryska = QWidget()
        layout_vlastni_tryska = QHBoxLayout(self.widget_vlastni_tryska)
        layout_vlastni_tryska.setContentsMargins(0, 0, 0, 0)
        self.inp_nozzle_h = QDoubleSpinBox(); self.inp_nozzle_h.setRange(0, 100); self.inp_nozzle_h.setValue(30.0)
        self.inp_nozzle_d = QDoubleSpinBox(); self.inp_nozzle_d.setRange(0.01, 10.0); self.inp_nozzle_d.setValue(0.4)
        layout_vlastni_tryska.addWidget(QLabel("Výška:")); layout_vlastni_tryska.addWidget(self.inp_nozzle_h)
        layout_vlastni_tryska.addWidget(QLabel("Průměr:")); layout_vlastni_tryska.addWidget(self.inp_nozzle_d)
        self.form_layout.addRow(self.widget_vlastni_tryska)
        self.widget_vlastni_tryska.setVisible(False)

        main_layout.addLayout(self.form_layout)
        self.form_layout.addRow(QLabel("<b>--- Vektorové výplně ---</b>"))
        self.cmb_infill_style = QComboBox(); self.cmb_infill_style.addItems(["S okraji", "Bez okrajů", "Okraje", "Had", "Tečky"])
        self.form_layout.addRow("Styl výplně:", self.cmb_infill_style)
        self.widget_infill = QWidget()
        layout_infill = QHBoxLayout(self.widget_infill)
        layout_infill.setContentsMargins(0, 0, 0, 0)
        self.inp_infill_val = QDoubleSpinBox(); self.inp_infill_val.setRange(0.1, 200.0); self.inp_infill_val.setValue(1.0); self.inp_infill_val.setSingleStep(0.1)
        self.cmb_infill_type = QComboBox(); self.cmb_infill_type.addItems(["mm", "%"])
        layout_infill.addWidget(self.inp_infill_val); layout_infill.addWidget(self.cmb_infill_type)
        self.form_layout.addRow("Hustota výplně:", self.widget_infill)
        self.inp_infill_angle = QSpinBox(); self.inp_infill_angle.setRange(0, 90); self.inp_infill_angle.setValue(0)
        self.form_layout.addRow("Úhel výplně [°]:", self.inp_infill_angle)
        main_layout.addStretch()

        # --- Ovládání tiskárny ---
        printer_layout = QFormLayout()
        printer_layout.addRow(QLabel("<b>--- Ovládání tiskárny ---</b>"))
        self.lbl_status = QLabel("Stav: Odpojeno"); printer_layout.addRow(self.lbl_status)
        
        # Výběr portu
        layout_port = QHBoxLayout()
        self.cmb_port = QComboBox()
        self.cmb_port.addItem("Automaticky")
        self.btn_refresh_ports = QPushButton("🔄")
        self.btn_refresh_ports.setFixedWidth(30)
        self.btn_refresh_ports.clicked.connect(self._refresh_ports)
        layout_port.addWidget(self.cmb_port)
        layout_port.addWidget(self.btn_refresh_ports)
        printer_layout.addRow("Port:", layout_port)
        self._refresh_ports()
        
        # Výběr Baudrate
        self.cmb_baud = QComboBox()
        self.cmb_baud.addItems(["115200", "250000", "57600", "9600"])
        self.cmb_baud.setCurrentText("115200")
        printer_layout.addRow("Rychlost (Baud):", self.cmb_baud)

        self.btn_connect = QPushButton("Připojit tiskárnu"); self.btn_connect.setStyleSheet("background-color: #0d6efd; color: white;"); main_layout.addWidget(self.btn_connect)
        self.btn_start_print = QPushButton("Start tisku"); self.btn_start_print.setStyleSheet("background-color: #198754; color: white;"); self.btn_start_print.hide(); main_layout.addWidget(self.btn_start_print)
        self.print_controls_widget = QWidget()
        layout_print_controls = QHBoxLayout(self.print_controls_widget); layout_print_controls.setContentsMargins(0, 0, 0, 0)
        self.btn_pause = QPushButton("Pozastavit"); self.btn_pause.setStyleSheet("background-color: #ffc107; color: black;")
        self.btn_stop = QPushButton("Zastavit"); self.btn_stop.setStyleSheet("background-color: #dc3545; color: white;")
        layout_print_controls.addWidget(self.btn_pause); layout_print_controls.addWidget(self.btn_stop); self.print_controls_widget.hide(); main_layout.addWidget(self.print_controls_widget)
        self.progress = QProgressBar(); self.progress.setValue(0); printer_layout.addRow(self.progress)
        main_layout.addLayout(printer_layout)
        self.btn_feedback = QPushButton("Nahlásit chybu / Nápad"); self.btn_feedback.setStyleSheet("background-color: #ffc107; color: black;"); self.btn_feedback.clicked.connect(self.open_feedback); main_layout.addWidget(self.btn_feedback)

        # --- Propojení událostí ---
        self._update_prime_style()
        self.cmb_holder.currentIndexChanged.connect(self._toggle_bed_heating)
        self.cmb_glass.currentIndexChanged.connect(self._toggle_custom_glass)
        self.cmb_nozzle.currentIndexChanged.connect(self._toggle_custom_nozzle)
        
        inputs = [self.cmb_holder, self.cmb_glass, self.cmb_nozzle, self.inp_count, self.inp_bed_temp, self.inp_z_offset, 
                  self.inp_extrusion, self.inp_nozzle_h, self.inp_nozzle_d, self.cmb_infill_style, 
                  self.inp_infill_val, self.cmb_infill_type, self.inp_infill_angle, self.btn_prime]
        for widget in inputs:
            if isinstance(widget, QComboBox): widget.currentIndexChanged.connect(self.values_changed.emit)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)): widget.valueChanged.connect(self.values_changed.emit)
            elif isinstance(widget, QPushButton): widget.clicked.connect(self.values_changed.emit)
                
        line_inputs = [self.inp_glass_x, self.inp_glass_y, self.inp_glass_z]
        for widget in line_inputs: widget.textChanged.connect(self.values_changed.emit)

        self._toggle_bed_heating()
        self._toggle_custom_glass()
        self._toggle_custom_nozzle()

        self.worker = SerialPrinterWorker()
        self.worker.status_changed.connect(self.update_status); self.worker.progress_changed.connect(self.progress.setValue)
        self.btn_connect.clicked.connect(self.toggle_connection); self.btn_stop.clicked.connect(self.stop_print); self.btn_pause.clicked.connect(self.toggle_pause)
        
        self.values_changed.connect(self._aktualizovat_limit_vzorku)
        self.values_changed.connect(self._update_total_z)
        self._aktualizovat_limit_vzorku() 
        self._update_total_z()

    def _update_prime_style(self):
        if self.btn_prime.isChecked():
            self.btn_prime.setText("Odpliv AKTIVNÍ")
            self.btn_prime.setStyleSheet("background-color: #0d6efd; color: white;")
        else:
            self.btn_prime.setText("Odpliv VYPNUTÝ")
            self.btn_prime.setStyleSheet("background-color: #444; color: #888;")

    def _toggle_custom_glass(self):
        is_custom = self.cmb_glass.currentText() == "Vlastní"
        self.widget_vlastni_sklo.setVisible(is_custom)
        self.values_changed.emit()
        
    def _toggle_custom_nozzle(self):
        is_custom = self.cmb_nozzle.currentText() == "Vlastní"
        self.widget_vlastni_tryska.setVisible(is_custom)
        self.values_changed.emit()
        
    def _toggle_bed_heating(self):
        is_multiplex = self.cmb_holder.currentText() == "Multiplex (více sklíček)"
        self.inp_bed_temp.setVisible(is_multiplex)
        label = self.form_layout.labelForField(self.inp_bed_temp)
        if label: label.setVisible(is_multiplex)
        if not is_multiplex: self.inp_bed_temp.setValue(0)
            
    def _handle_bed_temp_change(self, val):
        if 0 < val < 30:
            self.inp_bed_temp.blockSignals(True)
            if val > getattr(self, '_last_bed_temp', 0): self.inp_bed_temp.setValue(30)
            else: self.inp_bed_temp.setValue(0)
            self.inp_bed_temp.blockSignals(False)
        self._last_bed_temp = self.inp_bed_temp.value()
        self.values_changed.emit()
            
    def _refresh_ports(self):
        """Aktualizuje seznam dostupných COM portů."""
        current_selection = self.cmb_port.currentText()
        self.cmb_port.blockSignals(True)
        self.cmb_port.clear()
        self.cmb_port.addItem("Automaticky")
        
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            self.cmb_port.addItem(p.device)
            
        if current_selection in [self.cmb_port.itemText(i) for i in range(self.cmb_port.count())]:
            self.cmb_port.setCurrentText(current_selection)
        self.cmb_port.blockSignals(False)

    def update_status(self, msg):
        self.lbl_status.setText(f"Stav: {msg}")
        if msg == "Připojeno" or msg in ("Tisk dokončen", "Tisk zrušen"):
            self.lbl_status.setStyleSheet("color: #198754; font-weight: bold;"); self.set_ui_connected()
        elif "Chyba" in msg or msg == "Odpojeno":
            self.lbl_status.setStyleSheet("color: #dc3545; font-weight: bold;"); self.set_ui_disconnected()
            
    def toggle_connection(self):
        if self.worker.serial_conn and self.worker.serial_conn.is_open:
            self.worker.stop()
            if self.worker.serial_conn:
                self.worker.serial_conn.close()
                self.worker.serial_conn = None
            self.update_status("Odpojeno")
        else:
            selected_port = self.cmb_port.currentText()
            if selected_port == "Automaticky":
                self.worker.connect_printer(None)
            else:
                self.worker.connect_printer(selected_port)

    def open_feedback(self):
        dialog = FeedbackDialog(self); dialog.exec()

    def stop_print(self):
        self.worker.stop(); self.progress.setValue(0); self.set_ui_connected()

    def get_all_params(self):
        self.settings = load_settings()
        self.nozzle_defs = self.settings.get("nozzle_defs", {})
        glass_type = self.cmb_glass.currentText()
        if glass_type == "Vlastní":
            try: slide_w = float(self.inp_glass_x.text()); slide_h = float(self.inp_glass_y.text()); slide_z = float(self.inp_glass_z.text())
            except ValueError: slide_w, slide_h, slide_z = 25.0, 75.0, 1.0
        else: slide_w, slide_h, slide_z = self.sklo_dims.get(glass_type, [25.0, 75.0, 1.0])
        nozzle_type = self.cmb_nozzle.currentText()
        if nozzle_type == "Vlastní": nozzle_h = self.inp_nozzle_h.value(); nozzle_d = self.inp_nozzle_d.value()
        else: nozzle_h, nozzle_d = self.nozzle_defs.get(nozzle_type, [30.0, 0.4])
        return {
            'holder_type': self.cmb_holder.currentText(), 'glass_type': glass_type, 'slide_w': slide_w, 'slide_h': slide_h, 'slide_z': slide_z,
            'sample_count': self.inp_count.value(), 'z_offset': self.inp_z_offset.value(), 'extrusion_rate': self.inp_extrusion.value(),
            'nozzle_type': nozzle_type, 'nozzle_diam': nozzle_d, 'nozzle_height': nozzle_h,
            'print_speed': self.settings.get("print_speed", 1500), 'retraction': self.settings.get("retraction", 1.0),
            'bed_temp': self.inp_bed_temp.value(), 'infill_style': self.cmb_infill_style.currentText(),
            'infill_val': self.inp_infill_val.value(), 'infill_type': self.cmb_infill_type.currentText(),
            'infill_angle': self.inp_infill_angle.value(), 'prime_active': self.btn_prime.isChecked()
        }

    def get_vector_params(self):
        params = self.get_all_params(); params['margin'] = 1.5; return params

    def set_ui_disconnected(self):
        self.btn_connect.setText("Připojit tiskárnu"); self.btn_connect.setStyleSheet("background-color: #0d6efd; color: white;"); self.btn_start_print.hide(); self.print_controls_widget.hide()
        self.cmb_port.setEnabled(True); self.btn_refresh_ports.setEnabled(True)
        self.cmb_baud.setEnabled(True)

    def set_ui_connected(self):
        self.btn_connect.setText("Odpojit tiskárnu"); self.btn_connect.setStyleSheet("background-color: #6c757d; color: white;"); self.btn_start_print.show(); self.print_controls_widget.hide()
        self.cmb_port.setEnabled(False); self.btn_refresh_ports.setEnabled(False)
        self.cmb_baud.setEnabled(False)

    def set_ui_printing(self):
        self.btn_start_print.hide(); self.print_controls_widget.show()

    def _aktualizovat_limit_vzorku(self):
        params = self.get_all_params()
        if params['holder_type'] == "Na jeden vzorek": self.inp_count.setMaximum(50); return
        slide_w = params['slide_w']; slide_h = params['slide_h']
        if slide_w <= 0 or slide_h <= 0: return
        bed_x = self.settings.get("bed_max_x", 250.0); bed_y = self.settings.get("bed_max_y", 210.0)
        spacing = self.settings.get("multi_spacing", 5.0); start_x = self.settings.get("start_offset_x", 10.0); start_y = self.settings.get("start_offset_y", 10.0)
        max_count = 0; curr_x = bed_x - start_x - slide_w; curr_y = start_y
        while True:
            if curr_y + slide_h > bed_y and max_count > 0: curr_x -= (slide_w + spacing); curr_y = start_y
            if curr_x < 0: break
            max_count += 1; curr_y += (slide_h + spacing)
            if max_count > 500: break 
        self.inp_count.setMaximum(max(1, max_count))

    def toggle_pause(self):
        if not hasattr(self.worker, 'toggle_pause'): return
        is_paused = self.worker.toggle_pause()
        if is_paused: self.btn_pause.setText("Pokračovat"); self.btn_pause.setStyleSheet("background-color: #17a2b8; color: white;")
        else: self.btn_pause.setText("Pozastavit"); self.btn_pause.setStyleSheet("background-color: #ffc107; color: black;")

    def _update_total_z(self):
        self.settings = load_settings(); correction_z = self.settings.get("correction_z", 0.0)
        params = self.get_all_params()
        holder_type = params.get('holder_type', 'Na jeden vzorek')
        holder_z = 4.0 if holder_type == "Na jeden vzorek" else 0.0
        slide_z = params.get('slide_z', 1.0); layer_z = params.get('z_offset', 0.2)
        total_z = holder_z + slide_z + layer_z + correction_z
        self.lbl_total_z.setText(f"{total_z:.2f} mm")

    def refresh_settings(self):
        """Znovu načte seznamy skel a trysek z nastavení."""
        self.settings = load_settings()
        self.sklo_dims = self.settings.get("sklo_dims", {})
        self.nozzle_defs = self.settings.get("nozzle_defs", {})
        
        # Aktualizace ComboBoxů při zachování vybrané hodnoty pokud existuje
        curr_glass = self.cmb_glass.currentText()
        self.cmb_glass.blockSignals(True)
        self.cmb_glass.clear()
        self.cmb_glass.addItems(list(self.sklo_dims.keys()))
        if curr_glass in self.sklo_dims:
            self.cmb_glass.setCurrentText(curr_glass)
        self.cmb_glass.blockSignals(False)
        
        curr_nozzle = self.cmb_nozzle.currentText()
        self.cmb_nozzle.blockSignals(True)
        self.cmb_nozzle.clear()
        self.cmb_nozzle.addItems(list(self.nozzle_defs.keys()))
        if curr_nozzle in self.nozzle_defs:
            self.cmb_nozzle.setCurrentText(curr_nozzle)
        self.cmb_nozzle.blockSignals(False)
        
        self._aktualizovat_limit_vzorku()
        self._update_total_z()
