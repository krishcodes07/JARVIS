"""Left navigation drawer kept independent from the main window."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from jarvis_gui.components.icon_button import GlowIconButton
from jarvis_gui.conversation_store import ConversationSummary
from jarvis_gui.themes import Theme


class NavigationDrawer(QFrame):
    close_requested = Signal()
    new_chat_requested = Signal()
    conversation_selected = Signal(str)

    def __init__(self, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("Drawer")
        self.setFixedWidth(264)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        brand = QLabel("JARVIS")
        brand.setObjectName("BrandSmall")
        header.addWidget(brand)
        header.addStretch(1)
        self.close_button = GlowIconButton("close", theme, size=38)
        self.close_button.setToolTip("Close menu")
        self.close_button.clicked.connect(self.close_requested)
        header.addWidget(self.close_button)
        root.addLayout(header)

        title = QLabel("Assistant")
        title.setObjectName("DrawerTitle")
        root.addWidget(title)

        new_chat = QPushButton("New conversation")
        new_chat.setObjectName("PrimaryAction")
        new_chat.clicked.connect(self.new_chat_requested)
        root.addWidget(new_chat)

        section = QLabel("CONVERSATIONS")
        section.setObjectName("SectionLabel")
        root.addSpacing(7)
        root.addWidget(section)

        self.conversation_list = QListWidget()
        self.conversation_list.setObjectName("ConversationList")
        self.conversation_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.conversation_list.setSpacing(3)
        self.conversation_list.itemClicked.connect(self._select_conversation)
        root.addWidget(self.conversation_list, 1)

        footer = QLabel("LOCAL ASSISTANT  •  READY")
        footer.setObjectName("StatusLabel")
        footer.setWordWrap(True)
        root.addWidget(footer)

    def set_conversations(
        self,
        conversations: list[ConversationSummary],
        current_id: str | None = None,
    ) -> None:
        self.conversation_list.blockSignals(True)
        self.conversation_list.clear()
        selected_row = -1
        if not conversations:
            empty = QListWidgetItem("No saved conversations yet")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.conversation_list.addItem(empty)
        else:
            for row, conversation in enumerate(conversations):
                item = QListWidgetItem(conversation.title)
                item.setData(Qt.ItemDataRole.UserRole, conversation.id)
                item.setToolTip(
                    f"{conversation.title}\n{conversation.message_count} messages"
                )
                self.conversation_list.addItem(item)
                if conversation.id == current_id:
                    selected_row = row
        if selected_row >= 0:
            self.conversation_list.setCurrentRow(selected_row)
        self.conversation_list.blockSignals(False)

    def _select_conversation(self, item: QListWidgetItem) -> None:
        conversation_id = item.data(Qt.ItemDataRole.UserRole)
        if conversation_id:
            self.conversation_selected.emit(str(conversation_id))

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.close_button.set_theme(theme)
