"""
Architectural floor plan drawing preset generator.
"""

from cad_engine.geometry import Vec2
from cad_engine.entities import (
    LineEntity, CircleEntity, ArcEntity, RectEntity,
    PolylineEntity, TextEntity, DimensionEntity
)
from cad_engine.document import CadDocument, Layer


def create_sample_floor_plan(doc: CadDocument):
    """Populates doc with an architectural floor plan."""
    # Ensure Layers
    doc.add_layer(Layer("WALLS", color="#00FFFF", line_weight=0.50))
    doc.add_layer(Layer("DOORS", color="#00FF00", line_weight=0.25))
    doc.add_layer(Layer("WINDOWS", color="#00AAFF", line_weight=0.25))
    doc.add_layer(Layer("DIMENSIONS", color="#FF3333", line_weight=0.18))
    doc.add_layer(Layer("TEXT", color="#FFFF00", line_weight=0.25))
    doc.add_layer(Layer("FURNITURE", color="#808080", line_weight=0.18))

    # Outer Boundary Walls (400 x 300 units)
    # Living Room + Dining: (0, 0) to (240, 180)
    # Kitchen: (240, 0) to (400, 140)
    # Master Bedroom: (0, 180) to (220, 300)
    # Bedroom 2: (220, 180) to (400, 300)
    # Bathroom: (240, 140) to (340, 180)

    # 1. Exterior Walls (Double wall 10 thickness)
    outer_poly = [Vec2(0, 0), Vec2(400, 0), Vec2(400, 300), Vec2(0, 300)]
    doc.add_entity(PolylineEntity(outer_poly, is_closed=True, layer="WALLS"), record_undo=False)

    outer_inner_poly = [Vec2(10, 10), Vec2(390, 10), Vec2(390, 290), Vec2(10, 290)]
    doc.add_entity(PolylineEntity(outer_inner_poly, is_closed=True, layer="WALLS"), record_undo=False)

    # 2. Interior Partition Walls
    # Horizontal dividing wall between living and bedrooms
    doc.add_entity(LineEntity(Vec2(10, 180), Vec2(390, 180), layer="WALLS"), record_undo=False)
    doc.add_entity(LineEntity(Vec2(10, 190), Vec2(390, 190), layer="WALLS"), record_undo=False)

    # Vertical dividing wall between master bedroom and bedroom 2
    doc.add_entity(LineEntity(Vec2(220, 190), Vec2(220, 290), layer="WALLS"), record_undo=False)

    # Vertical dividing wall between living room and kitchen/bath
    doc.add_entity(LineEntity(Vec2(240, 10), Vec2(240, 180), layer="WALLS"), record_undo=False)

    # Wall between kitchen and bathroom
    doc.add_entity(LineEntity(Vec2(240, 120), Vec2(390, 120), layer="WALLS"), record_undo=False)

    # 3. Doors with Swing Arcs
    # Main Entrance door (at living room 20, 10)
    doc.add_entity(LineEntity(Vec2(20, 10), Vec2(20, 45), layer="DOORS"), record_undo=False)
    doc.add_entity(ArcEntity(Vec2(20, 10), 35.0, 0, 90, layer="DOORS"), record_undo=False)

    # Master Bedroom door
    doc.add_entity(LineEntity(Vec2(30, 190), Vec2(65, 190), layer="DOORS"), record_undo=False)
    doc.add_entity(ArcEntity(Vec2(30, 190), 35.0, 0, 90, layer="DOORS"), record_undo=False)

    # Bedroom 2 door
    doc.add_entity(LineEntity(Vec2(230, 190), Vec2(265, 190), layer="DOORS"), record_undo=False)
    doc.add_entity(ArcEntity(Vec2(230, 190), 35.0, 0, 90, layer="DOORS"), record_undo=False)

    # Kitchen door
    doc.add_entity(LineEntity(Vec2(240, 80), Vec2(240, 110), layer="DOORS"), record_undo=False)
    doc.add_entity(ArcEntity(Vec2(240, 80), 30.0, 90, 180, layer="DOORS"), record_undo=False)

    # 4. Windows
    # Living room window (bottom)
    doc.add_entity(RectEntity(Vec2(100, 5), Vec2(180, 15), layer="WINDOWS"), record_undo=False)
    doc.add_entity(LineEntity(Vec2(100, 10), Vec2(180, 10), layer="WINDOWS"), record_undo=False)

    # Master bedroom window (top)
    doc.add_entity(RectEntity(Vec2(80, 285), Vec2(150, 295), layer="WINDOWS"), record_undo=False)
    doc.add_entity(LineEntity(Vec2(80, 290), Vec2(150, 290), layer="WINDOWS"), record_undo=False)

    # Bedroom 2 window (top)
    doc.add_entity(RectEntity(Vec2(280, 285), Vec2(350, 295), layer="WINDOWS"), record_undo=False)
    doc.add_entity(LineEntity(Vec2(280, 290), Vec2(350, 290), layer="WINDOWS"), record_undo=False)

    # Kitchen window (right)
    doc.add_entity(RectEntity(Vec2(385, 40), Vec2(395, 90), layer="WINDOWS"), record_undo=False)

    # 5. Furniture Layout
    # Living room sofa & coffee table
    doc.add_entity(RectEntity(Vec2(50, 70), Vec2(150, 100), layer="FURNITURE"), record_undo=False)
    doc.add_entity(RectEntity(Vec2(70, 110), Vec2(130, 140), layer="FURNITURE"), record_undo=False)

    # Master Bed
    doc.add_entity(RectEntity(Vec2(80, 205), Vec2(140, 270), layer="FURNITURE"), record_undo=False)
    doc.add_entity(CircleEntity(Vec2(95, 255), 8, layer="FURNITURE"), record_undo=False)
    doc.add_entity(CircleEntity(Vec2(125, 255), 8, layer="FURNITURE"), record_undo=False)

    # Bedroom 2 Bed
    doc.add_entity(RectEntity(Vec2(280, 205), Vec2(340, 270), layer="FURNITURE"), record_undo=False)

    # Dining Table with chairs
    doc.add_entity(CircleEntity(Vec2(180, 70), 22, layer="FURNITURE"), record_undo=False)
    for ang in [0, 90, 180, 270]:
        import math
        rad = math.radians(ang)
        doc.add_entity(CircleEntity(Vec2(180 + 32 * math.cos(rad), 70 + 32 * math.sin(rad)), 6, layer="FURNITURE"), record_undo=False)

    # 6. Room Labels (Text)
    doc.add_entity(TextEntity("LIVING & DINING ROOM", Vec2(60, 40), height=10.0, layer="TEXT"), record_undo=False)
    doc.add_entity(TextEntity("MASTER BEDROOM", Vec2(70, 220), height=10.0, layer="TEXT"), record_undo=False)
    doc.add_entity(TextEntity("BEDROOM 2", Vec2(270, 220), height=10.0, layer="TEXT"), record_undo=False)
    doc.add_entity(TextEntity("KITCHEN", Vec2(280, 60), height=10.0, layer="TEXT"), record_undo=False)
    doc.add_entity(TextEntity("BATH", Vec2(280, 145), height=8.0, layer="TEXT"), record_undo=False)

    # 7. Dimensions
    # Overall Width Dimension (bottom)
    doc.add_entity(DimensionEntity(Vec2(0, 0), Vec2(400, 0), offset=-30.0, text="400.00 mm", layer="DIMENSIONS"), record_undo=False)
    # Overall Height Dimension (left)
    doc.add_entity(DimensionEntity(Vec2(0, 0), Vec2(0, 300), offset=30.0, text="300.00 mm", layer="DIMENSIONS"), record_undo=False)
    # Master Bedroom Width Dimension
    doc.add_entity(DimensionEntity(Vec2(0, 300), Vec2(220, 300), offset=20.0, text="220.00 mm", layer="DIMENSIONS"), record_undo=False)
    # Bedroom 2 Width Dimension
    doc.add_entity(DimensionEntity(Vec2(220, 300), Vec2(400, 300), offset=20.0, text="180.00 mm", layer="DIMENSIONS"), record_undo=False)

