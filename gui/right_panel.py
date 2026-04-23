from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QToolButton, 
                             QPushButton, QComboBox, QHBoxLayout, QLabel, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from gui.manual_movement import ManualMovementWidget

class CollapsibleBox(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QToolButton(text=title, checkable=True, checked=False)
        self.toggle_button.setStyleSheet("QToolButton { border: none; font-weight: bold; color: #0d6efd; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)

        self.content_area = QWidget()
        self.content_area.setVisible(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 5)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)

    def on_pressed(self):
        checked = not self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.content_area.setVisible(checked)

class RightPanel(QWidget):
    values_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(5, 5, 5, 5)

        # --- SEKCE RUČNÍHO OVLÁDÁNÍ ---
        # Získáme printer_worker (předpokládáme, že je dostupný v parent.left_panel.worker)
        printer_worker = parent.left_panel.worker if parent and hasattr(parent, 'left_panel') else None
        
        self.manual_box = CollapsibleBox("RUČNÍ OVLÁDÁNÍ POSUVU", self)
        self.manual_widget = ManualMovementWidget(printer_worker, self.manual_box.content_area)
        manual_layout = QVBoxLayout(self.manual_box.content_area)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.addWidget(self.manual_widget)
        
        main_layout.addWidget(self.manual_box)

        # --- SEZNAM SKLÍČEK (SCROLL) ---
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(scroll_area)

        self.slide_widgets = {}
        self.local_modifications = {} 
        self.current_count = 0
        self._is_syncing = False
        self.last_global_params = {}

    def update_slides(self, count, global_params):
        self.last_global_params = global_params
        if count != self.current_count:
            self.current_count = count
            for i in reversed(range(self.scroll_layout.count())):
                widget = self.scroll_layout.itemAt(i).widget()
                if widget: widget.deleteLater()
            self.slide_widgets.clear()

            self._is_syncing = True
            for i in range(count):
                if i not in self.local_modifications:
                    self.local_modifications[i] = {
                        'z_offset': False, 'extrusion_rate': False, 
                        'print_speed': False, 'infill_val': False, 'infill_type': False
                    }
                box = CollapsibleBox(f"Sklíčko {i + 1}")
                form = QFormLayout(box.content_area)
                btn_reset = QPushButton("Zrušit lokální změny")
                btn_reset.setStyleSheet("background-color: #6c757d; font-size: 9pt;")
                btn_reset.clicked.connect(lambda checked, idx=i: self.reset_slide(idx))
                inp_name = QLineEdit(); inp_name.setPlaceholderText(f"Sklíčko {i + 1}")
                inp_name.textChanged.connect(lambda text, b=box, idx=i: b.toggle_button.setText(text if text.strip() else f"Sklíčko {idx + 1}"))
                inp_note = QLineEdit(); inp_note.setPlaceholderText("Poznámka...")
                inp_z = QDoubleSpinBox(); inp_z.setRange(0.0, 5.0); inp_z.setSingleStep(0.05)
                
                # --- EXTRUZE S VÝBĚREM JEDNOTEK ---
                widget_ext = QWidget(); layout_ext = QHBoxLayout(widget_ext); layout_ext.setContentsMargins(0, 0, 0, 0)
                inp_ext = QDoubleSpinBox(); inp_ext.setRange(0.0001, 10000.0); inp_ext.setSingleStep(0.1); inp_ext.setDecimals(4)
                cmb_ext_units = QComboBox()
                self.ext_unit_options = {
                    "µl/mm": 1.0, "nl/mm": 0.001, "kroky/mm": 1.0
                }
                cmb_ext_units.addItems(list(self.ext_unit_options.keys()))
                layout_ext.addWidget(inp_ext); layout_ext.addWidget(cmb_ext_units)
                
                inp_speed = QSpinBox(); inp_speed.setRange(10, 10000); inp_speed.setSingleStep(100)
                widget_infill = QWidget(); layout_infill = QHBoxLayout(widget_infill); layout_infill.setContentsMargins(0, 0, 0, 0)
                inp_infill = QDoubleSpinBox(); inp_infill.setRange(0.1, 200.0); inp_infill.setSingleStep(0.1)
                cmb_infill_type = QComboBox(); cmb_infill_type.addItems(["mm", "%"])
                layout_infill.addWidget(inp_infill); layout_infill.addWidget(cmb_infill_type)
                
                # Napojení signálů
                inp_z.valueChanged.connect(lambda val, idx=i: self.mark_modified(idx, 'z_offset'))
                inp_ext.valueChanged.connect(lambda val, idx=i: self.mark_modified(idx, 'extrusion_rate'))
                cmb_ext_units.currentTextChanged.connect(lambda unit, idx=i: self._handle_ext_unit_change_local(idx, unit))
                inp_speed.valueChanged.connect(lambda val, idx=i: self.mark_modified(idx, 'print_speed'))
                inp_infill.valueChanged.connect(lambda val, idx=i: self.mark_modified(idx, 'infill_val'))
                cmb_infill_type.currentIndexChanged.connect(lambda val, idx=i: self.mark_modified(idx, 'infill_type'))
                
                form.addRow(btn_reset)
                form.addRow("Název:", inp_name); form.addRow("Poznámka:", inp_note); form.addRow("Z-offset [mm]:", inp_z)
                form.addRow("Extruze:", widget_ext); form.addRow("Rychlost [mm/min]:", inp_speed); form.addRow("Výplň:", widget_infill)
                self.scroll_layout.addWidget(box)
                self.slide_widgets[i] = {
                    'name': inp_name, 'note': inp_note, 'z_offset': inp_z, 'extrusion_rate': inp_ext, 'ext_units': cmb_ext_units,
                    'print_speed': inp_speed, 'infill_val': inp_infill, 'infill_type': cmb_infill_type, 'last_unit': "µl/mm"
                }
            self._is_syncing = False
        self.sync_globals(global_params)

    def _handle_ext_unit_change_local(self, idx, new_unit):
        """Přepočítá hodnotu extruze při změně jednotek u konkrétního sklíčka."""
        if idx not in self.slide_widgets: return
        data = self.slide_widgets[idx]
        old_unit = data.get('last_unit', "µl/mm")
        old_val = data['extrusion_rate'].value()
        
        # Načteme kalibrační faktor
        from gui.settings import load_settings
        import math
        settings = load_settings()
        filament_diam = settings.get('filament_diameter', 9.5)
        default_cal = 1.0 / (math.pi * ((filament_diam / 2.0) ** 2))
        cal_factor = settings.get("calibration_factor", default_cal)
        
        # Převod: stará hodnota -> µl/mm
        if old_unit == "kroky/mm":
            base_val = old_val / cal_factor
        else:
            base_val = old_val * self.ext_unit_options.get(old_unit, 1.0)
            
        # Převod: µl/mm -> nová hodnota
        if new_unit == "kroky/mm":
            new_val = base_val * cal_factor
            data['extrusion_rate'].setDecimals(1)
            data['extrusion_rate'].setSingleStep(0.1)
        else:
            new_val = base_val / self.ext_unit_options.get(new_unit, 1.0)
            data['extrusion_rate'].setDecimals(4)
            data['extrusion_rate'].setSingleStep(0.1)
        
        data['extrusion_rate'].blockSignals(True)
        data['extrusion_rate'].setValue(new_val)
        data['extrusion_rate'].blockSignals(False)
        data['last_unit'] = new_unit
        self.mark_modified(idx, 'extrusion_rate')

    def sync_globals(self, global_params):
        self._is_syncing = True
        
        # Načteme kalibrační faktor
        from gui.settings import load_settings
        import math
        settings = load_settings()
        filament_diam = settings.get('filament_diameter', 9.5)
        default_cal = 1.0 / (math.pi * ((filament_diam / 2.0) ** 2))
        cal_factor = settings.get("calibration_factor", default_cal)

        for i, widgets in self.slide_widgets.items():
            mods = self.local_modifications[i]
            if not mods['z_offset']: widgets['z_offset'].setValue(global_params.get('z_offset', 0.2))
            if not mods['extrusion_rate']: 
                # Synchronizace extruze (převod na aktuálně vybranou lokální jednotku)
                base_ext = global_params.get('extrusion_rate', 1.0) # Vždy v µl/mm (internal)
                current_unit = widgets['ext_units'].currentText()
                if current_unit == "kroky/mm":
                    widgets['extrusion_rate'].setDecimals(1)
                    widgets['extrusion_rate'].setSingleStep(0.1)
                    widgets['extrusion_rate'].setValue(base_ext * cal_factor)
                else:
                    factor = self.ext_unit_options.get(current_unit, 1.0)
                    widgets['extrusion_rate'].setDecimals(4)
                    widgets['extrusion_rate'].setSingleStep(0.1)
                    widgets['extrusion_rate'].setValue(base_ext / factor)
                widgets['last_unit'] = current_unit
            if not mods['print_speed']: widgets['print_speed'].setValue(global_params.get('print_speed', 1500))
            if not mods['infill_val']: widgets['infill_val'].setValue(global_params.get('infill_val', 1.0))
            if not mods['infill_type']: widgets['infill_type'].setCurrentText(global_params.get('infill_type', 'mm'))
        self._is_syncing = False

    def mark_modified(self, idx, param):
        if not self._is_syncing:
            self.local_modifications[idx][param] = True
            self.values_changed.emit()

    def reset_slide(self, idx):
        self.local_modifications[idx] = {
            'z_offset': False, 'extrusion_rate': False, 
            'print_speed': False, 'infill_val': False, 'infill_type': False
        }
        if self.last_global_params: 
            self.sync_globals(self.last_global_params)
        self.values_changed.emit()

    def get_overrides(self):
        overrides = {}
        
        # Načteme kalibrační faktor
        from gui.settings import load_settings
        import math
        settings = load_settings()
        filament_diam = settings.get('filament_diameter', 9.5)
        default_cal = 1.0 / (math.pi * ((filament_diam / 2.0) ** 2))
        cal_factor = settings.get("calibration_factor", default_cal)

        for i, data in self.slide_widgets.items():
            mods = self.local_modifications[i]
            slide_data = {'name': data['name'].text() or data['name'].placeholderText(), 'note': data['note'].text()}
            if mods['z_offset']: slide_data['z_offset'] = data['z_offset'].value()
            if mods['extrusion_rate']: 
                # Převod zpět na základní jednotku pro generátor
                unit = data['ext_units'].currentText()
                if unit == "kroky/mm":
                    slide_data['extrusion_rate'] = data['extrusion_rate'].value() / cal_factor
                else:
                    factor = self.ext_unit_options.get(unit, 1.0)
                    slide_data['extrusion_rate'] = data['extrusion_rate'].value() * factor
                slide_data['extrusion_unit'] = unit
            if mods['print_speed']: slide_data['print_speed'] = data['print_speed'].value()
            if mods['infill_val']: slide_data['infill_val'] = data['infill_val'].value()
            if mods['infill_type']: slide_data['infill_type'] = data['infill_type'].currentText()
            if slide_data: overrides[i] = slide_data
        return overrides
