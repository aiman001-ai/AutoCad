"""
Application dark theme stylesheet (QSS).
"""

DARK_THEME_QSS = """
QMainWindow {
    background-color: #1e1e24;
    color: #e0e0e0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 12px;
}

/* Menu Bar */
QMenuBar {
    background-color: #252526;
    color: #cccccc;
    border-bottom: 1px solid #333337;
    padding: 2px 6px;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    border-radius: 3px;
}

QMenuBar::item:selected {
    background-color: #094771;
    color: #ffffff;
}

QMenu {
    background-color: #252526;
    color: #e0e0e0;
    border: 1px solid #3f3f46;
    padding: 4px;
}

QMenu::item {
    padding: 5px 25px 5px 20px;
    border-radius: 2px;
}

QMenu::item:selected {
    background-color: #007acc;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #3f3f46;
    margin: 4px 10px;
}

/* Toolbars */
QToolBar {
    background-color: #2d2d30;
    border: none;
    border-bottom: 1px solid #3e3e42;
    padding: 3px;
    spacing: 4px;
}

QToolButton {
    background-color: transparent;
    color: #dcdcdc;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 4px 8px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #3e3e40;
    border: 1px solid #007acc;
}

QToolButton:pressed, QToolButton:checked {
    background-color: #0e639c;
    border: 1px solid #1177bb;
    color: #ffffff;
}

/* Dock Widgets */
QDockWidget {
    color: #cccccc;
    font-weight: bold;
    font-size: 11px;
}

QDockWidget::title {
    background-color: #252526;
    padding: 6px;
    border-bottom: 1px solid #3e3e42;
}

QDockWidget::close-button, QDockWidget::float-button {
    background: transparent;
    border: none;
    padding: 2px;
}

QDockWidget::close-button:hover, QDockWidget::float-button:hover {
    background-color: #3e3e40;
}

/* Tab Widgets & Docks */
QTabWidget::pane {
    border: 1px solid #333337;
    background-color: #252526;
}

QTabBar::tab {
    background-color: #2d2d30;
    color: #969696;
    padding: 6px 14px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1e1e24;
    color: #ffffff;
    border-top: 2px solid #007acc;
}

/* Tree / Table / List Views */
QTreeView, QTableView, QListView {
    background-color: #1e1e1e;
    color: #cccccc;
    border: 1px solid #333337;
    gridline-color: #2a2a2d;
    selection-background-color: #094771;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #2d2d30;
    color: #cccccc;
    padding: 4px 8px;
    border: 1px solid #3e3e42;
    font-weight: bold;
}

/* Inputs, ComboBox, SpinBox */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1e1e1e;
    color: #f1f1f1;
    border: 1px solid #3e3e42;
    border-radius: 2px;
    padding: 4px 6px;
    selection-background-color: #007acc;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #007acc;
}

QComboBox::drop-down {
    border: none;
    width: 18px;
}

QComboBox QAbstractItemView {
    background-color: #252526;
    border: 1px solid #3e3e42;
    selection-background-color: #094771;
    color: #e0e0e0;
}

/* Status Bar */
QStatusBar {
    background-color: #007acc;
    color: #ffffff;
    font-size: 11px;
    font-weight: 500;
    border-top: 1px solid #005999;
}

QStatusBar QLabel {
    color: #ffffff;
    padding: 2px 6px;
}

/* Status Bar Toggle Buttons (Snap/Grid/Ortho indicators) */
QStatusBar QPushButton {
    background-color: rgba(255, 255, 255, 0.12);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 2px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}

QStatusBar QPushButton:checked {
    background-color: #ffffff;
    color: #005999;
    border: 1px solid #ffffff;
}

QStatusBar QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.25);
}

/* Scrollbars */
QScrollBar:vertical {
    background: #1e1e1e;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #424242;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #5a5a5a;
}

QScrollBar:horizontal {
    background: #1e1e1e;
    height: 10px;
}

QScrollBar::handle:horizontal {
    background: #424242;
    min-width: 20px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #5a5a5a;
}

QScrollBar::add-line, QScrollBar::sub-line {
    background: none;
    border: none;
}
"""

