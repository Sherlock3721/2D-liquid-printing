# Laboratorní 2D Tisk Kapalin (G-Code Editor)

![Verze](https://img.shields.io/badge/verze-0.1.1-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-green)
![Platforma](https://img.shields.io/badge/platforma-Windows%20%7C%20Linux-lightgrey)

Specializovaný software pro precizní 2D dávkování a tisk kapalin v laboratorním prostředí. Aplikace slouží jako editor tiskových drah (slicing) i jako přímý kontroler pro 3D tiskárny (Marlin/Prusa).

## 🚀 Klíčové funkce

*   **Import a Příprava:**
    *   Podpora formátů **SVG, DXF** a syrového **G-code**.
    *   Integrovaný vektorový slicer s podporou různých stylů výplní (S okraji, Bez okrajů, Had).
    *   Automatické škálování a centrování na zvolený typ sklíčka.
*   **Laboratorní Specifika:**
    *   Předdefinované rozměry pro **laboratorní skla (76x26 mm)** a **FTO skla**.
    *   Výpočet extruze v **mikrolitrech na milimetr (µl/mm)**.
    *   Pokročilá správa **Z-offsetu** a korekce výšky pro různé držáky vzorků.
    *   **Multiplexní tisk:** Automatické rozkopírování vzorku na více sklíček s definovanou mezerou.
*   **Kontrola a Bezpečnost:**
    *   **Funkce Odpliv (Priming):** Automatická příprava trysky na pomocném sklíčku před zahájením měření.
    *   **Manuální ovládání:** Integrovaný panel pro ruční posuv os (Jog control) ve stylu Mainsail/Fluidd.
    *   **Live Preview:** Sledování aktuální pozice trysky na virtuální podložce v reálném čase.
*   **Data a Protokoly:**
    *   Export G-code s vloženými JSON metadaty (umožňuje zpětné načtení celého projektu).
    *   Automatické generování **CSV protokolů** z každého tisku pro laboratorní deníky.

## 🛠 Instalace (Vývoj)

1.  **Klonování repositáře:**
    ```bash
    git clone https://github.com/Sherlock3721/2D-liquid-printing.git
    cd 2D-liquid-printing
    ```

2.  **Vytvoření virtuálního prostředí:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux
    # nebo
    venv\Scripts\activate     # Windows
    ```

3.  **Instalace závislostí:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Spuštění:**
    ```bash
    python main.py
    ```

## 📦 Distribuce

Aplikaci lze zkompilovat do samostatného spustitelného souboru pomocí PyInstalleru:
```bash
pyinstaller main.spec
```
Pro uživatele Windows jsou hotové `.exe` soubory k dispozici v sekci **Releases**.

## ⚙️ Konfigurace

*   `settings.json`: Obsahuje limity tiskárny, startovací G-code a definice trysek.
*   `settings_default.json`: Výchozí tovární nastavení.

## 🤝 Podpora a Vývoj

Software obsahuje modul **Auto-Updater**, který automaticky kontroluje nové verze na GitHubu (pro zkompilované verze). Nápady na zlepšení nebo chyby můžete hlásit přímo skrze menu *Nápověda -> Nahlásit chybu*.

---
**Autor:** Cyril Veverka  
**Web:** [7wave.cz](https://7wave.cz)
