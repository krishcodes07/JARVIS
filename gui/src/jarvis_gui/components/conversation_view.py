"""Scrollable ChatGPT-style transcript composed from reusable message bubbles."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from jarvis_gui.themes import Theme


class MessageBubble(QFrame):
    def __init__(
        self,
        role: str,
        content: str,
        theme: Theme,
        *,
        pending: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.role = role
        self.pending = pending
        self.setObjectName("UserMessage" if role == "user" else "AssistantMessage")
        self.setMinimumWidth(320)
        self.setMaximumWidth(650)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 11)
        layout.setSpacing(4)

        self.role_label = QLabel("YOU" if role == "user" else "JARVIS")
        self.role_label.setObjectName("MessageRole")
        layout.addWidget(self.role_label)

        self.content_label = QLabel(content)
        self.content_label.setObjectName("MessageContent")
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.content_label)
        self.apply_theme(theme)

    def apply_theme(self, theme: Theme) -> None:
        if self.role == "user":
            background = theme.surface_alt
            border = theme.border
        else:
            background = theme.surface
            border = theme.border
        self.setStyleSheet(
            f"""
            QFrame#{self.objectName()} {{
                background: {background};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QLabel#MessageRole {{
                color: {theme.accent};
                border: none;
                background: transparent;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QLabel#MessageContent {{
                color: {theme.muted if self.pending else theme.text};
                border: none;
                background: transparent;
                font-size: 13px;
            }}
            """
        )


class ConversationView(QScrollArea):
    """Message transcript that remains hidden until a conversation starts."""

    def __init__(self, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self.theme = theme
        self._message_count = 0
        self._pending_row: QWidget | None = None
        self.setObjectName("ConversationView")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMinimumHeight(205)
        self.setMaximumHeight(265)
        self.viewport().setAutoFillBackground(False)

        self.content = QWidget()
        self.content.setObjectName("TranscriptContent")
        self.messages_layout = QVBoxLayout(self.content)
        self.messages_layout.setContentsMargins(10, 6, 10, 6)
        self.messages_layout.setSpacing(9)
        self.messages_layout.addStretch(1)
        self.setWidget(self.content)
        self.hide()

    @property
    def message_count(self) -> int:
        return self._message_count

    def clear_messages(self) -> None:
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._pending_row = None
        self._message_count = 0
        self.hide()

    def set_messages(self, messages: Iterable[object]) -> None:
        self.clear_messages()
        for message in messages:
            self.add_message(
                str(getattr(message, "role")),
                str(getattr(message, "content")),
                scroll=False,
            )
        if self._message_count:
            self.show()
            self._schedule_scroll()

    def add_message(self, role: str, content: str, *, scroll: bool = True) -> None:
        self.hide_pending()
        row = self._create_row(role, content)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, row)
        self._message_count += 1
        self.show()
        if scroll:
            self._schedule_scroll()

    def show_pending(self) -> None:
        self.hide_pending()
        self._pending_row = self._create_row(
            "assistant", "Thinking…", pending=True
        )
        self.messages_layout.insertWidget(
            self.messages_layout.count() - 1, self._pending_row
        )
        self.show()
        self._schedule_scroll()

    def hide_pending(self) -> None:
        if self._pending_row is None:
            return
        self.messages_layout.removeWidget(self._pending_row)
        self._pending_row.deleteLater()
        self._pending_row = None

    def _create_row(
        self, role: str, content: str, *, pending: bool = False
    ) -> QWidget:
        row = QWidget(self.content)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        bubble = MessageBubble(role, content, self.theme, pending=pending)
        if role == "user":
            layout.addStretch(1)
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch(1)
        return row

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        for bubble in self.findChildren(MessageBubble):
            bubble.apply_theme(theme)

    def _schedule_scroll(self) -> None:
        QTimer.singleShot(0, self._scroll_to_bottom)
        QTimer.singleShot(80, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
