"""
Object Snap (OSNAP) calculation engine: Endpoint, Midpoint, Center, Quadrant, Intersection, Grid.
"""

from typing import List, Optional, Tuple
from .geometry import Vec2, line_line_intersection
from .entities import CadEntity, LineEntity
from .document import CadDocument


class SnapResult:
    def __init__(self, point: Vec2, snap_type: str, entity: Optional[CadEntity] = None):
        self.point = point
        self.snap_type = snap_type  # 'ENDPOINT', 'MIDPOINT', 'CENTER', 'QUADRANT', 'INTERSECTION', 'GRID'
        self.entity = entity

    def __repr__(self):
        return f"SnapResult({self.snap_type} at {self.point})"


class SnapEngine:
    def __init__(self):
        self.osnap_enabled: bool = True
        self.grid_snap_enabled: bool = False
        self.grid_size: float = 10.0

        # Enabled snap modes
        self.enable_endpoint: bool = True
        self.enable_midpoint: bool = True
        self.enable_center: bool = True
        self.enable_quadrant: bool = True
        self.enable_intersection: bool = True

    def snap_to_grid(self, pt: Vec2) -> Vec2:
        if not self.grid_snap_enabled or self.grid_size <= 0:
            return pt
        gx = round(pt.x / self.grid_size) * self.grid_size
        gy = round(pt.y / self.grid_size) * self.grid_size
        return Vec2(gx, gy)

    def find_snap(self, doc: CadDocument, cursor_pt: Vec2, tolerance: float) -> Optional[SnapResult]:
        if not self.osnap_enabled:
            if self.grid_snap_enabled:
                gpt = self.snap_to_grid(cursor_pt)
                return SnapResult(gpt, "GRID")
            return None

        best_snap: Optional[SnapResult] = None
        best_dist = float('inf')

        # 1. Check entity keypoints (Endpoint, Midpoint, Center, Quadrant)
        for entity in doc.entities:
            layer = doc.layers.get(entity.layer)
            if layer and not layer.visible:
                continue

            for snap_type, pt in entity.get_snap_points():
                # Filter by enabled types
                if snap_type == "ENDPOINT" and not self.enable_endpoint:
                    continue
                if snap_type == "MIDPOINT" and not self.enable_midpoint:
                    continue
                if snap_type == "CENTER" and not self.enable_center:
                    continue
                if snap_type == "QUADRANT" and not self.enable_quadrant:
                    continue

                dist = cursor_pt.distance_to(pt)
                if dist <= tolerance and dist < best_dist:
                    best_dist = dist
                    best_snap = SnapResult(pt, snap_type, entity)

        # 2. Check Line-Line Intersections if enabled and tolerance permits
        if self.enable_intersection and best_dist > tolerance * 0.4:
            lines = [e for e in doc.entities if isinstance(e, LineEntity)]
            n = len(lines)
            for i in range(n):
                for j in range(i + 1, n):
                    ix = line_line_intersection(lines[i].start, lines[i].end, lines[j].start, lines[j].end)
                    if ix is not None:
                        dist = cursor_pt.distance_to(ix)
                        if dist <= tolerance and dist < best_dist:
                            best_dist = dist
                            best_snap = SnapResult(ix, "INTERSECTION")

        # Fallback to grid snap if enabled and no entity snapped
        if best_snap is None and self.grid_snap_enabled:
            gpt = self.snap_to_grid(cursor_pt)
            return SnapResult(gpt, "GRID")

        return best_snap

