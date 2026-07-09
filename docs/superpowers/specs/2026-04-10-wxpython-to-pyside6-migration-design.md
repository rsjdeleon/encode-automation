# wxPython → PySide6 Migration Design

**Date:** 2026-04-10  
**File:** `assistance-form-new.py`  
**Reason:** wxPython 4.2.2 has no Python 3.14+ support. PySide6 supports Python 3.14 and provides equivalent widgets.

---

## Scope

Only `assistance-form-new.py` is modified. All other files remain unchanged:
- `db_new_person.py` — SQLite person database
- `db_worker.py` — SQLite worker database
- `config.py` — dropdown lists and URLs
- `utilities.py` — helper functions
- `license.py` — license/trial validation

---

## Architecture

1-to-1 widget replacement. No changes to app logic, database layer, Selenium automation, or config. The `MyFrame` class becomes a `QMainWindow` subclass. Layout is preserved: scrollable form area on top, data table below, CRUD buttons at bottom.

---

## Widget Mapping

| wxPython | PySide6 |
|---|---|
| `wx.Frame` | `QMainWindow` |
| `wx.Panel` | `QWidget` |
| `wx.Notebook` | `QTabWidget` |
| `wx.ScrolledWindow` | `QScrollArea` |
| `wx.TextCtrl` | `QLineEdit` |
| `wx.Choice` / `wx.ComboBox` | `QComboBox` |
| `wx.CheckBox` | `QCheckBox` |
| `wx.Button` | `QPushButton` |
| `wx.ListCtrl` (multi-column, colored rows) | `QTableWidget` |
| `wx.adv.DatePickerCtrl` | `QDateEdit` with `calendarPopup=True` |
| `wx.StaticText` | `QLabel` |
| `wx.BoxSizer(wx.HORIZONTAL)` | `QHBoxLayout` |
| `wx.BoxSizer(wx.VERTICAL)` | `QVBoxLayout` |
| `wx.MessageDialog` | `QMessageBox` |
| `wx.CallAfter(fn)` | `QTimer.singleShot(0, fn)` |
| `wx.StaticLine` | `QFrame` with `HLine` shape |

---

## Key Behavioral Details

### AllCaps Input
`AllCapsTextCtrl` becomes a `QLineEdit` subclass that connects `textChanged` to a slot forcing uppercase via `setText()` while preserving cursor position using `blockSignals(True)`.

### Colored List Rows
`QTableWidget` supports per-cell and per-row colors via `QTableWidgetItem.setBackground(QColor(...))` and `setForeground(QColor(...))`. Row coloring logic (SW-based pastel colors + red for mode_release==1 + blue text for has_beneficiary==1) is preserved.

### Date Pickers
`QDateEdit(calendarPopup=True)` matches `wx.adv.DP_DROPDOWN`. Dates are read with `.date().toString("yyyy-MM-dd")` and set with `QDate.fromString(value, "yyyy-MM-dd")`.

### Disable Mousewheel on Dropdowns
Each `QComboBox` that needs mousewheel disabled gets a subclass override of `wheelEvent` that calls `event.ignore()`. A helper `make_no_scroll_combo()` factory returns this subclass instance.

### Keyboard Hotkey
`keyboard.add_hotkey('shift+enter', self.on_add_person)` is unchanged — the `keyboard` library is Python-native and framework-agnostic.

### Deferred UI Calls
`wx.CallAfter(fn)` → `QTimer.singleShot(0, fn)` for any post-event UI updates.

### Threading
Background Selenium thread calls `wx.CallAfter` → replaced with a custom `QObject` signal emitted from the thread, connected to UI slots on the main thread.

### `winsound`
Unchanged — Windows-native, not related to wxPython.

---

## File Changes

| File | Change |
|---|---|
| `assistance-form-new.py` | Full rewrite of GUI layer using PySide6 |
| `requirements.txt` | Replace `wxPython==4.2.2` with `PySide6` |
| `utilities.py` | Review `disable_mousewheel`, `set_date_value`, `get_date_value` — update signatures for PySide6 widget types |

---

## Out of Scope

- No visual redesign
- No changes to database schema
- No changes to Selenium automation logic
- No changes to config, license, or other supporting files
