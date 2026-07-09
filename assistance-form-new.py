import sys
import time
import threading
import os
import pickle
import csv
import string
import random
import sqlite3

from selenium.webdriver.common.alert import Alert
from datetime import datetime
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, QTabWidget,
    QScrollArea, QTableWidget, QTableWidgetItem, QTextEdit, QFrame,
    QMessageBox, QSizePolicy, QHeaderView,
)
from PySide6.QtCore import Qt, QDate, Signal, QObject, QTimer
from PySide6.QtGui import QColor, QFont, QCursor

from widgets import AllCapsLineEdit, NoScrollComboBox

from utilities import is_similar
from utilities import get_date_value
from utilities import disable_mousewheel
from utilities import set_date_value

from db_new_person import init_db_person, DB_NAME
from db_new_person import get_all_person_by_encoded
from db_new_person import set_encoded
from db_new_person import insert_person, update_person, delete_person_by_id

from db_worker import init_db_worker
from db_worker import get_all_workers, get_worker_id
from db_worker import insert_worker, update_worker, delete_worker_by_id

from config import mov_url
from config import offline_url
from config import website_url

from config import gender_list
from config import civil_status_list
from config import fund_source_list
from config import target_sector_list
from config import financial_assistance_list
from config import relationship_list
from config import list_of_city
from config import district_city
from config import mode_of_release
from config import approved_by_list
from config import client_sub_category

from license import is_trial_valid, activate_trial, get_device_id
import winsound
import keyboard

# Backward-compatible aliases within this file
AllCapsTextCtrl = AllCapsLineEdit
AllTextCtrl = QLineEdit


# Initialize SQLite database
def init_db():
    init_db_person()
    init_db_worker()

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
    row_data_sw = {}  # ID -> full data

    # Thread-safe UI signals
    _sig_log = Signal(str)
    _sig_set_running = Signal(bool)
    _sig_reload_person = Signal()
    _sig_select_first = Signal()
    _sig_msg_box = Signal(str, str, str)  # title, message, kind (info/error)

    def load_data_worker(self):
        selected_rows = self.list_ctrl_worker.selectedItems()
        self.selected_worker_id = int(selected_rows[0].text()) if selected_rows else None
        self.list_ctrl_worker.setRowCount(0)
        for row in get_all_workers():
            r = self.list_ctrl_worker.rowCount()
            self.list_ctrl_worker.insertRow(r)
            for col, val in enumerate(row):
                self.list_ctrl_worker.setItem(r, col, QTableWidgetItem(str(val)))
            self.row_data_sw[row[0]] = {
                "id": row[0], "sw_lname": row[1], "sw_fname": row[2],
                "sw_mname": row[3], "search_thru_first_name": row[4],
            }

    def on_add_worker(self, event=None):
        reply = QMessageBox.question(self, "Add", "Are you sure you want to add?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if insert_worker(
                self.sw_last_name.text(), self.sw_first_name.text(),
                self.sw_middle_name.text(), self.sw_thru_first_name.isChecked()
            ):
                self.load_data_worker()
                self.reload_choice_items()
            else:
                QMessageBox.critical(self, "Error", "Record already exist.")

    def on_update_worker(self, event=None):
        reply = QMessageBox.question(self, "Update", "Are you sure you want to update?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.selected_worker_id:
                update_worker(
                    self.selected_worker_id,
                    self.sw_last_name.text(), self.sw_first_name.text(),
                    self.sw_middle_name.text(), self.sw_thru_first_name.isChecked()
                )
                self.load_data_worker()
                self.reload_choice_items()

    def on_delete_worker(self, event=None):
        reply = QMessageBox.question(self, "Delete", "Are you sure you want to delete?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.selected_worker_id:
                delete_worker_by_id(self.selected_worker_id)
                self.load_data_worker()
                self.reload_choice_items()

    def on_select_worker(self):
        selected = self.list_ctrl_worker.selectedItems()
        if not selected:
            return
        row = self.list_ctrl_worker.currentRow()
        worker_id = int(self.list_ctrl_worker.item(row, 0).text())
        if worker_id in self.row_data_sw:
            worker = self.row_data_sw[worker_id]
            self.selected_worker_id = worker["id"]
            self.sw_last_name.setText(worker["sw_lname"])
            self.sw_first_name.setText(worker["sw_fname"])
            self.sw_middle_name.setText(worker["sw_mname"])
            self.sw_thru_first_name.setChecked(bool(worker["search_thru_first_name"]))

    def load_data_person(self):
        is_encoded = "1" if self.cb_encoded.isChecked() else "0"
        selected_row = self.list_ctrl.currentRow()
        self.list_ctrl.setRowCount(0)
        self.row_data.clear()

        sw_color_map = {}
        sw_column_index = 7
        assist_map = {0: "Medical", 1: "Burial", 2: "Transportation", 3: "Cash Support", 4: "Food"}

        for row in get_all_person_by_encoded(is_encoded):
            sw_value = row[sw_column_index]
            if sw_value not in sw_color_map:
                sw_color_map[sw_value] = QColor(
                    random.randint(180, 255),
                    random.randint(200, 255),
                    random.randint(180, 255)
                )

            assist = assist_map.get(row[4], "")
            r = self.list_ctrl.rowCount()
            self.list_ctrl.insertRow(r)
            for col, val in enumerate([
                str(row[0]), row[12], str(row[13]), str(row[14]), str(row[15]),
                str(row[17]), str(row[18]), assist, str(row[5]), str(row[7]), str(row[38])
            ]):
                item = QTableWidgetItem(val)
                self.list_ctrl.setItem(r, col, item)

            # Row color
            bg = sw_color_map[sw_value]
            if row[40] == 1:
                bg = QColor(255, 0, 0)
            for col in range(self.list_ctrl.columnCount()):
                self.list_ctrl.item(r, col).setBackground(bg)
                if row[37] == 1:
                    self.list_ctrl.item(r, col).setForeground(QColor(0, 0, 255))

            self.row_data[row[0]] = {
                "id": row[0], "encoder_name": row[1], "date_encoded": row[2],
                "target_sector": row[3], "financial_assist": row[4], "amount": row[5],
                "fund_source": row[6], "sw_lname": row[7], "sw_fname": row[8],
                "sw_mname": row[9], "interview_date": row[10], "client_relationship": row[11],
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
            }

        if 0 <= selected_row < self.list_ctrl.rowCount():
            self.list_ctrl.selectRow(selected_row)

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
                self.sw_lname.text(), self.sw_fname.text(), self.sw_mname.text(),
                get_date_value(self.interview_date),
                self.client_relationship.currentIndex(),
                self.client_lastname.text(), self.client_firstname.text(),
                self.client_middlename.text(), self.client_ext.text(),
                self.client_gender.currentIndex(),
                get_date_value(self.client_bday), self.client_age.text(),
                self.client_contact_no.text(),
                self.client_civil_status.currentIndex(),
                self.client_house_street.text(), self.client_barangay.text(),
                self.client_city.currentIndex(),
                self.bene_relationship.currentIndex(),
                self.bene_lastname.text(), self.bene_firstname.text(),
                self.bene_middlename.text(), self.bene_ext.text(),
                self.bene_gender.currentIndex(),
                get_date_value(self.bene_bday), self.bene_age.text(),
                self.bene_contact_no.text(),
                self.bene_civil_status.currentIndex(),
                self.bene_house_street.text(), self.bene_barangay.text(),
                self.bene_city.currentIndex(),
                self.has_beneficiary.isChecked(),
                self.mode_release.currentIndex(),
                self.approved_by.currentIndex(),
                self.sub_category.currentIndex(),
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
                    self.sw_lname.text(), self.sw_fname.text(), self.sw_mname.text(),
                    get_date_value(self.interview_date),
                    self.client_relationship.currentIndex(),
                    self.client_lastname.text(), self.client_firstname.text(),
                    self.client_middlename.text(), self.client_ext.text(),
                    self.client_gender.currentIndex(),
                    get_date_value(self.client_bday), self.client_age.text(),
                    self.client_contact_no.text(),
                    self.client_civil_status.currentIndex(),
                    self.client_house_street.text(), self.client_barangay.text(),
                    self.client_city.currentIndex(),
                    self.bene_relationship.currentIndex(),
                    self.bene_lastname.text(), self.bene_firstname.text(),
                    self.bene_middlename.text(), self.bene_ext.text(),
                    self.bene_gender.currentIndex(),
                    get_date_value(self.bene_bday), self.bene_age.text(),
                    self.bene_contact_no.text(),
                    self.bene_civil_status.currentIndex(),
                    self.bene_house_street.text(), self.bene_barangay.text(),
                    self.bene_city.currentIndex(),
                    self.has_beneficiary.isChecked(),
                    self.mode_release.currentIndex(),
                    self.approved_by.currentIndex(),
                    self.sub_category.currentIndex(),
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
        self.client_barangay.setText(person["client_barangay"])
        self.client_city.setCurrentIndex(person["client_city"])
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
        self.bene_barangay.setText(person["bene_barangay"])
        self.bene_city.setCurrentIndex(person["bene_city"])

        self.financial_assist.setCurrentIndex(person["financial_assist"])
        self.mode_release.setCurrentIndex(person["mode_release"])
        self.approved_by.setCurrentIndex(person["approved_by"])
        self.sub_category.setCurrentIndex(person["sub_category"])
        self.amount.setText(person["amount"])
        self.fund_source.setCurrentIndex(person["fund_source"])
        self.sw_lname.setText(person["sw_lname"])
        self.sw_fname.setText(person["sw_fname"])
        self.sw_mname.setText(person["sw_mname"])
        set_date_value(self.interview_date, person["interview_date"])
        self.has_beneficiary.setChecked(bool(person["has_beneficiary"]))
        self.sw_last_name.setText(person["sw_lname"])
        self.sw_first_name.setText(person["sw_fname"])
        self.sw_middle_name.setText(person["sw_mname"])

        data_id = get_worker_id(person["sw_lname"], person["sw_fname"], person["sw_mname"])
        if data_id:
            for index, (id_value, lname, fname, mname, thru) in enumerate(self.social_worker_list):
                if id_value == data_id[0]:
                    self.social_worker.setCurrentIndex(index)
                    break
        else:
            self.social_worker.setCurrentIndex(-1)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Client Assistance Form")
        self.resize(700, 700)

        self.selected_person_id = None
        self.selected_worker_id = None
        self.driver = None
        self.is_running = False
        self.stop_requested = False
        self.is_auto_fill = False
        self.is_finished_refresh = False

        keyboard.add_hotkey('shift+enter', self.on_add_person)

        central = QWidget()
        self.setCentralWidget(central)
        self.sizer = QVBoxLayout(central)

        # ── Scrollable area ──────────────────────────────────────────────
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.scroll_sizer = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)

        # ── Tab Widget ───────────────────────────────────────────────────
        notebook = QTabWidget()

        client_panel = QWidget()
        bene_panel = QWidget()
        sw_panel = QWidget()

        box_sizer_client = QVBoxLayout(client_panel)
        box_sizer_bene = QVBoxLayout(bene_panel)
        box_sizer_sw = QVBoxLayout(sw_panel)

        # ── Client Tab ───────────────────────────────────────────────────
        self.has_beneficiary = QCheckBox("Has Beneficiary")
        self.has_beneficiary.stateChanged.connect(self.has_beneficiary_event)
        box_sizer_client.addWidget(self.has_beneficiary)

        self.relationship_choices = [name for _, name in relationship_list]
        self.relationship_data_map = {value: name for name, value in relationship_list}

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
        self.client_gender = NoScrollComboBox()
        self.client_gender.addItems(gender_list)
        self.client_gender.setCurrentIndex(0)
        self.client_gender.currentIndexChanged.connect(self.on_choice_change_client)
        cl_gender_col.addWidget(self.client_gender)
        cl_gender_civil.addLayout(cl_gender_col)

        self.civil_status_choices = [name for _, name in civil_status_list]
        self.civil_status_data_map = {value: name for name, value in civil_status_list}
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

        cl_address = QHBoxLayout()
        cl_house_col = QVBoxLayout()
        cl_house_col.addWidget(QLabel("House | Street No:"))
        self.client_house_street = AllCapsLineEdit()
        cl_house_col.addWidget(self.client_house_street)
        cl_address.addLayout(cl_house_col)

        cl_brgy_col = QVBoxLayout()
        cl_brgy_col.addWidget(QLabel("Barangay"))
        self.client_barangay = QLineEdit()
        cl_brgy_col.addWidget(self.client_barangay)
        cl_address.addLayout(cl_brgy_col)

        cl_city_col = QVBoxLayout()
        cl_city_col.addWidget(QLabel("City | Municipality"))
        self.client_city = NoScrollComboBox()
        self.client_city.addItems(list_of_city)
        cl_city_col.addWidget(self.client_city)
        cl_address.addLayout(cl_city_col)
        box_sizer_client.addLayout(cl_address)

        box_sizer_client.addWidget(QLabel("Target Sector"))
        self.target_sector = NoScrollComboBox()
        self.target_sector.addItems(target_sector_list)
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
        self.bene_gender.addItems(gender_list)
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

        bene_address = QHBoxLayout()
        bene_house_col = QVBoxLayout()
        bene_house_col.addWidget(QLabel("House | Street No:"))
        self.bene_house_street = AllCapsLineEdit()
        bene_house_col.addWidget(self.bene_house_street)
        bene_address.addLayout(bene_house_col)

        bene_brgy_col = QVBoxLayout()
        bene_brgy_col.addWidget(QLabel("Barangay"))
        self.bene_barangay = AllCapsLineEdit()
        bene_brgy_col.addWidget(self.bene_barangay)
        bene_address.addLayout(bene_brgy_col)

        bene_city_col = QVBoxLayout()
        bene_city_col.addWidget(QLabel("City | Municipality"))
        self.bene_city = NoScrollComboBox()
        self.bene_city.addItems(list_of_city)
        bene_city_col.addWidget(self.bene_city)
        bene_address.addLayout(bene_city_col)
        box_sizer_bene.addLayout(bene_address)

        box_sizer_bene.addWidget(QLabel("Target Sector Beneficiary"))
        self.target_sector_bene = NoScrollComboBox()
        self.target_sector_bene.addItems(target_sector_list)
        self.target_sector_bene.setCurrentIndex(0)
        box_sizer_bene.addWidget(self.target_sector_bene)

        notebook.addTab(bene_panel, "Beneficiary Details")

        # ── Social Worker Tab ────────────────────────────────────────────
        box_sizer_sw.addSpacing(10)
        sw_caption_sizer = QHBoxLayout()
        sw_caption_sizer.addWidget(QLabel("Fullname (SW)"))
        self.sw_thru_first_name = QCheckBox("Search thru Firstname")
        sw_caption_sizer.addWidget(self.sw_thru_first_name)
        box_sizer_sw.addLayout(sw_caption_sizer)

        self.sw_last_name = QLineEdit()
        self.sw_last_name.setPlaceholderText("Last Name")
        self.sw_first_name = QLineEdit()
        self.sw_first_name.setPlaceholderText("First Name")
        self.sw_middle_name = QLineEdit()
        self.sw_middle_name.setPlaceholderText("Middle Name")
        sw_fullname_sizer = QHBoxLayout()
        sw_fullname_sizer.addWidget(self.sw_last_name)
        sw_fullname_sizer.addWidget(self.sw_first_name)
        sw_fullname_sizer.addWidget(self.sw_middle_name)
        box_sizer_sw.addLayout(sw_fullname_sizer)

        btn_sw_add = QPushButton("Add")
        btn_sw_update = QPushButton("Update")
        btn_sw_delete = QPushButton("Delete")
        btn_sw_add.clicked.connect(self.on_add_worker)
        btn_sw_update.clicked.connect(self.on_update_worker)
        btn_sw_delete.clicked.connect(self.on_delete_worker)
        sw_btn_sizer = QHBoxLayout()
        sw_btn_sizer.addWidget(btn_sw_add)
        sw_btn_sizer.addWidget(btn_sw_update)
        sw_btn_sizer.addWidget(btn_sw_delete)
        box_sizer_sw.addLayout(sw_btn_sizer)

        self.list_ctrl_worker = QTableWidget(0, 5)
        self.list_ctrl_worker.setHorizontalHeaderLabels(["ID", "Lastname", "Firstname", "Middlename", "Thru Firstname"])
        self.list_ctrl_worker.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.list_ctrl_worker.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.list_ctrl_worker.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.list_ctrl_worker.itemSelectionChanged.connect(self.on_select_worker)
        box_sizer_sw.addWidget(self.list_ctrl_worker)

        notebook.addTab(sw_panel, "Social Worker")

        self.scroll_sizer.addWidget(notebook, 1)

        # ── Assistance Section (below tabs) ─────────────────────────────
        assist_box = QVBoxLayout()

        assistance_sizer = QHBoxLayout()
        amount_col = QVBoxLayout()
        amount_col.addWidget(QLabel("Amount:"))
        self.amount = QLineEdit()
        amount_col.addWidget(self.amount)
        assistance_sizer.addLayout(amount_col)

        release_col = QVBoxLayout()
        release_col.addWidget(QLabel("Mode of Release"))
        self.mode_release = NoScrollComboBox()
        self.mode_release.addItems(mode_of_release)
        self.mode_release.setCurrentIndex(0)
        release_col.addWidget(self.mode_release)
        assistance_sizer.addLayout(release_col)

        financial_col = QVBoxLayout()
        financial_col.addWidget(QLabel("Assistance"))
        self.financial_assist = NoScrollComboBox()
        self.financial_assist.addItems(financial_assistance_list)
        self.financial_assist.setCurrentIndex(4)
        financial_col.addWidget(self.financial_assist)
        assistance_sizer.addLayout(financial_col)

        self.fund_source_choices = [name for _, name in fund_source_list]
        self.fund_source_data_map = {value: name for name, value in fund_source_list}
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
        self.sub_category = NoScrollComboBox()
        self.sub_category.addItems(list(client_sub_category.keys()))
        subcat_col.addWidget(self.sub_category)
        mode_sizer.addLayout(subcat_col)

        mode_admit_col = QVBoxLayout()
        mode_admit_col.addWidget(QLabel("Mode of Admission:"))
        self.mode_of_admission = NoScrollComboBox()
        self.mode_of_admission.addItems(["On-site", "Walk-in", "Referral"])
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
        self.social_worker_choices = [f"{fname}, {mname}, {lname}" for (_id, lname, fname, mname, _thru) in self.social_worker_list]

        worker_label_sizer = QHBoxLayout()
        worker_label_sizer.addWidget(QLabel("Social Worker"))
        assist_box.addLayout(worker_label_sizer)

        worker_sizer = QHBoxLayout()
        self.social_worker_filter = QLineEdit()
        self.social_worker_filter.textChanged.connect(self.on_sw_text_change)
        worker_sizer.addWidget(self.social_worker_filter, 2)
        self.social_worker = NoScrollComboBox()
        self.social_worker.addItems(self.social_worker_choices)
        self.social_worker.currentIndexChanged.connect(self.on_selection_worker)
        worker_sizer.addWidget(self.social_worker, 8)
        assist_box.addLayout(worker_sizer)

        self.sw_lname = QLineEdit()
        self.sw_lname.setPlaceholderText("Lastname")
        self.sw_lname.hide()
        self.sw_fname = QLineEdit()
        self.sw_fname.setPlaceholderText("Firstname")
        self.sw_fname.hide()
        self.sw_mname = QLineEdit()
        self.sw_mname.setPlaceholderText("Middlename")
        self.sw_mname.hide()

        sw_fullname_sizer2 = QHBoxLayout()
        sw_fullname_sizer2.addWidget(self.sw_lname)
        sw_fullname_sizer2.addWidget(self.sw_fname)
        sw_fullname_sizer2.addWidget(self.sw_mname)
        self.thru_firstname = QCheckBox("Search thru Firstname")
        self.thru_firstname.hide()
        assist_box.addLayout(sw_fullname_sizer2)

        self.encode_id = QLineEdit()
        self.encode_id.hide()

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        assist_box.addWidget(sep1)

        assist_box.addWidget(QLabel("Encoder Name:"))
        self.encoder_name = AllCapsLineEdit()
        assist_box.addWidget(self.encoder_name)

        assist_box.addWidget(QLabel("Approved By:"))
        self.approved_by = NoScrollComboBox()
        self.approved_by.addItems(list(approved_by_list.keys()))
        assist_box.addWidget(self.approved_by)

        assist_box.addWidget(QLabel("Date Entered:"))
        self.encoded_date = _QDE()
        self.encoded_date.setCalendarPopup(True)
        self.encoded_date.setDate(QDate.currentDate())
        assist_box.addWidget(self.encoded_date)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        self.scroll_sizer.addWidget(sep2)
        self.scroll_sizer.addLayout(assist_box)

        # ── CRUD + Table section ─────────────────────────────────────────
        crud_container = QVBoxLayout()

        self.auto_next = QCheckBox("Auto Next")
        self.auto_submit = QCheckBox("Auto Submit")
        self.auto_finish = QCheckBox("Auto Finish")

        btn_crud_add = QPushButton("Add")
        btn_crud_update = QPushButton("Update")
        btn_crud_delete = QPushButton("Delete")
        btn_crud_add.clicked.connect(self.on_add_person)
        btn_crud_update.clicked.connect(self.on_update_person)
        btn_crud_delete.clicked.connect(self.on_delete_person)

        btn_set_encoded = QPushButton("Set Encoded")
        btn_set_encoded.clicked.connect(self.on_set_encoded)

        self.cb_encoded = QCheckBox("Encoded")
        self.cb_encoded.stateChanged.connect(self.on_checkbox_change)

        btn_export = QPushButton("Export")
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
        self.list_ctrl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.list_ctrl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.list_ctrl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.list_ctrl.itemSelectionChanged.connect(self.on_select_person)
        crud_container.addWidget(self.list_ctrl)

        # ── Auto Fill section ────────────────────────────────────────────
        autofill_container = QVBoxLayout()

        self.fill_forms_btn = QPushButton("Fill Form")
        self.fill_forms_btn.clicked.connect(self.on_button_click)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.on_refresh)
        self.cb_website = QCheckBox("WEB")
        self.cb_offline = QCheckBox("OFF")
        self.cb_mov = QCheckBox("MOV")

        btn_stop = QPushButton("Stop")
        btn_stop.clicked.connect(self.on_stop)

        btn_auto_fill = QPushButton("Auto Fill")
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
        self.command_log.setMinimumHeight(50)
        self.command_log.setMaximumHeight(100)
        autofill_container.addWidget(self.command_log)

        autofill_container.addWidget(btn_auto_fill)

        self.sizer.addWidget(scroll_area, 6)
        crud_w = QWidget()
        crud_w.setLayout(crud_container)
        self.sizer.addWidget(crud_w, 3)

        autofill_w = QWidget()
        autofill_w.setLayout(autofill_container)
        self.sizer.addWidget(autofill_w, 1)

        # Connect thread-safe signals
        self._sig_log.connect(self.command_log.append)
        self._sig_set_running.connect(self.set_running_flag)
        self._sig_reload_person.connect(self.load_data_person)
        self._sig_select_first.connect(self.select_first_item)
        self._sig_msg_box.connect(self._show_msg_box)

        self.on_check_pickle()
        self.load_data_person()
        self.load_data_worker()

    def _show_msg_box(self, title, message, kind):
        if kind == "error":
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)

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
        self.on_save_data()
        if self.is_running:
            self.command_log.append("Task already running... Please wait.")
            return
        self.is_running = True
        self.command_log.append("Task started... Please wait.")
        threading.Thread(target=self.on_fill_up, daemon=True).start()

    def on_check_pickle(self):
        file_path = "data-new.pkl"

        # Check if the file exists
        if os.path.exists(file_path):
            self.on_load_data()
        else:
            self.on_save_data()

    def on_load_data(self):
        with open("data-new.pkl", "rb") as file:
            self.loaded_data = pickle.load(file)
        d = self.loaded_data
        self.mode_of_admission.setCurrentIndex(d.get("mode_of_admission", 1))
        self.encoder_name.setText(d.get("encoder_name", ""))
        set_date_value(self.encoded_date, d.get("encoded_date", "2000-01-01"))
        self.auto_next.setChecked(d.get("auto_next", False))
        self.auto_submit.setChecked(d.get("auto_submit", False))
        self.thru_firstname.setChecked(d.get("thru_firstname", False))
        self.target_sector.setCurrentIndex(d.get("target_sector", 0))
        self.financial_assist.setCurrentIndex(d.get("financial_assist", 0))
        self.mode_release.setCurrentIndex(d.get("mode_release", 0))
        self.amount.setText(d.get("amount", ""))
        self.fund_source.setCurrentIndex(d.get("fund_source", 0))
        self.sw_lname.setText(d.get("sw_lname", ""))
        self.sw_fname.setText(d.get("sw_fname", ""))
        self.sw_mname.setText(d.get("sw_mname", ""))
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
        self.client_barangay.setText(d.get("client_barangay", ""))
        self.client_city.setCurrentIndex(d.get("client_city", 0))
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
        self.bene_barangay.setText(d.get("bene_barangay", ""))
        self.bene_city.setCurrentIndex(d.get("bene_city", 0))
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
            "thru_firstname": self.thru_firstname.isChecked(),
            "target_sector": self.target_sector.currentIndex(),
            "financial_assist": self.financial_assist.currentIndex(),
            "mode_release": self.mode_release.currentIndex(),
            "amount": self.amount.text(),
            "fund_source": self.fund_source.currentIndex(),
            "sw_lname": self.sw_lname.text(),
            "sw_fname": self.sw_fname.text(),
            "sw_mname": self.sw_mname.text(),
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
            "client_barangay": self.client_barangay.text(),
            "client_city": self.client_city.currentIndex(),
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
            "bene_barangay": self.bene_barangay.text(),
            "bene_city": self.bene_city.currentIndex(),
            "has_beneficiary": self.has_beneficiary.isChecked(),
            "cb_encoded": self.cb_encoded.isChecked(),
            "auto_finish": self.auto_finish.isChecked(),
            "selected_id": self.encode_id.text(),
        }
        with open("data-new.pkl", "wb") as file:
            pickle.dump(self.data, file)

    def on_button_clear_all(self, event=None):
        for w in [self.client_lastname, self.client_firstname, self.client_middlename,
                  self.client_contact_no, self.client_age, self.client_house_street,
                  self.client_barangay, self.bene_lastname, self.bene_firstname,
                  self.bene_middlename, self.bene_contact_no, self.bene_age,
                  self.bene_house_street, self.bene_barangay]:
            w.setText("")
        for w in [self.client_gender, self.client_civil_status, self.client_city,
                  self.bene_gender, self.bene_civil_status, self.bene_city]:
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
        data["thru_firstname"] = self.thru_firstname.isChecked()
        data["target_sector"] = self.target_sector.currentIndex()
        data["financial_assist"] = self.financial_assist.currentIndex()

        data["mode_release"] = self.mode_release.currentIndex()

        data["amount"] = self.amount.text()
        data["fund_source"] = self.fund_source.currentIndex()
        data["sw_lname"] = self.sw_lname.text()
        data["sw_fname"] = self.sw_fname.text()
        data["sw_mname"] = self.sw_mname.text()
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
        data["client_barangay"] = self.client_barangay.text()
        data["client_city"] = self.client_city.currentIndex()

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
        data["bene_barangay"] = self.bene_barangay.text()
        data["bene_city"] = self.bene_city.currentIndex()

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

    def on_refresh(self, event=None):
        if self.cb_website.isChecked() or self.cb_offline.isChecked() or self.cb_mov.isChecked():
            chrome_options = webdriver.ChromeOptions()
            chrome_options.debugger_address = "localhost:9222"
            driver = webdriver.Chrome(options=chrome_options)

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
            driver.quit()
            self._sig_log.emit("Task completed!")
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

            # Attach to an existing Chrome session (Make sure Chrome is running with debugging mode)
            chrome_options = webdriver.ChromeOptions()
            chrome_options.debugger_address = "localhost:9222"  # Attach to existing Chrome session

            self.driver = webdriver.Chrome(options=chrome_options)  # Open Selenium with existing Chrome session

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

            self.driver.quit()
            self._sig_log.emit("Task completed!")

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

    def on_fill_crims_website(self, driver):
        try:
            if self.clickHrefButton(driver, "Add Client"):
                c_full_name = f'{self.client_lastname.text()} {self.client_firstname.text()} {self.client_middlename.text()}'
                if self.hasASearchField(driver, c_full_name):
                    if self.searchResult(driver) :
                        self.clickAddButton(driver, "Add Client")
                        return None
                    else:
                        self.clickIconButton(driver)
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

                    self.setTextField(driver, "queue_no", "0")

                    self.setDropDown(driver, "select2-mode_of_admission-container", self.mode_of_admission.currentText())
                    self.setDropDown(driver, "select2-cl_assisted_through-container", "Onsite")
                    self.setDropDown(driver, "select2-cl_typeid-container", "N/A")
                    self.setDropDown(driver, "select2-cl_referring_party-container", "Default Default Default")

                    if not self.has_beneficiary.isChecked():
                        self.setDropDown(driver, "select2-is_Self-container", "Yes")
                    else:
                        self.setDropDown(driver, "select2-is_Self-container", "No")

                    self.setDropDown(driver, "select2-cl_category-container", self.target_sector.currentText())
                    self.setDropDown(driver, "select2-cl_sub_category-container", "NONE OF THE ABOVE")

                    self.setTextField(driver, "lname", self.client_lastname.text())
                    self.setTextField(driver, "fname", self.client_firstname.text())
                    self.setTextField(driver, "mname", self.client_middlename.text())
                    client_ext_value = self.client_ext.text().lower()
                    if client_ext_value != "":
                        self.setTextField(driver, "xname", self.client_ext.text())

                    self.setDate(driver, "birthdate", self.client_bday.date())

                    self.setDropDown(driver, "select2-sex-container", self.client_gender.currentText())

                    client_contact_value = self.client_contact_no.text()
                    if client_contact_value == "" :
                        client_contact_value = "00000000000"

                    self.setTextField(driver, "contact_no", client_contact_value)

                    relationship_caption = self.client_relationship.currentText()
                    relationship_name = self.relationship_data_map[relationship_caption]

                    self.setDropDown(driver, "select2-relationship_bene-container", relationship_caption)

                    civil_status_caption = self.client_civil_status.currentText()
                    civil_status_name = self.civil_status_data_map[civil_status_caption]

                    self.setDropDown(driver, "select2-civil_status-container", civil_status_name)

                    self.setTextField(driver, "purok_street", self.client_house_street.text())

                    self.setDropDown(driver, "select2-region-container", "NCR [National Capital Region]")


                    districtNCR = district_city.get(self.client_city.currentText(), "NCR THIRD DISTRICT")

                    self.setDropDown(driver, "select2-province-container", districtNCR)

                    if self.client_city.currentText() == "NONE OF THE ABOVE":
                        self.stop_requested = True
                        city_value = "NONE OF THE ABOVE"
                    elif self.client_city.currentText() == "CITY OF CALOOCAN":
                        city_value = "KALOOKAN CITY"
                    elif self.client_city.currentText() == "CITY OF QUEZON CITY":
                        city_value = "QUEZON CITY"
                    else:
                        city_value = self.client_city.currentText()
                    self.setDropDown(driver, "select2-city_muni-container", city_value)

                    self.setDropDown(driver, "select2-barangay-container", self.client_barangay.text())

                    self.setDropDown(driver, "select2-occupation-container", "NONE OF THE ABOVE")

                    self.setTextField(driver, "salary", "0")

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

                        self.setDropDown(driver, "select2-b_sex-container", self.bene_gender.currentText())
                        self.setDropDown(driver, "select2-b_civil_status-container",
                                         self.bene_civil_status.currentText())
                        self.setDropDown(driver, "select2-b_referring_party-container", "Default Default Default")

                        self.setDate(driver, "b_birthdate", self.bene_bday.date())

                        self.setTextField(driver, "b_lname", self.bene_lastname.text())
                        self.setTextField(driver, "b_fname", self.bene_firstname.text())
                        self.setTextField(driver, "b_mname", self.bene_middlename.text())
                        self.setTextField(driver, "b_xname", self.bene_ext.text())

                        self.setDropDown(driver, "select2-b_region-container", "NCR [National Capital Region]")

                        districtNCR = district_city.get(self.client_city.currentText(), "NCR THIRD DISTRICT")
                        self.setDropDown(driver, "select2-b_province-container", districtNCR)

                        if self.client_city.currentText() == "NONE OF THE ABOVE":
                            self.stop_requested = True
                            city_value = "NONE OF THE ABOVE"
                        elif self.bene_city.currentText() == "CITY OF CALOOCAN":
                            city_value = "KALOOKAN CITY"
                        else:
                            city_value = self.client_city.currentText()
                        self.setDropDown(driver, "select2-b_city_muni-container", city_value)

                        self.setDropDown(driver, "select2-b_barangay-container", self.bene_barangay.text())

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
                    self.setDropDown(driver, "select2-bene_category-container", self.target_sector.currentText())
                    self.setDropDown(driver, "select2-bene_sub_category-container", "NONE OF THE ABOVE")

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
                    mode = self.mode_release.currentText().title()
                    self.setDropDown(driver, "select2-FA2mode_of_asssitance}-container", mode)

                    fund_source_caption = self.fund_source.currentText()

                    self.setDropDown(driver, "select2-FA2fund_source-container", fund_source_caption)

                    self.setTextField(driver, "FA[2][purpose]", purpose_value)
                    self.setTextField(driver, "FA[2][amount_of_assistance]", self.amount.text())

                    try:
                        driver.implicitly_wait(10)
                        # Switch to the alert (pop-up)
                        alert = Alert(driver)

                        # Accept the alert (click "OK")
                        alert.accept()
                        print("Alert accepted!")

                    except:
                        print("No alert present")

                    if self.auto_next.isChecked() :
                        self.clickNextButton(driver, "Next")
                        try:
                            driver.implicitly_wait(10)
                            # Switch to the alert (pop-up)
                            alert = Alert(driver)

                            # Accept the alert (click "OK")
                            alert.accept()
                            print("Alert accepted!")
                        except:
                            print("No alert present")
                        try:
                            driver.implicitly_wait(10)
                            # Switch to the alert (pop-up)
                            alert = Alert(driver)

                            # Accept the alert (click "OK")
                            alert.accept()
                            print("Alert accepted!")
                        except:
                            print("No alert present")
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "approver":
                    if self.thru_firstname.isChecked():
                        if self.sw_mname.text() == "" :
                            sw_full_name = f'{self.sw_fname.text()} {self.sw_lname.text()}'
                        else:
                            sw_full_name = f'{self.sw_fname.text()} {self.sw_mname.text()} {self.sw_lname.text()}'
                    else:
                        sw_full_name = f'{self.sw_lname.text()} {self.sw_fname.text()} {self.sw_mname.text()}'

                    self.setDropDown(driver, "select2-assessed_by-container", sw_full_name)


                    selected_index = self.approved_by.currentIndex()
                    if selected_index != -1:
                        selected_key = self.approved_by.currentText()
                        selected_value = approved_by_list[selected_key]
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
        region = "NCR [National Capital Region]"

        province = district_city.get(self.client_city.currentText(), "NCR THIRD DISTRICT")

        gformTitle = self.getGFormTitle(driver)

        if self.offline_page_title == self.getGFormTitle(driver):
            winsound.MessageBeep()
        else:
            self.offline_page_title = gformTitle

        if gformTitle == "approved by":

            selected_index = self.approved_by.currentIndex()
            if selected_index != -1:
                selected_key = self.approved_by.currentText()
                selected_value = approved_by_list[selected_key]
                self.setGFormRadioButton(driver, "", selected_key)

            self.setGFormRadioButton(driver, "REGION ASSESS", "NCR (National Capital Region)")
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
                self.setGFormRadioButton(driver, "SEX", self.bene_gender.currentText())
                self.setGFormRadioButton(driver, "CIVIL STATUS", self.bene_civil_status.currentText())

                self.setGFormDate(driver, "i50", self.bene_bday.date())

            self.setGFormTextField(driver, "i46 i47", date_str)

            mode_of_release_string = self.mode_release.currentText()
            self.setGFormRadioButton(driver, "MODE OF RELEASE", mode_of_release_string)
            self.setGFormRadioButton(driver, "DATE OF RELEASE", "2025")
            # i150 - INTERVIEW
            # i156 - DATE OF RELEASE
            self.setGFormDate(driver, "i150", self.interview_date.date())
            self.setGFormDate(driver, "i156", self.interview_date.date())

            sw_lname_value = string.capwords(self.sw_lname.text())
            sw_fname_value = string.capwords(self.sw_fname.text())
            sw_mname_value = string.capwords(self.sw_mname.text())
            sw_mname_initial_value = sw_mname_value[0].upper() if sw_mname_value else ""
            sw_full_name = f'{sw_lname_value}, {sw_fname_value} {sw_mname_initial_value}.'
            self.setGFormDropDown(driver, "i157 i160", sw_full_name)

            if self.auto_next.isChecked():
                self.clickGFormButton(driver, "Next")
        elif gformTitle == "barangay and district":
            self.setGFormTextField(driver, "i2 i3", self.client_barangay.text())
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

            self.setGFormDropDown(driver, "i31 i34", self.client_gender.currentText().upper())  # sex

            civil_status_caption = self.client_civil_status.currentText()
            civil_status_name = self.civil_status_data_map[civil_status_caption]

            self.setGFormRadioButton(driver, "CIVIL STATUS", civil_status_caption)

            self.setGFormDate(driver, "i61", self.client_bday.date())
            self.setGFormTextField(driver, "i63 i64", self.client_age.text())

            self.setGFormRadioButton(driver, "MODE OF ADMISSION", "WALK-IN")

            self.setGFormTextField(driver, "i96 i97", self.amount.text())

            fund_source_caption = self.fund_source.currentText()
            fund_source_name = self.fund_source_data_map[fund_source_caption]

            self.setGFormRadioButton(driver, "FUND SOURCE", fund_source_name)

            sector_value = self.target_sector.currentText()
            if sector_value.lower() == "senior citizens" :
                sector_value = "senior citizens (no subcategories)"
            #     SENIOR CITIZENS (no subcategories)
            self.setGFormRadioButton(driver, "CLIENT CATEGORY", sector_value)

            self.setGFormRadioButton(driver, "CLIENT SUB-CATEGORY", "Indigenous People")
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
            relationship_name = self.relationship_data_map[relationship_caption]

            self.setGFormRadioButton(driver, "RELATIONSHIP TO BENEFICIARY", relationship_name)
            if self.auto_next.isChecked():
                self.clickGFormButton(driver, "Next")
        elif is_similar(gformTitle, province.lower()):
            if self.client_city.currentText() == "NONE OF THE ABOVE":
                self.stop_requested = True
            else:
                self.setGFormDropDown(driver, "i1 i4", self.client_city.currentText())
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
            self.setGFormDropDown(driver, "i35 i38", region)
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

        sw_full_name = f'{self.sw_fname.text()} {self.sw_mname.text()} {self.sw_lname.text()}'
        self.setGFormTextField(driver, "i39 i40", sw_full_name)

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
                                time.sleep(0.5)
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
                                time.sleep(0.5)

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
                    time.sleep(0.5)  # Small delay to avoid issues

    def setGFormRecordEmailCheckbox(self, driver):
        try:
            checkboxes = driver.find_elements(By.XPATH, "//div[@role='checkbox']")
            for checkbox in checkboxes:
                if checkbox.get_attribute("aria-checked") != "true":
                    checkbox.click()
                    self.command_log.append("Checked: " + checkbox.accessible_name)
                    time.sleep(0.5)  # Small delay to avoid issues
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
                    time.sleep(0.5)  # Small delay to avoid issues
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
            dropdown = driver.find_element(By.XPATH, f"//div[@role='listbox' and @aria-labelledby='{pk_id}']")
            if dropdown:
                # Click to open the dropdown
                dropdown.click()
                time.sleep(0.5)

                options = driver.find_elements(By.XPATH, "//div[@role='option']")

                selected_option = None
                for option in options:
                    name_text = option.get_attribute("data-value").strip().lower()
                    if is_similar(name_text, value):
                        selected_option = option
                        break

                # Select the matched option if found
                if selected_option:
                    selected_option.click()
                    time.sleep(0.5)
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
            element = driver.find_element("id", name)

            # Check if the 'title' attribute exists and is not empty
            title_value = element.get_attribute("title")

            if title_value:
                self.command_log.append(f"Field {name}: already selected ")
            else:
                combobox = driver.find_element(By.XPATH,
                                       f"//span[@role='combobox' and @aria-labelledby='{name}']")
                # Click to open the dropdown
                combobox.click()
                time.sleep(0.5)  # Wait for dropdown options to appear

                # Define the option text to select
                option = driver.find_element(By.XPATH,
                                             f"//li[contains(@class, 'select2-results__option') and contains(normalize-space(), '{value}')]")  # Adjust text as needed
                option.click()
                time.sleep(0.5)
                self.command_log.append(f"Field {name}: {value} ")
        except NoSuchElementException:
            self.command_log.append(f"Error: Element with {name} not found. ")
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
            self.bene_barangay.setText(self.client_barangay.text())
            self.bene_city.setCurrentIndex(self.client_city.currentIndex())
        else:
            self.bene_house_street.setText("")
            self.bene_barangay.setText("")
            self.bene_city.setCurrentIndex(-1)

    def same_contact_event(self, state=None):
        if self.same_contact.isChecked():
            self.bene_contact_no.setText(self.client_contact_no.text())

    def has_beneficiary_event(self, state=None):
        if not self.has_beneficiary.isChecked():
            for w in [self.bene_lastname, self.bene_firstname, self.bene_middlename,
                      self.bene_age, self.bene_ext, self.bene_contact_no,
                      self.bene_house_street, self.bene_barangay]:
                w.setText("")
            self.bene_relationship.setCurrentIndex(-1)
            self.bene_gender.setCurrentIndex(-1)
            self.bene_civil_status.setCurrentIndex(-1)
            self.bene_city.setCurrentIndex(-1)
        else:
            self.bene_relationship.setCurrentIndex(self.client_relationship.currentIndex())

    def on_checkbox_change(self, state=None):
        self.load_data_person()

    def on_selection(self, index=None):
        name = self.client_civil_status.currentText()
        caption = self.civil_status_data_map.get(name, "")
        print(f"Selected Caption: {caption} Name: {name}")

    def on_selection_worker(self, index=None):
        selected = self.social_worker.currentText()
        if not selected:
            return
        name_parts = selected.split(",")
        if len(name_parts) < 3:
            return
        fname, mname, lname = name_parts[0], name_parts[1], name_parts[2]
        data_worker = get_worker_id(lname.strip(), fname.strip(), mname.strip())
        if data_worker:
            self.sw_lname.setText(data_worker[1])
            self.sw_fname.setText(data_worker[2])
            self.sw_mname.setText(data_worker[3])
            self.thru_firstname.setChecked(bool(data_worker[4]))

    def reload_choice_items(self):
        self.social_worker_list = get_all_workers()
        self.social_worker.clear()
        self.social_worker_choices = [f"{fname}, {mname}, {lname}" for (_id, lname, fname, mname, _thru) in self.social_worker_list]
        self.social_worker.addItems(self.social_worker_choices)

    def on_sw_text_change(self, text):
        typed = text.lower().strip()
        for index, name in enumerate(self.social_worker_choices):
            if name.lower().startswith(typed):
                self.social_worker.setCurrentIndex(index)
                self.on_selection_worker(index)
                break

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

        layout = QVBoxLayout(self)

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
