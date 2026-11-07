"""
Main application window: drafting ribbon, viewport, inspector, and file operations.
"""

import os
import sys
from typing import Optional, List, Dict
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar,
    QMenuBar, QMenu, QStatusBar, QDockWidget, QFileDialog,
    QMessageBox, QLabel, QPushButton, QComboBox, QColorDialog
)
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPixmap, QColor, QPainter, QPdfWriter, QPageSize

from cad_engine.geometry import Vec2
from cad_engine.entities import (
    LineEntity, CircleEntity, ArcEntity, RectEntity,
    PolylineEntity, SplineEntity, TextEntity, DimensionEntity
)
from cad_engine.document import CadDocument, Layer
from cad_engine.dxf_io import export_dxf, import_dxf, save_project, load_project
from cad_engine.lisp_parser import CadCommandProcessor

from .viewport import CadViewport
from .command_line import CadCommandLine
from .properties_dock import PropertiesDock
from .layer_dialog import LayerManagerDialog
from .styles import DARK_THEME_QSS


class CadMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoCAD 2026 Engine - [Drawing1.dwg]")
        self.resize(1280, 800)

        # Set Window & Taskbar Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons", "autocad.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Apply dark theme
        self.setStyleSheet(DARK_THEME_QSS)

        # CAD Core Document
        self.doc = CadDocument()

        # Viewport
        self.viewport = CadViewport(self.doc, self)
        self.setCentralWidget(self.viewport)

        # Bottom Command Line Console
        self._init_command_line()

        # Command Processor (CLI & AutoLISP & Python)
        self.cmd_processor = CadCommandProcessor(self.doc, {
            "log": self.cmd_line.log,
            "set_tool": self.viewport.set_tool,
            "redraw": self.viewport.update,
            "zoom_extents": self.viewport.zoom_extents,
            "open_layers": self.open_layer_manager,
        })
        self.cmd_line.command_submitted.connect(self._on_command_submitted)
        self.cmd_line.cancel_requested.connect(self._on_cancel_requested)

        # Right Dock: Properties Inspector
        self._init_properties_dock()

        # Menus & Toolbars
        self._init_menus()
        self._init_toolbars()

        # Status Bar
        self._init_status_bar()

        # Connect Viewport signals
        self.viewport.coordinates_changed.connect(self._on_coords_changed)
        self.viewport.selection_changed.connect(self._on_selection_changed)
        self.viewport.status_message.connect(self._on_status_message)

    def _init_command_line(self):
        self.cmd_dock = QDockWidget("Command Line", self)
        self.cmd_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)
        self.cmd_line = CadCommandLine(self)
        self.cmd_dock.setWidget(self.cmd_line)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.cmd_dock)

    def _init_properties_dock(self):
        self.prop_dock = QDockWidget("Properties", self)
        self.prop_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.prop_widget = PropertiesDock(self.doc, self)
        self.prop_widget.property_changed.connect(self.viewport.update)
        self.prop_dock.setWidget(self.prop_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.prop_dock)

    def _init_menus(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")
        self._add_action(file_menu, "New Drawing", "Ctrl+N", self.action_new)
        self._add_action(file_menu, "Open DXF / CAD...", "Ctrl+O", self.action_open)
        self._add_action(file_menu, "Save Project (.cad)", "Ctrl+S", self.action_save)
        self._add_action(file_menu, "Export DXF Drawing...", "Ctrl+Shift+S", self.action_export_dxf)
        file_menu.addSeparator()
        self._add_action(file_menu, "Export High-Res PNG Image...", None, self.action_export_png)
        self._add_action(file_menu, "Export Vector PDF Document...", None, self.action_export_pdf)
        file_menu.addSeparator()
        self._add_action(file_menu, "Exit", "Alt+F4", self.close)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        self._add_action(edit_menu, "Undo", "Ctrl+Z", self.action_undo)
        self._add_action(edit_menu, "Redo", "Ctrl+Y", self.action_redo)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Select All", "Ctrl+A", self.action_select_all)
        self._add_action(edit_menu, "Erase Selected", "Del", self.action_erase)
        self._add_action(edit_menu, "Clear Entire Drawing", None, self.action_clear_all)

        # View Menu
        view_menu = menubar.addMenu("&View")
        self._add_action(view_menu, "Zoom Extents", "Z, E", self.viewport.zoom_extents)
        self._add_action(view_menu, "Zoom In", "Ctrl+=", self.viewport.zoom_in)
        self._add_action(view_menu, "Zoom Out", "Ctrl+-", self.viewport.zoom_out)
        view_menu.addSeparator()
        act_grid = self._add_action(view_menu, "Toggle Grid", "F7", self.action_toggle_grid)
        act_grid.setCheckable(True)
        act_grid.setChecked(True)
        self.act_grid = act_grid

        act_iso = self._add_action(view_menu, "3D Isometric View", "F12", self.action_toggle_3d)
        act_iso.setCheckable(True)
        self.act_iso = act_iso

        # Draw Menu
        draw_menu = menubar.addMenu("&Draw")
        self._add_action(draw_menu, "Line (L)", "L", lambda: self.viewport.set_tool("LINE"))
        self._add_action(draw_menu, "Polyline (PL)", "P,L", lambda: self.viewport.set_tool("POLYLINE"))
        self._add_action(draw_menu, "Circle (C)", "C", lambda: self.viewport.set_tool("CIRCLE"))
        self._add_action(draw_menu, "Arc (A)", "A", lambda: self.viewport.set_tool("ARC"))
        self._add_action(draw_menu, "Rectangle (REC)", "R,E,C", lambda: self.viewport.set_tool("RECT"))
        self._add_action(draw_menu, "Spline (SPL)", None, lambda: self.viewport.set_tool("SPLINE"))
        self._add_action(draw_menu, "Text (T)", "T", lambda: self.viewport.set_tool("TEXT"))
        self._add_action(draw_menu, "Dimension (DIM)", "D", lambda: self.viewport.set_tool("DIMENSION"))

        # Modify Menu
        mod_menu = menubar.addMenu("&Modify")
        self._add_action(mod_menu, "Erase (E)", "E", self.action_erase)
        self._add_action(mod_menu, "Move Selected...", "M", self.action_move)
        self._add_action(mod_menu, "Copy Selected...", "C,O", self.action_copy)
        self._add_action(mod_menu, "Rotate Selected 90°", "R,O", self.action_rotate_90)
        self._add_action(mod_menu, "Scale Selected 2X", "S,C", self.action_scale_2x)

        # Tools Menu
        tools_menu = menubar.addMenu("&Tools")
        self._add_action(tools_menu, "Layer Properties Manager...", "L,A", self.open_layer_manager)
        tools_menu.addSeparator()
        self._add_action(tools_menu, "Run AutoLISP Example", None, self.action_run_lisp_demo)
        self._add_action(tools_menu, "Run Python Script Demo", None, self.action_run_python_demo)

        # Samples Menu (1-Click Presets)
        samples_menu = menubar.addMenu("&Samples")
        self._add_action(samples_menu, "Load Architectural Floor Plan", None, self.load_sample_floor_plan)
        self._add_action(samples_menu, "Load Mechanical Spur Gear", None, self.load_sample_mechanical)

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        self._add_action(help_menu, "Command & Shortcut Reference", "F1", self.action_help_commands)
        self._add_action(help_menu, "System Architecture & Specs", None, self.action_about_tech)

    def _init_toolbars(self):
        # 1. Main Ribbon Toolbar
        ribbon = QToolBar("Drafting Ribbon", self)
        ribbon.setIconSize(QSize(20, 20))
        ribbon.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, ribbon)

        # Draw Tools Group
        lbl_draw = QLabel(" <b>DRAW:</b> ")
        lbl_draw.setStyleSheet("color: #00e5ff;")
        ribbon.addWidget(lbl_draw)

        self._add_toolbar_btn(ribbon, "Line", lambda: self.viewport.set_tool("LINE"), "Draw straight line segment (L)")
        self._add_toolbar_btn(ribbon, "Polyline", lambda: self.viewport.set_tool("POLYLINE"), "Draw continuous polyline (PL)")
        self._add_toolbar_btn(ribbon, "Circle", lambda: self.viewport.set_tool("CIRCLE"), "Draw circle with center & radius (C)")
        self._add_toolbar_btn(ribbon, "Arc", lambda: self.viewport.set_tool("ARC"), "Draw 3-point circular arc (A)")
        self._add_toolbar_btn(ribbon, "Rectangle", lambda: self.viewport.set_tool("RECT"), "Draw rectangle (REC)")
        self._add_toolbar_btn(ribbon, "Spline", lambda: self.viewport.set_tool("SPLINE"), "Draw smooth curve through points (SPL)")
        self._add_toolbar_btn(ribbon, "Text", lambda: self.viewport.set_tool("TEXT"), "Insert single-line text (T)")
        self._add_toolbar_btn(ribbon, "Dimension", lambda: self.viewport.set_tool("DIMENSION"), "Add aligned linear dimension (DIM)")

        ribbon.addSeparator()

        # Modify Tools Group
        lbl_mod = QLabel(" <b>MODIFY:</b> ")
        lbl_mod.setStyleSheet("color: #ff9d00;")
        ribbon.addWidget(lbl_mod)

        self._add_toolbar_btn(ribbon, "Select", lambda: self.viewport.set_tool("SELECT"), "Object pick & selection tool")
        self._add_toolbar_btn(ribbon, "Erase", self.action_erase, "Delete selected entities (E)")
        self._add_toolbar_btn(ribbon, "Undo", self.action_undo, "Undo last operation (Ctrl+Z)")
        self._add_toolbar_btn(ribbon, "Redo", self.action_redo, "Redo operation (Ctrl+Y)")

        ribbon.addSeparator()

        # Layer Quick Dropdown
        lbl_layer = QLabel(" <b>LAYER:</b> ")
        lbl_layer.setStyleSheet("color: #a0a0a0;")
        ribbon.addWidget(lbl_layer)

        self.layer_combo = QComboBox()
        self.layer_combo.setMinimumWidth(120)
        self._refresh_layer_combo()
        self.layer_combo.currentTextChanged.connect(self._on_layer_combo_changed)
        ribbon.addWidget(self.layer_combo)

        btn_layer_mgr = QPushButton("Layers...")
        btn_layer_mgr.clicked.connect(self.open_layer_manager)
        ribbon.addWidget(btn_layer_mgr)

        ribbon.addSeparator()

        # Navigation & Samples Group
        self._add_toolbar_btn(ribbon, "Extents", self.viewport.zoom_extents, "Zoom to drawing extents (Z E)")
        self._add_toolbar_btn(ribbon, "3D View", self.action_toggle_3d, "Toggle 3D Axonometric Isometric View")

        # Preset Samples
        btn_plan = QPushButton("Floor Plan")
        btn_plan.setStyleSheet("background-color: #0e639c; color: white; font-weight: bold;")
        btn_plan.clicked.connect(self.load_sample_floor_plan)
        ribbon.addWidget(btn_plan)

        btn_gear = QPushButton("Mechanical Gear")
        btn_gear.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
        btn_gear.clicked.connect(self.load_sample_mechanical)
        ribbon.addWidget(btn_gear)

    def _refresh_layer_combo(self):
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for name, layer in self.doc.layers.items():
            pix = QPixmap(12, 12)
            pix.fill(QColor(layer.color))
            self.layer_combo.addItem(QIcon(pix), name)
        self.layer_combo.setCurrentText(self.doc.active_layer)
        self.layer_combo.blockSignals(False)

    def _on_layer_combo_changed(self, text: str):
        if text in self.doc.layers:
            self.doc.active_layer = text
            self.cmd_line.log(f"Active layer switched to '{text}'")

    def _init_status_bar(self):
        sb = self.statusBar()

        # Coordinates label
        self.coord_label = QLabel("X: 0.00   Y: 0.00")
        self.coord_label.setMinimumWidth(160)
        self.coord_label.setStyleSheet("color: #ffffff; font-family: Consolas; font-weight: bold;")
        sb.addWidget(self.coord_label)

        # Status mode buttons
        self.btn_snap = self._create_status_btn("SNAP", "Grid Snap (F9)", self.viewport.snap_engine.grid_snap_enabled, self._toggle_snap)
        self.btn_grid = self._create_status_btn("GRID", "Display Grid (F7)", self.viewport.grid_visible, self._toggle_grid)
        self.btn_ortho = self._create_status_btn("ORTHO", "Ortho Mode (F8)", self.viewport.ortho_enabled, self._toggle_ortho)
        self.btn_polar = self._create_status_btn("POLAR", "Polar Tracking (F10)", self.viewport.polar_enabled, self._toggle_polar)
        self.btn_osnap = self._create_status_btn("OSNAP", "Object Snap (F3)", self.viewport.snap_engine.osnap_enabled, self._toggle_osnap)
        self.btn_lwt = self._create_status_btn("LWT", "Show Line Weights", self.viewport.show_line_weights, self._toggle_lwt)
        self.btn_3d = self._create_status_btn("3D ISO", "3D Isometric Projection", self.viewport.is_3d_isometric, self.action_toggle_3d)

        sb.addPermanentWidget(self.btn_snap)
        sb.addPermanentWidget(self.btn_grid)
        sb.addPermanentWidget(self.btn_ortho)
        sb.addPermanentWidget(self.btn_polar)
        sb.addPermanentWidget(self.btn_osnap)
        sb.addPermanentWidget(self.btn_lwt)
        sb.addPermanentWidget(self.btn_3d)

    def _create_status_btn(self, text: str, tooltip: str, checked: bool, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setToolTip(tooltip)
        btn.clicked.connect(callback)
        return btn

    def _toggle_snap(self, val: bool):
        self.viewport.snap_engine.grid_snap_enabled = val
        self.cmd_line.log(f"SNAP {'<On>' if val else '<Off>'}")
        self.viewport.update()

    def _toggle_grid(self, val: bool):
        self.viewport.grid_visible = val
        self.act_grid.setChecked(val)
        self.cmd_line.log(f"GRID {'<On>' if val else '<Off>'}")
        self.viewport.update()

    def _toggle_ortho(self, val: bool):
        self.viewport.ortho_enabled = val
        self.cmd_line.log(f"ORTHOMODE {'<On>' if val else '<Off>'}")
        self.viewport.update()

    def _toggle_polar(self, val: bool):
        self.viewport.polar_enabled = val
        self.cmd_line.log(f"POLAR {'<On>' if val else '<Off>'}")
        self.viewport.update()

    def _toggle_osnap(self, val: bool):
        self.viewport.snap_engine.osnap_enabled = val
        self.cmd_line.log(f"OSNAP {'<On>' if val else '<Off>'}")
        self.viewport.update()

    def _toggle_lwt(self, val: bool):
        self.viewport.show_line_weights = val
        self.viewport.update()

    def _add_action(self, menu: QMenu, title: str, shortcut: Optional[str], slot) -> QAction:
        act = QAction(title, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    def _add_toolbar_btn(self, toolbar: QToolBar, title: str, slot, tooltip: str = ""):
        btn = QPushButton(title)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.clicked.connect(slot)
        toolbar.addWidget(btn)

    # Event Handlers & Slots
    def _on_coords_changed(self, x: float, y: float):
        self.coord_label.setText(f"X: {x:8.2f}   Y: {y:8.2f}")

    def _on_selection_changed(self):
        self.prop_widget.refresh()

    def _on_status_message(self, msg: str):
        self.statusBar().showMessage(msg, 3000)

    def _on_command_submitted(self, cmd_text: str):
        response = self.cmd_processor.execute_command_string(cmd_text)
        if response:
            self.cmd_line.log(response)
        self.prop_widget.refresh()
        self.viewport.update()

    def _on_cancel_requested(self):
        self.cmd_processor.cancel_active_command()
        self.viewport.cancel_tool()

    def open_layer_manager(self):
        dlg = LayerManagerDialog(self.doc, self)
        dlg.layers_updated.connect(self._on_layers_updated)
        dlg.exec()

    def _on_layers_updated(self):
        self._refresh_layer_combo()
        self.prop_widget.refresh()
        self.viewport.update()

    # File Operations
    def action_new(self):
        if QMessageBox.question(self, "New Drawing", "Clear current drawing and start a new one?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.doc.clear()
            self.prop_widget.refresh()
            self.viewport.zoom_extents()
            self.cmd_line.log("New drawing created.")

    def action_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Drawing File", "", "AutoCAD DXF / CAD Files (*.dxf *.cad);;AutoCAD DXF (*.dxf);;CAD JSON (*.cad)"
        )
        if not path:
            return
        try:
            if path.lower().endswith(".dxf"):
                new_doc = import_dxf(path)
                self.doc.layers = new_doc.layers
                self.doc.entities = new_doc.entities
                self.doc.active_layer = new_doc.active_layer
            else:
                new_doc = load_project(path)
                self.doc.layers = new_doc.layers
                self.doc.entities = new_doc.entities
                self.doc.active_layer = new_doc.active_layer

            self._refresh_layer_combo()
            self.prop_widget.refresh()
            self.viewport.zoom_extents()
            self.cmd_line.log(f"Drawing loaded successfully from: {os.path.basename(path)} ({len(self.doc.entities)} entities)")
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Failed to load file: {e}")

    def action_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save CAD Project", "Drawing1.cad", "CAD Project (*.cad)")
        if not path:
            return
        try:
            save_project(self.doc, path)
            self.cmd_line.log(f"Project saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save project: {e}")

    def action_export_dxf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export DXF Drawing", "Drawing1.dxf", "DXF Drawing (*.dxf)")
        if not path:
            return
        try:
            export_dxf(self.doc, path)
            self.cmd_line.log(f"DXF drawing exported: {path}")
            QMessageBox.information(self, "DXF Export", f"Successfully exported to DXF format.\n\nFile: {path}")
        except Exception as e:
            QMessageBox.critical(self, "DXF Export Error", f"Failed to export DXF: {e}")

    def action_export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG Image", "drawing.png", "PNG Image (*.png)")
        if not path:
            return
        try:
            pixmap = QPixmap(self.viewport.size() * 2)  # 2x supersampled high resolution
            pixmap.setDevicePixelRatio(2.0)
            self.viewport.render(pixmap)
            pixmap.save(path, "PNG")
            self.cmd_line.log(f"High-res PNG image exported: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Image Error", f"Failed to export PNG: {e}")

    def action_export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Vector PDF", "drawing.pdf", "PDF Document (*.pdf)")
        if not path:
            return
        try:
            writer = QPdfWriter(path)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setResolution(300)
            painter = QPainter(writer)
            self.viewport.render(painter)
            painter.end()
            self.cmd_line.log(f"Vector PDF exported: {path}")
            QMessageBox.information(self, "PDF Export", f"Drawing exported as vector PDF document:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "PDF Export Error", f"Failed to export PDF: {e}")

    # Edit Actions
    def action_undo(self):
        if self.doc.undo():
            self.prop_widget.refresh()
            self.viewport.update()
            self.cmd_line.log("Undo complete.")

    def action_redo(self):
        if self.doc.redo():
            self.prop_widget.refresh()
            self.viewport.update()
            self.cmd_line.log("Redo complete.")

    def action_select_all(self):
        self.doc.select_all()
        self.prop_widget.refresh()
        self.viewport.update()

    def action_erase(self):
        count = self.doc.delete_selected()
        self.prop_widget.refresh()
        self.viewport.update()
        self.cmd_line.log(f"{count} entity(ies) deleted.")

    def action_clear_all(self):
        self.doc.clear()
        self.prop_widget.refresh()
        self.viewport.update()
        self.cmd_line.log("Drawing cleared.")

    def action_move(self):
        if not self.doc.selection:
            QMessageBox.information(self, "Move", "Please select objects to move first.")
            return
        for e in self.doc.selection:
            e.move(Vec2(20.0, 20.0))
        self.viewport.update()
        self.cmd_line.log("Selected entities moved by (20, 20).")

    def action_copy(self):
        if not self.doc.selection:
            QMessageBox.information(self, "Copy", "Please select objects to copy first.")
            return
        new_ents = []
        for e in list(self.doc.selection):
            c = e.clone()
            c.move(Vec2(20.0, 20.0))
            self.doc.add_entity(c)
            new_ents.append(c)
        self.doc.clear_selection()
        for e in new_ents:
            self.doc.select(e)
        self.prop_widget.refresh()
        self.viewport.update()
        self.cmd_line.log(f"Copied {len(new_ents)} object(s).")

    def action_rotate_90(self):
        if not self.doc.selection:
            return
        bbox = self.doc.get_total_bbox()
        center = bbox.center
        for e in self.doc.selection:
            e.rotate(math.radians(90.0), center)
        self.viewport.update()
        self.cmd_line.log("Selected entities rotated 90 degrees.")

    def action_scale_2x(self):
        if not self.doc.selection:
            return
        bbox = self.doc.get_total_bbox()
        center = bbox.center
        for e in self.doc.selection:
            e.scale(1.5, center)
        self.viewport.update()
        self.cmd_line.log("Selected entities scaled by 1.5x.")

    def action_toggle_grid(self):
        self.viewport.grid_visible = not self.viewport.grid_visible
        self.btn_grid.setChecked(self.viewport.grid_visible)
        self.act_grid.setChecked(self.viewport.grid_visible)
        self.viewport.update()

    def action_toggle_3d(self):
        self.viewport.is_3d_isometric = not self.viewport.is_3d_isometric
        self.btn_3d.setChecked(self.viewport.is_3d_isometric)
        self.act_iso.setChecked(self.viewport.is_3d_isometric)
        mode_str = "3D Isometric View" if self.viewport.is_3d_isometric else "2D Plan View"
        self.cmd_line.log(f"Switched to {mode_str}.")
        self.viewport.update()

    # Script Demos
    def action_run_lisp_demo(self):
        self.cmd_processor.execute_command_string("(rect 0 0 150 100)")
        self.cmd_processor.execute_command_string("(circle 75 50 35)")
        self.cmd_processor.execute_command_string("(line 0 0 150 100)")
        self.cmd_processor.execute_command_string("(line 0 100 150 0)")
        self.viewport.zoom_extents()

    def action_run_python_demo(self):
        code = (
            "py: for i in range(12):\n"
            "    ang = math.radians(i * 30)\n"
            "    doc.add_entity(CircleEntity(Vec2(200 + 80*math.cos(ang), 100 + 80*math.sin(ang)), 10, layer='DOORS'))"
        )
        self.cmd_processor.execute_command_string(code)
        self.viewport.zoom_extents()

    # Preset Sample Loaders
    def load_sample_floor_plan(self):
        from samples.sample_floor_plan import create_sample_floor_plan
        self.doc.clear()
        create_sample_floor_plan(self.doc)
        self._refresh_layer_combo()
        self.prop_widget.refresh()
        self.viewport.zoom_extents()
        self.cmd_line.log("Architectural Floor Plan sample loaded successfully! (Walls, Doors, Windows, Dimensions)")

    def load_sample_mechanical(self):
        from samples.sample_mechanical import create_sample_mechanical_part
        self.doc.clear()
        create_sample_mechanical_part(self.doc)
        self._refresh_layer_combo()
        self.prop_widget.refresh()
        self.viewport.zoom_extents()
        self.cmd_line.log("Mechanical Component & Spur Gear sample loaded successfully!")

    # Help Dialogs
    def action_help_commands(self):
        help_txt = (
            "<h3>Command & Shortcut Reference</h3>"
            "<p><b>Drawing Shortcuts:</b><br>"
            "<b>L</b>: Line | <b>PL</b>: Polyline | <b>C</b>: Circle | <b>A</b>: Arc<br>"
            "<b>REC</b>: Rectangle | <b>SPL</b>: Spline | <b>T</b>: Text | <b>DIM</b>: Dimension</p>"
            "<p><b>Precision Function Keys:</b><br>"
            "<b>F3</b>: OSNAP (Endpoint, Midpoint, Center, Quadrant, Intersection)<br>"
            "<b>F7</b>: GRID display on/off<br>"
            "<b>F8</b>: ORTHO mode (lock horizontal/vertical)<br>"
            "<b>F9</b>: SNAP to grid<br>"
            "<b>F10</b>: POLAR tracking (45° angle alignment)<br>"
            "<b>F12</b>: 3D Isometric View</p>"
            "<p><b>Mouse Navigation:</b><br>"
            "<b>Scroll Wheel</b>: Zoom in/out at mouse pointer<br>"
            "<b>Middle Mouse Drag</b>: Pan viewport<br>"
            "<b>Left Drag Left-to-Right</b>: Window selection (Blue box)<br>"
            "<b>Left Drag Right-to-Left</b>: Crossing selection (Green box)</p>"
            "<p><b>AutoLISP & Scripting:</b><br>"
            "Type AutoLISP commands in the CLI: <code>(line 0 0 100 100)</code><br>"
            "Execute Python in the CLI: <code>py: [python code]</code></p>"
        )
        QMessageBox.information(self, "Command Reference", help_txt)

    def action_about_tech(self):
        about_txt = (
            "<h3>CAD Studio 2026 - System Architecture</h3>"
            "<p><b>Technical Specifications:</b></p>"
            "<ul>"
            "<li><b>Geometry Engine:</b> Vector math pipeline with AABB spatial queries and segment intersections</li>"
            "<li><b>Graphics Subsystem:</b> Qt 6 hardware-accelerated 2D/3D viewport with antialiasing</li>"
            "<li><b>File I/O Engine:</b> Standard DXF (R2010/R2018) read/write with layer styling</li>"
            "<li><b>Scripting Subsystem:</b> Integrated AutoLISP parser and Python scripting interface</li>"
            "<li><b>Precision Drafting:</b> Magnetic OSNAP subsystem, Ortho constraint, Polar alignment</li>"
            "<li><b>Document Model:</b> Transactional undo/redo stack with layer management</li>"
            "</ul>"
        )
        QMessageBox.about(self, "About CAD Studio 2026", about_txt)
