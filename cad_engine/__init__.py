"""
Core geometry, entity definitions, spatial query, and file format processors.
"""
from .geometry import Vec2, Vec3, BBox, distance_point_to_segment, closest_point_on_segment, line_line_intersection
from .entities import (
    CadEntity, LineEntity, CircleEntity, ArcEntity, RectEntity,
    PolylineEntity, SplineEntity, EllipseEntity, TextEntity, DimensionEntity
)
from .document import CadDocument, Layer, Command
from .snap import SnapEngine, SnapResult
from .dxf_io import export_dxf, import_dxf, save_project, load_project
from .lisp_parser import CadCommandProcessor

