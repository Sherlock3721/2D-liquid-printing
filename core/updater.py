import os
import sys
import time
import json
import urllib.request
import tempfile
import stat
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal
try:
    from packaging import version
except ImportError:
    # Fallback for simple version comparison if packaging is not available
    version = None

class AutoUpdater(QThread):
    update_available = pyqtSignal(str, str) # version, asset_url
    progress = pyqtSignal(int)
    update_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, current_version, repo_owner="Sherlock3721", repo_name="2D-liquid-printing", github_token=None):
        super().__init__()
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = github_token
        self._mode = "check" # 'check' or 'download'
        self.download_url = None

    def check_for_updates(self):
        self._mode = "check"
        if not self.isRunning():
            self.start()

    def download_and_prepare(self, url):
        self.download_url = url
        self._mode = "download"
        if not self.isRunning():
            self.start()

    def run(self):
        if self._mode == "check":
            self._do_check()
        elif self._mode == "download":
            self._do_download()

    def _get_headers(self):
        headers = {'User-Agent': 'DPI-Updater'}
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        return headers

    def _do_check(self):
        api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
        try:
            req = urllib.request.Request(api_url, headers=self._get_headers())
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                tag_name = data.get("tag_name", "")
                if not tag_name:
                    self.error.emit("Na GitHubu nebyla nalezena žádná verze (release).")
                    return

                latest_version = tag_name.lstrip("v")
                
                is_newer = False
                if version:
                    is_newer = version.parse(latest_version) > version.parse(self.current_version)
                else:
                    # Very basic fallback comparison
                    is_newer = latest_version != self.current_version

                if is_newer:
                    # Zjistit správný asset pro daný OS
                    system = sys.platform
                    asset_url = None
                    assets = data.get("assets", [])
                    
                    if not assets:
                        self.error.emit(f"Verze {latest_version} nalezena, ale neobsahuje žádné soubory ke stažení.")
                        return

                    for asset in assets:
                        name = asset["name"].lower()
                        if system.startswith("win"):
                            if name.endswith(".exe"):
                                asset_url = asset["browser_download_url"]
                                break
                        elif system.startswith("linux"):
                            # Flexibilnější detekce pro Linux
                            if "linux" in name or name == "main" or name == "gcode-editor" or asset["name"].endswith(".AppImage"):
                                asset_url = asset["browser_download_url"]
                                break
                        elif system == "darwin":
                            if "mac" in name or "darwin" in name or name.endswith(".dmg"):
                                asset_url = asset["browser_download_url"]
                                break
                    
                    # Fallback: pokud je jen jeden asset, zkusíme ho použít
                    if not asset_url and len(assets) == 1:
                        asset_url = assets[0]["browser_download_url"]

                    if asset_url:
                        self.update_available.emit(latest_version, asset_url)
                    else:
                        self.error.emit(f"Nová verze {latest_version} je k dispozici, ale nebyl nalezen vhodný soubor pro váš systém ({system}).")
                else:
                    self.error.emit("Používáte nejnovější verzi.")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.error.emit("Repositář nebo release nebyl nalezen. Ujistěte se, že je repositář veřejný nebo je nastaven správný token.")
            else:
                self.error.emit(f"Chyba HTTP při kontrole aktualizací ({e.code}): {e.reason}")
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

            # Pro soukromé repositáře musíme použít Request s headery i pro stahování assetu,
            # ale browser_download_url obvykle přesměrovává na S3, kde token nesmí být.
            # Nicméně urllib.request.urlretrieve token neumí.
            
            req = urllib.request.Request(self.download_url, headers=self._get_headers())
            with urllib.request.urlopen(req) as response, open(download_path, 'wb') as out_file:
                total_size = int(response.info().get('Content-Length', -1))
                downloaded = 0
                block_size = 8192
                while True:
                    block = response.read(block_size)
                    if not block:
                        break
                    downloaded += len(block)
                    out_file.write(block)
                    if total_size > 0:
                        self.progress.emit(int(downloaded * 100 / total_size))

            script_path = self._prepare_update_script(download_path)
            self.update_ready.emit(script_path)
            
        except Exception as e:
            self.error.emit(f"Chyba při stahování aktualizace: {e}")

    def _prepare_update_script(self, new_exe_path):
        current_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
        exe_name = os.path.basename(current_exe)
        temp_dir = tempfile.gettempdir()
        
        if sys.platform.startswith("win"):
            script_path = os.path.join(temp_dir, "gcode_editor_update.bat")
            # /timeout /t 3 zajistí, že se aplikace stihne ukončit
            bat_content = f"""@echo off
setlocal
echo Aktualizuji Droplet Printing Interface (DPI)...
echo Prosim cekejte, dokud se okno samo nezavre...

rem Pokusime se aplikaci ukoncet pokud bezi
taskkill /IM "{exe_name}" /F > NUL 2>&1
taskkill /IM main.exe /F > NUL 2>&1
taskkill /IM DPI.exe /F > NUL 2>&1

set "RETRY=0"
:loop
set /a RETRY+=1
if %RETRY% GTR 20 (
    echo CHYBA: Nepodarilo se nahradit soubor po 20 pokusech.
    pause
    exit /b 1
)

timeout /t 2 /nobreak > NUL
move /Y "{new_exe_path}" "{current_exe}"
if errorlevel 1 (
    echo Aplikace je stale blokovana, pokus %RETRY% z 20...
    goto loop
)

echo Aktualizace byla uspesna. Spoustim novou verzi...
start "" "{current_exe}"
endlocal
del "%~f0"
"""
            with open(script_path, "w", encoding="cp1250") as f:
                f.write(bat_content)
        else:
            script_path = os.path.join(temp_dir, "gcode_editor_update.sh")
            sh_content = f"""#!/bin/bash
echo "Aktualizuji Droplet Printing Interface (DPI)..."
sleep 3
mv -f "{new_exe_path}" "{current_exe}"
chmod +x "{current_exe}"
"{current_exe}" &
rm -- "$0"
"""
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(sh_content)
            st = os.stat(script_path)
            os.chmod(script_path, st.st_mode | stat.S_IEXEC)
            
        return script_path
