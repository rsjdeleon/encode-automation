"""Shared Qt stylesheet so every window in the app looks and feels the same."""

STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f1f5f9;
    font-family: "Segoe UI", sans-serif;
    color: #1e293b;
}

QDialog {
    background-color: #f1f5f9;
    font-family: "Segoe UI", sans-serif;
    color: #1e293b;
}

QFrame#card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}

QLabel.field-label {
    font-size: 10px;
    font-weight: 600;
    color: #475569;
    padding-top: 2px;
}

QLineEdit, QDateEdit, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 3px 6px;
    font-size: 12px;
    selection-background-color: #93c5fd;
}

QLineEdit:focus, QDateEdit:focus, QTextEdit:focus {
    border: 1px solid #2563eb;
}

QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 3px 6px;
    font-size: 12px;
}

QComboBox:focus {
    border: 1px solid #2563eb;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
}

QDateEdit::drop-down, QComboBox::drop-down {
    border: none;
    width: 18px;
}

QCheckBox {
    font-size: 11px;
    color: #334155;
    padding-top: 2px;
    background: transparent;
}

QCheckBox::indicator {
    background: transparent;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    width: 13px;
    height: 13px;
}

QCheckBox::indicator:checked {
    background: #2563eb;
    border: 1px solid #2563eb;
}

QPushButton {
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
    color: #1e293b;
    background-color: #ffffff;
}
QPushButton:hover { background-color: #f1f5f9; }

QTableWidget, QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #e2e8f0;
    font-size: 11px;
    alternate-background-color: #f8fafc;
}

QListWidget::item {
    padding: 4px 6px;
}

QListWidget::item:selected {
    background-color: #dbeafe;
    color: #0f172a;
}

QTableWidget::item {
    padding: 3px;
}

QTableWidget::item:selected {
    background-color: #dbeafe;
    color: #0f172a;
}

QHeaderView::section {
    background-color: #e2e8f0;
    color: #334155;
    padding: 4px;
    border: none;
    border-right: 1px solid #cbd5e1;
    font-size: 10px;
    font-weight: 600;
}

QTabWidget::pane {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #e2e8f0;
    color: #475569;
    padding: 4px 12px;
    margin-right: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-size: 11px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0f172a;
}

QScrollArea {
    border: none;
    background-color: transparent;
}
"""
