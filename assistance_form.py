import sys
import time
import threading
import os
import pickle
import csv
import random
import sqlite3
import traceback

from selenium.webdriver.common.alert import Alert
from datetime import datetime
from selenium import webdriver
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, QTabWidget,
    QScrollArea, QTableWidget, QTableWidgetItem, QTextEdit, QFrame,
    QMessageBox, QSizePolicy, QHeaderView,
)
from PySide6.QtCore import Qt, QDate, Signal, QObject, QTimer
from PySide6.QtGui import QColor, QFont, QCursor

from ui.widgets import AllCapsLineEdit, NoScrollComboBox, set_table_visible_rows, set_textedit_visible_rows

from ui.styles import STYLESHEET

from core.utilities import is_similar
from core.utilities import get_date_value
from core.utilities import disable_mousewheel
from core.utilities import set_date_value

from db.person_store import init_db_person, DB_NAME
from db.person_store import get_all_person_by_encoded
from db.person_store import set_encoded
from db.person_store import insert_person, update_person, delete_person_by_id

from db.worker_store import init_db_worker
from db.worker_store import get_all_workers, get_worker_by_full_name

from db.config_store import init_db_config, seed_from_config_if_empty, run_startup_config_migrations
from db.config_store import get_all_lists, get_items

from core.config import mov_url
from core.config import offline_url
from core.config import website_url
from core.config import list_of_city
from core.paths import FORM_CACHE_FILE_PATH, CRASH_LOG_FILE_PATH

from core.license import is_trial_valid, activate_trial, get_device_id
import winsound
import keyboard

# Backward-compatible aliases within this file
AllCapsTextCtrl = AllCapsLineEdit
AllTextCtrl = QLineEdit


def _log_crash(exc_type, exc_value, exc_tb):
    message = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        with open(CRASH_LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now().isoformat()} ---\n{message}")
    except Exception:
        pass
    print(message, file=sys.stderr)


def install_crash_logging():
    """The --windowed build has no console, so an unhandled exception in the
    main thread or the background automation thread (started via
    threading.Thread in on_button_click) would otherwise vanish silently --
    a button click that appears to do nothing, with no error and no log
    line. Route both to crash.log next to the exe so the real cause is
    visible instead of invisible."""
    sys.excepthook = _log_crash

    def _thread_excepthook(args):
        _log_crash(args.exc_type, args.exc_value, args.exc_traceback)

    threading.excepthook = _thread_excepthook


# Initialize SQLite database
def init_db():
    init_db_person()
    init_db_worker()
    init_db_config()
    seed_from_config_if_empty()
    run_startup_config_migrations()

def export_sqlite_to_csv(db_path, table_name, csv_path):
    """
    Exports records from a SQLite database table into a CSV file.
    """
    # Basic validation to avoid SQL injection via table_name
    import re

    if not re.match(r"^[A-Za-z0-9_]+$", table_name):
        raise ValueError("Invalid table name")

    # Ensure output directory exists
    out_dir = os.path.dirname(csv_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # table_name is validated, safe to format into SQL
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        column_names = [description[0] for description in cursor.description]

        with open(csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(column_names)
            writer.writerows(rows)

    except sqlite3.Error as e:
        raise e  # Let the caller handle errors
    finally:
        conn.close()


class MyFrame(QMainWindow):
    row_data = {}  # ID -> full data

    # Thread-safe UI signals
    _sig_log = Signal(str)
    _sig_set_running = Signal(bool)
    _sig_reload_person = Signal()
    _sig_select_first = Signal()
    _sig_msg_box = Signal(str, str, str)  # title, message, kind (info/error)

    def _format_table_date(self, value):
        if not value:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%m/%d/%Y")
        if isinstance(value, str):
            for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(value, pattern).strftime("%m/%d/%Y")
                except ValueError:
                    continue
        return str(value)

    def _table_foreground_for_background(self, background_color):
        """Return a readable text color for a given row background."""
        luminance = (
            0.299 * background_color.red()
            + 0.587 * background_color.green()
            + 0.114 * background_color.blue()
        )
        return QColor(255, 255, 255) if luminance < 140 else QColor(0, 0, 0)

    def load_data_person(self):
        is_encoded = "1" if self.cb_encoded.isChecked() else "0"
        selected_row = self.list_ctrl.currentRow()
        sorting_was_enabled = self.list_ctrl.isSortingEnabled()
        self.list_ctrl.setSortingEnabled(False)
        self.list_ctrl.setRowCount(0)
        self.row_data.clear()
        sw_column_index = 7
        assist_map = {0: "Medical", 1: "Burial", 2: "Transportation", 3: "Cash Support", 4: "Food"}

        try:
            for row in get_all_person_by_encoded(is_encoded):
                assist = assist_map.get(row[4], "")
                bday = self._format_table_date(row[17])
                r = self.list_ctrl.rowCount()
                self.list_ctrl.insertRow(r)
                for col, val in enumerate([
                    str(row[0]), row[12], str(row[13]), str(row[14]), str(row[15]),
                    bday, str(row[18]), assist, str(row[5]), str(row[7]), str(row[38])
                ]):
                    item = QTableWidgetItem(val)
                    if col == 5:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setForeground(QColor(15, 23, 42))
                    item.setBackground(QColor(255, 255, 255))
                    self.list_ctrl.setItem(r, col, item)

                # Strong visual warning only for rows that need attention.
                if row[40] == 1:
                    warning_bg = QColor(220, 38, 38)
                    warning_fg = QColor(255, 255, 255)
                    for col in range(self.list_ctrl.columnCount()):
                        item = self.list_ctrl.item(r, col)
                        item.setBackground(warning_bg)
                        item.setForeground(warning_fg)
                for col in range(self.list_ctrl.columnCount()):
                    item = self.list_ctrl.item(r, col)
                    item.setFont(self.list_ctrl.font())

                self.row_data[row[0]] = {
                "id": row[0], "encoder_name": row[1], "date_encoded": row[2],
                "target_sector": row[3], "financial_assist": row[4], "amount": row[5],
                "fund_source": row[6], "sw_full_name": row[7],
                "interview_date": row[10], "client_relationship": row[11],
                "client_lastname": row[12], "client_firstname": row[13], "client_middlename": row[14],
                "client_ext": row[15], "client_gender": row[16], "client_bday": row[17],
                "client_age": row[18], "client_contact_no": row[19], "client_civil_status": row[20],
                "client_house_street": row[21], "client_barangay": row[22], "client_city": row[23],
                "bene_relationship": row[24], "bene_lastname": row[25], "bene_firstname": row[26],
                "bene_middlename": row[27], "bene_ext": row[28], "bene_gender": row[29],
                "bene_bday": row[30], "bene_age": row[31], "bene_contact_no": row[32],
                "bene_civil_status": row[33], "bene_house_street": row[34], "bene_barangay": row[35],
                "bene_city": row[36], "has_beneficiary": row[37], "encoded": row[38],
                "target_sector_bene": row[39], "mode_release": row[40], "approved_by": row[41],
                "sub_category": row[42],
                    "client_region": row[43], "client_province": row[44],
                    "bene_region": row[45], "bene_province": row[46],
                }
        finally:
            self.list_ctrl.setSortingEnabled(sorting_was_enabled)

        if 0 <= selected_row < self.list_ctrl.rowCount():
            self.list_ctrl.selectRow(selected_row)

        self.list_ctrl.resizeColumnsToContents()
        self.list_ctrl.resizeRowsToContents()
        self.list_ctrl.horizontalHeader().setStretchLastSection(True)

    def select_first_item(self):
        if self.list_ctrl.rowCount() > 0:
            self.list_ctrl.selectRow(0)

    def on_add_person(self, event=None):
        reply = QMessageBox.question(self, "Add Person", "Are you sure you want to add?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if insert_person(
                self.encoder_name.text(),
                get_date_value(self.encoded_date),
                self.target_sector.currentIndex(),
                self.target_sector_bene.currentIndex(),
                self.financial_assist.currentIndex(),
                self.amount.text(),
                self.fund_source.currentIndex(),
                self.social_worker.currentText(), "", "",
                get_date_value(self.interview_date),
                self.client_relationship.currentIndex(),
                self.client_lastname.text(), self.client_firstname.text(),
                self.client_middlename.text(), self.client_ext.text(),
                self.client_gender.currentIndex(),
                get_date_value(self.client_bday), self.client_age.text(),
                self.client_contact_no.text(),
                self.client_civil_status.currentIndex(),
                self.client_house_street.text(), self.client_barangay.currentText(),
                self.client_city.currentText(),
                self.bene_relationship.currentIndex(),
                self.bene_lastname.text(), self.bene_firstname.text(),
                self.bene_middlename.text(), self.bene_ext.text(),
                self.bene_gender.currentIndex(),
                get_date_value(self.bene_bday), self.bene_age.text(),
                self.bene_contact_no.text(),
                self.bene_civil_status.currentIndex(),
                self.bene_house_street.text(), self.bene_barangay.currentText(),
                self.bene_city.currentText(),
                self.has_beneficiary.isChecked(),
                self.mode_release.currentIndex(),
                self.approved_by.currentIndex(),
                self.sub_category.currentIndex(),
                self.client_region.currentText(), self.client_province.currentText(),
                self.bene_region.currentText(), self.bene_province.currentText(),
            ):
                self.load_data_person()
                self.on_clear(None)
            else:
                QMessageBox.critical(self, "Error", "Record already exist.")
        QTimer.singleShot(0, self.client_lastname.setFocus)

    def on_update_person(self, event=None):
        reply = QMessageBox.question(self, "Update", "Are you sure you want to update?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.selected_person_id:
                update_person(
                    self.selected_person_id,
                    self.encoder_name.text(),
                    get_date_value(self.encoded_date),
                    self.target_sector_bene.currentIndex(),
                    self.target_sector.currentIndex(),
                    self.financial_assist.currentIndex(),
                    self.amount.text(),
                    self.fund_source.currentIndex(),
                    self.social_worker.currentText(), "", "",
                    get_date_value(self.interview_date),
                    self.client_relationship.currentIndex(),
                    self.client_lastname.text(), self.client_firstname.text(),
                    self.client_middlename.text(), self.client_ext.text(),
                    self.client_gender.currentIndex(),
                    get_date_value(self.client_bday), self.client_age.text(),
                    self.client_contact_no.text(),
                    self.client_civil_status.currentIndex(),
                    self.client_house_street.text(), self.client_barangay.currentText(),
                    self.client_city.currentText(),
                    self.bene_relationship.currentIndex(),
                    self.bene_lastname.text(), self.bene_firstname.text(),
                    self.bene_middlename.text(), self.bene_ext.text(),
                    self.bene_gender.currentIndex(),
                    get_date_value(self.bene_bday), self.bene_age.text(),
                    self.bene_contact_no.text(),
                    self.bene_civil_status.currentIndex(),
                    self.bene_house_street.text(), self.bene_barangay.currentText(),
                    self.bene_city.currentText(),
                    self.has_beneficiary.isChecked(),
                    self.mode_release.currentIndex(),
                    self.approved_by.currentIndex(),
                    self.sub_category.currentIndex(),
                    self.client_region.currentText(), self.client_province.currentText(),
                    self.bene_region.currentText(), self.bene_province.currentText(),
                )
                self.load_data_person()
                self.on_clear(None)

    def on_delete_person(self, event=None):
        reply = QMessageBox.question(self, "Delete", "Are you sure you want to delete?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.selected_person_id:
                delete_person_by_id(self.selected_person_id)
                self.load_data_person()
                self.on_clear(None)

    def on_set_encoded(self, event=None):
        reply = QMessageBox.question(self, "Confirm Action", "Do you want to continue?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.selected_person_id:
                set_encoded(self.encode_id.text(), not self.cb_encoded.isChecked())
                self.load_data_person()
                self.select_first_item()

    def on_stop(self, event=None):
        self.stop_requested = True

    def on_auto_fill(self, event=None):
        self.is_auto_fill = True
        self.on_button_click()

    def on_clear(self, event=None):
        self.selected_person_id = None

    def on_select_person(self):
        selected = self.list_ctrl.selectedItems()
        if not selected:
            return
        row = self.list_ctrl.currentRow()
        person_id = int(self.list_ctrl.item(row, 0).text())
        if person_id not in self.row_data:
            return
        person = self.row_data[person_id]
        self.selected_person_id = person["id"]
        self.encode_id.setText(str(person["id"]))

        self.client_lastname.setText(person["client_lastname"])
        self.client_firstname.setText(person["client_firstname"])
        self.client_middlename.setText(person["client_middlename"])
        self.client_age.setText(str(person["client_age"]))
        self.client_ext.setText(person["client_ext"])
        self.client_relationship.setCurrentIndex(person["client_relationship"])
        self.client_gender.setCurrentIndex(person["client_gender"])
        self.client_civil_status.setCurrentIndex(person["client_civil_status"])
        set_date_value(self.client_bday, person["client_bday"])
        self.client_contact_no.setText(person["client_contact_no"])
        self.client_house_street.setText(person["client_house_street"])
        self.client_region.setCurrentText(person["client_region"])
        self.client_province.setCurrentText(person["client_province"])
        self.client_city.setCurrentText(person["client_city"])
        self.client_barangay.setCurrentText(person["client_barangay"])
        self.target_sector.setCurrentIndex(person["target_sector"])

        self.bene_lastname.setText(person["bene_lastname"])
        self.bene_firstname.setText(person["bene_firstname"])
        self.bene_middlename.setText(person["bene_middlename"])
        self.bene_age.setText(str(person["bene_age"]))
        self.bene_ext.setText(person["bene_ext"])
        self.bene_relationship.setCurrentIndex(person["bene_relationship"])
        self.bene_gender.setCurrentIndex(person["bene_gender"])
        self.bene_civil_status.setCurrentIndex(person["bene_civil_status"])
        set_date_value(self.bene_bday, person["bene_bday"])
        self.bene_contact_no.setText(person["bene_contact_no"])
        self.bene_house_street.setText(person["bene_house_street"])
        self.bene_region.setCurrentText(person["bene_region"])
        self.bene_province.setCurrentText(person["bene_province"])
        self.bene_city.setCurrentText(person["bene_city"])
        self.bene_barangay.setCurrentText(person["bene_barangay"])

        self.financial_assist.setCurrentIndex(person["financial_assist"])
        self.mode_release.setCurrentIndex(person["mode_release"])
        self.approved_by.setCurrentIndex(person["approved_by"])
        self.sub_category.setCurrentIndex(person["sub_category"])
        self.amount.setText(person["amount"])
        self.fund_source.setCurrentIndex(person["fund_source"])
        set_date_value(self.interview_date, person["interview_date"])
        self.has_beneficiary.setChecked(bool(person["has_beneficiary"]))

        try:
            self.social_worker.setCurrentIndex(self.social_worker_choices.index(person["sw_full_name"]))
        except ValueError:
            self.social_worker.setCurrentIndex(-1)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Client Assistance Form")
        self.resize(760, 760)
        self.setStyleSheet(STYLESHEET)

        self.selected_person_id = None
        self.driver = None
        self.is_running = False
        self.stop_requested = False
        self.is_auto_fill = False
        self.is_finished_refresh = False

        self._list_meta_by_key = {}
        self._items_by_key = {}
        self.reload_config_data()

        keyboard.add_hotkey('shift+enter', self.on_add_person)

        central = QWidget()
        self.setCentralWidget(central)
        self.sizer = QVBoxLayout(central)
        self.sizer.setContentsMargins(10, 10, 10, 10)
        self.sizer.setSpacing(6)

        # ── Scrollable area ──────────────────────────────────────────────
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.scroll_sizer = QVBoxLayout(scroll_widget)
        self.scroll_sizer.setContentsMargins(0, 0, 0, 0)
        scroll_area.setWidget(scroll_widget)

        # ── Tab Widget ───────────────────────────────────────────────────
        notebook = QTabWidget()

        client_panel = QWidget()
        bene_panel = QWidget()

        box_sizer_client = QVBoxLayout(client_panel)
        box_sizer_client.setContentsMargins(10, 10, 10, 10)
        box_sizer_client.setSpacing(4)
        box_sizer_bene = QVBoxLayout(bene_panel)
        box_sizer_bene.setContentsMargins(10, 10, 10, 10)
        box_sizer_bene.setSpacing(4)

        # ── Client Tab ───────────────────────────────────────────────────
        self.has_beneficiary = QCheckBox("Has Beneficiary")
        self.has_beneficiary.stateChanged.connect(self.has_beneficiary_event)
        box_sizer_client.addWidget(self.has_beneficiary)

        relationship_rows = self._get_list_rows("relationship_list")
        self.relationship_choices = [col2 for _id, col1, col2, extra, extra2 in relationship_rows]
        # GForm submission still reverse-looks-up to the Label (col1) for now, pending a
        # live-form check on whether GForm Value is actually the correct radio-button text.
        self.relationship_gform_map = {col2: col1 for _id, col1, col2, extra, extra2 in relationship_rows}
        # Website already correctly used the dropdown's own displayed text (col2); this map
        # makes that independently editable via Website Value instead of implicitly col2 itself.
        self.relationship_website_map = {col2: (extra2 or col2) for _id, col1, col2, extra, extra2 in relationship_rows}

        box_sizer_client.addWidget(QLabel("Relationship to bene:"))
        self.client_relationship = NoScrollComboBox()
        self.client_relationship.addItems(self.relationship_choices)
        box_sizer_client.addWidget(self.client_relationship)

        box_sizer_client.addWidget(QLabel("Fullname:"))
        cl_fullname_sizer = QHBoxLayout()
        self.client_lastname = AllCapsLineEdit()
        self.client_lastname.setPlaceholderText("Lastname")
        self.client_firstname = AllCapsLineEdit()
        self.client_firstname.setPlaceholderText("Firstname")
        self.client_middlename = AllCapsLineEdit()
        self.client_middlename.setPlaceholderText("Middlename")
        self.client_ext = AllCapsLineEdit()
        self.client_ext.setPlaceholderText("Ext")
        self.client_ext.setFixedWidth(50)
        cl_fullname_sizer.addWidget(self.client_lastname)
        cl_fullname_sizer.addWidget(self.client_firstname)
        cl_fullname_sizer.addWidget(self.client_middlename)
        cl_fullname_sizer.addWidget(self.client_ext)
        box_sizer_client.addLayout(cl_fullname_sizer)

        cl_gender_civil = QHBoxLayout()
        cl_gender_col = QVBoxLayout()
        cl_gender_col.addWidget(QLabel("Gender"))
        gender_rows = self._get_list_rows("gender_list")
        self.gender_options = [col1 for _id, col1, col2, extra, extra2 in gender_rows]
        self.gender_gform_map = {col1: (col2 or col1) for _id, col1, col2, extra, extra2 in gender_rows}
        self.gender_website_map = {col1: (extra2 or col1) for _id, col1, col2, extra, extra2 in gender_rows}
        self.client_gender = NoScrollComboBox()
        self.client_gender.addItems(self.gender_options)
        self.client_gender.setCurrentIndex(0)
        self.client_gender.currentIndexChanged.connect(self.on_choice_change_client)
        cl_gender_col.addWidget(self.client_gender)
        cl_gender_civil.addLayout(cl_gender_col)

        civil_status_rows = self._get_list_rows("civil_status_list")
        self.civil_status_choices = [col1 for _id, col1, col2, extra, extra2 in civil_status_rows]
        self.civil_status_gform_map = {col1: (col2 or col1) for _id, col1, col2, extra, extra2 in civil_status_rows}
        self.civil_status_website_map = {col1: (extra2 or col1) for _id, col1, col2, extra, extra2 in civil_status_rows}
        cl_civil_col = QVBoxLayout()
        cl_civil_col.addWidget(QLabel("Civil Status"))
        self.client_civil_status = NoScrollComboBox()
        self.client_civil_status.addItems(self.civil_status_choices)
        self.client_civil_status.currentIndexChanged.connect(self.on_selection)
        cl_civil_col.addWidget(self.client_civil_status)
        cl_gender_civil.addLayout(cl_civil_col)
        box_sizer_client.addLayout(cl_gender_civil)

        from PySide6.QtWidgets import QDateEdit
        box_sizer_client.addWidget(QLabel("Birthday:"))
        self.client_bday = QDateEdit()
        self.client_bday.setCalendarPopup(True)
        self.client_bday.setDate(QDate.currentDate())
        self.client_bday.dateChanged.connect(self.c_compute_age)
        box_sizer_client.addWidget(self.client_bday)

        box_sizer_client.addWidget(QLabel("Age:"))
        self.client_age = AllCapsLineEdit()
        box_sizer_client.addWidget(self.client_age)

        box_sizer_client.addWidget(QLabel("Contact No:"))
        self.client_contact_no = AllCapsLineEdit()
        box_sizer_client.addWidget(self.client_contact_no)

        cl_address_row1 = QHBoxLayout()
        cl_region_col = QVBoxLayout()
        cl_region_col.addWidget(QLabel("Region"))
        self.client_region = NoScrollComboBox()
        self.client_region.addItems(self.region_options)
        cl_region_col.addWidget(self.client_region)
        cl_address_row1.addLayout(cl_region_col)

        cl_province_col = QVBoxLayout()
        cl_province_col.addWidget(QLabel("Province"))
        self.client_province = NoScrollComboBox()
        self.client_province.addItems(self.provinces_by_region.get(self.client_region.currentText(), []))
        cl_province_col.addWidget(self.client_province)
        cl_address_row1.addLayout(cl_province_col)

        self.client_region.currentIndexChanged.connect(self.on_client_region_changed)
        self.client_province.currentIndexChanged.connect(self.on_client_province_changed)

        cl_city_col = QVBoxLayout()
        cl_city_col.addWidget(QLabel("City | Municipality"))
        self.client_city = NoScrollComboBox()
        self.client_city.addItems(self.cities_by_province.get(self.client_province.currentText(), []))
        self.client_city.currentIndexChanged.connect(self.on_client_city_changed)
        cl_city_col.addWidget(self.client_city)
        cl_address_row1.addLayout(cl_city_col)
        box_sizer_client.addLayout(cl_address_row1)

        cl_address_row2 = QHBoxLayout()
        cl_house_col = QVBoxLayout()
        cl_house_col.addWidget(QLabel("House | Street No:"))
        self.client_house_street = AllCapsLineEdit()
        cl_house_col.addWidget(self.client_house_street)
        cl_address_row2.addLayout(cl_house_col, 6)

        cl_brgy_col = QVBoxLayout()
        cl_brgy_col.addWidget(QLabel("Barangay"))
        self.client_barangay = NoScrollComboBox()
        self.client_barangay.setEditable(True)
        cl_brgy_col.addWidget(self.client_barangay)
        cl_address_row2.addLayout(cl_brgy_col, 4)
        box_sizer_client.addLayout(cl_address_row2)

        target_sector_rows = self._get_list_rows("target_sector_list")
        self.target_sector_options = [col1 for _id, col1, col2, extra, extra2 in target_sector_rows]
        self.target_sector_gform_map = {col1: (col2 or col1) for _id, col1, col2, extra, extra2 in target_sector_rows}
        self.target_sector_website_map = {col1: (extra2 or col1) for _id, col1, col2, extra, extra2 in target_sector_rows}

        box_sizer_client.addWidget(QLabel("Target Sector"))
        self.target_sector = NoScrollComboBox()
        self.target_sector.addItems(self.target_sector_options)
        self.target_sector.setCurrentIndex(0)
        box_sizer_client.addWidget(self.target_sector)

        notebook.addTab(client_panel, "Client Information")

        # ── Beneficiary Tab ──────────────────────────────────────────────
        helper_sizer = QHBoxLayout()
        self.same_address = QCheckBox("Same Address")
        self.same_address.stateChanged.connect(self.same_address_event)
        self.same_contact = QCheckBox("Same Contact No.")
        self.same_contact.stateChanged.connect(self.same_contact_event)
        helper_sizer.addWidget(self.same_address)
        helper_sizer.addWidget(self.same_contact)
        box_sizer_bene.addLayout(helper_sizer)

        box_sizer_bene.addWidget(QLabel("Relationship to bene:"))
        self.bene_relationship = NoScrollComboBox()
        self.bene_relationship.addItems(self.relationship_choices)
        self.bene_relationship.setCurrentIndex(0)
        box_sizer_bene.addWidget(self.bene_relationship)

        box_sizer_bene.addWidget(QLabel("Fullname:"))
        bene_fullname_sizer = QHBoxLayout()
        self.bene_lastname = AllCapsLineEdit()
        self.bene_lastname.setPlaceholderText("Lastname")
        self.bene_firstname = AllCapsLineEdit()
        self.bene_firstname.setPlaceholderText("Firstname")
        self.bene_middlename = AllCapsLineEdit()
        self.bene_middlename.setPlaceholderText("Middlename")
        self.bene_ext = AllCapsLineEdit()
        self.bene_ext.setPlaceholderText("Ext")
        self.bene_ext.setFixedWidth(50)
        bene_fullname_sizer.addWidget(self.bene_lastname)
        bene_fullname_sizer.addWidget(self.bene_firstname)
        bene_fullname_sizer.addWidget(self.bene_middlename)
        bene_fullname_sizer.addWidget(self.bene_ext)
        box_sizer_bene.addLayout(bene_fullname_sizer)

        bene_gender_civil = QHBoxLayout()
        bene_gender_col = QVBoxLayout()
        bene_gender_col.addWidget(QLabel("Gender"))
        self.bene_gender = NoScrollComboBox()
        self.bene_gender.addItems(self.gender_options)
        self.bene_gender.setCurrentIndex(0)
        self.bene_gender.currentIndexChanged.connect(self.on_choice_change_bene)
        bene_gender_col.addWidget(self.bene_gender)
        bene_gender_civil.addLayout(bene_gender_col)

        bene_civil_col = QVBoxLayout()
        bene_civil_col.addWidget(QLabel("Civil Status"))
        self.bene_civil_status = NoScrollComboBox()
        self.bene_civil_status.addItems(self.civil_status_choices)
        bene_civil_col.addWidget(self.bene_civil_status)
        bene_gender_civil.addLayout(bene_civil_col)
        box_sizer_bene.addLayout(bene_gender_civil)

        box_sizer_bene.addWidget(QLabel("Birthday:"))
        self.bene_bday = QDateEdit()
        self.bene_bday.setCalendarPopup(True)
        self.bene_bday.setDate(QDate.currentDate())
        self.bene_bday.dateChanged.connect(self.b_compute_age)
        box_sizer_bene.addWidget(self.bene_bday)

        box_sizer_bene.addWidget(QLabel("Age:"))
        self.bene_age = AllCapsLineEdit()
        box_sizer_bene.addWidget(self.bene_age)

        box_sizer_bene.addWidget(QLabel("Contact No:"))
        self.bene_contact_no = AllCapsLineEdit()
        box_sizer_bene.addWidget(self.bene_contact_no)

        bene_address_row1 = QHBoxLayout()
        bene_region_col = QVBoxLayout()
        bene_region_col.addWidget(QLabel("Region"))
        self.bene_region = NoScrollComboBox()
        self.bene_region.addItems(self.region_options)
        bene_region_col.addWidget(self.bene_region)
        bene_address_row1.addLayout(bene_region_col)

        bene_province_col = QVBoxLayout()
        bene_province_col.addWidget(QLabel("Province"))
        self.bene_province = NoScrollComboBox()
        self.bene_province.addItems(self.provinces_by_region.get(self.bene_region.currentText(), []))
        bene_province_col.addWidget(self.bene_province)
        bene_address_row1.addLayout(bene_province_col)

        self.bene_region.currentIndexChanged.connect(self.on_bene_region_changed)
        self.bene_province.currentIndexChanged.connect(self.on_bene_province_changed)

        bene_city_col = QVBoxLayout()
        bene_city_col.addWidget(QLabel("City | Municipality"))
        self.bene_city = NoScrollComboBox()
        self.bene_city.addItems(self.cities_by_province.get(self.bene_province.currentText(), []))
        self.bene_city.currentIndexChanged.connect(self.on_bene_city_changed)
        bene_city_col.addWidget(self.bene_city)
        bene_address_row1.addLayout(bene_city_col)
        box_sizer_bene.addLayout(bene_address_row1)

        bene_address_row2 = QHBoxLayout()
        bene_house_col = QVBoxLayout()
        bene_house_col.addWidget(QLabel("House | Street No:"))
        self.bene_house_street = AllCapsLineEdit()
        bene_house_col.addWidget(self.bene_house_street)
        bene_address_row2.addLayout(bene_house_col, 6)

        bene_brgy_col = QVBoxLayout()
        bene_brgy_col.addWidget(QLabel("Barangay"))
        self.bene_barangay = NoScrollComboBox()
        self.bene_barangay.setEditable(True)
        bene_brgy_col.addWidget(self.bene_barangay)
        bene_address_row2.addLayout(bene_brgy_col, 4)
        box_sizer_bene.addLayout(bene_address_row2)

        box_sizer_bene.addWidget(QLabel("Target Sector Beneficiary"))
        self.target_sector_bene = NoScrollComboBox()
        self.target_sector_bene.addItems(self.target_sector_options)
        self.target_sector_bene.setCurrentIndex(0)
        box_sizer_bene.addWidget(self.target_sector_bene)

        notebook.addTab(bene_panel, "Beneficiary Details")

        self.scroll_sizer.addWidget(notebook, 1)

        # ── Assistance Section (below tabs) ─────────────────────────────
        assist_card = QFrame()
        assist_card.setObjectName("card")
        assist_box = QVBoxLayout(assist_card)
        assist_box.setContentsMargins(10, 10, 10, 10)
        assist_box.setSpacing(4)

        assistance_sizer = QHBoxLayout()
        amount_col = QVBoxLayout()
        amount_col.addWidget(QLabel("Amount:"))
        self.amount = QLineEdit()
        amount_col.addWidget(self.amount)
        assistance_sizer.addLayout(amount_col)

        release_col = QVBoxLayout()
        release_col.addWidget(QLabel("Mode of Release"))
        mode_release_rows = self._get_list_rows("mode_of_release")
        self.mode_release_options = [col1 for _id, col1, col2, extra, extra2 in mode_release_rows]
        self.mode_release_gform_map = {col1: (col2 or col1) for _id, col1, col2, extra, extra2 in mode_release_rows}
        self.mode_release_website_map = {col1: (extra2 or col1) for _id, col1, col2, extra, extra2 in mode_release_rows}
        self.mode_release = NoScrollComboBox()
        self.mode_release.addItems(self.mode_release_options)
        self.mode_release.setCurrentIndex(0)
        release_col.addWidget(self.mode_release)
        assistance_sizer.addLayout(release_col)

        financial_col = QVBoxLayout()
        financial_col.addWidget(QLabel("Assistance"))
        financial_assist_rows = self._get_list_rows("financial_assistance_list")
        self.financial_assist_options = [col1 for _id, col1, col2, extra, extra2 in financial_assist_rows]
        self.financial_assist = NoScrollComboBox()
        self.financial_assist.addItems(self.financial_assist_options)
        self.financial_assist.setCurrentIndex(4)
        financial_col.addWidget(self.financial_assist)
        assistance_sizer.addLayout(financial_col)

        fund_source_rows = self._get_list_rows("fund_source_list")
        self.fund_source_choices = [col1 for _id, col1, col2, extra, extra2 in fund_source_rows]
        self.fund_source_gform_map = {col1: (col2 or col1) for _id, col1, col2, extra, extra2 in fund_source_rows}
        self.fund_source_website_map = {col1: (extra2 or col1) for _id, col1, col2, extra, extra2 in fund_source_rows}
        fund_col = QVBoxLayout()
        fund_col.addWidget(QLabel("Fund Source:"))
        self.fund_source = NoScrollComboBox()
        self.fund_source.addItems(self.fund_source_choices)
        self.fund_source.setCurrentIndex(1)
        fund_col.addWidget(self.fund_source)
        assistance_sizer.addLayout(fund_col)
        assist_box.addLayout(assistance_sizer)

        mode_sizer = QHBoxLayout()
        subcat_col = QVBoxLayout()
        subcat_col.addWidget(QLabel("Sub Category"))
        sub_category_rows = self._get_list_rows("client_sub_category")
        self.sub_category_options = [col1 for _id, col1, col2, extra, extra2 in sub_category_rows]
        self.sub_category_gform_map = {col1: (col2 or col1) for _id, col1, col2, extra, extra2 in sub_category_rows}
        self.sub_category_website_map = {col1: (extra2 or col1) for _id, col1, col2, extra, extra2 in sub_category_rows}
        self.sub_category = NoScrollComboBox()
        self.sub_category.addItems(self.sub_category_options)
        subcat_col.addWidget(self.sub_category)
        mode_sizer.addLayout(subcat_col)

        mode_of_admission_rows = self._get_list_rows("mode_of_admission_list")
        self.mode_of_admission_options = [col1 for _id, col1, col2, extra, extra2 in mode_of_admission_rows]
        self.mode_of_admission_map = {col1: (col2 or col1) for _id, col1, col2, extra, extra2 in mode_of_admission_rows}

        mode_admit_col = QVBoxLayout()
        mode_admit_col.addWidget(QLabel("Mode of Admission:"))
        self.mode_of_admission = NoScrollComboBox()
        self.mode_of_admission.addItems(self.mode_of_admission_options)
        self.mode_of_admission.setCurrentIndex(1)
        mode_admit_col.addWidget(self.mode_of_admission)
        mode_sizer.addLayout(mode_admit_col)

        from PySide6.QtWidgets import QDateEdit as _QDE
        date_int_col = QVBoxLayout()
        date_int_col.addWidget(QLabel("Date Interview:"))
        self.interview_date = _QDE()
        self.interview_date.setCalendarPopup(True)
        self.interview_date.setDate(QDate.currentDate())
        date_int_col.addWidget(self.interview_date)
        mode_sizer.addLayout(date_int_col)
        assist_box.addLayout(mode_sizer)

        self.social_worker_list = get_all_workers()
        self.social_worker_choices = [full_name for (_id, full_name, _gform, _website) in self.social_worker_list]

        worker_label_sizer = QHBoxLayout()
        worker_label_sizer.addWidget(QLabel("Social Worker"))
        assist_box.addLayout(worker_label_sizer)

        worker_sizer = QHBoxLayout()
        self.social_worker = NoScrollComboBox()
        self.social_worker.addItems(self.social_worker_choices)
        self.social_worker.setEditable(True)
        self.social_worker.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.social_worker.lineEdit().editingFinished.connect(self.on_social_worker_editing_finished)
        worker_sizer.addWidget(self.social_worker, 8)
        assist_box.addLayout(worker_sizer)

        self.encode_id = QLineEdit()
        self.encode_id.hide()

        self.scroll_sizer.addWidget(assist_card)

        # ── Encoder Section ───────────────────────────────────────────────
        encoder_card = QFrame()
        encoder_card.setObjectName("card")
        encoder_box = QVBoxLayout(encoder_card)
        encoder_box.setContentsMargins(10, 10, 10, 10)
        encoder_box.setSpacing(4)

        encoder_box.addWidget(QLabel("Encoder Name:"))
        self.encoder_name = AllCapsLineEdit()
        encoder_box.addWidget(self.encoder_name)

        approved_by_rows = self._get_list_rows("approved_by_list")
        self.approved_by_options = [col1 for _id, col1, col2, extra, extra2 in approved_by_rows]
        self.approved_by_gform_map = {col1: (col2 or col1) for _id, col1, col2, extra, extra2 in approved_by_rows}
        self.approved_by_website_map = {col1: (extra2 or col1) for _id, col1, col2, extra, extra2 in approved_by_rows}

        encoder_box.addWidget(QLabel("Approved By:"))
        self.approved_by = NoScrollComboBox()
        self.approved_by.addItems(self.approved_by_options)
        encoder_box.addWidget(self.approved_by)

        encoder_box.addWidget(QLabel("Date Entered:"))
        self.encoded_date = _QDE()
        self.encoded_date.setCalendarPopup(True)
        self.encoded_date.setDate(QDate.currentDate())
        encoder_box.addWidget(self.encoded_date)

        self.scroll_sizer.addWidget(encoder_card)

        # ── CRUD + Table section ─────────────────────────────────────────
        crud_card = QFrame()
        crud_card.setObjectName("card")
        crud_container = QVBoxLayout(crud_card)
        crud_container.setContentsMargins(10, 10, 10, 10)
        crud_container.setSpacing(4)

        self.auto_next = QCheckBox("Auto Next")
        self.auto_submit = QCheckBox("Auto Submit")
        self.auto_finish = QCheckBox("Auto Finish")

        btn_crud_add = QPushButton("Add")
        btn_crud_add.setObjectName("addBtn")
        btn_crud_update = QPushButton("Update")
        btn_crud_update.setObjectName("updateBtn")
        btn_crud_delete = QPushButton("Delete")
        btn_crud_delete.setObjectName("deleteBtn")
        btn_crud_add.clicked.connect(self.on_add_person)
        btn_crud_update.clicked.connect(self.on_update_person)
        btn_crud_delete.clicked.connect(self.on_delete_person)

        btn_set_encoded = QPushButton("Set Encoded")
        btn_set_encoded.setObjectName("clearBtn")
        btn_set_encoded.clicked.connect(self.on_set_encoded)

        self.cb_encoded = QCheckBox("Encoded")
        self.cb_encoded.stateChanged.connect(self.on_checkbox_change)

        btn_export = QPushButton("Export")
        btn_export.setObjectName("clearBtn")
        btn_export.clicked.connect(self.on_export)

        control_container = QHBoxLayout()
        control_container.addWidget(btn_crud_add)
        control_container.addWidget(btn_crud_update)
        control_container.addWidget(btn_crud_delete)
        control_container.addWidget(btn_set_encoded)
        control_container.addStretch()
        control_container.addWidget(self.cb_encoded)
        control_container.addWidget(btn_export)
        crud_container.addLayout(control_container)

        self.list_ctrl = QTableWidget(0, 11)
        self.list_ctrl.setHorizontalHeaderLabels([
            "ID", "Lastname", "Firstname", "Middlename", "Ext",
            "Bday", "Age", "Assistance", "Amount", "SW", "Encoded"
        ])
        header = self.list_ctrl.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setDefaultSectionSize(110)
        header.setMinimumSectionSize(70)
        self.list_ctrl.setColumnWidth(5, 110)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.list_ctrl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.list_ctrl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.list_ctrl.setSortingEnabled(True)
        self.list_ctrl.itemSelectionChanged.connect(self.on_select_person)
        set_table_visible_rows(self.list_ctrl, 5)
        crud_container.addWidget(self.list_ctrl)

        # ── Auto Fill section ────────────────────────────────────────────
        autofill_card = QFrame()
        autofill_card.setObjectName("card")
        autofill_container = QVBoxLayout(autofill_card)
        autofill_container.setContentsMargins(10, 10, 10, 10)
        autofill_container.setSpacing(4)

        self.fill_forms_btn = QPushButton("Fill Form")
        self.fill_forms_btn.setObjectName("addBtn")
        self.fill_forms_btn.clicked.connect(self.on_button_click)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("clearBtn")
        self.refresh_btn.clicked.connect(self.on_refresh)
        self.cb_website = QCheckBox("WEB")
        self.cb_offline = QCheckBox("OFF")
        self.cb_mov = QCheckBox("MOV")

        btn_stop = QPushButton("Stop")
        btn_stop.setObjectName("deleteBtn")
        btn_stop.clicked.connect(self.on_stop)

        btn_auto_fill = QPushButton("Auto Fill")
        btn_auto_fill.setObjectName("addBtn")
        btn_auto_fill.clicked.connect(self.on_auto_fill)

        hbox_btns = QHBoxLayout()
        hbox_btns.addWidget(self.auto_next)
        hbox_btns.addWidget(self.auto_submit)
        hbox_btns.addWidget(self.auto_finish)
        hbox_btns.addWidget(btn_stop)
        hbox_btns.addStretch()
        hbox_btns.addWidget(self.cb_website)
        hbox_btns.addWidget(self.cb_offline)
        hbox_btns.addWidget(self.cb_mov)
        hbox_btns.addWidget(self.fill_forms_btn)
        hbox_btns.addWidget(self.refresh_btn)
        autofill_container.addLayout(hbox_btns)

        self.command_log = QTextEdit()
        self.command_log.setReadOnly(True)
        set_textedit_visible_rows(self.command_log, 3)
        # Every append() call site (there are dozens, scattered across the Selenium
        # automation helpers below, not just the thread-safe _sig_log path) should
        # keep the latest line in view — react to textChanged instead of wrapping
        # each call site individually.
        self.command_log.textChanged.connect(self._scroll_log_to_bottom)
        autofill_container.addWidget(self.command_log)

        autofill_container.addWidget(btn_auto_fill)

        self.sizer.addWidget(scroll_area, 1)
        self.sizer.addWidget(crud_card)
        self.sizer.addWidget(autofill_card)

        # Connect thread-safe signals
        self._sig_log.connect(self.command_log.append)
        self._sig_set_running.connect(self.set_running_flag)
        self._sig_reload_person.connect(self.load_data_person)
        self._sig_select_first.connect(self.select_first_item)
        self._sig_msg_box.connect(self._show_msg_box)

        self.on_check_pickle()
        self.load_data_person()

    def _show_msg_box(self, title, message, kind):
        if kind == "error":
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def _scroll_log_to_bottom(self):
        scrollbar = self.command_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _reload_config_cache(self):
        """Warm a per-session snapshot of config lists/items to avoid repeated
        get_all_lists()/get_items() round-trips during UI initialization."""
        self._list_meta_by_key = {}
        self._items_by_key = {}

        for list_id, list_key, label, kind, col1_label, col2_label in get_all_lists():
            self._list_meta_by_key[list_key] = {
                "list_id": list_id,
                "label": label,
                "kind": kind,
                "col1_label": col1_label,
                "col2_label": col2_label,
            }
            self._items_by_key[list_key] = get_items(list_id)

    def invalidate_config_cache(self):
        self._list_meta_by_key = {}
        self._items_by_key = {}

    def reload_config_data(self):
        """Refresh cache and rebuild all config-driven in-memory maps.

        This is the single invalidation/reload hook to call after any workflow
        that changes config.db values while this window remains open.
        """
        self._reload_config_cache()
        self.city_config = self._load_city_config()
        self.barangays_by_city = self._load_barangays_by_city()
        self.barangay_website_map = self._load_barangay_website_map()
        self.region_options = self._load_region_list()
        self.region_gform_map = self._load_region_gform_map()
        self.provinces_by_region = self._load_provinces_by_region()
        self.province_gform_map = self._load_province_gform_map()
        self.province_website_map = self._load_province_website_map()
        self.province_options = [p for provinces in self.provinces_by_region.values() for p in provinces]
        self.cities_by_province = self._load_cities_by_province()
        self.city_website_map = {city: info["city_website"] for city, info in self.city_config.items()}

    def _get_list_rows(self, key):
        """Return cached get_items() rows (id, col1, col2, extra, extra2) for a config list key."""
        return self._items_by_key.get(key, [])

    def _load_city_config(self):
        """Build {city: {"province", "region_gform", "region_website", "city_gform",
        "city_website"}} from list_of_city config rows (extra column holds the linked
        province's config_items.id). region_gform/region_website are derived by walking
        city -> province -> region (each linked by id) rather than being duplicated on
        every city row, so a renamed province/region doesn't silently orphan its cities.
        city_gform/city_website are the city's own values (e.g. "CITY OF CALOOCAN"'s
        website value is "KALOOKAN CITY")."""
        region_by_id = {
            str(item_id): {
                "gform": region_gform or region_label,
                "website": region_website or region_label,
            }
            for item_id, region_label, region_gform, _extra, region_website in self._get_list_rows("region_list")
        }

        province_by_id = {
            str(item_id): {"label": province_label, "region_id": region_id}
            for item_id, province_label, _col2, region_id, _extra2 in self._get_list_rows("province_list")
        }

        city_config = {}
        for _item_id, city, city_gform, province_id, city_website in self._get_list_rows("list_of_city"):
            province_info = province_by_id.get(province_id, {})
            region_info = region_by_id.get(province_info.get("region_id"), {})
            city_config[city] = {
                "province": province_info.get("label") or "NCR THIRD DISTRICT",
                "region_gform": region_info.get("gform") or "NCR (National Capital Region)",
                "region_website": region_info.get("website") or "NCR [National Capital Region]",
                "city_gform": city_gform or city,
                "city_website": city_website or city,
            }
        return city_config

    def _load_barangays_by_city(self):
        """Build {city label: [barangay, ...]} from barangay_list config rows (extra
        column holds the linked city's config_items.id, not its label, so a renamed
        city doesn't silently orphan its barangays)."""
        city_labels_by_id = {
            str(item_id): city_label
            for item_id, city_label, _col2, _extra, _extra2 in self._get_list_rows("list_of_city")
        }

        barangays_by_city = {}
        for _item_id, barangay, _col2, city_id, _extra2 in self._get_list_rows("barangay_list"):
            city_label = city_labels_by_id.get(city_id)
            if city_label is None:
                continue
            barangays_by_city.setdefault(city_label, []).append(barangay)
        return barangays_by_city

    def _load_region_list(self):
        """Build [region, ...] from region_list config rows."""
        return [col1 for _item_id, col1, _col2, _extra, _extra2 in self._get_list_rows("region_list")]

    def _load_region_gform_map(self):
        """Build {region label: GForm value} from region_list config rows."""
        return {col1: (col2 or col1) for _item_id, col1, col2, _extra, _extra2 in self._get_list_rows("region_list")}

    def _load_province_gform_map(self):
        """Build {province label: GForm value} from province_list config rows."""
        return {col1: (col2 or col1) for _item_id, col1, col2, _extra, _extra2 in self._get_list_rows("province_list")}

    def _load_province_website_map(self):
        """Build {province label: Website Value} from province_list config rows."""
        return {col1: (extra2 or col1) for _item_id, col1, _col2, _extra, extra2 in self._get_list_rows("province_list")}

    def _load_barangay_website_map(self):
        """Build {(city label, barangay label): Website Value} from barangay_list
        config rows (extra column holds the linked city's config_items.id, not its
        label). Keyed by city too, not just barangay label, since barangay names
        repeat across different cities."""
        city_labels_by_id = {
            str(item_id): city_label
            for item_id, city_label, _col2, _extra, _extra2 in self._get_list_rows("list_of_city")
        }

        barangay_website_map = {}
        for _item_id, barangay, _col2, city_id, extra2 in self._get_list_rows("barangay_list"):
            city_label = city_labels_by_id.get(city_id)
            if city_label is None:
                continue
            barangay_website_map[(city_label, barangay)] = extra2 or barangay
        return barangay_website_map

    def _load_provinces_by_region(self):
        """Build {region_label: [province, ...]} from province_list config rows
        (extra column holds the linked region's config_items.id, not its label,
        so a renamed region doesn't silently orphan its provinces)."""
        region_labels_by_id = {
            str(item_id): region_label
            for item_id, region_label, _col2, _extra, _extra2 in self._get_list_rows("region_list")
        }

        provinces_by_region = {}
        for _item_id, province, _col2, region_id, _extra2 in self._get_list_rows("province_list"):
            region_label = region_labels_by_id.get(region_id)
            if region_label is None:
                continue
            provinces_by_region.setdefault(region_label, []).append(province)
        return provinces_by_region

    def _load_cities_by_province(self):
        """Build {province: [city, ...]} from self.city_config's province field."""
        cities_by_province = {}
        for city, info in self.city_config.items():
            province = info["province"] if info["province"] in self.province_options else "NCR THIRD DISTRICT"
            cities_by_province.setdefault(province, []).append(city)
        return cities_by_province

    def _city_lookup(self, city):
        return self.city_config.get(city, {
            "province": "NCR THIRD DISTRICT",
            "region_gform": "NCR (National Capital Region)",
            "region_website": "NCR [National Capital Region]",
            "city_gform": city,
            "city_website": city,
        })

    def _resolve_pickle_city(self, value):
        """Old data-new.pkl files (saved before the City->Province migration) stored
        client_city/bene_city as the City combobox's currentIndex() (int), not its
        name. Resolve that to a city name using the fixed list_of_city order the
        index was originally saved against; a value that's already text (current
        format) needs no resolution."""
        if isinstance(value, int):
            if 0 <= value < len(list_of_city):
                return list_of_city[value][0]
            return ""
        return value or ""

    def on_client_region_changed(self, index=None):
        region = self.client_region.currentText()
        self.client_province.blockSignals(True)
        self.client_province.clear()
        self.client_province.addItems(self.provinces_by_region.get(region, []))
        self.client_province.setCurrentIndex(-1)
        self.client_province.blockSignals(False)
        self.client_city.blockSignals(True)
        self.client_city.clear()
        self.client_city.setCurrentIndex(-1)
        self.client_city.blockSignals(False)
        self.client_barangay.blockSignals(True)
        self.client_barangay.clear()
        self.client_barangay.setCurrentIndex(-1)
        self.client_barangay.blockSignals(False)

    def on_bene_region_changed(self, index=None):
        region = self.bene_region.currentText()
        self.bene_province.blockSignals(True)
        self.bene_province.clear()
        self.bene_province.addItems(self.provinces_by_region.get(region, []))
        self.bene_province.setCurrentIndex(-1)
        self.bene_province.blockSignals(False)
        self.bene_city.blockSignals(True)
        self.bene_city.clear()
        self.bene_city.setCurrentIndex(-1)
        self.bene_city.blockSignals(False)
        self.bene_barangay.blockSignals(True)
        self.bene_barangay.clear()
        self.bene_barangay.setCurrentIndex(-1)
        self.bene_barangay.blockSignals(False)

    def on_client_province_changed(self, index=None):
        province = self.client_province.currentText()
        self.client_city.blockSignals(True)
        self.client_city.clear()
        self.client_city.addItems(self.cities_by_province.get(province, []))
        self.client_city.setCurrentIndex(-1)
        self.client_city.blockSignals(False)
        self.client_barangay.blockSignals(True)
        self.client_barangay.clear()
        self.client_barangay.setCurrentIndex(-1)
        self.client_barangay.blockSignals(False)

    def on_bene_province_changed(self, index=None):
        province = self.bene_province.currentText()
        self.bene_city.blockSignals(True)
        self.bene_city.clear()
        self.bene_city.addItems(self.cities_by_province.get(province, []))
        self.bene_city.setCurrentIndex(-1)
        self.bene_city.blockSignals(False)
        self.bene_barangay.blockSignals(True)
        self.bene_barangay.clear()
        self.bene_barangay.setCurrentIndex(-1)
        self.bene_barangay.blockSignals(False)

    def on_client_city_changed(self, index=None):
        city = self.client_city.currentText()
        self.client_barangay.blockSignals(True)
        self.client_barangay.clear()
        self.client_barangay.addItems(self.barangays_by_city.get(city, []))
        self.client_barangay.setCurrentIndex(-1)
        self.client_barangay.blockSignals(False)

    def on_bene_city_changed(self, index=None):
        city = self.bene_city.currentText()
        self.bene_barangay.blockSignals(True)
        self.bene_barangay.clear()
        self.bene_barangay.addItems(self.barangays_by_city.get(city, []))
        self.bene_barangay.setCurrentIndex(-1)
        self.bene_barangay.blockSignals(False)

    def on_choice_change_client(self, index=None):
        bday = self.client_bday.date()
        bday_date = datetime(bday.year(), bday.month(), bday.day())
        today = datetime.today()
        age_value = today.year - bday_date.year - ((today.month, today.day) < (bday_date.month, bday_date.day))
        if age_value >= 60:
            self.target_sector.setCurrentIndex(3)
        elif 13 <= age_value <= 19:
            self.target_sector.setCurrentIndex(5)
        elif age_value < 13:
            self.target_sector.setCurrentIndex(4)
        else:
            if self.client_gender.currentText() == "Female":
                self.target_sector.setCurrentIndex(1)
            else:
                self.target_sector.setCurrentIndex(0)

    def on_choice_change_bene(self, index=None):
        bday = self.bene_bday.date()
        bday_date = datetime(bday.year(), bday.month(), bday.day())
        today = datetime.today()
        age_value = today.year - bday_date.year - ((today.month, today.day) < (bday_date.month, bday_date.day))
        if age_value >= 60:
            self.target_sector_bene.setCurrentIndex(3)
        elif 13 <= age_value <= 19:
            self.target_sector_bene.setCurrentIndex(5)
        elif age_value < 13:
            self.target_sector_bene.setCurrentIndex(4)
        else:
            if self.bene_gender.currentText() == "Female":
                self.target_sector_bene.setCurrentIndex(1)
            else:
                self.target_sector_bene.setCurrentIndex(0)

    def c_compute_age(self, date=None):
        bday = self.client_bday.date()
        bday_date = datetime(bday.year(), bday.month(), bday.day())
        today = datetime.today()
        age_value = today.year - bday_date.year - ((today.month, today.day) < (bday_date.month, bday_date.day))

        if age_value >= 60:
            self.target_sector.setCurrentIndex(3)
        elif 13 <= age_value <= 19:
            self.target_sector.setCurrentIndex(5)
        elif age_value < 13:
            self.target_sector.setCurrentIndex(4)
        else:
            if self.client_gender.currentText() == "Female":
                self.target_sector.setCurrentIndex(1)
            else:
                self.target_sector.setCurrentIndex(0)
        self.client_age.setText(str(age_value))

    def b_compute_age(self, date=None):
        bday = self.bene_bday.date()
        bday_date = datetime(bday.year(), bday.month(), bday.day())
        today = datetime.today()
        age_value = today.year - bday_date.year - ((today.month, today.day) < (bday_date.month, bday_date.day))

        if age_value >= 60:
            self.target_sector_bene.setCurrentIndex(3)
        elif 13 <= age_value <= 19:
            self.target_sector_bene.setCurrentIndex(5)
        elif age_value < 13:
            self.target_sector_bene.setCurrentIndex(4)
        else:
            if self.bene_gender.currentText() == "Female":
                self.target_sector_bene.setCurrentIndex(1)
            else:
                self.target_sector_bene.setCurrentIndex(0)
        self.bene_age.setText(str(age_value))

    def set_running_flag(self, value):
        self.is_running = value

    def on_button_click(self, event=None):
        try:
            self.on_save_data()
        except Exception as e:
            self.command_log.append(f"Error saving form data: {e}")
            _log_crash(*sys.exc_info())
            return
        if self.is_running:
            self.command_log.append("Task already running... Please wait.")
            return
        self.is_running = True
        self.command_log.append("Task started... Please wait.")
        threading.Thread(target=self.on_fill_up, daemon=True).start()

    def on_check_pickle(self):
        file_path = FORM_CACHE_FILE_PATH

        # Check if the file exists
        if os.path.exists(file_path):
            self.on_load_data()
        else:
            self.on_save_data()

    def on_load_data(self):
        with open(FORM_CACHE_FILE_PATH, "rb") as file:
            self.loaded_data = pickle.load(file)
        d = self.loaded_data
        self.mode_of_admission.setCurrentIndex(d.get("mode_of_admission", 1))
        self.encoder_name.setText(d.get("encoder_name", ""))
        set_date_value(self.encoded_date, d.get("encoded_date", "2000-01-01"))
        self.auto_next.setChecked(d.get("auto_next", False))
        self.auto_submit.setChecked(d.get("auto_submit", False))
        self.target_sector.setCurrentIndex(d.get("target_sector", 0))
        self.financial_assist.setCurrentIndex(d.get("financial_assist", 0))
        self.mode_release.setCurrentIndex(d.get("mode_release", 0))
        self.amount.setText(d.get("amount", ""))
        self.fund_source.setCurrentIndex(d.get("fund_source", 0))
        try:
            self.social_worker.setCurrentIndex(self.social_worker_choices.index(d.get("sw_full_name", "")))
        except ValueError:
            self.social_worker.setCurrentIndex(-1)
        set_date_value(self.interview_date, d.get("interview_date", "2000-01-01"))
        self.client_relationship.setCurrentIndex(d.get("client_relationship", 0))
        self.client_lastname.setText(d.get("client_lastname", ""))
        self.client_firstname.setText(d.get("client_firstname", ""))
        self.client_middlename.setText(d.get("client_middlename", ""))
        self.client_ext.setText(d.get("client_ext", ""))
        self.client_gender.setCurrentIndex(d.get("client_gender", 0))
        set_date_value(self.client_bday, d.get("client_bday", "2000-01-01"))
        self.client_age.setText(d.get("client_age", ""))
        self.client_contact_no.setText(d.get("client_contact_no", ""))
        self.client_civil_status.setCurrentIndex(d.get("client_civil_status", 0))
        self.client_house_street.setText(d.get("client_house_street", ""))
        self.client_region.setCurrentText(d.get("client_region", self.region_options[0] if self.region_options else ""))
        self.client_province.setCurrentText(d.get("client_province", ""))
        self.client_city.setCurrentText(self._resolve_pickle_city(d.get("client_city", "")))
        self.client_barangay.setCurrentText(d.get("client_barangay", ""))
        self.bene_relationship.setCurrentIndex(d.get("bene_relationship", 0))
        self.bene_lastname.setText(d.get("bene_lastname", ""))
        self.bene_firstname.setText(d.get("bene_firstname", ""))
        self.bene_middlename.setText(d.get("bene_middlename", ""))
        self.bene_ext.setText(d.get("bene_ext", ""))
        self.bene_gender.setCurrentIndex(d.get("bene_gender", 0))
        set_date_value(self.bene_bday, d.get("bene_bday", "2000-01-01"))
        self.bene_age.setText(d.get("bene_age", ""))
        self.bene_contact_no.setText(d.get("bene_contact_no", ""))
        self.bene_civil_status.setCurrentIndex(d.get("bene_civil_status", 0))
        self.bene_house_street.setText(d.get("bene_house_street", ""))
        self.bene_region.setCurrentText(d.get("bene_region", self.region_options[0] if self.region_options else ""))
        self.bene_province.setCurrentText(d.get("bene_province", ""))
        self.bene_city.setCurrentText(self._resolve_pickle_city(d.get("bene_city", "")))
        self.bene_barangay.setCurrentText(d.get("bene_barangay", ""))
        self.has_beneficiary.setChecked(d.get("has_beneficiary", False))
        self.cb_encoded.setChecked(d.get("cb_encoded", False))
        self.auto_finish.setChecked(d.get("auto_finish", False))
        self.selected_person_id = d.get("selected_id")
        self.encode_id.setText(str(self.selected_person_id or ""))

    def on_save_data(self):
        self.data = {
            "mode_of_admission": self.mode_of_admission.currentIndex(),
            "encoder_name": self.encoder_name.text(),
            "encoded_date": get_date_value(self.encoded_date),
            "auto_next": self.auto_next.isChecked(),
            "auto_submit": self.auto_submit.isChecked(),
            "target_sector": self.target_sector.currentIndex(),
            "financial_assist": self.financial_assist.currentIndex(),
            "mode_release": self.mode_release.currentIndex(),
            "amount": self.amount.text(),
            "fund_source": self.fund_source.currentIndex(),
            "sw_full_name": self.social_worker.currentText(),
            "interview_date": get_date_value(self.interview_date),
            "client_relationship": self.client_relationship.currentIndex(),
            "client_lastname": self.client_lastname.text(),
            "client_firstname": self.client_firstname.text(),
            "client_middlename": self.client_middlename.text(),
            "client_ext": self.client_ext.text(),
            "client_gender": self.client_gender.currentIndex(),
            "client_bday": get_date_value(self.client_bday),
            "client_age": self.client_age.text(),
            "client_contact_no": self.client_contact_no.text(),
            "client_civil_status": self.client_civil_status.currentIndex(),
            "client_house_street": self.client_house_street.text(),
            "client_region": self.client_region.currentText(),
            "client_province": self.client_province.currentText(),
            "client_barangay": self.client_barangay.currentText(),
            "client_city": self.client_city.currentText(),
            "bene_relationship": self.bene_relationship.currentIndex(),
            "bene_lastname": self.bene_lastname.text(),
            "bene_firstname": self.bene_firstname.text(),
            "bene_middlename": self.bene_middlename.text(),
            "bene_ext": self.bene_ext.text(),
            "bene_gender": self.bene_gender.currentIndex(),
            "bene_bday": get_date_value(self.bene_bday),
            "bene_age": self.bene_age.text(),
            "bene_contact_no": self.bene_contact_no.text(),
            "bene_civil_status": self.bene_civil_status.currentIndex(),
            "bene_house_street": self.bene_house_street.text(),
            "bene_region": self.bene_region.currentText(),
            "bene_province": self.bene_province.currentText(),
            "bene_barangay": self.bene_barangay.currentText(),
            "bene_city": self.bene_city.currentText(),
            "has_beneficiary": self.has_beneficiary.isChecked(),
            "cb_encoded": self.cb_encoded.isChecked(),
            "auto_finish": self.auto_finish.isChecked(),
            "selected_id": self.encode_id.text(),
        }
        with open(FORM_CACHE_FILE_PATH, "wb") as file:
            pickle.dump(self.data, file)

    def on_button_clear_all(self, event=None):
        for w in [self.client_lastname, self.client_firstname, self.client_middlename,
                  self.client_contact_no, self.client_age, self.client_house_street,
                  self.bene_lastname, self.bene_firstname,
                  self.bene_middlename, self.bene_contact_no, self.bene_age,
                  self.bene_house_street]:
            w.setText("")
        for w in [self.client_gender, self.client_civil_status, self.client_city,
                  self.bene_gender, self.bene_civil_status, self.bene_city,
                  self.client_barangay, self.bene_barangay,
                  self.client_province, self.bene_province]:
            w.setCurrentIndex(-1)
        self.command_log.append("All fields have been cleared.")

    def on_button_save(self, event=None):
        data = {}
        # basic info
        data["mode_of_admission"] = self.mode_of_admission.currentIndex()
        data["encoder_name"] = self.encoder_name.text()
        data["encoded_date"] = get_date_value(self.encoded_date)

        # assistance info
        data["auto_next"] = self.auto_next.isChecked()
        data["auto_submit"] = self.auto_submit.isChecked()
        data["target_sector"] = self.target_sector.currentIndex()
        data["financial_assist"] = self.financial_assist.currentIndex()

        data["mode_release"] = self.mode_release.currentIndex()

        data["amount"] = self.amount.text()
        data["fund_source"] = self.fund_source.currentIndex()
        data["sw_full_name"] = self.social_worker.currentText()
        data["interview_date"] = get_date_value(self.interview_date)

        # client
        data["client_relationship"] = self.client_relationship.currentIndex()

        data["client_lastname"] = self.client_lastname.text()
        data["client_firstname"] = self.client_firstname.text()
        data["client_middlename"] = self.client_middlename.text()

        data["client_gender"] = self.client_gender.currentIndex()

        data["client_bday"] = get_date_value(self.client_bday)
        data["client_age"] = self.client_age.text()

        data["client_contact_no"] = self.client_contact_no.text()
        data["client_civil_status"] = self.client_civil_status.currentIndex()

        data["client_house_street"] = self.client_house_street.text()
        data["client_region"] = self.client_region.currentText()
        data["client_province"] = self.client_province.currentText()
        data["client_barangay"] = self.client_barangay.currentText()
        data["client_city"] = self.client_city.currentText()

        # Bene
        data["bene_relationship"] = self.bene_relationship.currentIndex()

        data["bene_lastname"] = self.bene_lastname.text()
        data["bene_firstname"] = self.bene_firstname.text()
        data["bene_middlename"] = self.bene_middlename.text()

        data["bene_gender"] = self.bene_gender.currentIndex()

        data["bene_bday"] = get_date_value(self.bene_bday)
        data["bene_age"] = self.bene_age.text()

        data["bene_contact_no"] = self.bene_contact_no.text()
        data["bene_civil_status"] = self.bene_civil_status.currentIndex()

        data["bene_house_street"] = self.bene_house_street.text()
        data["bene_region"] = self.bene_region.currentText()
        data["bene_province"] = self.bene_province.currentText()
        data["bene_barangay"] = self.bene_barangay.currentText()
        data["bene_city"] = self.bene_city.currentText()

        data["has_beneficiary"] = self.has_beneficiary.isChecked()
        data["cb_encoded"] = self.cb_encoded.isChecked()

        data["selected_id"] = self.selected_person_id

        # Define CSV file path
        csv_file = "data.csv"

        # Check if file exists to determine if we should write headers
        file_exists = os.path.exists(csv_file)

        # Open CSV file in append mode
        with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=data.keys())

            # Write headers only if the file is new
            if not file_exists:
                writer.writeheader()

            # Write the data row
            writer.writerow(data)

        self.command_log.append(f"Data saved successfully to {csv_file}")

    def _connect_chrome_debugger(self, retries=3, base_delay=1.0):
        """Attach to an existing Chrome debug session with bounded retries."""
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                chrome_options = webdriver.ChromeOptions()
                chrome_options.debugger_address = "localhost:9222"
                return webdriver.Chrome(options=chrome_options)
            except Exception as exc:
                last_error = exc
                self._sig_log.emit(f"Chrome attach failed (attempt {attempt}/{retries}): {exc}")
                if attempt < retries:
                    time.sleep(base_delay * attempt)

        raise RuntimeError(f"Unable to attach to Chrome debugger on localhost:9222: {last_error}")

    def _accept_alert_if_present(self, driver, timeout=2):
        """Best-effort alert accept that does not block when no alert exists."""
        try:
            WebDriverWait(driver, timeout).until(EC.alert_is_present())
            Alert(driver).accept()
            self.command_log.append("Alert accepted.")
            return True
        except TimeoutException:
            return False
        except Exception as exc:
            self.command_log.append(f"Alert handling failed: {exc}")
            return False

    def on_refresh(self, event=None):
        if self.cb_website.isChecked() or self.cb_offline.isChecked() or self.cb_mov.isChecked():
            driver = None
            try:
                driver = self._connect_chrome_debugger()
            except Exception as exc:
                self.command_log.append(f"Cannot connect to Chrome debugger: {exc}")
                return

            try:
                if self.cb_mov.isChecked():
                    if self.switch_to_tab(driver, mov_url):
                        self.clickAddButton(driver, "Submit another response")
                    else:
                        self.command_log.append("URL not found in any open tab.")
                if self.cb_offline.isChecked():
                    if self.switch_to_tab(driver, offline_url):
                        self.clickAddButton(driver, "Submit another response")
                    else:
                        self.command_log.append("URL not found in any open tab.")
                if self.cb_website.isChecked():
                    if self.switch_to_tab(driver, website_url):
                        self.clickAddButton(driver, "Home")
                    else:
                        self.command_log.append("URL not found in any open tab.")
                self._sig_log.emit("Task completed!")
            finally:
                if driver is not None:
                    try:
                        driver.quit()
                    except Exception:
                        pass
        else:
            self.command_log.append("Please select a checkbox(s).")

    def on_fill_up(self):
        if self.list_ctrl.rowCount() <= 0:
            self.stop_requested = True

        if self.stop_requested:
            self.stop_requested = False
            self._sig_log.emit("Task was stopped.")
            self._sig_set_running.emit(False)  # Reset flag on completion
            return

        is_end_mov = False
        is_end_offline = False
        is_end_website = False

        if self.cb_website.isChecked() or self.cb_offline.isChecked() or self.cb_mov.isChecked():
            try:
                self.driver = self._connect_chrome_debugger()

                # Get all currently open tabs
                if self.cb_mov.isChecked():
                    if self.switch_to_tab(self.driver, mov_url):
                        is_end_mov = self.is_end_of_g_form(self.driver)
                        if not is_end_mov :
                            self.on_fill_crims_mov(self.driver)
                    else:
                        self.command_log.append("URL not found in any open tab.")

                if self.cb_offline.isChecked():
                    if self.switch_to_tab(self.driver, offline_url):
                        is_end_offline = self.is_end_of_g_form(self.driver)
                        if not is_end_offline:
                            self.on_fill_crims_offline(self.driver)
                    else:
                        self.command_log.append("URL not found in any open tab.")

                if self.cb_website.isChecked():
                    if self.switch_to_tab(self.driver, website_url):
                        is_end_website = self.is_end_of_website(self.driver)
                        if not is_end_website:
                            self.on_fill_crims_website(self.driver)
                    else:
                        self.command_log.append("URL not found in any open tab.")

                self._sig_log.emit("Task completed!")
            except Exception as exc:
                self._sig_log.emit(f"Automation stopped: {exc}")
                self.stop_requested = False
                self._sig_set_running.emit(False)
                return
            finally:
                if self.driver is not None:
                    try:
                        self.driver.quit()
                    except Exception:
                        pass
                    self.driver = None

        else:
            self.command_log.append("Please select a checkbox(s).")

        if self.auto_finish.isChecked() :

            if (is_end_website == self.cb_website.isChecked()) and (is_end_mov == self.cb_mov.isChecked()) and (is_end_offline == self.cb_offline.isChecked()):

                self._sig_set_running.emit(False)  # Reset flag on completion
                self.stop_requested = False
                set_encoded(self.encode_id.text(), True)
                self._sig_reload_person.emit()
                self._sig_select_first.emit()

                """ select next record """
                """ trigger on fill up """
                if self.is_auto_fill :
                    time.sleep(1)
                    self.on_refresh()
                    time.sleep(1)
                    self.on_fill_up()
                else:
                    return
            else:
                time.sleep(1)
                self.on_fill_up()
        else:
            self._sig_set_running.emit(False)  # Reset flag on completion

    def switch_to_tab(self, driver, url_part):
        for handle in driver.window_handles:
            driver.switch_to.window(handle)

            if url_part in driver.current_url:  # Check if the URL contains the desired string
                # self.command_log.append(f"Switched to tab: {driver.current_url}")
                return True
        return False

    website_page_title = ""
    offline_page_title = ""
    mov_page_title = ""

    def _normalize_crims_bday_text(self, value):
        """Normalize CRIMS birthday text to the yyyy-mm-dd table format."""
        if isinstance(value, QDate):
            text = value.toString("yyyy-MM-dd")
        elif isinstance(value, datetime):
            text = value.strftime("%Y-%m-%d")
        else:
            text = "" if value is None else str(value)

        collapsed = "".join(text.split())
        if not collapsed:
            return ""

        for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(collapsed, pattern).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return collapsed

    def _click_search_result_row_by_bday(self, driver, target_bday):
        """Open the first searched client row whose visible birthday matches."""
        normalized_target = self._normalize_crims_bday_text(target_bday)
        if not normalized_target:
            self.command_log.append("Birthday match skipped: no target birthday available.")
            return False

        row_xpath = (
            "//table//tbody/tr[.//*[contains(@class, 'glyphicon-share-alt')]]"
            " | //table//tr[.//*[contains(@class, 'glyphicon-share-alt')]]"
        )

        try:
            rows = WebDriverWait(driver, 8).until(
                lambda d: [row for row in d.find_elements(By.XPATH, row_xpath) if row.is_displayed()]
            )
        except TimeoutException:
            self.command_log.append("Search results did not load in time.")
            return False

        for row in rows:
            for cell in row.find_elements(By.TAG_NAME, "td"):
                visible_bday = self._normalize_crims_bday_text(cell.text)
                if visible_bday != normalized_target:
                    continue

                try:
                    action = row.find_element(
                        By.XPATH,
                        ".//a[.//*[contains(@class, 'glyphicon-share-alt')]]"
                        " | .//*[contains(@class, 'glyphicon-share-alt')]",
                    )
                    action.click()
                    self.command_log.append(f"Opened existing client with birthday {normalized_target}.")
                    return True
                except NoSuchElementException:
                    self.command_log.append(
                        f"Birthday {normalized_target} matched, but no row action was found."
                    )
                    return False
                except Exception as exc:
                    self.command_log.append(
                        f"Birthday {normalized_target} matched, but opening the row failed: {exc}"
                    )
                    return False

        self.command_log.append(
            f"Name search returned rows, but none matched birthday {normalized_target}."
        )
        return False

    def on_fill_crims_website(self, driver):
        try:
            if self.clickHrefButton(driver, "Add Client"):
                c_full_name = f'{self.client_lastname.text()} {self.client_firstname.text()} {self.client_middlename.text()}'
                if self.hasASearchField(driver, c_full_name):
                    if self.searchResult(driver):
                        self.command_log.append("No name match found. Adding a new client.")
                        self.clickAddButton(driver, "Add Client")
                        return None
                    if self._click_search_result_row_by_bday(driver, self.client_bday.date()):
                        return None
                    self.command_log.append("No birthday-matching row found. Adding a new client.")
                    self.clickAddButton(driver, "Add Client")
                    return None
                return None

            if self.clickHrefButton(driver, "Add Beneficiary"):
                self.clickAddButton(driver, "Add Beneficiary")
                return None

            if self.website_page_title == self.getTitle(driver):
                winsound.MessageBeep()
            else:
                self.website_page_title = self.getTitle(driver)

            match self.getTitle(driver):
                case "family composition":
                    if self.auto_next.isChecked():
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "confirmation":
                    if self.auto_next.isChecked():
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "clients information":
                    try:
                        file_name = "default.png"  # Replace with your actual file name
                        file_path = os.path.abspath(file_name)  # Convert to absolute path
                        # Locate file input using ID and upload the file
                        file_input = driver.find_element(By.ID, "user_file")
                        file_input.send_keys(file_path)  # Upload file
                    except NoSuchElementException:
                        self.command_log.append(f"Error: Element with File upload not found. ")
                    except Exception as e:
                        self.command_log.append(f"Element not existing {e} ")
                        return False

                    self.setTextField(driver, "cl_pcn", "0")

                    self.setDropDown(driver, "select2-cl_typeid-container", "N/A")

                    self.setTextField(driver, "cl_id_number", "0")
                    
                    self.setTextField(driver, "queue_no", "0")

                    mode_of_admission_caption = self.mode_of_admission.currentText()
                    self.setDropDown(driver, "select2-mode_of_admission-container",
                                     self.mode_of_admission_map.get(mode_of_admission_caption, mode_of_admission_caption))
                    self.setDropDown(driver, "select2-cl_assisted_through-container", "Onsite")
                    self.setDropDown(driver, "select2-cl_typeid-container", "N/A")
                    self.setDropDown(driver, "select2-cl_referring_party-container", "Default Default Default")

                    if not self.has_beneficiary.isChecked():
                        self.setDropDown(driver, "select2-is_Self-container", "Yes")
                    else:
                        self.setDropDown(driver, "select2-is_Self-container", "No")

                    self.setDropDown(driver, "select2-cl_category-container",
                                     self.target_sector_website_map.get(self.target_sector.currentText(), self.target_sector.currentText()))
                    self.setDropDown(
                        driver, "select2-cl_sub_category-container",
                        self.sub_category_website_map.get(self.sub_category.currentText(), self.sub_category.currentText()),
                    )

                    self.setTextField(driver, "lname", self.client_lastname.text())
                    self.setTextField(driver, "fname", self.client_firstname.text())
                    self.setTextField(driver, "mname", self.client_middlename.text())
                    client_ext_value = self.client_ext.text().lower()
                    if client_ext_value != "":
                        self.setTextField(driver, "xname", self.client_ext.text())

                    self.setDate(driver, "birthdate", self.client_bday.date())

                    self.setDropDown(driver, "select2-sex-container", self.gender_website_map.get(self.client_gender.currentText(), self.client_gender.currentText()))

                    client_contact_value = self.client_contact_no.text()
                    if client_contact_value == "" :
                        client_contact_value = "00000000000"

                    self.setTextField(driver, "contact_no", client_contact_value)

                    relationship_caption = self.client_relationship.currentText()

                    self.setDropDown(
                        driver, "select2-relationship_bene-container",
                        self.relationship_website_map.get(relationship_caption, relationship_caption),
                    )

                    civil_status_caption = self.client_civil_status.currentText()
                    civil_status_name = self.civil_status_website_map[civil_status_caption]

                    self.setDropDown(driver, "select2-civil_status-container", civil_status_name)

                    self.setTextField(driver, "purok_street", self.client_house_street.text())

                    client_city_lookup = self._city_lookup(self.client_city.currentText())
                    self.setDropDown(driver, "select2-region-container", client_city_lookup["region_website"])

                    self.setDropDown(
                        driver, "select2-province-container",
                        self.province_website_map.get(self.client_province.currentText(), self.client_province.currentText()),
                    )

                    if self.client_city.currentText() == "NONE OF THE ABOVE":
                        self.stop_requested = True
                        city_value = "NONE OF THE ABOVE"
                    else:
                        city_value = self.city_website_map.get(self.client_city.currentText(), self.client_city.currentText())
                    self.setDropDown(driver, "select2-city_muni-container", city_value)

                    self.setDropDown(
                        driver, "select2-barangay-container",
                        self.barangay_website_map.get(
                            (self.client_city.currentText(), self.client_barangay.currentText()),
                            self.client_barangay.currentText(),
                        ),
                    )

                    self.setDropDown(driver, "select2-occupation-container", "NONE OF THE ABOVE")

                    self.setTextField(driver, "salary", "0")

                    self.setTextField(driver, "fam_members", "0")

                    if self.auto_next.isChecked() :
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "beneficiary information":
                    self.setTextField(driver, "b_pcn", "0")
                    self.setDropDown(driver, "select2-b_assisted_through-container", "Onsite")
                    self.setDropDown(driver, "select2-id_type_id-container", "N/A")

                    if self.has_beneficiary.isChecked():
                        self.selectCheckBox(driver, "uniform-same_add_client")

                        self.setDropDown(driver, "select2-b_sex-container", self.gender_website_map.get(self.bene_gender.currentText(), self.bene_gender.currentText()))
                        bene_civil_status_caption = self.bene_civil_status.currentText()
                        self.setDropDown(driver, "select2-b_civil_status-container",
                                         self.civil_status_website_map.get(bene_civil_status_caption, bene_civil_status_caption))
                        self.setDropDown(driver, "select2-b_referring_party-container", "Default Default Default")

                        self.setDate(driver, "b_birthdate", self.bene_bday.date())

                        self.setTextField(driver, "b_lname", self.bene_lastname.text())
                        self.setTextField(driver, "b_fname", self.bene_firstname.text())
                        self.setTextField(driver, "b_mname", self.bene_middlename.text())
                        self.setTextField(driver, "b_xname", self.bene_ext.text())

                        bene_city_lookup = self._city_lookup(self.bene_city.currentText())
                        self.setDropDown(driver, "select2-b_region-container", bene_city_lookup["region_website"])

                        self.setDropDown(
                            driver, "select2-b_province-container",
                            self.province_website_map.get(self.bene_province.currentText(), self.bene_province.currentText()),
                        )

                        if self.bene_city.currentText() == "NONE OF THE ABOVE":
                            self.stop_requested = True
                            city_value = "NONE OF THE ABOVE"
                        else:
                            city_value = self.city_website_map.get(self.bene_city.currentText(), self.bene_city.currentText())
                        self.setDropDown(driver, "select2-b_city_muni-container", city_value)

                        self.setDropDown(
                            driver, "select2-b_barangay-container",
                            self.barangay_website_map.get(
                                (self.bene_city.currentText(), self.bene_barangay.currentText()),
                                self.bene_barangay.currentText(),
                            ),
                        )

                        self.setTextField(driver, "b_purok_street", self.bene_house_street.text())
                        self.setTextField(driver, "b_contact_no", self.bene_contact_no.text())
                    else:
                        self.selectCheckBox(driver, "uniform-is_existing_self")
                        self.setDropDown(driver, "select2-b_referring_party-container", "Default Default Default")

                    if self.auto_next.isChecked():
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "assessment":
                    self.setDropDown(driver, "select2-bene_category-container",
                                     self.target_sector_website_map.get(self.target_sector.currentText(), self.target_sector.currentText()))
                    self.setDropDown(
                        driver, "select2-bene_sub_category-container",
                        self.sub_category_website_map.get(self.sub_category.currentText(), self.sub_category.currentText()),
                    )

                    value_string = ""
                    if self.client_gender.currentText().lower() == "male":
                        gender_string = "HIS"
                    else:
                        gender_string = "HER"
                    match self.financial_assist.currentText().lower():
                        case "medical":
                            value_string = f"THE CLIENT SEEK'S MEDICAL ASSISTANCE TO AUGMENT {gender_string} MEDICAL EXPENSES"
                        case "transportation":
                            value_string = f"THE CLIENT SEEK'S TRANSPORTATION ASSISTANCE TO AUGMENT {gender_string} TRAVEL EXPENSES"
                        case "burial":
                            value_string = f"THE CLIENT SEEK'S BURIAL ASSISTANCE TO AUGMENT {gender_string} FUNERAL EXPENSES"
                        case "food subsidy":
                            value_string = f"THE CLIENT SEEK'S FINANCIAL ASSISTANCE TO AUGMENT {gender_string} DAILY EXPENSES"

                    self.setTextAreaField(driver, "problem_presented", value_string)
                    self.setTextAreaField(driver, "sw_assessment", value_string)
                    if self.auto_next.isChecked() :
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "recommended services and assistance":
                    if self.selectDefaultCheckBox(driver, "uniform-financial_assistance"):
                        self.clickButton(driver, "add_famCompo")

                    assistance_value = ""
                    purpose_value = ""
                    match self.financial_assist.currentText().lower():
                        case "medical":
                            assistance_value = "Medical Assistance"
                            purpose_value = "MEDICAL EXPENSES"
                        case "transportation":
                            assistance_value = "Transportation Assistance"
                            purpose_value = "TRANSPORTATION EXPENSES"
                        case "burial":
                            assistance_value = "Funeral Assistance"
                            purpose_value = "FUNERAL EXPENSES"
                        case "food subsidy":
                            assistance_value = "Food Subsidy / Assistance"
                            purpose_value = "DAILY NEEDS"

                    self.setDropDown(driver, "select2-FA2type_financial_assistance-container", assistance_value)

                    # need testing
                    mode_release_caption = self.mode_release.currentText()
                    mode = self.mode_release_website_map.get(mode_release_caption, mode_release_caption).title()
                    self.setDropDown(driver, "select2-FA2mode_of_asssitance}-container", mode)

                    fund_source_caption = self.fund_source.currentText()

                    self.setDropDown(driver, "select2-FA2fund_source-container",
                                     self.fund_source_website_map.get(fund_source_caption, fund_source_caption))

                    self.setTextField(driver, "FA[2][purpose]", purpose_value)
                    self.setTextField(driver, "FA[2][amount_of_assistance]", self.amount.text())

                    self._accept_alert_if_present(driver)

                    if self.auto_next.isChecked() :
                        self.clickNextButton(driver, "Next")
                        self._accept_alert_if_present(driver)
                        self._accept_alert_if_present(driver)
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "approver":
                    worker = self._selected_worker()
                    website_value = worker[3] if worker else ""
                    self.setDropDown(driver, "select2-assessed_by-container", website_value)


                    selected_index = self.approved_by.currentIndex()
                    if selected_index != -1:
                        selected_key = self.approved_by.currentText()
                        selected_value = self.approved_by_website_map[selected_key]
                        self.setDropDown(driver, "select2-approved_by-container", selected_value)

                    self.setDropDown(driver, "select2-status-container", "Approved")
                    self.setDate(driver, "dt_assistanceProvided", self.interview_date.date())
                    if self.auto_submit.isChecked():
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
            return None
        except Exception as e:
            self.command_log.append(f"Error in : {e} ")
            return None

    def on_fill_crims_offline(self, driver):
        offline_city_lookup = self._city_lookup(self.client_city.currentText())
        region = self.region_gform_map.get(self.client_region.currentText(), self.client_region.currentText())

        province = self.province_gform_map.get(self.client_province.currentText(), self.client_province.currentText())

        gformTitle = self.getGFormTitle(driver)

        if self.offline_page_title == self.getGFormTitle(driver):
            winsound.MessageBeep()
        else:
            self.offline_page_title = gformTitle

        if gformTitle == "approved by":

            selected_index = self.approved_by.currentIndex()
            if selected_index != -1:
                selected_key = self.approved_by.currentText()
                selected_value = self.approved_by_gform_map[selected_key]
                self.setGFormRadioButton(driver, "", selected_value)

            self.setGFormRadioButton(driver, "REGION ASSESS", offline_city_lookup["region_gform"])
            self.setGFormRadioButton(driver, "PAYEE", "N/A")

            client_contact_value = self.client_contact_no.text()
            if client_contact_value == "":
                self.setGFormRadioButton(driver, "CLIENT CONTACT NUMBER", "N/A")
            else:
                self.setGFormRadioButtonOthers(driver, "CLIENT CONTACT NUMBER", client_contact_value)

            bene_contact_value = self.has_beneficiary.isChecked()
            if bene_contact_value == "":
                self.setGFormRadioButtonOthers(driver, "BENEFICIARY CONTACT NUMBER", bene_contact_value)
            else:
                self.setGFormRadioButton(driver, "BENEFICIARY CONTACT NUMBER", "N/A")

            self.setGFormRadioButton(driver, "STATUS", "APPROVED")

            if self.auto_submit.isChecked():
                self.clickSubmitButton(driver, "Submit")
        elif gformTitle == "beneficiary":
            if not self.has_beneficiary.isChecked():
                self.setGFormRadioButton(driver, "LASTNAME", "N/A")
                self.setGFormRadioButton(driver, "FIRST NAME","N/A")
                self.setGFormRadioButton(driver, "MIDDLE NAME", "N/A")
                self.setGFormRadioButton(driver, "EXTENSION NAME", "N/A")

                self.setGFormRadioButton(driver, "AGE", "N/A")
                self.setGFormRadioButton(driver, "BENEFICIARY CATEGORY", "N/A")
                self.setGFormRadioButton(driver, "SEX", "N/A")
                self.setGFormRadioButton(driver, "CIVIL STATUS", "N/A")
                date_str = "N/A"
            else:
                date_str = self.bene_bday.date().toString("MM-dd-yyyy")
                self.setGFormRadioButtonOthers(driver, "LASTNAME", self.bene_lastname.text())
                self.setGFormRadioButtonOthers(driver, "FIRST NAME", self.bene_firstname.text())
                self.setGFormRadioButtonOthers(driver, "MIDDLE NAME", self.bene_middlename.text())
                self.setGFormRadioButton(driver, "EXTENSION NAME", "N/A")

                self.setGFormRadioButtonOthers(driver, "AGE", self.bene_age.text())
                self.setGFormRadioButton(driver, "BENEFICIARY CATEGORY", "N/A")
                self.setGFormRadioButton(driver, "SEX", self.gender_gform_map.get(self.bene_gender.currentText(), self.bene_gender.currentText()))
                bene_civil_status_caption = self.bene_civil_status.currentText()
                self.setGFormRadioButton(driver, "CIVIL STATUS", self.civil_status_gform_map.get(bene_civil_status_caption, bene_civil_status_caption))

                self.setGFormDate(driver, "i50", self.bene_bday.date())

            self.setGFormTextField(driver, "i46 i47", date_str)

            mode_release_caption = self.mode_release.currentText()
            mode_of_release_string = self.mode_release_gform_map.get(mode_release_caption, mode_release_caption)
            self.setGFormRadioButton(driver, "MODE OF RELEASE", mode_of_release_string)
            self.setGFormRadioButton(driver, "DATE OF RELEASE", "2025")
            # i150 - INTERVIEW
            # i156 - DATE OF RELEASE
            self.setGFormDate(driver, "i150", self.interview_date.date())
            self.setGFormDate(driver, "i156", self.interview_date.date())

            worker = self._selected_worker()
            gform_value = worker[2] if worker else ""
            self.setGFormDropDown(driver, "i157 i160", gform_value)

            if self.auto_next.isChecked():
                self.clickGFormButton(driver, "Next")
        elif gformTitle == "barangay and district":
            self.setGFormTextField(driver, "i2 i3", self.client_barangay.currentText().upper())
            self.setGFormDropDown(driver, "i6 i9", "I")

            self.setGFormTextField(driver, "i22 i23", self.client_lastname.text())
            self.setGFormTextField(driver, "i12 i13", self.client_firstname.text())
            self.setGFormTextField(driver, "i17 i18", self.client_middlename.text())

            client_ext_value = self.client_ext.text().lower()
            if client_ext_value != "":
                if client_ext_value.lower() in ["jr", "sr"] and not client_ext_value.endswith("."):
                    client_ext_value = client_ext_value + "."
            else:
                client_ext_value = "N/A"
            self.setGFormDropDown(driver, "i26 i29", client_ext_value.lower())  # extension name

            gender_value = self.gender_gform_map.get(self.client_gender.currentText(), self.client_gender.currentText())
            self.setGFormDropDown(driver, "i31 i34", gender_value.upper())  # sex

            civil_status_caption = self.client_civil_status.currentText()
            civil_status_name = self.civil_status_gform_map[civil_status_caption]

            self.setGFormRadioButton(driver, "CIVIL STATUS", civil_status_name)

            self.setGFormDate(driver, "i61", self.client_bday.date())
            self.setGFormTextField(driver, "i63 i64", self.client_age.text())

            mode_of_admission_caption = self.mode_of_admission.currentText()
            self.setGFormRadioButton(driver, "MODE OF ADMISSION",
                                     self.mode_of_admission_map.get(mode_of_admission_caption, mode_of_admission_caption))

            self.setGFormTextField(driver, "i96 i97", self.amount.text())

            fund_source_caption = self.fund_source.currentText()
            fund_source_name = self.fund_source_gform_map[fund_source_caption]

            self.setGFormRadioButton(driver, "FUND SOURCE", fund_source_name)

            sector_choice = self.target_sector.currentText()
            sector_value = self.target_sector_gform_map.get(sector_choice, sector_choice)
            if sector_choice.lower() == "senior citizens" :
                sector_value = "senior citizens (no subcategories)"
            #     SENIOR CITIZENS (no subcategories)
            self.setGFormRadioButton(driver, "CLIENT CATEGORY", sector_value)

            self.setGFormRadioButton(
                driver, "CLIENT SUB-CATEGORY",
                self.sub_category_gform_map.get(self.sub_category.currentText(), self.sub_category.currentText()),
            )
            # "Medical", "Burial", "Transportation", "Cash Support", "Food Subsidy"
            match self.financial_assist.currentText().lower():
                case "medical":
                    self.setGFormRadioButton(driver, "TYPE OF ASSISTANCE", "MEDICAL ASSISTANCE")
                    self.setGFormRadioButton(driver, "PROBLEM PRESENTED", "FOR MEDICAL EXPENSES")
                    self.setGFormRadioButton(driver, "ASSESSMENT", "THE CLIENT SEEK'S MEDICAL ASSISTANCE TO AUGMENT MEDICAL EXPENSES")
                case "transportation":
                    self.setGFormRadioButton(driver, "TYPE OF ASSISTANCE", "TRANSPORTATION ASSISTANCE")
                    self.setGFormRadioButton(driver, "PROBLEM PRESENTED", "FOR TRAVEL EXPENSES")
                    self.setGFormRadioButton(driver, "ASSESSMENT",
                                         "THE CLIENT SEEK'S TRANSPORTATION ASSISTANCE TO AUGMENT TRAVEL EXPENSES")
                case "burial":
                    self.setGFormRadioButton(driver, "TYPE OF ASSISTANCE", "BURIAL ASSISTANCE")
                    self.setGFormRadioButton(driver, "PROBLEM PRESENTED", "FOR FUNERAL EXPENSES")
                    self.setGFormRadioButton(driver, "ASSESSMENT",
                                         "THE CLIENT SEEK'S BURIAL ASSISTANCE TO AUGMENT FUNERAL EXPENSES")
                case "food subsidy":
                    self.setGFormRadioButton(driver, "TYPE OF ASSISTANCE", "FOOD SUBSIDY")
                    self.setGFormRadioButton(driver, "PROBLEM PRESENTED", "FOR DAILY EXPENSES")
                    self.setGFormRadioButton(driver, "ASSESSMENT",
                                             "THE CLIENT SEEK'S FINANCIAL ASSISTANCE TO AUGMENT DAILY EXPENSES")

            self.setGFormRadioButton(driver, "OCCUPATION", "NONE OF THE ABOVE")
            self.setGFormRadioButton(driver, "SALARY", "0")

            relationship_caption = self.client_relationship.currentText()
            relationship_name = self.relationship_gform_map[relationship_caption]

            self.setGFormRadioButton(driver, "RELATIONSHIP TO BENEFICIARY", relationship_name)
            if self.auto_next.isChecked():
                self.clickGFormButton(driver, "Next")
        elif is_similar(gformTitle, province.lower()):
            if self.client_city.currentText() == "NONE OF THE ABOVE":
                self.stop_requested = True
            else:
                city_gform_value = self._city_lookup(self.client_city.currentText())["city_gform"]
                self.setGFormDropDown(driver, "i1 i4", city_gform_value)
                if self.auto_next.isChecked():
                    self.clickGFormButton(driver, "Next")
        elif is_similar(gformTitle, region.lower()):
            self.setGFormDropDown(driver, "i1 i4", province)
            if self.auto_next.isChecked():
                self.clickGFormButton(driver, "Next")
        else:
            self.setGFormRecordEmailCheckbox(driver)
            self.setGFormDate(driver, "i13", self.encoded_date.date())
            self.setGFormTextField(driver, "i15 i16", self.encoder_name.text())

            self.selectSingleItemFirstOption(driver)
            self.setGFormDropDown(
                driver, "i35 i38",
                self.region_gform_map.get(self.client_region.currentText(), self.client_region.currentText()),
            )
            if self.auto_next.isChecked():
                self.clickGFormButton(driver, "Next")

    def on_fill_crims_mov(self, driver):
        self.setGFormTextField(driver, "i2 i3", self.encoder_name.text())

        c_full_name = f'{self.client_firstname.text()} {self.client_middlename.text()} {self.client_lastname.text()}'
        self.setGFormTextField(driver, "i7 i8", c_full_name)

        if self.has_beneficiary.isChecked():
            b_full_name = f'{self.bene_firstname.text()} {self.bene_middlename.text()} {self.bene_lastname.text()}'
            self.setGFormTextField(driver, "i12 i13", b_full_name)
        else:
            self.setGFormTextField(driver, "i12 i13", c_full_name)

        self.setGFormTextField(driver, "i34 i35", self.amount.text())

        worker = self._selected_worker()
        gform_value = worker[2] if worker else ""
        self.setGFormTextField(driver, "i39 i40", gform_value)

        self.setGFormAssistance(driver)

        if self.auto_submit.isChecked():
            self.clickSubmitButton(driver, "Submit")

    def getGFormTitle(self, driver):
        try:
            # Locate the heading div with role='heading'
            heading = driver.find_element(By.XPATH, "//div[@role='heading']//div[contains(@class, 'aG9Vid')]")
            # Get the text
            content = heading.text.strip()
            self.command_log.append(f"Title: {content}. ")
            return content.lower()
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return ""
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return ""

    def setGFormTextField(self, driver, pk_id, value):
        try:
            text_field = driver.find_element(By.XPATH, f'//input[@aria-describedby="{pk_id}"]')

            if text_field and text_field.get_attribute("value") == "":
                text_field.send_keys(value)
            else:
                self.command_log.append("Text field is already filled. ")
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
        except Exception as e:
            self.command_log.append(f"Unexpected error: {e} ")

    def setGFormDate(self, driver, pk_id, value):
        """value is a QDate object."""
        try:
            date_str = value.toString("yyyy-MM-dd")  # native <input type="date"> value format
            date_field = driver.find_element(By.XPATH, f'//input[@aria-labelledby="{pk_id}"]')
            driver.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                date_field, date_str
            )
        except NoSuchElementException:
            self.command_log.append("Error: Element not found.")
        except Exception as e:
            self.command_log.append(f"Unexpected error: {e}")

    def setGFormRadioButton(self, driver, name, value):
        try:
            radio_groups = driver.find_elements(By.XPATH, "//div[@role='radiogroup']")

            for group in radio_groups:
                # Find the first radio button inside each group and click it
                radio_options = group.find_elements(By.XPATH, ".//div[@role='radio']")

                selected_option = None
                for option in radio_options:
                    if option.get_attribute("aria-checked") == "true":
                        selected_option = option
                        break  # Stop once we find a selected option

                if not selected_option:
                    if group.accessible_name.__contains__(name):
                        for option in radio_options:
                            option_text = option.get_attribute("aria-label")  # Get the option text
                            if is_similar(option_text.lower() and option_text.strip().lower(), value.lower()):
                                option.click()
                                WebDriverWait(driver, 2).until(
                                    lambda d: option.get_attribute("aria-checked") == "true"
                                )
                                self.command_log.append(f"Selected: {option_text}")
                                break  # Stop once we find and click the right option
                continue
        except NoSuchElementException:
            self.command_log.append(f"Error: Element entered not found.")
        except Exception as e:
            self.command_log.append(f"Unexpected error: {e} ")

    def setGFormRadioButtonOthers(self, driver, name, value):
        try:
            radio_groups = driver.find_elements(By.XPATH, "//div[@role='radiogroup']")

            for group in radio_groups:
                if name.lower() in group.accessible_name.lower():  # Match the group name (case-insensitive)

                    # Find all radio options within this group
                    radio_options = group.find_elements(By.XPATH, ".//div[@role='radio']")

                    for option in radio_options:
                        if option.get_attribute("aria-checked") == "true":
                            break  # Stop once we find a selected option

                        option_text = option.get_attribute("aria-label")  # Get the radio button label

                        # Check if the option is "Other:"
                        if option_text is None:
                            try:
                                option.click()  # Select "Other"

                                # Find the corresponding text input field inside the radio group
                                text_field = group.find_element(By.XPATH, ".//input[@type='text']")
                                text_field.send_keys(value)  # Input custom text
                                WebDriverWait(driver, 2).until(
                                    lambda d: (text_field.get_attribute("value") or "") != ""
                                )

                                self.command_log.append(f"Selected: {option_text}, Entered: {value}")
                                break  # Stop after finding the first "Other" option
                            except NoSuchElementException:
                                self.command_log.append("Error: No text field found for 'Other' option.")
                                break  # Stop after finding and selecting "Other:"
                    continue  # Move to the next radio group if needed
        except NoSuchElementException:
            self.command_log.append(f"Error: Element entered not found.")
        except Exception as e:
            self.command_log.append(f"Unexpected error: {e} ")

    def selectSingleItemFirstOption(self, driver):
        radio_groups = driver.find_elements(By.XPATH, "//div[@role='radiogroup']")

        for group in radio_groups:
            # Find the first radio button inside each group and click it
            radio_options = group.find_elements(By.XPATH, ".//div[@role='radio']")

            selected_option = None
            for option in radio_options:
                if option.get_attribute("aria-checked") == "true":
                    selected_option = option
                    break  # Stop once we find a selected option

            if not selected_option:
                if len(radio_options) == 1:
                    radio_options[0].click()
                    self.command_log.append("Field :" + group.accessible_name + " = " + radio_options[0].accessible_name)
                    WebDriverWait(driver, 2).until(
                        lambda d: radio_options[0].get_attribute("aria-checked") == "true"
                    )

    def setGFormRecordEmailCheckbox(self, driver):
        try:
            checkboxes = driver.find_elements(By.XPATH, "//div[@role='checkbox']")
            for checkbox in checkboxes:
                if checkbox.get_attribute("aria-checked") != "true":
                    checkbox.click()
                    self.command_log.append("Checked: " + checkbox.accessible_name)
                    WebDriverWait(driver, 2).until(
                        lambda d: checkbox.get_attribute("aria-checked") == "true"
                    )
        except NoSuchElementException:
            self.command_log.append("Error: Element not found.")
        except Exception as e:
            self.command_log.append(f"Unexpected error: {e}")

    def selectAllItemFirstOption(self, driver):
        try:
            radio_groups = driver.find_elements(By.XPATH, "//div[@role='radiogroup']")

            for group in radio_groups:
                # Find the first radio button inside each group and click it
                radio_options = group.find_elements(By.XPATH, ".//div[@role='radio']")

                selected_option = None
                for option in radio_options:
                    if option.get_attribute("aria-checked") == "true":
                        selected_option = option
                        break  # Stop once we find a selected option

                if not selected_option:
                    radio_options[0].click()
                    self.command_log.append("Field :" + group.accessible_name + " = " + radio_options[0].accessible_name + " ")
                    WebDriverWait(driver, 2).until(
                        lambda d: radio_options[0].get_attribute("aria-checked") == "true"
                    )
                    return None
                return None
            return None
        except NoSuchElementException:
            self.command_log.append(f"Error: Dropdown element not found. ")
            return False
        except Exception as e:
            return False

    def setGFormDropDown(self, driver, pk_id, value):
        try:

            # Locate the dropdown field (adjust XPath based on your form structure)
            dropdown = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[@role='listbox' and @aria-labelledby='{pk_id}']"))
            )
            if dropdown:
                # Click to open the dropdown
                dropdown.click()

                options = WebDriverWait(driver, 8).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[@role='option']"))
                )

                selected_option = None
                for option in options:
                    name_text = option.get_attribute("data-value").strip().lower()
                    if is_similar(name_text, value):
                        selected_option = option
                        break

                # Select the matched option if found
                if selected_option:
                    selected_option.click()
                    self.command_log.append(f"Selected: {selected_option.get_attribute('data-value')}")
                    return None
                return None
            else:
                self.command_log.append("No matching name found! ")
                return True
        except NoSuchElementException:
            self.command_log.append(f"Error: Dropdown element not found. ")
            return False
        except Exception as e:
            return False

    def setGFormAssistance(self, driver):
        # Find all groups of radio buttons
        radio_groups = driver.find_elements(By.XPATH, "//div[@role='radiogroup']")
        for group in radio_groups:
            # Find the first radio button inside each group and click it
            radio_options = group.find_elements(By.XPATH, ".//div[@role='radio']")

            selected_option = None
            for option in radio_options:
                if option.get_attribute("aria-checked") == "true":
                    selected_option = option
                    break  # Stop once we find a selected option

            if (not selected_option):
                if group.accessible_name.__contains__("TYPES OF ASSISSTANCE"):
                    # "Medical", "Burial", "Transportation", "Cash Support", "Food Subsidy"
                    match self.financial_assist.currentText().lower():
                        case "medical":
                            radio_options[3].click()
                        case "transportation":
                            radio_options[2].click()
                        case "burial":
                            radio_options[1].click()
                        case "food subsidy":
                            radio_options[0].click()
                        case _:
                            radio_options[3].click()
                            self.command_log.append("Field :" + group.accessible_name + " = " + radio_options[1].accessible_name + " ")
                    continue

    def clickGFormButton(self, driver, value):
        try:
            button = driver.find_element(By.XPATH, f"//span[contains(text(), '{value}')]")

            if button is not None:
                button.click()
                self.command_log.append(f"Button click: {value} ")
            return True
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return False
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return False

    def setDate(self, driver, name, value):
        """value is a QDate object."""
        try:
            date_str = value.toString("MM-dd-yyyy")
            date_field = driver.find_element(By.ID, name)
            date_field.send_keys(date_str)
            self.command_log.append(f"Date {name}: {date_str}")
        except Exception as e:
            self.command_log.append(f"Error in Date {e}")

    def checkIfExisting(self, driver, name):
        try:
            div_element = driver.find_element(By.ID, name)

            if div_element is not None:
                if div_element.is_displayed() and div_element.is_enabled():
                    return True
                else:
                    return False
            else:
                return False
        except NoSuchElementException:
            self.command_log.append(f"Error: Element with {name} not found. ")
        except Exception as e:
            self.command_log.append(f"Element not existing {e} ")
            return False

    def selectCheckBox(self, driver, name):
        try:
            div_element = driver.find_element(By.ID, name)

            if div_element is not None:
                div_element.click()
        except NoSuchElementException:
            self.command_log.append(f"Error: Element with {name} not found. ")
        except Exception as e:
            self.command_log.append(f"Element not existing {e} ")

    def selectDefaultCheckBox(self, driver, name):
        try:
            div_element = driver.find_element(By.ID, name)

            if div_element is not None:
                if div_element.is_selected():
                    return False
                else:
                    div_element.click()
                    return True
            return True
        except NoSuchElementException:
            self.command_log.append(f"Error: Element with {name} not found. ")
        except Exception as e:
            self.command_log.append(f"Element not existing {e} ")
            return False

    def clickButton(self, driver, name):
        try:
            div_element = driver.find_element(By.ID, name)

            if div_element is not None:
                div_element.click()
        except NoSuchElementException:
            self.command_log.append(f"Error: Element with {name} not found. ")
        except Exception as e:
            self.command_log.append(f"Element not existing {e} ")

    def setDropDown(self, driver, name, value):
        try:
            element = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.ID, name)))

            # Check if the 'title' attribute exists and is not empty
            title_value = element.get_attribute("title")

            if title_value:
                self.command_log.append(f"Field {name}: already selected ")
            else:
                combobox = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, f"//span[@role='combobox' and @aria-labelledby='{name}']"))
                )
                # Click to open the dropdown
                combobox.click()

                # Define the option text to select
                option = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH,
                                                f"//li[contains(@class, 'select2-results__option') and contains(normalize-space(), '{value}')]"))
                )
                option.click()
                self.command_log.append(f"Field {name}: {value} ")
        except NoSuchElementException:
            self.command_log.append(f"Error: Element with {name} not found. ")
        except TimeoutException:
            self.command_log.append(f"Error: Timed out while selecting {name} -> {value}.")
        except Exception as e:
            return

    def setTextField(self, driver, name, value):
        try:

            # Find the input field by ID and fill it
            input_field = driver.find_element(By.ID, name)

            # Check if the field already contains the desired value
            current_text = input_field.get_attribute("value").strip()
            if current_text == value:
                self.command_log.append(f"Field {name} already contains the desired value. Skipping...")
                return

            input_field.send_keys(value)
            self.command_log.append(f"Field {name}: {value} ")
        except NoSuchElementException:
            self.command_log.append(f"Error: Element with {name} not found. ")
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")

    def setTextAreaField(self, driver, name, value):
        try:

            # Find the input field by ID and fill it
            username_field = driver.find_element(By.NAME, name)
            username_field.send_keys(value)
            self.command_log.append(f"Field {name}: {value} ")
        except NoSuchElementException:
            self.command_log.append(f"Error: Element with {name} not found. ")
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")

    def getTitle(self, driver):
        try:
            visible_fieldset = driver.find_element(By.XPATH, "//fieldset[contains(@style, 'display: block;')]")

            element = visible_fieldset.find_element(By.XPATH, ".//h6[contains(@class, 'form-wizard-title')]")
            # Get full text and remove the <span> and <small> parts
            full_text = element.text.strip()

            # Remove the <span> part (number count)
            span_text = element.find_element(By.TAG_NAME, "span").text.strip()
            full_text = full_text.replace(span_text, "").strip()

            # Remove the <small> part if present
            small_tags = element.find_elements(By.TAG_NAME, "small")
            if small_tags:
                full_text = full_text.replace(small_tags[0].text.strip(), "").strip()
            self.command_log.append(f"Extracted Text: {full_text.lower()} ")
            return full_text.lower()
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")

    def hasASearchField(self, driver, value):
        try:

            # Locate the search input field using placeholder
            search_input = driver.find_element(By.XPATH, "//input[@placeholder='Search']")

            # Type the search query
            search_input.clear()
            search_input.send_keys(value)
            self.command_log.append(f"Search Text: {value} ")
            time.sleep(1)
            return True
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return False
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return False

    def clickHrefButton(self, driver, value):
        try:
            add_client_button = driver.find_element(By.XPATH, f"//a[contains(text(), '{value}')]")

            self.command_log.append(f"Button click: {value} ")
            return True
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return False
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return False

    def clickAddButton(self, driver, value):
        try:
            add_client_button = driver.find_element(By.XPATH, f"//a[contains(text(), '{value}')]")
            add_client_button.click()
            self.command_log.append(f"Button click: {value} ")
            return True
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return False
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return False

    def clickIconButton(self, driver):
        try:
            icon = driver.find_element(By.CLASS_NAME, "glyphicon-share-alt")

            # Perform the click action
            icon.click()
            return True
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return False
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return False

    def searchResult(self, driver):
        try:
            icon = driver.find_element(By.CLASS_NAME, "no-results")
            return True
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return False
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return False

    def clickNextButton(self, driver, value):
        try:
            next_button = driver.find_element(By.XPATH, f"//button[normalize-space(text())='{value}']")
            if next_button is not None:
                next_button.click()
            self.command_log.append(f"Button click: {value} ")
            return True
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return False
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return False

    def clickSubmitButton(self, driver, value):
        try:
            # Find the element by XPath (using aria-label or text)
            element = driver.find_element(By.XPATH, f"//div[@role='button' and @aria-label='{value}']")
            if element is not None:
                element.click()
            self.command_log.append(f"Button click: {value} ")
            return True
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return False
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return False

    def is_end_of_website(self, driver):
        try:
            website_finished = driver.find_element(By.XPATH, "//h3[@class='panel-title' and contains(text(), 'Social Worker Assessment List')]")
            if website_finished is not None:
                return True
            return False
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return False
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return False

    def is_end_of_g_form(self, driver):
        try:
            element = driver.find_element(By.XPATH, "//div[@class='vHW8K' and text()='Your response has been recorded.']")
            if element is not None:
                return True
            return False
        except NoSuchElementException:
            self.command_log.append(f"Error: Element not found. ")
            return False
        except Exception as e:
            self.command_log.append(f"Error in Element {e} ")
            return False

    def proceed_to_new(self, driver):
        self.clickHrefButton(driver, "Home")

    def same_address_event(self, state=None):
        if self.same_address.isChecked():
            self.bene_house_street.setText(self.client_house_street.text())
            self.bene_region.setCurrentText(self.client_region.currentText())
            self.bene_province.setCurrentText(self.client_province.currentText())
            self.bene_city.setCurrentText(self.client_city.currentText())
            self.bene_barangay.setCurrentText(self.client_barangay.currentText())
        else:
            self.bene_house_street.setText("")
            self.bene_province.setCurrentIndex(-1)

    def same_contact_event(self, state=None):
        if self.same_contact.isChecked():
            self.bene_contact_no.setText(self.client_contact_no.text())

    def has_beneficiary_event(self, state=None):
        if not self.has_beneficiary.isChecked():
            for w in [self.bene_lastname, self.bene_firstname, self.bene_middlename,
                      self.bene_age, self.bene_ext, self.bene_contact_no,
                      self.bene_house_street]:
                w.setText("")
            self.bene_relationship.setCurrentIndex(-1)
            self.bene_gender.setCurrentIndex(-1)
            self.bene_civil_status.setCurrentIndex(-1)
            self.bene_province.setCurrentIndex(-1)
        else:
            self.bene_relationship.setCurrentIndex(self.client_relationship.currentIndex())

    def on_checkbox_change(self, state=None):
        self.load_data_person()

    def on_selection(self, index=None):
        name = self.client_civil_status.currentText()
        caption = self.civil_status_gform_map.get(name, "")
        print(f"Selected Caption: {caption} Name: {name}")

    def _selected_worker(self):
        """Return (id, full_name, gform_value, website_value) for the currently selected social worker, or None."""
        index = self.social_worker.currentIndex()
        if 0 <= index < len(self.social_worker_list):
            return self.social_worker_list[index]
        return None

    def reload_choice_items(self):
        self.social_worker_list = get_all_workers()
        self.social_worker.clear()
        self.social_worker_choices = [full_name for (_id, full_name, _gform, _website) in self.social_worker_list]
        self.social_worker.addItems(self.social_worker_choices)

    def on_social_worker_editing_finished(self):
        """Unlike Barangay, Social Worker must reference a real worker record —
        typing is only for locating an existing choice via the dropdown (which now
        opens on click, same as Barangay). Any text that isn't an exact match to a
        known choice once editing ends is discarded rather than saved."""
        try:
            index = self.social_worker_choices.index(self.social_worker.currentText())
        except ValueError:
            index = -1
        self.social_worker.setCurrentIndex(index)

    def on_export(self, event=None):
        self.command_log.append("Exporting, please wait...")
        QApplication.processEvents()

        def export_task():
            try:
                export_sqlite_to_csv(DB_NAME, "person", "person-backup-db.csv")
                self._sig_msg_box.emit("Success", "Export completed successfully!", "info")
            except Exception as e:
                self._sig_msg_box.emit("Error", str(e), "error")
            finally:
                self._sig_log.emit("Export done.")

        threading.Thread(target=export_task, daemon=True).start()


class ActivationFrame(QDialog):
    def __init__(self, on_activate_success):
        super().__init__()
        self.on_activate_success = on_activate_success
        self.setWindowTitle("Activate App")
        self.setFixedSize(480, 230)
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Device Id:"))
        self.label_text = get_device_id()
        device_label = QLabel(self.label_text)
        font = device_label.font()
        font.setBold(True)
        device_label.setFont(font)
        device_label.setCursor(Qt.CursorShape.PointingHandCursor)
        device_label.mousePressEvent = self._copy_to_clipboard
        layout.addWidget(device_label)

        layout.addWidget(QLabel("License key:"))
        self.key_input = QLineEdit()
        layout.addWidget(self.key_input)

        activate_btn = QPushButton("Activate")
        activate_btn.setObjectName("addBtn")
        activate_btn.clicked.connect(self._on_activate)
        layout.addWidget(activate_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

    def _copy_to_clipboard(self, event):
        QApplication.clipboard().setText(self.label_text)
        QMessageBox.information(self, "Success", "Copied to clipboard!")

    def _on_activate(self):
        user_key = self.key_input.text().strip()
        if not user_key:
            QMessageBox.critical(self, "Error", "Please enter a key.")
            return
        if activate_trial(user_key):
            QMessageBox.information(self, "Success", "Activation successful!")
            self.status_label.setText("Activated ✔️")
            self.key_input.setEnabled(False)
            self.accept()
            self.on_activate_success()
        else:
            QMessageBox.critical(self, "Error", "Invalid key.")
            self.status_label.setText("Activation failed ❌")


if __name__ == "__main__":
    install_crash_logging()
    app = QApplication(sys.argv)
    init_db()

    if is_trial_valid():
        window = MyFrame()
        window.show()
    else:
        def open_main():
            window = MyFrame()
            window.show()

        dlg = ActivationFrame(open_main)
        dlg.exec()

    sys.exit(app.exec())
