import json
import urllib.request
import urllib.parse
import urllib.error
import time
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, 
                             QTextEdit, QPushButton, QMessageBox, QLabel, QLineEdit)
from PyQt6.QtCore import QThread, pyqtSignal

# --- MATRIX NASTAVENÍ ---
MATRIX_SERVER = "https://matrix.7wave.cz"
ROOM_ID = "!OPln_hRT-9VZf4fCutS5wpsvdP_W5agt1rYSC31etis" # Použij tvé funkční ID
ACCESS_TOKEN = "KdJIOdCGfr1pg8XHIVgVXWicrZJt0FQN"
# ------------------------

class MatrixSenderThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, message_body):
        super().__init__()
        self.message_body = message_body

    def run(self):
        safe_room_id = urllib.parse.quote(ROOM_ID)
        txn_id = str(int(time.time() * 1000))
        url = f"{MATRIX_SERVER}/_matrix/client/v3/rooms/{safe_room_id}/send/m.room.message/{txn_id}"
        
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        data = {
            "msgtype": "m.text",
            "body": self.message_body
        }
        
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='PUT')
            with urllib.request.urlopen(req, timeout=10) as response:
                self.finished.emit(True, "Zpráva byla úspěšně odeslána.")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            self.finished.emit(False, f"HTTP Chyba {e.code}:\n{error_body}")
        except Exception as e:
            self.finished.emit(False, str(e))

class FeedbackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nahlásit chybu / Nápad")
        self.resize(400, 350)
        
        layout = QVBoxLayout(self)
        
        self.lbl_info = QLabel("Zpráva bude odeslána administrátorovi přes Matrix.")
        self.lbl_info.setStyleSheet("color: #aaa; font-style: italic;")
        layout.addWidget(self.lbl_info)
        
        form = QFormLayout()
        
        # Výběr typu
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Nahlášení chyby (Bug)", "Nápad na vylepšení (Wishlist)", "Dotaz"])
        self.cmb_type.currentTextChanged.connect(self.toggle_contact)
        form.addRow("Typ zprávy:", self.cmb_type)
        
        # Kontaktní pole (skryté ve výchozím stavu)
        self.lbl_contact = QLabel("E-mail / Telefon:")
        self.inp_contact = QLineEdit()
        form.addRow(self.lbl_contact, self.inp_contact)
        self.toggle_contact(self.cmb_type.currentText())
        
        layout.addLayout(form)
        
        # Zpráva
        self.txt_message = QTextEdit()
        self.txt_message.setPlaceholderText("Popište problém nebo nápad...")
        layout.addWidget(self.txt_message)
        
        # Odeslat
        self.btn_send = QPushButton("Odeslat zprávu")
        self.btn_send.clicked.connect(self.send_message)
        layout.addWidget(self.btn_send)

    def toggle_contact(self, text):
        is_query = (text == "Dotaz")
        self.lbl_contact.setVisible(is_query)
        self.inp_contact.setVisible(is_query)
        
    def send_message(self):
        text = self.txt_message.toPlainText().strip()
        msg_type = self.cmb_type.currentText()
        contact = self.inp_contact.text().strip()

        if not text:
            QMessageBox.warning(self, "Chyba", "Zpráva nesmí být prázdná.")
            return
            
        if msg_type == "Dotaz" and not contact:
            QMessageBox.warning(self, "Chyba", "Pro dotaz prosím vyplňte kontaktní údaje (e-mail nebo telefon).")
            return

        # Sestavení zprávy
        contact_str = f" (Kontakt: {contact})" if (msg_type == "Dotaz" and contact) else ""
        formatted_message = f"[{msg_type}]{contact_str}\n{text}"
        
        self.btn_send.setEnabled(False)
        self.btn_send.setText("Odesílám...")
        
        self.thread = MatrixSenderThread(formatted_message)
        self.thread.finished.connect(self.on_sent)
        self.thread.start()
        
    def on_sent(self, success, response_text):
        self.btn_send.setEnabled(True)
        self.btn_send.setText("Odeslat zprávu")
        
        if success:
            QMessageBox.information(self, "Odesláno", response_text)
            self.accept()
        else:
            QMessageBox.critical(self, "Chyba připojení", f"Zprávu se nepodařilo odeslat:\n{response_text}")
