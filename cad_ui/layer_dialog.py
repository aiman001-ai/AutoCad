"""
Layer properties manager dialog: visibility, color, line type, and lock state.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QColorDialog, QMessageBox, QComboBox
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap

from cad_engine.document import CadDocument, Layer


class LayerManagerDialog(QDialog):
    layers_updated = pyqtSignal()

    def __init__(self, doc: CadDocument, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.setWindowTitle("Layer Properties Manager")
        self.resize(650, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Buttons Bar
        btn_bar = QHBoxLayout()
        self.btn_new = QPushButton("New Layer")
        self.btn_delete = QPushButton("Delete Layer")
        self.btn_set_current = QPushButton("Set Current")

        btn_bar.addWidget(self.btn_new)
        btn_bar.addWidget(self.btn_delete)
        btn_bar.addWidget(self.btn_set_current)
        btn_bar.addStretch()

        self.btn_new.clicked.connect(self._create_layer)
        self.btn_delete.clicked.connect(self._delete_layer)
        self.btn_set_current.clicked.connect(self._set_current_layer)

        layout.addLayout(btn_bar)

        # Layer Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Status", "Name", "Visible", "Color", "Line Type", "Line Weight"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        layout.addWidget(self.table)

        # Bottom Close button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(0)
        for layer_name, layer in self.doc.layers.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Status (Current active layer checkmark)
            is_active = (layer_name == self.doc.active_layer)
            item_status = QTableWidgetItem("✓ Current" if is_active else "")
            item_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            if is_active:
                item_status.setForeground(QColor(0, 220, 255))
            item_status.setFlags(item_status.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, item_status)

            # Name
            item_name = QTableWidgetItem(layer_name)
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, item_name)

            # Visible
            item_vis = QTableWidgetItem("👁 Yes" if layer.visible else "🚫 Off")
            item_vis.setFlags(item_vis.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item_vis)

            # Color (Swatch)
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(layer.color))
            item_color = QTableWidgetItem(layer.color)
            item_color.setIcon(QIcon(pixmap))
            item_color.setFlags(item_color.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, item_color)

            # Line Type
            item_ltype = QTableWidgetItem(layer.line_type)
            item_ltype.setFlags(item_ltype.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, item_ltype)

            # Line Weight
            item_lwt = QTableWidgetItem(f"{layer.line_weight:.2f} mm")
            item_lwt.setFlags(item_lwt.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 5, item_lwt)

    def _create_layer(self):
        idx = 1
        new_name = f"Layer_{idx}"
        while new_name in self.doc.layers:
            idx += 1
            new_name = f"Layer_{idx}"

        self.doc.add_layer(Layer(new_name, color="#00AAFF"))
        self.refresh_table()
        self.layers_updated.emit()

    def _delete_layer(self):
        row = self.table.currentRow()
        if row < 0:
            return
        layer_name = self.table.item(row, 1).text()
        if layer_name == "0":
            QMessageBox.warning(self, "Invalid Operation", "The default layer '0' cannot be deleted.")
            return
        if layer_name == self.doc.active_layer:
            QMessageBox.warning(self, "Invalid Operation", "Cannot delete the currently active layer.")
            return

        del self.doc.layers[layer_name]
        self.refresh_table()
        self.layers_updated.emit()

    def _set_current_layer(self):
        row = self.table.currentRow()
        if row < 0:
            return
        layer_name = self.table.item(row, 1).text()
        self.doc.active_layer = layer_name
        self.refresh_table()
        self.layers_updated.emit()

    def _on_cell_double_clicked(self, row: int, col: int):
        layer_name = self.table.item(row, 1).text()
        layer = self.doc.layers.get(layer_name)
        if not layer:
            return

        # Double click visibility column to toggle
        if col == 2:
            layer.visible = not layer.visible
            self.refresh_table()
            self.layers_updated.emit()

        # Double click color column to choose color
        elif col == 3:
            c = QColorDialog.getColor(QColor(layer.color), self, f"Select Color for {layer_name}")
            if c.isValid():
                layer.color = c.name().upper()
                self.refresh_table()
                self.layers_updated.emit()

