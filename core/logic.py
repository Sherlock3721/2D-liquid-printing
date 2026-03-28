import os
import re
import math
from core.vector_slicer import VectorSlicer
from gui.settings import load_settings

# Skutečná fyzická tloušťka podkladu pod sklíčkem
HOLDER_THICKNESS = {
    "Na jeden vzorek": 4.0,
    "Multiplex (více sklíček)": 0.0 
}

def get_layout_positions(count, slide_w, slide_h, spacing, holder_type, bed_max_x, bed_max_y, prime_active=False):
    from gui.settings import load_settings
    settings = load_settings()
    
    start_x = settings.get("start_offset_x", 10.0)
    start_y = settings.get("start_offset_y", 10.0)
    
    positions = []
    # Formát: (x, y, w, h, is_prime)
    
    if holder_type == "Na jeden vzorek":
        # Hlavní vzorek (Front-Right)
        main_x = bed_max_x - start_x - slide_w
        positions.append((main_x, start_y, slide_w, slide_h, False))
        
        if prime_active:
            # Odpliv: 76x26 otočené na 26x76, posunuté o 20mm vlevo od hlavního skla
            # Standardní laboratorní sklo je 76x26 (zde otočené)
            p_w, p_h = 26.0, 76.0 
            p_x = main_x - 20.0 - p_w
            positions.append((p_x, start_y, p_w, p_h, True))
            
        return positions

    # Multiplex: Začínáme vpravo vpředu
    curr_x = bed_max_x - start_x - slide_w
    curr_y = start_y
    
    # Pro multiplex přidáme slot pro odpliv, pokud je aktivní
    actual_count = count + 1 if prime_active else count

    for i in range(actual_count):
        is_prime = (prime_active and i == 0)
        
        # Pokud přetečeme na výšku dozadu, posuneme se doleva na nový sloupec
        if curr_y + slide_h > bed_max_y and len(positions) > 0:
            curr_x -= (slide_w + spacing)
            curr_y = start_y

        if curr_x < 0:
            break

        positions.append((curr_x, curr_y, slide_w, slide_h, is_prime))
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
            
            for i in range(sample_count):
                vp = vector_params.copy()
                vp['user_scale'] = user_scales.get(i, 1.0)
                
                if i in slide_overrides:
                    vp['infill_val'] = slide_overrides[i].get('infill_val', vp['infill_val'])
                    vp['infill_type'] = slide_overrides[i].get('infill_type', vp.get('infill_type', 'mm'))
                
                try:
                    px, py = slicer.process(
                        path, vp['slide_w'], vp['slide_h'], vp.get('margin', 1.5), 
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
            
            with open(path, 'r') as f:
                for line in f:
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
