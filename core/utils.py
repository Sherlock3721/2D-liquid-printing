import sys
import os

def get_resource_path(relative_path):
    """
    Získá absolutní cestu k prostředku, funguje pro vývoj i PyInstaller.
    PyInstaller při běhu z .exe rozbaluje data do dočasné složky sys._MEIPASS.
    """
    if getattr(sys, 'frozen', False):
        # Pokud aplikace běží jako .exe (frozen)
        base_path = sys._MEIPASS
    else:
        # Pokud běží z Pythonu
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    return os.path.join(base_path, relative_path)
