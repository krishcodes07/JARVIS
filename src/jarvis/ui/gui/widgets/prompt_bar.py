"""Prompt input bar widget with text field, file attachment, mic toggle, and submit button."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QWidget

from jarvis.ui.gui.widgets.buttons import GlowIconButton

if TYPE_CHECKING:
    from jarvis.ui.gui.themes import Theme


class PromptBar(QFrame):
    """Input bar widget for composing and submitting prompts."""

    submitted = Signal(str)
    attachment_requested = Signal()
    microphone_toggled = Signal(bool)

    def __init__(self, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("PromptCard")
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Attachment button
        self.attach_btn = GlowIconButton("attach", theme, size=40)
        self.attach_btn.setToolTip("Attach file")
        self.attach_btn.clicked.connect(self.attachment_requested.emit)
        layout.addWidget(self.attach_btn)

        # Text Input
        self.input = QLineEdit()
        self.input.setObjectName("PromptInput")
        self.input.setPlaceholderText("Ask me anything...")
        self.input.returnPressed.connect(self._on_submit)
        font = self.input.font()
        font.setPixelSize(14)
        self.input.setFont(font)
        layout.addWidget(self.input, 1)

        # Mic toggle button
        self.mic_btn = GlowIconButton("mic", theme, size=40, checkable=True)
        self.mic_btn.setToolTip("Toggle microphone")
        self.mic_btn.toggled.connect(self.microphone_toggled.emit)
        layout.addWidget(self.mic_btn)

        # Send button
        self.send_btn = GlowIconButton("send", theme, size=40)
        self.send_btn.setToolTip("Send message")
        self.send_btn.clicked.connect(self._on_submit)
        layout.addWidget(self.send_btn)

        self.apply_theme(theme)

    def focus_input(self) -> None:
        self.input.setFocus()

    def set_busy(self, busy: bool) -> None:
        self.input.setEnabled(not busy)
        self.send_btn.setEnabled(not busy)
        self.attach_btn.setEnabled(not busy)

    def _on_submit(self) -> None:
        text = self.input.text().strip()
        if text:
            self.input.clear()
            self.submitted.emit(text)

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.attach_btn.set_theme(theme)
        self.mic_btn.set_theme(theme)
        self.send_btn.set_theme(theme)
        self.setStyleSheet(
            f"""
            QFrame#PromptCard {{
                background: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 32px;
            }}
            QLineEdit#PromptInput {{
                background: transparent;
                color: {theme.text};
                border: none;
                padding: 0 8px;
            }}
            """
        )
