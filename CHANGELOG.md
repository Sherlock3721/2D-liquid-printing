# Changelog

Všechny významné změny v tomto projektu budou dokumentovány v tomto souboru.

## [1.0.0] - 2026-04-16 (Produkční verze)

### 🚀 Novinky a vylepšení
*   **Oficiální produkční verze:** Aplikace byla povýšena na verzi 1.0.0 a je připravena pro běžné laboratorní použití.
*   **Vypnutí terminálu (Windows):** Při spuštění .exe souboru se již nezobrazuje černé okno terminálu pro čistší uživatelský zážitek.
*   **Oprava dekódování komunikace:** Vyřešena chyba `utf-8 codec can't decode byte 0xc1`, která způsobovala pády při specifických odpovědích z některých tiskáren (např. s českou diakritikou nebo binárními daty).
*   **Oprava automatických aktualizací:** Synchronizovány názvy repositářů v updateru, což zajišťuje správnou detekci a stahování nových verzí přímo z GitHubu.

## [0.1.21] - 2026-04-16

### 🚀 Novinky a vylepšení
*   **Odhad času tisku a ujeté vzdálenosti:** Aplikace nyní v reálném čase vypočítává celkovou dráhu tiskové hlavy a odhaduje zbývající čas do konce tisku. Tyto statistiky jsou zobrazeny v levém panelu pod ukazatelem průběhu.
*   **Vylepšené manuální ovládání:** Panel manuálního pohybu byl kompletně přepracován. Nyní umožňuje přechod na absolutní souřadnice (X, Y, Z), zobrazuje aktuální pozici trysky v reálném čase a přehledněji indikuje stav motorů.
*   **Sledování Z-osy:** V reálném čase je nyní sledována a aktualizována také pozice osy Z, což poskytuje lepší přehled o aktuální výšce nanášení.
*   **Optimalizace výpočtu extruze:** Zpřesněn výpočet extruze pro různé styly výplně a zaveden parametr pro plochu virtuálního filamentu pro lepší kompatibilitu s Prusa/Marlin tiskárnami.

### 🛠 Opravy chyb
*   **Stabilizace GUI:** Opraveny možné pády při aktualizaci pozice trysky a vylepšeno přepínání stavů ovládacích prvků během tisku.
*   **Oprava pádů v updateru:** Zajištěno bezpečnější ukončení procesů před aktualizací na Windows.

## [0.1.15] - 2026-04-01

### 🚀 Novinky a vylepšení
*   **Nastavení zobrazení plochy:** V pokročilém nastavení nyní můžete vypnout/zapnout zobrazení hlavních os (X, Y) tiskárny pro čistší náhled.
*   **Robustnější Updater (Windows):** Vylepšen mechanismus aktualizace na Windows. Updater se nyní aktivně pokusí ukončit běžící procesy aplikace před instalací nové verze a lépe ošetřuje případy, kdy je soubor blokován.

### 🛠 Opravy chyb
*   **Oprava pádu (IndentationError):** Odstraněna syntaktická chyba v levém panelu, která znemožňovala spuštění aplikace.

## [0.1.14] - 2026-04-01

### 🚀 Novinky a vylepšení
*   **Volba přenosové rychlosti (Baudrate):** Do ovládání tiskárny byla přidána možnost zvolit rychlost komunikace (standardně 115200 nebo 250000). To je klíčové pro tiskárny, které nevyužívají výchozí rychlost.
*   **Stabilnější inicializace spojení:** Přidána povinná prodleva 2,5 sekundy po otevření portu, která dává tiskárně čas na restart a náběh firmwaru před prvním příkazem. Tím se řeší chyba "Tiskárna neodpovídá".
*   **Robustnější čtení odpovědí:** Zlepšen mechanismus ověřování spojení pro lepší kompatibilitu s různými verzemi firmwaru Marlin a Prusa.

## [0.1.13] - 2026-04-01

### 🛠 Opravy chyb
*   **Finalizace vzorků a verze:** Zahrnutí všech zbývajících změn do buildu.

## [0.1.12] - 2026-04-01

### 🛠 Opravy chyb
*   **Obnova vzorků:** Vrácení původního obsahu složky `gcodes/` podle požadavku uživatele.

## [0.1.11] - 2026-04-01

### 🛠 Opravy chyb (Hotfix)
*   **Kritická oprava syntaxe:** Opakované odstranění poškozeného konce souboru `main.py`, který znemožňoval kompilaci.

## [0.1.10] - 2026-04-01

### 🛠 Opravy chyb (Hotfix)
*   **Oprava SyntaxError (podruhé):** Odstranění zbytkového kódu na konci souboru `main.py`, který způsoboval pád sestavení.

## [0.1.9] - 2026-04-01

### 🛠 Opravy chyb (Hotfix)
*   **Oprava SyntaxError:** Opravena syntaktická chyba v hlavním souboru `main.py`, která bránila úspěšnému sestavení (buildu) aplikace.

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
