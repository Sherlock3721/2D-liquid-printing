import ezdxf
import math
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
        from ezdxf import path as dxfpath
        try:
            doc = ezdxf.readfile(path_str)
        except Exception as e:
            try:
                doc = ezdxf.readfile(path_str, encoding='cp1250')
            except:
                raise ValueError(f"Nelze načíst DXF soubor: {e}")
                
        # Detekce jednotek DXF
        # 1: Inches, 4: Millimeters, 5: Centimeters, 6: Meters
        units = doc.header.get('$INSUNITS', 0)
        dxf_to_mm = 1.0
        if units == 1: dxf_to_mm = 25.4
        elif units == 5: dxf_to_mm = 10.0
        elif units == 6: dxf_to_mm = 1000.0
        
        msp = doc.modelspace()
        self.geometries = []
        
        try:
            # Renderování všech entit (včetně bloků INSERT) do objektů Path
            all_paths = list(dxfpath.render_paths(msp))
            
            # Klíčový krok: Seskupení cest podle toho, která je uvnitř které (otvory)
            # nest_paths vrací seznam top-level cest, které mají v sobě uložené děti (otvory)
            nested_paths = dxfpath.nest_paths(all_paths)
            
            def process_nested_path(p):
                coords = list(p.flattening(distance=0.1))
                if not coords: return
                
                # Aplikace měřítka jednotek
                if dxf_to_mm != 1.0:
                    coords = [(x * dxf_to_mm, y * dxf_to_mm) for x, y in coords]
                
                is_closed = p.is_closed
                if not is_closed and len(coords) >= 3:
                    d = math.hypot(coords[0][0] - coords[-1][0], coords[0][1] - coords[-1][1])
                    if d < 0.01: is_closed = True
                
                if is_closed and len(coords) >= 3:
                    holes = []
                    # Zpracování otvorů (dětí této cesty)
                    if hasattr(p, 'children'):
                        for child in p.children:
                            child_coords = list(child.flattening(distance=0.1))
                            if len(child_coords) >= 3:
                                if dxf_to_mm != 1.0:
                                    child_coords = [(x * dxf_to_mm, y * dxf_to_mm) for x, y in child_coords]
                                holes.append(child_coords)
                    
                    try:
                        poly = Polygon(coords, holes)
                        if not poly.is_valid:
                            poly = make_valid(poly)
                        
                        if poly.geom_type == 'Polygon':
                            self.geometries.append(poly)
                        elif poly.geom_type in ['MultiPolygon', 'GeometryCollection']:
                            for g in getattr(poly, 'geoms', []):
                                if g.geom_type == 'Polygon':
                                    self.geometries.append(g)
                    except:
                        self.geometries.append(LineString(coords))
                elif len(coords) >= 2:
                    self.geometries.append(LineString(coords))
            
            for p in nested_paths:
                process_nested_path(p)
                
        except Exception as e:
            print(f"Chyba při renderování DXF: {e}")
            # Nouzový fallback
            for entity in msp:
                try:
                    p = dxfpath.make_path(entity)
                    coords = list(p.flattening(distance=0.1))
                    if len(coords) >= 2:
                        if dxf_to_mm != 1.0:
                            coords = [(x * dxf_to_mm, y * dxf_to_mm) for x, y in coords]
                        self.geometries.append(LineString(coords))
                except: continue

    def process(self, filepath, slide_w, slide_h, margin, auto_scale=False, params=None):
        if params is None: params = {}
        ext = filepath.lower()
        if ext.endswith('.svg'):
            self.load_svg(filepath)
            self.geometries = [scale(g, xfact=1.0, yfact=-1.0, origin=(0, 0)) for g in self.geometries]
        elif ext.endswith('.dxf'):
            self.load_dxf(filepath)
        else:
            raise ValueError("Nepodporovaný formát souboru.")
        if not self.geometries:
            raise ValueError("Soubor neobsahuje žádné platné křivky k tisku.")

        merged = unary_union(self.geometries)
        minx, miny, maxx, maxy = merged.bounds
        self.geometries = [translate(g, xoff=-minx, yoff=-miny) for g in self.geometries]
        width, height = maxx - minx, maxy - miny
        
        if width > slide_w + 0.1 or height > slide_h + 0.1:
            if auto_scale:
                scale_f = min((slide_w - 2*margin)/width, (slide_h - 2*margin)/height)
                self.geometries = [scale(g, xfact=scale_f, yfact=scale_f, origin=(0,0)) for g in self.geometries]
                width, height = width*scale_f, height*scale_f
            else:
                raise NeedsScalingError(width, height, slide_w, slide_h)

        offset_x, offset_y = (slide_w - width)/2.0, (slide_h - height)/2.0
        centered_geoms = [translate(g, xoff=offset_x, yoff=offset_y) for g in self.geometries]
        
        user_scale = params.get('user_scale', 1.0)
        if user_scale != 1.0:
            merged_c = unary_union(centered_geoms)
            c_minx, c_maxy = merged_c.bounds[0], merged_c.bounds[3]
            centered_geoms = [scale(g, xfact=user_scale, yfact=user_scale, origin=(c_minx, c_maxy)) for g in centered_geoms]

        path_x, path_y = [], []
        infill_style = params.get('infill_style', 'S okraji')
        infill_val = params.get('infill_val', 1.0)
        infill_type = params.get('infill_type', 'mm')
        infill_angle = params.get('infill_angle', 0)
        nozzle_diam = params.get('nozzle_diam', 0.4)
        infill_spacing = nozzle_diam / (infill_val / 100.0) if infill_type == "%" and infill_val > 0 else infill_val

        for geom in centered_geoms:
            if infill_style == "Tečky":
                from shapely.geometry import Point
                if isinstance(geom, Polygon):
                    centroid = geom.centroid
                    rot_g = make_valid(rotate(geom, -infill_angle, origin=centroid)) if infill_angle != 0 else geom
                    if rot_g.is_empty: continue
                    bx1, by1, bx2, by2 = rot_g.bounds
                    y_c = by1 + (infill_spacing/2.0)
                    while y_c < by2:
                        x_c = bx1 + (infill_spacing/2.0)
                        while x_c < bx2:
                            pt = Point(x_c, y_c)
                            if rot_g.contains(pt):
                                res_pt = rotate(pt, infill_angle, origin=centroid) if infill_angle != 0 else pt
                                path_x.append([res_pt.x, res_pt.x])
                                path_y.append([res_pt.y, res_pt.y])
                            x_c += infill_spacing
                        y_c += infill_spacing
                elif isinstance(geom, (LineString, MultiLineString)):
                    lines = geom.geoms if hasattr(geom, 'geoms') else [geom]
                    for line in lines:
                        dist = 0.0
                        while dist <= line.length:
                            pt = line.interpolate(dist)
                            path_x.append([pt.x, pt.x])
                            path_y.append([pt.y, pt.y])
                            dist += infill_spacing if infill_spacing > 0 else line.length + 1
                continue

            if isinstance(geom, Polygon):
                if infill_style in ["S okraji", "Okraje"]:
                    path_x.append(list(geom.exterior.xy[0]))
                    path_y.append(list(geom.exterior.xy[1]))
                    for interior in geom.interiors:
                        path_x.append(list(interior.xy[0]))
                        path_y.append(list(interior.xy[1]))
                        
                if infill_style in ["S okraji", "Bez okrajů", "Had"] and infill_spacing > 0:
                    centroid = geom.centroid
                    rot_g = make_valid(rotate(geom, -infill_angle, origin=centroid)) if infill_angle != 0 else geom
                    if rot_g.is_empty: continue
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
                                        path_x.append(curr_had_x)
                                        path_y.append(curr_had_y)
                                        curr_had_x, curr_had_y = lx, ly
                                rev = not rev
                            if curr_had_x:
                                path_x.append(curr_had_x)
                                path_y.append(curr_had_y)
                        else:
                            for l in lines:
                                fl = rotate(l, infill_angle, origin=centroid) if infill_angle != 0 else l
                                path_x.append(list(fl.xy[0]))
                                path_y.append(list(fl.xy[1]))
            elif isinstance(geom, LineString):
                path_x.append(list(geom.xy[0]))
                path_y.append(list(geom.xy[1]))
        return path_x, path_y
