try:
    import cv2
except ImportError:
    pass

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QComboBox
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, pyqtSlot
from core.camera_handler import CameraHandler, OPENCV_AVAILABLE

class CameraWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.handler = CameraHandler()
        self.handler.frame_ready.connect(self.update_frame)
        self.current_rotation = 0
        self._setup_ui()
        
        # Automatická detekce a start
        self._refresh_cameras()
        self._auto_start()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 10)
        self.main_layout.setSpacing(5)

        # Hlavička s výběrem a rotací
        header_lay = QHBoxLayout()
        self.lbl_title = QLabel("Kamera")
        self.lbl_title.setStyleSheet("font-weight: bold; color: #aaa;")
        
        self.btn_rotate = QPushButton("⟳")
        self.btn_rotate.setFixedSize(30, 24)
        self.btn_rotate.setToolTip("Otočit obraz o 90°")
        self.btn_rotate.clicked.connect(self._rotate_camera)
        
        self.cmb_source = QComboBox()
        self.cmb_source.setFixedWidth(110)
        self.cmb_source.currentIndexChanged.connect(self._on_source_changed)
        
        header_lay.addWidget(self.lbl_title)
        header_lay.addStretch()
        header_lay.addWidget(self.btn_rotate)
        header_lay.addWidget(self.cmb_source)
        self.main_layout.addLayout(header_lay)

        self.viewfinder = QLabel("Kamera vypnuta")
        self.viewfinder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewfinder.setMinimumSize(320, 180)
        self.viewfinder.setStyleSheet("background-color: #111; border: 1px solid #444; color: #555; border-radius: 4px;")
        self.main_layout.addWidget(self.viewfinder)

        btn_layout = QHBoxLayout()
        self.btn_toggle = QPushButton("Zapnout kameru")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.clicked.connect(self._toggle_camera)
        btn_layout.addWidget(self.btn_toggle)
        
        self.main_layout.addLayout(btn_layout)

        if not OPENCV_AVAILABLE:
            self.viewfinder.setText("Chybí knihovna OpenCV\n(pip install opencv-python)")
            self.btn_toggle.setEnabled(False)
            self.cmb_source.setEnabled(False)
            self.btn_rotate.setEnabled(False)

    def _refresh_cameras(self):
        """Zjistí dostupné kamery a naplní dropdown."""
        self.cmb_source.blockSignals(True)
        self.cmb_source.clear()
        cameras = CameraHandler.get_available_cameras()
        if not cameras:
            self.cmb_source.addItem("Nenalezena")
            self.viewfinder.setVisible(False)
            self.btn_toggle.setVisible(False)
            self.btn_rotate.setVisible(False)
        else:
            for idx in cameras:
                label = f"USB Kamera {idx}"
                if idx > 0: label += " (Ext.)"
                self.cmb_source.addItem(label, idx)
            
            # Prioritní volba: pokud existuje index > 0 (externí), vyber ho
            ext_idx = -1
            for i in range(self.cmb_source.count()):
                if self.cmb_source.itemData(i) > 0:
                    ext_idx = i
                    break
            if ext_idx != -1:
                self.cmb_source.setCurrentIndex(ext_idx)

            self.viewfinder.setVisible(True)
            self.btn_toggle.setVisible(True)
            self.btn_rotate.setVisible(True)
        self.cmb_source.blockSignals(False)

    def _auto_start(self):
        """Automaticky spustí kameru při startu aplikace."""
        if OPENCV_AVAILABLE and self.cmb_source.currentData() is not None and self.cmb_source.currentData() != -1:
            if self.cmb_source.currentText() != "Nenalezena":
                self.btn_toggle.setChecked(True)
                self._toggle_camera(True)

    def _rotate_camera(self):
        """Cyklicky mění rotaci obrazu."""
        self.current_rotation = (self.current_rotation + 90) % 360
        self.handler.set_rotation(self.current_rotation)

    def _on_source_changed(self):
        if self.btn_toggle.isChecked():
            self._toggle_camera(False)
            self.btn_toggle.setChecked(False)

    def _toggle_camera(self, checked):
        if not OPENCV_AVAILABLE: return
        if checked:
            idx = self.cmb_source.currentData()
            if idx is not None:
                self.handler.start(index=idx)
                self.btn_toggle.setText("Vypnout kameru")
                self.btn_toggle.setStyleSheet("background-color: #dc3545; color: white;")
        else:
            self.handler.stop()
            self.btn_toggle.setText("Zapnout kameru")
            self.btn_toggle.setStyleSheet("background-color: #0d6efd; color: white;")
            self.viewfinder.clear()
            self.viewfinder.setText("Kamera vypnuta")

    @pyqtSlot(object)
    def update_frame(self, frame):
        if frame is None or not self.viewfinder.isVisible(): return
        
        # Konverze BGR (OpenCV) na RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.viewfinder.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        self.viewfinder.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        self.handler.stop()
        super().closeEvent(event)
