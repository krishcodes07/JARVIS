"""Composable prompt input bar with attachment, voice, and send controls."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QSizePolicy

from jarvis_gui.components.icon_button import GlowIconButton
from jarvis_gui.themes import Theme


class PromptBar(QFrame):
    submitted = Signal(str)
    attachment_requested = Signal()
    microphone_toggled = Signal(bool)

    def __init__(self, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("PromptBar")
        self.setMinimumHeight(68)
        self.setMaximumWidth(820)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 8, 8)
        layout.setSpacing(6)

        self.input = QLineEdit()
        self.input.setObjectName("PromptInput")
        self.input.setPlaceholderText("Ask me anything...")
        self.input.setClearButtonEnabled(False)
        self.input.returnPressed.connect(self._submit)
        layout.addWidget(self.input, 1)

        self.attach_button = GlowIconButton("attach", theme, size=40)
        self.attach_button.setToolTip("Attach a file")
        self.attach_button.clicked.connect(self.attachment_requested)
        layout.addWidget(self.attach_button)

        self.mic_button = GlowIconButton("mic", theme, size=40, checkable=True)
        self.mic_button.setToolTip("Toggle microphone")
        self.mic_button.toggled.connect(self.microphone_toggled)
        layout.addWidget(self.mic_button)

        self.send_button = GlowIconButton("send", theme, size=46)
        self.send_button.setToolTip("Send message")
        self.send_button.clicked.connect(self._submit)
        layout.addWidget(self.send_button)
        self.apply_theme(theme)

    def _submit(self) -> None:
        prompt = self.input.text().strip()
        if not prompt or not self.input.isEnabled():
            return
        self.input.clear()
        self.submitted.emit(prompt)

    def set_busy(self, busy: bool) -> None:
        self.input.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        self.input.setPlaceholderText(
            "JARVIS is thinking..." if busy else "Ask me anything..."
        )

    def focus_input(self) -> None:
        self.input.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.setStyleSheet(
            f"""
            QFrame#PromptBar {{
                background: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 14px;
            }}
            QFrame#PromptBar:focus-within {{ border-color: {theme.accent}; }}
            QLineEdit#PromptInput {{
                color: {theme.text};
                background: transparent;
                border: none;
                padding: 8px 4px;
                font-size: 15px;
                selection-background-color: {theme.accent_soft};
            }}
            QLineEdit#PromptInput:disabled {{ color: {theme.muted}; }}
            """
        )
        for button in (self.attach_button, self.mic_button, self.send_button):
            button.set_theme(theme)
