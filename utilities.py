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
    """Get the selected date from QDateEdit as a string (YYYY-MM-dd)."""
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
