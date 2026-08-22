"""Scrollable conversation view displaying message bubbles and pending thinking indicator."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from jarvis.ui.gui.store import ConversationMessage
    from jarvis.ui.gui.themes import Theme


class ConversationView(QScrollArea):
    """Scrollable conversation container displaying message bubbles."""

    def __init__(self, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.container.setObjectName("ConversationContainer")
        self.layout_box = QVBoxLayout(self.container)
        self.layout_box.setContentsMargins(12, 12, 12, 12)
        self.layout_box.setSpacing(12)
        self.layout_box.addStretch(1)
        self.setWidget(self.container)

        self.pending_widget: QWidget | None = None
        self.apply_theme(theme)

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QWidget#ConversationContainer {
                background: transparent;
            }
            """
        )

    def _clear_layout(self, layout) -> None:
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            l = item.layout()
            if w is not None:
                w.deleteLater()
            elif l is not None:
                self._clear_layout(l)

    def clear_messages(self) -> None:
        self.hide_pending()
        while self.layout_box.count() > 1:
            item = self.layout_box.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            l = item.layout()
            if w is not None:
                w.deleteLater()
            elif l is not None:
                self._clear_layout(l)

    def add_message(self, role: str, content: str) -> None:
        self.hide_pending()

        display_text = content
        if role != "user":
            cleaned = re.sub(
                r"<(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>(.*?)(?:</(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>|$)",
                "",
                content,
                flags=re.DOTALL | re.IGNORECASE,
            ).strip()
            if cleaned:
                display_text = cleaned

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)

        bubble = QLabel(display_text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        font = bubble.font()
        font.setPixelSize(13)
        bubble.setFont(font)

        if role == "user":
            row.addStretch(1)
            bubble.setStyleSheet(
                f"""
                QLabel {{
                    background: {self.theme.accent};
                    color: {self.theme.background};
                    border-radius: 12px;
                    border-bottom-right-radius: 2px;
                    padding: 10px 14px;
                    max-width: 620px;
                    font-weight: 500;
                }}
                """
            )
            row.addWidget(bubble)
        else:
            bubble.setStyleSheet(
                f"""
                QLabel {{
                    background: {self.theme.surface};
                    color: {self.theme.text};
                    border: 1px solid {self.theme.border};
                    border-radius: 12px;
                    border-bottom-left-radius: 2px;
                    padding: 10px 14px;
                    max-width: 680px;
                }}
                """
            )
            row.addWidget(bubble)
            row.addStretch(1)

        idx = max(0, self.layout_box.count() - 1)
        self.layout_box.insertLayout(idx, row)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def set_messages(self, messages: list[ConversationMessage]) -> None:
        self.clear_messages()
        for msg in messages:
            self.add_message(msg.role, msg.content)

    def show_pending(self) -> None:
        if self.pending_widget is not None:
            return

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("JARVIS is thinking…")
        lbl.setStyleSheet(
            f"""
            QLabel {{
                color: {self.theme.accent};
                background: {self.theme.surface_alt};
                border: 1px solid {self.theme.border};
                border-radius: 10px;
                padding: 6px 12px;
                font-style: italic;
                font-size: 12px;
            }}
            """
        )
        row.addWidget(lbl)
        row.addStretch(1)

        w = QWidget()
        w.setLayout(row)
        idx = max(0, self.layout_box.count() - 1)
        self.layout_box.insertWidget(idx, w)
        self.pending_widget = w
        QTimer.singleShot(50, self._scroll_to_bottom)

    def hide_pending(self) -> None:
        if self.pending_widget is not None:
            self.layout_box.removeWidget(self.pending_widget)
            self.pending_widget.deleteLater()
            self.pending_widget = None

    def _scroll_to_bottom(self) -> None:
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
