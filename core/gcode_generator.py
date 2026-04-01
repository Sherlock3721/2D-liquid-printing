import os
import re
import math
from gui.settings import load_settings

def generate_gcode(logic, params):
    from core.logic import get_layout_positions, HOLDER_THICKNESS
    
    if not logic.filepath: raise ValueError("Není načten žádný vstupní vzorek.")

    settings = load_settings()

    typ_drzaku = params.get('holder_type', 'Na jeden vzorek')
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

    area = math.pi * ((nozzle_diam / 2.0) ** 2)
    
    holder_z = HOLDER_THICKNESS.get(typ_drzaku, 0.0)
    surface_z = holder_z + slide_z

    result = []
    result.append(settings["start_gcode"])
    if not result[-1].endswith("\n"): result.append("\n")

    if typ_drzaku == "Multiplex (více sklíček)" and bed_temp > 0:
        result.append(f"M140 S{bed_temp} ; Zacit nahrivat podlozku\n")
        result.append(f"M190 S{bed_temp} ; Pockat na nahrati podlozky na {bed_temp} C\n")

    positions = get_layout_positions(pocet_vzorku, slide_w, slide_h, spacing, typ_drzaku, settings["bed_max_x"], settings["bed_max_y"], prime_active=prime_active)

    measurement_idx = 0
    infill_style = params.get('infill_style', 'S okraji')

    for i, (posun_x, posun_y, sw, sh, is_prime) in enumerate(positions):
        if is_prime:
            result.append(f"\n; --- VZOREK (ODPLIV) ---\n")
        else:
            result.append(f"\n; --- VZOREK {measurement_idx + 1} ---\n")
            
        result.append(settings["loop_start_gcode"])
        if not result[-1].endswith("\n"): result.append("\n")

        # Overrides se vztahují pouze na reálná měření, nikoliv na odpliv
        current_overrides = slide_overrides.get(str(measurement_idx) if not is_prime else "-1", {})
        loc_z = current_overrides.get('z_offset', z_offset)
        loc_ext = current_overrides.get('extrusion_rate', extrusion_rate)
        loc_spd = current_overrides.get('print_speed', print_speed)
        loc_infill_style = current_overrides.get('infill_style', infill_style)
        
        loc_e_per_mm = loc_ext / area
        print_z = surface_z + loc_z

        # Kešování parametrů transformace
        t = transforms[measurement_idx] if transforms and not is_prime and measurement_idx < len(transforms) else None
        S = t['scale'] if t else 1.0
        gui_dx = t['gui_dx'] if t else 0.0
        gui_dy = t['gui_dy'] if t else 0.0
        cx_t = t['cx'] if t else 0.0
        cy_t = t['cy'] if t else 0.0
        bed_y = settings["bed_max_y"]

        def transform_pt(x_orig, y_orig):
            phys_x_base = posun_x + x_orig
            phys_y_base = posun_y + y_orig
            gui_x_base = phys_x_base
            gui_y_base = bed_y - phys_y_base
            gui_x_new = (gui_x_base - cx_t) * S + cx_t + gui_dx
            gui_y_new = (gui_y_base - cy_t) * S + cy_t + gui_dy
            return gui_x_new, bed_y - gui_y_new

        if is_prime:
            # Sekvence pro odpliv: čtverec 10x10 mm uprostřed skla
            cx, cy = posun_x + sw/2, posun_y + sh/2
            x1, x2 = cx - 5, cx + 5
            y1, y2 = cy - 5, cy + 5
            
            result.append(f"G0 Z{print_z + 2.0:.3f} F1000 ; Z-hop pro odpliv\n")
            result.append(f"G0 X{x1:.3f} Y{y1:.3f} F3000\n")
            result.append(f"G0 Z{print_z:.3f} F1000\n")
            result.append("M83 ; Relativní extruze\n")
            
            e_seg = 10.0 * loc_e_per_mm
            result.append(f"G1 X{x2:.3f} Y{y1:.3f} E{e_seg:.5f} F{loc_spd}\n")
            result.append(f"G1 X{x2:.3f} Y{y2:.3f} E{e_seg:.5f} F{loc_spd}\n")
            result.append(f"G1 X{x1:.3f} Y{y2:.3f} E{e_seg:.5f} F{loc_spd}\n")
            result.append(f"G1 X{x1:.3f} Y{y1:.3f} E{e_seg:.5f} F{loc_spd}\n")
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
                    
                    if loc_infill_style == "Tečky" and len(px) == 2 and px[0] == px[1]:
                        # SPECIÁLNÍ REŽIM: Tečky (Dávkování kapek)
                        # loc_ext v tomto případě interpretujeme jako µl na jednu kapku
                        dot_e = loc_ext / area 
                        
                        result.append(f"G0 Z{print_z + 2.0:.3f} F1000 ; Z-hop nad bod\n")
                        result.append(f"G0 X{abs_x:.3f} Y{abs_y:.3f} F3000\n")
                        result.append(f"G0 Z{print_z:.3f} F1000 ; Klesnuti k povrchu\n")
                        result.append(f"G1 E{dot_e:.5f} F300 ; Pomale davkovani kapky\n")
                        result.append(f"G0 Z{print_z + 2.0:.3f} F1000 ; Z-hop po davkovani\n")
                        continue

                    result.append(f"G0 Z{print_z + 2.0:.3f} F1000 ; Z-hop\n")
                    result.append(f"G0 X{abs_x:.3f} Y{abs_y:.3f} F3000\n")
                    result.append(f"G0 Z{print_z:.3f} F1000\n")
                    if is_retracted and retraction > 0:
                        result.append(f"G1 E{retraction:.5f} F{retract_speed} ; Deretrakce\n")
                        is_retracted = False
                    for j in range(1, len(px)):
                        ax_prev, ay_prev = transform_pt(px[j-1], py[j-1])
                        ax, ay = transform_pt(px[j], py[j])
                        dist = math.hypot(ax - ax_prev, ay - ay_prev)
                        result.append(f"G1 X{ax:.3f} Y{ay:.3f} E{dist * loc_e_per_mm:.5f} F{loc_spd}\n")
                    if retraction > 0:
                        result.append(f"G1 E{-retraction:.5f} F{retract_speed} ; Retrakce\n")
                        is_retracted = True
                result.append(f"G0 Z{print_z + 2.0:.3f} F1000\n")
            else:
                last_x, last_y = 0.0, 0.0
                for line in logic.original_lines:
                    orig_l = line.split(';')[0].strip()
                    comment = " ;" + line.split(';', 1)[1].strip() if ';' in line else ""
                    if not orig_l or orig_l.upper().startswith('M'):
                        result.append(line.rstrip() + "\n"); continue
                    orig_l_up = orig_l.upper(); modified_line = orig_l
                    if 'G1' in orig_l_up or 'G0' in orig_l_up:
                        mx = re.search(r'X([0-9\.\-]+)', orig_l_up); my = re.search(r'Y([0-9\.\-]+)', orig_l_up)
                        ox = float(mx.group(1)) if mx else last_x; oy = float(my.group(1)) if my else last_y
                        ax, ay = transform_pt(ox, oy)
                        if 'E' in orig_l_up:
                            lax, lay = transform_pt(last_x, last_y)
                            dist = math.hypot(ax - lax, ay - lay)
                            if dist > 0:
                                modified_line = re.sub(r'E([0-9\.\-]+)', f"E{dist * loc_e_per_mm:.5f}", modified_line, flags=re.I)
                                if 'F' in modified_line: modified_line = re.sub(r'F([0-9\.]+)', f"F{loc_spd}", modified_line, flags=re.I)
                                else: modified_line += f" F{loc_spd}"
                        if mx: modified_line = re.sub(r'X[0-9\.\-]+', f"X{ax:.3f}", modified_line, flags=re.I)
                        if my: modified_line = re.sub(r'Y[0-9\.\-]+', f"Y{ay:.3f}", modified_line, flags=re.I)
                        last_x, last_y = ox, oy
                    if 'Z' in orig_l_up: modified_line = re.sub(r'Z([0-9\.\-]+)', f"Z{print_z:.3f}", modified_line, flags=re.I)
                    result.append(modified_line + comment + "\n")            
            measurement_idx += 1

        result.append(settings["loop_end_gcode"])
        if not result[-1].endswith("\n"): result.append("\n")
        if typ_drzaku == "Na jeden vzorek" and not is_prime and measurement_idx < pocet_vzorku:
            result.append("; --- PAUZA PRO VÝMĚNU VZORKU ---\nG0 Z20.0 F1000\nG0 X10 Y200 F3000\nM0 Vymen vzorek\n")

    if typ_drzaku == "Multiplex (více sklíček)" and bed_temp > 0: result.append("M140 S0 ; Vypnout vyhrivani podlozky\n")
    result.append(settings["end_gcode"])
    if not result[-1].endswith("\n"): result.append("\n")
    return "".join(result)
