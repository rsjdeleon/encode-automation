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
