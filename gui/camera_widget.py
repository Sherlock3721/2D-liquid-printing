import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, pyqtSlot
from core.camera_handler import CameraHandler

class CameraWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.handler = CameraHandler()
        self.handler.frame_ready.connect(self.update_frame)
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.lbl_title = QLabel("Záznam z kamery (USB)")
        self.lbl_title.setStyleSheet("font-weight: bold; color: #aaa;")
        layout.addWidget(self.lbl_title)

        self.viewfinder = QLabel("Kamera vypnuta")
        self.viewfinder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewfinder.setMinimumSize(320, 240)
        self.viewfinder.setStyleSheet("background-color: #111; border: 1px solid #444; color: #555;")
        layout.addWidget(self.viewfinder)

        btn_layout = QHBoxLayout()
        self.btn_toggle = QPushButton("Zapnout kameru")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.clicked.connect(self._toggle_camera)
        btn_layout.addWidget(self.btn_toggle)
        
        layout.addLayout(btn_layout)

    def _toggle_camera(self, checked):
        if checked:
            self.handler.start()
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
        if frame is None: return
        
        # Konverze BGR (OpenCV) na RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Škálování na velikost labelu při zachování poměru stran
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.viewfinder.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        self.viewfinder.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        self.handler.stop()
        super().closeEvent(event)
