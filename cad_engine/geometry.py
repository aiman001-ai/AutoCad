"""
2D and 3D vector math, bounding boxes, and geometric intersection algorithms.
"""

import math
from typing import List, Tuple, Optional


class Vec2:
    __slots__ = ('x', 'y')

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    def __repr__(self):
        return f"Vec2({self.x:.3f}, {self.y:.3f})"

    def __eq__(self, other):
        if not isinstance(other, Vec2):
            return False
        return math.isclose(self.x, other.x, abs_tol=1e-7) and math.isclose(self.y, other.y, abs_tol=1e-7)

    def __hash__(self):
        return hash((round(self.x, 5), round(self.y, 5)))

    def __add__(self, other: 'Vec2') -> 'Vec2':
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vec2') -> 'Vec2':
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> 'Vec2':
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> 'Vec2':
        return Vec2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> 'Vec2':
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide vector by zero")
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> 'Vec2':
        return Vec2(-self.x, -self.y)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def distance_to(self, other: 'Vec2') -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def normalized(self) -> 'Vec2':
        l = self.length()
        if l == 0:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / l, self.y / l)

    def dot(self, other: 'Vec2') -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: 'Vec2') -> float:
        return self.x * other.y - self.y * other.x

    def angle_rad(self) -> float:
        return math.atan2(self.y, self.x)

    def angle_deg(self) -> float:
        deg = math.degrees(math.atan2(self.y, self.x))
        return deg if deg >= 0 else deg + 360.0

    def rotated(self, angle_rad: float, center: Optional['Vec2'] = None) -> 'Vec2':
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        if center is None:
            return Vec2(self.x * c - self.y * s, self.x * s + self.y * c)
        dx = self.x - center.x
        dy = self.y - center.y
        rx = dx * c - dy * s
        ry = dx * s + dy * c
        return Vec2(center.x + rx, center.y + ry)

    def lerp(self, other: 'Vec2', t: float) -> 'Vec2':
        return Vec2(self.x + (other.x - self.x) * t, self.y + (other.y - self.y) * t)

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


class Vec3:
    __slots__ = ('x', 'y', 'z')

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __repr__(self):
        return f"Vec3({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"

    def to_vec2(self) -> Vec2:
        return Vec2(self.x, self.y)


class BBox:
    """Axis-Aligned Bounding Box (AABB)"""
    def __init__(self, min_x: float = float('inf'), min_y: float = float('inf'),
                 max_x: float = float('-inf'), max_y: float = float('-inf')):
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y

    def is_valid(self) -> bool:
        return self.min_x <= self.max_x and self.min_y <= self.max_y

    def expand_to_point(self, pt: Vec2):
        if pt.x < self.min_x:
            self.min_x = pt.x
        if pt.x > self.max_x:
            self.max_x = pt.x
        if pt.y < self.min_y:
            self.min_y = pt.y
        if pt.y > self.max_y:
            self.max_y = pt.y

    def expand_to_bbox(self, other: 'BBox'):
        if not other.is_valid():
            return
        if other.min_x < self.min_x:
            self.min_x = other.min_x
        if other.max_x > self.max_x:
            self.max_x = other.max_x
        if other.min_y < self.min_y:
            self.min_y = other.min_y
        if other.max_y > self.max_y:
            self.max_y = other.max_y

    @property
    def width(self) -> float:
        return max(0.0, self.max_x - self.min_x)

    @property
    def height(self) -> float:
        return max(0.0, self.max_y - self.min_y)

    @property
    def center(self) -> Vec2:
        return Vec2((self.min_x + self.max_x) * 0.5, (self.min_y + self.max_y) * 0.5)

    def contains_point(self, pt: Vec2) -> bool:
        return self.min_x <= pt.x <= self.max_x and self.min_y <= pt.y <= self.max_y

    def contains_bbox(self, other: 'BBox') -> bool:
        return (self.min_x <= other.min_x and self.max_x >= other.max_x and
                self.min_y <= other.min_y and self.max_y >= other.max_y)

    def intersects(self, other: 'BBox') -> bool:
        return not (self.max_x < other.min_x or self.min_x > other.max_x or
                    self.max_y < other.min_y or self.min_y > other.max_y)

    def buffer(self, padding: float) -> 'BBox':
        return BBox(self.min_x - padding, self.min_y - padding,
                    self.max_x + padding, self.max_y + padding)


def distance_point_to_segment(p: Vec2, a: Vec2, b: Vec2) -> float:
    ab = b - a
    l_sq = ab.length_sq()
    if l_sq == 0.0:
        return p.distance_to(a)
    t = max(0.0, min(1.0, (p - a).dot(ab) / l_sq))
    projection = a + ab * t
    return p.distance_to(projection)


def closest_point_on_segment(p: Vec2, a: Vec2, b: Vec2) -> Vec2:
    ab = b - a
    l_sq = ab.length_sq()
    if l_sq == 0.0:
        return a
    t = max(0.0, min(1.0, (p - a).dot(ab) / l_sq))
    return a + ab * t


def line_line_intersection(p1: Vec2, p2: Vec2, p3: Vec2, p4: Vec2) -> Optional[Vec2]:
    """Finds intersection point between two line segments (if any)."""
    d = (p2.x - p1.x) * (p4.y - p3.y) - (p2.y - p1.y) * (p4.x - p3.x)
    if abs(d) < 1e-9:
        return None  # Parallel or collinear

    u = ((p3.x - p1.x) * (p4.y - p3.y) - (p3.y - p1.y) * (p4.x - p3.x)) / d
    v = ((p3.x - p1.x) * (p2.y - p1.y) - (p3.y - p1.y) * (p2.x - p1.x)) / d

    if 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0:
        return Vec2(p1.x + u * (p2.x - p1.x), p1.y + u * (p2.y - p1.y))
    return None


def offset_segment(p1: Vec2, p2: Vec2, dist: float) -> Tuple[Vec2, Vec2]:
    """Offsets a 2D line segment perpendicularly by dist (+ for left, - for right)."""
    v = p2 - p1
    l = v.length()
    if l == 0:
        return (p1, p2)
    # Normal vector perpendicular to (p2 - p1)
    norm = Vec2(-v.y / l, v.x / l) * dist
    return (p1 + norm, p2 + norm)


def mirror_point(pt: Vec2, axis_p1: Vec2, axis_p2: Vec2) -> Vec2:
    """Mirrors a 2D point across an arbitrary axis line (axis_p1 to axis_p2)."""
    v = axis_p2 - axis_p1
    l_sq = v.length_sq()
    if l_sq == 0:
        return pt
    # Project pt onto axis line
    t = (pt - axis_p1).dot(v) / l_sq
    proj = axis_p1 + v * t
    # Reflected point
    return proj + (proj - pt)


def polygon_area(points: List[Vec2]) -> float:
    """Computes signed area of a 2D polygon using the Shoelace formula."""
    n = len(points)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i].x * points[j].y
        area -= points[j].x * points[i].y
    return abs(area) * 0.5


