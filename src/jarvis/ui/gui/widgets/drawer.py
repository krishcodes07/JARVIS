"""Side navigation drawer showing conversation history and search filter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jarvis.ui.gui.widgets.buttons import GlowIconButton

if TYPE_CHECKING:
    from jarvis.ui.gui.store import ConversationSummary
    from jarvis.ui.gui.themes import Theme


class NavigationDrawer(QFrame):
    """Side navigation drawer showing chat sessions and New Chat trigger."""

    close_requested = Signal()
    new_chat_requested = Signal()
    conversation_selected = Signal(str)

    def __init__(self, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("Drawer")
        self.setFixedWidth(280)
        self._conversations: list[ConversationSummary] = []
        self._active_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Header row with title & close button
        header_row = QHBoxLayout()
        title_label = QLabel("Conversations")
        font = title_label.font()
        font.setPixelSize(15)
        font.setBold(True)
        title_label.setFont(font)
        header_row.addWidget(title_label)
        header_row.addStretch(1)

        self.close_btn = GlowIconButton("close", theme, size=32)
        self.close_btn.clicked.connect(self.close_requested.emit)
        header_row.addWidget(self.close_btn)
        layout.addLayout(header_row)

        # New Chat Button
        self.new_chat_btn = QPushButton("＋  New Chat")
        self.new_chat_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.new_chat_btn.setFixedHeight(38)
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)
        layout.addWidget(self.new_chat_btn)

        # Search input field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search sessions…")
        self.search_input.setFixedHeight(34)
        self.search_input.textChanged.connect(self._filter_list)
        layout.addWidget(self.search_input)

        # Session List Widget
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("SessionList")
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, 1)

        self.apply_theme(theme)

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.close_btn.set_theme(theme)
        self.setStyleSheet(
            f"""
            QFrame#Drawer {{
                background: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 12px;
            }}
            QLabel {{
                color: {theme.text};
            }}
            QPushButton {{
                background: {theme.accent_soft};
                color: {theme.accent};
                border: 1px solid {theme.accent};
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {theme.accent};
                color: {theme.background};
            }}
            QLineEdit {{
                background: {theme.surface_alt};
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            """
        )

    def set_conversations(
        self,
        conversations: list[ConversationSummary],
        active_id: str | None,
    ) -> None:
        self._conversations = conversations
        self._active_id = active_id
        self._render_list()

    def _render_list(self) -> None:
        self.list_widget.clear()
        filter_text = self.search_input.text().casefold()

        for item_data in self._conversations:
            if filter_text and filter_text not in item_data.title.casefold():
                continue

            item = QListWidgetItem(item_data.title)
            item.setData(Qt.ItemDataRole.UserRole, item_data.id)
            if item_data.id == self._active_id:
                item.setSelected(True)
            self.list_widget.addItem(item)

    def _filter_list(self) -> None:
        self._render_list()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        if conv_id:
            self.conversation_selected.emit(str(conv_id))
