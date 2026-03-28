import ezdxf
from svgpathtools import svg2paths
from shapely.geometry import Polygon, LineString, MultiLineString
from shapely.ops import unary_union
from shapely.affinity import translate, scale, rotate
from shapely.validation import make_valid

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
            
            # 1. Rozdělení složené cesty (např. tvar + díra) na samostatné smyčky
            subpaths = p.continuous_subpaths()
            sub_polygons = []
            sub_lines = []
            
            for sub_p in subpaths:
                if sub_p.length() == 0: continue
                
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

            # 2. Sloučení polygonů (vytvoření děr pomocí symetrické diference / XOR)
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
                            
            # 3. Přidání případných volných čar
            self.geometries.extend(sub_lines)

    def load_dxf(self, path):
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        self.geometries = []
        for entity in msp:
            if entity.dxftype() == 'LWPOLYLINE':
                coords = [(p[0], p[1]) for p in entity.get_points(format='xy')]
                if entity.closed and len(coords) >= 3:
                    poly = Polygon(coords)
                    if not poly.is_valid:
                        poly = make_valid(poly)
                    if poly.geom_type == 'Polygon':
                        self.geometries.append(poly)
                else:
                    self.geometries.append(LineString(coords))
            elif entity.dxftype() == 'LINE':
                self.geometries.append(LineString([(entity.dxf.start.x, entity.dxf.start.y), 
                                                   (entity.dxf.end.x, entity.dxf.end.y)]))

    def process(self, filepath, slide_w, slide_h, margin, auto_scale=False, params=None):
        if params is None: params = {}
            
        ext = filepath.lower()
        if ext.endswith('.svg'):
            self.load_svg(filepath)
            # Invertujeme Y pro SVG
            self.geometries = [scale(g, xfact=1.0, yfact=-1.0, origin=(0, 0)) for g in self.geometries]
        elif ext.endswith('.dxf'):
            self.load_dxf(filepath)
        else:
            raise ValueError("Nepodporovaný formát souboru.")

        if not self.geometries:
            raise ValueError("Soubor neobsahuje žádné platné křivky k tisku.")

        # 1. Čisté zarovnání do 0,0
        merged = unary_union(self.geometries)
        minx, miny, maxx, maxy = merged.bounds
        self.geometries = [translate(g, xoff=-minx, yoff=-miny) for g in self.geometries]

        width = maxx - minx
        height = maxy - miny
        
        tolerance = 0.1 # Drobná tolerance pro šířky čar ze SVG

        # 2. Zjištění zda se musí měnit velikost (KONTROLA POUZE VŮČI ČISTÉMU SKLU)
        if width > slide_w + tolerance or height > slide_h + tolerance:
            if auto_scale:
                # Je to VĚTŠÍ než fyzické sklo. Smrskneme to.
                # Nyní aplikujeme margin, aby zmenšený objekt nebyl úplně na hraně skla.
                target_w = max(1.0, slide_w - 2 * margin)
                target_h = max(1.0, slide_h - 2 * margin)
                
                scale_factor = min(target_w / width, target_h / height)
                self.geometries = [scale(g, xfact=scale_factor, yfact=scale_factor, origin=(0,0)) for g in self.geometries]
                width *= scale_factor
                height *= scale_factor
            else:
                # Je to větší než sklo, ale zatím nemáme povolení zmenšovat -> vyhodíme chybu
                raise NeedsScalingError(width, height, slide_w, slide_h)

        # 3. Vycentrování na podložku
        # (Pokud je soubor přesně velký jako sklo, width i height jsou stejné a offset vyjde přesně 0.0)
        offset_x = (slide_w - width) / 2.0
        offset_y = (slide_h - height) / 2.0
        centered_geoms = [translate(g, xoff=offset_x, yoff=offset_y) for g in self.geometries]

        # 4. Aplikace fyzického měřítka od uživatele
        user_scale = params.get('user_scale', 1.0)
        if user_scale != 1.0:
            merged_c = unary_union(centered_geoms)
            c_minx, c_miny, c_maxx, c_maxy = merged_c.bounds
            centered_geoms = [scale(g, xfact=user_scale, yfact=user_scale, origin=(c_minx, c_maxy)) for g in centered_geoms]

        # 5. Generování infillu a okrajů
        path_x, path_y = [], []
        infill_style = params.get('infill_style', 'S okraji')
        infill_val = params.get('infill_val', 1.0)
        infill_type = params.get('infill_type', 'mm')
        infill_angle = params.get('infill_angle', 0)
        nozzle_diam = params.get('nozzle_diam', 0.4)

        infill_spacing = nozzle_diam / (infill_val / 100.0) if infill_type == "%" and infill_val > 0 else infill_val

        for geom in centered_geoms:
            if infill_style == "Dot Dispenser":
                from shapely.geometry import Point
                if isinstance(geom, Polygon):
                    centroid = geom.centroid
                    # Rotujeme polygon pro výpočet mřížky pod úhlem
                    rotated_geom = make_valid(rotate(geom, -infill_angle, origin=centroid)) if infill_angle != 0 else geom
                    if rotated_geom.is_empty: continue
                    
                    g_minx, g_miny, g_maxx, g_maxy = rotated_geom.bounds
                    
                    # Generování mřížky bodů
                    y_curr = g_miny + (infill_spacing / 2.0)
                    while y_curr < g_maxy:
                        x_curr = g_minx + (infill_spacing / 2.0)
                        while x_curr < g_maxx:
                            pt = Point(x_curr, y_curr)
                            if rotated_geom.contains(pt):
                                # Rotace bodu zpět do původní orientace
                                res_pt = rotate(pt, infill_angle, origin=centroid) if infill_angle != 0 else pt
                                path_x.append([res_pt.x, res_pt.x])
                                path_y.append([res_pt.y, res_pt.y])
                            x_curr += infill_spacing
                        y_curr += infill_spacing
                
                elif isinstance(geom, (LineString, MultiLineString)):
                    # Pro čáry vygenerujeme body podél trasy
                    lines = geom.geoms if hasattr(geom, 'geoms') else [geom]
                    for line in lines:
                        length = line.length
                        dist = 0.0
                        while dist <= length:
                            pt = line.interpolate(dist)
                            path_x.append([pt.x, pt.x])
                            path_y.append([pt.y, pt.y])
                            dist += infill_spacing if infill_spacing > 0 else length + 1
                continue

            if isinstance(geom, Polygon):
                if infill_style in ["S okraji", "Okraje"]:
                    x, y = geom.exterior.xy
                    path_x.append(list(x))
                    path_y.append(list(y))
                    
                    for interior in geom.interiors:
                        ix, iy = interior.xy
                        path_x.append(list(ix))
                        path_y.append(list(iy))
                    
                if infill_style in ["S okraji", "Bez okrajů", "Had"] and infill_spacing > 0:
                    centroid = geom.centroid
                    rotated_geom = make_valid(rotate(geom, -infill_angle, origin=centroid)) if infill_angle != 0 else geom
                        
                    if rotated_geom.is_empty: continue

                    g_minx, g_miny, g_maxx, g_maxy = rotated_geom.bounds
                    y_infill = g_miny + (infill_spacing / 2.0)
                    grid_lines = []
                    
                    while y_infill < g_maxy:
                        grid_lines.append(LineString([(g_minx - 1, y_infill), (g_maxx + 1, y_infill)]))
                        y_infill += infill_spacing
                    
                    if grid_lines:
                        intersection = rotated_geom.intersection(MultiLineString(grid_lines))
                        if infill_angle != 0:
                            intersection = rotate(intersection, infill_angle, origin=centroid)
                        
                        intersect_lines = []
                        if isinstance(intersection, LineString):
                            intersect_lines.append(intersection)
                        elif hasattr(intersection, 'geoms'):
                            intersect_lines.extend([l for l in intersection.geoms if isinstance(l, LineString)])
                        
                        if infill_style == "Had":
                            had_x, had_y = [], []
                            reverse = False
                            for line in intersect_lines:
                                lx, ly = list(line.xy[0]), list(line.xy[1])
                                if reverse:
                                    lx.reverse()
                                    ly.reverse()
                                had_x.extend(lx)
                                had_y.extend(ly)
                                reverse = not reverse
                            if had_x:
                                path_x.append(had_x)
                                path_y.append(had_y)
                        else:
                            for line in intersect_lines:
                                x, y = line.xy
                                path_x.append(list(x))
                                path_y.append(list(y))
            
            elif isinstance(geom, LineString):
                x, y = geom.xy
                path_x.append(list(x))
                path_y.append(list(y))

        return path_x, path_y
