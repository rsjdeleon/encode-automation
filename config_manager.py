import sys
import threading

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QListWidget,
    QListWidgetItem, QComboBox, QStackedWidget, QTextEdit, QCheckBox,
)
from PySide6.QtCore import Qt, Signal

from db.config_store import (
    init_db_config, seed_from_config_if_empty, backfill_city_regions,
    migrate_gender_to_pairs, migrate_target_sector_to_pairs,
    migrate_mode_of_release_to_pairs, migrate_financial_assistance_to_pairs,
    migrate_civil_status_to_pairs, migrate_fund_source_to_pairs,
    migrate_relationship_to_pairs, migrate_client_sub_category_to_pairs,
    migrate_target_sector_to_dual_pairs, migrate_approved_by_to_dual_pairs,
    migrate_region_to_dual_pairs, migrate_province_region_link_to_id,
    migrate_city_province_link_to_id, migrate_barangay_city_link_to_id,
    migrate_province_to_dual_pairs,
    migrate_city_to_dual_pairs, migrate_barangay_to_dual_pairs,
    migrate_gender_to_dual_pairs,
    migrate_civil_status_to_dual_pairs, migrate_fund_source_to_dual_pairs,
    migrate_mode_of_release_to_dual_pairs, migrate_financial_assistance_to_dual_pairs,
    migrate_relationship_to_dual_pairs, migrate_client_sub_category_to_dual_pairs,
    remove_approver_list, get_all_lists, get_items, insert_item, update_item,
    delete_item,
)
from sync_config_from_website import sync_field, FIELD_SYNC_TARGETS, GFORM_SYNC_TARGETS

from ui.styles import STYLESHEET

# Primary personal-info group in the sidebar.
PERSONAL_GROUP_ORDER = {
    "gender_list": 0,
    "civil_status_list": 1,
    "relationship_list": 2,
}

# Address-related lists shown together under a group header in cascade order.
ADDRESS_GROUP_ORDER = {"region_list": 0, "province_list": 1, "list_of_city": 2, "barangay_list": 3}

# Sentinel used in category_rows for the standalone "Sync" sidebar entry (not
# tied to any config_lists row, so it can't be an int index or None like a
# group header).
SYNC_ROW = "sync"


class ConfigManagerWindow(QMainWindow):
    # Sync runs Selenium on a background thread; these marshal its output back
    # to the GUI thread (Qt widgets can't be touched from a non-GUI thread).
    _sig_sync_log = Signal(str)
    _sig_sync_done = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration Manager")
        self.resize(920, 620)
        self.setStyleSheet(STYLESHEET)

        self.lists = []  # (id, key, label, kind, col1_label, col2_label)
        self.current_list = None
        self.selected_item_id = None
        self.row_data = {}

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # ── Category list (left) ────────────────────────────────────────
        category_card = QFrame()
        category_card.setObjectName("card")
        category_layout = QVBoxLayout(category_card)
        category_layout.setContentsMargins(10, 10, 10, 10)
        category_layout.setSpacing(4)
        category_layout.addWidget(QLabel("Config Categories"))

        self.category_list = QListWidget()
        self.category_list.setMaximumWidth(220)
        self.category_list.currentRowChanged.connect(self.on_select_category)
        category_layout.addWidget(self.category_list)
        root.addWidget(category_card)

        # ── Detail panel (right) ─────────────────────────────────────────
        # A stacked widget so the sidebar's "Sync" entry can swap this whole
        # panel for the Sync UI, while every other entry keeps showing the
        # normal category CRUD form + table.
        self.right_stack = QStackedWidget()

        crud_page = QWidget()
        right_container = QVBoxLayout(crud_page)
        right_container.setSpacing(8)

        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(4)

        # Row 1: the item's own identity (name + primary value).
        fields_row1 = QHBoxLayout()
        fields_row1.setSpacing(6)

        col1_col = QVBoxLayout()
        self.col1_label = QLabel("VALUE")
        self.col1_label.setProperty("class", "field-label")
        self.col1_input = QLineEdit()
        col1_col.addWidget(self.col1_label)
        col1_col.addWidget(self.col1_input)
        fields_row1.addLayout(col1_col, 1)

        self.col2_col = QVBoxLayout()
        self.col2_label = QLabel("VALUE 2")
        self.col2_label.setProperty("class", "field-label")
        self.col2_input = QLineEdit()
        self.col2_col.addWidget(self.col2_label)
        self.col2_col.addWidget(self.col2_input)
        fields_row1.addLayout(self.col2_col, 1)

        form_layout.addLayout(fields_row1)

        # Row 2: link to the parent list (picker) + website value. Only one of
        # the three pickers is ever visible at a time, depending on kind.
        fields_row2 = QHBoxLayout()
        fields_row2.setSpacing(6)

        # Single shared column: exactly one of the three pickers below is ever
        # visible at a time (depending on kind), all sharing one caption label.
        # They must live in ONE layout column (not three) so this column and
        # region_website_col are the only two stretch-carrying items in this row
        # — otherwise Qt splits the row's width across all three picker columns
        # even while two of them are empty/hidden, shrinking the visible one.
        self.picker_col = QVBoxLayout()
        self.picker_label = QLabel("LINK")
        self.picker_label.setProperty("class", "field-label")
        self.picker_col.addWidget(self.picker_label)

        self.province_picker = QComboBox()
        self.province_picker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.province_picker.setMinimumContentsLength(1)
        self.picker_col.addWidget(self.province_picker)

        self.city_picker = QComboBox()
        self.city_picker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.city_picker.setMinimumContentsLength(1)
        self.picker_col.addWidget(self.city_picker)

        self.region_picker = QComboBox()
        self.region_picker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.region_picker.setMinimumContentsLength(1)
        self.picker_col.addWidget(self.region_picker)

        fields_row2.addLayout(self.picker_col, 1)

        self.region_website_col = QVBoxLayout()
        self.region_website_label = QLabel("WEBSITE VALUE")
        self.region_website_label.setProperty("class", "field-label")
        self.region_website_input = QLineEdit()
        self.region_website_col.addWidget(self.region_website_label)
        self.region_website_col.addWidget(self.region_website_input)
        fields_row2.addLayout(self.region_website_col, 1)

        form_layout.addLayout(fields_row2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_add = QPushButton("Add")
        self.btn_update = QPushButton("Update")
        self.btn_delete = QPushButton("Delete")
        self.btn_clear = QPushButton("Clear")
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

        right_container.addWidget(form_card)

        filter_row = QHBoxLayout()
        filter_label = QLabel("SEARCH")
        filter_label.setProperty("class", "field-label")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter items in this category...")
        self.search_box.textChanged.connect(self.apply_filter)
        filter_row.addWidget(filter_label)
        filter_row.addWidget(self.search_box)
        right_container.addLayout(filter_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Value", "Value 2", "District", "Region (Website)"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.on_select_item)
        right_container.addWidget(self.table, 1)

        self.right_stack.addWidget(crud_page)  # index 0
        self.right_stack.addWidget(self._build_sync_page())  # index 1
        root.addWidget(self.right_stack, 1)

        self._sig_sync_log.connect(self.sync_output.append)
        self._sig_sync_done.connect(lambda: self.btn_run_sync.setEnabled(True))

        self.load_categories()

    # ── Sync ───────────────────────────────────────────────────────────
    def _build_sync_page(self):
        """Build the Sync panel: pick a field + source (Website/GForm), run
        sync_field() from sync_config_from_website.py on a background thread
        (it drives Selenium, which blocks), and stream its log output here."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        sync_card = QFrame()
        sync_card.setObjectName("card")
        sync_form = QVBoxLayout(sync_card)
        sync_form.setContentsMargins(10, 10, 10, 10)
        sync_form.setSpacing(4)

        info_label = QLabel(
            "Reads the real options from the live CRIMS website or Google Form and "
            "corrects the matching config value. Read-only against the site/form — "
            "requires Chrome already running with --remote-debugging-port=9222, "
            "logged in, and sitting on the page/step for the field below."
        )
        info_label.setWordWrap(True)
        sync_form.addWidget(info_label)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(6)

        field_col = QVBoxLayout()
        field_label = QLabel("FIELD")
        field_label.setProperty("class", "field-label")
        self.sync_field_picker = QComboBox()
        self.sync_field_picker.addItems(list(FIELD_SYNC_TARGETS.keys()))
        self.sync_field_picker.currentTextChanged.connect(self._update_sync_field_options)
        field_col.addWidget(field_label)
        field_col.addWidget(self.sync_field_picker)
        fields_row.addLayout(field_col, 1)

        source_col = QVBoxLayout()
        source_label = QLabel("SOURCE")
        source_label.setProperty("class", "field-label")
        self.sync_source_picker = QComboBox()
        source_col.addWidget(source_label)
        source_col.addWidget(self.sync_source_picker)
        fields_row.addLayout(source_col, 1)

        self.sync_city_col = QVBoxLayout()
        self.sync_city_label = QLabel("CITY")
        self.sync_city_label.setProperty("class", "field-label")
        self.sync_city_picker = QComboBox()
        self.sync_city_col.addWidget(self.sync_city_label)
        self.sync_city_col.addWidget(self.sync_city_picker)
        fields_row.addLayout(self.sync_city_col, 1)

        sync_form.addLayout(fields_row)

        btn_row = QHBoxLayout()
        self.btn_run_sync = QPushButton("Run Sync")
        self.btn_run_sync.clicked.connect(self.on_run_sync)
        btn_row.addWidget(self.btn_run_sync)
        self.sync_add_missing = QCheckBox("Also add missing records")
        btn_row.addWidget(self.sync_add_missing)
        btn_row.addStretch()
        sync_form.addLayout(btn_row)

        layout.addWidget(sync_card)

        self.sync_output = QTextEdit()
        self.sync_output.setReadOnly(True)
        layout.addWidget(self.sync_output, 1)

        self._update_sync_field_options(self.sync_field_picker.currentText())
        return page

    def _update_sync_field_options(self, field_id):
        self.sync_source_picker.clear()
        self.sync_source_picker.addItem("Website")
        if field_id in GFORM_SYNC_TARGETS:
            self.sync_source_picker.addItem("GForm")

        is_barangay = field_id == "barangay"
        self.sync_city_label.setVisible(is_barangay)
        self.sync_city_picker.setVisible(is_barangay)
        if is_barangay:
            self._populate_sync_city_picker()

    def _populate_sync_city_picker(self):
        self.sync_city_picker.clear()
        for list_id, key, label, kind, col1_label, col2_label in get_all_lists():
            if key == "list_of_city":
                for _item_id, col1, _col2, _extra, _extra2 in get_items(list_id):
                    self.sync_city_picker.addItem(col1)
                break

    def on_run_sync(self):
        field_id = self.sync_field_picker.currentText()
        source = "gform" if self.sync_source_picker.currentText() == "GForm" else "website"
        add_missing = self.sync_add_missing.isChecked()
        city = self.sync_city_picker.currentText() if self.sync_city_picker.isVisible() else None

        self.sync_output.clear()
        self.btn_run_sync.setEnabled(False)
        self._sig_sync_log.emit(
            f"Running sync for {field_id!r} (source={source}, add_missing={add_missing}, city={city!r})..."
        )

        def task():
            try:
                sync_field(field_id, source=source, log=self._sig_sync_log.emit, add_missing=add_missing, city=city)
            except Exception as e:
                self._sig_sync_log.emit(f"Error: {e}")
            finally:
                self._sig_sync_done.emit()

        threading.Thread(target=task, daemon=True).start()

    # ── Categories ─────────────────────────────────────────────────────
    def load_categories(self):
        self.lists = get_all_lists()
        self.category_list.clear()
        self.category_rows = []  # QListWidget row -> index into self.lists (None for group headers)

        personal_indices = sorted(
            (i for i, row in enumerate(self.lists) if row[1] in PERSONAL_GROUP_ORDER),
            key=lambda i: PERSONAL_GROUP_ORDER[self.lists[i][1]],
        )
        address_indices = sorted(
            (i for i, row in enumerate(self.lists) if row[1] in ADDRESS_GROUP_ORDER),
            key=lambda i: ADDRESS_GROUP_ORDER[self.lists[i][1]],
        )
        assistance_indices = [
            i for i, row in enumerate(self.lists)
            if row[1] not in PERSONAL_GROUP_ORDER and row[1] not in ADDRESS_GROUP_ORDER
        ]

        if personal_indices:
            self._add_category_header("Personal")
            self.category_rows.append(None)
            for idx in personal_indices:
                self.category_list.addItem(self.lists[idx][2])
                self.category_rows.append(idx)

        if assistance_indices:
            self._add_category_header("Assistance")
            self.category_rows.append(None)
            for idx in assistance_indices:
                self.category_list.addItem(self.lists[idx][2])
                self.category_rows.append(idx)

        if address_indices:
            self._add_category_header("Address")
            self.category_rows.append(None)
            for idx in address_indices:
                self.category_list.addItem(self.lists[idx][2])
                self.category_rows.append(idx)

        self._add_category_header("Tools")
        self.category_rows.append(None)
        self.category_list.addItem("Sync")
        self.category_rows.append(SYNC_ROW)

        self._select_first_selectable_row()

    def _add_category_header(self, text):
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.category_list.addItem(item)

    def _select_first_selectable_row(self):
        for row, idx in enumerate(self.category_rows):
            if idx is not None:
                self.category_list.setCurrentRow(row)
                return

    def on_select_category(self, row):
        if row < 0 or row >= len(self.category_rows) or self.category_rows[row] is None:
            return
        if self.category_rows[row] == SYNC_ROW:
            self.current_list = None
            self.right_stack.setCurrentIndex(1)
            return
        self.right_stack.setCurrentIndex(0)
        list_id, key, label, kind, col1_label, col2_label = self.lists[self.category_rows[row]]
        self.current_list = {
            "id": list_id, "key": key, "label": label, "kind": kind,
            "col1_label": col1_label, "col2_label": col2_label,
        }

        is_cities = kind == "cities"
        is_barangays = kind == "barangays"
        is_provinces = kind == "provinces"
        is_dual_value = kind in ("cities", "dual_pairs", "provinces", "barangays")

        col2_visible = col2_label is not None
        col2_header = col2_label or "Value 2"
        website_header = "Website Value"

        self.col1_label.setText(col1_label.upper())
        self.col2_label.setText(col2_header.upper())
        self.col2_input.setVisible(col2_visible)
        self.col2_label.setVisible(col2_visible)

        self.region_website_label.setText(website_header.upper())
        self.region_website_input.setVisible(is_dual_value)
        self.region_website_label.setVisible(is_dual_value)

        extra_header = "Province" if is_cities else ("City" if is_barangays else ("Region" if is_provinces else ""))
        has_picker = is_cities or is_barangays or is_provinces

        self.city_picker.setVisible(is_barangays)
        if is_barangays:
            self._populate_city_picker()

        self.region_picker.setVisible(is_provinces)
        if is_provinces:
            self._populate_region_picker()

        self.province_picker.setVisible(is_cities)
        if is_cities:
            self._populate_province_picker()

        self.picker_label.setText(extra_header.upper())
        self.picker_label.setVisible(has_picker)

        # Cities: Province (the link column) goes last, after Website Value.
        # Every other kind keeps link-then-website.
        self.extra_col, self.extra2_col = (4, 3) if is_cities else (3, 4)
        headers = ["ID", col1_label, col2_header, "", ""]
        headers[self.extra_col] = extra_header
        headers[self.extra2_col] = website_header
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setColumnHidden(2, not col2_visible)
        self.table.setColumnHidden(self.extra_col, not has_picker)
        self.table.setColumnHidden(self.extra2_col, not is_dual_value)

        self.clear_form()
        self.load_items()

    def _populate_city_picker(self):
        self.city_picker.clear()
        for list_id, key, label, kind, col1_label, col2_label in self.lists:
            if key == "list_of_city":
                for item_id, col1, _col2, _extra, _extra2 in get_items(list_id):
                    self.city_picker.addItem(col1, str(item_id))
                break

    def _city_labels_by_id(self):
        """{city config_items.id (as str): city label}, used to display barangay->city
        links (stored by id) as readable text in the items table."""
        labels_by_id = {}
        for list_id, key, label, kind, col1_label, col2_label in self.lists:
            if key == "list_of_city":
                for item_id, col1, _col2, _extra, _extra2 in get_items(list_id):
                    labels_by_id[str(item_id)] = col1
                break
        return labels_by_id

    def _populate_region_picker(self):
        self.region_picker.clear()
        for list_id, key, label, kind, col1_label, col2_label in self.lists:
            if key == "region_list":
                for item_id, col1, _col2, _extra, _extra2 in get_items(list_id):
                    self.region_picker.addItem(col1, str(item_id))
                break

    def _region_labels_by_id(self):
        """{region config_items.id (as str): region label}, used to display province->region
        links (stored by id) as readable text in the items table."""
        labels_by_id = {}
        for list_id, key, label, kind, col1_label, col2_label in self.lists:
            if key == "region_list":
                for item_id, col1, _col2, _extra, _extra2 in get_items(list_id):
                    labels_by_id[str(item_id)] = col1
                break
        return labels_by_id

    def _populate_province_picker(self):
        self.province_picker.clear()
        for list_id, key, label, kind, col1_label, col2_label in self.lists:
            if key == "province_list":
                for item_id, col1, _col2, _extra, _extra2 in get_items(list_id):
                    self.province_picker.addItem(col1, str(item_id))
                break

    def _province_labels_by_id(self):
        """{province config_items.id (as str): province label}, used to display city->province
        links (stored by id) as readable text in the items table."""
        labels_by_id = {}
        for list_id, key, label, kind, col1_label, col2_label in self.lists:
            if key == "province_list":
                for item_id, col1, _col2, _extra, _extra2 in get_items(list_id):
                    labels_by_id[str(item_id)] = col1
                break
        return labels_by_id

    # ── Items ──────────────────────────────────────────────────────────
    def load_items(self):
        self.row_data.clear()
        self.table.setRowCount(0)
        if not self.current_list:
            return
        is_provinces = self.current_list["kind"] == "provinces"
        is_cities = self.current_list["kind"] == "cities"
        is_barangays = self.current_list["kind"] == "barangays"
        region_labels_by_id = self._region_labels_by_id() if is_provinces else {}
        province_labels_by_id = self._province_labels_by_id() if is_cities else {}
        city_labels_by_id = self._city_labels_by_id() if is_barangays else {}
        for item_id, col1, col2, extra, extra2 in get_items(self.current_list["id"]):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(item_id)))
            self.table.setItem(r, 1, QTableWidgetItem(col1 or ""))
            self.table.setItem(r, 2, QTableWidgetItem(col2 or ""))
            if is_provinces:
                extra_display = region_labels_by_id.get(extra, extra or "")
            elif is_cities:
                extra_display = province_labels_by_id.get(extra, extra or "")
            elif is_barangays:
                extra_display = city_labels_by_id.get(extra, extra or "")
            else:
                extra_display = extra or ""
            self.table.setItem(r, self.extra_col, QTableWidgetItem(extra_display))
            self.table.setItem(r, self.extra2_col, QTableWidgetItem(extra2 or ""))
            self.row_data[item_id] = {"col1": col1, "col2": col2, "extra": extra, "extra2": extra2}
        self.apply_filter(self.search_box.text())

    def apply_filter(self, text):
        needle = text.strip().lower()
        for r in range(self.table.rowCount()):
            if not needle:
                self.table.setRowHidden(r, False)
                continue
            haystack = " ".join(
                self.table.item(r, c).text().lower() for c in (1, 2, 3, 4)
            )
            self.table.setRowHidden(r, needle not in haystack)

    def on_select_item(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = self.table.currentRow()
        item_id = int(self.table.item(row, 0).text())
        item = self.row_data.get(item_id)
        if item:
            self.selected_item_id = item_id
            self.col1_input.setText(item["col1"] or "")
            self.col2_input.setText(item["col2"] or "")
            self.region_website_input.setText(item["extra2"] or "")
            if self.current_list and self.current_list["kind"] == "barangays":
                self.city_picker.setCurrentIndex(self.city_picker.findData(item["extra"]))
            if self.current_list and self.current_list["kind"] == "provinces":
                self.region_picker.setCurrentIndex(self.region_picker.findData(item["extra"]))
            if self.current_list and self.current_list["kind"] == "cities":
                self.province_picker.setCurrentIndex(self.province_picker.findData(item["extra"]))

    def clear_form(self):
        self.selected_item_id = None
        self.col1_input.clear()
        self.col2_input.clear()
        self.region_website_input.clear()
        self.city_picker.setCurrentIndex(-1)
        self.region_picker.setCurrentIndex(-1)
        self.province_picker.setCurrentIndex(-1)
        self.table.clearSelection()

    def _col2_value(self):
        if not self.current_list:
            return None
        if self.current_list["col2_label"]:
            return self.col2_input.text()
        return None

    def _extra_value(self):
        if not self.current_list:
            return None
        if self.current_list["kind"] == "cities":
            return self.province_picker.currentData()
        if self.current_list["kind"] == "barangays":
            return self.city_picker.currentData()
        if self.current_list["kind"] == "provinces":
            return self.region_picker.currentData()
        return None

    def _extra2_value(self):
        if self.current_list and self.current_list["kind"] in ("cities", "dual_pairs", "provinces", "barangays"):
            return self.region_website_input.text()
        return None

    def on_add(self):
        if not self.current_list:
            return
        if not self.col1_input.text().strip():
            QMessageBox.information(self, "Add", f"{self.current_list['col1_label']} is required.")
            return
        reply = QMessageBox.question(
            self, "Add", "Are you sure you want to add this item?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            insert_item(
                self.current_list["id"], self.col1_input.text(), self._col2_value(),
                self._extra_value(), self._extra2_value(),
            )
            self.clear_form()
            self.load_items()

    def on_update(self):
        if not self.selected_item_id:
            QMessageBox.information(self, "Update", "Select a record from the table first.")
            return
        reply = QMessageBox.question(
            self, "Update", "Are you sure you want to update this item?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            update_item(
                self.selected_item_id, self.col1_input.text(), self._col2_value(),
                self._extra_value(), self._extra2_value(),
            )
            self.clear_form()
            self.load_items()

    def on_delete(self):
        if not self.selected_item_id:
            QMessageBox.information(self, "Delete", "Select a record from the table first.")
            return
        reply = QMessageBox.question(
            self, "Delete", "Are you sure you want to delete this item?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_item(self.selected_item_id)
            self.clear_form()
            self.load_items()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db_config()
    seed_from_config_if_empty()
    backfill_city_regions()
    migrate_gender_to_pairs()
    migrate_target_sector_to_pairs()
    migrate_mode_of_release_to_pairs()
    migrate_financial_assistance_to_pairs()
    migrate_civil_status_to_pairs()
    migrate_fund_source_to_pairs()
    migrate_relationship_to_pairs()
    migrate_client_sub_category_to_pairs()
    migrate_target_sector_to_dual_pairs()
    migrate_approved_by_to_dual_pairs()
    migrate_region_to_dual_pairs()
    migrate_province_region_link_to_id()
    migrate_city_province_link_to_id()
    migrate_barangay_city_link_to_id()
    migrate_province_to_dual_pairs()
    migrate_city_to_dual_pairs()
    migrate_barangay_to_dual_pairs()
    migrate_gender_to_dual_pairs()
    migrate_civil_status_to_dual_pairs()
    migrate_fund_source_to_dual_pairs()
    migrate_mode_of_release_to_dual_pairs()
    migrate_financial_assistance_to_dual_pairs()
    migrate_relationship_to_dual_pairs()
    migrate_client_sub_category_to_dual_pairs()
    remove_approver_list()
    window = ConfigManagerWindow()
    window.show()
    sys.exit(app.exec())
