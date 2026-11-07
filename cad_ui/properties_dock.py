"""
Property inspector dock for inspecting and editing entity geometry and attributes.
"""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QScrollArea
)
from PyQt6.QtGui import QFont, QColor

from cad_engine.geometry import Vec2
from cad_engine.entities import (
    CadEntity, LineEntity, CircleEntity, ArcEntity, RectEntity,
    PolylineEntity, SplineEntity, EllipseEntity, TextEntity, DimensionEntity
)
from cad_engine.document import CadDocument


class PropertiesDock(QWidget):
    property_changed = pyqtSignal()

    def __init__(self, doc: CadDocument, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.current_entity: Optional[CadEntity] = None
        self._updating: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Title / Type Header
        self.title_label = QLabel("No Selection")
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #00e5ff; padding: 4px;")
        layout.addWidget(self.title_label)

        # Table of Properties
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.cellChanged.connect(self._on_cell_changed)

        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        self._updating = True
        self.table.setRowCount(0)

        sel_count = len(self.doc.selection)
        if sel_count == 0:
            self.title_label.setText("No Selection")
            self._add_row("Total Objects", str(len(self.doc.entities)), editable=False)
            self._add_row("Active Layer", self.doc.active_layer, editable=False)
            self._add_row("Total Layers", str(len(self.doc.layers)), editable=False)
            self.current_entity = None
            self._updating = False
            return

        if sel_count > 1:
            self.title_label.setText(f"{sel_count} Objects Selected")
            self._add_row("Selection Count", str(sel_count), editable=False)
            self.current_entity = None
            self._updating = False
            return

        # Single Entity Selected
        e = list(self.doc.selection)[0]
        self.current_entity = e
        self.title_label.setText(f"{e.entity_type}")

        # General
        self._add_row("Handle ID", e.id, editable=False)
        self._add_row("Layer", e.layer, editable=True)
        self._add_row("Color", e.color, editable=True)
        self._add_row("Line Type", e.line_type, editable=True)
        self._add_row("Line Weight", f"{e.line_width:.2f}", editable=True)

        # Specific Geometry
        if isinstance(e, LineEntity):
            self._add_row("Start X", f"{e.start.x:.2f}", editable=True)
            self._add_row("Start Y", f"{e.start.y:.2f}", editable=True)
            self._add_row("End X", f"{e.end.x:.2f}", editable=True)
            self._add_row("End Y", f"{e.end.y:.2f}", editable=True)
            self._add_row("Length", f"{e.length:.2f}", editable=False)
            self._add_row("Angle", f"{e.angle_deg:.1f}°", editable=False)

        elif isinstance(e, CircleEntity):
            self._add_row("Center X", f"{e.center.x:.2f}", editable=True)
            self._add_row("Center Y", f"{e.center.y:.2f}", editable=True)
            self._add_row("Radius", f"{e.radius:.2f}", editable=True)
            self._add_row("Diameter", f"{e.diameter:.2f}", editable=False)
            self._add_row("Circumference", f"{e.circumference:.2f}", editable=False)
            self._add_row("Area", f"{e.area:.2f}", editable=False)

        elif isinstance(e, ArcEntity):
            self._add_row("Center X", f"{e.center.x:.2f}", editable=True)
            self._add_row("Center Y", f"{e.center.y:.2f}", editable=True)
            self._add_row("Radius", f"{e.radius:.2f}", editable=True)
            self._add_row("Start Angle", f"{e.start_angle:.1f}°", editable=True)
            self._add_row("End Angle", f"{e.end_angle:.1f}°", editable=True)
            self._add_row("Arc Length", f"{e.arc_length:.2f}", editable=False)

        elif isinstance(e, RectEntity):
            self._add_row("P1 X", f"{e.p1.x:.2f}", editable=True)
            self._add_row("P1 Y", f"{e.p1.y:.2f}", editable=True)
            self._add_row("P2 X", f"{e.p2.x:.2f}", editable=True)
            self._add_row("P2 Y", f"{e.p2.y:.2f}", editable=True)
            self._add_row("Width", f"{e.width:.2f}", editable=False)
            self._add_row("Height", f"{e.height:.2f}", editable=False)
            self._add_row("Area", f"{e.area:.2f}", editable=False)

        elif isinstance(e, PolylineEntity):
            self._add_row("Vertex Count", str(len(e.points)), editable=False)
            self._add_row("Total Length", f"{e.total_length:.2f}", editable=False)
            self._add_row("Closed", str(e.is_closed), editable=True)

        elif isinstance(e, TextEntity):
            self._add_row("Text", e.text, editable=True)
            self._add_row("Pos X", f"{e.pos.x:.2f}", editable=True)
            self._add_row("Pos Y", f"{e.pos.y:.2f}", editable=True)
            self._add_row("Height", f"{e.height:.2f}", editable=True)
            self._add_row("Rotation", f"{e.rotation_deg:.1f}°", editable=True)

        elif isinstance(e, DimensionEntity):
            self._add_row("Distance", f"{e.distance:.2f}", editable=False)
            self._add_row("Custom Text", e.custom_text or "", editable=True)
            self._add_row("Offset", f"{e.offset:.2f}", editable=True)

        self._updating = False

    def _add_row(self, name: str, value: str, editable: bool = False):
        row = self.table.rowCount()
        self.table.insertRow(row)

        item_name = QTableWidgetItem(name)
        item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.table.setItem(row, 0, item_name)

        item_val = QTableWidgetItem(value)
        if not editable:
            item_val.setFlags(item_val.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_val.setForeground(QColor(160, 160, 160))
        self.table.setItem(row, 1, item_val)

    def _on_cell_changed(self, row: int, col: int):
        if self._updating or col != 1 or not self.current_entity:
            return

        prop_name = self.table.item(row, 0).text()
        new_val = self.table.item(row, 1).text()
        e = self.current_entity

        try:
            if prop_name == "Layer":
                if new_val in self.doc.layers:
                    e.layer = new_val
            elif prop_name == "Color":
                e.color = new_val
            elif prop_name == "Line Type":
                e.line_type = new_val.upper()
            elif prop_name == "Line Weight":
                e.line_width = float(new_val)

            elif isinstance(e, LineEntity):
                if prop_name == "Start X": e.start = Vec2(float(new_val), e.start.y)
                elif prop_name == "Start Y": e.start = Vec2(e.start.x, float(new_val))
                elif prop_name == "End X": e.end = Vec2(float(new_val), e.end.y)
                elif prop_name == "End Y": e.end = Vec2(e.end.x, float(new_val))

            elif isinstance(e, CircleEntity):
                if prop_name == "Center X": e.center = Vec2(float(new_val), e.center.y)
                elif prop_name == "Center Y": e.center = Vec2(e.center.x, float(new_val))
                elif prop_name == "Radius": e.radius = max(0.01, float(new_val))

            elif isinstance(e, ArcEntity):
                if prop_name == "Center X": e.center = Vec2(float(new_val), e.center.y)
                elif prop_name == "Center Y": e.center = Vec2(e.center.x, float(new_val))
                elif prop_name == "Radius": e.radius = max(0.01, float(new_val))
                elif prop_name == "Start Angle": e.start_angle = float(new_val.replace('°', ''))
                elif prop_name == "End Angle": e.end_angle = float(new_val.replace('°', ''))

            elif isinstance(e, TextEntity):
                if prop_name == "Text": e.text = new_val
                elif prop_name == "Height": e.height = max(1.0, float(new_val))
                elif prop_name == "Rotation": e.rotation_deg = float(new_val.replace('°', ''))

            self.property_changed.emit()
            self.refresh()
        except Exception:
            pass

