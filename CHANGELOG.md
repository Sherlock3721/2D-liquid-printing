# Changelog

Všechny významné změny v tomto projektu budou dokumentovány v tomto souboru.

## [1.3.7] - 2026-04-27

### 🚀 Novinky a vylepšení
*   **Modul kamery:** Přidána funkce pro uložení snímku (screenshot) z živého náhledu pomocí ikony `svg/screenshot.svg`.
*   **Optimalizace:** Vylepšen algoritmus pro dávkování teček (dot dispensing), oprava rotace obrazu z kamery a celkové vyčištění repozitáře.

### 🛠 Opravy chyb
*   **Vykreslování (Graphics View):** Opravena chyba indexování při aktivním "odplivu" (priming).
*   **Oprava GUI:** Vyřešena syntaktická chyba `SyntaxError` v `setStyleSheet`.

## [1.3.6] - 2026-04-24

### 🛠 Opravy chyb
*   **Vykreslování barev v SVG:** Opraven problém, kdy se ikony v panelu ručního ovládání zobrazovaly bez barev. Kód nyní automaticky převádí CSS styly v SVG na nativní XML atributy, které jsou plně kompatibilní s Qt rendererem.

## [1.3.5] - 2026-04-24

### 🛠 Opravy chyb
*   **Oprava SVG ikon:** Vyřešen problém s nenačítáním ikon v panelu ručního ovládání. Ikony jsou nyní správně mapovány na XML ID prvků a je zajištěno jejich vykreslení i v případě, že jsou v původním SVG souboru skryté.

## [1.3.4] - 2026-04-24

### 🚀 Novinky a vylepšení
*   **Perzistence kamery:** Aplikace si nyní pamatuje nastavenou rotaci obrazu (uloženo v `settings.json`) a automaticky ji aplikuje při dalším spuštění.
*   **Vylepšené UI ovládání:** Původní textová tlačítka v panelu ručního ovládání byla nahrazena moderními ikonami načtenými přímo ze souboru `svg/manual_movement.svg`.

## [1.3.3] - 2026-04-24

### 🛠 Opravy a zabezpečení
*   **Omezení ručního ovládání:** Manuální posuv motorů je nyní automaticky zablokován, pokud není tiskárna připojena nebo pokud právě probíhá tisk. Tím se předchází kolizím a chybám v komunikaci.
*   **Logika Bed Levelingu:** 
    *   Deaktivace Bed Levelingu je nyní při spuštění aplikace zakázána. První tisk po startu musí vždy obsahovat plnou kalibraci pro zajištění bezpečnosti. Možnost vypnutí se zpřístupní až od druhého tisku.
    *   Ruční tlačítka pro "Home" v ovládacím panelu nyní provádějí pouze základní homing os (`G28`), nikoliv plný Bed Leveling rituál.

## [1.3.2] - 2026-04-24

### 🚀 Novinky a vylepšení
*   **Automatizace kamery:**
    *   **Auto-start:** Kamera se nyní automaticky připojí a spustí při otevření aplikace.
    *   **Priorita externí kamery:** Systém automaticky preferuje externí USB kameru (index 1 a vyšší) před vestavěnou webkamerou.
    *   **Rotace obrazu:** Přidáno tlačítko pro cyklickou rotaci obrazu (0°, 90°, 180°, 270°), aby byl náhled vždy správně orientován bez ohledu na fyzické uchycení kamery.

## [1.3.1] - 2026-04-24

### 🛠 Opravy a vylepšení
*   **Stabilizace modulu kamery:**
    *   Aplikace již nespadne, pokud chybí knihovna `opencv-python` (nyní je závislost ošetřena).
    *   Přidán **výběr zdroje kamery** (dropdown menu) pro systémy s více USB kamerami.
    *   **Inteligentní skrývání:** Pokud není nalezena žádná kamera, náhled se automaticky schová, aby nezabíral místo v panelu.

## [1.3.0] - 2026-04-24

### 🚀 Novinky a vylepšení
*   **Integrace USB kamery:** Do pravého panelu (nad manuální ovládání) byl přidán modul pro zobrazení živého náhledu z USB kamery. Tento modul slouží jako základ pro budoucí systém automatické detekce selhání a ochrany trysky.
*   **Závislosti:** Přidána podpora pro knihovnu OpenCV (`opencv-python`) pro zpracování obrazu.

## [1.2.7] - 2026-04-24

### 🛠 Opravy a doladění
*   **Upřesnění Bed Leveling rituálu:** Při vypnutém Bed Levelingu se nyní přeskakuje pouze samotná kalibrace sítě (`G80`). Ruční rituál PINDA (výzvy k zasunutí/vysunutí sondy) a základní zahomování (`G28`) zůstávají zachovány, protože jsou nezbytné pro bezpečnou orientaci tiskárny.

## [1.2.6] - 2026-04-24

### 🚀 Novinky a vylepšení
*   **Přepínač Bed Leveling:** Do levého panelu (sekce Podložka) přidáno tlačítko pro zapnutí/vypnutí Bed Levelingu.
    *   Pokud je vypnutý, tiskárna při přímém tisku z aplikace přeskočí PINDA kalibrační rituál (rychlejší start).
    *   V exportovaném G-code souboru zůstává kalibrace vždy aktivní pro zajištění nezávislosti souboru.
*   **Reorganizace UI:** Parametr "Absolutní Z tiskárny" byl odstraněn z hlavního panelu pro lepší přehlednost a přesunut do **Nastavení -> záložka Převody**, kde se dynamicky přepočítává pro vybraný profil.

## [1.2.5] - 2026-04-24

### 🚀 Novinky a vylepšení
*   **Robustní tisk pod úroveň Z=0 (G92 Shift):** Implementována spolehlivá metoda pro tisk v záporných výškách (když je tryska fyzicky výše než PINDA sonda). Aplikace nyní automaticky vypočítá potřebný posun a pomocí příkazu `G92` virtuálně posune souřadný systém nahoru. To umožňuje trysce sjet až na sklo bez chybových hlášek tiskárny ("Z level enforced").
*   **Odstranění M211:** Vzhledem k nespolehlivosti příkazů pro vypnutí endstopů u některých verzí firmware byly tyto příkazy zcela nahrazeny výše zmíněným posunem.

## [1.2.4] - 2026-04-24

### 🛠 Opravy chyb
*   **Konečná oprava "Z level enforced" při startu:** Odstraněn příkaz `M211 S1` z úplného začátku souboru. Tento příkaz způsoboval chybu, pokud tiskárna po předchozím tisku zůstala v záporných souřadnicích. Nyní `G28` (homing) proběhne v původním stavu, což chybu eliminuje.
*   **Reset stavu po tisku:** Přidán příkaz `M211 S1` na konec G-kódu, aby byla tiskárna vždy zanechána v bezpečném stavu se zapnutými endstopy.

## [1.2.3] - 2026-04-24

### 🛠 Opravy chyb
*   **Oprava "Z level enforced" při levelingu:** Odstraněn rizikový posun souřadnic `G92`. Místo toho se nyní používá bezpečnější sekvence `M211 S1` na začátku souboru (pro korektní bed leveling) a `M211 S0` až po zahomování.
*   **Vylepšená kompatibilita endstopů:** Všechny pohyby v ose Z byly změněny z `G0` na `G1`, což zaručuje, že firmware (zejména u Prusa tiskáren) správně respektuje vypnutí softwarových endstopů i při pohybech pod úroveň nuly.

## [1.2.2] - 2026-04-24

### 🛠 Opravy chyb
*   **Robustní řešení pro Z < 0 (G92 Shift):** Nahrazen příkaz `M211 S0` (který některé tiskárny ignorují) spolehlivější metodou posunu souřadnic. Pokud výpočet Z vyžaduje pohyb pod úroveň nuly, celá osa Z se v G-kódu virtuálně posune nahoru pomocí `G92`. To zaručuje, že tiskárna nikdy nenarazí na softwarový endstop, i když fyzicky tiskne pod úrovní původního `Z=0`.

## [1.2.1] - 2026-04-24

### 🚀 Novinky a vylepšení
*   **Interaktivní vizuální schéma:** Do nastavení bylo přidáno interaktivní SVG schéma pro intuitivní konfiguraci trysek, komory a tloušťky substrátů.
*   **Individuální parametry trysek:** Každá tryska má nyní vlastní parametr "Skrytá délka", což nahrazuje dřívější globální nastavení a umožňuje přesnější kalibraci různých typů trysek.
*   **Tloušťka držáku / masky:** Přidán nový parametr v záložce Podložka, který je synchronizován s výškou vrstvy a vizualizován v interaktivním schématu.
*   **Vylepšený náhled (Graphics View):**
    *   Při spuštění se náhled automaticky vycentruje na tiskovou plochu.
    *   Umožněno odzoomování až 50 mm mimo tiskovou plochu pro lepší orientaci.
    *   Opraveno chování zoomu a zarovnání scény k levému hornímu rohu.

### 🛠 Opravy chyb
*   **Oprava G-code generátoru:** Vyřešena kritická chyba, kdy byl vygenerovaný G-code posunutý oproti vizuálnímu náhledu. Nyní se transformace (posun, měřítko) shodují 1:1.
*   **Stabilizace nastavení:** Opraveny pády aplikace (`AttributeError`, `NameError`) při otevírání a ukládání pokročilého nastavení.
*   **Oprava ukládání:** Zajištěna správná persistence parametrů tloušťky vrstvy a jejich okamžité promítnutí do hlavního panelu.
*   **SVG Rendering Hotfix:** Vyčištěny vnitřní struktury SVG schématu pro odstranění chyb Qt rendereru ("Could not add child element").

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
