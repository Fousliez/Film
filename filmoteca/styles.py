APP_STYLESHEET = """
QWidget {
    background: #11151c;
    color: #e9edf5;
    font-family: "Inter", "Segoe UI", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog { background: #11151c; }
QFrame#sidebar, QFrame#detailPanel, QFrame#card {
    background: #171d27;
    border: 1px solid #263041;
    border-radius: 12px;
}
QLabel#appTitle { font-size: 22px; font-weight: 700; color: #ffffff; }
QLabel#sectionTitle { font-size: 18px; font-weight: 700; color: #ffffff; }
QLabel#muted { color: #98a4b7; }
QLabel#posterPlaceholder {
    background: #0c1016;
    border: 1px dashed #36445a;
    border-radius: 10px;
    color: #6f7d91;
}
QPushButton {
    background: #252f40;
    border: 1px solid #344158;
    border-radius: 8px;
    padding: 8px 12px;
}
QPushButton:hover { background: #303c51; }
QPushButton:pressed { background: #1e2735; }
QPushButton#primaryButton {
    background: #5b7cfa;
    border-color: #6c8afd;
    color: white;
    font-weight: 600;
}
QPushButton#primaryButton:hover { background: #6c8afd; }
QPushButton#dangerButton { background: #45232a; border-color: #743440; }
QPushButton#navButton {
    text-align: left;
    padding: 10px 14px;
    border: none;
    background: transparent;
}
QPushButton#navButton:checked { background: #25314a; color: white; font-weight: 600; }
QPushButton#starButton {
    border: none;
    background: transparent;
    padding: 0;
    font-size: 22px;
    color: #667085;
}
QPushButton#starButton[active="true"] { color: #f4c451; }
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background: #0e131b;
    border: 1px solid #303b4e;
    border-radius: 8px;
    padding: 7px 9px;
    selection-background-color: #5b7cfa;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #6c8afd;
}
QTableWidget {
    background: #121821;
    alternate-background-color: #161e29;
    border: 1px solid #293447;
    border-radius: 10px;
    gridline-color: #273143;
    selection-background-color: #293c66;
    selection-color: white;
}
QHeaderView::section {
    background: #1b2330;
    color: #aeb8c8;
    border: none;
    border-bottom: 1px solid #303b4e;
    padding: 8px;
    font-weight: 600;
}
QTabWidget::pane { border: 1px solid #293447; border-radius: 8px; top: -1px; }
QTabBar::tab { background: #171d27; padding: 9px 14px; border: 1px solid #293447; }
QTabBar::tab:selected { background: #25314a; color: white; }
QScrollBar:vertical { width: 10px; background: transparent; }
QScrollBar::handle:vertical {
    background: #38465d;
    border-radius: 5px;
    min-height: 30px;
}
QToolTip { background: #222a38; color: white; border: 1px solid #44516a; }
"""
