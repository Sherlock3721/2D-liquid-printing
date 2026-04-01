from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPathItem, QGraphicsRectItem, QGraphicsItemGroup, QGraphicsItem, QGraphicsEllipseItem
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath, QPainter, QTransform, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF

class DraggableGCode(QGraphicsItemGroup):
    def __init__(self, allowed_rect, index):
        super().__init__()
        self.allowed_rect = allowed_rect
        self.index = index
        self.siblings = []
        
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges |
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        
        self.is_resizing = False
        self.resize_start_pos = None
        self.resize_start_scale = 1.0
        self._is_syncing = False

    def boundingRect(self):
        rect = super().boundingRect()
        margin = 5.0 / self.scale() if self.scale() > 0 else 5.0
        return rect.adjusted(-margin, -margin, margin, margin)

    def paint(self, painter, option, widget=None):
        from PyQt6.QtWidgets import QStyle
        option.state &= ~QStyle.StateFlag.State_HasFocus
        option.state &= ~QStyle.StateFlag.State_Selected
        super().paint(painter, option, widget)
        
        if self.isSelected():
            rect = super().boundingRect()
            
            pen = QPen(QColor(0, 150, 255), 1, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            
            h_size = 4.0 / self.scale() if self.scale() > 0 else 4.0
            painter.setBrush(QBrush(QColor(0, 150, 255)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(rect.right() - h_size, rect.bottom() - h_size, h_size, h_size))

    def hoverMoveEvent(self, event):
        rect = super().boundingRect()
        h_size = 4.0 / self.scale() if self.scale() > 0 else 4.0
        handle_rect = QRectF(rect.right() - h_size, rect.bottom() - h_size, h_size, h_size)
        
        if handle_rect.contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            view = self.scene().views()[0]
            if hasattr(view, 'save_state'):
                view.save_state()

        rect = super().boundingRect()
        h_size = 4.0 / self.scale() if self.scale() > 0 else 4.0
        handle_rect = QRectF(rect.right() - h_size, rect.bottom() - h_size, h_size, h_size)
        
        if event.button() == Qt.MouseButton.LeftButton and handle_rect.contains(event.pos()):
            self.is_resizing = True
            self.resize_start_pos = event.scenePos()
            self.resize_start_scale = self.scale()
            event.accept()
        else:
            self.is_resizing = False
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_resizing:
            origin_scene = self.mapToScene(self.transformOriginPoint())
            dy = event.scenePos().y() - origin_scene.y()
            
            rect = self.childrenBoundingRect()
            native_w = rect.width()
            native_h = rect.height()
            
            if native_h > 0 and native_w > 0:
                scale_factor = dy / native_h if dy > 0 else 0.1
                
                from PyQt6.QtWidgets import QApplication
                apply_to_all = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)

                absolute_max_scale = float('inf')

                if apply_to_all:
                    for sibling in self.siblings:
                        s_rect = sibling.childrenBoundingRect()
                        s_w = s_rect.width()
                        s_h = s_rect.height()
                        
                        if s_w > 0 and s_h > 0:
                            s_origin = sibling.mapToScene(sibling.transformOriginPoint())
                            
                            max_glass_x = sibling.allowed_rect.width() / s_w
                            max_glass_y = sibling.allowed_rect.height() / s_h
                            
                            dist_right = sibling.allowed_rect.right() - s_origin.x()
                            dist_bottom = sibling.allowed_rect.bottom() - s_origin.y()
                            
                            max_pos_x = dist_right / s_w
                            max_pos_y = dist_bottom / s_h
                            
                            s_limit = min(max_glass_x, max_glass_y, max_pos_x, max_pos_y)
                            absolute_max_scale = min(absolute_max_scale, s_limit)
                else:
                    max_glass_x = self.allowed_rect.width() / native_w
                    max_glass_y = self.allowed_rect.height() / native_h
                    
                    dist_right = self.allowed_rect.right() - origin_scene.x()
                    dist_bottom = self.allowed_rect.bottom() - origin_scene.y()
                    
                    max_pos_x = dist_right / native_w
                    max_pos_y = dist_bottom / native_h
                    
                    absolute_max_scale = min(max_glass_x, max_glass_y, max_pos_x, max_pos_y)

                if absolute_max_scale == float('inf'):
                    absolute_max_scale = 1.0

                scale_factor = max(0.1, min(scale_factor, absolute_max_scale))
                self._apply_scale(scale_factor, apply_to_all)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_resizing:
            self.is_resizing = False
            
            updates = [(item.index, item.scale()) for item in self.siblings if item.scale() != 1.0]
            
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
            
            # PŘICHYTÁVÁNÍ K MŘÍŽCE (Ctrl)
            if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
                new_pos.setX(round(new_pos.x()))
                new_pos.setY(round(new_pos.y()))

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
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))
        
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
        logic = view_parent.parent().logic if view_parent and hasattr(view_parent.parent(), 'logic') else None
        if not logic: return

        pen_print = QPen(QColor(255, 30, 30), 0.4)
        pen_print.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen_travel = QPen(QColor(150, 0, 0), 0.2, Qt.PenStyle.DashLine)

        for data in state:
            i = data['index']
            movable_group = DraggableGCode(data['allowed_rect'], index=i)
            
            if hasattr(logic, 'paths_by_index') and i in logic.paths_by_index:
                px_list, py_list = logic.paths_by_index[i]['x'], logic.paths_by_index[i]['y']
            else:
                px_list, py_list = logic.path_x, logic.path_y
                
            path_print = QPainterPath()
            path_travel = QPainterPath()
            gx, gy = data['allowed_rect'].x(), data['allowed_rect'].y()
            
            last_pt = None
            for px, py in zip(px_list, py_list):
                if last_pt:
                    path_travel.moveTo(last_pt[0] + gx, gy + last_pt[1])
                    path_travel.lineTo(px[0] + gx, gy + py[0])
                
                path_print.moveTo(px[0] + gx, gy + py[0])
                for x, y in zip(px[1:], py[1:]):
                    path_print.lineTo(x + gx, gy + y)
                last_pt = (px[-1], py[-1])
            
            item_travel = QGraphicsPathItem(path_travel)
            item_travel.setPen(pen_travel)
            movable_group.addToGroup(item_travel)

            item_print = QGraphicsPathItem(path_print)
            item_print.setPen(pen_print)
            movable_group.addToGroup(item_print)
            
            movable_group.setZValue(1)
            movable_group.setTransformOriginPoint(item_print.boundingRect().topLeft())
            
            movable_group.setScale(data['scale'])
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
            scene_rect = self.sceneRect()
            view_rect = self.viewport().rect()
            if scene_rect.width() > 0:
                min_scale_x = view_rect.width() / (scene_rect.width() + 50)
                min_scale_y = view_rect.height() / (scene_rect.height() + 50)
                min_scale = max(0.1, min(min_scale_x, min_scale_y))

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
        for sx, sy, sw, sh in self.slides_info:
            if not (sx > scene_rect_vis.right() or sx + sw < scene_rect_vis.left() or 
                    sy > scene_rect_vis.bottom() or sy + sh < scene_rect_vis.top()):
                
                draw_x_axis(sy + sh, sx, sx + sw, 0, sw, pen_slide)
                draw_y_axis(sx, sy + sh, sy, 0, sh, pen_slide)

    def redraw_scene(self, logic, params, slide_dims, positions, bed_max_x, bed_max_y, loaded_transforms=None):
        saved_transforms = {}
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
                    saved_transforms[item.index] = {'pos': item.pos(), 'scale': item.scale()}
                except RuntimeError: pass
                                   
        self.scene.clear()
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
                # Trasa odplivu: čtverec 10x10 mm uprostřed
                path_prime = QPainterPath()
                px, py = gx + sw/2 - 5, gy + sh/2 - 5
                path_prime.addRect(px, view_y(py, 10), 10, 10)
                item_prime_trace = QGraphicsPathItem(path_prime)
                item_prime_trace.setPen(pen_prime_trace)
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
                    # Přesun k novému segmentu
                    if last_pt:
                        path_travel.moveTo(last_pt[0] + gx, view_y(last_pt[1] + gy))
                        path_travel.lineTo(px[0] + gx, view_y(py[0] + gy))

                    if len(px) == 2 and px[0] == px[1]:
                        # Vizualizace kapky: malý kroužek o průměru trysky
                        r = max(0.5, nozzle_diam / 2.0)
                        path_print.addEllipse(QPointF(px[0] + gx, view_y(py[0] + gy)), r, r)
                    else:
                        path_print.moveTo(px[0] + gx, view_y(py[0] + gy))
                        for x, y in zip(px[1:], py[1:]):
                            path_print.lineTo(x + gx, view_y(y + gy))
                    last_pt = (px[-1], py[-1])

                item_travel = QGraphicsPathItem(path_travel)
                item_travel.setPen(pen_travel)
                movable_group.addToGroup(item_travel)

                item_print = QGraphicsPathItem(path_print)
                item_print.setPen(pen_print)
                
                # Pokud jsou v cestě tečky, vyplníme je barvou pera
                if any(len(p) == 2 and p[0] == p[1] for p in px_list):
                    item_print.setBrush(QBrush(pen_print.color()))
                    
                movable_group.addToGroup(item_print)
                movable_group.setZValue(1)
                movable_group.setTransformOriginPoint(item_print.boundingRect().topLeft())
                
                if i in saved_transforms:
                    movable_group.setScale(saved_transforms[i]['scale'])
                    movable_group.setPos(saved_transforms[i]['pos'])
                
                self.scene.addItem(movable_group)
                self.gcode_items.append(movable_group)

            for item in self.gcode_items: item.siblings = self.gcode_items

        self.fitInView(QRectF(0, 0, bed_max_x, bed_max_y), Qt.AspectRatioMode.KeepAspectRatio)
        self.centerOn(bed_max_x / 2.0, bed_max_y / 2.0)
        
    def update_nozzle_position(self, x, y, is_extruding):
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
                        'scale': item.scale(), 'gui_dx': item.pos().x(), 'gui_dy': item.pos().y(),
                        'cx': item.transformOriginPoint().x(), 'cy': item.transformOriginPoint().y()
                    })
                else: transforms.append({'deleted': True})
        return transforms
