# Mapa Projektu: Laboratorní 2D Tisk Kapalin

## [[main.py]] (Hlavní aplikace)
- **Třída `GCodeApp`**
    - **Proměnné**
        - `logic` (Instance GCodeLogic)
        - `graphics_view` (InteractiveGraphicsView)
        - `left_panel` (LeftPanel)
        - `right_panel` (RightPanel)
        - `updater` (AutoUpdater)
        - `user_scales`
        - `menu_actions`
        - `loaded_transforms`
    - **Konexe (Signály -> Sloty)**
        - `left_panel.values_changed` -> `update_preview`
        - `right_panel.values_changed` -> `update_preview`
        - `worker.pos_changed` -> `graphics_view.update_nozzle_position`
        - `worker.status_changed` -> `_update_menu_status`
        - `updater.update_available` -> `on_update_available`

## [[printer_com.py]] (Komunikace)
- **Třída `SerialPrinterWorker`**
    - **Proměnné**
        - `serial_conn` (Sériový port)
        - `is_printing` (Stav tisku)
        - `is_paused` (Pauza)
        - `cur_x`, `cur_y`, `cur_z` (Pozice)
        - `port`, `baudrate`
    - **Signály (Výstupní)**
        - `pos_changed` (Změna souřadnic)
        - `status_changed` (Stav tiskárny)
        - `progress_changed` (Procenta)
        - `stats_changed` (Čas/Vzdálenost)
        - `temp_changed` (Teplota)

## Složka `core` (Logika)
### [[core/logic.py]]
- **Třída `GCodeLogic`**
    - **Proměnné**
        - `filepath`
        - `original_lines`
        - `paths_by_index`
        - `is_vector`
        - `travel_x`, `travel_y`
### [[core/vector_slicer.py]]
- **Třída `VectorSlicer`**
    - **Proměnné**: `geometries`
- **Třída `DXFParser`**
    - **Proměnné**: `dxf_to_mm`, `entities`, `units`, `path`
### [[core/gcode_generator.py]]
- **Funkce**
    - `generate_gcode`
    - `apply_z_heights`
    - `insert_metadata`
### [[core/extrusion_logic.py]]
- **Třída `ExtrusionCalculator`**
    - **Proměnné**: `filament_diameter`, `filament_area`, `flow_multiplier`
### [[core/updater.py]]
- **Třída `AutoUpdater`**
    - **Signály**: `update_available`, `update_ready`, `progress`, `error`

## Složka `gui` (Rozhraní)
### [[gui/left_panel.py]]
- **Třída `LeftPanel`**
    - **Prvky (UI)**
        - `btn_load` (Načíst)
        - `btn_start_print` (Start)
        - `btn_pause` (Pauza)
        - `cmb_glass` (Výběr skla)
        - `widget_infill` (Výplň)
    - **Signály**: `values_changed`
### [[gui/right_panel.py]]
- **Třída `RightPanel`**
    - **Proměnné**
        - `slide_widgets` (Jednotlivá sklíčka)
        - `local_modifications` (Změny)
        - `manual_widget` (Ruční posuv)
    - **Signály**: `values_changed`
### [[gui/graphics_view.py]]
- **Třída `InteractiveGraphicsView`**
    - **Proměnné**: `scene`, `nozzle_item`, `gcode_items`, `undo_stack`
### [[gui/manual_movement.py]]
- **Třída `ManualMovementWidget`**
    - **Ovládací prvky**: `btn_x_plus`, `btn_y_plus`, `btn_z_plus`, `btn_home_xy`
### [[gui/settings.py]]
- **Třída `SettingsDialog`**
    - **Proměnné**: `inp_bed_x`, `inp_bed_y`, `inp_spacing`
### [[gui/menu_bar.py]]
- **Menu**: `Soubor`, `Nástroje`, `Nápověda`
### [[gui/feedback_dialog.py]]
- **Třída `FeedbackDialog`**
    - **Signály**: `finished` (přes Thread)
