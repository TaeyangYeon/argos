"""
Dark theme QSS stylesheet for the Argos vision algorithm design application.

This module contains the complete QSS stylesheet for the modern dark theme.
All color constants and styles are defined in a single DARK_THEME_QSS string.
"""

DARK_THEME_QSS = """
/* Main Color System */
QMainWindow, QWidget {
    background-color: #1A1A2E;
    color: #E0E0E0;
    font-family: "Noto Sans KR", "Arial", sans-serif;
    font-size: 14px;
}

/* QPushButton Styles */
QPushButton {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    border-radius: 6px;
    padding: 8px 16px;
    color: #E0E0E0;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #1E2A4A;
    border-color: #1E88E5;
}

QPushButton:pressed {
    background-color: #0F3460;
}

QPushButton:disabled {
    background-color: #1A1A2E;
    color: #616161;
    border-color: #2A2A4A;
}

QPushButton#primaryBtn {
    background-color: #1E88E5;
    border-color: #1E88E5;
}

QPushButton#primaryBtn:hover {
    background-color: #1565C0;
    border-color: #1565C0;
}

QPushButton#primaryBtn:pressed {
    background-color: #0D47A1;
}

QPushButton#dangerBtn {
    background-color: #E53935;
    border-color: #E53935;
}

QPushButton#dangerBtn:hover {
    background-color: #C62828;
    border-color: #C62828;
}

QPushButton#dangerBtn:pressed {
    background-color: #B71C1C;
}

/* QLabel Styles */
QLabel {
    color: #E0E0E0;
    background: transparent;
}

QLabel#titleLabel {
    color: #E0E0E0;
    font-size: 18px;
    font-weight: 600;
}

QLabel#subtitleLabel {
    color: #9E9E9E;
    font-size: 12px;
}

/* QScrollArea Styles */
QScrollArea {
    border: 1px solid #2A2A4A;
    background-color: #1A1A2E;
}

QScrollBar:vertical {
    background: #16213E;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #1E88E5;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #1565C0;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollBar:horizontal {
    background: #16213E;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background: #1E88E5;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background: #1565C0;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}

/* QToolBar Styles */
QToolBar {
    background-color: #16213E;
    border-bottom: 1px solid #2A2A4A;
    spacing: 3px;
    padding: 4px;
}

QToolBar::separator {
    background: #2A2A4A;
    width: 1px;
    height: 20px;
}

/* QSplitter Styles */
QSplitter::handle {
    background-color: #2A2A4A;
}

QSplitter::handle:vertical {
    height: 2px;
}

QSplitter::handle:horizontal {
    width: 2px;
}

/* QFrame Styles */
QFrame#card {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    border-radius: 8px;
    padding: 12px;
}

QFrame#card:hover {
    background-color: #1E2A4A;
}

QFrame#sidebar {
    background-color: #0F3460;
    border: none;
}

/* QStackedWidget Styles */
QStackedWidget {
    background-color: #1A1A2E;
}

/* QComboBox Styles */
QComboBox {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    border-radius: 4px;
    padding: 6px 12px;
    color: #E0E0E0;
    min-width: 120px;
}

QComboBox:hover {
    border-color: #1E88E5;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #2A2A4A;
}

QComboBox::down-arrow {
    width: 12px;
    height: 12px;
    background: #E0E0E0;
}

QComboBox QAbstractItemView {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    selection-background-color: #1E88E5;
    color: #E0E0E0;
}

/* QLineEdit Styles */
QLineEdit {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    border-radius: 4px;
    padding: 8px 12px;
    color: #E0E0E0;
}

QLineEdit:focus {
    border-color: #1E88E5;
    outline: none;
}

/* QTextEdit Styles */
QTextEdit {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    border-radius: 4px;
    color: #E0E0E0;
    selection-background-color: #1E88E5;
    selection-color: #FFFFFF;
}

/* QProgressBar Styles */
QProgressBar {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    border-radius: 4px;
    text-align: center;
    color: #E0E0E0;
}

QProgressBar::chunk {
    background-color: #1E88E5;
    border-radius: 3px;
}

/* QTabWidget Styles */
QTabWidget::pane {
    border: 1px solid #2A2A4A;
    background-color: #1A1A2E;
}

QTabBar::tab {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    color: #9E9E9E;
}

QTabBar::tab:selected {
    background-color: #1E88E5;
    color: #FFFFFF;
}

QTabBar::tab:hover {
    background-color: #1E2A4A;
    color: #E0E0E0;
}

/* QTableWidget Styles */
QTableWidget {
    background-color: #16213E;
    alternate-background-color: #1A1A2E;
    gridline-color: #2A2A4A;
    selection-background-color: #1E88E5;
    color: #E0E0E0;
}

QHeaderView::section {
    background-color: #0F3460;
    border: 1px solid #2A2A4A;
    padding: 8px;
    color: #E0E0E0;
    font-weight: 600;
}

/* QMessageBox Styles */
QMessageBox {
    background-color: #1A1A2E;
    color: #E0E0E0;
}

QMessageBox QPushButton {
    min-width: 80px;
}

/* QDialog Styles */
QDialog {
    background-color: #1A1A2E;
    color: #E0E0E0;
}

/* QToolTip Styles */
QToolTip {
    background-color: #0F3460;
    border: 1px solid #1E88E5;
    border-radius: 4px;
    padding: 4px 8px;
    color: #E0E0E0;
}

/* QStatusBar Styles */
QStatusBar {
    background-color: #16213E;
    border-top: 1px solid #2A2A4A;
    color: #E0E0E0;
}

QStatusBar::item {
    border: none;
}
"""