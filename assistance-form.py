import wx
import wx.adv
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

from utilities import is_similar
from utilities import get_date_value
from utilities import disable_mousewheel
from utilities import set_date_value

from db_person import init_db_person, DB_NAME
from db_person import get_all_person_by_encoded
from db_person import set_encoded
from db_person import insert_person, update_person, delete_person_by_id

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

from license import is_trial_valid, activate_trial, get_device_id


# Initialize SQLite database
def init_db():
    init_db_person()
    init_db_worker()

def export_sqlite_to_csv(db_path, table_name, csv_path):
    """
    Exports records from a SQLite database table into a CSV file.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
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

class AllCapsTextCtrl(wx.TextCtrl):
    def __init__(self, parent, *args, **kwargs):
        super(AllCapsTextCtrl, self).__init__(parent, *args, **kwargs)
        self.Bind(wx.EVT_TEXT, self.on_text_change)

    def on_text_change(self, event):
        value = self.GetValue()
        if value != value.upper():
            # Prevent cursor jumping by remembering position
            pos = self.GetInsertionPoint()
            self.ChangeValue(value.upper())
            self.SetInsertionPoint(pos)
        event.Skip()  # Allow other handlers

class MyFrame(wx.Frame):
    row_data = {}  # ID -> full data
    row_data_sw = {}  # ID -> full data



    def load_data_worker(self):
        self.selected_worker_id = self.list_ctrl_worker.GetFirstSelected()
        self.list_ctrl_worker.DeleteAllItems()
        for row in get_all_workers():
            index = self.list_ctrl_worker.InsertItem(self.list_ctrl_worker.GetItemCount(), str(row[0]))
            self.list_ctrl_worker.SetItem(index, 1, row[1])
            self.list_ctrl_worker.SetItem(index, 2, str(row[2]))
            self.list_ctrl_worker.SetItem(index, 3, str(row[3]))
            self.list_ctrl_worker.SetItem(index, 4, str(row[4]))

            # Optionally store a reference map if needed
            self.row_data_sw[row[0]] = {
                "id": row[0],
                "sw_lname": row[1],
                "sw_fname": row[2],
                "sw_mname": row[3],
                "search_thru_first_name": row[4],
            }

    def on_add_worker(self, event):
        dialog = wx.MessageDialog(
            self,
            "Are you sure you want to add?",
            "Add",
            style=wx.YES_NO | wx.ICON_QUESTION
        )
        result = dialog.ShowModal()
        if result == wx.ID_YES:
            if insert_worker(
                    self.sw_last_name.GetValue(),
                    self.sw_first_name.GetValue(),
                    self.sw_middle_name.GetValue(),
                    self.sw_thru_first_name.GetValue()
            ):
                self.load_data_worker()
                self.reload_choice_items()
            else:
                wx.MessageBox("Record already exist.", "Error", wx.OK | wx.ICON_ERROR)

        dialog.Destroy()

    def on_update_worker(self, event):
        dialog = wx.MessageDialog(
            self,
            "Are you sure you want to update ?",
            "Update",
            style=wx.YES_NO | wx.ICON_QUESTION
        )
        result = dialog.ShowModal()

        if result == wx.ID_YES:
            """Updates the selected record"""
            if self.selected_worker_id:
                update_worker(
                    self.selected_worker_id,
                    self.sw_last_name.GetValue(),
                    self.sw_first_name.GetValue(),
                    self.sw_middle_name.GetValue(),
                    self.sw_thru_first_name.GetValue()
                )
                self.load_data_worker()
                self.reload_choice_items()

        dialog.Destroy()

    def on_delete_worker(self, event):
        dialog = wx.MessageDialog(
            self,
            "Are you sure you want to delete?",
            "Delete",
            style=wx.YES_NO | wx.ICON_QUESTION
        )
        result = dialog.ShowModal()

        if result == wx.ID_YES:
            """Deletes the selected record"""
            if self.selected_worker_id:
                delete_worker_by_id(self.selected_worker_id)
                self.load_data_worker()
                self.reload_choice_items()

        dialog.Destroy()

    def on_select_worker(self, event):
        index = event.GetIndex()
        self.selected_worker_id = int(self.list_ctrl_worker.GetItemText(index))
        if self.selected_worker_id in self.row_data_sw:
            worker = self.row_data_sw[self.selected_worker_id]
            self.selected_worker_id = worker["id"]

            self.sw_last_name.SetValue(worker["sw_lname"])
            self.sw_first_name.SetValue(worker["sw_fname"])
            self.sw_middle_name.SetValue(worker["sw_mname"])
            self.sw_thru_first_name.SetValue(worker["search_thru_first_name"])

    def load_data_person(self):
        is_encoded = "1" if self.cb_encoded.GetValue() else "0"
        selected_index = self.list_ctrl.GetFirstSelected()
        self.list_ctrl.DeleteAllItems()

        # Assign a color per unique SW value
        sw_color_map = {}
        sw_column_index = 7

        for row in get_all_person_by_encoded(is_encoded):
            sw_value = row[sw_column_index]
            if sw_value not in sw_color_map:
                sw_color_map[sw_value] = wx.Colour(
                    random.randint(180, 255),
                    random.randint(200, 255),
                    random.randint(180, 255)
                )

            assist = ""
            if row[4] == 0 :
                assist = "Medical"
            elif row[4] == 1 :
                assist = "Burial"
            elif row[4] == 2:
                assist = "Transportation"
            elif row[4] == 3:
                assist = "Cash Support"
            elif row[4] == 4:
                assist = "Food"

            index = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), str(row[0]))
            self.list_ctrl.SetItem(index, 1, row[12])
            self.list_ctrl.SetItem(index, 2, str(row[13]))
            self.list_ctrl.SetItem(index, 3, str(row[14]))
            self.list_ctrl.SetItem(index, 4, str(row[15]))
            self.list_ctrl.SetItem(index, 5, str(row[17]))
            self.list_ctrl.SetItem(index, 6, str(row[18]))
            self.list_ctrl.SetItem(index, 7, str(assist))
            self.list_ctrl.SetItem(index, 8, str(row[5]))
            self.list_ctrl.SetItem(index, 9, str(row[7]))
            self.list_ctrl.SetItem(index, 10, str(row[38]))

            self.list_ctrl.SetItemBackgroundColour(index, sw_color_map[sw_value])

            if row[23] == 5:
                self.list_ctrl.SetItemBackgroundColour(index, wx.Colour(255, 0, 0))

            # Optionally store a reference map if needed
            self.row_data[row[0]] = {
                "id": row[0],
                "encoder_name": row[1],
                "date_encoded": row[2],
                "target_sector": row[3],
                "financial_assist": row[4],
                "amount": row[5],
                "fund_source": row[6],
                "sw_lname": row[7],
                "sw_fname": row[8],
                "sw_mname": row[9],
                "interview_date": row[10],
                "client_relationship": row[11],
                "client_lastname": row[12],
                "client_firstname": row[13],
                "client_middlename": row[14],
                "client_ext": row[15],
                "client_gender": row[16],
                "client_bday": row[17],
                "client_age": row[18],
                "client_contact_no": row[19],
                "client_civil_status": row[20],
                "client_house_street": row[21],
                "client_barangay": row[22],
                "client_city": row[23],
                "bene_relationship": row[24],
                "bene_lastname": row[25],
                "bene_firstname": row[26],
                "bene_middlename": row[27],
                "bene_ext": row[28],
                "bene_gender": row[29],
                "bene_bday": row[30],
                "bene_age": row[31],
                "bene_contact_no": row[32],
                "bene_civil_status": row[33],
                "bene_house_street": row[34],
                "bene_barangay": row[35],
                "bene_city": row[36],
                "has_beneficiary": row[37],
                "encoded": row[38],
                "target_sector_bene": row[39],
            }

            if 0 <= selected_index < self.list_ctrl.GetItemCount():
                self.list_ctrl.Select(selected_index)
                self.list_ctrl.Focus(selected_index)

    def select_first_item(self):
        # Select first item if list has records
        if self.list_ctrl.GetItemCount() > 0:
            self.list_ctrl.Select(0, True)  # Selects the first item
            self.list_ctrl.Focus(0)  # Focuses the first item for keyboard interaction

    def on_add_person(self, event):
        dialog = wx.MessageDialog(
            self,
            "Are you sure you want to add?",
            "Add",
            style=wx.YES_NO | wx.ICON_QUESTION
        )
        result = dialog.ShowModal()

        if result == wx.ID_YES:
            """Handles adding a new record"""
            cl_bday = self.client_bday.GetValue()
            cl_bday = cl_bday.FormatISODate()
            be_bday = self.bene_bday.GetValue()
            be_bday = be_bday.FormatISODate()
            date_encoded_val = self.encoded_date.GetValue()
            date_encoded_val = date_encoded_val.FormatISODate()
            date_interview_val = self.interview_date.GetValue()
            date_interview_val = date_interview_val.FormatISODate()
            if insert_person(
                self.encoder_name.GetValue(),
                date_encoded_val,

                self.target_sector.GetSelection(),
                self.target_sector_bene.GetSelection(),
                self.financial_assist.GetSelection(),
                self.amount.GetValue(),
                self.fund_source.GetSelection(),
                self.sw_lname.GetValue(),
                self.sw_fname.GetValue(),
                self.sw_mname.GetValue(),
                date_interview_val,

                self.client_relationship.GetSelection(),

                self.client_lastname.GetValue(),
                self.client_firstname.GetValue(),
                self.client_middlename.GetValue(),

                self.client_ext.GetValue(),

                self.client_gender.GetSelection(),

                cl_bday,
                self.client_age.GetValue(),

                self.client_contact_no.GetValue(),
                self.client_civil_status.GetSelection(),

                self.client_house_street.GetValue(),
                self.client_barangay.GetValue(),
                self.client_city.GetSelection(),

                # Bene
                self.bene_relationship.GetSelection(),

                self.bene_lastname.GetValue(),
                self.bene_firstname.GetValue(),
                self.bene_middlename.GetValue(),
                self.bene_ext.GetValue(),

                self.bene_gender.GetSelection(),

                be_bday,
                self.bene_age.GetValue(),

                self.bene_contact_no.GetValue(),
                self.bene_civil_status.GetSelection(),

                self.bene_house_street.GetValue(),
                self.bene_barangay.GetValue(),
                self.bene_city.GetSelection(),

                self.has_beneficiary.GetValue(),
            ):
                self.load_data_person()
                self.on_clear(None)
            else:
                wx.MessageBox("Record already exist.", "Error", wx.OK | wx.ICON_ERROR)

        dialog.Destroy()

    def on_update_person(self, event):
        dialog = wx.MessageDialog(
            self,
            "Are you sure you want to update ?",
            "Update",
            style=wx.YES_NO | wx.ICON_QUESTION
        )
        result = dialog.ShowModal()

        if result == wx.ID_YES:
            """Updates the selected record"""
            if self.selected_person_id:
                cl_bday = self.client_bday.GetValue()
                cl_bday = cl_bday.FormatISODate()
                be_bday = self.bene_bday.GetValue()
                be_bday = be_bday.FormatISODate()
                date_encoded_val = self.encoded_date.GetValue()
                date_encoded_val = date_encoded_val.FormatISODate()
                date_interview_val = self.interview_date.GetValue()
                date_interview_val = date_interview_val.FormatISODate()
                update_person(
                    self.selected_person_id,
                    self.encoder_name.GetValue(),
                    date_encoded_val,

                    self.target_sector_bene.GetSelection(),
                    self.target_sector.GetSelection(),
                    self.financial_assist.GetSelection(),
                    self.amount.GetValue(),
                    self.fund_source.GetSelection(),
                    self.sw_lname.GetValue(),
                    self.sw_fname.GetValue(),
                    self.sw_mname.GetValue(),
                    date_interview_val,

                    self.client_relationship.GetSelection(),

                    self.client_lastname.GetValue(),
                    self.client_firstname.GetValue(),
                    self.client_middlename.GetValue(),

                    self.client_ext.GetValue(),

                    self.client_gender.GetSelection(),

                    cl_bday,
                    self.client_age.GetValue(),

                    self.client_contact_no.GetValue(),
                    self.client_civil_status.GetSelection(),

                    self.client_house_street.GetValue(),
                    self.client_barangay.GetValue(),
                    self.client_city.GetSelection(),

                    # Bene
                    self.bene_relationship.GetSelection(),

                    self.bene_lastname.GetValue(),
                    self.bene_firstname.GetValue(),
                    self.bene_middlename.GetValue(),
                    self.bene_ext.GetValue(),

                    self.bene_gender.GetSelection(),

                    be_bday,
                    self.bene_age.GetValue(),

                    self.bene_contact_no.GetValue(),
                    self.bene_civil_status.GetSelection(),

                    self.bene_house_street.GetValue(),
                    self.bene_barangay.GetValue(),
                    self.bene_city.GetSelection(),

                    self.has_beneficiary.GetValue(),
                )
                self.load_data_person()
                self.on_clear(None)

        dialog.Destroy()

    def on_delete_person(self, event):
        dialog = wx.MessageDialog(
            self,
            "Are you sure you want to delete?",
            "Delete",
            style=wx.YES_NO | wx.ICON_QUESTION
        )
        result = dialog.ShowModal()

        if result == wx.ID_YES:
            """Deletes the selected record"""
            if self.selected_person_id:
                delete_person_by_id(self.selected_person_id)
                self.load_data_person()
                self.on_clear(None)

        dialog.Destroy()

    def on_set_encoded(self, event):
        dialog = wx.MessageDialog(
            self,
            "Do you want to continue?",
            "Confirm Action",
            style=wx.YES_NO | wx.ICON_QUESTION
        )
        result = dialog.ShowModal()

        if result == wx.ID_YES:
            if self.selected_person_id:
                set_encoded(self.encode_id.GetValue(), True)
                self.load_data_person()
                self.select_first_item()

        dialog.Destroy()

    def on_stop(self, event):
        self.stop_requested = True

    def on_clear(self, event):
        self.selected_person_id = None

    def on_select_person(self, event):
        index = event.GetIndex()
        self.selected_person_id = int(self.list_ctrl.GetItemText(index))

        if self.selected_person_id in self.row_data:
            person = self.row_data[self.selected_person_id]
            self.selected_person_id = person["id"]
            self.encode_id.SetValue(str(person["id"]))

            self.client_lastname.SetValue(person["client_lastname"])
            self.client_firstname.SetValue(person["client_firstname"])
            self.client_middlename.SetValue(person["client_middlename"])

            self.client_age.SetValue(str(person["client_age"]))
            self.client_ext.SetValue(person["client_ext"])
            self.client_relationship.SetSelection(person["client_relationship"])
            self.client_gender.SetSelection(person["client_gender"])
            self.client_civil_status.SetSelection(person["client_civil_status"])
            set_date_value(self.client_bday, person["client_bday"])
            self.client_contact_no.SetValue(person["client_contact_no"])
            self.client_house_street.SetValue(person["client_house_street"])
            self.client_barangay.SetValue(person["client_barangay"])
            self.client_city.SetSelection(person["client_city"])
            self.target_sector.SetSelection(person["target_sector"])

            self.bene_lastname.SetValue(person["bene_lastname"])
            self.bene_firstname.SetValue(person["bene_firstname"])
            self.bene_middlename.SetValue(person["bene_middlename"])

            self.bene_age.SetValue(str(person["bene_age"]))
            self.bene_ext.SetValue(person["bene_ext"])
            self.bene_relationship.SetSelection(person["bene_relationship"])
            self.bene_gender.SetSelection(person["bene_gender"])
            self.bene_civil_status.SetSelection(person["bene_civil_status"])
            set_date_value(self.bene_bday, person["bene_bday"])
            self.bene_contact_no.SetValue(person["bene_contact_no"])
            self.bene_house_street.SetValue(person["bene_house_street"])
            self.bene_barangay.SetValue(person["bene_barangay"])
            self.bene_city.SetSelection(person["bene_city"])

            self.target_sector.SetSelection(person["target_sector"])
            self.financial_assist.SetSelection(person["financial_assist"])
            self.amount.SetValue(person["amount"])
            self.fund_source.SetSelection(person["fund_source"])
            self.sw_lname.SetValue(person["sw_lname"])
            self.sw_fname.SetValue(person["sw_fname"])
            self.sw_mname.SetValue(person["sw_mname"])
            set_date_value(self.interview_date, person["interview_date"])

            self.has_beneficiary.SetValue(person["has_beneficiary"])

            self.sw_last_name.SetValue(person["sw_lname"])
            self.sw_first_name.SetValue(person["sw_fname"])
            self.sw_middle_name.SetValue(person["sw_mname"])

            data_id = get_worker_id(person["sw_lname"], person["sw_fname"], person["sw_mname"])
            if data_id:
                for index, (id_value, lname, fname, mname, thru) in enumerate(self.social_worker_list):
                    if id_value == data_id[0]:
                        self.social_worker.SetSelection(index)
                        break
            else:
                self.social_worker.SetSelection(-1)

    def __init__(self):
        super().__init__(None, title="Client Assistance Form", size=(700, 768))

        self.selected_person_id = None
        self.selected_worker_id = None
        self.driver = None
        self.is_running = False
        self.stop_requested = False

        panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # Scrollable Panel
        scroll = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        scroll.SetScrollRate(5, 5)
        self.scroll_sizer = wx.BoxSizer(wx.VERTICAL)

        # Encoding Forms
        self.fill_forms_btn = wx.Button(panel, label="Fill Form")
        self.fill_forms_btn.Bind(wx.EVT_BUTTON, self.on_button_click)

        # self.clear_all_btn = wx.Button(panel, label="Clear All")
        # self.clear_all_btn.Bind(wx.EVT_BUTTON, self.on_button_clear_all)

        self.save_btn = wx.Button(panel, label="Save")
        self.save_btn.Bind(wx.EVT_BUTTON, self.on_button_save)
        self.save_btn.Hide()

        self.refresh_btn = wx.Button(panel, label="Refresh")
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)

        # Create Checkboxes
        self.cb_website = wx.CheckBox(panel, label="WEB")
        self.cb_offline = wx.CheckBox(panel, label="OFF")
        self.cb_mov = wx.CheckBox(panel, label="MOV")

        # Buttons
        option_sizer = wx.BoxSizer(wx.HORIZONTAL)
        option_sizer.Add(self.cb_website, 1,  wx.EXPAND, 5)
        option_sizer.Add(self.cb_offline, 1,  wx.EXPAND, 5)
        option_sizer.Add(self.cb_mov, 1, wx.EXPAND, 5)



        # Create a notebook (tab panel) inside the scrolled window
        notebook = wx.Notebook(scroll)

        # Create some panels for the tabs
        client_panel = wx.Panel(notebook)
        bene_panel = wx.Panel(notebook)
        sw_panel = wx.Panel(notebook)

        # # Create a BoxSizer with a horizontal layout inside each tab
        box_sizer_client = wx.BoxSizer(wx.VERTICAL)
        box_sizer_bene = wx.BoxSizer(wx.VERTICAL)
        box_sizer_sw = wx.BoxSizer(wx.VERTICAL)

        # Beneficiary Checkbox
        self.has_beneficiary = wx.CheckBox(client_panel, label="Has Beneficiary")
        self.has_beneficiary.Bind(wx.EVT_CHECKBOX, self.has_beneficiary_event)
        box_sizer_client.Add(self.has_beneficiary, 0, wx.ALL | wx.EXPAND, 5)

        self.relationship_choices = [name for _, name in relationship_list]
        self.relationship_data_map = {value: name for name, value in relationship_list}

        self.client_relationship = wx.Choice(client_panel, choices=self.relationship_choices)
        box_sizer_client.Add(wx.StaticText(client_panel, label="Relationship to bene:"), 0, wx.ALL, 5)
        box_sizer_client.Add(self.client_relationship, 0, wx.ALL | wx.EXPAND, 5)

        self.client_lastname = AllCapsTextCtrl(client_panel, style=wx.TE_PROCESS_ENTER)

        self.client_lastname.SetHint("Lastname")
        cl_fullname_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cl_fullname_sizer.Add(self.client_lastname, 1, wx.EXPAND, 5)
        cl_fullname_sizer.AddSpacer(10)

        self.client_firstname = AllCapsTextCtrl(client_panel, style=wx.TE_PROCESS_ENTER)
        self.client_firstname.SetHint("Firstname")
        cl_fullname_sizer.Add(self.client_firstname, 1, wx.EXPAND, 5)
        cl_fullname_sizer.AddSpacer(10)

        self.client_middlename = AllCapsTextCtrl(client_panel, style=wx.TE_PROCESS_ENTER)
        self.client_middlename.SetHint("Middlename")
        cl_fullname_sizer.Add(self.client_middlename, 1, wx.EXPAND, 5)
        cl_fullname_sizer.AddSpacer(10)

        self.client_ext = AllCapsTextCtrl(client_panel, style=wx.TE_PROCESS_ENTER, size=(50, -1))
        self.client_ext.SetHint("Ext")
        cl_fullname_sizer.Add(self.client_ext, 0, wx.EXPAND, 5)

        box_sizer_client.Add(wx.StaticText(client_panel, label="Fullname:"), 0, wx.ALL, 5)
        box_sizer_client.Add(cl_fullname_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.client_gender = wx.Choice(client_panel, choices=gender_list)
        self.client_gender.Bind(wx.EVT_CHOICE, self.on_choice_change_client)  # Bind event
        self.client_gender.SetSelection(0)
        cl_gender_civil_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cl_gender_sizer = wx.BoxSizer(wx.VERTICAL)
        cl_gender_sizer.Add(wx.StaticText(client_panel, label="Gender"), 1, wx.EXPAND, 5)
        cl_gender_sizer.Add(self.client_gender, 1, wx.EXPAND, 5)
        cl_gender_civil_sizer.Add(cl_gender_sizer, 1, wx.EXPAND, 5)

        # Create display strings combining the two data fields
        self.civil_status_choices = [name for _, name in civil_status_list]
        # Create a map for quick lookup
        self.civil_status_data_map = {value: name for name, value in civil_status_list}

        self.client_civil_status = wx.ComboBox(client_panel, choices=self.civil_status_choices, style=wx.CB_READONLY)
        # Bind event
        self.client_civil_status.Bind(wx.EVT_COMBOBOX, self.on_selection)
        cl_gender_civil_sizer.AddSpacer(10)
        cl_civil_sizer = wx.BoxSizer(wx.VERTICAL)
        cl_civil_sizer.Add(wx.StaticText(client_panel, label="Civil Status"), 1, wx.EXPAND, 5)
        cl_civil_sizer.Add(self.client_civil_status, 1, wx.EXPAND, 5)
        cl_gender_civil_sizer.Add(cl_civil_sizer, 1, wx.EXPAND, 5)
        box_sizer_client.Add(cl_gender_civil_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.client_bday = wx.adv.DatePickerCtrl(client_panel, style=wx.adv.DP_DROPDOWN)
        self.client_bday.Bind(wx.adv.EVT_DATE_CHANGED, self.c_compute_age)  # Bind event
        box_sizer_client.Add(wx.StaticText(client_panel, label="Birthday:"), 0, wx.ALL, 5)
        box_sizer_client.Add(self.client_bday, 0, wx.ALL | wx.EXPAND, 5)

        self.client_age = AllCapsTextCtrl(client_panel, style=wx.TE_PROCESS_ENTER)
        box_sizer_client.Add(wx.StaticText(client_panel, label="Age:"), 0, wx.ALL, 5)
        box_sizer_client.Add(self.client_age, 0, wx.ALL | wx.EXPAND, 5)

        self.client_contact_no = AllCapsTextCtrl(client_panel, style=wx.TE_PROCESS_ENTER)
        box_sizer_client.Add(wx.StaticText(client_panel, label="Contact No:"), 0, wx.ALL, 5)
        box_sizer_client.Add(self.client_contact_no, 0, wx.ALL | wx.EXPAND, 5)

        self.client_house_street = AllCapsTextCtrl(client_panel, style=wx.TE_PROCESS_ENTER)
        cl_address_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cl_house_sizer = wx.BoxSizer(wx.VERTICAL)
        cl_house_sizer.Add(wx.StaticText(client_panel, label="House | Street No:"), 1, wx.EXPAND, 5)
        cl_house_sizer.Add(self.client_house_street, 1, wx.EXPAND, 5)
        cl_address_sizer.Add(cl_house_sizer, 1, wx.EXPAND, 5)

        self.client_barangay = AllCapsTextCtrl(client_panel, style=wx.TE_PROCESS_ENTER)
        cl_address_sizer.AddSpacer(10)
        cl_brgy_sizer = wx.BoxSizer(wx.VERTICAL)
        cl_brgy_sizer.Add(wx.StaticText(client_panel, label="Barangay"), 1, wx.EXPAND, 5)
        cl_brgy_sizer.Add(self.client_barangay, 1, wx.EXPAND, 5)
        cl_address_sizer.Add(cl_brgy_sizer, 1, wx.EXPAND, 5)

        self.client_city = wx.Choice(client_panel, choices=list_of_city)
        cl_address_sizer.AddSpacer(10)
        cl_city_sizer = wx.BoxSizer(wx.VERTICAL)
        cl_city_sizer.Add(wx.StaticText(client_panel, label="City | Municipality"), 1, wx.EXPAND, 5)
        cl_city_sizer.Add(self.client_city, 1, wx.EXPAND, 5)
        cl_address_sizer.Add(cl_city_sizer, 1, wx.EXPAND, 5)

        # Force tab order explicitly
        self.client_gender.MoveAfterInTabOrder(self.client_ext)
        self.client_civil_status.MoveAfterInTabOrder(self.client_gender)
        self.client_bday.MoveAfterInTabOrder(self.client_civil_status)
        self.client_age.MoveAfterInTabOrder(self.client_bday)
        self.client_contact_no.MoveAfterInTabOrder(self.client_age)
        self.client_house_street.MoveAfterInTabOrder(self.client_contact_no)
        self.client_barangay.MoveAfterInTabOrder(self.client_house_street)
        self.client_city.MoveAfterInTabOrder(self.client_barangay)

        disable_mousewheel(self.client_relationship)
        disable_mousewheel(self.client_gender)
        disable_mousewheel(self.client_civil_status)
        disable_mousewheel(self.client_city)

        box_sizer_client.Add(cl_address_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.target_sector = wx.Choice(client_panel, choices=target_sector_list)
        self.target_sector.SetSelection(0)
        box_sizer_client.Add(wx.StaticText(client_panel, label="Target Sector"), 0, wx.ALL, 5)
        box_sizer_client.Add(self.target_sector, 1, wx.ALL | wx.EXPAND, 5)

        box_sizer_client.AddSpacer(10)

        # Set the sizer for each panel
        client_panel.SetSizerAndFit(box_sizer_client)

        # Beneficiary Checkbox
        self.same_address = wx.CheckBox(bene_panel, label="Same Address")
        self.same_address.Bind(wx.EVT_CHECKBOX, self.same_address_event)

        self.same_contact = wx.CheckBox(bene_panel, label="Same Contact No.")
        self.same_contact.Bind(wx.EVT_CHECKBOX, self.same_contact_event)

        helper_sizer = wx.BoxSizer(wx.HORIZONTAL)
        helper_sizer.Add(self.same_address, 0, wx.ALL | wx.EXPAND, 5)
        helper_sizer.Add(self.same_contact, 0, wx.ALL | wx.EXPAND, 5)

        box_sizer_bene.Add(helper_sizer, 0, wx.EXPAND, 5)

        self.relationship_choices = [name for _, name in relationship_list]
        self.relationship_data_map = {value: name for name, value in relationship_list}

        self.bene_relationship = wx.Choice(bene_panel, choices=self.relationship_choices)
        self.bene_relationship.SetSelection(0)
        box_sizer_bene.Add(wx.StaticText(bene_panel, label="Relationship to bene:"), 0, wx.ALL, 5)
        box_sizer_bene.Add(self.bene_relationship, 0, wx.ALL | wx.EXPAND, 5)

        self.bene_lastname = AllCapsTextCtrl(bene_panel, style=wx.TE_PROCESS_ENTER)
        self.bene_firstname = AllCapsTextCtrl(bene_panel, style=wx.TE_PROCESS_ENTER)
        self.bene_middlename = AllCapsTextCtrl(bene_panel, style=wx.TE_PROCESS_ENTER)
        self.bene_lastname.SetHint("Lastname")
        self.bene_firstname.SetHint("Firstname")
        self.bene_middlename.SetHint("Middlename")
        self.bene_ext = AllCapsTextCtrl(bene_panel, style=wx.TE_PROCESS_ENTER, size=(50, -1))
        self.bene_ext.SetHint("Ext")
        bene_fullname_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bene_fullname_sizer.Add(self.bene_lastname, 1, wx.EXPAND, 5)
        bene_fullname_sizer.AddSpacer(10)
        bene_fullname_sizer.Add(self.bene_firstname, 1, wx.EXPAND, 5)
        bene_fullname_sizer.AddSpacer(10)
        bene_fullname_sizer.Add(self.bene_middlename, 1, wx.EXPAND, 5)
        bene_fullname_sizer.AddSpacer(10)
        bene_fullname_sizer.Add(self.bene_ext, 0, wx.EXPAND, 5)

        box_sizer_bene.Add(wx.StaticText(bene_panel, label="Fullname:"), 0, wx.ALL, 5)
        box_sizer_bene.Add(bene_fullname_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.bene_gender = wx.Choice(bene_panel, choices=gender_list)
        self.bene_gender.Bind(wx.EVT_CHOICE, self.on_choice_change_bene)  # Bind event
        self.bene_gender.SetSelection(0)
        bene_gender_civil_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bene_gender_sizer = wx.BoxSizer(wx.VERTICAL)
        bene_gender_sizer.Add(wx.StaticText(bene_panel, label="Gender"), 1, wx.EXPAND, 5)
        bene_gender_sizer.Add(self.bene_gender, 1, wx.EXPAND, 5)
        bene_gender_civil_sizer.Add(bene_gender_sizer, 1, wx.EXPAND, 5)

        self.bene_civil_status = wx.Choice(bene_panel,choices=self.civil_status_choices)
        bene_gender_civil_sizer.AddSpacer(10)
        bene_civil_sizer = wx.BoxSizer(wx.VERTICAL)
        bene_civil_sizer.Add(wx.StaticText(bene_panel, label="Civil Status"), 1, wx.EXPAND, 5)
        bene_civil_sizer.Add(self.bene_civil_status, 1, wx.EXPAND, 5)
        bene_gender_civil_sizer.Add(bene_civil_sizer, 1, wx.EXPAND, 5)

        box_sizer_bene.Add(bene_gender_civil_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.bene_bday = wx.adv.DatePickerCtrl(bene_panel, style=wx.adv.DP_DROPDOWN)
        self.bene_bday.Bind(wx.adv.EVT_DATE_CHANGED, self.b_compute_age)  # Bind event
        box_sizer_bene.Add(wx.StaticText(bene_panel, label="Birthday:"), 0, wx.ALL, 5)
        box_sizer_bene.Add(self.bene_bday, 0, wx.ALL | wx.EXPAND, 5)

        self.bene_age = AllCapsTextCtrl(bene_panel, style=wx.TE_PROCESS_ENTER)
        box_sizer_bene.Add(wx.StaticText(bene_panel, label="Age:"), 0, wx.ALL, 5)
        box_sizer_bene.Add(self.bene_age, 0, wx.ALL | wx.EXPAND, 5)

        self.bene_contact_no = AllCapsTextCtrl(bene_panel, style=wx.TE_PROCESS_ENTER)
        box_sizer_bene.Add(wx.StaticText(bene_panel, label="Contact No:"), 0, wx.ALL, 5)
        box_sizer_bene.Add(self.bene_contact_no, 0, wx.ALL | wx.EXPAND, 5)

        self.bene_house_street = AllCapsTextCtrl(bene_panel, style=wx.TE_PROCESS_ENTER)
        self.bene_barangay = AllCapsTextCtrl(bene_panel, style=wx.TE_PROCESS_ENTER)
        self.bene_city = wx.Choice(bene_panel, choices=list_of_city)

        bene_address_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bene_house_sizer = wx.BoxSizer(wx.VERTICAL)
        bene_house_sizer.Add(wx.StaticText(bene_panel, label="House | Street No:"), 1, wx.EXPAND, 5)
        bene_house_sizer.Add(self.bene_house_street, 1, wx.EXPAND, 5)
        bene_address_sizer.Add(bene_house_sizer, 1, wx.EXPAND, 5)

        bene_address_sizer.AddSpacer(10)
        bene_brgy_sizer = wx.BoxSizer(wx.VERTICAL)
        bene_brgy_sizer.Add(wx.StaticText(bene_panel, label="Barangay"), 1, wx.EXPAND, 5)
        bene_brgy_sizer.Add(self.bene_barangay, 1, wx.EXPAND, 5)
        bene_address_sizer.Add(bene_brgy_sizer, 1, wx.EXPAND, 5)

        bene_address_sizer.AddSpacer(10)
        bene_city_sizer = wx.BoxSizer(wx.VERTICAL)
        bene_city_sizer.Add(wx.StaticText(bene_panel, label="City | Municipality"), 1, wx.EXPAND, 5)
        bene_city_sizer.Add(self.bene_city, 1, wx.EXPAND, 5)
        bene_address_sizer.Add(bene_city_sizer, 1, wx.EXPAND, 5)

        box_sizer_bene.Add(bene_address_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Force tab order explicitly
        self.bene_gender.MoveAfterInTabOrder(self.bene_ext)
        self.bene_civil_status.MoveAfterInTabOrder(self.bene_gender)
        self.bene_bday.MoveAfterInTabOrder(self.bene_civil_status)
        self.bene_age.MoveAfterInTabOrder(self.bene_bday)
        self.bene_contact_no.MoveAfterInTabOrder(self.bene_age)
        self.bene_house_street.MoveAfterInTabOrder(self.bene_contact_no)
        self.bene_barangay.MoveAfterInTabOrder(self.bene_house_street)
        self.bene_city.MoveAfterInTabOrder(self.bene_barangay)
        #
        disable_mousewheel(self.bene_relationship)
        disable_mousewheel(self.bene_gender)
        disable_mousewheel(self.bene_civil_status)
        disable_mousewheel(self.bene_city)

        self.target_sector_bene = wx.Choice(bene_panel, choices=target_sector_list)
        self.target_sector_bene.SetSelection(0)
        box_sizer_bene.Add(wx.StaticText(bene_panel, label="Target Sector Beneficiary"), 0, wx.ALL| wx.EXPAND, 5)
        box_sizer_bene.Add(self.target_sector_bene, 1, wx.ALL | wx.EXPAND, 5)
        box_sizer_bene.AddSpacer(10)

        bene_panel.SetSizerAndFit(box_sizer_bene)

        self.sw_last_name = wx.TextCtrl(sw_panel)
        self.sw_first_name = wx.TextCtrl(sw_panel)
        self.sw_middle_name = wx.TextCtrl(sw_panel)
        self.sw_last_name.SetHint("Last Name")
        self.sw_first_name.SetHint("First Name")
        self.sw_middle_name.SetHint("Middle Name")

        sw_sizer_fullname = wx.BoxSizer(wx.HORIZONTAL)
        sw_sizer_fullname.Add(self.sw_last_name, 1, wx.EXPAND, 5)
        sw_sizer_fullname.AddSpacer(10)
        sw_sizer_fullname.Add(self.sw_first_name, 1, wx.EXPAND, 5)
        sw_sizer_fullname.AddSpacer(10)
        sw_sizer_fullname.Add(self.sw_middle_name, 1, wx.EXPAND, 5)

        # Search thru Firstname
        self.sw_thru_first_name = wx.CheckBox(sw_panel, label="Search thru Firstname")
        # assist_box.Add(self.thru_firstname, 0, wx.ALL, 5)

        sw_sizer_caption = wx.BoxSizer(wx.HORIZONTAL)
        sw_sizer_caption.Add(wx.StaticText(sw_panel, label="Fullname (SW)"), 1, wx.ALL, 5)
        sw_sizer_caption.Add(self.sw_thru_first_name, 0, wx.ALL, 5)

        box_sizer_sw.AddSpacer(10)
        box_sizer_sw.Add(sw_sizer_caption, 0, wx.EXPAND, 5)
        box_sizer_sw.Add(sw_sizer_fullname, 0, wx.ALL | wx.EXPAND, 5)

        btn_sw_add = wx.Button(sw_panel, label="Add")
        btn_sw_update = wx.Button(sw_panel, label="Update")
        btn_sw_delete = wx.Button(sw_panel, label="Delete")

        # Event bindings
        btn_sw_add.Bind(wx.EVT_BUTTON, self.on_add_worker)
        btn_sw_update.Bind(wx.EVT_BUTTON, self.on_update_worker)
        btn_sw_delete.Bind(wx.EVT_BUTTON, self.on_delete_worker)

        control_container = wx.BoxSizer(wx.HORIZONTAL)
        control_container.Add(btn_sw_add, 0, wx.EXPAND, 5)
        control_container.AddSpacer(5)
        control_container.Add(btn_sw_update, 0, wx.EXPAND, 5)
        control_container.AddSpacer(5)
        control_container.Add(btn_sw_delete, 0, wx.EXPAND, 5)
        control_container.AddSpacer(5)

        box_sizer_sw.Add(control_container, 0, wx.ALL | wx.EXPAND, 5)

        # Table (ListCtrl)
        self.list_ctrl_worker = wx.ListCtrl(sw_panel, style=wx.LB_SINGLE, size=(-1, -1))
        self.list_ctrl_worker.InsertColumn(0, "ID", width=30)
        self.list_ctrl_worker.InsertColumn(1, "Lastname", width=200)
        self.list_ctrl_worker.InsertColumn(2, "Firstname", width=200)
        self.list_ctrl_worker.InsertColumn(3, "Middlename", width=100)
        self.list_ctrl_worker.InsertColumn(4, "Thru Firstname", width=100)
        self.list_ctrl_worker.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select_worker)
        box_sizer_sw.Add(self.list_ctrl_worker, 1, wx.ALL | wx.EXPAND, 5)

        sw_panel.SetSizerAndFit(box_sizer_sw)

        # Add panels to the notebook
        notebook.AddPage(client_panel, "Client Information")
        notebook.AddPage(bene_panel, "Beneficiary Details")
        notebook.AddPage(sw_panel, "Social Worker")

        self.scroll_sizer.Add(notebook, 1, flag=wx.EXPAND)

        self.mode_of_admission = wx.Choice(scroll, choices=["On-site", "Walk-in", "Referral"])
        self.mode_of_admission.SetSelection(1)  # Default: Walk-In

        self.interview_date = wx.adv.DatePickerCtrl(scroll)

        # Assistance Information Group

        assist_box = wx.BoxSizer(wx.VERTICAL)
        assistance_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.amount = wx.TextCtrl(scroll)
        assistance_amount_sizer = wx.BoxSizer(wx.VERTICAL)
        assistance_amount_sizer.Add(wx.StaticText(scroll, label="Amount:"), 0, wx.ALL, 5)
        assistance_amount_sizer.Add(self.amount, 0, wx.EXPAND, 5)
        assistance_sizer.Add(assistance_amount_sizer, 1, wx.EXPAND, 5)

        assistance_sizer.AddSpacer(10)

        self.financial_assist = wx.Choice(scroll, choices=financial_assistance_list, size=(150, -1))
        self.financial_assist.SetSelection(4)
        assistance_financial_sizer = wx.BoxSizer(wx.VERTICAL)
        assistance_financial_sizer.Add(wx.StaticText(scroll, label="Assistance"), 1, wx.ALL , 5)
        assistance_financial_sizer.Add(self.financial_assist, 0, wx.EXPAND, 5)
        assistance_sizer.Add(assistance_financial_sizer, 0, wx.EXPAND, 5)

        assistance_sizer.AddSpacer(10)

        # PSIF 2025, AKAP
        self.fund_source_choices = [name for _, name in fund_source_list]
        self.fund_source_data_map = {value: name for name, value in fund_source_list}

        self.fund_source = wx.Choice(scroll, choices=self.fund_source_choices, size=(150, -1))
        self.fund_source.SetSelection(1)
        fund_sizer = wx.BoxSizer(wx.VERTICAL)
        fund_sizer.Add(wx.StaticText(scroll, label="Fund Source:"), 1, wx.ALL, 5)
        fund_sizer.Add(self.fund_source, 0, wx.EXPAND, 5)
        assistance_sizer.Add(fund_sizer, 0, wx.EXPAND, 5)

        assist_box.Add(assistance_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.social_worker_list = get_all_workers()
        self.social_worker_choices = [f"{fname}, {mname}, {lname}" for (_id, lname, fname, mname, _thru) in self.social_worker_list]

        self.social_worker = wx.Choice(scroll, choices=self.social_worker_choices, size=(150, -1))
        self.social_worker.Bind(wx.EVT_CHOICE, self.on_selection_worker)  # Bind event

        self.social_worker_filter = wx.TextCtrl(scroll)
        self.social_worker_filter.Bind(wx.EVT_TEXT, self.on_sw_text_change)

        worker_label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        worker_label_sizer.Add(wx.StaticText(scroll, label="Social Worker"), 1, wx.ALL, 5)
        assist_box.Add(worker_label_sizer, 0, wx.EXPAND, 5)

        worker_sizer = wx.BoxSizer(wx.HORIZONTAL)
        worker_sizer.Add(self.social_worker_filter, 0,  wx.EXPAND, 5)
        worker_sizer.AddSpacer(10)
        worker_sizer.Add(self.social_worker, 1,  wx.EXPAND, 5)

        assist_box.Add(worker_sizer, 0, wx.ALL | wx.EXPAND, 5)

        mode_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mode_of_admission_sizer = wx.BoxSizer(wx.VERTICAL)
        mode_of_admission_sizer.Add(wx.StaticText(scroll, label="Mode of Admission:"), 0, wx.ALL, 5)
        mode_of_admission_sizer.Add(self.mode_of_admission, 0, wx.EXPAND, 5)
        mode_sizer.Add(mode_of_admission_sizer, 1, wx.EXPAND, 5)

        mode_sizer.AddSpacer(10)

        date_interview_sizer = wx.BoxSizer(wx.VERTICAL)
        date_interview_sizer.Add(wx.StaticText(scroll, label="Date Interview :"), 0, wx.ALL, 5)
        date_interview_sizer.Add(self.interview_date, 0, wx.EXPAND, 5)
        mode_sizer.Add(date_interview_sizer, 1, wx.EXPAND, 5)

        assist_box.Add(mode_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.sw_lname = wx.TextCtrl(scroll)
        self.sw_fname = wx.TextCtrl(scroll)
        self.sw_mname = wx.TextCtrl(scroll)
        self.sw_lname.SetHint("Lastname")
        self.sw_fname.SetHint("Firstname")
        self.sw_mname.SetHint("Middlename")
        self.sw_lname.Hide()
        self.sw_fname.Hide()
        self.sw_mname.Hide()

        sw_fullname_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sw_fullname_sizer.Add(self.sw_lname, 1, wx.EXPAND, 5)
        sw_fullname_sizer.AddSpacer(10)
        sw_fullname_sizer.Add(self.sw_fname, 1, wx.EXPAND, 5)
        sw_fullname_sizer.AddSpacer(10)
        sw_fullname_sizer.Add(self.sw_mname, 1, wx.EXPAND, 5)

        # Search thru Firstname
        self.thru_firstname = wx.CheckBox(scroll, label="Search thru Firstname")
        self.thru_firstname.Hide()

        label_sw = wx.StaticText(scroll, label="Fullname (SW)")
        label_sw.Hide()
        # assist_box.Add(self.thru_firstname, 0, wx.ALL, 5)

        sw_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sw_sizer.Add(label_sw, 1, wx.ALL, 5)
        sw_sizer.Add(self.thru_firstname, 0, wx.ALL, 5)

        # Force tab order explicitly
        self.financial_assist.MoveAfterInTabOrder(self.amount)
        self.fund_source.MoveAfterInTabOrder(self.financial_assist)
        self.mode_of_admission.MoveAfterInTabOrder(self.fund_source)
        self.interview_date.MoveAfterInTabOrder(self.mode_of_admission)
        self.sw_lname.MoveAfterInTabOrder(self.interview_date)
        self.sw_fname.MoveAfterInTabOrder(self.sw_lname)
        self.sw_mname.MoveAfterInTabOrder(self.sw_fname)

        disable_mousewheel(self.target_sector)
        disable_mousewheel(self.financial_assist)

        self.encode_id = wx.TextCtrl(scroll)
        self.encode_id.Hide()

        horizontal_line = wx.StaticLine(scroll, style=wx.LI_HORIZONTAL)
        assist_box.AddSpacer(5)
        assist_box.Add(horizontal_line, 0, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=5)

        self.encoder_name = AllCapsTextCtrl(scroll, style=wx.TE_PROCESS_ENTER)
        assist_box.Add(wx.StaticText(scroll, label="Encoder Name:"), 0, wx.ALL, 5)
        assist_box.Add(self.encoder_name, 0, wx.ALL | wx.EXPAND, 5)

        self.encoded_date = wx.adv.DatePickerCtrl(scroll)
        assist_box.Add(wx.StaticText(scroll, label="Date Entered:"), 0, wx.ALL, 5)
        assist_box.Add(self.encoded_date, 0, wx.ALL | wx.EXPAND, 5)

        horizontal_line = wx.StaticLine(scroll, style=wx.LI_HORIZONTAL)
        self.scroll_sizer.AddSpacer(5)
        self.scroll_sizer.Add(horizontal_line, 0, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=5)

        self.scroll_sizer.Add(assist_box, 0,  wx.EXPAND, 10)

        scroll.SetSizer(self.scroll_sizer)

        crud_container = wx.BoxSizer(wx.VERTICAL)

        self.auto_next = wx.CheckBox(panel, label="Auto Next")
        self.auto_submit = wx.CheckBox(panel, label="Auto Submit")
        self.auto_finish = wx.CheckBox(panel, label="Auto Finish")

        btn_crud_add = wx.Button(panel, label="Add")
        btn_crud_update = wx.Button(panel, label="Update")
        btn_crud_delete = wx.Button(panel, label="Delete")


        # Event bindings
        btn_crud_add.Bind(wx.EVT_BUTTON, self.on_add_person)
        btn_crud_update.Bind(wx.EVT_BUTTON, self.on_update_person)
        btn_crud_delete.Bind(wx.EVT_BUTTON, self.on_delete_person)

        control_container = wx.BoxSizer(wx.HORIZONTAL)
        control_container.Add(btn_crud_add, 0,  wx.EXPAND, 5)
        control_container.AddSpacer(5)
        control_container.Add(btn_crud_update, 0, wx.EXPAND, 5)
        control_container.AddSpacer(5)
        control_container.Add(btn_crud_delete, 0,  wx.EXPAND, 5)
        control_container.AddSpacer(5)

        btn_set_encoded = wx.Button(panel, label="Set Encoded")
        btn_set_encoded.Bind(wx.EVT_BUTTON, self.on_set_encoded)
        control_container.Add(btn_set_encoded, 0, wx.EXPAND, 5)
        control_container.AddSpacer(5)

        control_container.Add(wx.StaticText(panel, label=""), 1,  wx.EXPAND, 5)

        self.cb_encoded = wx.CheckBox(panel, label="Encoded")
        self.cb_encoded.Bind(wx.EVT_CHECKBOX, self.on_checkbox_change)
        export_sizer = wx.BoxSizer(wx.HORIZONTAL)
        control_container.Add(self.cb_encoded, 0,  wx.EXPAND, 5)

        btn_export = wx.Button(panel, label="Export")
        btn_export.Bind(wx.EVT_BUTTON, self.on_export)
        control_container.Add(btn_export, 0,  wx.EXPAND, 5)

        crud_container.Add(control_container, 0, wx.EXPAND | wx.ALL , 5)

        list_container = wx.BoxSizer(wx.VERTICAL)

        # Table (ListCtrl)
        self.list_ctrl = wx.ListCtrl(panel, style=wx.LB_SINGLE)
        self.list_ctrl.InsertColumn(0, "ID", width=30)
        self.list_ctrl.InsertColumn(1, "Lastname", width=100)
        self.list_ctrl.InsertColumn(2, "Firstname", width=100)
        self.list_ctrl.InsertColumn(3, "Middlename", width=100)
        self.list_ctrl.InsertColumn(4, "Ext", width=50)
        self.list_ctrl.InsertColumn(5, "Bday", width=100)
        self.list_ctrl.InsertColumn(6, "Age", width=50)
        self.list_ctrl.InsertColumn(7, "Assistance", width=100)
        self.list_ctrl.InsertColumn(8, "Amount", width=100)
        self.list_ctrl.InsertColumn(9, "SW", width=100)
        self.list_ctrl.InsertColumn(10, "Encoded", width=80)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select_person)

        list_container.Add(self.list_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        list_log_container = wx.BoxSizer(wx.HORIZONTAL)
        list_log_container.Add(list_container, 1, wx.EXPAND , 10)
        crud_container.Add(list_log_container, 1, wx.ALL | wx.EXPAND, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(option_sizer, 0, wx.EXPAND, 5)
        btn_sizer.Add(self.fill_forms_btn, 1, wx.EXPAND, 5)
        btn_sizer.Add(self.refresh_btn, 1, wx.EXPAND, 5)

        btn_stop = wx.Button(panel, label="Stop")
        btn_stop.Bind(wx.EVT_BUTTON, self.on_stop)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        hbox_btns.AddMany([
            (self.auto_next, 0, wx.ALL | wx.EXPAND, 5),
            (self.auto_submit, 0, wx.ALL | wx.EXPAND, 5),
            (self.auto_finish, 0, wx.ALL | wx.EXPAND, 5),
            (btn_stop, 0, wx.ALL | wx.EXPAND, 5),
            (wx.StaticText(panel, label=""), 1, wx.ALL | wx.EXPAND, 5),
            (btn_sizer, 1, wx.ALL, 5)
        ])
        crud_container.Add(hbox_btns, 0, wx.ALL , 5)

        self.command_log = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 100))
        self.command_log.SetMinSize((-1, 50))
        crud_container.Add(self.command_log, 0, wx.EXPAND, 10)

        self.sizer.Add(scroll, 1, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(crud_container, 0, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(self.sizer)
        self.Centre()

        self.on_check_pickle()

        self.load_data_person()
        self.load_data_worker()

    def on_choice_change_client(self, event):
        bday_wx = self.client_bday.GetValue()

        bday_date = datetime(bday_wx.GetYear(), bday_wx.GetMonth() + 1, bday_wx.GetDay())

        today = datetime.today()
        age_value = today.year - bday_date.year - ((today.month, today.day) < (bday_date.month, bday_date.day))

        if age_value >= 60:
            self.target_sector.SetSelection(3)
        elif 13 <= age_value <= 19:
            self.target_sector.SetSelection(5)
        elif age_value < 13:
            self.target_sector.SetSelection(4)
        else:
            if self.client_gender.GetStringSelection() == "Female":
                self.target_sector.SetSelection(1)
            else:
                self.target_sector.SetSelection(0)

    def on_choice_change_bene(self, event):
        bday_wx = self.bene_bday.GetValue()

        bday_date = datetime(bday_wx.GetYear(), bday_wx.GetMonth() + 1, bday_wx.GetDay())

        today = datetime.today()
        age_value = today.year - bday_date.year - ((today.month, today.day) < (bday_date.month, bday_date.day))

        if age_value >= 60:
            self.target_sector_bene.SetSelection(3)
        elif 13 <= age_value <= 19:
            self.target_sector_bene.SetSelection(5)
        elif age_value < 13:
            self.target_sector_bene.SetSelection(4)
        else:
            if self.bene_gender.GetStringSelection() == "Female":
                self.target_sector_bene.SetSelection(1)
            else:
                self.target_sector_bene.SetSelection(0)

    def c_compute_age(self, event):
        """Compute age based on selected birthday."""

        bday_wx = self.client_bday.GetValue()
        bday_date = datetime(bday_wx.GetYear(), bday_wx.GetMonth() + 1, bday_wx.GetDay())

        today = datetime.today()
        age_value = today.year - bday_date.year - ((today.month, today.day) < (bday_date.month, bday_date.day))

        if age_value >= 60:
            self.target_sector.SetSelection(3)
        elif 13 <= age_value <= 19:
            self.target_sector.SetSelection(5)
        elif age_value < 13:
            self.target_sector.SetSelection(4)
        else:
            if self.client_gender.GetStringSelection() == "Female":
                self.target_sector.SetSelection(1)
            else:
                self.target_sector.SetSelection(0)

        self.client_age.SetValue(str(age_value))

    def b_compute_age(self, event):
        """Compute age based on selected birthday."""

        bday_wx = self.bene_bday.GetValue()
        bday_date = datetime(bday_wx.GetYear(), bday_wx.GetMonth() + 1, bday_wx.GetDay())

        today = datetime.today()
        age_value = today.year - bday_date.year - ((today.month, today.day) < (bday_date.month, bday_date.day))

        if age_value >= 60:
            self.target_sector_bene.SetSelection(3)
        elif 13 <= age_value <= 19:
            self.target_sector_bene.SetSelection(5)
        elif age_value < 13:
            self.target_sector_bene.SetSelection(4)
        else:
            if self.bene_gender.GetStringSelection() == "Female":
                self.target_sector_bene.SetSelection(1)
            else:
                self.target_sector_bene.SetSelection(0)

        self.bene_age.SetValue(str(age_value))

    def set_running_flag(self, value):
        self.is_running = value

    def on_button_click(self, event):
        self.on_save_data()

        if self.is_running:
            self.command_log.AppendText("Task already running... Please wait.\n")
            return

        self.is_running = True  # Set flag to prevent re-clicking
        # Start a new thread to run the on_fill_up function
        self.command_log.AppendText("Task started... Please wait.\n")
        thread = threading.Thread(target=self.on_fill_up, daemon=True)
        thread.start()

    def on_check_pickle(self):
        file_path = "data-old.pkl"

        # Check if the file exists
        if os.path.exists(file_path):
            self.on_load_data()
        else:
            self.on_save_data()

    def on_load_data(self):

        # Load from file
        with open("data-old.pkl", "rb") as file:
            self.loaded_data = pickle.load(file)
        print("Loaded Data:", self.loaded_data)

        # basic info
        self.mode_of_admission.SetSelection(self.loaded_data.get("mode_of_admission"))
        self.encoder_name.SetValue(self.loaded_data.get("encoder_name"))
        set_date_value(self.encoded_date, self.loaded_data.get("encoded_date"))

        # assistance info
        self.auto_next.SetValue(self.loaded_data.get("auto_next"))
        self.auto_submit.SetValue(self.loaded_data.get("auto_submit"))
        self.thru_firstname.SetValue(self.loaded_data.get("thru_firstname"))
        self.target_sector.SetSelection(self.loaded_data.get("target_sector"))
        self.financial_assist.SetSelection(self.loaded_data.get("financial_assist"))
        self.amount.SetValue(self.loaded_data.get("amount"))
        self.fund_source.SetSelection(self.loaded_data.get("fund_source"))
        self.sw_lname.SetValue(self.loaded_data.get("sw_lname"))
        self.sw_fname.SetValue(self.loaded_data.get("sw_fname"))
        self.sw_mname.SetValue(self.loaded_data.get("sw_mname"))
        set_date_value(self.interview_date, self.loaded_data.get("interview_date"))

        # client
        self.client_relationship.SetSelection(self.loaded_data.get("client_relationship"))

        self.client_lastname.SetValue(self.loaded_data.get("client_lastname"))
        self.client_firstname.SetValue(self.loaded_data.get("client_firstname"))
        self.client_middlename.SetValue(self.loaded_data.get("client_middlename"))

        self.client_ext.SetValue(self.loaded_data.get("client_ext"))

        self.client_gender.SetSelection(self.loaded_data.get("client_gender"))

        set_date_value(self.client_bday, self.loaded_data.get("client_bday"))
        self.client_age.SetValue(self.loaded_data.get("client_age"))

        self.client_contact_no.SetValue(self.loaded_data.get("client_contact_no"))
        self.client_civil_status.SetSelection(self.loaded_data.get("client_civil_status"))

        self.client_house_street.SetValue(self.loaded_data.get("client_house_street"))
        self.client_barangay.SetValue(self.loaded_data.get("client_barangay"))
        self.client_city.SetSelection(self.loaded_data.get("client_city"))

        # Bene
        self.bene_relationship.SetSelection(self.loaded_data.get("bene_relationship"))

        self.bene_lastname.SetValue(self.loaded_data.get("bene_lastname"))
        self.bene_firstname.SetValue(self.loaded_data.get("bene_firstname"))
        self.bene_middlename.SetValue(self.loaded_data.get("bene_middlename"))
        self.bene_ext.SetValue(self.loaded_data.get("bene_ext"))

        self.bene_gender.SetSelection(self.loaded_data.get("bene_gender"))

        set_date_value(self.bene_bday, self.loaded_data.get("bene_bday"))
        self.bene_age.SetValue(self.loaded_data.get("bene_age"))

        self.bene_contact_no.SetValue(self.loaded_data.get("bene_contact_no"))
        self.bene_civil_status.SetSelection(self.loaded_data.get("bene_civil_status"))

        self.bene_house_street.SetValue(self.loaded_data.get("bene_house_street"))
        self.bene_barangay.SetValue(self.loaded_data.get("bene_barangay"))
        self.bene_city.SetSelection(self.loaded_data.get("bene_city"))

        self.has_beneficiary.SetValue(self.loaded_data.get("has_beneficiary"))

        self.cb_encoded.SetValue(self.loaded_data.get("cb_encoded"))

        self.auto_finish.SetValue(self.loaded_data.get("auto_finish"))

        self.selected_person_id = self.loaded_data.get("selected_id")

        #encode_id
        self.encode_id.SetValue(str(self.selected_person_id))

    def on_save_data(self):
        self.data = {}

        # basic info
        self.data["mode_of_admission"] = self.mode_of_admission.GetSelection()
        self.data["encoder_name"] = self.encoder_name.GetValue()
        self.data["encoded_date"] = get_date_value(self.encoded_date)

        # assistance info
        self.data["auto_next"] = self.auto_next.GetValue()
        self.data["auto_submit"] = self.auto_submit.GetValue()
        self.data["thru_firstname"] = self.thru_firstname.GetValue()
        self.data["target_sector"] = self.target_sector.GetSelection()
        self.data["financial_assist"] = self.financial_assist.GetSelection()
        self.data["amount"] = self.amount.GetValue()
        self.data["fund_source"] = self.fund_source.GetSelection()
        self.data["sw_lname"] = self.sw_lname.GetValue()
        self.data["sw_fname"] = self.sw_fname.GetValue()
        self.data["sw_mname"] = self.sw_mname.GetValue()
        self.data["interview_date"] = get_date_value(self.interview_date)

        # client
        self.data["client_relationship"] = self.client_relationship.GetSelection()

        self.data["client_lastname"] = self.client_lastname.GetValue()
        self.data["client_firstname"] = self.client_firstname.GetValue()
        self.data["client_middlename"] = self.client_middlename.GetValue()
        self.data["client_ext"] = self.client_ext.GetValue()

        self.data["client_gender"] = self.client_gender.GetSelection()

        self.data["client_bday"] = get_date_value(self.client_bday)
        self.data["client_age"] = self.client_age.GetValue()

        self.data["client_contact_no"] = self.client_contact_no.GetValue()
        self.data["client_civil_status"] = self.client_civil_status.GetSelection()

        self.data["client_house_street"] = self.client_house_street.GetValue()
        self.data["client_barangay"] = self.client_barangay.GetValue()
        self.data["client_city"] = self.client_city.GetSelection()

        # Bene
        self.data["bene_relationship"] = self.bene_relationship.GetSelection()

        self.data["bene_lastname"] = self.bene_lastname.GetValue()
        self.data["bene_firstname"] = self.bene_firstname.GetValue()
        self.data["bene_middlename"] = self.bene_middlename.GetValue()
        self.data["bene_ext"] = self.bene_ext.GetValue()

        self.data["bene_gender"] = self.bene_gender.GetSelection()

        self.data["bene_bday"] = get_date_value(self.bene_bday)
        self.data["bene_age"] = self.bene_age.GetValue()

        self.data["bene_contact_no"] = self.bene_contact_no.GetValue()
        self.data["bene_civil_status"] = self.bene_civil_status.GetSelection()

        self.data["bene_house_street"] = self.bene_house_street.GetValue()
        self.data["bene_barangay"] = self.bene_barangay.GetValue()
        self.data["bene_city"] = self.bene_city.GetSelection()

        self.data["has_beneficiary"] = self.has_beneficiary.GetValue()
        self.data["cb_encoded"] = self.cb_encoded.GetValue()

        self.data["auto_finish"] =self.auto_finish.GetValue()

        self.data["selected_id"] = self.encode_id.GetValue()

        # Save to file
        with open("data-old.pkl", "wb") as file:
            pickle.dump(self.data, file)

    def on_button_clear_all(self, event):
        self.client_lastname.SetValue("")

        self.client_firstname.SetValue("")
        self.client_middlename.SetValue("")

        self.client_contact_no.SetValue("")
        self.client_age.SetValue("")

        self.client_house_street.SetValue("")
        self.client_barangay.SetValue("")

        self.client_gender.SetSelection(-1)
        self.client_civil_status.SetSelection(-1)
        self.client_city.SetSelection(-1)

        self.bene_lastname.SetValue("")
        self.bene_firstname.SetValue("")
        self.bene_middlename.SetValue("")

        self.bene_contact_no.SetValue("")
        self.bene_age.SetValue("")

        self.bene_house_street.SetValue("")
        self.bene_barangay.SetValue("")

        self.bene_gender.SetSelection(-1)
        self.bene_civil_status.SetSelection(-1)
        self.bene_city.SetSelection(-1)

        self.command_log.AppendText("All fields have been cleared.\n")

    def on_button_save(self, event):
        data = {}
        # basic info
        data["mode_of_admission"] = self.mode_of_admission.GetSelection()
        data["encoder_name"] = self.encoder_name.GetValue()
        data["encoded_date"] = get_date_value(self.encoded_date)

        # assistance info
        data["auto_next"] = self.auto_next.GetValue()
        data["auto_submit"] = self.auto_submit.GetValue()
        data["thru_firstname"] = self.thru_firstname.GetValue()
        data["target_sector"] = self.target_sector.GetSelection()
        data["financial_assist"] = self.financial_assist.GetSelection()
        data["amount"] = self.amount.GetValue()
        data["fund_source"] = self.fund_source.GetSelection()
        data["sw_lname"] = self.sw_lname.GetValue()
        data["sw_fname"] = self.sw_fname.GetValue()
        data["sw_mname"] = self.sw_mname.GetValue()
        data["interview_date"] = get_date_value(self.interview_date)

        # client
        data["client_relationship"] = self.client_relationship.GetSelection()

        data["client_lastname"] = self.client_lastname.GetValue()
        data["client_firstname"] = self.client_firstname.GetValue()
        data["client_middlename"] = self.client_middlename.GetValue()

        data["client_gender"] = self.client_gender.GetSelection()

        data["client_bday"] = get_date_value(self.client_bday)
        data["client_age"] = self.client_age.GetValue()

        data["client_contact_no"] = self.client_contact_no.GetValue()
        data["client_civil_status"] = self.client_civil_status.GetSelection()

        data["client_house_street"] = self.client_house_street.GetValue()
        data["client_barangay"] = self.client_barangay.GetValue()
        data["client_city"] = self.client_city.GetSelection()

        # Bene
        data["bene_relationship"] = self.bene_relationship.GetSelection()

        data["bene_lastname"] = self.bene_lastname.GetValue()
        data["bene_firstname"] = self.bene_firstname.GetValue()
        data["bene_middlename"] = self.bene_middlename.GetValue()

        data["bene_gender"] = self.bene_gender.GetSelection()

        data["bene_bday"] = get_date_value(self.bene_bday)
        data["bene_age"] = self.bene_age.GetValue()

        data["bene_contact_no"] = self.bene_contact_no.GetValue()
        data["bene_civil_status"] = self.bene_civil_status.GetSelection()

        data["bene_house_street"] = self.bene_house_street.GetValue()
        data["bene_barangay"] = self.bene_barangay.GetValue()
        data["bene_city"] = self.bene_city.GetSelection()

        data["has_beneficiary"] = self.has_beneficiary.GetValue()
        data["cb_encoded"] = self.cb_encoded.GetValue()

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

        self.command_log.AppendText(f"Data saved successfully to {csv_file}\n")

    def on_refresh(self, event):
        if self.cb_website.GetValue() or self.cb_offline.GetValue() or self.cb_mov.GetValue():

            # Attach to an existing Chrome session (Make sure Chrome is running with debugging mode)
            chrome_options = webdriver.ChromeOptions()
            chrome_options.debugger_address = "localhost:9222"  # Attach to existing Chrome session

            driver = webdriver.Chrome(options=chrome_options)  # Open Selenium with existing Chrome session

            if self.cb_mov.GetValue():
                if self.switch_to_tab(driver, mov_url):
                    self.clickAddButton(driver, "Submit another response")
                else:
                    self.command_log.AppendText("URL not found in any open tab.\n")

            if self.cb_offline.GetValue():
                if self.switch_to_tab(driver, offline_url):
                    self.clickAddButton(driver, "Submit another response")
                else:
                    self.command_log.AppendText("URL not found in any open tab.\n")

            if self.cb_website.GetValue():
                if self.switch_to_tab(driver, website_url):
                    self.clickAddButton(driver, "Home")
                else:
                    self.command_log.AppendText("URL not found in any open tab.\n")

            driver.quit()
            wx.CallAfter(self.command_log.AppendText, "Task completed!\n")

        else:
            self.command_log.AppendText("Please select a checkbox(s). \n")

    def on_fill_up(self):
        if self.stop_requested:
            self.stop_requested = False
            wx.CallAfter(self.command_log.AppendText, "Task was stopped.\n")
            wx.CallAfter(self.set_running_flag, False)  # Reset flag on completion
            return

        is_end_mov = False
        is_end_offline = False
        is_end_website = False

        if self.cb_website.GetValue() or self.cb_offline.GetValue() or self.cb_mov.GetValue():

            # Attach to an existing Chrome session (Make sure Chrome is running with debugging mode)
            chrome_options = webdriver.ChromeOptions()
            chrome_options.debugger_address = "localhost:9222"  # Attach to existing Chrome session

            self.driver = webdriver.Chrome(options=chrome_options)  # Open Selenium with existing Chrome session

            # Get all currently open tabs
            if self.cb_mov.GetValue():
                if self.switch_to_tab(self.driver, mov_url):
                    is_end_mov = self.is_end_of_g_form(self.driver)
                    if not is_end_mov :
                        self.on_fill_crims_mov(self.driver)
                else:
                    self.command_log.AppendText("URL not found in any open tab.\n")

            if self.cb_offline.GetValue():
                if self.switch_to_tab(self.driver, offline_url):
                    is_end_offline = self.is_end_of_g_form(self.driver)
                    if not is_end_offline:
                        self.on_fill_crims_offline(self.driver)
                else:
                    self.command_log.AppendText("URL not found in any open tab.\n")

            if self.cb_website.GetValue():
                if self.switch_to_tab(self.driver, website_url):
                    is_end_website = self.is_end_of_website(self.driver)
                    if not is_end_website:
                        self.on_fill_crims_website(self.driver)
                else:
                    self.command_log.AppendText("URL not found in any open tab.\n")

            self.driver.quit()
            wx.CallAfter(self.command_log.AppendText, "Task completed!\n")

        else:
            self.command_log.AppendText("Please select a checkbox(s). \n")

        if self.auto_finish.GetValue() :

            if (is_end_website == self.cb_website.GetValue()) and (is_end_mov == self.cb_mov.GetValue()) and (is_end_offline == self.cb_offline.GetValue()):

                wx.CallAfter(self.set_running_flag, False)  # Reset flag on completion
                self.stop_requested = False
                set_encoded(self.encode_id.GetValue(), True)
                self.load_data_person()
                self.select_first_item()

                """ select next record """
                """ trigger on fill up """
                # time.sleep(1)
                # self.on_fill_up()
                return
            else:
                time.sleep(1)
                self.on_fill_up()
        else:
            wx.CallAfter(self.set_running_flag, False)  # Reset flag on completion

    def switch_to_tab(self, driver, url_part):
        for handle in driver.window_handles:
            driver.switch_to.window(handle)

            if url_part in driver.current_url:  # Check if the URL contains the desired string
                # self.command_log.AppendText(f"Switched to tab: {driver.current_url}\n")
                return True
        return False

    def on_fill_crims_website(self, driver):
        try:
            if self.clickHrefButton(driver, "Add Client"):
                c_full_name = f'{self.client_lastname.GetValue()} {self.client_firstname.GetValue()} {self.client_middlename.GetValue()}'
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

            match self.getTitle(driver):
                case "family composition":
                    if self.auto_next.GetValue():
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "confirmation":
                    if self.auto_next.GetValue():
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
                        self.command_log.AppendText(f"Error: Element with File upload not found. \n")
                    except Exception as e:
                        self.command_log.AppendText(f"Element not existing {e} \n")
                        return False

                    self.setTextField(driver, "cl_pcn", "0")

                    self.setTextField(driver, "queue_no", "0")

                    self.setDropDown(driver, "select2-mode_of_admission-container", self.mode_of_admission.GetStringSelection())
                    self.setDropDown(driver, "select2-cl_assisted_through-container", "Onsite")
                    self.setDropDown(driver, "select2-cl_typeid-container", "N/A")
                    self.setDropDown(driver, "select2-cl_referring_party-container", "Default Default Default")

                    if not self.has_beneficiary.GetValue():
                        self.setDropDown(driver, "select2-is_Self-container", "Yes")
                    else:
                        self.setDropDown(driver, "select2-is_Self-container", "No")

                    self.setDropDown(driver, "select2-cl_category-container", self.target_sector.GetStringSelection())
                    self.setDropDown(driver, "select2-cl_sub_category-container", "NONE OF THE ABOVE")

                    self.setTextField(driver, "lname", self.client_lastname.GetValue())
                    self.setTextField(driver, "fname", self.client_firstname.GetValue())
                    self.setTextField(driver, "mname", self.client_middlename.GetValue())
                    client_ext_value = self.client_ext.GetValue().lower()
                    if client_ext_value != "":
                        self.setTextField(driver, "xname", self.client_ext.GetValue())

                    self.setDate(driver, "birthdate", self.client_bday.GetValue())

                    self.setDropDown(driver, "select2-sex-container", self.client_gender.GetStringSelection())

                    client_contact_value = self.client_contact_no.GetValue()
                    if client_contact_value == "" :
                        client_contact_value = "00000000000"

                    self.setTextField(driver, "contact_no", client_contact_value)

                    relationship_caption = self.client_relationship.GetStringSelection()
                    relationship_name = self.relationship_data_map[relationship_caption]

                    self.setDropDown(driver, "select2-relationship_bene-container", relationship_caption)

                    civil_status_caption = self.client_civil_status.GetStringSelection()
                    civil_status_name = self.civil_status_data_map[civil_status_caption]

                    self.setDropDown(driver, "select2-civil_status-container", civil_status_name)

                    self.setTextField(driver, "purok_street", self.client_house_street.GetValue())

                    self.setDropDown(driver, "select2-region-container", "NCR [National Capital Region]")

                    if self.client_city.GetStringSelection() == "CITY OF QUEZON CITY":
                        self.setDropDown(driver, "select2-province-container", "NCR SECOND DISTRICT")
                    else:
                        self.setDropDown(driver, "select2-province-container", "NCR THIRD DISTRICT")

                    if self.client_city.GetStringSelection() == "NONE OF THE ABOVE":
                        self.stop_requested = True
                        city_value = "NONE OF THE ABOVE"
                    elif self.client_city.GetStringSelection() == "CITY OF CALOOCAN":
                        city_value = "KALOOKAN CITY"
                    elif self.client_city.GetStringSelection() == "CITY OF QUEZON CITY":
                        city_value = "QUEZON CITY"
                    else:
                        city_value = self.client_city.GetStringSelection()
                    self.setDropDown(driver, "select2-city_muni-container", city_value)

                    self.setDropDown(driver, "select2-barangay-container", self.client_barangay.GetValue())

                    self.setDropDown(driver, "select2-occupation-container", "NONE OF THE ABOVE")

                    self.setTextField(driver, "salary", "0")

                    if self.auto_next.GetValue() :
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "beneficiary information":
                    self.setTextField(driver, "b_pcn", "0")
                    self.setDropDown(driver, "select2-b_assisted_through-container", "Onsite")
                    self.setDropDown(driver, "select2-id_type_id-container", "N/A")

                    if self.has_beneficiary.GetValue():
                        self.selectCheckBox(driver, "uniform-same_add_client")

                        self.setDropDown(driver, "select2-b_sex-container", self.bene_gender.GetStringSelection())
                        self.setDropDown(driver, "select2-b_civil_status-container",
                                         self.bene_civil_status.GetStringSelection())
                        self.setDropDown(driver, "select2-b_referring_party-container", "Default Default Default")

                        self.setDate(driver, "b_birthdate", self.bene_bday.GetValue())

                        self.setTextField(driver, "b_lname", self.bene_lastname.GetValue())
                        self.setTextField(driver, "b_fname", self.bene_firstname.GetValue())
                        self.setTextField(driver, "b_mname", self.bene_middlename.GetValue())
                        self.setTextField(driver, "b_xname", self.bene_ext.GetValue())

                        self.setDropDown(driver, "select2-b_region-container", "NCR [National Capital Region]")

                        self.setDropDown(driver, "select2-b_province-container", "NCR THIRD DISTRICT")

                        if self.client_city.GetStringSelection() == "NONE OF THE ABOVE":
                            self.stop_requested = True
                            city_value = "NONE OF THE ABOVE"
                        elif self.bene_city.GetStringSelection() == "CITY OF CALOOCAN":
                            city_value = "KALOOKAN CITY"
                        else:
                            city_value = self.client_city.GetStringSelection()
                        self.setDropDown(driver, "select2-b_city_muni-container", city_value)

                        self.setDropDown(driver, "select2-b_barangay-container", self.bene_barangay.GetValue())

                        self.setTextField(driver, "b_purok_street", self.bene_house_street.GetValue())
                        self.setTextField(driver, "b_contact_no", self.bene_contact_no.GetValue())
                    else:
                        self.selectCheckBox(driver, "uniform-is_existing_self")
                        self.setDropDown(driver, "select2-b_referring_party-container", "Default Default Default")

                    if self.auto_next.GetValue():
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "assessment":
                    self.setDropDown(driver, "select2-bene_category-container", self.target_sector.GetStringSelection())
                    self.setDropDown(driver, "select2-bene_sub_category-container", "NONE OF THE ABOVE")

                    value_string = ""
                    if self.client_gender.GetStringSelection().lower() == "male":
                        gender_string = "HIS"
                    else:
                        gender_string = "HER"
                    match self.financial_assist.GetStringSelection().lower():
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
                    if self.auto_next.GetValue() :
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
                case "recommended services and assistance":
                    if self.selectDefaultCheckBox(driver, "uniform-financial_assistance"):
                        self.clickButton(driver, "add_famCompo")

                    assistance_value = ""
                    purpose_value = ""
                    match self.financial_assist.GetStringSelection().lower():
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
                    self.setDropDown(driver, "select2-FA2mode_of_asssitance}-container", "Cash")

                    fund_source_caption = self.fund_source.GetStringSelection()

                    self.setDropDown(driver, "select2-FA2fund_source-container", fund_source_caption)

                    self.setTextField(driver, "FA[2][purpose]", purpose_value)
                    self.setTextField(driver, "FA[2][amount_of_assistance]", self.amount.GetValue())

                    try:
                        driver.implicitly_wait(10)
                        # Switch to the alert (pop-up)
                        alert = Alert(driver)

                        # Accept the alert (click "OK")
                        alert.accept()
                        print("Alert accepted!")

                    except:
                        print("No alert present")

                    if self.auto_next.GetValue() :
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
                    if self.thru_firstname.GetValue():
                        if self.sw_mname.GetValue() == "" :
                            sw_full_name = f'{self.sw_fname.GetValue()} {self.sw_lname.GetValue()}'
                        else:
                            sw_full_name = f'{self.sw_fname.GetValue()} {self.sw_mname.GetValue()} {self.sw_lname.GetValue()}'
                    else:
                        sw_full_name = f'{self.sw_lname.GetValue()} {self.sw_fname.GetValue()} {self.sw_mname.GetValue()}'
                    self.setDropDown(driver, "select2-assessed_by-container", sw_full_name)

                    self.setDropDown(driver, "select2-approved_by-container", "MARICEL M BARNEDO") #ANTHONY LISONDRA ALCANTARA
                    self.setDropDown(driver, "select2-status-container", "Approved")
                    self.setDate(driver, "dt_assistanceProvided", self.interview_date.GetValue())
                    if self.auto_submit.GetValue():
                        self.clickNextButton(driver, "Next")
                        return None
                    return None
            return None
        except Exception as e:
            self.command_log.AppendText(f"Error in : {e} \n")
            return None

    def on_fill_crims_offline(self, driver):
        region = "NCR [National Capital Region]"
        if self.client_city.GetStringSelection() == "CITY OF QUEZON CITY":
            province = "NCR SECOND DISTRICT"
        else:
            province = "NCR THIRD DISTRICT"
        gformTitle = self.getGFormTitle(driver)
        if gformTitle == "approved by":
            self.setGFormRadioButton(driver, "", "Maricel M. Barnedo") #
            self.setGFormRadioButton(driver, "REGION ASSESS", "NCR (National Capital Region)")
            self.setGFormRadioButton(driver, "PAYEE", "N/A")

            client_contact_value = self.client_contact_no.GetValue()
            if client_contact_value == "":
                self.setGFormRadioButton(driver, "CLIENT CONTACT NUMBER", "N/A")
            else:
                self.setGFormRadioButtonOthers(driver, "CLIENT CONTACT NUMBER", client_contact_value)

            bene_contact_value = self.has_beneficiary.GetValue()
            if bene_contact_value == "":
                self.setGFormRadioButtonOthers(driver, "BENEFICIARY CONTACT NUMBER", bene_contact_value)
            else:
                self.setGFormRadioButton(driver, "BENEFICIARY CONTACT NUMBER", "N/A")

            self.setGFormRadioButton(driver, "STATUS", "APPROVED")

            if self.auto_submit.GetValue():
                self.clickSubmitButton(driver, "Submit")
        elif gformTitle == "beneficiary":
            if not self.has_beneficiary.GetValue():
                self.selectAllItemFirstOption(driver)
                date_str = "N/A"
            else:
                date_str = self.bene_bday.GetValue().Format("%m-%d-%Y")
                self.setGFormRadioButtonOthers(driver, "LASTNAME", self.bene_lastname.GetValue())
                self.setGFormRadioButtonOthers(driver, "FIRST NAME", self.bene_firstname.GetValue())
                self.setGFormRadioButtonOthers(driver, "MIDDLE NAME", self.bene_middlename.GetValue())
                self.setGFormRadioButton(driver, "EXTENSION NAME", "N/A")

                # date_str = self.bene_bday.GetValue().Format("%m-%d-%Y")
                # self.setGFormRadioButtonOthers(driver, "BIRTHDAY", date_str)
                self.setGFormRadioButtonOthers(driver, "AGE", self.bene_age.GetValue())
                self.setGFormRadioButton(driver, "BENEFICIARY CATEGORY", "N/A")
                self.setGFormRadioButton(driver, "SEX", self.bene_gender.GetStringSelection())
                self.setGFormRadioButton(driver, "CIVIL STATUS", self.bene_civil_status.GetStringSelection())

                self.setGFormDate(driver, "i50", self.bene_bday.GetValue())

            self.setGFormTextField(driver, "i46 i47", date_str)

            self.setGFormRadioButton(driver, "MODE OF RELEASE", "CASH")
            self.setGFormRadioButton(driver, "DATE OF RELEASE", "2025")
            # i150 - INTERVIEW
            # i156 - DATE OF RELEASE
            self.setGFormDate(driver, "i150", self.interview_date.GetValue())
            self.setGFormDate(driver, "i156", self.interview_date.GetValue())
            # self.setGFormDate(driver, "i149", self.interview_date.GetValue())

            sw_lname_value = string.capwords(self.sw_lname.GetValue())
            sw_fname_value = string.capwords(self.sw_fname.GetValue())
            sw_mname_value = string.capwords(self.sw_mname.GetValue())
            sw_mname_initial_value = sw_mname_value[0].upper() if sw_mname_value else ""
            sw_full_name = f'{sw_lname_value}, {sw_fname_value} {sw_mname_initial_value}.'
            self.setGFormDropDown(driver, "i157 i160", sw_full_name)

            if self.auto_next.GetValue():
                self.clickGFormButton(driver, "Next")
        elif gformTitle == "barangay and district":
            self.setGFormTextField(driver, "i2 i3", self.client_barangay.GetValue())
            self.setGFormDropDown(driver, "i6 i9", "I")

            self.setGFormTextField(driver, "i22 i23", self.client_lastname.GetValue())
            self.setGFormTextField(driver, "i12 i13", self.client_firstname.GetValue())
            self.setGFormTextField(driver, "i17 i18", self.client_middlename.GetValue())

            client_ext_value = self.client_ext.GetValue().lower()
            if client_ext_value != "":
                if client_ext_value.lower() in ["jr", "sr"] and not client_ext_value.endswith("."):
                    client_ext_value = client_ext_value + "."
            else:
                client_ext_value = "N/A"
            self.setGFormDropDown(driver, "i26 i29", client_ext_value.lower())  # extension name

            self.setGFormDropDown(driver, "i31 i34", self.client_gender.GetStringSelection().upper())  # sex

            civil_status_caption = self.client_civil_status.GetStringSelection()
            civil_status_name = self.civil_status_data_map[civil_status_caption]

            self.setGFormRadioButton(driver, "CIVIL STATUS", civil_status_caption)

            self.setGFormDate(driver, "i61", self.client_bday.GetValue())
            self.setGFormTextField(driver, "i63 i64", self.client_age.GetValue())

            self.setGFormRadioButton(driver, "MODE OF ADMISSION", "WALK-IN")

            self.setGFormTextField(driver, "i96 i97", self.amount.GetValue())

            fund_source_caption = self.fund_source.GetStringSelection()
            fund_source_name = self.fund_source_data_map[fund_source_caption]

            self.setGFormRadioButton(driver, "FUND SOURCE", fund_source_name)

            sector_value = self.target_sector.GetStringSelection()
            if sector_value.lower() == "senior citizens" :
                sector_value = "senior citizens (no subcategories)"
            #     SENIOR CITIZENS (no subcategories)
            self.setGFormRadioButton(driver, "CLIENT CATEGORY", sector_value)

            self.setGFormRadioButton(driver, "CLIENT SUB-CATEGORY", "Indigenous People")
            # "Medical", "Burial", "Transportation", "Cash Support", "Food Subsidy"
            match self.financial_assist.GetStringSelection().lower():
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

            relationship_caption = self.client_relationship.GetStringSelection()
            relationship_name = self.relationship_data_map[relationship_caption]

            # if self.client_relationship.GetStringSelection() == "Not Specified":
            #     client_relationship_value = "SELF"
            # else:
            #     client_relationship_value = self.client_relationship.GetStringSelection()
            self.setGFormRadioButton(driver, "RELATIONSHIP TO BENEFICIARY", relationship_name)
            if self.auto_next.GetValue():
                self.clickGFormButton(driver, "Next")
        elif is_similar(gformTitle, province.lower()):
            if self.client_city.GetStringSelection() == "NONE OF THE ABOVE":
                self.stop_requested = True
            else:
                self.setGFormDropDown(driver, "i1 i4", self.client_city.GetStringSelection())
                if self.auto_next.GetValue():
                    self.clickGFormButton(driver, "Next")
        elif is_similar(gformTitle, region.lower()):
            self.setGFormDropDown(driver, "i1 i4", province)
            if self.auto_next.GetValue():
                self.clickGFormButton(driver, "Next")
        else:
            self.setGFormDate(driver, "i6", self.encoded_date.GetValue())
            self.setGFormTextField(driver, "i8 i9", self.encoder_name.GetValue())

            self.selectSingleItemFirstOption(driver)
            self.setGFormDropDown(driver, "i28 i31", region)
            if self.auto_next.GetValue():
                self.clickGFormButton(driver, "Next")

    def on_fill_crims_mov(self, driver):
        self.setGFormTextField(driver, "i2 i3", self.encoder_name.GetValue())

        c_full_name = f'{self.client_firstname.GetValue()} {self.client_middlename.GetValue()} {self.client_lastname.GetValue()}'
        self.setGFormTextField(driver, "i7 i8", c_full_name)

        if self.has_beneficiary.GetValue():
            b_full_name = f'{self.bene_firstname.GetValue()} {self.bene_middlename.GetValue()} {self.bene_lastname.GetValue()}'
            self.setGFormTextField(driver, "i12 i13", b_full_name)
        else:
            self.setGFormTextField(driver, "i12 i13", c_full_name)

        self.setGFormTextField(driver, "i34 i35", self.amount.GetValue())

        sw_full_name = f'{self.sw_fname.GetValue()} {self.sw_mname.GetValue()} {self.sw_lname.GetValue()}'
        self.setGFormTextField(driver, "i39 i40", sw_full_name)

        self.setGFormAssistance(driver)

        if self.auto_submit.GetValue():
            self.clickSubmitButton(driver, "Submit")

    def getGFormTitle(self, driver):
        try:
            # Locate the heading div with role='heading'
            heading = driver.find_element(By.XPATH, "//div[@role='heading']//div[contains(@class, 'aG9Vid')]")
            # Get the text
            content = heading.text.strip()
            self.command_log.AppendText(f"Title: {content}. \n")
            return content.lower()
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return ""
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return ""

    def setGFormTextField(self, driver, pk_id, value):
        try:
            text_field = driver.find_element(By.XPATH, f'//input[@aria-describedby="{pk_id}"]')

            if text_field and text_field.get_attribute("value") == "":
                text_field.send_keys(value)
            else:
                self.command_log.AppendText("Text field is already filled. \n")
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
        except Exception as e:
            self.command_log.AppendText(f"Unexpected error: {e} \n")

    def setGFormDate(self, driver, pk_id, value):
        try:
            date_field = driver.find_element(By.XPATH, f'//input[@aria-labelledby="{pk_id}"]')

            if date_field:
                date_str = value.Format("%m-%d-%Y")
            date_field.clear()
            date_field.send_keys(date_str)
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
        except Exception as e:
            self.command_log.AppendText(f"Unexpected error: {e} \n")

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
                            # if option_text.lower() and option_text.strip().lower() == value.lower(): # Match text exactly
                            if is_similar(option_text.lower() and option_text.strip().lower(), value.lower()):
                                option.click()
                                time.sleep(0.5)
                                self.command_log.AppendText(f"Selected: {option_text}\n")
                                break  # Stop once we find and click the right option
                continue
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element entered not found.\n")
        except Exception as e:
            self.command_log.AppendText(f"Unexpected error: {e} \n")

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

                                self.command_log.AppendText(f"Selected: {option_text}, Entered: {value}\n")
                                break  # Stop after finding the first "Other" option
                            except NoSuchElementException:
                                self.command_log.AppendText("Error: No text field found for 'Other' option.\n")
                                break  # Stop after finding and selecting "Other:"
                    continue  # Move to the next radio group if needed
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element entered not found.\n")
        except Exception as e:
            self.command_log.AppendText(f"Unexpected error: {e} \n")

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
                    self.command_log.AppendText("Field :" + group.accessible_name + " = " + radio_options[0].accessible_name + "\n")
                    time.sleep(0.5)  # Small delay to avoid issues

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
                    self.command_log.AppendText("Field :" + group.accessible_name + " = " + radio_options[0].accessible_name + " \n")
                    time.sleep(0.5)  # Small delay to avoid issues
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Dropdown element not found. \n")
            return False
        except Exception as e:
            # self.command_log.AppendText(f"Unexpected error: {e} \n")
            return False

    def setGFormDropDown(self, driver, pk_id, value):
        try:

            # Locate the dropdown field (adjust XPath based on your form structure)
            dropdown = driver.find_element(By.XPATH, f"//div[@role='listbox' and @aria-labelledby='{pk_id}']")
            # f"//span[@role='combobox' and @aria-labelledby='{name}']"
            if dropdown:
                # Click to open the dropdown
                dropdown.click()
                time.sleep(0.5)

                options = driver.find_elements(By.XPATH, "//div[@role='option']")

                selected_option = None
                for option in options:
                    name_text = option.get_attribute("data-value").strip().lower()
                    # # if all(part in name_text for part in user_input_interviewer.split()):
                    if is_similar(name_text, value):
                        selected_option = option
                        break

                # Select the matched option if found
                if selected_option:
                    selected_option.click()
                    time.sleep(0.5)
                    self.command_log.AppendText(f"Selected: {selected_option.get_attribute('data-value')}")
            else:
                self.command_log.AppendText("No matching name found! \n")
                return True
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Dropdown element not found. \n")
            return False
        except Exception as e:
            # self.command_log.AppendText(f"Unexpected error: {e} \n")
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
                    match self.financial_assist.GetStringSelection().lower():
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
                            self.command_log.AppendText("Field :" + group.accessible_name + " = " + radio_options[1].accessible_name + " \n")
                    continue

    def clickGFormButton(self, driver, value):
        try:
            button = driver.find_element(By.XPATH, f"//span[contains(text(), '{value}')]")

            if button is not None:
                button.click()
                self.command_log.AppendText(f"Button click: {value} \n")
            return True
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return False
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return False

    def setDate(self, driver, name, value):
        try:
            # Convert to string format YYYY-MM-DD
            date_str = value.Format("%m-%d-%Y")
            # Locate the date input field by ID
            date_field = driver.find_element(By.ID, name)  # Replace with actual ID

            # Set the date (YYYY-MM-DD format)
            date_field.send_keys(date_str)
            self.command_log.AppendText(f"Date {name}: {value} \n")
        except Exception as e:
            self.command_log.AppendText(f"Error in Date {e} \n")

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
            self.command_log.AppendText(f"Error: Element with {name} not found. \n")
        except Exception as e:
            self.command_log.AppendText(f"Element not existing {e} \n")
            return False

    def selectCheckBox(self, driver, name):
        try:
            div_element = driver.find_element(By.ID, name)

            if div_element is not None:
                div_element.click()
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element with {name} not found. \n")
        except Exception as e:
            self.command_log.AppendText(f"Element not existing {e} \n")

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
            self.command_log.AppendText(f"Error: Element with {name} not found. \n")
        except Exception as e:
            self.command_log.AppendText(f"Element not existing {e} \n")
            return False

    def clickButton(self, driver, name):
        try:
            div_element = driver.find_element(By.ID, name)

            if div_element is not None:
                div_element.click()
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element with {name} not found. \n")
        except Exception as e:
            self.command_log.AppendText(f"Element not existing {e} \n")

    def setDropDown(self, driver, name, value):
        try:
            element = driver.find_element("id", name)

            # Check if the 'title' attribute exists and is not empty
            title_value = element.get_attribute("title")

            if title_value:
                self.command_log.AppendText(f"Field {name}: already selected \n")
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
                self.command_log.AppendText(f"Field {name}: {value} \n")
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element with {name} not found. \n")
        except Exception as e:
            # self.command_log.AppendText(f"Error in Element {e} \n")
            return

    def setTextField(self, driver, name, value):
        try:

            # Find the input field by ID and fill it
            input_field = driver.find_element(By.ID, name)

            # Check if the field already contains the desired value
            current_text = input_field.get_attribute("value").strip()
            if current_text == value:
                self.command_log.AppendText(f"Field {name} already contains the desired value. Skipping...\n")
                return

            input_field.send_keys(value)
            self.command_log.AppendText(f"Field {name}: {value} \n")
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element with {name} not found. \n")
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")

    def setTextAreaField(self, driver, name, value):
        try:

            # Find the input field by ID and fill it
            username_field = driver.find_element(By.NAME, name)
            username_field.send_keys(value)
            self.command_log.AppendText(f"Field {name}: {value} \n")
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element with {name} not found. \n")
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")

    def getTitle(self, driver):
        try:
            visible_fieldset = driver.find_element(By.XPATH, "//fieldset[contains(@style, 'display: block;')]")

            element = visible_fieldset.find_element(By.XPATH, ".//h6[contains(@class, 'form-wizard-title')]")
            # clients_info_text = element.text.strip().replace(element.find_element(By.TAG_NAME, "span").text, "").strip().lower()
            #
            # Get full text and remove the <span> and <small> parts
            full_text = element.text.strip()

            # Remove the <span> part (number count)
            span_text = element.find_element(By.TAG_NAME, "span").text.strip()
            full_text = full_text.replace(span_text, "").strip()

            # Remove the <small> part if present
            small_tags = element.find_elements(By.TAG_NAME, "small")
            if small_tags:
                full_text = full_text.replace(small_tags[0].text.strip(), "").strip()
            self.command_log.AppendText(f"Extracted Text: {full_text.lower()} \n")
            return full_text.lower()
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")

    def hasASearchField(self, driver, value):
        try:

            # Locate the search input field using placeholder
            search_input = driver.find_element(By.XPATH, "//input[@placeholder='Search']")

            # Type the search query
            search_input.send_keys(value)
            self.command_log.AppendText(f"Search Text: {value} \n")
            time.sleep(1)
            return True
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return False
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return False

    def clickHrefButton(self, driver, value):
        try:
            add_client_button = driver.find_element(By.XPATH, f"//a[contains(text(), '{value}')]")

            self.command_log.AppendText(f"Button click: {value} \n")
            return True
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return False
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return False

    def clickAddButton(self, driver, value):
        try:
            add_client_button = driver.find_element(By.XPATH, f"//a[contains(text(), '{value}')]")
            add_client_button.click()
            self.command_log.AppendText(f"Button click: {value} \n")
            return True
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return False
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return False

    def clickIconButton(self, driver):
        try:
            icon = driver.find_element(By.CLASS_NAME, "glyphicon-share-alt")

            # Perform the click action
            icon.click()
            return True
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return False
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return False

    def searchResult(self, driver):
        try:
            icon = driver.find_element(By.CLASS_NAME, "no-results")
            return True
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return False
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return False

    def clickNextButton(self, driver, value):
        try:
            next_button = driver.find_element(By.XPATH, f"//button[normalize-space(text())='{value}']")
            if next_button is not None:
                next_button.click()
            self.command_log.AppendText(f"Button click: {value} \n")
            return True
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return False
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return False

    def clickSubmitButton(self, driver, value):
        try:
            # Find the element by XPath (using aria-label or text)
            # //div[@role='heading']//div[contains(@class, 'aG9Vid')]
            element = driver.find_element(By.XPATH, f"//div[@role='button' and @aria-label='{value}']")
            if element is not None:
                element.click()
            self.command_log.AppendText(f"Button click: {value} \n")
            return True
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return False
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return False

    def is_end_of_website(self, driver):
        try:
            website_finished = driver.find_element(By.XPATH, "//h3[@class='panel-title' and contains(text(), 'Social Worker Assessment List')]")
            if website_finished is not None:
                return True
            return False
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return False
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return False

    def is_end_of_g_form(self, driver):
        try:
            element = driver.find_element(By.XPATH, "//div[@class='vHW8K' and text()='Your response has been recorded.']")
            if element is not None:
                return True
            return False
        except NoSuchElementException:
            self.command_log.AppendText(f"Error: Element not found. \n")
            return False
        except Exception as e:
            self.command_log.AppendText(f"Error in Element {e} \n")
            return False

    def proceed_to_new(self, driver):
        self.clickHrefButton(driver, "Home")

    def same_address_event(self, event):
        checkbox = event.GetEventObject()
        is_checked = checkbox.GetValue()
        if is_checked:
            self.bene_house_street.SetValue(self.client_house_street.GetValue())
            self.bene_barangay.SetValue(self.client_barangay.GetValue())
            self.bene_city.SetSelection(self.client_city.GetSelection())
        else :
            self.bene_house_street.SetValue("")
            self.bene_barangay.SetValue("")
            self.bene_city.SetSelection(-1)

    def same_contact_event(self, event):
        checkbox = event.GetEventObject()
        is_checked = checkbox.GetValue()
        if is_checked:
            self.bene_contact_no.SetValue(self.client_contact_no.GetValue())

    def has_beneficiary_event(self, event):
        checkbox = event.GetEventObject()
        is_checked = checkbox.GetValue()
        if not is_checked:
            self.bene_lastname.SetValue("")
            self.bene_firstname.SetValue("")
            self.bene_middlename.SetValue("")

            self.bene_age.SetValue("")
            self.bene_ext.SetValue("")
            self.bene_relationship.SetSelection(-1)
            self.bene_gender.SetSelection(-1)
            self.bene_civil_status.SetSelection(-1)

            self.bene_contact_no.SetValue("")

            self.bene_house_street.SetValue("")
            self.bene_barangay.SetValue("")
            self.bene_city.SetSelection(-1)
        else:
            self.bene_relationship.SetSelection(self.client_relationship.GetSelection())


    def on_checkbox_change(self, event):
        checkbox = event.GetEventObject()
        is_checked = checkbox.GetValue()
        self.load_data_person()

    def on_selection(self, event):
        name = self.client_civil_status.GetStringSelection()
        caption = self.civil_status_data_map[name]
        print(f"Selected Caption: {caption} Name : {name}\n ")

    def on_selection_worker(self, event):
        selected = self.social_worker.GetStringSelection()
        name_parts = selected.split(",")

        fname = name_parts[0]
        mname = name_parts[1]
        lname = name_parts[2]

        data_worker = get_worker_id(lname.strip(), fname.strip(), mname.strip())
        if data_worker:
            # data = self.get_worker_by_id(data_id[0])

            self.sw_lname.SetValue(data_worker[1])
            self.sw_fname.SetValue(data_worker[2])
            self.sw_mname.SetValue(data_worker[3])
            self.thru_firstname.SetValue(data_worker[4])

            print(f"Selected Caption: {selected} : {data_worker} ")

    def reload_choice_items(self):
        """Reload the Choice items from the database."""
        self.social_worker_list = get_all_workers()

        # Clear old items
        self.social_worker.Clear()

        # Create and insert new display names
        self.social_worker_choices = [f"{fname}, {mname}, {lname}" for (_id, lname, fname, mname, _thru) in self.social_worker_list]

        for name in self.social_worker_choices:
            self.social_worker.Append(name)

    def on_sw_text_change(self, event):
        """Handle text typing in ComboBox to auto-select matching item."""
        typed_text = self.social_worker_filter.GetValue().lower().strip()

        for index, name in enumerate(self.social_worker_choices):
            if name.lower().startswith(typed_text):
                self.social_worker.SetSelection(index)
                self.on_selection_worker(event)
                # self.social_worker.SetValue(name)
                # Move cursor to end so user can continue typing
                # self.social_worker.SetInsertionPointEnd()
                break

    def on_export(self, event):
        """
        Handles the export button click.
        Shows a loading indicator while exporting.
        """
        self.busy_info = wx.BusyInfo("Exporting, please wait...", parent=self)
        wx.Yield()  # Allow the busy info to display immediately

        def export_task():
            try:
                export_sqlite_to_csv(
                    db_path=DB_NAME,
                    table_name="person",
                    csv_path="person-backup-db.csv"
                )
                wx.CallAfter(wx.MessageBox, "Export completed successfully!", "Success", wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.CallAfter(wx.MessageBox, f"Error: {e}", "Error", wx.OK | wx.ICON_ERROR)
            finally:
                wx.CallAfter(self.clear_busy_info)

        # Run export in a separate thread
        threading.Thread(target=export_task).start()

    def clear_busy_info(self):
        """Safely clear the busy indicator."""
        if self.busy_info:
            self.busy_info = None  # When BusyInfo object is deleted, it closes the message automatically


# === wxPython UI ===
class ActivationFrame(wx.Frame):
    def __init__(self, parent, app, title="Activate App"):
        super().__init__(parent, title=title, size=(480, 230))
        self.app = app  # <-- store reference to MainApp

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Info Text
        info_device = wx.StaticText(panel, label="Device Id:")
        vbox.Add(info_device, flag=wx.ALL, border=10)

        self.label_text = get_device_id()
        label = wx.StaticText(panel, label=self.label_text)
        font = label.GetFont()
        font.MakeBold()
        label.SetFont(font)

        # Change cursor to indicate clickable
        label.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        # Bind mouse click event
        label.Bind(wx.EVT_LEFT_DOWN, self.copy_to_clipboard)
        vbox.Add(label, flag=wx.ALL, border=10)

        # Info Text
        info_text = wx.StaticText(panel, label="License key:")
        vbox.Add(info_text, flag=wx.ALL, border=10)

        # Key input field
        self.key_input = wx.TextCtrl(panel)
        vbox.Add(self.key_input, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        # Activate button
        activate_btn = wx.Button(panel, label="Activate")
        activate_btn.Bind(wx.EVT_BUTTON, self.on_activate)
        vbox.Add(activate_btn, flag=wx.ALL | wx.CENTER, border=15)

        # Status label
        self.status_label = wx.StaticText(panel, label="")
        vbox.Add(self.status_label, flag=wx.ALL | wx.CENTER, border=10)

        panel.SetSizer(vbox)

        self.Centre()
        self.Show()

    def copy_to_clipboard(self, event):
        """Copies label text to the system clipboard."""
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.label_text))
            wx.TheClipboard.Close()
            wx.MessageBox("Copied to clipboard!", "Success", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox("Unable to access clipboard.", "Error", wx.OK | wx.ICON_ERROR)

    def on_activate(self, event):
        """
        Handles activation button click.
        """
        user_key = self.key_input.GetValue().strip()
        if not user_key:
            wx.MessageBox("Please enter a key.", "Error", wx.OK | wx.ICON_ERROR)
            return

        if activate_trial(user_key):
            wx.MessageBox("Activation successful!", "Success", wx.OK | wx.ICON_INFORMATION)
            self.status_label.SetLabel("Activated ✔️")
            self.key_input.Disable()

            # --- OPEN MAIN APP ---
            self.Destroy()  # Close Activation Window
            self.app.open_main_app()
        else:
            wx.MessageBox("Invalid key.", "Error", wx.OK | wx.ICON_ERROR)
            self.status_label.SetLabel("Activation failed ❌")

class MainApp(wx.App):
    def OnInit(self):
        if is_trial_valid():
            self.open_main_app()
        else:
            self.frame = ActivationFrame(None, self)
        return True

    def open_main_app(self):
        """Opens the main application window."""
        init_db()
        self.main_frame = MyFrame()
        self.main_frame.Show()

class MainAppFrame(wx.Frame):
    """Main Application Window (after activation)."""
    def __init__(self, parent):
        # You can continue to the main app here (e.g., open main window)
        init_db()
        app = wx.App(False)
        frame = MyFrame()
        frame.Show()

if __name__ == "__main__":
    app = MainApp(False)
    app.MainLoop()
    # init_db()
    # app = wx.App(False)
    # frame = MyFrame()
    # frame.Show()
    # app.MainLoop()