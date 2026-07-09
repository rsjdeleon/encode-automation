# wxPython → PySide6 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all wxPython usage in `assistance-form-new.py` and `utilities.py` with PySide6 so the app runs on Python 3.14+.

**Architecture:** 1-to-1 widget replacement — `MyFrame(wx.Frame)` becomes `MyFrame(QMainWindow)`, `ActivationFrame(wx.Frame)` becomes `ActivationFrame(QDialog)`, `MainApp(wx.App)` becomes a standard `QApplication` entry point. A new `widgets.py` extracts `AllCapsLineEdit` and `NoScrollComboBox` helper classes. Thread-to-UI calls (`wx.CallAfter`) are replaced with Qt `Signal` emissions.

**Tech Stack:** PySide6 6.x, Python 3.14, SQLite (unchanged), Selenium (unchanged), keyboard (unchanged)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `requirements.txt` | Modify | Replace `wxPython==4.2.2` with `PySide6` |
| `utilities.py` | Modify | Remove wx imports; rewrite `disable_mousewheel`, `get_date_value`, `set_date_value` for PySide6 |
| `widgets.py` | Create | `AllCapsLineEdit`, `NoScrollComboBox` reusable widget helpers |
| `assistance-form-new.py` | Modify | Full GUI layer rewrite: imports, class definitions, all wx.* calls |

---

## Task 1: Install PySide6 and update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt**

Replace contents:
```
PySide6
selenium
keyboard
```

- [ ] **Step 2: Install PySide6**

Run:
```bash
py -3.14 -m pip install PySide6
```
Expected: `Successfully installed PySide6-...`

- [ ] **Step 3: Verify import works**

Run:
```bash
py -3.14 -c "from PySide6.QtWidgets import QApplication; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: replace wxPython with PySide6 in requirements"
```

---

## Task 2: Rewrite utilities.py for PySide6

**Files:**
- Modify: `utilities.py`

- [ ] **Step 1: Rewrite utilities.py**

Replace the entire file with:
```python
import os
import signal
from difflib import SequenceMatcher
from PySide6.QtCore import QDate


def is_similar(text1, text2, threshold=0.9):
    return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio() >= threshold


def disable_mousewheel(widget):
    """No-op: NoScrollComboBox handles this via wheelEvent override."""
    pass


def get_date_value(date_edit):
    """Get the selected date from QDateEdit as a string (YYYY-MM-DD)."""
    return date_edit.date().toString("yyyy-MM-dd")


def set_date_value(date_edit, date_str):
    """Set QDateEdit to a given date string (YYYY-MM-DD)."""
    date = QDate.fromString(date_str, "yyyy-MM-dd")
    if date.isValid():
        date_edit.setDate(date)
        return True
    return False


def stop_selenium(driver, log_widget):
    if driver:
        os.kill(driver.service.process.pid, signal.SIGTERM)
    log_widget.append("Selenium WebDriver stopped.")
```

- [ ] **Step 2: Verify import**

Run:
```bash
py -3.14 -c "from utilities import is_similar, get_date_value, set_date_value; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add utilities.py
git commit -m "feat: rewrite utilities.py for PySide6 (remove wx dependency)"
```

---

## Task 3: Create widgets.py with reusable PySide6 helpers

**Files:**
- Create: `widgets.py`

- [ ] **Step 1: Create widgets.py**

```python
from PySide6.QtWidgets import QLineEdit, QComboBox


class AllCapsLineEdit(QLineEdit):
    """QLineEdit that forces all input to uppercase."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self._force_upper)

    def _force_upper(self, text):
        if text != text.upper():
            pos = self.cursorPosition()
            self.blockSignals(True)
            self.setText(text.upper())
            self.blockSignals(False)
            self.setCursorPosition(pos)


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores mousewheel scroll to prevent accidental selection changes."""

    def wheelEvent(self, event):
        event.ignore()
```

- [ ] **Step 2: Verify import**

Run:
```bash
py -3.14 -c "from widgets import AllCapsLineEdit, NoScrollComboBox; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add widgets.py
git commit -m "feat: add AllCapsLineEdit and NoScrollComboBox PySide6 widget helpers"
```

---

## Task 4: Migrate ActivationFrame and MainApp entry point

**Files:**
- Modify: `assistance-form-new.py` (bottom section only, lines 2908–3016)

- [ ] **Step 1: Replace ActivationFrame and entry point**

Find and replace everything from `class ActivationFrame` to end of file with:

```python
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
```

- [ ] **Step 2: Add `sys` and Qt imports at top of file**

Replace the existing import block at the top of `assistance-form-new.py` (lines 1–50) with:

```python
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
```

- [ ] **Step 3: Verify file parses**

Run:
```bash
py -3.14 -c "import ast; ast.parse(open('assistance-form-new.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add assistance-form-new.py
git commit -m "feat: migrate ActivationFrame and entry point to PySide6"
```

---

## Task 5: Add Qt Signal bridge for thread-safe UI updates

**Files:**
- Modify: `assistance-form-new.py` — add signals to `MyFrame` class definition

- [ ] **Step 1: Add class-level signals and connect them in `__init__`**

After the imports and before `def init_db():`, add the `AllCapsTextCtrl = AllCapsLineEdit` alias and `AllTextCtrl = QLineEdit` alias for backward compatibility within the file:

```python
# Initialize SQLite database
def init_db():
    init_db_person()
    init_db_worker()
```

Then in `MyFrame` class definition, add signals as class attributes (before `__init__`):

```python
class MyFrame(QMainWindow):
    row_data = {}
    row_data_sw = {}

    # Thread-safe UI signals
    _sig_log = Signal(str)
    _sig_set_running = Signal(bool)
    _sig_reload_person = Signal()
    _sig_select_first = Signal()
    _sig_msg_box = Signal(str, str, str)  # title, message, kind (info/error)
```

- [ ] **Step 2: Connect signals in `__init__` (add these lines at the end of `__init__` before `self.on_check_pickle()`)**

```python
        # Connect thread-safe signals
        self._sig_log.connect(self.command_log.append)
        self._sig_set_running.connect(self.set_running_flag)
        self._sig_reload_person.connect(self.load_data_person)
        self._sig_select_first.connect(self.select_first_item)
        self._sig_msg_box.connect(self._show_msg_box)
```

- [ ] **Step 3: Add `_show_msg_box` helper method to `MyFrame`**

```python
    def _show_msg_box(self, title, message, kind):
        if kind == "error":
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)
```

- [ ] **Step 4: Commit**

```bash
git add assistance-form-new.py
git commit -m "feat: add Qt Signal bridge for thread-safe UI updates in MyFrame"
```

---

## Task 6: Rewrite MyFrame.__init__ — complete UI layout

**Files:**
- Modify: `assistance-form-new.py` — replace the entire `__init__` method of `MyFrame`

- [ ] **Step 1: Replace `MyFrame.__init__` with PySide6 layout code**

Replace the entire `def __init__(self):` method (lines 612–1248) with:

```python
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
        worker_sizer.addWidget(self.social_worker_filter)
        self.social_worker = NoScrollComboBox()
        self.social_worker.addItems(self.social_worker_choices)
        self.social_worker.currentIndexChanged.connect(self.on_selection_worker)
        worker_sizer.addWidget(self.social_worker)
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
        crud_container.addLayout(hbox_btns)

        self.command_log = QTextEdit()
        self.command_log.setReadOnly(True)
        self.command_log.setMinimumHeight(50)
        self.command_log.setMaximumHeight(100)
        crud_container.addWidget(self.command_log)

        crud_container.addWidget(btn_auto_fill)

        self.sizer.addWidget(scroll_area, 1)
        crud_w = QWidget()
        crud_w.setLayout(crud_container)
        self.sizer.addWidget(crud_w)

        # Connect thread-safe signals
        self._sig_log.connect(self.command_log.append)
        self._sig_set_running.connect(self.set_running_flag)
        self._sig_reload_person.connect(self.load_data_person)
        self._sig_select_first.connect(self.select_first_item)
        self._sig_msg_box.connect(self._show_msg_box)

        self.on_check_pickle()
        self.load_data_person()
        self.load_data_worker()
```

- [ ] **Step 2: Verify file parses**

Run:
```bash
py -3.14 -c "import ast; ast.parse(open('assistance-form-new.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add assistance-form-new.py
git commit -m "feat: rewrite MyFrame.__init__ with PySide6 layout"
```

---

## Task 7: Migrate data load/save and CRUD methods

**Files:**
- Modify: `assistance-form-new.py` — update method bodies for wx-API calls

- [ ] **Step 1: Update `load_data_worker`**

Replace `self.list_ctrl_worker.DeleteAllItems()` pattern with QTableWidget:

```python
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
```

- [ ] **Step 2: Update `load_data_person`**

```python
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
```

- [ ] **Step 3: Update `select_first_item`**

```python
    def select_first_item(self):
        if self.list_ctrl.rowCount() > 0:
            self.list_ctrl.selectRow(0)
```

- [ ] **Step 4: Update CRUD confirm dialogs**

Replace all `wx.MessageDialog` / `wx.MessageBox` patterns in `on_add_worker`, `on_update_worker`, `on_delete_worker`, `on_add_person`, `on_update_person`, `on_delete_person`, `on_set_encoded`:

Pattern to use everywhere:
```python
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
```

Replace `on_add_person`, `on_update_person`, `on_delete_person`, `on_set_encoded` with PySide6 versions:

```python
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
```

- [ ] **Step 5: Update `on_select_worker`**

```python
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
```

- [ ] **Step 6: Update `on_select_person`**

```python
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
```

- [ ] **Step 7: Verify file parses**

Run:
```bash
py -3.14 -c "import ast; ast.parse(open('assistance-form-new.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add assistance-form-new.py
git commit -m "feat: migrate load/select/CRUD methods to PySide6 API"
```

---

## Task 8: Migrate remaining event handlers and UI methods

**Files:**
- Modify: `assistance-form-new.py`

- [ ] **Step 1: Update age computation methods**

Replace `bday_wx.GetYear()` / `.GetMonth()` / `.GetDay()` pattern in `c_compute_age`, `b_compute_age`, `on_choice_change_client`, `on_choice_change_bene`:

```python
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
```

- [ ] **Step 2: Update checkbox event handlers**

```python
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
```

- [ ] **Step 3: Update social worker filter methods**

```python
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
```

- [ ] **Step 4: Update pickle save/load methods**

In `on_save_data`, replace all `self.xxx.GetValue()` → `self.xxx.text()`, `GetSelection()` → `currentIndex()`, `GetValue()` on checkbox → `isChecked()`, and `get_date_value(picker)` stays the same (already updated in Task 2):

```python
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
```

In `on_load_data`, replace all `SetValue`/`SetSelection` with `setText`/`setCurrentIndex`/`setChecked`:

```python
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
```

- [ ] **Step 5: Update `on_export`**

Replace `wx.BusyInfo` and `wx.Yield()` and `wx.CallAfter`:

```python
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
```

- [ ] **Step 6: Update `on_clear` and `on_button_clear_all`**

```python
    def on_clear(self, event=None):
        self.selected_person_id = None

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
```

- [ ] **Step 7: Verify file parses**

Run:
```bash
py -3.14 -c "import ast; ast.parse(open('assistance-form-new.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add assistance-form-new.py
git commit -m "feat: migrate event handlers, pickle save/load, and export to PySide6"
```

---

## Task 9: Fix wx.CallAfter and wx date API in Selenium/threading methods

**Files:**
- Modify: `assistance-form-new.py`

- [ ] **Step 1: Replace `wx.CallAfter` in `on_fill_up` and `on_refresh`**

Find every `wx.CallAfter(self.command_log.AppendText, ...)` and replace with `self._sig_log.emit(...)`.
Find every `wx.CallAfter(self.set_running_flag, ...)` and replace with `self._sig_set_running.emit(...)`.
Find `wx.CallAfter(wx.MessageBox, msg, title, style)` and replace with `self._sig_msg_box.emit(title, msg, "info")`.

Also replace the direct (unwrapped) calls to `self.load_data_person()` and `self.select_first_item()` inside the thread with their signal equivalents:
- `self.load_data_person()` → `self._sig_reload_person.emit()`
- `self.select_first_item()` → `self._sig_select_first.emit()`

Also replace `self.command_log.AppendText(text)` (non-threaded direct calls) with `self.command_log.append(text)`.

- [ ] **Step 2: Update `on_button_click` and `on_auto_fill`**

```python
    def on_button_click(self, event=None):
        self.on_save_data()
        if self.is_running:
            self.command_log.append("Task already running... Please wait.")
            return
        self.is_running = True
        self.command_log.append("Task started... Please wait.")
        threading.Thread(target=self.on_fill_up, daemon=True).start()

    def on_auto_fill(self, event=None):
        self.is_auto_fill = True
        self.on_button_click()

    def on_stop(self, event=None):
        self.stop_requested = True
```

- [ ] **Step 3: Fix wx.DateTime date API in Selenium helper methods**

Every call to `value.Format("%m-%d-%Y")` where `value` is a `wx.DateTime` from `GetValue()` needs to become a `QDate` call. Update `setDate` and `setGFormDate`:

```python
    def setDate(self, driver, name, value):
        """value is a QDate object."""
        try:
            date_str = value.toString("MM-dd-yyyy")
            date_field = driver.find_element(By.ID, name)
            date_field.send_keys(date_str)
            self.command_log.append(f"Date {name}: {date_str}")
        except Exception as e:
            self.command_log.append(f"Error in Date {e}")

    def setGFormDate(self, driver, pk_id, value):
        """value is a QDate object."""
        try:
            date_str = value.toString("MM-dd-yyyy")
            date_field = driver.find_element(By.XPATH, f'//input[@aria-labelledby="{pk_id}"]')
            if date_field:
                date_field.clear()
                date_field.send_keys(date_str)
        except NoSuchElementException:
            self.command_log.append("Error: Element not found.")
        except Exception as e:
            self.command_log.append(f"Unexpected error: {e}")
```

Update all callers to pass `.date()` instead of `.GetValue()`:
- `self.setDate(driver, "birthdate", self.client_bday.GetValue())` → `self.setDate(driver, "birthdate", self.client_bday.date())`
- `self.setDate(driver, "b_birthdate", self.bene_bday.GetValue())` → `self.setDate(driver, "b_birthdate", self.bene_bday.date())`
- `self.setDate(driver, "dt_assistanceProvided", self.interview_date.GetValue())` → `self.setDate(driver, "dt_assistanceProvided", self.interview_date.date())`
- All `self.setGFormDate(driver, ..., self.xxx.GetValue())` → `self.setGFormDate(driver, ..., self.xxx.date())`

Also fix in `on_fill_crims_offline` at line where `date_str = self.bene_bday.GetValue().Format("%m-%d-%Y")`:
```python
date_str = self.bene_bday.date().toString("MM-dd-yyyy")
```

- [ ] **Step 4: Fix remaining wx.* references in Selenium methods**

Replace all remaining wx-specific calls in `on_fill_crims_website`, `on_fill_crims_offline`, `on_fill_crims_mov`:

- `self.client_gender.GetStringSelection()` → `self.client_gender.currentText()`
- `self.client_city.GetStringSelection()` → `self.client_city.currentText()`
- `self.financial_assist.GetStringSelection()` → `self.financial_assist.currentText()`
- `self.client_lastname.GetValue()` → `self.client_lastname.text()`
- `self.mode_of_admission.GetStringSelection()` → `self.mode_of_admission.currentText()`
- `self.has_beneficiary.GetValue()` → `self.has_beneficiary.isChecked()`
- `self.target_sector.GetStringSelection()` → `self.target_sector.currentText()`
- `self.mode_release.GetStringSelection()` → `self.mode_release.currentText()`
- `self.fund_source.GetStringSelection()` → `self.fund_source.currentText()`
- `self.approved_by.GetSelection()` → `self.approved_by.currentIndex()`
- `self.approved_by.GetString(selected_index)` → `self.approved_by.currentText()` (already have index from above, simplify)
- `wx.NOT_FOUND` → `-1`
- `self.thru_firstname.GetValue()` → `self.thru_firstname.isChecked()`
- `self.client_civil_status.GetStringSelection()` → `self.client_civil_status.currentText()`
- `self.client_relationship.GetStringSelection()` → `self.client_relationship.currentText()`
- `self.bene_civil_status.GetStringSelection()` → `self.bene_civil_status.currentText()`
- `self.bene_gender.GetStringSelection()` → `self.bene_gender.currentText()`
- `self.bene_city.GetStringSelection()` → `self.bene_city.currentText()`
- All `self.xxx.GetValue()` on QLineEdit fields → `self.xxx.text()`
- `self.encode_id.GetValue()` → `self.encode_id.text()`

- [ ] **Step 5: Fix `on_refresh`**

```python
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
```

- [ ] **Step 6: Verify file parses**

Run:
```bash
py -3.14 -c "import ast; ast.parse(open('assistance-form-new.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add assistance-form-new.py
git commit -m "feat: replace wx.CallAfter with Qt signals and fix wx date API in Selenium methods"
```

---

## Task 10: Smoke test — launch the app

**Files:** None (verification only)

- [ ] **Step 1: Run the app**

Run:
```bash
py -3.14 assistance-form-new.py
```
Expected: App window opens titled "Client Assistance Form" with tabs (Client Information, Beneficiary Details, Social Worker), data table at bottom, and form fields visible. No import errors in the terminal.

- [ ] **Step 2: Verify key interactions**
  - Click "Client Information" tab → form fields visible
  - Click "Beneficiary Details" tab → form fields visible
  - Click "Social Worker" tab → table visible
  - Type in a name field → text appears in uppercase automatically
  - Click the date picker → calendar popup appears
  - Select a row in the data table → form fields populate
  - Click "Add" → confirmation dialog appears

- [ ] **Step 3: Commit final state**

```bash
git add assistance-form-new.py utilities.py widgets.py requirements.txt
git commit -m "feat: complete wxPython to PySide6 migration — app runs on Python 3.14"
```
