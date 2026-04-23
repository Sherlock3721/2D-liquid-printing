import math
import re
from svgpathtools import svg2paths, Line
from shapely.geometry import Polygon, LineString, MultiLineString
from shapely.ops import unary_union
from shapely.affinity import translate, scale, rotate
from shapely.validation import make_valid

class DXFParser:
    """Vlastní lehký parser pro DXF soubory zaměřený na 2D entity."""
    def __init__(self, path):
        self.path = path
        self.entities = []
        self.units = 0 # 0 = Unitless, 1 = Inches, 5 = CM, 6 = Meters
        self.dxf_to_mm = 1.0

    def parse(self):
        try:
            with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.readlines()
        except Exception:
            return []

        # Vyčištění řádků
        data = [line.strip() for line in content]
        
        self.entities = []
        i = 0
        current_entity = None
        
        while i < len(data) - 1:
            try:
                code = int(data[i])
                val = data[i+1]
                i += 2
            except:
                i += 1
                continue
            
            # Detekce jednotek v hlavičce ($INSUNITS)
            if code == 9 and val == "$INSUNITS":
                # Hledáme kód 70 v následujících pár řádcích
                for j in range(0, 10, 2):
                    if i + j + 1 < len(data) and data[i+j] == "70":
                        try:
                            self.units = int(data[i+j+1])
                            if self.units == 1: self.dxf_to_mm = 25.4      # Inches
                            elif self.units == 4: self.dxf_to_mm = 1.0     # Millimeters
                            elif self.units == 5: self.dxf_to_mm = 10.0    # Centimeters
                            elif self.units == 6: self.dxf_to_mm = 1000.0  # Meters
                            elif self.units == 8: self.dxf_to_mm = 25.4 * 12.0 # Feet
                            elif self.units == 11: self.dxf_to_mm = 1e-3   # Microns
                        except: pass
                        break
            
            # Začátek nové entity
            if code == 0:
                if val in ["LINE", "LWPOLYLINE", "CIRCLE", "ARC"]:
                    current_entity = {"type": val}
                    self.entities.append(current_entity)
                else:
                    current_entity = None
                continue

            # Přidávání dat k aktuální entitě
            if current_entity:
                if current_entity["type"] == "LWPOLYLINE":
                    if code == 10: # X souřadnice
                        if "pts" not in current_entity: current_entity["pts"] = []
                        current_entity["pts"].append([float(val), 0.0])
                    elif code == 20: # Y souřadnice
                        if "pts" in current_entity and current_entity["pts"]:
                            current_entity["pts"][-1][1] = float(val)
                else:
                    # Ostatní entity (LINE, CIRCLE, ARC)
                    if code in [10, 20, 11, 21, 40, 50, 51]:
                        if code not in current_entity:
                            current_entity[code] = []
                        current_entity[code].append(float(val))

        return self.convert_to_shapely()

    def convert_to_shapely(self):
        geoms = []
        for ent in self.entities:
            etype = ent.get("type")
            try:
                if etype == "LINE":
                    # LINE má vždy aspoň jeden bod 10,20 a 11,21
                    x1, y1 = ent[10][0], ent[20][0]
                    x2, y2 = ent[11][0], ent[21][0]
                    geoms.append(LineString([(x1*self.dxf_to_mm, y1*self.dxf_to_mm), (x2*self.dxf_to_mm, y2*self.dxf_to_mm)]))
                
                elif etype == "LWPOLYLINE":
                    pts_raw = ent.get("pts", [])
                    # Přepočet na milimetry a zajištění 2D
                    pts = [(p[0]*self.dxf_to_mm, p[1]*self.dxf_to_mm) for p in pts_raw]
                    if len(pts) >= 2:
                        geoms.append(LineString(pts))

                elif etype == "CIRCLE" or etype == "ARC":
                    cx, cy = ent[10][0] * self.dxf_to_mm, ent[20][0] * self.dxf_to_mm
                    r = ent.get(40, 0) * self.dxf_to_mm
                    if r <= 0: continue
                    
                    start_angle = ent.get(50, 0.0)
                    end_angle = ent.get(51, 360.0) if etype == "ARC" else 360.0
                    
                    # Aproximace kružnice/oblouku úsečkami
                    num_segments = 64
                    pts = []
                    if etype == "CIRCLE":
                        for a in range(num_segments + 1):
                            ang = math.radians(a * 360.0 / num_segments)
                            pts.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
                    else:
                        # ARC
                        if end_angle < start_angle: end_angle += 360
                        span = end_angle - start_angle
                        seg_count = max(2, int(num_segments * span / 360))
                        for a in range(seg_count + 1):
                            ang = math.radians(start_angle + a * span / seg_count)
                            pts.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
                    
                    if len(pts) >= 2:
                        geoms.append(LineString(pts))
            except: continue
        return geoms

class NeedsScalingError(Exception):
    def __init__(self, w, h, max_w, max_h):
        self.w = w
        self.h = h
        self.max_w = max_w
        self.max_h = max_h
        super().__init__("Tvar je příliš velký.")
        
class VectorSlicer:
    def __init__(self):
        self.geometries = []

    def load_svg(self, path):
        paths, _ = svg2paths(path)
        self.geometries = []
        for p in paths:
            if p.length() == 0: continue
            subpaths = p.continuous_subpaths()
            sub_polygons = []
            sub_lines = []
            for sub_p in subpaths:
                if sub_p.length() == 0: continue
                
                # Pokud je to přímka, stačí nám 2 body (start a konec)
                if isinstance(sub_p, Line):
                    coords = [(sub_p.start.real, sub_p.start.imag), (sub_p.end.real, sub_p.end.imag)]
                else:
                    # Pro křivky použijeme vzorkování
                    num_points = max(2, int(sub_p.length() * 10))
                    points = [sub_p.point(i/(num_points-1)) for i in range(num_points)]
                    coords = [(pt.real, pt.imag) for pt in points]
                
                if sub_p.isclosed() and len(coords) >= 3:
                    poly = Polygon(coords)
                    if not poly.is_valid:
                        poly = make_valid(poly)
                    if poly.geom_type == 'Polygon':
                        sub_polygons.append(poly)
                    elif poly.geom_type in ['MultiPolygon', 'GeometryCollection']:
                        for geom in getattr(poly, 'geoms', []):
                            if geom.geom_type == 'Polygon':
                                sub_polygons.append(geom)
                else:
                    sub_lines.append(LineString(coords))
            if sub_polygons:
                final_poly = sub_polygons[0]
                for poly in sub_polygons[1:]:
                    final_poly = final_poly.symmetric_difference(poly)
                if not final_poly.is_valid:
                    final_poly = make_valid(final_poly)
                if final_poly.geom_type == 'Polygon':
                    self.geometries.append(final_poly)
                elif final_poly.geom_type in ['MultiPolygon', 'GeometryCollection']:
                    for geom in getattr(final_poly, 'geoms', []):
                        if geom.geom_type == 'Polygon':
                            self.geometries.append(geom)
            self.geometries.extend(sub_lines)

    def load_dxf(self, path_str):
        parser = DXFParser(path_str)
        self.geometries = parser.parse()

    def process(self, filepath, slide_w, slide_h, margin, auto_scale=False, params=None):
        if params is None: params = {}
        ext = filepath.lower()
        if ext.endswith('.svg'):
            self.load_svg(filepath)
            self.geometries = [scale(g, xfact=1.0, yfact=-1.0, origin=(0, 0)) for g in self.geometries]
        elif ext.endswith('.dxf'):
            self.load_dxf(filepath)
            self.geometries = [scale(g, xfact=1.0, yfact=-1.0, origin=(0, 0)) for g in self.geometries]
        else:
            raise ValueError("Nepodporovaný formát souboru.")
        return self.process_geometries(self.geometries, slide_w, slide_h, margin, auto_scale, params)

    def process_geometries(self, geometries, slide_w, slide_h, margin, auto_scale=False, params=None):
        if not geometries:
            raise ValueError("Geometrie je prázdná.")
        if params is None: params = {}

        # 1. Normalizace: Posuneme vše tak, aby bounding box začínal na (0,0)
        merged_init = unary_union(geometries)
        minx, miny, maxx, maxy = merged_init.bounds
        normalized_geoms = [translate(g, xoff=-minx, yoff=-miny) for g in geometries]
        
        width, height = maxx - minx, maxy - miny
        
        # 2. Automatické měřítko, pokud je potřeba
        if width > slide_w + 0.1 or height > slide_h + 0.1:
            if auto_scale:
                scale_f = min((slide_w - 2*margin)/width, (slide_h - 2*margin)/height)
                normalized_geoms = [scale(g, xfact=scale_f, yfact=scale_f, origin=(0,0)) for g in normalized_geoms]
                width, height = width*scale_f, height*scale_f
            else:
                raise NeedsScalingError(width, height, slide_w, slide_h)

        # 3. Vycentrování na sklíčku
        offset_x, offset_y = (slide_w - width)/2.0, (slide_h - height)/2.0
        centered_geoms = [translate(g, xoff=offset_x, yoff=offset_y) for g in normalized_geoms]
        
        user_scale = params.get('user_scale', 1.0)
        if user_scale != 1.0:
            merged_c = unary_union(centered_geoms)
            c_minx, c_maxy = merged_c.bounds[0], merged_c.bounds[3]
            centered_geoms = [scale(g, xfact=user_scale, yfact=user_scale, origin=(c_minx, c_maxy)) for g in centered_geoms]

        # 3.5 Optimalizace pořadí objektů (Nearest Neighbor podle centroidů)
        if centered_geoms:
            opt_geoms = []
            curr_pt = (0, 0)
            unvisited = list(centered_geoms)
            while unvisited:
                best_geom = None
                best_dist = float('inf')
                for g in unvisited:
                    gc = g.centroid
                    dist = (curr_pt[0] - gc.x)**2 + (curr_pt[1] - gc.y)**2
                    if dist < best_dist:
                        best_dist = dist
                        best_geom = g
                opt_geoms.append(best_geom)
                curr_pt = (best_geom.centroid.x, best_geom.centroid.y)
                unvisited.remove(best_geom)
            centered_geoms = opt_geoms

        # 4. Finalizace cest (Simplifikace a řazení: Perimetr -> Infill pro každý objekt)
        path_x, path_y = [], []
        infill_style = params.get('infill_style', 'S okraji')
        infill_val = params.get('infill_val', 1.0)
        infill_type = params.get('infill_type', 'mm')
        infill_angle = params.get('infill_angle', 0)
        nozzle_diam = params.get('nozzle_diam', 0.4)
        infill_spacing = nozzle_diam / (infill_val / 100.0) if infill_type == "%" and infill_val > 0 else infill_val
        
        # Tolerance pro zjednodušení (0.1 mm je bezpečný kompromis pro kapaliny)
        SIMPLIFY_TOLERANCE = 0.1

        def optimize_subpaths(px_list, py_list, start_pt):
            if not px_list: return [], [], start_pt
            opt_x, opt_y = [], []
            curr_pt = start_pt
            unvisited = list(range(len(px_list)))
            
            while unvisited:
                best_idx = -1
                best_dist = float('inf')
                reverse_path = False
                
                for i in unvisited:
                    # Ochrana proti prázdným seznamům bodů
                    if not px_list[i] or not py_list[i]:
                        continue

                    s_pt = (px_list[i][0], py_list[i][0])
                    e_pt = (px_list[i][-1], py_list[i][-1])
                    
                    d_start = (curr_pt[0] - s_pt[0])**2 + (curr_pt[1] - s_pt[1])**2
                    if d_start < best_dist:
                        best_dist = d_start
                        best_idx = i
                        reverse_path = False
                        
                    d_end = (curr_pt[0] - e_pt[0])**2 + (curr_pt[1] - e_pt[1])**2
                    if d_end < best_dist:
                        best_dist = d_end
                        best_idx = i
                        reverse_path = True
                
                if best_idx == -1: # Pokud jsme nenašli žádný platný bod (vše prázdné)
                    for i in unvisited: unvisited.remove(i)
                    break
                
                # Pokud je vzdálenost k dalšímu bodu téměř nulová (< 0.05 mm),
                # spojíme body do jednoho seznamu (v rámci opt_x[-1]) místo přidání nového seznamu.
                JOIN_THRESHOLD_SQ = 0.05**2
                can_join = False
                if opt_x and best_dist < JOIN_THRESHOLD_SQ:
                    can_join = True

                new_seg_x = px_list[best_idx][::-1] if reverse_path else px_list[best_idx]
                new_seg_y = py_list[best_idx][::-1] if reverse_path else py_list[best_idx]

                if can_join:
                    # Přidáme body k poslednímu existujícímu segmentu (vynecháme první bod, je duplicitní)
                    opt_x[-1].extend(new_seg_x[1:])
                    opt_y[-1].extend(new_seg_y[1:])
                else:
                    opt_x.append(new_seg_x)
                    opt_y.append(new_seg_y)
                
                curr_pt = (opt_x[-1][-1], opt_y[-1][-1])
                unvisited.remove(best_idx)
            return opt_x, opt_y, curr_pt

        global_curr_pt = (0, 0)

        for geom in centered_geoms:
            # Zjednodušení geometrie pro redukci mikrosegmentů
            geom = geom.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
            
            if infill_style == "Tečky":
                from shapely.geometry import Point
                obj_px, obj_py = [], []
                if isinstance(geom, Polygon):
                    centroid = geom.centroid
                    rot_g = make_valid(rotate(geom, -infill_angle, origin=centroid)) if infill_angle != 0 else geom
                    if not rot_g.is_empty:
                        bx1, by1, bx2, by2 = rot_g.bounds
                        y_c = by1 + (infill_spacing/2.0)
                        while y_c < by2:
                            x_c = bx1 + (infill_spacing/2.0)
                            while x_c < bx2:
                                pt = Point(x_c, y_c)
                                if rot_g.contains(pt):
                                    res_pt = rotate(pt, infill_angle, origin=centroid) if infill_angle != 0 else pt
                                    obj_px.append([res_pt.x, res_pt.x])
                                    obj_py.append([res_pt.y, res_pt.y])
                                x_c += infill_spacing
                            y_c += infill_spacing
                elif isinstance(geom, (LineString, MultiLineString)):
                    lines = geom.geoms if hasattr(geom, 'geoms') else [geom]
                    for line in lines:
                        dist = 0.0
                        while dist <= line.length:
                            pt = line.interpolate(dist)
                            obj_px.append([pt.x, pt.x])
                            obj_py.append([pt.y, pt.y])
                            dist += infill_spacing if infill_spacing > 0 else line.length + 1
                            
                ox, oy, global_curr_pt = optimize_subpaths(obj_px, obj_py, global_curr_pt)
                path_x.extend(ox)
                path_y.extend(oy)
                continue

            obj_perim_x, obj_perim_y = [], []
            obj_infill_x, obj_infill_y = [], []

            if isinstance(geom, Polygon):
                # --- PERIMETR OBJEKTU ---
                if infill_style in ["S okraji", "Okraje"]:
                    obj_perim_x.append(list(geom.exterior.xy[0]))
                    obj_perim_y.append(list(geom.exterior.xy[1]))
                    for interior in geom.interiors:
                        obj_perim_x.append(list(interior.xy[0]))
                        obj_perim_y.append(list(interior.xy[1]))
                        
                # --- INFILL OBJEKTU (hned po jeho perimetru) ---
                if infill_style in ["S okraji", "Bez okrajů", "Had"] and infill_spacing > 0:
                    centroid = geom.centroid
                    rot_g = make_valid(rotate(geom, -infill_angle, origin=centroid)) if infill_angle != 0 else geom
                    if not rot_g.is_empty:
                        bx1, by1, bx2, by2 = rot_g.bounds
                        y_f = by1 + (infill_spacing/2.0)
                        grid = []
                        while y_f < by2:
                            grid.append(LineString([(bx1-1, y_f), (bx2+1, y_f)]))
                            y_f += infill_spacing
                        if grid:
                            inter = rot_g.intersection(MultiLineString(grid))
                            lines = []
                            if isinstance(inter, LineString):
                                lines.append(inter)
                            elif hasattr(inter, 'geoms'):
                                lines.extend([l for l in inter.geoms if isinstance(l, LineString)])
                            
                        if infill_style == "Had":
                            by_y = {}
                            for l in lines:
                                yv = round(l.coords[0][1], 4)
                                if yv not in by_y: by_y[yv] = []
                                by_y[yv].append(l)
                            sorted_y = sorted(by_y.keys())
                            rev = False
                            curr_had_x, curr_had_y = [], []
                            for y_idx, yv in enumerate(sorted_y):
                                row = sorted(by_y[yv], key=lambda l: l.coords[0][0])
                                if rev:
                                    row.reverse()
                                for seg_idx, l in enumerate(row):
                                    fl = rotate(l, infill_angle, origin=centroid) if infill_angle != 0 else l
                                    lx, ly = list(fl.xy[0]), list(fl.xy[1])
                                    if rev:
                                        lx.reverse()
                                        ly.reverse()
                                    if seg_idx == 0:
                                        curr_had_x.extend(lx)
                                        curr_had_y.extend(ly)
                                    else:
                                        obj_infill_x.append(curr_had_x)
                                        obj_infill_y.append(curr_had_y)
                                        curr_had_x, curr_had_y = lx, ly
                                rev = not rev
                            if curr_had_x:
                                obj_infill_x.append(curr_had_x)
                                obj_infill_y.append(curr_had_y)
                        else:
                            for l in lines:
                                fl = rotate(l, infill_angle, origin=centroid) if infill_angle != 0 else l
                                obj_infill_x.append(list(fl.xy[0]))
                                obj_infill_y.append(list(fl.xy[1]))
            elif isinstance(geom, (LineString, MultiLineString)):
                # --- STROKES (Neuzavřené cesty) ---
                if hasattr(geom, 'geoms'):
                    for g in geom.geoms:
                        obj_perim_x.append(list(g.xy[0]))
                        obj_perim_y.append(list(g.xy[1]))
                else:
                    obj_perim_x.append(list(geom.xy[0]))
                    obj_perim_y.append(list(geom.xy[1]))

            # Optimalizace a spojení perimetru a infillu pro tento objekt
            if obj_perim_x:
                ox, oy, global_curr_pt = optimize_subpaths(obj_perim_x, obj_perim_y, global_curr_pt)
                path_x.extend(ox)
                path_y.extend(oy)
                
            if obj_infill_x:
                ox, oy, global_curr_pt = optimize_subpaths(obj_infill_x, obj_infill_y, global_curr_pt)
                path_x.extend(ox)
                path_y.extend(oy)

        return path_x, path_y
