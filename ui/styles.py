APP_STYLESHEET = """
/* ── Main window ── */
QMainWindow {
    background-color: #ecf0f1;
}

/* ── Menu bar ── */
QMenuBar {
    background-color: #2c3e50;
    color: #ecf0f1;
    font-size: 13px;
    padding: 2px 4px;
}
QMenuBar::item:selected {
    background-color: #34495e;
    border-radius: 3px;
}
QMenu {
    background-color: #2c3e50;
    color: #ecf0f1;
    border: 1px solid #1a252f;
}
QMenu::item:selected {
    background-color: #2980b9;
}
QMenu::separator {
    height: 1px;
    background: #566573;
    margin: 3px 10px;
}

/* ── Toolbar ── */
QToolBar {
    background-color: #dfe6e9;
    border-bottom: 1px solid #b2bec3;
    spacing: 4px;
    padding: 3px 6px;
}
QToolBar QToolButton {
    background-color: #2980b9;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: bold;
    min-width: 80px;
}
QToolBar QToolButton:hover {
    background-color: #2471a3;
}
QToolBar QToolButton:pressed {
    background-color: #1f618d;
}
QToolBar::separator {
    width: 1px;
    background: #b2bec3;
    margin: 4px 6px;
}

/* ── Dock widgets ── */
QDockWidget {
    font-size: 12px;
    font-weight: bold;
    color: white;
}
QDockWidget::title {
    background-color: #2c5f8a;
    color: white;
    padding: 5px 8px;
    text-align: left;
}

/* ── Group boxes ── */
QGroupBox {
    font-size: 11px;
    font-weight: bold;
    color: #1a5276;
    border: 1px solid #aab7b8;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    background-color: white;
}

/* ── Input widgets ── */
QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox {
    border: 1px solid #aab7b8;
    border-radius: 3px;
    padding: 3px 6px;
    background-color: white;
    font-size: 12px;
    min-height: 22px;
    color: #2c3e50;
}
QDoubleSpinBox:focus, QSpinBox:focus,
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2980b9;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* ── Labels ── */
QLabel {
    color: #2c3e50;
    font-size: 12px;
}

/* ── Buttons ── */
QPushButton {
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 12px;
}
QPushButton#run_btn {
    background-color: #27ae60;
    color: white;
    border: none;
    font-weight: bold;
}
QPushButton#run_btn:hover {
    background-color: #1e8449;
}
QPushButton#run_btn:pressed {
    background-color: #196f3d;
}

/* ── Check box ── */
QCheckBox {
    font-size: 12px;
    color: #2c3e50;
    spacing: 6px;
}

/* ── Scroll area ── */
QScrollArea {
    border: none;
    background-color: transparent;
}

/* ── Tab widget ── */
QTabWidget::pane {
    border: 1px solid #aab7b8;
    background-color: white;
}
QTabBar::tab {
    background-color: #dfe6e9;
    color: #2c3e50;
    padding: 6px 14px;
    border: 1px solid #aab7b8;
    border-bottom: none;
    font-size: 12px;
    min-width: 100px;
}
QTabBar::tab:selected {
    background-color: white;
    color: #1a5276;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background-color: #ccd6dd;
}

/* ── Table ── */
QTableWidget {
    gridline-color: #dfe6e9;
    font-size: 11px;
    selection-background-color: #aed6f1;
    alternate-background-color: #f8f9fa;
}
QHeaderView::section {
    background-color: #2c5f8a;
    color: white;
    padding: 4px 8px;
    border: none;
    font-size: 11px;
    font-weight: bold;
}

/* ── Status bar ── */
QStatusBar {
    background-color: #2c3e50;
    color: #ecf0f1;
    font-size: 11px;
}
QStatusBar::item {
    border: none;
}
"""
