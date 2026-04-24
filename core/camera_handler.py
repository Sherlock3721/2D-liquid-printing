import cv2
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

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.cap:
            self.cap.release()
            self.cap = None

    def _capture_loop(self):
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
                time.sleep(0.1) # Krátká pauza při chybě čtení
            
            # FPS omezení na cca 30
            time.sleep(0.03)

    def get_available_cameras(self):
        """Pokusí se najít dostupné indexy kamer."""
        available = []
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
