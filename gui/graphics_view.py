from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPathItem, QGraphicsRectItem, QGraphicsItemGroup, QGraphicsItem, QGraphicsEllipseItem, QMenu
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath, QPainter, QTransform, QFont, QAction
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtSvg import QSvgRenderer

class DraggableGCode(QGraphicsItemGroup):
    def __init__(self, allowed_rect, index):
        super().__init__()
        self.allowed_rect = allowed_rect
        self.index = index
        self.siblings = []
        
        # Načtení ikon
        import os
        svg_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'svg')
        self.renderer_scale = QSvgRenderer(os.path.join(svg_dir, 'scale-arrow.svg'))
        self.renderer_rotate = QSvgRenderer(os.path.join(svg_dir, 'corner-arrow.svg'))
        
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges |
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        
        self.is_resizing = False
        self.is_rotating = False
        self.interaction_mode = 'scale' # 'scale' nebo 'rotate' (Inkscape styl)
        self.resize_start_pos = None
        self.resize_start_scale = 1.0
        self.rotate_start_angle = 0.0
        self.rotate_mouse_start_angle = 0.0
        self._is_syncing = False

    def _get_total_scale(self):
        # Kombinované měřítko: item scale * view zoom
        view_scale = 1.0
        if self.scene() and self.scene().views():
            view_scale = self.scene().views()[0].transform().m11()
        return self.scale() * view_scale

    def boundingRect(self):
        rect = super().boundingRect()
        # Dynamický margin podle zoomu, aby úchyty nebyly ořezávány (zvětšeno pro větší ikony)
        ts = self._get_total_scale()
        margin = 20.0 / ts if ts > 0 else 20.0
        return rect.adjusted(-margin, -margin, margin, margin)

    def _get_handles(self):
        # rect jsou vnitřní hranice drah
        rect = self.childrenBoundingRect()
        
        # Celkové měřítko pro konstantní vizuální velikost (10mm na obrazovce)
        ts = self._get_total_scale()
        
        h_size = 10.0 / ts if ts > 0 else 10.0
        offset = 1.5 / ts if ts > 0 else 1.5
        
        return {
            'tl': QRectF(rect.left() - h_size - offset, rect.top() - h_size - offset, h_size, h_size),
            'tr': QRectF(rect.right() + offset, rect.top() - h_size - offset, h_size, h_size),
            'bl': QRectF(rect.left() - h_size - offset, rect.bottom() + offset, h_size, h_size),
            'br': QRectF(rect.right() + offset, rect.bottom() + offset, h_size, h_size)
        }

    def paint(self, painter, option, widget=None):
        from PyQt6.QtWidgets import QStyle
        option.state &= ~QStyle.StateFlag.State_HasFocus
        option.state &= ~QStyle.StateFlag.State_Selected
        super().paint(painter, option, widget)
        
        if self.isSelected():
            handles = self._get_handles()
            order = ['tl', 'tr', 'br', 'bl']
            
            for i, key in enumerate(order):
                h_rect = handles[key]
                painter.save()
                
                painter.translate(h_rect.center())
                painter.rotate(i * 90)
                painter.translate(-h_rect.width()/2, -h_rect.height()/2)
                
                target_rect = QRectF(0, 0, h_rect.width(), h_rect.height())
                
                if self.interaction_mode == 'scale':
                    self.renderer_scale.render(painter, target_rect)
                else:
                    self.renderer_rotate.render(painter, target_rect)
                
                painter.restore()

    def hoverMoveEvent(self, event):
        handles = self._get_handles()
        handle_key = None
        for key, h_rect in handles.items():
            if h_rect.contains(event.pos()):
                handle_key = key
                break
        
        if handle_key:
            if self.interaction_mode == 'scale':
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.interaction_mode = 'rotate' if self.interaction_mode == 'scale' else 'scale'
            self.update()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            view = self.scene().views()[0]
            if hasattr(view, 'save_state'):
                view.save_state()

        handles = self._get_handles()
        handle_key = None
        for key, h_rect in handles.items():
            if h_rect.contains(event.pos()):
                handle_key = key
                break
        
        if event.button() == Qt.MouseButton.LeftButton and handle_key:
            if self.interaction_mode == 'scale':
                self.is_resizing = True
                self.handle_key = handle_key
                import math
                # Určení protějšího (fixního) rohu
                rect = self.childrenBoundingRect()
                opp_map = {'tl': rect.bottomRight(), 'tr': rect.bottomLeft(), 
                           'bl': rect.topRight(), 'br': rect.topLeft()}
                self.resize_anchor_local = opp_map[handle_key]
                # Kotva ve scéně musí zůstat fixní
                self.resize_anchor_scene = self.mapToScene(self.resize_anchor_local)
                
                diff = event.scenePos() - self.resize_anchor_scene
                self.resize_start_dist_scene = math.hypot(diff.x(), diff.y())
                self.resize_start_scale = self.scale()
            else:
                self.is_rotating = True
                origin_scene = self.mapToScene(self.transformOriginPoint())
                diff = event.scenePos() - origin_scene
                import math
                self.rotate_mouse_start_angle = math.degrees(math.atan2(diff.y(), diff.x()))
                self.rotate_start_angle = self.rotation()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            # Povolíme kontextové menu, ale nesmíme volat super() pokud chceme zabránit 
            # standardnímu chování Qt (které by mohlo zrušit výběr)
            event.accept()
        else:
            self.is_resizing = False
            self.is_rotating = False
            super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        scene = self.scene()
        if not scene: return
        views = scene.views()
        if not views: return
        view = views[0]
        main_window = view.parent().parent()
        menu = QMenu()
        
        act_center = QAction("Vycentrovat na sklo", menu)
        act_reset_scale = QAction("Resetovat měřítko (1.0)", menu)
        act_reset_rot = QAction("Resetovat rotaci (0°)", menu)
        act_reset_all = QAction("Resetovat vše", menu)
        act_rot_90 = QAction("Otočit o +90°", menu)
        act_apply_all = QAction("Aplikovat transformace na všechna skla", menu)
        act_delete = QAction("Smazat objekt", menu)
        
        menu.addActions([act_center, act_reset_scale, act_reset_rot, act_reset_all, act_rot_90])
        menu.addSeparator()
        menu.addActions([act_apply_all, act_delete])
        
        action = menu.exec(event.screenPos())
        
        if action:
            if hasattr(view, 'save_state'): view.save_state()
            
            if action == act_center:
                # Precizní vycentrování středu objektu na střed skla
                cur_center_s = self.mapToScene(self.childrenBoundingRect().center())
                tgt_center_s = self.allowed_rect.center()
                self.setPos(self.pos() + (tgt_center_s - cur_center_s))
                
            elif action == act_reset_scale:
                # Výpočet měřítka pro návrat k absolutnímu 1.0
                curr_abs = main_window.user_scales.get(self.index, 1.0)
                if curr_abs != 0:
                    self.setScale(1.0 / curr_abs)
                
            elif action == act_reset_rot:
                self.setRotation(0.0)

            elif action == act_reset_all:
                curr_abs = main_window.user_scales.get(self.index, 1.0)
                if curr_abs != 0: self.setScale(1.0 / curr_abs)
                self.setRotation(0.0)
                # Vycentrování (střed na střed)
                cur_center_s = self.mapToScene(self.childrenBoundingRect().center())
                tgt_center_s = self.allowed_rect.center()
                self.setPos(self.pos() + (tgt_center_s - cur_center_s))
                
            elif action == act_rot_90:
                self.setRotation(self.rotation() + 90)
                
            elif action == act_apply_all:
                # 1. Zjistíme cílový stav (absolutní scale, rotaci a relativní střed)
                target_abs_scale = main_window.user_scales.get(self.index, 1.0) * self.scale()
                target_rot = self.rotation()
                # Relativní pozice středu vůči levému hornímu rohu skla
                cur_center_s = self.mapToScene(self.childrenBoundingRect().center())
                rel_center_offset = cur_center_s - self.allowed_rect.topLeft()
                
                for s in self.siblings:
                    if s != self:
                        s.prepareGeometryChange()
                        # Škálování tak, aby výsledné user_scale bylo target_abs_scale
                        s_logic_scale = main_window.user_scales.get(s.index, 1.0)
                        if s_logic_scale != 0:
                            s.setScale(target_abs_scale / s_logic_scale)
                        
                        s.setRotation(target_rot)
                        
                        # Pozicování: Střed s musí být na stejném relativním místě jeho skla
                        s_tgt_center_s = s.allowed_rect.topLeft() + rel_center_offset
                        s_cur_center_s = s.mapToScene(s.childrenBoundingRect().center())
                        s.setPos(s.pos() + (s_tgt_center_s - s_cur_center_s))
                        
            elif action == act_delete:
                if self in view.gcode_items:
                    view.gcode_items.remove(self)
                scene.removeItem(self)
                main_window.update_preview()
                return

            # Pro všechny operace z menu použijeme střed jako kotvu pro plynulý update
            self._trigger_full_update(handle_key='center')

    def _trigger_full_update(self, handle_key='br'):
        # Pomocná metoda pro odeslání změn do main_window
        scene = self.scene()
        if not scene: return
        views = scene.views()
        if not views: return
        view = views[0]
        
        updates = []
        for item in self.siblings:
            if item.scene() == scene:
                ir = item.childrenBoundingRect()
                # Dynamická volba kotvy (BR pro manuální resize, Center pro menu akce)
                if handle_key == 'center':
                    i_a_l = ir.center()
                else:
                    i_a_l = ir.bottomRight()
                
                i_a_s = item.mapToScene(i_a_l)
                updates.append({
                    'index': item.index, 'scale': item.scale(),
                    'anchor_s': i_a_s, 'handle_key': handle_key, 'is_resizing': True
                })
        
        parent = view.parent()
        while parent:
            if hasattr(parent, 'apply_visual_scale'):
                parent.apply_visual_scale(updates)
                break
            parent = parent.parent()

    def mouseMoveEvent(self, event):
        import math
        from PyQt6.QtWidgets import QApplication
        apply_to_all = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)

        if self.is_resizing:
            # Anchor (fixní bod) ve scéně
            # Musíme ho přepočítat, protože item.pos() se mohl změnit v minulé iteraci
            rect = self.childrenBoundingRect()
            opp_map = {'tl': rect.bottomRight(), 'tr': rect.bottomLeft(), 
                       'bl': rect.topRight(), 'br': rect.topLeft()}
            anchor_l = opp_map[self.handle_key]
            anchor_s = self.mapToScene(anchor_l)
            
            # Aktuální vzdálenost od kotvy
            diff = event.scenePos() - anchor_s
            curr_dist = math.hypot(diff.x(), diff.y())
            
            if self.resize_start_dist_scene > 0:
                # Navrhované nové měřítko
                new_scale = (curr_dist / self.resize_start_dist_scene) * self.resize_start_scale
                
                # Limitace měřítka, aby žádný roh nevyjel ze skla
                def get_max_scale_constrained(item, h_key):
                    i_rect = item.childrenBoundingRect()
                    i_corners = [i_rect.topLeft(), i_rect.topRight(), i_rect.bottomLeft(), i_rect.bottomRight()]
                    
                    # Kotva pro tento konkrétní item (ve scéně)
                    i_opp_map = {'tl': i_rect.bottomRight(), 'tr': i_rect.bottomLeft(), 
                                 'bl': i_rect.topRight(), 'br': i_rect.topLeft()}
                    i_anchor_l = i_opp_map[h_key]
                    i_anchor_s = item.mapToScene(i_anchor_l)
                    
                    # Vektory od kotvy k rohům při scale=1.0 (včetně rotace)
                    # P_scene = anchor_s + (P_local - anchor_local) * rot * scale
                    t = QTransform().rotate(item.rotation())
                    
                    m_scale = 100.0
                    ar = item.allowed_rect
                    
                    for p_l in i_corners:
                        # Směrový vektor v souřadnicích scény pro scale=1.0
                        vec = t.map(p_l - i_anchor_l)
                        
                        # Musí platit pro X i Y:
                        # ar.left <= i_anchor_s.x + vec.x * S <= ar.right
                        # ar.top <= i_anchor_s.y + vec.y * S <= ar.bottom
                        for val_s, v_comp, low, high in [
                            (i_anchor_s.x(), vec.x(), ar.left(), ar.right()),
                            (i_anchor_s.y(), vec.y(), ar.top(), ar.bottom())
                        ]:
                            if abs(v_comp) > 1e-6:
                                s_low = (low - val_s) / v_comp
                                s_high = (high - val_s) / v_comp
                                s_limit = max(s_low, s_high) # S > 0
                                if s_limit > 0: m_scale = min(m_scale, s_limit)
                    return m_scale

                targets = self.siblings if apply_to_all else [self]
                abs_max_s = min([get_max_scale_constrained(it, self.handle_key) for it in targets])
                
                final_scale = max(0.01, min(new_scale, abs_max_s))
                
                # Aplikace s udržením kotvy
                for item in targets:
                    item.prepareGeometryChange()
                    # Znovu zjistíme kotvu před změnou měřítka
                    ir = item.childrenBoundingRect()
                    i_opp = {'tl': ir.bottomRight(), 'tr': ir.bottomLeft(), 'bl': ir.topRight(), 'br': ir.topLeft()}
                    i_a_l = i_opp[self.handle_key]
                    i_a_s = item.mapToScene(i_a_l)
                    
                    item.setScale(final_scale)
                    
                    # Posun, aby kotva zůstala na stejném místě ve scéně
                    i_a_s_new = item.mapToScene(i_a_l)
                    item.setPos(item.pos() + (i_a_s - i_a_s_new))
        
        elif self.is_rotating:
            origin_scene = self.mapToScene(self.transformOriginPoint())
            diff = event.scenePos() - origin_scene
            current_mouse_angle = math.degrees(math.atan2(diff.y(), diff.x()))
            delta = current_mouse_angle - self.rotate_mouse_start_angle
            new_angle = self.rotate_start_angle + delta
            
            if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
                new_angle = round(new_angle / 15.0) * 15.0
            
            # Kontrola, zda objekt nevyjede ze skla
            def is_valid_rotation(angle, items):
                for item in items:
                    # Simulujeme rotaci
                    old_rot = item.rotation()
                    item.setRotation(angle)
                    # Získáme rohy bounding boxu v souřadnicích scény
                    rect = item.childrenBoundingRect()
                    corners = [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]
                    all_inside = True
                    for c in corners:
                        sc = item.mapToScene(c)
                        if not item.allowed_rect.contains(sc):
                            all_inside = False
                            break
                    item.setRotation(old_rot) # Vrátíme zpět
                    if not all_inside: return False
                return True

            targets = self.siblings if apply_to_all else [self]
            if is_valid_rotation(new_angle, targets):
                for item in targets:
                    item.prepareGeometryChange()
                    item.setRotation(new_angle)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_resizing or self.is_rotating:
            # Uložíme si stav před resetem pro potřeby aktualizace
            is_res = self.is_resizing
            h_key = getattr(self, 'handle_key', 'br')
            
            self.is_resizing = False
            self.is_rotating = False
            
            # Pro každého sourozence zjistíme jeho aktuální kotvu ve scéně
            updates = []
            for item in self.siblings:
                ir = item.childrenBoundingRect()
                i_opp = {'tl': ir.bottomRight(), 'tr': ir.bottomLeft(), 'bl': ir.topRight(), 'br': ir.topLeft()}
                i_a_l = i_opp[h_key]
                i_a_s = item.mapToScene(i_a_l)
                
                updates.append({
                    'index': item.index,
                    'scale': item.scale(),
                    'anchor_s': i_a_s,
                    'handle_key': h_key,
                    'is_resizing': is_res
                })
            
            if updates:
                view = self.scene().views()[0]
                parent = view.parent()
                while parent:
                    if hasattr(parent, 'apply_visual_scale'):
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(0, lambda p=parent, u=updates: p.apply_visual_scale(u))
                        break
                    parent = parent.parent()
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and not self.is_resizing:
            from PyQt6.QtWidgets import QApplication
            new_pos = value
            
            # PŘICHYTÁVÁNÍ K MŘÍŽCE (Ctrl) - začíná vlevo dole
            if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
                # Vzdálenost od levého dolního rohu:
                rel_x = new_pos.x() - self.allowed_rect.left()
                rel_y = self.allowed_rect.bottom() - new_pos.y()
                
                new_pos.setX(self.allowed_rect.left() + round(rel_x))
                new_pos.setY(self.allowed_rect.bottom() - round(rel_y))

            self.prepareGeometryChange()
            delta = new_pos - self.pos()
            
            current_scene_rect = self.mapToScene(self.childrenBoundingRect()).boundingRect()
            proposed_rect = current_scene_rect.translated(delta)

            if proposed_rect.left() < self.allowed_rect.left():
                new_pos.setX(new_pos.x() + (self.allowed_rect.left() - proposed_rect.left()))
            elif proposed_rect.right() > self.allowed_rect.right():
                new_pos.setX(new_pos.x() - (proposed_rect.right() - self.allowed_rect.right()))

            if proposed_rect.top() < self.allowed_rect.top():
                new_pos.setY(new_pos.y() + (self.allowed_rect.top() - proposed_rect.top()))
            elif proposed_rect.bottom() > self.allowed_rect.bottom():
                new_pos.setY(new_pos.y() - (proposed_rect.bottom() - self.allowed_rect.bottom()))
            
            actual_delta = new_pos - self.pos()

            if not self._is_syncing:
                from PyQt6.QtWidgets import QApplication
                if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
                    for sibling in self.siblings:
                        if sibling != self:
                            sibling._is_syncing = True
                            sibling.setPos(sibling.pos() + actual_delta)
                            sibling._is_syncing = False
                            
            return new_pos
        return super().itemChange(change, value)

    def _apply_scale(self, new_scale, apply_to_all):
        self.prepareGeometryChange()
        self.setScale(new_scale)
        if apply_to_all:
            for sibling in self.siblings:
                if sibling != self:
                    sibling.prepareGeometryChange()
                    sibling.setScale(new_scale)


class InteractiveGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.slides_info = [] 
        self.bed_w = 250.0 
        self.bed_h = 210.0      
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))
        
        # Zajištění překreslení mřížky při změně výběru
        self.scene.selectionChanged.connect(self.viewport().update)
        
        self.undo_stack = []
        self.redo_stack = []

    def save_state(self):
        state = []
        for item in getattr(self, 'gcode_items', []):
            if item.scene() == self.scene:
                state.append({
                    'index': item.index,
                    'pos': item.pos(),
                    'scale': item.scale(),
                    'rotation': item.rotation(),
                    'allowed_rect': item.allowed_rect
                })
        self.undo_stack.append(state)
        self.redo_stack.clear()

    def restore_state(self, state):
        for item in self.gcode_items:
            if item.scene() == self.scene:
                self.scene.removeItem(item)
        self.gcode_items.clear()

        view_parent = self.parent()
        # Získání logiky a parametrů z hlavního okna
        main_window = view_parent.parent() if view_parent else None
        logic = main_window.logic if main_window and hasattr(main_window, 'logic') else None
        params = main_window.left_panel.get_all_params() if main_window and hasattr(main_window, 'left_panel') else {}
        if not logic: return

        nozzle_diam = params.get('nozzle_diam', 0.4)
        pen_print = QPen(QColor(255, 30, 30), nozzle_diam)
        pen_print.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen_travel = QPen(QColor(150, 0, 0), nozzle_diam/2, Qt.PenStyle.DashLine)

        def view_y(gcode_y, obj_h=0): 
            return self.bed_h - gcode_y - obj_h

        for data in state:
            i = data['index']
            movable_group = DraggableGCode(data['allowed_rect'], index=i)
            
            if hasattr(logic, 'paths_by_index') and i in logic.paths_by_index:
                px_list, py_list = logic.paths_by_index[i]['x'], logic.paths_by_index[i]['y']
            else:
                px_list, py_list = logic.path_x, logic.path_y
                
            path_print = QPainterPath()
            path_travel = QPainterPath()
            sh = data['allowed_rect'].height()

            last_pt = None
            for px, py in zip(px_list, py_list):
                # Přesun k novému segmentu (relativně k vnitřku sklíčka)
                if last_pt:
                    path_travel.moveTo(last_pt[0], sh - last_pt[1])
                    path_travel.lineTo(px[0], sh - py[0])
                
                if len(px) == 2 and px[0] == px[1] and py[0] == py[1]:
                    # Vizualizace kapky
                    r = max(0.4, nozzle_diam / 2.0)
                    path_print.addEllipse(QPointF(px[0], sh - py[0]), r, r)
                else:
                    path_print.moveTo(px[0], sh - py[0])
                    for x, y in zip(px[1:], py[1:]):
                        path_print.lineTo(x, sh - y)
                last_pt = (px[-1], py[-1])
            
            item_travel = QGraphicsPathItem(path_travel)
            item_travel.setPen(pen_travel)
            movable_group.addToGroup(item_travel)

            item_print = QGraphicsPathItem(path_print)
            item_print.setPen(pen_print)
            
            # Pokud jsou v cestě tečky, vyplníme je barvou pera
            # Efektivní kontrola: Stačí se podívat na první prvek, u teček jsou všechny stejné,
            # nebo použít informaci o stylu z dat, pokud by tam byla.
            has_dots = False
            if px_list and len(px_list[0]) == 2 and px_list[0][0] == px_list[0][1]:
                if py_list and py_list[0][0] == py_list[0][1]:
                    has_dots = True
            
            if has_dots:
                item_print.setBrush(QBrush(pen_print.color()))
            movable_group.addToGroup(item_print)
            
            movable_group.setZValue(1)
            movable_group.setTransformOriginPoint(item_print.boundingRect().center())
            
            movable_group.setScale(data['scale'])
            movable_group.setRotation(data.get('rotation', 0.0))
            movable_group.setPos(data['pos'])
            
            self.scene.addItem(movable_group)
            self.gcode_items.append(movable_group)
            
        for item in self.gcode_items:
            item.siblings = self.gcode_items

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_A:
            for item in getattr(self, 'gcode_items', []):
                item.setSelected(True)
            event.accept()

        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected = self.scene.selectedItems()
            if selected:
                self.save_state()
                for item in selected:
                    if isinstance(item, DraggableGCode):
                        self.scene.removeItem(item)
                        if item in self.gcode_items:
                            self.gcode_items.remove(item)
                event.accept()

        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Z:
            if self.undo_stack:
                current_state = [{'index': it.index, 'pos': it.pos(), 'scale': it.scale(), 'allowed_rect': it.allowed_rect} 
                                 for it in self.gcode_items if it.scene() == self.scene]
                self.redo_stack.append(current_state)
                
                last_state = self.undo_stack.pop()
                self.restore_state(last_state)
            event.accept()

        elif modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_Z:
            if self.redo_stack:
                current_state = [{'index': it.index, 'pos': it.pos(), 'scale': it.scale(), 'allowed_rect': it.allowed_rect} 
                                 for it in self.gcode_items if it.scene() == self.scene]
                self.undo_stack.append(current_state)
                
                next_state = self.redo_stack.pop()
                self.restore_state(next_state)
            event.accept()

        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if not item or item.zValue() < 0:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            else:
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        current_scale = self.transform().m11()

        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            view_rect = self.viewport().rect()
            # Povolíme odzoomování tak, aby byl vidět i prostor KOLEM podložky (margin 50mm na každou stranu)
            min_scale_x = view_rect.width() / (self.bed_w + 100)
            min_scale_y = view_rect.height() / (self.bed_h + 100)
            min_scale = min(min_scale_x, min_scale_y)
            
            min_scale = max(0.01, min_scale)

            if current_scale * zoom_out_factor > min_scale:
                self.scale(zoom_out_factor, zoom_out_factor)
            else:
                self.setTransform(QTransform.fromScale(min_scale, min_scale))

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        
        if hasattr(self, 'bed_w'):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(50, 50, 50)))
            painter.drawRect(QRectF(0, 0, self.bed_w, self.bed_h))

        scale = self.transform().m11()
        grid_size = 1 if scale > 5 else (5 if scale > 2 else 10)

        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        alpha = 80 if grid_size >= 5 else 40
        pen = QPen(QColor(100, 100, 100, alpha))
        pen.setCosmetic(True)
        painter.setPen(pen)

        from PyQt6.QtCore import QLineF
        lines = []
        x = left
        while x <= rect.right():
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
            x += grid_size
            
        y = top
        while y <= rect.bottom():
            lines.append(QLineF(rect.left(), y, rect.right(), y))
            y += grid_size
            
        painter.drawLines(lines)

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        
        scale = self.transform().m11()
        if scale < 0.05 or not hasattr(self, 'bed_w'): return
        
        view_rect = self.viewport().rect()
        vp_w = view_rect.width()
        vp_h = view_rect.height()

        painter.setTransform(QTransform())
        
        major_step = 10 if scale < 5 else 5
        minor_step = 5 if scale < 5 else 1

        def draw_x_axis(scene_y, scene_x_start, scene_x_end, val_start, val_end, p_pen):
            painter.setPen(p_pen)
            view_y_ideal = self.mapFromScene(QPointF(0, scene_y)).y()
            is_visible = view_y_ideal <= vp_h
            draw_y = min(view_y_ideal, vp_h - 1)
            
            tick_dir = 1 if is_visible else -1 

            view_x_start = self.mapFromScene(QPointF(scene_x_start, 0)).x()
            view_x_end = self.mapFromScene(QPointF(scene_x_end, 0)).x()

            line_start = max(0, int(view_x_start))
            line_end = min(vp_w, int(view_x_end))
            if line_start < line_end:
                painter.drawLine(line_start, int(draw_y), line_end, int(draw_y))

            curr_val = val_start
            while curr_val <= val_end:
                scene_x = scene_x_start + (curr_val - val_start)
                vx = self.mapFromScene(QPointF(scene_x, 0)).x()
                if 0 <= vx <= vp_w:
                    if curr_val % major_step == 0:
                        painter.drawLine(int(vx), int(draw_y), int(vx), int(draw_y + 8 * tick_dir))
                        ty = draw_y + 20 if tick_dir == 1 else draw_y - 12
                        painter.drawText(int(vx) - 8, int(ty), f"{curr_val:g}")
                    elif curr_val % minor_step == 0:
                        painter.drawLine(int(vx), int(draw_y), int(vx), int(draw_y + 4 * tick_dir))
                curr_val += minor_step

        def draw_y_axis(scene_x, scene_y_bottom, scene_y_top, val_start, val_end, p_pen):
            painter.setPen(p_pen)
            view_x_ideal = self.mapFromScene(QPointF(scene_x, 0)).x()
            is_visible = view_x_ideal >= 0
            draw_x = max(view_x_ideal, 0)
            
            tick_dir = -1 if is_visible else 1 

            view_y_bottom = self.mapFromScene(QPointF(0, scene_y_bottom)).y()
            view_y_top = self.mapFromScene(QPointF(0, scene_y_top)).y()

            line_bottom = min(vp_h, int(view_y_bottom))
            line_top = max(0, int(view_y_top))
            if line_top < line_bottom:
                painter.drawLine(int(draw_x), line_top, int(draw_x), line_bottom)

            curr_val = val_start
            while curr_val <= val_end:
                scene_y = scene_y_bottom - (curr_val - val_start)
                vy = self.mapFromScene(QPointF(0, scene_y)).y()
                if 0 <= vy <= vp_h:
                    if curr_val % major_step == 0:
                        painter.drawLine(int(draw_x), int(vy), int(draw_x + 8 * tick_dir), int(vy))
                        tx = draw_x - 28 if tick_dir == -1 else draw_x + 12
                        painter.drawText(int(tx), int(vy) + 4, f"{curr_val:g}")
                    elif curr_val % minor_step == 0:
                        painter.drawLine(int(draw_x), int(vy), int(draw_x + 4 * tick_dir), int(vy))
                curr_val += minor_step

        from gui.settings import load_settings
        settings = load_settings()
        
        if settings.get("show_bed_axes", True):
            pen_main = QPen(QColor(150, 150, 150, 200), 1)
            draw_x_axis(self.bed_h, 0, self.bed_w, 0, self.bed_w, pen_main)
            draw_y_axis(0, self.bed_h, 0, 0, self.bed_h, pen_main)

        pen_slide = QPen(QColor(150, 220, 150, 220), 1)
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        if not settings.get("show_slide_grid", True):
            return

        scene_rect_vis = self.mapToScene(view_rect).boundingRect()
        
        # Určíme, která sklíčka mají vybraný objekt (pro zobrazení mřížky)
        selected_slides = set()
        for item in self.scene.selectedItems():
            if hasattr(item, 'allowed_rect'):
                selected_slides.add((item.allowed_rect.x(), item.allowed_rect.y()))

        for sx, sy, sw, sh in self.slides_info:
            # Mřížku zobrazíme jen pokud je na sklíčku něco vybráno
            if not selected_slides or (sx, sy) not in selected_slides:
                continue
                
            if not (sx > scene_rect_vis.right() or sx + sw < scene_rect_vis.left() or 
                    sy > scene_rect_vis.bottom() or sy + sh < scene_rect_vis.top()):
                
                draw_x_axis(sy + sh, sx, sx + sw, 0, sw, pen_slide)
                draw_y_axis(sx, sy + sh, sy, 0, sh, pen_slide)

    def redraw_scene(self, logic, params, slide_dims, positions, bed_max_x, bed_max_y, loaded_transforms=None, first_load=False):
        saved_transforms = {}
        # Detekce změny rozměrů podložky pro případný reset kamery
        bed_changed = abs(self.bed_w - bed_max_x) > 1.0 or abs(self.bed_h - bed_max_y) > 1.0
        
        if loaded_transforms:
            for i, t in enumerate(loaded_transforms):
                if not t.get('deleted', False):
                    saved_transforms[i] = {
                        'pos': QPointF(t.get('gui_dx', 0), t.get('gui_dy', 0)),
                        'scale': t.get('scale', 1.0)
                    }
        elif hasattr(self, 'gcode_items'):
            for item in self.gcode_items:
                try:
                    saved_transforms[item.index] = {
                        'pos': item.pos(), 
                        'scale': item.scale(),
                        'rotation': item.rotation()
                    }
                except RuntimeError: pass
                                   
        self.scene.clear()
        # Nastavení plochy scény s okrajem 50mm kolem tiskové plochy
        margin = 50.0
        self.scene.setSceneRect(-margin, -margin, bed_max_x + 2*margin, bed_max_y + 2*margin)
        self.slides_info = []
        self.gcode_items = []
        self.bed_w = bed_max_x
        self.bed_h = bed_max_y

        pen_slide = QPen(QColor(0, 128, 0), 1); pen_slide.setCosmetic(True)
        brush_slide = QBrush(QColor(50, 70, 50, 150))
        brush_prime = QBrush(QColor(70, 70, 70, 150)) # Tmavší pro odpliv
        pen_prime_trace = QPen(QColor(200, 200, 200), 0.4)

        if not positions: return

        def view_y(gcode_y, obj_h=0): return bed_max_y - gcode_y - obj_h

        prime_active = params.get('prime_active', True)

        for i, (gx, gy, sw, sh, is_prime) in enumerate(positions):
            sy = view_y(gy, sh)
            self.slides_info.append((gx, sy, sw, sh))
            
            s_brush = brush_prime if is_prime else brush_slide
            slide = self.scene.addRect(gx, sy, sw, sh, pen_slide, s_brush)
            slide.setZValue(-1)
            
            if is_prime and prime_active:
                # Trasa odplivu: PLNÝ čtverec 10x10 mm uprostřed
                path_prime = QPainterPath()
                px, py = gx + sw/2 - 5, gy + sh/2 - 5
                path_prime.addRect(px, view_y(py, 10), 10, 10)
                item_prime_trace = QGraphicsPathItem(path_prime)
                item_prime_trace.setPen(pen_prime_trace)
                item_prime_trace.setBrush(QBrush(QColor(150, 150, 150, 150)))
                self.scene.addItem(item_prime_trace)

        if logic.filepath:
            nozzle_diam = params.get('nozzle_diam', 0.4)    
            pen_print = QPen(QColor(255, 30, 30), nozzle_diam); pen_print.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen_travel = QPen(QColor(150, 0, 0), nozzle_diam/2, Qt.PenStyle.DashLine)
            
            # Tiskeme pouze na měřicí skla
            measurement_positions = [(p, idx) for idx, p in enumerate(positions) if not p[4]]
            
            for i, (pos_data, original_idx) in enumerate(measurement_positions):
                gx, gy, sw, sh, _ = pos_data
                sy = view_y(gy, sh)
                local_allowed_rect = QRectF(gx, sy, sw, sh)
                movable_group = DraggableGCode(local_allowed_rect, index=i)
                
                if hasattr(logic, 'paths_by_index') and i in logic.paths_by_index:
                    px_list = logic.paths_by_index[i]['x']
                    py_list = logic.paths_by_index[i]['y']
                else:
                    px_list = logic.path_x; py_list = logic.path_y
                    
                path_print = QPainterPath()
                path_travel = QPainterPath()
                last_pt = None
                
                for px, py in zip(px_list, py_list):
                    # Přesun k novému segmentu (relativně k vnitřku sklíčka)
                    if last_pt:
                        path_travel.moveTo(last_pt[0], sh - last_pt[1])
                        path_travel.lineTo(px[0], sh - py[0])

                    if len(px) == 2 and px[0] == px[1] and py[0] == py[1]:
                        # Vizualizace kapky (jen pokud se nemění X ani Y)
                        r = max(0.4, nozzle_diam / 2.0)
                        path_print.addEllipse(QPointF(px[0], sh - py[0]), r, r)
                    else:
                        path_print.moveTo(px[0], sh - py[0])
                        for x, y in zip(px[1:], py[1:]):
                            path_print.lineTo(x, sh - y)
                    last_pt = (px[-1], py[-1])

                item_travel = QGraphicsPathItem(path_travel)
                item_travel.setPen(pen_travel)
                movable_group.addToGroup(item_travel)

                item_print = QGraphicsPathItem(path_print)
                item_print.setPen(pen_print)
                
                if any(len(p) == 2 and p[0] == p[1] and py_list[idx][0] == py_list[idx][1] for idx, p in enumerate(px_list)):
                    item_print.setBrush(QBrush(pen_print.color()))
                    
                movable_group.addToGroup(item_print)
                movable_group.setZValue(1)
                
                # Klíčová změna: TransformOriginPoint MUSÍ být nastaven jako první
                movable_group.setTransformOriginPoint(item_print.boundingRect().center())

                # Získání informací o kotvě z hlavního okna (pokud existují)
                main_window = self.parent().parent()
                anchors = getattr(main_window, 'last_anchors', {})
                anchor_data = anchors.get(i)

                if i in saved_transforms:
                    # Pokud právě proběhl redraw po manipulaci, visual scale by měl být 1.0, 
                    # protože se už zapekl do user_scale v logic.
                    # Ale pozor - redraw může být vyvolán i změnou jiného parametru.
                    v_scale = saved_transforms[i]['scale']
                    v_pos = saved_transforms[i]['pos']
                    v_rot = saved_transforms[i].get('rotation', 0.0)
                    
                    if anchor_data:
                        # Pokud máme kotvu, zrušíme visual scale a přichytíme k ní
                        anchor_s, h_key = anchor_data
                        movable_group.setScale(1.0)
                        movable_group.setRotation(v_rot)
                        
                        # Zjistíme scénickou pozici kotvy na NOVÝCH drahách (při scale 1.0)
                        # Jelikož jsme už nastavili rotaci a scale, mapToScene funguje správně.
                        ir = item_print.boundingRect()
                        opp_map = {
                            'tl': ir.bottomRight(), 'tr': ir.bottomLeft(), 
                            'bl': ir.topRight(), 'br': ir.topLeft(),
                            'center': ir.center()
                        }
                        a_l = opp_map[h_key]
                        
                        # Aktuální pozice kotvy ve scéně při stávajícím setPos(0,0)
                        current_anchor_s = movable_group.mapToScene(a_l)
                        
                        # Nastavíme pozici tak, aby lokální kotva byla na cílové scénické kotvě
                        movable_group.setPos(movable_group.pos() + (anchor_s - current_anchor_s))
                        # Smažeme kotvu, aby se nepoužila při dalším redraw (např. změna teploty)
                        del anchors[i]
                    else:
                        movable_group.setScale(v_scale)
                        movable_group.setRotation(v_rot)
                        movable_group.setPos(v_pos)
                elif loaded_transforms and i < len(loaded_transforms):
                    # Pro načtená metadata použijeme uloženou absolutní pozici
                    lt = loaded_transforms[i]
                    movable_group.setScale(lt.get('scale', 1.0))
                    movable_group.setRotation(lt.get('rotation', 0.0))
                    movable_group.setPos(lt.get('gui_dx', gx), lt.get('gui_dy', sy))
                else:
                    # Vycentrování na sklíčku pro první načtení
                    rect = item_print.boundingRect()
                    ox = (sw - rect.width()) / 2.0 - rect.left()
                    oy = (sh - rect.height()) / 2.0 - rect.top()
                    movable_group.setPos(gx + ox, sy + oy)
                
                self.scene.addItem(movable_group)
                self.gcode_items.append(movable_group)

            for item in self.gcode_items: item.siblings = self.gcode_items

        if first_load or bed_changed:
            from PyQt6.QtCore import QTimer
            # Použijeme krátký delay, aby měl viewport už finální rozměry
            QTimer.singleShot(50, lambda: self.fitInView(QRectF(0, 0, bed_max_x, bed_max_y), Qt.AspectRatioMode.KeepAspectRatio))
        
    def update_nozzle_position(self, x, y, z, is_extruding):
        if not hasattr(self, 'bed_h'): return
        scene_x = x; scene_y = self.bed_h - y
        try:
            if not hasattr(self, 'nozzle_item') or self.nozzle_item.scene() != self.scene: raise RuntimeError
        except RuntimeError:
            self.nozzle_item = QGraphicsEllipseItem(-3, -3, 6, 6)
            self.nozzle_item.setZValue(10); self.scene.addItem(self.nozzle_item)
        self.nozzle_item.setPos(scene_x, scene_y)
        if is_extruding:
            self.nozzle_item.setBrush(QBrush(QColor(255, 0, 0))); self.nozzle_item.setPen(QPen(QColor(150, 0, 0)))
        else:
            self.nozzle_item.setBrush(QBrush(QColor(0, 150, 255))); self.nozzle_item.setPen(QPen(QColor(0, 100, 200)))

    def get_transforms(self):
        transforms = []
        if hasattr(self, 'gcode_items'):
            for item in self.gcode_items:
                if item.scene() == self.scene:
                    transforms.append({
                        'scale': item.scale(), 'rotation': item.rotation(),
                        'gui_dx': item.pos().x(), 'gui_dy': item.pos().y(),
                        'cx': item.transformOriginPoint().x(), 'cy': item.transformOriginPoint().y()
                    })
                else: transforms.append({'deleted': True})
        return transforms
