"""
Document management, layer tables, spatial query indexing, and undo/redo stacks.
"""

from typing import List, Dict, Optional, Set, Any
from .geometry import Vec2, BBox
from .entities import (
    CadEntity, LineEntity, CircleEntity, ArcEntity, RectEntity,
    PolylineEntity, SplineEntity, EllipseEntity, TextEntity, DimensionEntity
)


class Layer:
    def __init__(self, name: str, color: str = "#FFFFFF", line_type: str = "CONTINUOUS",
                 line_weight: float = 0.25, visible: bool = True, locked: bool = False):
        self.name: str = name
        self.color: str = color
        self.line_type: str = line_type
        self.line_weight: float = line_weight
        self.visible: bool = visible
        self.locked: bool = locked

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "color": self.color,
            "line_type": self.line_type,
            "line_weight": self.line_weight,
            "visible": self.visible,
            "locked": self.locked,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Layer':
        return cls(
            name=data.get("name", "0"),
            color=data.get("color", "#FFFFFF"),
            line_type=data.get("line_type", "CONTINUOUS"),
            line_weight=data.get("line_weight", 0.25),
            visible=data.get("visible", True),
            locked=data.get("locked", False),
        )


class Command:
    """Base Command class for Undo/Redo."""
    def execute(self, doc: 'CadDocument'):
        raise NotImplementedError

    def undo(self, doc: 'CadDocument'):
        raise NotImplementedError


class AddEntityCommand(Command):
    def __init__(self, entity: CadEntity):
        self.entity = entity

    def execute(self, doc: 'CadDocument'):
        doc._add_entity_direct(self.entity)

    def undo(self, doc: 'CadDocument'):
        doc._remove_entity_direct(self.entity)


class DeleteEntitiesCommand(Command):
    def __init__(self, entities: List[CadEntity]):
        self.entities = list(entities)

    def execute(self, doc: 'CadDocument'):
        for e in self.entities:
            doc._remove_entity_direct(e)

    def undo(self, doc: 'CadDocument'):
        for e in self.entities:
            doc._add_entity_direct(e)


class MoveEntitiesCommand(Command):
    def __init__(self, entities: List[CadEntity], delta: Vec2):
        self.entities = list(entities)
        self.delta = delta

    def execute(self, doc: 'CadDocument'):
        for e in self.entities:
            e.move(self.delta)

    def undo(self, doc: 'CadDocument'):
        inv = -self.delta
        for e in self.entities:
            e.move(inv)


class CadDocument:
    def __init__(self):
        self.layers: Dict[str, Layer] = {}
        self.active_layer: str = "0"
        self.active_color: str = "BYLAYER"
        self.active_line_type: str = "BYLAYER"

        self.entities: List[CadEntity] = []
        self.selection: Set[CadEntity] = set()

        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []

        self._init_default_layers()

    def _init_default_layers(self):
        # Standard drafting layers
        self.add_layer(Layer("0", color="#FFFFFF", line_type="CONTINUOUS", line_weight=0.25))
        self.add_layer(Layer("WALLS", color="#00FFFF", line_type="CONTINUOUS", line_weight=0.50))
        self.add_layer(Layer("DOORS", color="#00FF00", line_type="CONTINUOUS", line_weight=0.25))
        self.add_layer(Layer("WINDOWS", color="#00AAFF", line_type="CONTINUOUS", line_weight=0.25))
        self.add_layer(Layer("DIMENSIONS", color="#FF0000", line_type="CONTINUOUS", line_weight=0.18))
        self.add_layer(Layer("TEXT", color="#FFFF00", line_type="CONTINUOUS", line_weight=0.25))
        self.add_layer(Layer("CENTERLINE", color="#FF00FF", line_type="CENTER", line_weight=0.18))
        self.add_layer(Layer("HIDDEN", color="#808080", line_type="HIDDEN", line_weight=0.18))

    def add_layer(self, layer: Layer):
        self.layers[layer.name] = layer

    def get_effective_color(self, entity: CadEntity) -> str:
        if entity.color and entity.color != "BYLAYER":
            return entity.color
        layer = self.layers.get(entity.layer)
        if layer:
            return layer.color
        return "#FFFFFF"

    def get_effective_line_weight(self, entity: CadEntity) -> float:
        layer = self.layers.get(entity.layer)
        if layer:
            return layer.line_weight
        return entity.line_width

    # Command Execution / Undo-Redo
    def execute(self, cmd: Command):
        cmd.execute(self)
        self.undo_stack.append(cmd)
        self.redo_stack.clear()

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        cmd = self.undo_stack.pop()
        cmd.undo(self)
        self.redo_stack.append(cmd)
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        cmd = self.redo_stack.pop()
        cmd.execute(self)
        self.undo_stack.append(cmd)
        return True

    # Entity Management
    def add_entity(self, entity: CadEntity, record_undo: bool = True):
        # Assign active layer if entity layer is default
        if entity.layer == "0" and self.active_layer != "0":
            entity.layer = self.active_layer
        if record_undo:
            self.execute(AddEntityCommand(entity))
        else:
            self._add_entity_direct(entity)

    def _add_entity_direct(self, entity: CadEntity):
        if entity not in self.entities:
            self.entities.append(entity)

    def _remove_entity_direct(self, entity: CadEntity):
        if entity in self.entities:
            self.entities.remove(entity)
        if entity in self.selection:
            self.selection.remove(entity)
            entity.selected = False

    def remove_entity(self, entity: CadEntity, record_undo: bool = True):
        if record_undo:
            self.execute(DeleteEntitiesCommand([entity]))
        else:
            self._remove_entity_direct(entity)

    def delete_selected(self) -> int:
        if not self.selection:
            return 0
        to_del = list(self.selection)
        self.execute(DeleteEntitiesCommand(to_del))
        self.selection.clear()
        return len(to_del)

    def clear(self):
        self.entities.clear()
        self.selection.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()

    # Selection
    def select(self, entity: CadEntity):
        entity.selected = True
        self.selection.add(entity)

    def deselect(self, entity: CadEntity):
        entity.selected = False
        if entity in self.selection:
            self.selection.remove(entity)

    def clear_selection(self):
        for e in self.selection:
            e.selected = False
        self.selection.clear()

    def select_all(self):
        for e in self.entities:
            layer = self.layers.get(e.layer)
            if layer and not layer.visible:
                continue
            e.selected = True
            self.selection.add(e)

    # Spatial Queries
    def find_at(self, pt: Vec2, tolerance: float) -> Optional[CadEntity]:
        # Top-down order (last created checked first)
        for e in reversed(self.entities):
            layer = self.layers.get(e.layer)
            if layer and not layer.visible:
                continue
            if e.hit_test(pt, tolerance):
                return e
        return None

    def find_in_box(self, box: BBox, crossing: bool = False) -> List[CadEntity]:
        result = []
        for e in self.entities:
            layer = self.layers.get(e.layer)
            if layer and not layer.visible:
                continue
            e_box = e.get_bbox()
            if crossing:
                # Green crossing box: entity touches or is inside
                if box.intersects(e_box):
                    result.append(e)
            else:
                # Blue window box: entity completely inside
                if box.contains_bbox(e_box):
                    result.append(e)
        return result

    def get_total_bbox(self) -> BBox:
        total = BBox()
        for e in self.entities:
            layer = self.layers.get(e.layer)
            if layer and not layer.visible:
                continue
            total.expand_to_bbox(e.get_bbox())
        if not total.is_valid():
            return BBox(-100, -100, 100, 100)
        return total

