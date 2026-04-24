import os
import re
import math
from gui.settings import load_settings
from core.extrusion_logic import ExtrusionCalculator

def generate_gcode(logic, params):
    from core.logic import get_layout_positions
    
    if not logic.filepath: raise ValueError("Není načten žádný vstupní vzorek.")

    settings = load_settings()
    
    # Inicializace logiky pro extruzi
    filament_diam = params.get('filament_diameter', 9.5)
    flow_mult = params.get('flow_multiplier', 1.0)
    
    # Výchozí kalibrační faktor z průměru filamentu (1 µl = 1 mm³)
    default_cal = 1.0 / (math.pi * ((filament_diam / 2.0) ** 2))
    cal_factor = settings.get("calibration_factor", default_cal)
    
    ext_calc = ExtrusionCalculator(
        filament_diameter=filament_diam, 
        flow_multiplier=flow_mult,
        calibration_factor=cal_factor
    )

    typ_drzaku = "Multiplex (více sklíček)"
    z_offset = params.get('z_offset', 0.2)
    pocet_vzorku = params.get('sample_count', 1)
    bed_temp = params.get('bed_temp', 0)
    prime_active = params.get('prime_active', True)
    
    slide_w = params.get('slide_w', 25.0)
    slide_h = params.get('slide_h', 75.0)
    slide_z = params.get('slide_z', 1.0)
    
    spacing = settings["multi_spacing"] 
    transforms = params.get('transforms', [])
    slide_overrides = params.get('slide_overrides', {})

    extrusion_rate = params.get('extrusion_rate', 1.0)
    nozzle_diam = params.get('nozzle_diam', 0.4) 
    print_speed = settings.get("print_speed", 1500)
    retraction = settings.get("retraction", 1.0)
    retract_speed = 3000

    block_h = settings.get("block_height", 34.0)
    # hidden_h is now ideally per-nozzle, fallback to global settings for compatibility
    hidden_h = params.get('nozzle_hidden', settings.get("hidden_nozzle_part", 4.0))

    total_dist = 0.0
    total_time_sec = 0.0

    # --- VÝPOČET FINÁLNÍHO Z A MOŽNÉHO POSUNU (SHIFT) ---
    # Pokud tiskárna odmítá jet pod Z=0 (limit PINDA sondy), použijeme trik s G92.
    # Zjistíme nejnižší Z v celém souboru.
    min_needed_z = 999.0
    
    def get_abs_z(loc_z_off, loc_nz_h, loc_nz_hid, loc_sl_z):
        return -block_h + loc_nz_h - loc_nz_hid + loc_sl_z + loc_z_off

    # Prověříme základní parametry a odpliv
    min_needed_z = min(min_needed_z, get_abs_z(z_offset, params.get('nozzle_height', 30.0), hidden_h, slide_z))
    
    # Prověříme všechna sklíčka a jejich případné override
    for m_idx in range(pocet_vzorku):
        overrides = slide_overrides.get(str(m_idx), {})
        loc_z = overrides.get('z_offset', z_offset)
        loc_nz_h = overrides.get('nozzle_height', params.get('nozzle_height', 30.0))
        loc_nz_hid = overrides.get('nozzle_hidden', hidden_h)
        min_needed_z = min(min_needed_z, get_abs_z(loc_z, loc_nz_h, loc_nz_hid, slide_z))

    z_shift = 0.0
    if min_needed_z < 0.0:
        # Posuneme vše o abs(min_z) + malou rezervu nahoru, aby tiskárna jela v kladných číslech
        z_shift = abs(min_needed_z) + 1.0 

    result = []
    # Startovní G-code (včetně G28/G80)
    result.append(settings["start_gcode"])
    if not result[-1].endswith("\n"): result.append("\n")

    if z_shift > 0:
        result.append(f"; --- VIRTUÁLNÍ POSUN Z (SHIFT {z_shift:.2f}mm) ---\n")
        result.append(f"; Tryska musí pod úroveň PINDA sondy. Lžeme tiskárně o výšce pomocí G92.\n")
        result.append(f"G1 Z20 F1000 ; Výjezd do bezpečné výšky\n")
        result.append(f"G92 Z{20.0 + z_shift:.3f} ; Nastavení posunuté nuly\n\n")

    if bed_temp > 0:
        result.append(f"M140 S{bed_temp} ; Zacit nahrivat podlozku\n")
        result.append(f"M190 S{bed_temp} ; Pockat na nahrati podlozky na {bed_temp} C\n")
        total_time_sec += 60 # Odhad 1 minuta na nahřátí

    positions = get_layout_positions(pocet_vzorku, slide_w, slide_h, spacing, typ_drzaku, settings["bed_max_x"], settings["bed_max_y"], prime_active=prime_active)

    measurement_idx = 0
    infill_style = params.get('infill_style', 'S okraji')

    last_abs_x, last_abs_y = 0.0, 0.0 # Pro výpočet travelů mezi sklíčky

    for i, (posun_x, posun_y, sw, sh, is_prime) in enumerate(positions):
        if is_prime:
            result.append(f"\n; --- VZOREK (ODPLIV) ---\n")
        else:
            result.append(f"\n; --- VZOREK {measurement_idx + 1} ---\n")
            
        result.append(settings["loop_start_gcode"])
        if not result[-1].endswith("\n"): result.append("\n")

        current_overrides = slide_overrides.get(str(measurement_idx) if not is_prime else "-1", {})
        loc_z = current_overrides.get('z_offset', z_offset)
        loc_ext = current_overrides.get('extrusion_rate', extrusion_rate)
        loc_spd = current_overrides.get('print_speed', print_speed)
        loc_infill_style = current_overrides.get('infill_style', infill_style)
        loc_nozzle_h = current_overrides.get('nozzle_height', params.get('nozzle_height', 30.0))
        
        # Výpočet extruze pomocí nové logiky
        loc_unit = current_overrides.get('extrusion_unit', params.get('extrusion_unit', 'µl/mm'))
        loc_e_per_mm = ext_calc.calculate_e_per_mm(loc_ext, loc_unit, nozzle_diam, loc_spd)
        
        # Nový výpočet absolutního Z: - Výška bloku + Výška trysky - Schovaná část + Tloušťka skla + lokální offset + virtuální posun
        print_z = -block_h + loc_nozzle_h - hidden_h + slide_z + loc_z + z_shift

        t = transforms[measurement_idx] if transforms and not is_prime and measurement_idx < len(transforms) else None
        S = t['scale'] if t else 1.0
        gui_dx = t['gui_dx'] if t else 0.0
        gui_dy = t['gui_dy'] if t else 0.0
        cx_t = t['cx'] if t else 0.0
        cy_t = t['cy'] if t else 0.0
        bed_y = settings["bed_max_y"]

        def transform_pt(x_orig, y_orig):
            # Bod relativně k počátku skupiny v GUI
            # V GUI kreslíme: x_orig, sh - y_orig (Y je invertované)
            local_gui_x = x_orig
            local_gui_y = sh - y_orig
            
            # Aplikace měřítka kolem transformOriginPoint (cx_t, cy_t)
            # ParentPos = item.pos() + Origin + S * (Local - Origin)
            gui_x_new = gui_dx + cx_t + (local_gui_x - cx_t) * S
            gui_y_new = gui_dy + cy_t + (local_gui_y - cy_t) * S
            
            # Převod zpět na G-code Y (invertovat přes bed_max_y)
            return gui_x_new, bed_y - gui_y_new

        if is_prime:
            cx, cy = posun_x + sw/2, posun_y + sh/2
            x1, x2 = cx - 5, cx + 5
            y1, y2 = cy - 5, cy + 5
            
            # Travel k začátku odplivu
            start_abs_x, start_abs_y = x1, y1
            travel_dist = math.hypot(start_abs_x - last_abs_x, start_abs_y - last_abs_y)
            total_time_sec += (travel_dist / 3000) * 60
            last_abs_x, last_abs_y = start_abs_x, start_abs_y

            result.append(f"G1 Z{print_z + 2.0:.3f} F1000 ; Z-hop pro odpliv\n")
            result.append(f"G0 X{x1:.3f} Y{y1:.3f} F3000\n")
            result.append(f"G1 Z{print_z:.3f} F1000\n")
            result.append("M83 ; Relativní extruze\n")
            
            curr_y = y1
            direction = 1
            while curr_y <= y2:
                target_x = x2 if direction > 0 else x1
                dist = abs(target_x - (x1 if direction > 0 else x2))
                result.append(f"G1 X{target_x:.3f} Y{curr_y:.3f} E{dist * loc_e_per_mm:.5f} F{loc_spd}\n")
                total_dist += dist
                total_time_sec += (dist / loc_spd) * 60
                
                curr_y += nozzle_diam
                if curr_y <= y2:
                    result.append(f"G1 X{target_x:.3f} Y{curr_y:.3f} E{nozzle_diam * loc_e_per_mm:.5f} F{loc_spd}\n")
                    total_dist += nozzle_diam
                    total_time_sec += (nozzle_diam / loc_spd) * 60
                direction *= -1
                last_abs_x, last_abs_y = target_x, curr_y
            result.append(f"G0 Z{print_z + 2.0:.3f} F1000\n")
        else:
            if logic.is_vector:
                result.append("M83 ; Prepnuti na relativni extruzi pro vektory\n")
                result.append("G92 E0.0 ; Reset extruderu pro toto sklicko\n")
                is_retracted = False
                
                if hasattr(logic, 'paths_by_index') and measurement_idx in logic.paths_by_index:
                    px_list = logic.paths_by_index[measurement_idx]['x']
                    py_list = logic.paths_by_index[measurement_idx]['y']
                else:
                    px_list = logic.path_x; py_list = logic.path_y

                for px, py in zip(px_list, py_list):
                    if not px: continue
                    abs_x, abs_y = transform_pt(px[0], py[0])
                    
                    # Travel k začátku segmentu
                    travel_dist = math.hypot(abs_x - last_abs_x, abs_y - last_abs_y)
                    total_time_sec += (travel_dist / 3000) * 60
                    last_abs_x, last_abs_y = abs_x, abs_y

                    if loc_infill_style == "Tečky" and len(px) == 2 and px[0] == px[1]:
                        # loc_ext v tomto případě interpretujeme jako µl (nebo kroky) na jednu kapku
                        dot_unit = "kroky" if loc_unit == "kroky/mm" else "µl"
                        dot_e = ext_calc.calculate_dot_extrusion(loc_ext, dot_unit)
                        result.append(f"G1 Z{print_z + 2.0:.3f} F1000 ; Z-hop nad bod\n")
                        result.append(f"G0 X{abs_x:.3f} Y{abs_y:.3f} F3000\n")
                        result.append(f"G1 Z{print_z:.3f} F1000 ; Klesnuti k povrchu\n")
                        result.append(f"G1 E{dot_e:.5f} F300 ; Pomale davkovani kapky\n")
                        result.append(f"G1 Z{print_z + 2.0:.3f} F1000 ; Z-hop po davkovani\n")
                        total_time_sec += 2 # Odhad na jednu tečku
                        continue

                    result.append(f"G1 Z{print_z + 2.0:.3f} F1000 ; Z-hop\n")
                    result.append(f"G0 X{abs_x:.3f} Y{abs_y:.3f} F3000\n")
                    result.append(f"G1 Z{print_z:.3f} F1000\n")
                    if is_retracted and retraction > 0:
                        result.append(f"G1 E{retraction:.5f} F{retract_speed} ; Deretrakce\n")
                        is_retracted = False
                    for j in range(1, len(px)):
                        ax_prev, ay_prev = transform_pt(px[j-1], py[j-1])
                        ax, ay = transform_pt(px[j], py[j])
                        dist = math.hypot(ax - ax_prev, ay - ay_prev)
                        result.append(f"G1 X{ax:.3f} Y{ay:.3f} E{dist * loc_e_per_mm:.5f} F{loc_spd}\n")
                        total_dist += dist
                        total_time_sec += (dist / loc_spd) * 60
                        last_abs_x, last_abs_y = ax, ay
                    if retraction > 0:
                        result.append(f"G1 E{-retraction:.5f} F{retract_speed} ; Retrakce\n")
                        is_retracted = True
                result.append(f"G1 Z{print_z + 2.0:.3f} F1000\n")
            else:
                l_x, l_y = 0.0, 0.0
                off_x = getattr(logic, 'gcode_offset_x', 0.0)
                off_y = getattr(logic, 'gcode_offset_y', 0.0)
                
                for line in logic.original_lines:
                    orig_l = line.split(';')[0].strip()
                    comment = " ;" + line.split(';', 1)[1].strip() if ';' in line else ""
                    if not orig_l or orig_l.upper().startswith('M'):
                        result.append(line.rstrip() + "\n"); continue
                    orig_l_up = orig_l.upper(); modified_line = orig_l
                    if 'G1' in orig_l_up or 'G0' in orig_l_up:
                        mx = re.search(r'X([0-9\.\-]+)', orig_l_up); my = re.search(r'Y([0-9\.\-]+)', orig_l_up)
                        ox = float(mx.group(1)) if mx else l_x; oy = float(my.group(1)) if my else l_y
                        
                        # Aplikujeme normalizační posuv (vycentrování na sklíčku)
                        # a pak transformaci na pozici sklíčka na podložce
                        ax, ay = transform_pt(ox + off_x, oy + off_y)
                        
                        dist_head = math.hypot(ax - last_abs_x, ay - last_abs_y)
                        
                        if 'E' in orig_l_up:
                            lax, lay = transform_pt(l_x + off_x, l_y + off_y)
                            dist = math.hypot(ax - lax, ay - lay)
                            if dist > 0:
                                modified_line = re.sub(r'E([0-9\.\-]+)', f"E{dist * loc_e_per_mm:.5f}", modified_line, flags=re.I)
                                if 'F' in modified_line: modified_line = re.sub(r'F([0-9\.]+)', f"F{loc_spd}", modified_line, flags=re.I)
                                else: modified_line += f" F{loc_spd}"
                                total_dist += dist
                                total_time_sec += (dist / loc_spd) * 60
                        else:
                            # Travel
                            total_time_sec += (dist_head / 3000) * 60

                        if mx: modified_line = re.sub(r'X[0-9\.\-]+', f"X{ax:.3f}", modified_line, flags=re.I)
                        if my: modified_line = re.sub(r'Y[0-9\.\-]+', f"Y{ay:.3f}", modified_line, flags=re.I)
                        l_x, l_y = ox, oy
                        last_abs_x, last_abs_y = ax, ay
                    if 'Z' in orig_l_up: modified_line = re.sub(r'Z([0-9\.\-]+)', f"Z{print_z:.3f}", modified_line, flags=re.I)
                    result.append(modified_line + comment + "\n")            
            measurement_idx += 1

        result.append(settings["loop_end_gcode"])
        if not result[-1].endswith("\n"): result.append("\n")

    if bed_temp > 0: result.append("M140 S0 ; Vypnout vyhrivani podlozky\n")
    result.append(settings["end_gcode"])
    if not result[-1].endswith("\n"): result.append("\n")
    return "".join(result), total_dist, total_time_sec
