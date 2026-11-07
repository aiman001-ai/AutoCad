"""
Geometric entity models: Line, Circle, Arc, Rect, Polyline, Spline, Ellipse, Text, and Dimension.
"""

import math
import uuid
from typing import List, Dict, Tuple, Optional, Any
from .geometry import Vec2, BBox, distance_point_to_segment, closest_point_on_segment


class CadEntity:
    """Base class for all CAD geometric entities."""

    def __init__(self, layer: str = "0", color: str = "BYLAYER", line_width: float = 1.0, line_type: str = "CONTINUOUS"):
        self.id: str = uuid.uuid4().hex[:8].upper()
        self.layer: str = layer
        self.color: str = color  # "BYLAYER" or "#RRGGBB"
        self.line_width: float = line_width
        self.line_type: str = line_type
        self.selected: bool = False
        self.visible: bool = True

    @property
    def entity_type(self) -> str:
        return self.__class__.__name__.replace("Entity", "").upper()

    def get_bbox(self) -> BBox:
        raise NotImplementedError

    def get_snap_points(self) -> List[Tuple[str, Vec2]]:
        """Returns list of (snap_type, point) where snap_type is ENDPOINT, MIDPOINT, CENTER, etc."""
        return []

    def hit_test(self, pt: Vec2, tolerance: float) -> bool:
        raise NotImplementedError

    def move(self, delta: Vec2):
        raise NotImplementedError

    def rotate(self, angle_rad: float, center: Vec2):
        raise NotImplementedError

    def scale(self, factor: float, center: Vec2):
        raise NotImplementedError

    def clone(self) -> 'CadEntity':
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.entity_type,
            "id": self.id,
            "layer": self.layer,
            "color": self.color,
            "line_width": self.line_width,
            "line_type": self.line_type,
        }


class LineEntity(CadEntity):
    def __init__(self, start: Vec2, end: Vec2, **kwargs):
        super().__init__(**kwargs)
        self.start = Vec2(start.x, start.y)
        self.end = Vec2(end.x, end.y)

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def angle_deg(self) -> float:
        return (self.end - self.start).angle_deg()

    def get_bbox(self) -> BBox:
        bb = BBox()
        bb.expand_to_point(self.start)
        bb.expand_to_point(self.end)
        return bb

    def get_snap_points(self) -> List[Tuple[str, Vec2]]:
        mid = (self.start + self.end) * 0.5
        return [
            ("ENDPOINT", self.start),
            ("ENDPOINT", self.end),
            ("MIDPOINT", mid),
        ]

    def hit_test(self, pt: Vec2, tolerance: float) -> bool:
        return distance_point_to_segment(pt, self.start, self.end) <= tolerance

    def move(self, delta: Vec2):
        self.start = self.start + delta
        self.end = self.end + delta

    def rotate(self, angle_rad: float, center: Vec2):
        self.start = self.start.rotated(angle_rad, center)
        self.end = self.end.rotated(angle_rad, center)

    def scale(self, factor: float, center: Vec2):
        self.start = center + (self.start - center) * factor
        self.end = center + (self.end - center) * factor

    def clone(self) -> 'LineEntity':
        e = LineEntity(self.start, self.end, layer=self.layer, color=self.color,
                       line_width=self.line_width, line_type=self.line_type)
        return e

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "start": [self.start.x, self.start.y],
            "end": [self.end.x, self.end.y]
        })
        return d


class CircleEntity(CadEntity):
    def __init__(self, center: Vec2, radius: float, **kwargs):
        super().__init__(**kwargs)
        self.center = Vec2(center.x, center.y)
        self.radius = max(0.0001, float(radius))

    @property
    def diameter(self) -> float:
        return self.radius * 2.0

    @property
    def circumference(self) -> float:
        return 2.0 * math.pi * self.radius

    @property
    def area(self) -> float:
        return math.pi * self.radius * self.radius

    def get_bbox(self) -> BBox:
        return BBox(
            self.center.x - self.radius, self.center.y - self.radius,
            self.center.x + self.radius, self.center.y + self.radius
        )

    def get_snap_points(self) -> List[Tuple[str, Vec2]]:
        cx, cy, r = self.center.x, self.center.y, self.radius
        return [
            ("CENTER", self.center),
            ("QUADRANT", Vec2(cx + r, cy)),
            ("QUADRANT", Vec2(cx - r, cy)),
            ("QUADRANT", Vec2(cx, cy + r)),
            ("QUADRANT", Vec2(cx, cy - r)),
        ]

    def hit_test(self, pt: Vec2, tolerance: float) -> bool:
        dist = pt.distance_to(self.center)
        # Hit either on perimeter or if tolerance is large
        return abs(dist - self.radius) <= tolerance

    def move(self, delta: Vec2):
        self.center = self.center + delta

    def rotate(self, angle_rad: float, center: Vec2):
        self.center = self.center.rotated(angle_rad, center)

    def scale(self, factor: float, center: Vec2):
        self.center = center + (self.center - center) * factor
        self.radius *= abs(factor)

    def clone(self) -> 'CircleEntity':
        return CircleEntity(self.center, self.radius, layer=self.layer, color=self.color,
                            line_width=self.line_width, line_type=self.line_type)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "center": [self.center.x, self.center.y],
            "radius": self.radius
        })
        return d


class ArcEntity(CadEntity):
    def __init__(self, center: Vec2, radius: float, start_angle_deg: float, end_angle_deg: float, **kwargs):
        super().__init__(**kwargs)
        self.center = Vec2(center.x, center.y)
        self.radius = max(0.0001, float(radius))
        self.start_angle = float(start_angle_deg) % 360.0
        self.end_angle = float(end_angle_deg) % 360.0

    @property
    def sweep_angle(self) -> float:
        sweep = (self.end_angle - self.start_angle) % 360.0
        return 360.0 if sweep == 0 else sweep

    @property
    def arc_length(self) -> float:
        return 2.0 * math.pi * self.radius * (self.sweep_angle / 360.0)

    def get_start_point(self) -> Vec2:
        rad = math.radians(self.start_angle)
        return Vec2(self.center.x + self.radius * math.cos(rad),
                    self.center.y + self.radius * math.sin(rad))

    def get_end_point(self) -> Vec2:
        rad = math.radians(self.end_angle)
        return Vec2(self.center.x + self.radius * math.cos(rad),
                    self.center.y + self.radius * math.sin(rad))

    def get_mid_point(self) -> Vec2:
        mid_ang = math.radians((self.start_angle + self.sweep_angle * 0.5) % 360.0)
        return Vec2(self.center.x + self.radius * math.cos(mid_ang),
                    self.center.y + self.radius * math.sin(mid_ang))

    def get_bbox(self) -> BBox:
        bb = BBox()
        bb.expand_to_point(self.get_start_point())
        bb.expand_to_point(self.get_end_point())
        # Check cardinal directions 0, 90, 180, 270 if enclosed by arc
        for card in [0, 90, 180, 270]:
            diff = (card - self.start_angle) % 360.0
            if diff <= self.sweep_angle:
                rad = math.radians(card)
                bb.expand_to_point(Vec2(self.center.x + self.radius * math.cos(rad),
                                        self.center.y + self.radius * math.sin(rad)))
        return bb

    def get_snap_points(self) -> List[Tuple[str, Vec2]]:
        return [
            ("ENDPOINT", self.get_start_point()),
            ("ENDPOINT", self.get_end_point()),
            ("MIDPOINT", self.get_mid_point()),
            ("CENTER", self.center),
        ]

    def hit_test(self, pt: Vec2, tolerance: float) -> bool:
        dist = pt.distance_to(self.center)
        if abs(dist - self.radius) > tolerance:
            return False
        ang = (pt - self.center).angle_deg()
        diff = (ang - self.start_angle) % 360.0
        return diff <= self.sweep_angle

    def move(self, delta: Vec2):
        self.center = self.center + delta

    def rotate(self, angle_rad: float, center: Vec2):
        self.center = self.center.rotated(angle_rad, center)
        deg = math.degrees(angle_rad)
        self.start_angle = (self.start_angle + deg) % 360.0
        self.end_angle = (self.end_angle + deg) % 360.0

    def scale(self, factor: float, center: Vec2):
        self.center = center + (self.center - center) * factor
        self.radius *= abs(factor)

    def clone(self) -> 'ArcEntity':
        return ArcEntity(self.center, self.radius, self.start_angle, self.end_angle,
                         layer=self.layer, color=self.color, line_width=self.line_width, line_type=self.line_type)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "center": [self.center.x, self.center.y],
            "radius": self.radius,
            "start_angle": self.start_angle,
            "end_angle": self.end_angle
        })
        return d


class RectEntity(CadEntity):
    def __init__(self, p1: Vec2, p2: Vec2, **kwargs):
        super().__init__(**kwargs)
        self.p1 = Vec2(min(p1.x, p2.x), min(p1.y, p2.y))
        self.p2 = Vec2(max(p1.x, p2.x), max(p1.y, p2.y))

    @property
    def width(self) -> float:
        return self.p2.x - self.p1.x

    @property
    def height(self) -> float:
        return self.p2.y - self.p1.y

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def perimeter(self) -> float:
        return 2.0 * (self.width + self.height)

    def get_corners(self) -> List[Vec2]:
        return [
            self.p1,
            Vec2(self.p2.x, self.p1.y),
            self.p2,
            Vec2(self.p1.x, self.p2.y)
        ]

    def get_bbox(self) -> BBox:
        return BBox(self.p1.x, self.p1.y, self.p2.x, self.p2.y)

    def get_snap_points(self) -> List[Tuple[str, Vec2]]:
        c = self.get_corners()
        snaps = [("ENDPOINT", pt) for pt in c]
        snaps.append(("MIDPOINT", (c[0] + c[1]) * 0.5))
        snaps.append(("MIDPOINT", (c[1] + c[2]) * 0.5))
        snaps.append(("MIDPOINT", (c[2] + c[3]) * 0.5))
        snaps.append(("MIDPOINT", (c[3] + c[0]) * 0.5))
        snaps.append(("CENTER", (self.p1 + self.p2) * 0.5))
        return snaps

    def hit_test(self, pt: Vec2, tolerance: float) -> bool:
        c = self.get_corners()
        for i in range(4):
            if distance_point_to_segment(pt, c[i], c[(i + 1) % 4]) <= tolerance:
                return True
        return False

    def move(self, delta: Vec2):
        self.p1 = self.p1 + delta
        self.p2 = self.p2 + delta

    def rotate(self, angle_rad: float, center: Vec2):
        # When rotated, becomes polyline or rotated points
        p1 = self.p1.rotated(angle_rad, center)
        p2 = self.p2.rotated(angle_rad, center)
        self.p1 = Vec2(min(p1.x, p2.x), min(p1.y, p2.y))
        self.p2 = Vec2(max(p1.x, p2.x), max(p1.y, p2.y))

    def scale(self, factor: float, center: Vec2):
        self.p1 = center + (self.p1 - center) * factor
        self.p2 = center + (self.p2 - center) * factor

    def clone(self) -> 'RectEntity':
        return RectEntity(self.p1, self.p2, layer=self.layer, color=self.color,
                          line_width=self.line_width, line_type=self.line_type)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "p1": [self.p1.x, self.p1.y],
            "p2": [self.p2.x, self.p2.y]
        })
        return d


class PolylineEntity(CadEntity):
    def __init__(self, points: List[Vec2], is_closed: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.points = [Vec2(p.x, p.y) for p in points]
        self.is_closed = is_closed

    @property
    def total_length(self) -> float:
        tot = 0.0
        n = len(self.points)
        if n < 2:
            return 0.0
        for i in range(n - 1):
            tot += self.points[i].distance_to(self.points[i + 1])
        if self.is_closed and n > 2:
            tot += self.points[-1].distance_to(self.points[0])
        return tot

    def get_bbox(self) -> BBox:
        bb = BBox()
        for p in self.points:
            bb.expand_to_point(p)
        return bb

    def get_snap_points(self) -> List[Tuple[str, Vec2]]:
        snaps = []
        n = len(self.points)
        for i, pt in enumerate(self.points):
            snaps.append(("ENDPOINT", pt))
            if i < n - 1:
                snaps.append(("MIDPOINT", (pt + self.points[i + 1]) * 0.5))
        if self.is_closed and n > 2:
            snaps.append(("MIDPOINT", (self.points[-1] + self.points[0]) * 0.5))
        return snaps

    def hit_test(self, pt: Vec2, tolerance: float) -> bool:
        n = len(self.points)
        for i in range(n - 1):
            if distance_point_to_segment(pt, self.points[i], self.points[i + 1]) <= tolerance:
                return True
        if self.is_closed and n > 2:
            if distance_point_to_segment(pt, self.points[-1], self.points[0]) <= tolerance:
                return True
        return False

    def move(self, delta: Vec2):
        self.points = [p + delta for p in self.points]

    def rotate(self, angle_rad: float, center: Vec2):
        self.points = [p.rotated(angle_rad, center) for p in self.points]

    def scale(self, factor: float, center: Vec2):
        self.points = [center + (p - center) * factor for p in self.points]

    def clone(self) -> 'PolylineEntity':
        return PolylineEntity(self.points, self.is_closed, layer=self.layer, color=self.color,
                              line_width=self.line_width, line_type=self.line_type)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "points": [[p.x, p.y] for p in self.points],
            "is_closed": self.is_closed
        })
        return d


class SplineEntity(CadEntity):
    def __init__(self, control_points: List[Vec2], **kwargs):
        super().__init__(**kwargs)
        self.control_points = [Vec2(p.x, p.y) for p in control_points]
        self._sampled_points = self._compute_curve()

    def _compute_curve(self, samples_per_seg: int = 16) -> List[Vec2]:
        pts = self.control_points
        n = len(pts)
        if n < 2:
            return pts[:]
        if n == 2:
            return [pts[0], pts[1]]

        # Catmull-Rom spline interpolation through control points
        curve = []
        for i in range(n - 1):
            p0 = pts[max(0, i - 1)]
            p1 = pts[i]
            p2 = pts[i + 1]
            p3 = pts[min(n - 1, i + 2)]

            for s in range(samples_per_seg):
                t = s / float(samples_per_seg)
                t2 = t * t
                t3 = t2 * t
                # Catmull-Rom formula
                x = 0.5 * ((2 * p1.x) +
                           (-p0.x + p2.x) * t +
                           (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 +
                           (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3)
                y = 0.5 * ((2 * p1.y) +
                           (-p0.y + p2.y) * t +
                           (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 +
                           (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3)
                curve.append(Vec2(x, y))
        curve.append(pts[-1])
        return curve

    def get_bbox(self) -> BBox:
        bb = BBox()
        for p in self._sampled_points:
            bb.expand_to_point(p)
        return bb

    def get_snap_points(self) -> List[Tuple[str, Vec2]]:
        snaps = [("ENDPOINT", self.control_points[0]), ("ENDPOINT", self.control_points[-1])]
        for p in self.control_points[1:-1]:
            snaps.append(("MIDPOINT", p))
        return snaps

    def hit_test(self, pt: Vec2, tolerance: float) -> bool:
        curve = self._sampled_points
        for i in range(len(curve) - 1):
            if distance_point_to_segment(pt, curve[i], curve[i + 1]) <= tolerance:
                return True
        return False

    def move(self, delta: Vec2):
        self.control_points = [p + delta for p in self.control_points]
        self._sampled_points = self._compute_curve()

    def rotate(self, angle_rad: float, center: Vec2):
        self.control_points = [p.rotated(angle_rad, center) for p in self.control_points]
        self._sampled_points = self._compute_curve()

    def scale(self, factor: float, center: Vec2):
        self.control_points = [center + (p - center) * factor for p in self.control_points]
        self._sampled_points = self._compute_curve()

    def clone(self) -> 'SplineEntity':
        return SplineEntity(self.control_points, layer=self.layer, color=self.color,
                            line_width=self.line_width, line_type=self.line_type)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "control_points": [[p.x, p.y] for p in self.control_points]
        })
        return d


class EllipseEntity(CadEntity):
    def __init__(self, center: Vec2, rx: float, ry: float, rotation_deg: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.center = Vec2(center.x, center.y)
        self.rx = max(0.001, float(rx))
        self.ry = max(0.001, float(ry))
        self.rotation_deg = float(rotation_deg)

    def get_bbox(self) -> BBox:
        # Approximate bounding box
        max_r = max(self.rx, self.ry)
        return BBox(self.center.x - max_r, self.center.y - max_r,
                    self.center.x + max_r, self.center.y + max_r)

    def get_snap_points(self) -> List[Tuple[str, Vec2]]:
        cx, cy = self.center.x, self.center.y
        rad = math.radians(self.rotation_deg)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        return [
            ("CENTER", self.center),
            ("QUADRANT", Vec2(cx + self.rx * cos_r, cy + self.rx * sin_r)),
            ("QUADRANT", Vec2(cx - self.rx * cos_r, cy - self.rx * sin_r)),
            ("QUADRANT", Vec2(cx - self.ry * sin_r, cy + self.ry * cos_r)),
            ("QUADRANT", Vec2(cx + self.ry * sin_r, cy - self.ry * cos_r)),
        ]

    def hit_test(self, pt: Vec2, tolerance: float) -> bool:
        # Unrotate point
        p_rel = (pt - self.center).rotated(-math.radians(self.rotation_deg))
        # Ellipse equation normalized: (x/rx)^2 + (y/ry)^2 ~ 1
        val = (p_rel.x / self.rx) ** 2 + (p_rel.y / self.ry) ** 2
        # Check proximity to 1.0 boundary
        dist = abs(math.sqrt(max(0.0, val)) - 1.0) * min(self.rx, self.ry)
        return dist <= tolerance

    def move(self, delta: Vec2):
        self.center = self.center + delta

    def rotate(self, angle_rad: float, center: Vec2):
        self.center = self.center.rotated(angle_rad, center)
        self.rotation_deg = (self.rotation_deg + math.degrees(angle_rad)) % 360.0

    def scale(self, factor: float, center: Vec2):
        self.center = center + (self.center - center) * factor
        self.rx *= abs(factor)
        self.ry *= abs(factor)

    def clone(self) -> 'EllipseEntity':
        return EllipseEntity(self.center, self.rx, self.ry, self.rotation_deg,
                             layer=self.layer, color=self.color, line_width=self.line_width, line_type=self.line_type)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "center": [self.center.x, self.center.y],
            "rx": self.rx,
            "ry": self.ry,
            "rotation_deg": self.rotation_deg
        })
        return d


class TextEntity(CadEntity):
    def __init__(self, text: str, pos: Vec2, height: float = 12.0, rotation_deg: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.text = str(text)
        self.pos = Vec2(pos.x, pos.y)
        self.height = max(1.0, float(height))
        self.rotation_deg = float(rotation_deg)

    def get_bbox(self) -> BBox:
        # Rough estimation of text width: ~0.6 * height * length
        w = len(self.text) * self.height * 0.6
        h = self.height
        return BBox(self.pos.x, self.pos.y - h, self.pos.x + w, self.pos.y + h * 0.2)

    def get_snap_points(self) -> List[Tuple[str, Vec2]]:
        return [("ENDPOINT", self.pos)]

    def hit_test(self, pt: Vec2, tolerance: float) -> bool:
        return self.get_bbox().buffer(tolerance).contains_point(pt)

    def move(self, delta: Vec2):
        self.pos = self.pos + delta

    def rotate(self, angle_rad: float, center: Vec2):
        self.pos = self.pos.rotated(angle_rad, center)
        self.rotation_deg = (self.rotation_deg + math.degrees(angle_rad)) % 360.0

    def scale(self, factor: float, center: Vec2):
        self.pos = center + (self.pos - center) * factor
        self.height *= abs(factor)

    def clone(self) -> 'TextEntity':
        return TextEntity(self.text, self.pos, self.height, self.rotation_deg,
                          layer=self.layer, color=self.color, line_width=self.line_width, line_type=self.line_type)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "text": self.text,
            "pos": [self.pos.x, self.pos.y],
            "height": self.height,
            "rotation_deg": self.rotation_deg
        })
        return d


class DimensionEntity(CadEntity):
    """Linear dimension entity with extension lines, dimension line, ticks/arrows, and distance text."""
    def __init__(self, p1: Vec2, p2: Vec2, offset: float = 20.0, text: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.p1 = Vec2(p1.x, p1.y)
        self.p2 = Vec2(p2.x, p2.y)
        self.offset = float(offset)
        self.custom_text = text

    @property
    def distance(self) -> float:
        return self.p1.distance_to(self.p2)

    @property
    def display_text(self) -> str:
        if self.custom_text:
            return self.custom_text
        return f"{self.distance:.1f}"

    def get_dim_line_points(self) -> Tuple[Vec2, Vec2]:
        v = self.p2 - self.p1
        l = v.length()
        if l == 0:
            return (self.p1, self.p2)
        normal = Vec2(-v.y / l, v.x / l)
        d1 = self.p1 + normal * self.offset
        d2 = self.p2 + normal * self.offset
        return (d1, d2)

    def get_bbox(self) -> BBox:
        bb = BBox()
        bb.expand_to_point(self.p1)
        bb.expand_to_point(self.p2)
        d1, d2 = self.get_dim_line_points()
        bb.expand_to_point(d1)
        bb.expand_to_point(d2)
        return bb

    def get_snap_points(self) -> List[Tuple[str, Vec2]]:
        d1, d2 = self.get_dim_line_points()
        return [
            ("ENDPOINT", self.p1),
            ("ENDPOINT", self.p2),
            ("MIDPOINT", (d1 + d2) * 0.5),
        ]

    def hit_test(self, pt: Vec2, tolerance: float) -> bool:
        d1, d2 = self.get_dim_line_points()
        if distance_point_to_segment(pt, d1, d2) <= tolerance:
            return True
        if distance_point_to_segment(pt, self.p1, d1) <= tolerance:
            return True
        if distance_point_to_segment(pt, self.p2, d2) <= tolerance:
            return True
        return False

    def move(self, delta: Vec2):
        self.p1 = self.p1 + delta
        self.p2 = self.p2 + delta

    def rotate(self, angle_rad: float, center: Vec2):
        self.p1 = self.p1.rotated(angle_rad, center)
        self.p2 = self.p2.rotated(angle_rad, center)

    def scale(self, factor: float, center: Vec2):
        self.p1 = center + (self.p1 - center) * factor
        self.p2 = center + (self.p2 - center) * factor
        self.offset *= abs(factor)

    def clone(self) -> 'DimensionEntity':
        return DimensionEntity(self.p1, self.p2, self.offset, self.custom_text,
                               layer=self.layer, color=self.color, line_width=self.line_width, line_type=self.line_type)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "p1": [self.p1.x, self.p1.y],
            "p2": [self.p2.x, self.p2.y],
            "offset": self.offset,
            "text": self.custom_text
        })
        return d

