"""
Mechanical component and spur gear drawing preset generator.
"""

import math
from cad_engine.geometry import Vec2
from cad_engine.entities import (
    LineEntity, CircleEntity, ArcEntity, RectEntity,
    PolylineEntity, TextEntity, DimensionEntity
)
from cad_engine.document import CadDocument, Layer


def create_sample_mechanical_part(doc: CadDocument):
    """Populates doc with an engineering spur gear and mounting flange."""
    # Ensure Layers
    doc.add_layer(Layer("0", color="#FFFFFF", line_weight=0.35))
    doc.add_layer(Layer("GEAR_TEETH", color="#00FFFF", line_weight=0.50))
    doc.add_layer(Layer("HUB", color="#FFFF00", line_weight=0.35))
    doc.add_layer(Layer("HOLES", color="#00FF00", line_weight=0.35))
    doc.add_layer(Layer("CENTERLINE", color="#FF00FF", line_type="CENTER", line_weight=0.18))
    doc.add_layer(Layer("DIMENSIONS", color="#FF3333", line_weight=0.18))
    doc.add_layer(Layer("TEXT", color="#FFFFFF", line_weight=0.25))

    center = Vec2(0.0, 0.0)

    # 1. Centerlines
    doc.add_entity(LineEntity(Vec2(-160, 0), Vec2(160, 0), layer="CENTERLINE"), record_undo=False)
    doc.add_entity(LineEntity(Vec2(0, -160), Vec2(0, 160), layer="CENTERLINE"), record_undo=False)

    # 2. Shaft Bore & Keyway (Radius 20, Keyway 8x5)
    doc.add_entity(CircleEntity(center, 20.0, layer="HUB"), record_undo=False)
    # Keyway notch at top (x: -4 to 4, y: 18 to 26)
    doc.add_entity(RectEntity(Vec2(-4, 18), Vec2(4, 25), layer="HUB"), record_undo=False)

    # 3. Inner Hub Ring
    doc.add_entity(CircleEntity(center, 40.0, layer="HUB"), record_undo=False)

    # 4. Bolt Hole Circle (PCD = 140, Radius = 70, 6 bolt holes of dia 12)
    pcd_radius = 70.0
    doc.add_entity(CircleEntity(center, pcd_radius, layer="CENTERLINE", line_type="CENTER"), record_undo=False)

    for i in range(6):
        ang_deg = i * 60.0
        rad = math.radians(ang_deg)
        hole_c = Vec2(center.x + pcd_radius * math.cos(rad), center.y + pcd_radius * math.sin(rad))
        doc.add_entity(CircleEntity(hole_c, 6.0, layer="HOLES"), record_undo=False)
        # Small center marks for each hole
        doc.add_entity(LineEntity(hole_c - Vec2(10, 0), hole_c + Vec2(10, 0), layer="CENTERLINE"), record_undo=False)
        doc.add_entity(LineEntity(hole_c - Vec2(0, 10), hole_c + Vec2(0, 10), layer="CENTERLINE"), record_undo=False)

    # 5. Spur Gear Teeth
    # Root radius = 105, Pitch radius = 115, Tip radius = 125, 20 teeth
    num_teeth = 20
    r_root = 105.0
    r_tip = 125.0

    teeth_points = []
    for i in range(num_teeth):
        base_ang = (i / num_teeth) * 2.0 * math.pi
        pitch_step = (2.0 * math.pi) / num_teeth

        a0 = base_ang
        a1 = base_ang + pitch_step * 0.25
        a2 = base_ang + pitch_step * 0.50
        a3 = base_ang + pitch_step * 0.75

        # Root point 1
        teeth_points.append(Vec2(center.x + r_root * math.cos(a0), center.y + r_root * math.sin(a0)))
        # Tip point 1
        teeth_points.append(Vec2(center.x + r_tip * math.cos(a1), center.y + r_tip * math.sin(a1)))
        # Tip point 2
        teeth_points.append(Vec2(center.x + r_tip * math.cos(a2), center.y + r_tip * math.sin(a2)))
        # Root point 2
        teeth_points.append(Vec2(center.x + r_root * math.cos(a3), center.y + r_root * math.sin(a3)))

    doc.add_entity(PolylineEntity(teeth_points, is_closed=True, layer="GEAR_TEETH"), record_undo=False)

    # Pitch Circle
    doc.add_entity(CircleEntity(center, 115.0, layer="CENTERLINE", line_type="CENTER"), record_undo=False)

    # 6. Dimensions
    # Shaft Diameter
    doc.add_entity(DimensionEntity(Vec2(-20, 0), Vec2(20, 0), offset=-25.0, text="Ø 40.0 H7", layer="DIMENSIONS"), record_undo=False)
    # Bolt PCD
    doc.add_entity(DimensionEntity(Vec2(-70, 0), Vec2(70, 0), offset=-50.0, text="PCD Ø 140.0", layer="DIMENSIONS"), record_undo=False)
    # Outside Gear Tip Diameter
    doc.add_entity(DimensionEntity(Vec2(-125, 0), Vec2(125, 0), offset=145.0, text="Tip Ø 250.0 mm", layer="DIMENSIONS"), record_undo=False)

    # 7. Title Block Text
    doc.add_entity(TextEntity("SPUR GEAR 20-TEETH MODULE 6", Vec2(-100, -180), height=11.0, layer="TEXT"), record_undo=False)
    doc.add_entity(TextEntity("MATERIAL: 4140 ALLOY STEEL (HEAT TREATED)", Vec2(-115, -200), height=9.0, layer="TEXT"), record_undo=False)
    doc.add_entity(TextEntity("6X Ø12 MOUNTING HOLES EQ. SPACED ON Ø140 PCD", Vec2(-130, -218), height=8.0, layer="TEXT"), record_undo=False)

