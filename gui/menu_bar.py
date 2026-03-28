from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMessageBox
from gui.feedback_dialog import FeedbackDialog
from gui.settings import SettingsDialog # PŘIDÁNO: Import nového okna

def create_main_menu(main_window):
    menu_bar = main_window.menuBar()

    # --- SOUBOR ---
    menu_file = menu_bar.addMenu("Soubor")
    
    action_load = QAction("Načíst vzorek", main_window)
    action_load.setShortcut("Ctrl+O")
    action_load.triggered.connect(main_window.load_file)
    menu_file.addAction(action_load)

    action_save = QAction("Vygenerovat a uložit", main_window)
    action_save.setShortcut("Ctrl+S")
    action_save.triggered.connect(main_window.save_file)
    menu_file.addAction(action_save)

    action_csv = QAction("Uložit protokol jako CSV", main_window)
    action_csv.triggered.connect(main_window.export_csv)
    menu_file.addAction(action_csv)

    menu_file.addSeparator()

    action_quit = QAction("Ukončit", main_window)
    action_quit.setShortcut("Ctrl+Q")
    action_quit.triggered.connect(main_window.close)
    menu_file.addAction(action_quit)

    # --- NASTAVENÍ ---
    menu_settings = menu_bar.addMenu("Nastavení")
    
    # NOVÉ: Vyvolání nového dialogu nastavení
    action_settings = QAction("Pokročilé nastavení", main_window)
    def show_settings():
        dialog = SettingsDialog(main_window)
        if dialog.exec():  # Pokud uživatel klikne na "Uložit a zavřít"
            main_window.left_panel._aktualizovat_limit_vzorku()
            main_window.update_preview() # Vynutí překreslení grafiky
    action_settings.triggered.connect(show_settings)
    menu_settings.addAction(action_settings)

    # RUČNÍ OVLÁDÁNÍ
    action_manual = QAction("Ruční ovládání", main_window)
    action_manual.setEnabled(True) # Debugging: Povoleno i bez tiskárny
    action_manual.triggered.connect(main_window.open_manual_control)
    menu_settings.addAction(action_manual)

    # --- NÁPOVĚDA ---
    menu_help = menu_bar.addMenu("Nápověda")
    
    action_feedback = QAction("Nahlásit chybu / Nápad", main_window)
    def show_feedback():
        dialog = FeedbackDialog(main_window)
        dialog.exec()
    action_feedback.triggered.connect(show_feedback)
    menu_help.addAction(action_feedback)
    
    # NOVÉ: Kontrola aktualizací
    action_update = QAction("Zkontrolovat aktualizace", main_window)
    action_update.triggered.connect(main_window.check_updates_manually)
    menu_help.addAction(action_update)
    
    menu_help.addSeparator()
    
    # VYLEPŠENO: Krásnější stránka "O aplikaci"
    action_about = QAction("O aplikaci", main_window)
    def show_about():
        from main import APP_VERSION
        about_text = f"""
        <h2 style='color: #0d6efd;'>Laboratorní 2D Tisk Kapalin</h2>
        <p><b>Verze:</b> {APP_VERSION}</p>
        <p>Software navržený pro precizní 2D dávkování a tisk kapalin na laboratorní sklíčka. 
        Obsahuje integrovaný vektorový slicer, přímou komunikaci přes sériovou linku 
        a generátor protokolů.</p>
        <hr>
        <p><b>Autor:</b> Cyril Veverka</p>
        <p><b>Web:</b> <a href='https://7wave.cz'>7wave.cz</a></p>
        <p><b>Podpora:</b> Přes menu Nápověda -> Nahlásit chybu</p>
        """
        QMessageBox.about(main_window, "O aplikaci", about_text)
    action_about.triggered.connect(show_about)
    menu_help.addAction(action_about)

    return {
        'manual': action_manual
    }
