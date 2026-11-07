"""
Command line console with command history, auto-complete, and logging.
"""

from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QLabel, QCompleter, QDockWidget
)
from PyQt6.QtGui import QFont, QKeyEvent, QTextCursor


class CadCommandLine(QWidget):
    command_submitted = pyqtSignal(str)
    cancel_requested = pyqtSignal()

    CAD_COMMANDS = [
        "LINE", "L", "CIRCLE", "C", "RECT", "REC", "RECTANGLE",
        "ARC", "A", "PLINE", "PL", "SPLINE", "SPL", "TEXT", "T",
        "DIM", "D", "DIMENSION", "ERASE", "E", "DEL",
        "MOVE", "M", "COPY", "CO", "CP", "ROTATE", "RO", "SCALE", "SC",
        "TRIM", "TR", "EXTEND", "EX", "OFFSET", "O",
        "UNDO", "U", "REDO", "CLEAR", "ZOOM", "Z", "PAN", "P",
        "LAYER", "LA", "COLOR", "COL", "HELP", "?"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history: List[str] = []
        self.history_index: int = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Output Log (Monospace CAD terminal)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(80)
        self.log_area.setFont(QFont("Consolas", 10))
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #141414;
                color: #d4d4d4;
                border: 1px solid #333333;
                border-radius: 2px;
                padding: 4px;
            }
        """)

        # Input Row
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(4)

        self.prompt_label = QLabel("Command:")
        self.prompt_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.prompt_label.setStyleSheet("color: #00e5ff; padding-left: 2px;")

        self.input_field = QLineEdit()
        self.input_field.setFont(QFont("Consolas", 10))
        self.input_field.setPlaceholderText("Type a command or AutoLISP expression (e.g. LINE, CIRCLE, (line 0 0 100 100))")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #007acc;
                border-radius: 2px;
                padding: 4px 6px;
            }
            QLineEdit:focus {
                border: 1px solid #00e5ff;
            }
        """)

        # Auto-complete
        completer = QCompleter(self.CAD_COMMANDS, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.input_field.setCompleter(completer)

        # Event filter for keys
        self.input_field.installEventFilter(self)

        input_row.addWidget(self.prompt_label)
        input_row.addWidget(self.input_field)

        layout.addWidget(self.log_area)
        layout.addLayout(input_row)

        self.log("CAD Studio 2026 initialized. Ready for commands. Type HELP or ? for quick reference.")

    def set_prompt(self, text: str):
        self.prompt_label.setText(text)

    def log(self, text: str):
        self.log_area.append(text)
        self.log_area.moveCursor(QTextCursor.MoveOperation.End)

    def eventFilter(self, obj, event):
        if obj == self.input_field and event.type() == QKeyEvent.Type.KeyPress:
            key = event.key()

            # Spacebar or Enter submits command
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._submit_current_text()
                return True

            elif key == Qt.Key.Key_Space:
                txt = self.input_field.text().strip()
                # If single command word, Space triggers command execution
                if txt and not (' ' in txt or txt.startswith('(') or txt.startswith('py:')):
                    self._submit_current_text()
                    return True

            elif key == Qt.Key.Key_Escape:
                self.input_field.clear()
                self.set_prompt("Command:")
                self.cancel_requested.emit()
                self.log("*Cancel*")
                return True

            elif key == Qt.Key.Key_Up:
                self._navigate_history(-1)
                return True

            elif key == Qt.Key.Key_Down:
                self._navigate_history(1)
                return True

        return super().eventFilter(obj, event)

    def _submit_current_text(self):
        cmd = self.input_field.text().strip()
        self.input_field.clear()
        if not cmd:
            # Re-issue last command on empty Enter
            if self.history:
                cmd = self.history[-1]
            else:
                return

        self.history.append(cmd)
        self.history_index = len(self.history)

        self.log(f"<font color='#00e5ff'><b>Command:</b></font> {cmd}")
        self.command_submitted.emit(cmd)

    def _navigate_history(self, delta: int):
        if not self.history:
            return
        new_idx = self.history_index + delta
        if 0 <= new_idx < len(self.history):
            self.history_index = new_idx
            self.input_field.setText(self.history[self.history_index])
        elif new_idx >= len(self.history):
            self.history_index = len(self.history)
            self.input_field.clear()

