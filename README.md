# AutoCAD 2026 Engine (CAD Studio)

A 2D/3D Computer-Aided Design (CAD) desktop application built with PyQt6, hardware-accelerated graphics viewport, standard Autodesk DXF file compatibility, precision Object Snap (OSNAP) engine, and integrated AutoLISP & Python scripting console.

---

## Features

### 1. Viewport & Graphics Subsystem
- **Infinite Navigation:** Smooth pan (middle mouse drag) and cursor-centered zoom (mouse wheel).
- **Adaptive Cartesian Grid:** Automatic grid density scaling for micro and macro drafting.
- **Crosshair & Pickbox:** Precision crosshairs with coordinate tracking (`X`, `Y`).
- **Axonometric 3D Mode:** Instant toggle between 2D Plan View and 3D Isometric View (`F12`).
- **AutoCAD Selection Modes:**
  - *Window Selection (Left-to-Right):* Blue translucent box (selects fully enclosed entities).
  - *Crossing Selection (Right-to-Left):* Green translucent box (selects intersecting entities).

### 2. Precision Drafting Controls
- **OSNAP (`F3`):** Magnetic snapping for Endpoint, Midpoint, Center, Quadrant, and Intersection.
- **GRID (`F7`):** Toggle background grid display.
- **ORTHO (`F8`):** Lock drawing vectors to 90-degree orthogonal axes.
- **POLAR (`F10`):** Polar tracking alignment guidelines at 45-degree intervals.
- **SNAP (`F9`):** Snap cursor to coordinate grid intervals.

### 3. Drafting Entities
- **Line (`L`):** Continuous straight-line segments.
- **Polyline (`PL`):** Multi-segment continuous paths with open/close modes.
- **Circle (`C`):** Center-radius circle entity.
- **Arc (`A`):** 3-point circular arc with sweep calculation.
- **Rectangle (`REC`):** Axis-aligned rectangle polygon.
- **Spline (`SPL`):** Smooth Catmull-Rom spline curve.
- **Text (`T`):** Single-line annotative text labels.
- **Dimension (`DIM`):** Linear dimensioning with extension lines, tick marks, and measurement text.

### 4. Command Line Interface (CLI) & Scripting
- Bottom command dock with history, suggestions, and auto-completion.
- Supports standard CAD commands (`LINE`, `CIRCLE`, `RECT`, `ARC`, `PLINE`, `SPLINE`, `DIM`, `TEXT`, `ERASE`, `UNDO`, `REDO`, `ZOOM`, `PAN`, `LAYER`).
- **AutoLISP Evaluation:** Execute LISP expressions directly, e.g. `(line 0 0 100 100)`, `(circle 50 50 25)`.
- **Python Scripting Interface:** Run script commands directly via `py:`, e.g.:
  ```python
  py: [doc.add_entity(CircleEntity(Vec2(i * 30, 0), 10)) for i in range(10)]
  ```

### 5. Layer Management & Property Inspector
- **Layer Manager:** Create and organize layers with custom RGB colors, line types (Continuous, Dashed, Center, Hidden), line weights (0.18mm - 0.50mm), visibility toggles, and lock states.
- **Property Inspector:** Live inspection and modification of selected entity geometry (coordinates, length, radius, angle, area, and layer assignment).

### 6. File Compatibility
- **AutoCAD DXF Export (`.dxf`):** Generates standard AutoCAD DXF R2010/R2018 format drawings compatible with Autodesk AutoCAD, LibreCAD, and SolidWorks.
- **DXF Import (`.dxf`):** Reads and parses DXF drawings, geometry, layers, and styles into the active workspace.
- **Native Project (`.cad`):** Lossless JSON-based CAD document serialization.
- **High-Res Export:** Direct export to 300 DPI PNG images and vector PDF documents.

---

## Quick Start

### Prerequisites
- Python 3.10+ (64-bit)
- Dependencies: `PyQt6`, `ezdxf`, `numpy`

```bash
pip install -r requirements.txt
```

### Running the Application
- **Method 1:** Double-click `run_cad.bat`
- **Method 2:** Run via Python:
  ```bash
  python main.py
  ```
- **Method 3:** Double-click the desktop shortcut `AutoCAD 2026` (run `install.bat` to recreate shortcut if needed).

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| **L** | Line Tool |
| **C** | Circle Tool |
| **REC** | Rectangle Tool |
| **A** | Arc Tool |
| **PL** | Polyline Tool |
| **SPL** | Spline Tool |
| **T** | Text Tool |
| **D / DIM** | Dimension Tool |
| **E / Delete** | Erase Selected Entities |
| **Ctrl + Z** | Undo |
| **Ctrl + Y** | Redo |
| **Ctrl + A** | Select All |
| **F3** | Toggle Object Snap (OSNAP) |
| **F7** | Toggle Grid Display |
| **F8** | Toggle Ortho Mode |
| **F9** | Toggle Grid Snap |
| **F10** | Toggle Polar Tracking |
| **F12** | Toggle 3D Isometric View |
| **Mouse Wheel** | Zoom In / Out at Cursor |
| **Middle Click Drag** | Pan Viewport |
| **Esc** | Cancel Tool / Deselect |
| **Spacebar / Enter** | Repeat Last Command / Submit CLI Input |

---

## Project Structure

```
cad/
├── cad_engine/                # Core CAD math and document models
│   ├── geometry.py            # 2D/3D vectors, AABB, ray-tracing, intersections
│   ├── entities.py            # Geometric entity implementations
│   ├── document.py            # Document database, layers, undo/redo stack
│   ├── snap.py                # OSNAP precision snapping engine
│   ├── dxf_io.py              # DXF and JSON import/export
│   └── lisp_parser.py         # CLI, AutoLISP, and Python scripting engine
├── cad_ui/                    # Qt6 graphical user interface
│   ├── main_window.py         # Main CAD window, ribbon, menus, status bar
│   ├── viewport.py            # Graphics viewport and interaction canvas
│   ├── command_line.py        # CLI console dock with command completion
│   ├── properties_dock.py     # Live entity property inspector
│   ├── layer_dialog.py        # Layer properties manager dialog
│   └── styles.py              # Application dark theme styling (QSS)
├── samples/                   # Sample drawing presets
│   ├── sample_floor_plan.py   # Architectural floor plan generator
│   ├── sample_mechanical.py   # Mechanical spur gear generator
│   ├── sample_generator.py    # Pre-generates DXF and CAD sample files
│   ├── sample_floor_plan.dxf  # Architectural sample DXF
│   └── sample_mechanical.dxf  # Mechanical sample DXF
├── icons/                     # Application icons
│   ├── autocad.ico            # Windows icon resource
│   └── autocad.png            # PNG logo asset
├── install_desktop_shortcut.py# Windows shortcut installer
├── install.bat                # Shortcut installer batch script
├── run_cad.bat                # Application launcher batch script
├── main.py                    # Application entry point
├── requirements.txt           # Python package dependencies
└── README.md                  # Project documentation
```
