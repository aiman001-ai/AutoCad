"""
DXF and JSON serialization handlers for drawing documents.
"""

import json
import math
from typing import Optional
import ezdxf
from .geometry import Vec2
from .entities import (
    CadEntity, LineEntity, CircleEntity, ArcEntity, RectEntity,
    PolylineEntity, SplineEntity, EllipseEntity, TextEntity, DimensionEntity
)
from .document import CadDocument, Layer


def hex_to_rgb(hex_str: str) -> tuple:
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return (255, 255, 255)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def export_dxf(doc: CadDocument, filepath: str):
    """Exports drawing document to standard DXF format (R2010)."""
    dxf_doc = ezdxf.new('R2010')
    msp = dxf_doc.modelspace()

    # 1. Setup Layers
    for layer_name, layer in doc.layers.items():
        if layer_name in dxf_doc.layers:
            dxf_layer = dxf_doc.layers.get(layer_name)
        else:
            dxf_layer = dxf_doc.layers.add(layer_name)
        try:
            dxf_layer.rgb = hex_to_rgb(layer.color)
        except Exception:
            pass

    # 2. Export Entities
    for e in doc.entities:
        attribs = {'layer': e.layer}

        if isinstance(e, LineEntity):
            msp.add_line((e.start.x, e.start.y), (e.end.x, e.end.y), dxfattribs=attribs)

        elif isinstance(e, CircleEntity):
            msp.add_circle((e.center.x, e.center.y), e.radius, dxfattribs=attribs)

        elif isinstance(e, ArcEntity):
            msp.add_arc((e.center.x, e.center.y), e.radius, e.start_angle, e.end_angle, dxfattribs=attribs)

        elif isinstance(e, RectEntity):
            pts = [(c.x, c.y) for c in e.get_corners()]
            msp.add_lwpolyline(pts, close=True, dxfattribs=attribs)

        elif isinstance(e, PolylineEntity):
            pts = [(p.x, p.y) for p in e.points]
            msp.add_lwpolyline(pts, close=e.is_closed, dxfattribs=attribs)

        elif isinstance(e, SplineEntity):
            try:
                msp.add_spline([(p.x, p.y, 0) for p in e.control_points], dxfattribs=attribs)
            except Exception:
                # Fallback to polyline curve
                pts = [(p.x, p.y) for p in e._sampled_points]
                msp.add_lwpolyline(pts, close=False, dxfattribs=attribs)

        elif isinstance(e, EllipseEntity):
            try:
                msp.add_ellipse(
                    (e.center.x, e.center.y),
                    major_axis=(e.rx, 0, 0),
                    ratio=min(1.0, e.ry / max(0.001, e.rx)),
                    dxfattribs=attribs
                )
            except Exception:
                pass

        elif isinstance(e, TextEntity):
            msp.add_text(
                e.text,
                dxfattribs={
                    'layer': e.layer,
                    'height': e.height,
                    'insert': (e.pos.x, e.pos.y),
                    'rotation': e.rotation_deg
                }
            )

        elif isinstance(e, DimensionEntity):
            # Write linear dimension as line + text + ticks for maximum DXF compatibility
            d1, d2 = e.get_dim_line_points()
            msp.add_line((e.p1.x, e.p1.y), (d1.x, d1.y), dxfattribs=attribs)
            msp.add_line((e.p2.x, e.p2.y), (d2.x, d2.y), dxfattribs=attribs)
            msp.add_line((d1.x, d1.y), (d2.x, d2.y), dxfattribs=attribs)
            mid = (d1 + d2) * 0.5
            msp.add_text(
                e.display_text,
                dxfattribs={'layer': e.layer, 'height': 8.0, 'insert': (mid.x, mid.y + 2.0)}
            )

    dxf_doc.saveas(filepath)


def import_dxf(filepath: str) -> CadDocument:
    """Imports an existing DXF file into a CadDocument."""
    dxf_doc = ezdxf.readfile(filepath)
    msp = dxf_doc.modelspace()
    doc = CadDocument()
    doc.clear()

    # Load Layers
    for layer in dxf_doc.layers:
        color = "#FFFFFF"
        if layer.rgb:
            color = rgb_to_hex(*layer.rgb)
        doc.add_layer(Layer(layer.dxf.name, color=color))

    # Load Entities
    for e in msp:
        dxftype = e.dxftype()
        layer = e.dxf.layer if hasattr(e.dxf, 'layer') else "0"

        if dxftype == 'LINE':
            start = Vec2(e.dxf.start.x, e.dxf.start.y)
            end = Vec2(e.dxf.end.x, e.dxf.end.y)
            doc.add_entity(LineEntity(start, end, layer=layer), record_undo=False)

        elif dxftype == 'CIRCLE':
            center = Vec2(e.dxf.center.x, e.dxf.center.y)
            radius = float(e.dxf.radius)
            doc.add_entity(CircleEntity(center, radius, layer=layer), record_undo=False)

        elif dxftype == 'ARC':
            center = Vec2(e.dxf.center.x, e.dxf.center.y)
            radius = float(e.dxf.radius)
            start_ang = float(e.dxf.start_angle)
            end_ang = float(e.dxf.end_angle)
            doc.add_entity(ArcEntity(center, radius, start_ang, end_ang, layer=layer), record_undo=False)

        elif dxftype == 'LWPOLYLINE':
            pts = [Vec2(p[0], p[1]) for p in e.get_points()]
            if pts:
                is_closed = bool(e.closed)
                doc.add_entity(PolylineEntity(pts, is_closed=is_closed, layer=layer), record_undo=False)

        elif dxftype == 'POLYLINE':
            pts = [Vec2(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
            if pts:
                is_closed = bool(e.is_closed)
                doc.add_entity(PolylineEntity(pts, is_closed=is_closed, layer=layer), record_undo=False)

        elif dxftype == 'SPLINE':
            pts = [Vec2(p[0], p[1]) for p in e.control_points]
            if pts:
                doc.add_entity(SplineEntity(pts, layer=layer), record_undo=False)

        elif dxftype == 'ELLIPSE':
            center = Vec2(e.dxf.center.x, e.dxf.center.y)
            rx = math.hypot(e.dxf.major_axis.x, e.dxf.major_axis.y)
            ry = rx * float(e.dxf.ratio)
            ang = math.degrees(math.atan2(e.dxf.major_axis.y, e.dxf.major_axis.x))
            doc.add_entity(EllipseEntity(center, rx, ry, rotation_deg=ang, layer=layer), record_undo=False)

        elif dxftype in ('TEXT', 'MTEXT'):
            text = e.text if hasattr(e, 'text') else e.dxf.text if hasattr(e.dxf, 'text') else ""
            pos = Vec2(e.dxf.insert.x, e.dxf.insert.y)
            h = float(e.dxf.height) if hasattr(e.dxf, 'height') else 12.0
            rot = float(e.dxf.rotation) if hasattr(e.dxf, 'rotation') else 0.0
            doc.add_entity(TextEntity(text, pos, height=h, rotation_deg=rot, layer=layer), record_undo=False)

    return doc


def save_project(doc: CadDocument, filepath: str):
    """Saves document as native JSON format."""
    data = {
        "version": "1.0",
        "active_layer": doc.active_layer,
        "layers": [layer.to_dict() for layer in doc.layers.values()],
        "entities": [e.to_dict() for e in doc.entities]
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def load_project(filepath: str) -> CadDocument:
    """Loads document from native JSON format."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    doc = CadDocument()
    doc.clear()

    for l_data in data.get("layers", []):
        doc.add_layer(Layer.from_dict(l_data))

    doc.active_layer = data.get("active_layer", "0")

    for ed in data.get("entities", []):
        t = ed.get("type")
        kw = {
            "layer": ed.get("layer", "0"),
            "color": ed.get("color", "BYLAYER"),
            "line_width": ed.get("line_width", 1.0),
            "line_type": ed.get("line_type", "CONTINUOUS")
        }
        if t == "LINE":
            p1 = Vec2(*ed["start"])
            p2 = Vec2(*ed["end"])
            doc.add_entity(LineEntity(p1, p2, **kw), record_undo=False)
        elif t == "CIRCLE":
            c = Vec2(*ed["center"])
            doc.add_entity(CircleEntity(c, ed["radius"], **kw), record_undo=False)
        elif t == "ARC":
            c = Vec2(*ed["center"])
            doc.add_entity(ArcEntity(c, ed["radius"], ed["start_angle"], ed["end_angle"], **kw), record_undo=False)
        elif t == "RECT":
            p1 = Vec2(*ed["p1"])
            p2 = Vec2(*ed["p2"])
            doc.add_entity(RectEntity(p1, p2, **kw), record_undo=False)
        elif t == "POLYLINE":
            pts = [Vec2(*p) for p in ed["points"]]
            doc.add_entity(PolylineEntity(pts, is_closed=ed.get("is_closed", False), **kw), record_undo=False)
        elif t == "SPLINE":
            pts = [Vec2(*p) for p in ed["control_points"]]
            doc.add_entity(SplineEntity(pts, **kw), record_undo=False)
        elif t == "ELLIPSE":
            c = Vec2(*ed["center"])
            doc.add_entity(EllipseEntity(c, ed["rx"], ed["ry"], ed.get("rotation_deg", 0.0), **kw), record_undo=False)
        elif t == "TEXT":
            pos = Vec2(*ed["pos"])
            doc.add_entity(TextEntity(ed["text"], pos, ed.get("height", 12.0), ed.get("rotation_deg", 0.0), **kw), record_undo=False)
        elif t == "DIMENSION":
            p1 = Vec2(*ed["p1"])
            p2 = Vec2(*ed["p2"])
            doc.add_entity(DimensionEntity(p1, p2, ed.get("offset", 20.0), ed.get("text"), **kw), record_undo=False)

    return doc

