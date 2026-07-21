import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt

from db.worker_store import (
    init_db_worker, get_all_workers, insert_worker,
    update_worker, delete_worker_by_id,
)

from ui.styles import STYLESHEET


class SocialWorkerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Social Worker Management")
        self.resize(820, 620)
        self.setStyleSheet(STYLESHEET)

        self.selected_worker_id = None
        self.row_data = {}

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(4)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(6)

        full_name_col = QVBoxLayout()
        full_name_label = QLabel("FULL NAME")
        full_name_label.setProperty("class", "field-label")
        self.sw_full_name = QLineEdit()
        self.sw_full_name.setPlaceholderText("Full Name")
        full_name_col.addWidget(full_name_label)
        full_name_col.addWidget(self.sw_full_name)
        fields_row.addLayout(full_name_col)

        gform_col = QVBoxLayout()
        gform_label = QLabel("GFORM VALUE")
        gform_label.setProperty("class", "field-label")
        self.sw_gform_value = QLineEdit()
        self.sw_gform_value.setPlaceholderText("Value submitted to the Google Form")
        gform_col.addWidget(gform_label)
        gform_col.addWidget(self.sw_gform_value)
        fields_row.addLayout(gform_col)

        website_col = QVBoxLayout()
        website_label = QLabel("WEBSITE VALUE")
        website_label.setProperty("class", "field-label")
        self.sw_website_value = QLineEdit()
        self.sw_website_value.setPlaceholderText("Value submitted to the CRIMS website")
        website_col.addWidget(website_label)
        website_col.addWidget(self.sw_website_value)
        fields_row.addLayout(website_col)

        form_layout.addLayout(fields_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_add = QPushButton("Add")
        self.btn_add.setObjectName("addBtn")
        self.btn_update = QPushButton("Update")
        self.btn_update.setObjectName("updateBtn")
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("deleteBtn")
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("clearBtn")
        self.btn_add.clicked.connect(self.on_add)
        self.btn_update.clicked.connect(self.on_update)
        self.btn_delete.clicked.connect(self.on_delete)
        self.btn_clear.clicked.connect(self.clear_form)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_update)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        form_layout.addLayout(btn_row)

        root.addWidget(form_card)

        filter_row = QHBoxLayout()
        filter_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter by full name, gform value, or website value...")
        self.search_box.textChanged.connect(self.apply_filter)
        filter_row.addWidget(filter_label)
        filter_row.addWidget(self.search_box)
        root.addLayout(filter_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Full Name", "GForm Value", "Website Value"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.on_select_row)
        root.addWidget(self.table, 1)

        self.load_data()

    def load_data(self):
        self.row_data.clear()
        self.table.setRowCount(0)
        for row in get_all_workers():
            r = self.table.rowCount()
            self.table.insertRow(r)
            for col, val in enumerate(row):
                self.table.setItem(r, col, QTableWidgetItem(str(val)))
            self.row_data[row[0]] = {
                "id": row[0], "full_name": row[1], "gform_value": row[2],
                "website_value": row[3],
            }
        self.apply_filter(self.search_box.text())

    def apply_filter(self, text):
        needle = text.strip().lower()
        for r in range(self.table.rowCount()):
            if not needle:
                self.table.setRowHidden(r, False)
                continue
            haystack = " ".join(
                self.table.item(r, c).text().lower() for c in (1, 2, 3)
            )
            self.table.setRowHidden(r, needle not in haystack)

    def on_select_row(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = self.table.currentRow()
        worker_id = int(self.table.item(row, 0).text())
        worker = self.row_data.get(worker_id)
        if worker:
            self.selected_worker_id = worker["id"]
            self.sw_full_name.setText(worker["full_name"])
            self.sw_gform_value.setText(worker["gform_value"] or "")
            self.sw_website_value.setText(worker["website_value"] or "")

    def clear_form(self):
        self.selected_worker_id = None
        self.sw_full_name.clear()
        self.sw_gform_value.clear()
        self.sw_website_value.clear()
        self.table.clearSelection()

    def on_add(self):
        if not self.sw_full_name.text().strip():
            QMessageBox.information(self, "Add", "Full Name is required.")
            return
        reply = QMessageBox.question(
            self, "Add", "Are you sure you want to add this social worker?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if insert_worker(
                self.sw_full_name.text(), self.sw_gform_value.text(),
                self.sw_website_value.text()
            ):
                self.clear_form()
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Record already exists.")

    def on_update(self):
        if not self.selected_worker_id:
            QMessageBox.information(self, "Update", "Select a record from the table first.")
            return
        reply = QMessageBox.question(
            self, "Update", "Are you sure you want to update this social worker?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            update_worker(
                self.selected_worker_id,
                self.sw_full_name.text(), self.sw_gform_value.text(),
                self.sw_website_value.text()
            )
            self.clear_form()
            self.load_data()

    def on_delete(self):
        if not self.selected_worker_id:
            QMessageBox.information(self, "Delete", "Select a record from the table first.")
            return
        reply = QMessageBox.question(
            self, "Delete", "Are you sure you want to delete this social worker?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_worker_by_id(self.selected_worker_id)
            self.clear_form()
            self.load_data()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db_worker()
    window = SocialWorkerWindow()
    window.show()
    sys.exit(app.exec())
