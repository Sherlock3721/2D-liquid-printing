import time
import serial
import serial.tools.list_ports
import re
from PyQt6.QtCore import QThread, pyqtSignal

class SerialPrinterWorker(QThread):
    status_changed = pyqtSignal(str)
    temp_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)
    pos_changed = pyqtSignal(float, float, bool)

    def __init__(self, baudrate=115200):
        super().__init__()
        self.port = None
        self.baudrate = baudrate
        self.serial_conn = None
        self.gcode_lines = []
        self.is_printing = False
        self.running = False
        self.is_paused = False

    def connect_printer(self, manual_port=None):
        """Pokusí se připojit k tiskárně (automaticky nebo na zvolený port)."""
        if manual_port:
            # Vytvoříme pomocný objekt pro kompatibilitu s cyklem
            class DummyPort: pass
            p = DummyPort(); p.device = manual_port
            ports = [p]
        else:
            ports = list(serial.tools.list_ports.comports())
            
        if not ports:
            self.status_changed.emit("Chyba: Žádné porty nenalezeny")
            return False

        for p in ports:
            try:
                self.port = p.device
                self.status_changed.emit(f"Prověřuji {self.port}...")
                
                # Otevřeme port. timeout=2 je důležitý pro readline
                self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=2, write_timeout=2)
                
                # 1. Počkej, až se tiskárna vzpamatuje z resetu (DTR/RTS)
                time.sleep(2.5)
                self.serial_conn.reset_input_buffer()
                
                # 2. Zkus poslat M115 a čekej na odpověď
                self.serial_conn.write(b"\nM115\n")
                
                start_time = time.time()
                verified = False
                
                # Budeme číst řádky po dobu 3 sekund
                while time.time() - start_time < 3:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode('utf-8', errors='ignore').lower()
                        if any(x in line for x in ["ok", "marlin", "prusa", "cap:", "start", "echo:"]):
                            verified = True
                            break
                    time.sleep(0.1)
                
                if verified:
                    self.status_changed.emit("Připojeno")
                    return True
                else:
                    self.serial_conn.close()
                    self.serial_conn = None
            except Exception as e:
                print(f"Chyba na portu {p.device}: {e}")
                if self.serial_conn: self.serial_conn.close()
                self.serial_conn = None
                continue

        self.status_changed.emit("Chyba: Tiskárna neodpovídá")
        return False

    def print_file(self, filepath):
        self.gcode_lines = []
        with open(filepath, 'r') as f:
            for line in f:
                clean_line = line.split(';')[0].strip()
                if clean_line:
                    self.gcode_lines.append(clean_line)
                    
        self.is_printing = True
        self.running = True
        self.is_paused = False
        self.start()

    def run(self):
        total_lines = len(self.gcode_lines)
        if total_lines == 0: return
        
        cur_x, cur_y, last_e = 0.0, 0.0, 0.0
        
        for i, line in enumerate(self.gcode_lines):
            # 1. Zvládnutí pauzy
            while self.is_paused and self.running:
                time.sleep(0.5) # Vlákno spí, dokud uživatel neklikne na Pokračovat
                
            # 2. Zvládnutí Stopky
            if not self.running:
                break
                
            # 3. Odeslání příkazu
            try:
                self.serial_conn.write((line + '\n').encode('utf-8'))
            except serial.SerialException:
                self.status_changed.emit("Chyba zápisu: Přerušeno spojení")
                break
            
            # 4. Aktualizace 3D Náhledu Trysky
            is_extruding = False
            if line.startswith('G0') or line.startswith('G1'):
                mx = re.search(r'X([0-9\.\-]+)', line)
                my = re.search(r'Y([0-9\.\-]+)', line)
                me = re.search(r'E([0-9\.\-]+)', line)
                
                if mx: cur_x = float(mx.group(1))
                if my: cur_y = float(my.group(1))
                if me: 
                    current_e = float(me.group(1))
                    if current_e > last_e: is_extruding = True
                    last_e = current_e
                    
                self.pos_changed.emit(cur_x, cur_y, is_extruding)

            # 5. Čekání na potvrzení (Ping-Pong)
            while self.running:
                try:
                    response = self.serial_conn.readline().decode('utf-8').strip()
                    
                    if not response:
                        continue # Pokud je tiskárna ticho (např. nahřívá se), čekáme dál
                        
                    if response.startswith("T:") or "B:" in response:
                        self.temp_changed.emit(response)
                        
                    elif "ok" in response.lower():
                        break # Tiskárna příkaz zpracovala, můžeme poslat další
                        
                except Exception:
                    self.running = False
                    break        
                    
            # 6. Aktualizace ukazatele průběhu
            if i % 5 == 0 or i == total_lines - 1:
                self.progress_changed.emit(int((i / total_lines) * 100))

        self.is_printing = False
        if self.running:
            self.status_changed.emit("Tisk dokončen")
        self.running = False

    def toggle_pause(self):
        """Zapne nebo vypne pauzu."""
        self.is_paused = not getattr(self, 'is_paused', False)
        
        if self.serial_conn and self.serial_conn.is_open:
            if self.is_paused:
                self.serial_conn.write(b"M601\n") # Prusa: Pozastavit tisk
            else:
                self.serial_conn.write(b"M602\n") # Prusa: Pokračovat v tisku
                
        return self.is_paused

    def send_command(self, gcode):
        """Odešle jeden G-kód příkaz přímo do tiskárny."""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write((gcode + '\n').encode('utf-8'))
                return True
            except Exception as e:
                print(f"Chyba při odesílání příkazu: {e}")
        return False

    def stop(self):
        """Okamžitě zastaví probíhající tisk bez odpojení tiskárny."""
        self.running = False # Vypne posílání G-kódů ve vlákně
        self.is_printing = False
        self.is_paused = False
        
        if self.serial_conn and self.serial_conn.is_open:
            # 1. Okamžitý stop motorů a vymazání vnitřního bufferu tiskárny
            self.serial_conn.write(b"M410\n") 
            time.sleep(0.5)
            
            # 2. Bezpečný odjezd hlavy nahoru a odsunutí podložky
            safe_stop_gcode = (
                "G91\n"          # Relativní souřadnice
                "G0 Z15 F1000\n" # Vyjet 15 mm nahoru
                "G90\n"          # Absolutní souřadnice
                "G0 X10 Y200 F5000\n" # Podložka dopředu k uživateli
            )
            self.serial_conn.write(safe_stop_gcode.encode('utf-8'))
            
        self.status_changed.emit("Tisk zrušen")
