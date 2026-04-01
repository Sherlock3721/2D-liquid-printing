# Changelog

Všechny významné změny v tomto projektu budou dokumentovány v tomto souboru.

## [0.1.7] - 2026-04-01

### 🚀 Novinky a vylepšení
*   **Manuální výběr portu:** Do levého panelu byl přidán rozbalovací seznam (ComboBox) se všemi dostupnými COM porty a tlačítko pro jejich aktualizaci. Uživatel tak může ručně vybrat správný port, pokud automatická detekce selže.
*   **Validace spojení s tiskárnou:** Připojení k tiskárně je nyní robustnější. Aplikace po otevření portu pošle příkaz `M115` a čeká na potvrzení od tiskárny. Tím se eliminuje "falešné připojení" k nesprávným portům (např. Bluetooth), které se na Windows často vyskytuje.
*   **Ošetření DTR resetu:** Byl prodloužen časový limit pro navázání prvního kontaktu po otevření portu na 4 sekundy, což dává tiskárně dostatek času na restart po připojení k PC.

### 🛠 Opravy chyb (Bug Fixes)
*   **Falešné připojení na Windows:** Opravena chyba, kdy se aplikace tvářila jako připojená, i když tiskárna nebyla fyzicky přítomna.

## [0.1.6] - 2026-04-01

### 🚀 Novinky a vylepšení
*   **Automatické hlášení chyb:** Implementován globální systém pro zachytávání neočekávaných pádů aplikace s možností okamžitého odeslání výpisu chyby (traceback) přímo vývojářům přes Matrix (Element).
*   **Vylepšený updater pro Windows:** Opravena kritická chyba, kdy se na Windows sice stáhla nová verze, ale nedošlo k její instalaci. Nyní updater v cyklu čeká na úplné ukončení běžící aplikace a poté bezpečně provede výměnu souboru.
*   **Refresh vzorků:** Složka `gcodes/` byla pročištěna a nahrazena novými vzorovými soubory pro snadnější testování.

### 🛠 Opravy chyb (Bug Fixes)
*   **Oprava kódování (charmap):** Opravena chyba `'charmap' codec can't decode...` při načítání G-kódu na systémech Windows. Všechny soubory jsou nyní důsledně otevírány s kódováním UTF-8.

## [0.1.5] - 2026-04-01

Tato verze přináší opravy kritických chyb při nastavování hardwaru, vylepšení vizualizace a optimalizaci tiskových tras.

### 🚀 Novinky a vylepšení
*   **Vizualizace přejezdů:** V interaktivním náhledu se nyní zobrazují pohyby naprázdno (travel moves) jako **tmavě červená přerušovaná čára**. Máte tak lepší přehled o tom, kudy tryska poletí bez tisku.
*   **Seznam klávesových zkratek:** Do menu *Nápověda -> Klávesové zkratky* byl přidán přehledný seznam všech dostupných zkratek pro zrychlení práce s aplikací.
*   **Přejmenování "Dot Dispenser":** Funkce byla přejmenována na srozumitelnější český název **"Tečky"** (v GUI i v G-kódu).
*   **Kontinuita výplně Had:** Algoritmus pro výplň "Had" byl optimalizován tak, aby vytvářel co nejdelší souvislou čáru a minimalizoval zbytečné retrakce při zachování prázdných míst (děr) v geometrii.

### 🛠 Opravy chyb (Bug Fixes)
*   **Oprava pádů v nastavení:** Opravena kritická chyba `TypeError`, která způsobovala pád aplikace při pokusu o přidání nové trysky nebo typu sklíčka.
*   **Respektování děr v SVG:** Opravena chyba, kdy výplň "Had" ignorovala prázdná místa (díry) v SVG souborech a nekontrolovaně je vyplňovala.
*   **Oprava Undo/Redo:** Opraven výpočet souřadnic Y v historii změn (Undo/Redo), který způsoboval posun objektů při návratu zpět.
*   **Stabilita v PyQt6:** Opraveny konflikty v signálech tlačítek, které způsobovaly pády v novějších verzích knihovny PyQt6.
*   **G-code generátor:** Opravena chyba nedefinovaného stylu výplně a vylepšeno kešování transformací pro rychlejší export velkých souborů.
*   **Syntaxe v Sliceru:** Opraveny syntaktické chyby v `core/vector_slicer.py` (středníky u bloků).

### ⚙️ Technické změny
*   Navýšení verze aplikace na **v0.1.5**.
*   Refaktorizace `core/vector_slicer.py` pro lepší čitelnost.
*   Zpřesnění výpočtu pozic v režimu Multiplex při aktivním "odplivu" (priming slot).
