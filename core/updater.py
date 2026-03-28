import os
import sys
import time
import json
import urllib.request
import tempfile
import stat
from PyQt6.QtCore import QThread, pyqtSignal
from packaging import version

class AutoUpdater(QThread):
    update_available = pyqtSignal(str, str) # version, asset_url
    progress = pyqtSignal(int)
    update_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, current_version, repo_owner="uzivatel", repo_name="gcode-editor"):
        super().__init__()
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self._mode = "check" # 'check' or 'download'
        self.download_url = None

    def check_for_updates(self):
        self._mode = "check"
        self.start()

    def download_and_prepare(self, url):
        self.download_url = url
        self._mode = "download"
        self.start()

    def run(self):
        if self._mode == "check":
            self._do_check()
        elif self._mode == "download":
            self._do_download()

    def _do_check(self):
        api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'GCode-Editor-Updater'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name", "").lstrip("v")
                
                if version.parse(latest_version) > version.parse(self.current_version):
                    # Zjistit správný asset pro daný OS
                    system = sys.platform
                    asset_url = None
                    for asset in data.get("assets", []):
                        name = asset["name"].lower()
                        if system.startswith("win") and name.endswith(".exe"):
                            asset_url = asset["browser_download_url"]
                            break
                        elif system.startswith("linux") and "linux" in name:
                            asset_url = asset["browser_download_url"]
                            break
                        elif system == "darwin" and ("mac" in name or "darwin" in name):
                            asset_url = asset["browser_download_url"]
                            break
                    
                    if asset_url:
                        self.update_available.emit(latest_version, asset_url)
        except Exception as e:
            self.error.emit(f"Chyba při kontrole aktualizací: {e}")

    def _do_download(self):
        try:
            temp_dir = tempfile.gettempdir()
            filename = self.download_url.split('/')[-1]
            download_path = os.path.join(temp_dir, filename)

            def report_hook(count, block_size, total_size):
                if total_size > 0:
                    percent = int(count * block_size * 100 / total_size)
                    self.progress.emit(min(100, percent))

            urllib.request.urlretrieve(self.download_url, download_path, reporthook=report_hook)
            
            script_path = self._prepare_update_script(download_path)
            self.update_ready.emit(script_path)
            
        except Exception as e:
            self.error.emit(f"Chyba při stahování aktualizace: {e}")

    def _prepare_update_script(self, new_exe_path):
        current_exe = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        temp_dir = tempfile.gettempdir()
        
        if sys.platform.startswith("win"):
            script_path = os.path.join(temp_dir, "gcode_editor_update.bat")
            bat_content = f"""@echo off
echo Aktualizuji Laboratorni 2D Tisk Kapalin...
echo Prosim cekejte...
timeout /t 3 /nobreak > NUL
move /Y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
"""
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
        else:
            script_path = os.path.join(temp_dir, "gcode_editor_update.sh")
            sh_content = f"""#!/bin/bash
echo "Aktualizuji Laboratorni 2D Tisk Kapalin..."
sleep 3
mv -f "{new_exe_path}" "{current_exe}"
chmod +x "{current_exe}"
"{current_exe}" &
rm -- "$0"
"""
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(sh_content)
            # Make script executable
            st = os.stat(script_path)
            os.chmod(script_path, st.st_mode | stat.S_IEXEC)
            
        return script_path
