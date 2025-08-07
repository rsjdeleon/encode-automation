import wx
import os
import signal

from difflib import SequenceMatcher

def is_similar(text1, text2, threshold=0.9):
    return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio() >= threshold

def disable_mousewheel(widget):
    widget.Bind(wx.EVT_MOUSEWHEEL, lambda event: None)

def stop_selenium(self):
    if self.driver:
        os.kill(self.driver.service.process.pid, signal.SIGTERM)

    self.command_log.AppendText("Selenium WebDriver stopped.\n")

def get_date_value(date_picker):
    """Get the selected date from DatePickerCtrl as a string (YYYY-MM-DD)."""
    return date_picker.GetValue().FormatISODate()

def set_date_value(date_picker, date_str):
    """Set DatePickerCtrl to a given date string (YYYY-MM-DD)."""

    date_obj = wx.DateTime()
    date_obj.ParseDate(date_str)

    if date_obj.IsValid():
        date_picker.SetValue(date_obj)
        return True
    return False