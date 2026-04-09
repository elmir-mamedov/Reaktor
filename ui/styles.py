LIGHT_STYLESHEET = """
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
    background-color: #dfe6e9;
    color: #2c3e50;
    border: 1px solid #aab7b8;
    border-radius: 4px;
padding: 6px 16px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #ccd6dd;
}
QPushButton:pressed {
    background-color: #b2bec3;
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
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 2px solid #7f8c8d;
    border-radius: 3px;
    background-color: white;
}
QCheckBox::indicator:checked {
    background-color: #2c3e50;
    border-color: #2c3e50;
    image: url(ui/check.svg);
}
QCheckBox::indicator:hover {
    border-color: #2980b9;
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

/* ── Scroll bars ── */
QScrollBar:vertical {
    background: #f0f2f3;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #b2bec3;
    min-height: 24px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #95a5a6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #f0f2f3;
    height: 10px;
    margin: 0;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #b2bec3;
    min-width: 24px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #95a5a6;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
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

DARK_STYLESHEET = """
/* ── Main window ── */
QMainWindow {
    background-color: #0f0f0f;
}
QWidget {
    background-color: #0f0f0f;
    color: #e8e8e8;
}

/* ── Menu bar ── */
QMenuBar {
    background-color: #0a0a0a;
    color: #e8e8e8;
    font-size: 13px;
    padding: 2px 4px;
}
QMenuBar::item:selected {
    background-color: #1e1e1e;
    border-radius: 3px;
}
QMenu {
    background-color: #111111;
    color: #e8e8e8;
    border: 1px solid #2a2a2a;
}
QMenu::item:selected {
    background-color: #2980b9;
}
QMenu::separator {
    height: 1px;
    background: #2a2a2a;
    margin: 3px 10px;
}

/* ── Toolbar ── */
QToolBar {
    background-color: #111111;
    border-bottom: 1px solid #2a2a2a;
    spacing: 4px;
    padding: 3px 6px;
}
QToolBar QToolButton {
    background-color: #1a4a6e;
    color: #e8e8e8;
    border: none;
    border-radius: 4px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: bold;
    min-width: 80px;
}
QToolBar QToolButton:hover {
    background-color: #2980b9;
}
QToolBar QToolButton:pressed {
    background-color: #1f618d;
}
QToolBar::separator {
    width: 1px;
    background: #2a2a2a;
    margin: 4px 6px;
}

/* ── Dock widgets ── */
QDockWidget {
    font-size: 12px;
    font-weight: bold;
    color: #e8e8e8;
}
QDockWidget::title {
    background-color: #111111;
    color: #e8e8e8;
    padding: 5px 8px;
    text-align: left;
}

/* ── Group boxes ── */
QGroupBox {
    font-size: 11px;
    font-weight: bold;
    color: #a0c8e8;
    border: 1px solid #2a2a2a;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    background-color: #0f0f0f;
}

/* ── Input widgets ── */
QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox {
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    padding: 3px 6px;
    background-color: #1a1a1a;
    font-size: 12px;
    min-height: 22px;
    color: #e8e8e8;
}
QDoubleSpinBox:focus, QSpinBox:focus,
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2980b9;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #1a1a1a;
    color: #e8e8e8;
    border: 1px solid #2a2a2a;
    selection-background-color: #2980b9;
}

/* ── Labels ── */
QLabel {
    color: #e8e8e8;
    font-size: 12px;
}

/* ── Buttons ── */
QPushButton {
    background-color: #1a1a1a;
    color: #e8e8e8;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #242424;
}
QPushButton:pressed {
    background-color: #2e2e2e;
}
QPushButton#run_btn {
    background-color: #1e8449;
    color: white;
    border: none;
    font-weight: bold;
}
QPushButton#run_btn:hover {
    background-color: #27ae60;
}
QPushButton#run_btn:pressed {
    background-color: #196f3d;
}

/* ── Check box ── */
QCheckBox {
    font-size: 12px;
    color: #e8e8e8;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 2px solid #555555;
    border-radius: 3px;
    background-color: #1a1a1a;
}
QCheckBox::indicator:checked {
    background-color: #1a1a1a;
    border-color: #555555;
    image: url(ui/check.svg);
}
QCheckBox::indicator:hover {
    border-color: #2980b9;
}

/* ── Scroll area ── */
QScrollArea {
    border: none;
    background-color: transparent;
}

/* ── Tab widget ── */
QTabWidget::pane {
    border: 1px solid #2a2a2a;
    background-color: #111111;
}
QTabBar::tab {
    background-color: #111111;
    color: #888888;
    padding: 6px 14px;
    border: 1px solid #2a2a2a;
    border-bottom: none;
    font-size: 12px;
    min-width: 100px;
}
QTabBar::tab:selected {
    background-color: #0f0f0f;
    color: #e8e8e8;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background-color: #1a1a1a;
}

/* ── Table ── */
QTableWidget {
    gridline-color: #2a2a2a;
    font-size: 11px;
    background-color: #0f0f0f;
    color: #e8e8e8;
    selection-background-color: #1a3a5c;
    alternate-background-color: #141414;
}
QHeaderView::section {
    background-color: #111111;
    color: #e8e8e8;
    padding: 4px 8px;
    border: none;
    border-right: 1px solid #2a2a2a;
    font-size: 11px;
    font-weight: bold;
}

/* ── Status bar ── */
QStatusBar {
    background-color: #0a0a0a;
    color: #e8e8e8;
    font-size: 11px;
}
QStatusBar::item {
    border: none;
}

/* ── Scroll bars ── */
QScrollBar:vertical {
    background: #1a1a1a;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #3a3a3a;
    min-height: 24px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #555555;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #1a1a1a;
    height: 10px;
    margin: 0;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #3a3a3a;
    min-width: 24px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #555555;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #2a2a2a;
}
"""

APP_STYLESHEET = DARK_STYLESHEET
