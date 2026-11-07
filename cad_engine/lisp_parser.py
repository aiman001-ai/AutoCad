"""
Command parser, AutoLISP expression evaluator, and embedded scripting engine.
"""

import re
import shlex
from typing import List, Optional, Callable, Any
from .geometry import Vec2
from .entities import (
    LineEntity, CircleEntity, ArcEntity, RectEntity,
    PolylineEntity, SplineEntity, TextEntity, DimensionEntity
)
from .document import CadDocument


def parse_point(arg: str) -> Optional[Vec2]:
    """Parses 'x,y' or '(x y)' format into Vec2."""
    arg = arg.strip('()[] ')
    if ',' in arg:
        parts = arg.split(',')
    else:
        parts = arg.split()
    if len(parts) >= 2:
        try:
            return Vec2(float(parts[0]), float(parts[1]))
        except ValueError:
            return None
    return None


class CadCommandProcessor:
    def __init__(self, doc: CadDocument, ui_callbacks: Optional[dict] = None):
        self.doc = doc
        self.callbacks = ui_callbacks or {}
        # Multi-step command state
        self.active_interactive_cmd: Optional[str] = None
        self.interactive_data: list = []

    def log(self, text: str):
        if "log" in self.callbacks:
            self.callbacks["log"](text)
        else:
            print(text)

    def execute_command_string(self, cmd_line: str) -> str:
        cmd_line = cmd_line.strip()
        if not cmd_line:
            return ""

        # 1. Python direct execution (like ObjectARX / PyAutoCAD)
        if cmd_line.startswith("py:"):
            code = cmd_line[3:].strip()
            return self._exec_python(code)

        # 2. AutoLISP expression: (command ...) or (circle ...)
        if cmd_line.startswith("(") and cmd_line.endswith(")"):
            return self._eval_lisp(cmd_line)

        # 3. Handle interactive ongoing command continuation
        if self.active_interactive_cmd:
            return self._handle_interactive_step(cmd_line)

        # 4. Standard AutoCAD CLI commands
        parts = cmd_line.split()
        verb = parts[0].upper()
        args = parts[1:]

        return self._dispatch_cad_command(verb, args)

    def cancel_active_command(self):
        if self.active_interactive_cmd:
            cmd = self.active_interactive_cmd
            self.active_interactive_cmd = None
            self.interactive_data.clear()
            self.log(f"*Cancel* ({cmd})")

    def _dispatch_cad_command(self, verb: str, args: List[str]) -> str:
        # Command Aliases
        aliases = {
            "L": "LINE",
            "C": "CIRCLE",
            "REC": "RECT",
            "RECTANGLE": "RECT",
            "A": "ARC",
            "PL": "PLINE",
            "POLYLINE": "PLINE",
            "SPL": "SPLINE",
            "T": "TEXT",
            "MTEXT": "TEXT",
            "D": "DIM",
            "DIMENSION": "DIM",
            "E": "ERASE",
            "DEL": "ERASE",
            "U": "UNDO",
            "Z": "ZOOM",
            "P": "PAN",
            "LA": "LAYER",
            "COL": "COLOR",
            "?": "HELP"
        }
        cmd = aliases.get(verb, verb)

        if cmd == "LINE":
            if len(args) >= 2:
                p1 = parse_point(args[0])
                p2 = parse_point(args[1])
                if p1 and p2:
                    self.doc.add_entity(LineEntity(p1, p2))
                    self._request_redraw()
                    return f"Line created: ({p1.x}, {p1.y}) to ({p2.x}, {p2.y})"
            # Start interactive LINE
            self.active_interactive_cmd = "LINE"
            self.interactive_data = []
            if "set_tool" in self.callbacks:
                self.callbacks["set_tool"]("LINE")
            return "Specify first point:"

        elif cmd == "CIRCLE":
            if len(args) >= 2:
                c = parse_point(args[0])
                try:
                    r = float(args[1])
                    if c:
                        self.doc.add_entity(CircleEntity(c, r))
                        self._request_redraw()
                        return f"Circle created: center ({c.x}, {c.y}), radius {r}"
                except ValueError:
                    pass
            self.active_interactive_cmd = "CIRCLE"
            self.interactive_data = []
            if "set_tool" in self.callbacks:
                self.callbacks["set_tool"]("CIRCLE")
            return "Specify center point for circle:"

        elif cmd == "RECT":
            if len(args) >= 2:
                p1 = parse_point(args[0])
                p2 = parse_point(args[1])
                if p1 and p2:
                    self.doc.add_entity(RectEntity(p1, p2))
                    self._request_redraw()
                    return f"Rectangle created: ({p1.x}, {p1.y}) to ({p2.x}, {p2.y})"
            self.active_interactive_cmd = "RECT"
            self.interactive_data = []
            if "set_tool" in self.callbacks:
                self.callbacks["set_tool"]("RECT")
            return "Specify first corner of rectangle:"

        elif cmd == "ARC":
            if len(args) >= 4:
                c = parse_point(args[0])
                try:
                    r = float(args[1])
                    sa = float(args[2])
                    ea = float(args[3])
                    if c:
                        self.doc.add_entity(ArcEntity(c, r, sa, ea))
                        self._request_redraw()
                        return f"Arc created: center ({c.x}, {c.y}), radius {r}"
                except ValueError:
                    pass
            if "set_tool" in self.callbacks:
                self.callbacks["set_tool"]("ARC")
            return "Specify center point for arc:"

        elif cmd == "TEXT":
            if len(args) >= 2:
                pos = parse_point(args[0])
                text = " ".join(args[1:])
                if pos:
                    self.doc.add_entity(TextEntity(text, pos))
                    self._request_redraw()
                    return f"Text '{text}' placed at ({pos.x}, {pos.y})"
            if "set_tool" in self.callbacks:
                self.callbacks["set_tool"]("TEXT")
            return "Specify text insertion point:"

        elif cmd == "DIM":
            if len(args) >= 2:
                p1 = parse_point(args[0])
                p2 = parse_point(args[1])
                if p1 and p2:
                    self.doc.add_entity(DimensionEntity(p1, p2))
                    self._request_redraw()
                    return f"Dimension created: {p1.distance_to(p2):.2f}"
            if "set_tool" in self.callbacks:
                self.callbacks["set_tool"]("DIMENSION")
            return "Specify first extension line origin:"

        elif cmd == "ERASE":
            count = self.doc.delete_selected()
            self._request_redraw()
            return f"{count} entity(ies) deleted." if count > 0 else "No objects selected. Select objects to erase."

        elif cmd == "UNDO":
            if self.doc.undo():
                self._request_redraw()
                return "Command undone."
            return "Nothing to undo."

        elif cmd == "REDO":
            if self.doc.redo():
                self._request_redraw()
                return "Command redone."
            return "Nothing to redo."

        elif cmd == "CLEAR":
            self.doc.clear()
            self._request_redraw()
            return "Drawing cleared."

        elif cmd == "ZOOM":
            sub = args[0].upper() if args else "EXTENTS"
            if sub in ("E", "EXTENTS", "ALL", "A"):
                if "zoom_extents" in self.callbacks:
                    self.callbacks["zoom_extents"]()
                return "Zooming to drawing extents."
            return "ZOOM [All/Center/Dynamic/Extents/Window] <Extents>:"

        elif cmd == "LAYER":
            if args:
                name = args[0].upper()
                if name in self.doc.layers:
                    self.doc.active_layer = name
                    return f"Current layer set to '{name}'."
                return f"Layer '{name}' does not exist. Use Layer dialog to create it."
            if "open_layers" in self.callbacks:
                self.callbacks["open_layers"]()
            return "Opening Layer Manager..."

        elif cmd == "HELP":
            return (
                "--- Command & Shortcut Reference ---\n"
                "Draw Tools: LINE (L), CIRCLE (C), RECT (REC), ARC (A), PLINE (PL), SPLINE (SPL), TEXT (T), DIM (D)\n"
                "Edit Tools: ERASE (E), UNDO (U), REDO, CLEAR, ZOOM (Z), LAYER (LA)\n"
                "AutoLISP: (line x1 y1 x2 y2), (circle cx cy r), (rect x1 y1 x2 y2)\n"
                "Python Scripting: py: for i in range(5): doc.add_entity(CircleEntity(Vec2(i*30, 0), 10))\n"
                "Precision Keys: F3 (OSNAP), F7 (GRID), F8 (ORTHO), F9 (SNAP)"
            )

        return f"Unknown command \"{verb}\". Press HELP or ? for command list."

    def _handle_interactive_step(self, text: str) -> str:
        pt = parse_point(text)
        if pt is None:
            return f"Invalid point coordinate: {text}. Format: x,y"

        if self.active_interactive_cmd == "LINE":
            if not self.interactive_data:
                self.interactive_data.append(pt)
                return f"Specify next point [or press Enter/Esc to finish]:"
            else:
                p1 = self.interactive_data[-1]
                p2 = pt
                self.doc.add_entity(LineEntity(p1, p2))
                self.interactive_data.append(p2)
                self._request_redraw()
                return f"Specify next point [or press Enter/Esc to finish]:"

        elif self.active_interactive_cmd == "CIRCLE":
            if not self.interactive_data:
                self.interactive_data.append(pt)
                return "Specify radius of circle:"
            else:
                # If numeric radius or second point
                c = self.interactive_data[0]
                r = c.distance_to(pt)
                self.doc.add_entity(CircleEntity(c, r))
                self.active_interactive_cmd = None
                self.interactive_data.clear()
                self._request_redraw()
                return f"Circle created with radius {r:.2f}."

        elif self.active_interactive_cmd == "RECT":
            if not self.interactive_data:
                self.interactive_data.append(pt)
                return "Specify other corner of rectangle:"
            else:
                p1 = self.interactive_data[0]
                p2 = pt
                self.doc.add_entity(RectEntity(p1, p2))
                self.active_interactive_cmd = None
                self.interactive_data.clear()
                self._request_redraw()
                return f"Rectangle created."

        return ""

    def _eval_lisp(self, expr: str) -> str:
        """Simple AutoLISP interpreter for basic CAD geometry calls."""
        clean = expr.strip("() ")
        tokens = clean.split()
        if not tokens:
            return ""
        fn = tokens[0].lower()
        args = tokens[1:]

        try:
            if fn in ("line", "c:line"):
                x1, y1, x2, y2 = map(float, args[:4])
                self.doc.add_entity(LineEntity(Vec2(x1, y1), Vec2(x2, y2)))
                self._request_redraw()
                return f"AutoLISP: LINE created."

            elif fn in ("circle", "c:circle"):
                cx, cy, r = map(float, args[:3])
                self.doc.add_entity(CircleEntity(Vec2(cx, cy), r))
                self._request_redraw()
                return f"AutoLISP: CIRCLE created."

            elif fn in ("rect", "c:rect"):
                x1, y1, x2, y2 = map(float, args[:4])
                self.doc.add_entity(RectEntity(Vec2(x1, y1), Vec2(x2, y2)))
                self._request_redraw()
                return f"AutoLISP: RECT created."

            elif fn in ("text", "c:text"):
                # (text "hello" 10 20)
                text_val = args[0].strip('"')
                x, y = float(args[1]), float(args[2])
                self.doc.add_entity(TextEntity(text_val, Vec2(x, y)))
                self._request_redraw()
                return f"AutoLISP: TEXT created."

            elif fn == "+":
                nums = [float(a) for a in args]
                return str(sum(nums))

            elif fn == "*":
                prod = 1.0
                for a in args:
                    prod *= float(a)
                return str(prod)

        except Exception as e:
            return f"AutoLISP Error: {e}"

        return f"Unknown AutoLISP function: {fn}"

    def _exec_python(self, code: str) -> str:
        """Executes embedded Python code with direct access to doc, Vec2, entities."""
        local_scope = {
            "doc": self.doc,
            "Vec2": Vec2,
            "LineEntity": LineEntity,
            "CircleEntity": CircleEntity,
            "ArcEntity": ArcEntity,
            "RectEntity": RectEntity,
            "PolylineEntity": PolylineEntity,
            "SplineEntity": SplineEntity,
            "TextEntity": TextEntity,
            "DimensionEntity": DimensionEntity,
        }
        try:
            # Try eval first, then exec
            try:
                res = eval(code, {}, local_scope)
                self._request_redraw()
                return f"Python Result: {res}"
            except SyntaxError:
                exec(code, {}, local_scope)
                self._request_redraw()
                return "Python executed successfully."
        except Exception as e:
            return f"Python Script Error: {e}"

    def _request_redraw(self):
        if "redraw" in self.callbacks:
            self.callbacks["redraw"]()

