"""Compact card for dummy or real assistant responses."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from jarvis_gui.themes import Theme


class ResponseCard(QFrame):
    def __init__(self, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("ResponseCard")
        self.setMaximumWidth(760)
        self.setMinimumHeight(82)

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        self.indicator = QLabel("●")
        self.indicator.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.indicator.setFixedWidth(16)
        root.addWidget(self.indicator)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        self.prompt_label = QLabel()
        self.prompt_label.setObjectName("StatusLabel")
        self.prompt_label.setWordWrap(True)
        self.response_label = QLabel()
        self.response_label.setObjectName("ResponseLabel")
        self.response_label.setWordWrap(True)
        self.response_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        text_layout.addWidget(self.prompt_label)
        text_layout.addWidget(self.response_label)
        root.addLayout(text_layout, 1)

        self.apply_theme(theme)
        self.hide()

    def show_loading(self, prompt: str) -> None:
        self.prompt_label.setText(f"YOU  •  {prompt}")
        self.response_label.setText("Analyzing your request…")
        self.show()

    def show_response(self, prompt: str, response: str) -> None:
        self.prompt_label.setText(f"YOU  •  {prompt}")
        self.response_label.setText(response)
        self.show()

    def clear_response(self) -> None:
        self.hide()
        self.prompt_label.clear()
        self.response_label.clear()

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.indicator.setStyleSheet(
            f"color: {theme.accent}; font-size: 12px; border: none;"
        )

