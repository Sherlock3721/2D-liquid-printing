import os
import re
import math
from core.vector_slicer import VectorSlicer
from gui.settings import load_settings

# Skutečná fyzická tloušťka podkladu pod sklíčkem
HOLDER_THICKNESS = {
    "Multiplex (více sklíček)": 0.0 
}

def get_layout_positions(count, slide_w, slide_h, spacing, holder_type, bed_max_x, bed_max_y, prime_active=False):
    from gui.settings import load_settings
    settings = load_settings()
    
    start_x = settings.get("start_offset_x", 10.0)
    start_y = settings.get("start_offset_y", 10.0)
    
    positions = []
    # Formát: (x, y, w, h, is_prime)
    
    # Multiplex: Začínáme vpravo vpředu
    curr_y = start_y
    base_right = bed_max_x - start_x
    
    # Šířka aktuálního sloupce (první sloupec může být širší kvůli odplivu)
    current_col_w = max(76.0, slide_w) if prime_active else slide_w
    curr_col_left = base_right - current_col_w
    
    if prime_active:
        p_w, p_h = 76.0, 26.0
        # Odpliv zarovnáme k pravému okraji (base_right)
        p_x = base_right - p_w
        positions.append((p_x, curr_y, p_w, p_h, True))
        curr_y += (p_h + spacing)

    for i in range(count):
        # Pokud přetečeme na výšku dozadu, posuneme se doleva na NOVÝ SLOUPEC
        if curr_y + slide_h > bed_max_y and len(positions) > 0:
            # Nový pravý okraj je vlevo od nejlevnějšího bodu předchozího sloupce
            base_right = curr_col_left - spacing
            current_col_w = slide_w # Další sloupce už nemají prime slide
            curr_col_left = base_right - current_col_w
            curr_y = start_y

        # Pozice vzorku (vždy vpravo v rámci svého aktuálního sloupce)
        sample_x = base_right - slide_w
        
        if sample_x < 0:
            break

        positions.append((sample_x, curr_y, slide_w, slide_h, False))
        curr_y += (slide_h + spacing)

    return positions

class GCodeLogic:
    def __init__(self):
        self.filepath = None
        self.original_lines = []
        self.path_x = []
        self.path_y = []
        self.travel_x = []
        self.travel_y = []
        self.is_vector = False

    def load_file(self, path, vector_params=None, auto_scale=False, user_scales=None, sample_count=1, slide_overrides=None):
        self.filepath = path
        self.original_lines = []
        self.path_x, self.path_y = [], []
        self.travel_x, self.travel_y = [], []
        self.paths_by_index = {} 
        self.is_vector = path.lower().endswith(('.svg', '.dxf'))

        if self.is_vector:
            if not vector_params: return
            slicer = VectorSlicer()
            if user_scales is None: user_scales = {}
            if slide_overrides is None: slide_overrides = {}
            
            # 1. Načteme geometrii jednou (bez měřítka a centrování prozatím)
            if path.lower().endswith('.svg'):
                slicer.load_svg(path)
                from shapely.affinity import scale
                slicer.geometries = [scale(g, xfact=1.0, yfact=-1.0, origin=(0, 0)) for g in slicer.geometries]
            else:
                slicer.load_dxf(path)
                from shapely.affinity import scale
                slicer.geometries = [scale(g, xfact=1.0, yfact=-1.0, origin=(0, 0)) for g in slicer.geometries]
            
            base_geometries = slicer.geometries
            
            # 2. Pro každé sklíčko aplikujeme specifické parametry (infill, měřítko)
            for i in range(sample_count):
                vp = vector_params.copy()
                vp['user_scale'] = user_scales.get(i, 1.0)
                
                if i in slide_overrides:
                    vp['infill_val'] = slide_overrides[i].get('infill_val', vp['infill_val'])
                    vp['infill_type'] = slide_overrides[i].get('infill_type', vp.get('infill_type', 'mm'))
                
                # Slicer.process_geometries (vytvoříme si ji v sliceru) provede zbytek
                try:
                    px, py = slicer.process_geometries(
                        base_geometries, vp['slide_w'], vp['slide_h'], vp.get('margin', 1.5), 
                        auto_scale=auto_scale, params=vp
                    )
                    self.paths_by_index[i] = {'x': px, 'y': py}
                except Exception as e:
                    if i == 0: raise e
                    else: self.paths_by_index[i] = {'x': [], 'y': []}
                                   
            if 0 in self.paths_by_index:
                self.path_x = self.paths_by_index[0]['x']
                self.path_y = self.paths_by_index[0]['y']
                
            for i in range(len(self.path_x) - 1):
                self.travel_x.append([self.path_x[i][-1], self.path_x[i+1][0]])
                self.travel_y.append([self.path_y[i][-1], self.path_y[i+1][0]])
        else:
            cur_x, cur_y = 0.0, 0.0
            current_segment_x, current_segment_y = [], []
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                # Fallback pro staré soubory na Windows
                with open(path, 'r', encoding='cp1250') as f:
                    lines = f.readlines()

            for line in lines:
                self.original_lines.append(line)
                clean_line = line.split(';')[0].upper().strip()
                
                if 'G0' in clean_line or 'G1' in clean_line:
                    mx = re.search(r'X([0-9\.\-]+)', clean_line)
                    my = re.search(r'Y([0-9\.\-]+)', clean_line)
                    new_x = float(mx.group(1)) if mx else cur_x
                    new_y = float(my.group(1)) if my else cur_y
                    
                    if clean_line.startswith('G0'):
                        if len(current_segment_x) > 1:
                            self.path_x.append(current_segment_x)
                            self.path_y.append(current_segment_y)
                        current_segment_x = [new_x]
                        current_segment_y = [new_y]
                        self.travel_x.append([cur_x, new_x])
                        self.travel_y.append([cur_y, new_y])
                    else:
                        current_segment_x.append(new_x)
                        current_segment_y.append(new_y)
                    
                    cur_x, cur_y = new_x, new_y
                        
                if len(current_segment_x) > 1:
                    self.path_x.append(current_segment_x)
                    self.path_y.append(current_segment_y)

    def generate_gcode(self, params):
        from core.gcode_generator import generate_gcode
        return generate_gcode(self, params)
