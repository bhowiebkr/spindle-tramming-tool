from __future__ import annotations

from typing import Any
from typing import List
from typing import Optional

from PySide6.QtCore import QRegularExpression
from PySide6.QtCore import Qt
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtGui import QFont
from PySide6.QtGui import QKeyEvent
from PySide6.QtGui import QPainter
from PySide6.QtGui import QPaintEvent
from PySide6.QtGui import QPen
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QLineEdit
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget


class FloatLineEdit(QLineEdit):  # type: ignore
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # Set up a regular expression for floating point numbers
        float_regex = QRegularExpression(
            r"^-?\d*\.?\d*$"
        )  # Regex to match float numbers
        self.validator = QRegularExpressionValidator(float_regex, self)
        self.setValidator(self.validator)

        # Connect textChanged signal to validate input
        self.textChanged.connect(self.validate_text)

    def validate_text(self) -> None:
        """Validate the current text to ensure it's a valid float"""
        text = self.text()
        if text:
            try:
                # Try to convert the text to float
                float(text)
                self.setStyleSheet("")  # Clear any error styling
            except ValueError:
                # Invalid float; apply error styling
                self.setStyleSheet("border: 1px solid red;")
        else:
            self.setStyleSheet("")  # Clear any error styling if the text is empty

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Override to handle key events"""
        super().keyPressEvent(event)
        # Validate the text after the key press event
        self.validate_text()
