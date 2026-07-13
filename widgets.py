from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QLineEdit, QComboBox, QCompleter


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
    """QComboBox that ignores mousewheel scroll to prevent accidental selection changes.
    When editable, also opens the dropdown on a click anywhere in the field (not just
    the arrow button), since Qt's default editable-combobox behavior only opens the
    popup via the arrow, making it feel like a plain textfield otherwise. Also
    configures live search-as-you-type filtering: by default Qt's auto-attached
    completer for an editable combobox only does inline prefix completion (ghost
    text), not a filtered dropdown list — useless for long lists (e.g. a city with
    100+ barangays) where you can't see what else matches. PopupCompletion +
    MatchContains shows a filtered popup of every option containing the typed
    text, updated as you type."""

    def wheelEvent(self, event):
        event.ignore()

    def setEditable(self, editable):
        super().setEditable(editable)
        if editable and self.lineEdit() is not None:
            self.lineEdit().installEventFilter(self)
            completer = self.completer()
            if completer is not None:
                completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
                completer.setFilterMode(Qt.MatchFlag.MatchContains)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def eventFilter(self, obj, event):
        if obj is self.lineEdit() and event.type() == QEvent.Type.MouseButtonPress:
            self.showPopup()
        return super().eventFilter(obj, event)


def set_table_visible_rows(table, rows):
    """Cap a QTableWidget's height so only `rows` records show before it scrolls."""
    row_height = table.verticalHeader().defaultSectionSize()
    header_height = table.horizontalHeader().sizeHint().height()
    frame = table.frameWidth() * 2
    table.setFixedHeight(header_height + row_height * rows + frame)


def set_textedit_visible_rows(text_edit, rows):
    """Cap a QTextEdit's height so only `rows` lines of text show before it scrolls."""
    line_height = text_edit.fontMetrics().lineSpacing()
    frame = text_edit.frameWidth() * 2
    doc_margin = text_edit.document().documentMargin() * 2
    text_edit.setFixedHeight(line_height * rows + frame + doc_margin)
