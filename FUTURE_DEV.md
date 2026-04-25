# Future Development Roadmap 🚀

Tento dokument shrnuje plánované funkce, optimalizace a vize pro budoucí rozvoj aplikace Droplet Printing Interface (DPI).

## ⚡ Výkon a Architektura
- **Kompletní přepis do Rustu:** Přepis celé aplikace do jazyka Rust (např. pomocí Tauri). Cílem je eliminovat lagy při zpracování tisíců bodů (tečkování), zlepšení výkonu na méně výkoných zařízení.
- **Inkrementální rendering:** Optimalizace `InteractiveGraphicsView`, aby nedocházelo k překreslování celé scény při pohybu jednoho sklíčka.
- **Background Processing:** Přesunutí výpočtů geometrie do samostatného vlákna, aby GUI zůstalo responzivní i během náročných operací.

## 🔬 Laboratorní Funkce
- **Dot Dispensing (Tečkování):** Dokončení plné podpory pro bodové dávkování s přesným řízením objemu jedné kapky.
- **Grid Dispersing (Mřížka):** Přidání Mřížkové textury
- **Pokročilé nastavení výšky trstvy:** V součastnosti se dá stanovit jen výška trysky která nanáší mokrou vrstvu. Pomocí výpočtů ze známích vlsatností by se mohla dát stanovit reálná výška mokré vrsty a teoreticky i suché vrstvy.

## 📸 Integrace Hardwaru
- **Vizuální kontrola:** Využití kamery pro automatickou detekci okrajů sklíčka a kalibraci offsetu trysky.
- **AI analýza kapek:** Automatické vyhodnocování kvality natištěných kapek pomocí počítačového vidění.
- **Podpora Klipperu:** Rozšíření komunikace o nativní podporu pro firmware Klipper (API).

## 🛠 Uživatelské Rozhraní
- **Tmavý/Světlý režim:** Plná podpora témat pro lepší čitelnost v různých laboratorních podmínkách.
- **Lokalizace:** Podpora pro další jazyky (angličtina).

---
Nápady na další funkce můžete posílat skrze vestavěný formulář pro zpětnou vazbu v aplikaci.
