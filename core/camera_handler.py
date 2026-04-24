try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class CameraHandler(QObject):
    frame_ready = pyqtSignal(object) # Vysílá numpy pole (frame)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.cap = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

    def start(self, index=None):
        if not OPENCV_AVAILABLE: return
        if self.running: self.stop()
        if index is not None:
            self.camera_index = index
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        if self.cap:
            self.cap.release()
            self.cap = None

    def _capture_loop(self):
        if not OPENCV_AVAILABLE: return
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"Chyba: Kameru s indexem {self.camera_index} nelze otevřít.")
            self.running = False
            return

        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_ready.emit(frame)
            else:
                time.sleep(0.1)
            
            time.sleep(0.03)

    @staticmethod
    def get_available_cameras():
        """Pokusí se najít dostupné indexy kamer."""
        if not OPENCV_AVAILABLE: return []
        available = []
        # Kontrola prvních 3 indexů (většinou stačí)
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
