import csv

def export_protocol_csv(file_path, params):
    count = params.get('sample_count', 1)
    overrides = params.get('slide_overrides', {})
    
    headers = [
        "Slicko", "Nazev", "Poznamka", 
        "Typ_drzaku", "Typ_skla", "Sklo_X [mm]", "Sklo_Y [mm]", "Sklo_Z [mm]",
        "Teplota_podlozky [C]", "Tryska [mm]", "Retrakce [mm]", 
        "Styl_vyplne", "Uhel_vyplne",
        "Z-offset [mm]", "Extruze [ml/mm]", "Rychlost [mm/min]", 
        "Hustota_vyplne", "Jednotka_vyplne"
    ]
    
    with open(file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(headers)
        
        for i in range(count):
            slide_data = overrides.get(i, {})
            
            name = slide_data.get('name', f"Sklíčko {i+1}")
            note = slide_data.get('note', "")
            
            z_off = slide_data.get('z_offset', params.get('z_offset', 0.2))
            ext = slide_data.get('extrusion_rate', params.get('extrusion_rate', 0.05))
            spd = slide_data.get('print_speed', params.get('print_speed', 1500))
            inf = slide_data.get('infill_val', params.get('infill_val', 1.0))
            inf_t = slide_data.get('infill_type', params.get('infill_type', 'mm'))
            
            writer.writerow([
                i + 1, name, note,
                params.get('holder_type', ''), params.get('glass_type', ''), 
                params.get('slide_w', ''), params.get('slide_h', ''), params.get('slide_z', ''),
                params.get('bed_temp', ''), params.get('nozzle_diam', ''), 
                params.get('retraction', ''), params.get('infill_style', ''), params.get('infill_angle', ''),
                z_off, ext, spd, inf, inf_t
            ])
