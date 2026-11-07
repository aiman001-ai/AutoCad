"""
Interactive CAD graphics viewport with pan/zoom navigation, dynamic grid,
OSNAP markers, ortho/polar tracking, and selection management.
"""

import math
from typing import List, Optional, Tuple, Set
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, pyqtSignal
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPolygonF,
    QPainterPath, QMouseEvent, QWheelEvent, QKeyEvent, QAction
)

from cad_engine.geometry import Vec2, BBox, distance_point_to_segment
from cad_engine.entities import (
    CadEntity, LineEntity, CircleEntity, ArcEntity, RectEntity,
    PolylineEntity, SplineEntity, EllipseEntity, TextEntity, DimensionEntity
)
from cad_engine.document import CadDocument
from cad_engine.snap import SnapEngine, SnapResult


class CadViewport(QWidget):
    # Signals
    coordinates_changed = pyqtSignal(float, float)  # (world_x, world_y)
    selection_changed = pyqtSignal()
    status_message = pyqtSignal(str)
    command_finished = pyqtSignal(str)

    def __init__(self, doc: CadDocument, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.snap_engine = SnapEngine()

        # Canvas State
        self.pan_x: float = 0.0
        self.pan_y: float = 0.0
        self.zoom: float = 1.0  # Screen pixels per world unit

        # Drafting Modes
        self.grid_visible: bool = True
        self.ortho_enabled: bool = False      # F8
        self.polar_enabled: bool = True       # F10
        self.show_line_weights: bool = True
        self.is_3d_isometric: bool = False    # 3D view toggle

        # Current Tool
        self.current_tool: str = "SELECT"
        # Tool state buffer
        self.active_points: List[Vec2] = []
        self.cursor_world: Vec2 = Vec2(0, 0)
        self.last_snap: Optional[SnapResult] = None

        # Mouse interaction
        self.is_panning: bool = False
        self.pan_start_mouse: QPoint = QPoint()
        self.pan_start_cam: Tuple[float, float] = (0.0, 0.0)

        # Selection box
        self.is_box_selecting: bool = False
        self.box_start_world: Vec2 = Vec2(0, 0)
        self.box_current_world: Vec2 = Vec2(0, 0)

        # Enable mouse tracking for crosshair and OSNAP
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Background canvas palette
        self.bg_color = QColor(30, 32, 38)

    # Coordinate Conversions (Cartesian Y-Up)
    def world_to_screen(self, w: Vec2) -> QPointF:
        if self.is_3d_isometric:
            # Axonometric 30-degree projection
            iso_x = (w.x - w.y) * math.cos(math.radians(30))
            iso_y = (w.x + w.y) * math.sin(math.radians(30))
            sx = self.width() * 0.5 + (iso_x - self.pan_x) * self.zoom
            sy = self.height() * 0.5 - (iso_y - self.pan_y) * self.zoom
            return QPointF(sx, sy)

        sx = self.width() * 0.5 + (w.x - self.pan_x) * self.zoom
        sy = self.height() * 0.5 - (w.y - self.pan_y) * self.zoom
        return QPointF(sx, sy)

    def screen_to_world(self, s: QPointF) -> Vec2:
        wx = self.pan_x + (s.x() - self.width() * 0.5) / self.zoom
        wy = self.pan_y - (s.y() - self.height() * 0.5) / self.zoom
        return Vec2(wx, wy)

    def set_tool(self, tool_name: str):
        self.current_tool = tool_name
        self.active_points.clear()
        self.status_message.emit(f"Active Tool: {tool_name}")
        self.update()

    def cancel_tool(self):
        if self.active_points:
            self.active_points.clear()
            self.status_message.emit("Action cancelled")
        else:
            self.doc.clear_selection()
            self.current_tool = "SELECT"
            self.selection_changed.emit()
            self.status_message.emit("Ready")
        self.update()

    def zoom_extents(self):
        bbox = self.doc.get_total_bbox()
        if not bbox.is_valid():
            self.pan_x, self.pan_y = 0.0, 0.0
            self.zoom = 1.0
            self.update()
            return

        cx, cy = bbox.center.x, bbox.center.y
        w = max(10.0, bbox.width * 1.25)
        h = max(10.0, bbox.height * 1.25)

        view_w = max(100, self.width())
        view_h = max(100, self.height())

        scale_x = view_w / w
        scale_y = view_h / h

        self.pan_x = cx
        self.pan_y = cy
        self.zoom = min(scale_x, scale_y)
        self.update()

    def zoom_in(self):
        self.zoom *= 1.25
        self.update()

    def zoom_out(self):
        self.zoom /= 1.25
        self.update()

    # Paint Engine
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # 1. Fill background
        painter.fillRect(self.rect(), self.bg_color)

        # 2. Draw Dynamic Grid & Origin Axes
        if self.grid_visible and not self.is_3d_isometric:
            self._draw_grid(painter)

        self._draw_origin_axes(painter)

        # 3. Draw Document Entities
        self._draw_entities(painter)

        # 4. Draw Rubber-band Preview for active drawing tool
        self._draw_tool_preview(painter)

        # 5. Draw Polar Tracking Guideline
        if self.polar_enabled and len(self.active_points) > 0:
            self._draw_polar_tracking(painter)

        # 6. Draw Window/Crossing Selection Box
        if self.is_box_selecting:
            self._draw_selection_box(painter)

        # 7. Draw OSNAP marker & Crosshair Cursor
        if not self.is_panning:
            self._draw_osnap_marker(painter)
            self._draw_crosshairs(painter)

        painter.end()

    def _draw_grid(self, painter: QPainter):
        """Draws adaptive infinite Cartesian CAD grid."""
        # Calculate optimal grid spacing based on zoom
        min_pixels = 25
        base_step = 10.0
        exp = math.floor(math.log10(max(1e-5, min_pixels / (self.zoom * base_step))))
        spacing = (10 ** exp) * base_step
        if spacing * self.zoom < min_pixels:
            spacing *= 2
        if spacing * self.zoom < min_pixels:
            spacing *= 2.5

        top_left = self.screen_to_world(QPointF(0, 0))
        bottom_right = self.screen_to_world(QPointF(self.width(), self.height()))

        min_x = math.floor(min(top_left.x, bottom_right.x) / spacing) * spacing
        max_x = math.ceil(max(top_left.x, bottom_right.x) / spacing) * spacing
        min_y = math.floor(min(top_left.y, bottom_right.y) / spacing) * spacing
        max_y = math.ceil(max(top_left.y, bottom_right.y) / spacing) * spacing

        pen_minor = QPen(QColor(42, 45, 54), 1, Qt.PenStyle.DotLine)
        pen_major = QPen(QColor(52, 57, 68), 1, Qt.PenStyle.SolidLine)

        curr_x = min_x
        while curr_x <= max_x:
            is_major = math.isclose(curr_x % (spacing * 5), 0, abs_tol=1e-5)
            painter.setPen(pen_major if is_major else pen_minor)
            p1 = self.world_to_screen(Vec2(curr_x, min_y))
            p2 = self.world_to_screen(Vec2(curr_x, max_y))
            painter.drawLine(p1, p2)
            curr_x += spacing

        curr_y = min_y
        while curr_y <= max_y:
            is_major = math.isclose(curr_y % (spacing * 5), 0, abs_tol=1e-5)
            painter.setPen(pen_major if is_major else pen_minor)
            p1 = self.world_to_screen(Vec2(min_x, curr_y))
            p2 = self.world_to_screen(Vec2(max_x, curr_y))
            painter.drawLine(p1, p2)
            curr_y += spacing

    def _draw_origin_axes(self, painter: QPainter):
        """Draws UCS origin indicator (Red X, Green Y)."""
        origin = self.world_to_screen(Vec2(0, 0))
        axis_len = 60.0

        # X Axis - Red
        painter.setPen(QPen(QColor(231, 76, 60), 2))
        painter.drawLine(origin, QPointF(origin.x() + axis_len, origin.y()))
        painter.drawText(QPointF(origin.x() + axis_len + 5, origin.y() + 4), "X")

        # Y Axis - Green
        painter.setPen(QPen(QColor(46, 204, 113), 2))
        painter.drawLine(origin, QPointF(origin.x(), origin.y() - axis_len))
        painter.drawText(QPointF(origin.x() - 4, origin.y() - axis_len - 5), "Y")

    def _draw_entities(self, painter: QPainter):
        for e in self.doc.entities:
            layer = self.doc.layers.get(e.layer)
            if layer and not layer.visible:
                continue

            # Color resolution
            hex_color = self.doc.get_effective_color(e)
            qcolor = QColor(hex_color)

            # Pen setup
            lw = self.doc.get_effective_line_weight(e) if self.show_line_weights else 1.0
            screen_lw = max(1.0, lw * 1.5)

            pen = QPen(qcolor, screen_lw)
            if e.line_type == "DASHED":
                pen.setStyle(Qt.PenStyle.DashLine)
            elif e.line_type == "CENTER":
                pen.setStyle(Qt.PenStyle.DashDotLine)
            elif e.line_type == "HIDDEN":
                pen.setStyle(Qt.PenStyle.DotLine)

            # Selected entities highlighted with glowing cyan
            if e.selected:
                glow_pen = QPen(QColor(0, 220, 255, 180), screen_lw + 3)
                painter.setPen(glow_pen)
                self._render_single_entity(painter, e)
                pen = QPen(QColor(255, 255, 255), screen_lw, Qt.PenStyle.SolidLine)

            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            self._render_single_entity(painter, e)

            # Draw Grip points if selected
            if e.selected:
                self._draw_entity_grips(painter, e)

    def _render_single_entity(self, painter: QPainter, e: CadEntity):
        if isinstance(e, LineEntity):
            p1 = self.world_to_screen(e.start)
            p2 = self.world_to_screen(e.end)
            painter.drawLine(p1, p2)

        elif isinstance(e, CircleEntity):
            center = self.world_to_screen(e.center)
            r_px = e.radius * self.zoom
            painter.drawEllipse(center, r_px, r_px)

        elif isinstance(e, ArcEntity):
            center = self.world_to_screen(e.center)
            r_px = e.radius * self.zoom
            rect = QRectF(center.x() - r_px, center.y() - r_px, r_px * 2, r_px * 2)
            # In Qt, 0 deg is 3 o'clock, counter-clockwise is negative angles in screen space (since Y is down)
            start_qt = int(e.start_angle * 16)
            sweep_qt = int(e.sweep_angle * 16)
            painter.drawArc(rect, start_qt, sweep_qt)

        elif isinstance(e, RectEntity):
            c = [self.world_to_screen(pt) for pt in e.get_corners()]
            poly = QPolygonF(c)
            painter.drawPolygon(poly)

        elif isinstance(e, PolylineEntity):
            pts = [self.world_to_screen(pt) for pt in e.points]
            if len(pts) >= 2:
                poly = QPolygonF(pts)
                if e.is_closed:
                    painter.drawPolygon(poly)
                else:
                    painter.drawPolyline(poly)

        elif isinstance(e, SplineEntity):
            pts = [self.world_to_screen(pt) for pt in e._sampled_points]
            if len(pts) >= 2:
                poly = QPolygonF(pts)
                painter.drawPolyline(poly)

        elif isinstance(e, EllipseEntity):
            center = self.world_to_screen(e.center)
            rx_px = e.rx * self.zoom
            ry_px = e.ry * self.zoom
            painter.save()
            painter.translate(center)
            painter.rotate(-e.rotation_deg)
            painter.drawEllipse(QPointF(0, 0), rx_px, ry_px)
            painter.restore()

        elif isinstance(e, TextEntity):
            pos = self.world_to_screen(e.pos)
            h_px = max(8, int(e.height * self.zoom))
            font = QFont("Arial", h_px, QFont.Weight.Medium)
            painter.setFont(font)
            painter.save()
            painter.translate(pos)
            painter.rotate(-e.rotation_deg)
            painter.drawText(0, 0, e.text)
            painter.restore()

        elif isinstance(e, DimensionEntity):
            self._render_dimension(painter, e)

    def _render_dimension(self, painter: QPainter, e: DimensionEntity):
        d1, d2 = e.get_dim_line_points()
        p1_scr = self.world_to_screen(e.p1)
        p2_scr = self.world_to_screen(e.p2)
        d1_scr = self.world_to_screen(d1)
        d2_scr = self.world_to_screen(d2)

        # Extension lines
        dim_pen = QPen(painter.pen())
        dim_pen.setWidth(1)
        painter.setPen(dim_pen)
        painter.drawLine(p1_scr, d1_scr)
        painter.drawLine(p2_scr, d2_scr)
        # Main dimension line
        painter.drawLine(d1_scr, d2_scr)

        # Arrows/Ticks at endpoints
        v = d2_scr - d1_scr
        l = math.hypot(v.x(), v.y())
        if l > 0:
            ux, uy = v.x() / l, v.y() / l
            arrow_size = 8.0
            # Arrow at d1
            painter.drawLine(d1_scr, d1_scr + QPointF(ux * arrow_size + uy * 3, uy * arrow_size - ux * 3))
            painter.drawLine(d1_scr, d1_scr + QPointF(ux * arrow_size - uy * 3, uy * arrow_size + ux * 3))
            # Arrow at d2
            painter.drawLine(d2_scr, d2_scr + QPointF(-ux * arrow_size + uy * 3, -uy * arrow_size - ux * 3))
            painter.drawLine(d2_scr, d2_scr + QPointF(-ux * arrow_size - uy * 3, -uy * arrow_size + ux * 3))

        # Text in middle
        mid_scr = (d1_scr + d2_scr) * 0.5
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QPointF(mid_scr.x() - 15, mid_scr.y() - 4), e.display_text)

    def _draw_entity_grips(self, painter: QPainter, e: CadEntity):
        """Draws grip boxes on keypoints of selected entities."""
        grip_brush = QBrush(QColor(0, 122, 204))
        grip_pen = QPen(QColor(255, 255, 255), 1)
        painter.setBrush(grip_brush)
        painter.setPen(grip_pen)
        grip_size = 6.0

        for _, pt in e.get_snap_points():
            scr = self.world_to_screen(pt)
            painter.drawRect(QRectF(scr.x() - grip_size * 0.5, scr.y() - grip_size * 0.5, grip_size, grip_size))

    def _draw_tool_preview(self, painter: QPainter):
        """Rubber band preview of active drawing operation."""
        if not self.active_points and self.current_tool not in ("LINE", "CIRCLE", "RECT", "POLYLINE", "SPLINE", "DIMENSION"):
            return

        preview_pen = QPen(QColor(255, 200, 0), 1, Qt.PenStyle.DashLine)
        painter.setPen(preview_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        target = self.cursor_world

        if self.current_tool == "LINE" and self.active_points:
            p1 = self.world_to_screen(self.active_points[-1])
            p2 = self.world_to_screen(target)
            painter.drawLine(p1, p2)
            self._draw_hud_info(painter, p2, self.active_points[-1].distance_to(target), (target - self.active_points[-1]).angle_deg())

        elif self.current_tool == "CIRCLE" and self.active_points:
            c = self.active_points[0]
            r = c.distance_to(target)
            c_scr = self.world_to_screen(c)
            r_px = r * self.zoom
            painter.drawEllipse(c_scr, r_px, r_px)
            painter.drawLine(c_scr, self.world_to_screen(target))
            self._draw_hud_info(painter, self.world_to_screen(target), r, (target - c).angle_deg(), label="R")

        elif self.current_tool == "RECT" and self.active_points:
            p1 = self.active_points[0]
            corners = [
                self.world_to_screen(p1),
                self.world_to_screen(Vec2(target.x, p1.y)),
                self.world_to_screen(target),
                self.world_to_screen(Vec2(p1.x, target.y))
            ]
            painter.drawPolygon(QPolygonF(corners))

        elif self.current_tool == "POLYLINE" and self.active_points:
            pts = [self.world_to_screen(p) for p in self.active_points]
            pts.append(self.world_to_screen(target))
            painter.drawPolyline(QPolygonF(pts))

        elif self.current_tool == "SPLINE" and self.active_points:
            pts = list(self.active_points) + [target]
            temp_spline = SplineEntity(pts)
            curve_pts = [self.world_to_screen(p) for p in temp_spline._sampled_points]
            painter.drawPolyline(QPolygonF(curve_pts))

        elif self.current_tool == "DIMENSION" and self.active_points:
            p1 = self.active_points[0]
            temp_dim = DimensionEntity(p1, target, offset=20.0)
            self._render_dimension(painter, temp_dim)

    def _draw_hud_info(self, painter: QPainter, pos: QPointF, dist: float, angle: float, label: str = "L"):
        """Displays floating measurement HUD near the cursor."""
        text = f"{label}: {dist:.2f}  ∡ {angle:.1f}°"
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor(255, 255, 255))
        painter.setBrush(QBrush(QColor(30, 30, 30, 200)))
        rect = QRectF(pos.x() + 15, pos.y() - 25, 120, 20)
        painter.drawRoundedRect(rect, 3, 3)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_polar_tracking(self, painter: QPainter):
        """Draws polar tracking ray if cursor is near 0, 45, 90, 135, etc."""
        if not self.active_points:
            return
        origin = self.active_points[-1]
        v = self.cursor_world - origin
        deg = v.angle_deg()
        # Find nearest 45 degree angle
        nearest_step = round(deg / 45.0) * 45.0
        if abs(deg - nearest_step) <= 2.5:  # Tolerance
            rad = math.radians(nearest_step)
            ray_end = origin + Vec2(math.cos(rad), math.sin(rad)) * 5000.0
            p1 = self.world_to_screen(origin)
            p2 = self.world_to_screen(ray_end)
            painter.setPen(QPen(QColor(46, 204, 113, 180), 1, Qt.PenStyle.DashLine))
            painter.drawLine(p1, p2)

    def _draw_selection_box(self, painter: QPainter):
        p1 = self.world_to_screen(self.box_start_world)
        p2 = self.world_to_screen(self.box_current_world)
        rect = QRectF(p1, p2).normalized()

        if self.box_current_world.x >= self.box_start_world.x:
            # Window Selection (Blue)
            painter.setBrush(QBrush(QColor(0, 122, 204, 60)))
            painter.setPen(QPen(QColor(0, 122, 204), 1, Qt.PenStyle.SolidLine))
        else:
            # Crossing Selection (Green)
            painter.setBrush(QBrush(QColor(46, 204, 113, 60)))
            painter.setPen(QPen(QColor(46, 204, 113), 1, Qt.PenStyle.DashLine))
        painter.drawRect(rect)

    def _draw_osnap_marker(self, painter: QPainter):
        if not self.last_snap:
            return
        scr = self.world_to_screen(self.last_snap.point)
        snap_type = self.last_snap.snap_type
        painter.setPen(QPen(QColor(0, 255, 128), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        sz = 7.0
        if snap_type == "ENDPOINT":
            painter.drawRect(QRectF(scr.x() - sz, scr.y() - sz, sz * 2, sz * 2))
        elif snap_type == "MIDPOINT":
            poly = QPolygonF([
                QPointF(scr.x(), scr.y() - sz),
                QPointF(scr.x() - sz, scr.y() + sz),
                QPointF(scr.x() + sz, scr.y() + sz)
            ])
            painter.drawPolygon(poly)
        elif snap_type in ("CENTER", "GRID"):
            painter.drawEllipse(scr, sz, sz)
        elif snap_type in ("QUADRANT", "INTERSECTION"):
            painter.drawLine(QPointF(scr.x() - sz, scr.y() - sz), QPointF(scr.x() + sz, scr.y() + sz))
            painter.drawLine(QPointF(scr.x() - sz, scr.y() + sz), QPointF(scr.x() + sz, scr.y() - sz))

        # Tag label
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(QPointF(scr.x() + 10, scr.y() - 5), snap_type.capitalize())

    def _draw_crosshairs(self, painter: QPainter):
        """Draws crosshair cursor with central target box."""
        pos = self.mapFromGlobal(self.cursor().pos())
        cx, cy = pos.x(), pos.y()

        painter.setPen(QPen(QColor(180, 180, 180, 180), 1))
        # Horizontal & Vertical lines across window
        painter.drawLine(0, cy, self.width(), cy)
        painter.drawLine(cx, 0, cx, self.height())

        # Central Pickbox
        sz = 4.0
        painter.setPen(QPen(QColor(240, 240, 240), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(cx - sz, cy - sz, sz * 2, sz * 2))

    # Mouse Events
    def mousePressEvent(self, event: QMouseEvent):
        # Middle Mouse Button or Alt+Left Click: Pan
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and self.current_tool == "PAN"):
            self.is_panning = True
            self.pan_start_mouse = event.pos()
            self.pan_start_cam = (self.pan_x, self.pan_y)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.RightButton:
            self._handle_right_click(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            click_world = self._resolve_input_point(event.pos())

            if self.current_tool == "SELECT":
                # Hit test single entity
                tol = 8.0 / self.zoom
                hit = self.doc.find_at(click_world, tol)
                if hit:
                    if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                        if hit.selected:
                            self.doc.deselect(hit)
                        else:
                            self.doc.select(hit)
                    else:
                        self.doc.clear_selection()
                        self.doc.select(hit)
                    self.selection_changed.emit()
                    self.update()
                else:
                    # Start window/crossing selection box
                    if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                        self.doc.clear_selection()
                        self.selection_changed.emit()
                    self.is_box_selecting = True
                    self.box_start_world = click_world
                    self.box_current_world = click_world
                    self.update()

            elif self.current_tool in ("LINE", "CIRCLE", "RECT", "POLYLINE", "SPLINE", "DIMENSION"):
                self._handle_tool_click(click_world)

            elif self.current_tool == "TEXT":
                self.doc.add_entity(TextEntity("Sample Text", click_world))
                self.set_tool("SELECT")
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_panning:
            dx = (event.pos().x() - self.pan_start_mouse.x()) / self.zoom
            dy = (event.pos().y() - self.pan_start_mouse.y()) / self.zoom
            if not self.is_3d_isometric:
                self.pan_x = self.pan_start_cam[0] - dx
                self.pan_y = self.pan_start_cam[1] + dy
            self.update()
            return

        raw_world = self.screen_to_world(QPointF(event.pos()))

        # Check OSNAP
        tol_world = 12.0 / self.zoom
        snap = self.snap_engine.find_snap(self.doc, raw_world, tol_world)
        self.last_snap = snap

        curr_pt = snap.point if snap else raw_world

        # Check Ortho (F8)
        if self.ortho_enabled and self.active_points:
            anchor = self.active_points[-1]
            dx = abs(curr_pt.x - anchor.x)
            dy = abs(curr_pt.y - anchor.y)
            if dx > dy:
                curr_pt = Vec2(curr_pt.x, anchor.y)
            else:
                curr_pt = Vec2(anchor.x, curr_pt.y)

        self.cursor_world = curr_pt
        self.coordinates_changed.emit(self.cursor_world.x, self.cursor_world.y)

        if self.is_box_selecting:
            self.box_current_world = raw_world

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton or self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if event.button() == Qt.MouseButton.LeftButton and self.is_box_selecting:
            self.is_box_selecting = False
            box = BBox()
            box.expand_to_point(self.box_start_world)
            box.expand_to_point(self.box_current_world)
            is_crossing = self.box_current_world.x < self.box_start_world.x
            found = self.doc.find_in_box(box, crossing=is_crossing)
            for e in found:
                self.doc.select(e)
            self.selection_changed.emit()
            self.update()

    def wheelEvent(self, event: QWheelEvent):
        # Zoom centered at mouse position
        mouse_scr = QPointF(event.position())
        mouse_world_before = self.screen_to_world(mouse_scr)

        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 0.85
        self.zoom *= factor

        # Clamp zoom
        self.zoom = max(0.001, min(1000.0, self.zoom))

        mouse_world_after = self.screen_to_world(mouse_scr)
        self.pan_x += (mouse_world_before.x - mouse_world_after.x)
        self.pan_y += (mouse_world_before.y - mouse_world_after.y)

        self.update()

    def _resolve_input_point(self, pos: QPoint) -> Vec2:
        if self.last_snap:
            return self.last_snap.point
        return self.cursor_world

    def _handle_tool_click(self, pt: Vec2):
        if self.current_tool == "LINE":
            if not self.active_points:
                self.active_points.append(pt)
                self.status_message.emit("Specify next point:")
            else:
                self.doc.add_entity(LineEntity(self.active_points[-1], pt))
                self.active_points = [pt]  # Continuous segment chain
                self.status_message.emit("Specify next point [or Enter to finish]:")
                self.update()

        elif self.current_tool == "CIRCLE":
            if not self.active_points:
                self.active_points.append(pt)
                self.status_message.emit("Specify radius of circle:")
            else:
                c = self.active_points[0]
                r = c.distance_to(pt)
                self.doc.add_entity(CircleEntity(c, r))
                self.active_points.clear()
                self.set_tool("SELECT")

        elif self.current_tool == "RECT":
            if not self.active_points:
                self.active_points.append(pt)
                self.status_message.emit("Specify other corner:")
            else:
                self.doc.add_entity(RectEntity(self.active_points[0], pt))
                self.active_points.clear()
                self.set_tool("SELECT")

        elif self.current_tool == "POLYLINE":
            self.active_points.append(pt)
            self.status_message.emit(f"Polyline: {len(self.active_points)} points. Right click or Enter to finish.")
            self.update()

        elif self.current_tool == "SPLINE":
            self.active_points.append(pt)
            self.status_message.emit(f"Spline: {len(self.active_points)} points. Right click or Enter to finish.")
            self.update()

        elif self.current_tool == "DIMENSION":
            if not self.active_points:
                self.active_points.append(pt)
                self.status_message.emit("Specify second extension line origin:")
            else:
                p1 = self.active_points[0]
                self.doc.add_entity(DimensionEntity(p1, pt))
                self.active_points.clear()
                self.set_tool("SELECT")

    def _handle_right_click(self, event: QMouseEvent):
        # Finish polyline or spline
        if self.current_tool == "POLYLINE" and len(self.active_points) >= 2:
            self.doc.add_entity(PolylineEntity(self.active_points))
            self.active_points.clear()
            self.set_tool("SELECT")
            self.update()
            return

        if self.current_tool == "SPLINE" and len(self.active_points) >= 2:
            self.doc.add_entity(SplineEntity(self.active_points))
            self.active_points.clear()
            self.set_tool("SELECT")
            self.update()
            return

        if self.active_points or self.current_tool != "SELECT":
            self.cancel_tool()
            return

        # Context Menu
        menu = QMenu(self)
        act_undo = menu.addAction("Undo")
        act_redo = menu.addAction("Redo")
        menu.addSeparator()
        act_extents = menu.addAction("Zoom Extents")
        act_del = menu.addAction("Erase Selected")
        menu.addSeparator()
        act_cancel = menu.addAction("Cancel")

        action = menu.exec(event.globalPosition().toPoint())
        if action == act_undo:
            self.doc.undo()
            self.update()
        elif action == act_redo:
            self.doc.redo()
            self.update()
        elif action == act_extents:
            self.zoom_extents()
        elif action == act_del:
            self.doc.delete_selected()
            self.selection_changed.emit()
            self.update()
        elif action == act_cancel:
            self.cancel_tool()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        if key == Qt.Key.Key_Escape:
            self.cancel_tool()

        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.current_tool == "POLYLINE" and len(self.active_points) >= 2:
                self.doc.add_entity(PolylineEntity(self.active_points))
                self.active_points.clear()
                self.set_tool("SELECT")
                self.update()
            elif self.current_tool == "SPLINE" and len(self.active_points) >= 2:
                self.doc.add_entity(SplineEntity(self.active_points))
                self.active_points.clear()
                self.set_tool("SELECT")
                self.update()
            elif self.current_tool == "LINE":
                self.active_points.clear()
                self.set_tool("SELECT")
                self.update()

        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.doc.delete_selected()
            self.selection_changed.emit()
            self.update()

        # Function Keys shortcuts
        elif key == Qt.Key.Key_F3:
            self.snap_engine.osnap_enabled = not self.snap_engine.osnap_enabled
            self.status_message.emit(f"OSNAP {'ON' if self.snap_engine.osnap_enabled else 'OFF'}")
            self.update()

        elif key == Qt.Key.Key_F7:
            self.grid_visible = not self.grid_visible
            self.status_message.emit(f"GRID {'ON' if self.grid_visible else 'OFF'}")
            self.update()

        elif key == Qt.Key.Key_F8:
            self.ortho_enabled = not self.ortho_enabled
            self.status_message.emit(f"ORTHO {'ON' if self.ortho_enabled else 'OFF'}")
            self.update()

        elif key == Qt.Key.Key_F9:
            self.snap_engine.grid_snap_enabled = not self.snap_engine.grid_snap_enabled
            self.status_message.emit(f"SNAP {'ON' if self.snap_engine.grid_snap_enabled else 'OFF'}")
            self.update()

        elif key == Qt.Key.Key_F10:
            self.polar_enabled = not self.polar_enabled
            self.status_message.emit(f"POLAR {'ON' if self.polar_enabled else 'OFF'}")
            self.update()
        else:
            super().keyPressEvent(event)

