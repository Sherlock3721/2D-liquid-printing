import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QGraphicsView, 
                             QGraphicsScene, QGraphicsItem, QGraphicsRectItem,
                             QGraphicsTextItem, QGraphicsItemGroup, QInputDialog,
                             QGraphicsEllipseItem, QGraphicsPathItem, QLabel)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QByteArray, QRect
from PyQt6.QtGui import QBrush, QColor, QPen, QPainter, QFont
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
import xml.etree.ElementTree as ET

# Registrace jmenných prostorů pro korektní XML výstup
ET.register_namespace('', "http://www.w3.org/2000/svg")
ET.register_namespace('inkscape', "http://www.inkscape.org/namespaces/inkscape")
ET.register_namespace('sodipodi', "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd")

class ClickableGroup(QGraphicsItemGroup):
    def __init__(self, element_id, label, parent=None):
        super().__init__(parent)
        self.element_id = element_id
        self.label = label
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptHoverEvents(True)
        self.is_selected = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()  # Zastaví propagaci do spodních vrstev
            self.scene().owner_view.handle_group_click(self)
        else:
            super().mousePressEvent(event)

    def set_highlight(self, highlight, renderer):
        self.is_selected = highlight
        if highlight:
            bounds = renderer.boundsOnElement(self.element_id)
            if bounds.isEmpty(): return
            self.overlay = QGraphicsRectItem(bounds)
            self.overlay.setBrush(QBrush(QColor(255, 0, 0, 60)))
            self.overlay.setPen(QPen(QColor(255, 0, 0), 0.3))
            self.overlay.setZValue(1)
            self.scene().addItem(self.overlay)
        else:
            if hasattr(self, 'overlay') and self.overlay in self.scene().items():
                self.scene().removeItem(self.overlay)

class InteractiveSvgSchema(QGraphicsView):
    valueUpdated = pyqtSignal(str, float)
    groupClicked = pyqtSignal(str, str) # Emits (key, label) when an element is clicked

    def __init__(self, svg_path, parent=None):
        super().__init__(parent)
        self.settings_parent = parent
        self._scene = QGraphicsScene(self)
        # Scéna musí odkazovat na tento View, aby ClickableGroup našel handle_group_click
        self._scene.owner_view = self
        self.setScene(self._scene)
        
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        # Zakázání posuvníků a odstranění rámečku
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setStyleSheet("background: transparent;")
        
        # Nastavení PEVNÉ VELIKOSTI widgetu pro zamezení přetečení
        self.setFixedSize(350, 450)
        
        self.svg_path = svg_path
        self.groups = {}
        self.ns = {'svg': 'http://www.w3.org/2000/svg', 
                   'inkscape': 'http://www.inkscape.org/namespaces/inkscape'}
        
        self.help_texts = {
            "Výška trysky": {"desc": "Plná délka trysky.\nModifikuje: Z-výšku, odpliv.", "key": "nozzle_height"},
            "Výska komory": {"desc": "Výška topného bloku.\nModifikuje: block_height.", "key": "block_height"},
            "Průměr trysky": {"desc": "Vnitřní průměr trysky.\nModifikuje: Šířku čáry.", "key": "nozzle_diam"},
            "Vnitřní průměr stříkačky": {"desc": "Průměr pístu.\nStandard: 9.5 mm.", "key": "filament_diameter"},
            "Výška držáku": {"desc": "Výška spodního držáku nad sklem.", "key": "holder_z"},
            "Tlouštka skla": {"desc": "Výška substrátu.\nStandard: 1.0 mm.", "key": "slide_z"},
            "Výška vrstvy": {"desc": "Mezera mezi tryskou a sklem.", "key": "z_offset"},
            "Schovaná část trysky": {"desc": "Délka závitu v bloku.", "key": "hidden_nozzle_part"}
        }
        
        self.load_svg()

    def load_svg(self):
        if not os.path.exists(self.svg_path): return

        self.renderer = QSvgRenderer(self.svg_path)
        self.svg_item = QGraphicsSvgItem()
        self.svg_item.setSharedRenderer(self.renderer)
        self._scene.addItem(self.svg_item)

        self.tree = ET.parse(self.svg_path)
        self.root = self.tree.getroot()
        
        if 'xmlns' not in self.root.attrib:
            self.root.set('xmlns', "http://www.w3.org/2000/svg")

        # Nastavení scény podle rendereru nebo viewBoxu
        viewbox = QRectF()
        if self.renderer.isValid():
            viewbox = self.renderer.viewBoxF()
        
        if viewbox.isEmpty():
            vb_attr = self.root.get('viewBox')
            if vb_attr:
                try:
                    vx, vy, vw, vh = map(float, vb_attr.split())
                    viewbox = QRectF(vx, vy, vw, vh)
                except: pass
        
        if viewbox.isEmpty():
            viewbox = QRectF(0, 0, 113, 171) # Fallback

        # Měřítko SVG prvku tak, aby odpovídalo jednotkám viewBoxu (scény)
        if self.renderer.isValid():
            db = self.renderer.defaultSize()
            if db.width() > 0:
                scale = viewbox.width() / db.width()
                self.svg_item.setScale(scale)

        self.setSceneRect(viewbox)
        self.refresh_svg()
        self.setup_interactive_elements()


    def setup_interactive_elements(self):
        for g in self.root.findall('.//svg:g', self.ns):
            label = g.get('{http://www.inkscape.org/namespaces/inkscape}label')
            # Povolíme interaktivitu pro všechny skupiny kromě Pozadí a hit_box
            if label and label not in ["Pozadí", "hit_box"]:
                el_id = g.get('id')
                if not el_id: continue
                bounds = self.renderer.boundsOnElement(el_id)
                if bounds.isEmpty(): continue
                
                group_item = ClickableGroup(el_id, label)
                rect_item = QGraphicsRectItem(bounds)
                rect_item.setBrush(QBrush(QColor(0, 0, 0, 0)))
                rect_item.setPen(QPen(Qt.PenStyle.NoPen))
                
                group_item.addToGroup(rect_item)
                self._scene.addItem(group_item)
                self.groups[label] = group_item

        hit_box = self.root.find('.//svg:g[@inkscape:label="hit_box"]', self.ns)
        if hit_box is not None:
            hit_box.set('style', 'display:none')
        self.refresh_svg()

    def refresh_svg(self):
        try:
            svg_data = ET.tostring(self.root, encoding='utf-8', xml_declaration=True)
            if not self.renderer.load(QByteArray(svg_data)):
                self.renderer.load(self.svg_path)
            self.svg_item.update()
            self._scene.update()
        except Exception as e:
            print(f"Chyba při refresh_svg: {e}")

    def update_svg_text(self, group_label, new_value, refresh=True):
        for g in self.root.findall('.//svg:g', self.ns):
            label = g.get('{http://www.inkscape.org/namespaces/inkscape}label')
            if label == group_label:
                # Najdeme textový prvek s labelem "Hodnota"
                for text in g.findall('.//svg:text', self.ns):
                    t_label = text.get('{http://www.inkscape.org/namespaces/inkscape}label')
                    if t_label == "Hodnota":
                        # Najdeme první tspan
                        tspan = text.find('.//svg:tspan', self.ns)
                        if tspan is not None:
                            # Vyčistíme všechny vnořené prvky v tomto tspanu
                            for child in list(tspan): tspan.remove(child)
                            tspan.text = f"{new_value:.2f} mm"
                            
                            # Vyčistíme i ostatní tspany v rámci stejného textu
                            for other_tspan in text.findall('.//svg:tspan', self.ns):
                                if other_tspan != tspan:
                                    other_tspan.text = ""
                                    for child in list(other_tspan): other_tspan.remove(child)
                        else:
                            # Pokud tspan není, vyčistíme text a nastavíme přímo
                            for child in list(text): text.remove(child)
                            text.text = f"{new_value:.2f} mm"
                break
        if refresh:
            self.refresh_svg()

    def update_tooltip(self, label, visible=True):
        hit_box = self.root.find('.//svg:g[@inkscape:label="hit_box"]', self.ns)
        if hit_box is None:
            return

        hit_box.set('style', 'display:inline' if visible else 'display:none')
        if visible:
            info = self.help_texts.get(label, {})
            for text in hit_box.findall('.//svg:text', self.ns):
                t_label = text.get('{http://www.inkscape.org/namespaces/inkscape}label')
                if t_label == "Nadpis":
                    # Vyčistíme text/tspan
                    tspan = text.find('.//svg:tspan', self.ns)
                    target = tspan if tspan is not None else text
                    for child in list(target): target.remove(child)
                    target.text = label
                elif t_label == "Popis":
                    desc = info.get("desc", "")
                    lines = desc.split('\n')
                    tspans = text.findall('.//svg:tspan', self.ns)
                    if tspans:
                        for i, t in enumerate(tspans):
                            for child in list(t): t.remove(child)
                            t.text = lines[i] if i < len(lines) else ""
                    else:
                        for child in list(text): text.remove(child)
                        text.text = desc
        self.refresh_svg()

    def handle_group_click(self, group):
        for g in self.groups.values(): g.set_highlight(False, self.renderer)
        group.set_highlight(True, self.renderer)
        self.update_tooltip(group.label, True)
        
        info = self.help_texts.get(group.label, {})
        key = info.get("key", group.label) # Dynamicky zjistíme klíč z názvu pokud není v help_texts
        
        self.groupClicked.emit(key, group.label)

    def set_initial_values(self, settings_dict, use_explicit=False):
        for label, group in self.groups.items():
            info = self.help_texts.get(label, {})
            key = info.get("key", label)
            val = None
            
            if use_explicit:
                if key == "nozzle_height": val = settings_dict.get("nozzle_height_val")
                elif key == "nozzle_diam": val = settings_dict.get("nozzle_diam_val")
                elif key == "hidden_nozzle_part": val = settings_dict.get("nozzle_hidden_val")
                elif key == "slide_z": val = settings_dict.get("slide_z_val")
                else: val = settings_dict.get(key)
            
            # Fallback na standardní mapování pokud val je stále None
            if val is None:
                if key == "nozzle_height": 
                    val = settings_dict.get("nozzle_defs", {}).get("Vlastní", [30, 0.4, 4])[0]
                elif key == "nozzle_diam":
                    val = settings_dict.get("nozzle_defs", {}).get("Vlastní", [30, 0.4, 4])[1]
                elif key == "hidden_nozzle_part":
                    nozzle_vlastni = settings_dict.get("nozzle_defs", {}).get("Vlastní")
                    if nozzle_vlastni and len(nozzle_vlastni) > 2:
                        val = nozzle_vlastni[2]
                    else:
                        val = settings_dict.get(key, 4.0)
                elif key == "slide_z":
                    val = settings_dict.get("sklo_dims", {}).get("Vlastní", [76, 26, 1.0])[2]
                elif key == "z_offset":
                    val = settings_dict.get("default_z_offset", 0.2)
                else:
                    val = settings_dict.get(key)

            if val is not None:
                try:
                    self.update_svg_text(label, float(val), refresh=False)
                except: pass
        self.refresh_svg()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_scale()

    def showEvent(self, event):
        super().showEvent(event)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self.update_scale)

    def update_scale(self):
        if not self.scene() or self.sceneRect().isEmpty():
            return
            
        # Resetujeme transformaci před výpočtem nového měřítka
        self.resetTransform()
        
        # Přidáme malý padding (10%) kolem scény pro zoom-out efekt
        rect = self.sceneRect()
        margin_w = rect.width() * 0.1
        margin_h = rect.height() * 0.1
        padded_rect = rect.adjusted(-margin_w, -margin_h, margin_w, margin_h)
        
        # Vynutíme fitting do aktuálního (pevného) viewportu s paddingem
        self.fitInView(padded_rect, Qt.AspectRatioMode.KeepAspectRatio)


class ExtrusionSettingsTab(QWidget):
    def __init__(self, svg_path, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = InteractiveSvgSchema(svg_path, self)
        layout.addWidget(self.view)
        self.view.valueUpdated.connect(self.propagate_value)

    def handle_group_click(self, group):
        self.view.handle_group_click(group)

    def propagate_value(self, key, value):
        p = self.parent(); 
        while p:
            if hasattr(p, "update_from_schema"): p.update_from_schema(key, value); break
            p = p.parent()
