"""Main application composition shell for the JARVIS GUI interface."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from jarvis.ui.gui.config import UIConfig
from jarvis.ui.gui.services.engine_service import JarvisAIService
from jarvis.ui.gui.store import ConversationStore
from jarvis.ui.gui.themes import build_stylesheet, get_theme
from jarvis.ui.gui.widgets import (
    ConversationView,
    GlowIconButton,
    JarvisOrb,
    NavigationDrawer,
    PromptBar,
    SettingsPage,
)


class JarvisWindow(QMainWindow):
    """Responsive application shell that wires widgets to services and settings."""

    def __init__(
        self,
        *,
        config: UIConfig | None = None,
        ai_service: Any | None = None,
        engine: Any | None = None,
        conversation_store: ConversationStore | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.config = config or UIConfig.load()
        self.theme = get_theme(self.config.theme_name, self.config.accent_name)
        self.engine = engine
        if ai_service is not None:
            self.ai_service = ai_service
        else:
            self.ai_service = JarvisAIService(engine=engine, parent=self)
        self.conversation_store = conversation_store or ConversationStore.default()
        self.current_conversation_id: str | None = None
        self._pending_counts: dict[str, int] = {}
        self._attachment_path = ""
        self._speech_stop_timer = QTimer(self)
        self._speech_stop_timer.setSingleShot(True)
        self._speech_stop_timer.timeout.connect(self._finish_speaking)

        self.setWindowTitle("JARVIS • Command Interface")
        self.resize(1280, 760)
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._connect_signals()
        self._install_shortcuts()
        self.apply_config(self.config, persist=False)
        self._refresh_conversation_list()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 18, 18, 18)

        self.app_frame = QFrame()
        self.app_frame.setObjectName("AppFrame")
        frame_layout = QHBoxLayout(self.app_frame)
        frame_layout.setContentsMargins(14, 14, 14, 14)
        frame_layout.setSpacing(14)
        root_layout.addWidget(self.app_frame)

        self.navigation = NavigationDrawer(self.theme)
        self.navigation.hide()
        frame_layout.addWidget(self.navigation)

        self.page_stack = QStackedWidget()
        frame_layout.addWidget(self.page_stack, 1)

        content = QFrame()
        self.assistant_page = content
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 10)
        content_layout.setSpacing(7)
        self.page_stack.addWidget(content)

        header = QHBoxLayout()
        self.menu_button = GlowIconButton("menu", self.theme, size=50, checkable=True)
        self.menu_button.setToolTip("Open command menu")
        header.addWidget(self.menu_button)
        header.addStretch(1)

        self.mode_badge = QLabel("●  READY")
        self.mode_badge.setObjectName("StatusLabel")
        self.mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.mode_badge)
        header.addStretch(1)

        self.settings_button = GlowIconButton("settings", self.theme, size=46)
        self.settings_button.setToolTip("Open settings")
        header.addWidget(self.settings_button)
        content_layout.addLayout(header)

        self.orb = JarvisOrb(self.theme, self.config)
        content_layout.addWidget(self.orb, 1)

        transcript_row = QHBoxLayout()
        transcript_row.setContentsMargins(38, 0, 38, 0)
        transcript_row.addStretch(1)
        self.conversation_view = ConversationView(self.theme)
        transcript_row.addWidget(self.conversation_view, 5)
        transcript_row.addStretch(1)
        content_layout.addLayout(transcript_row)

        prompt_row = QHBoxLayout()
        prompt_row.setContentsMargins(24, 0, 24, 0)
        prompt_row.addStretch(1)
        self.prompt_bar = PromptBar(self.theme)
        prompt_row.addWidget(self.prompt_bar, 5)
        prompt_row.addStretch(1)
        content_layout.addLayout(prompt_row)

        self.settings = SettingsPage(self.theme, self.config)
        self.page_stack.addWidget(self.settings)

    def _connect_signals(self) -> None:
        self.menu_button.toggled.connect(self._toggle_navigation)
        self.settings_button.clicked.connect(self._show_settings_page)
        self.navigation.close_requested.connect(
            lambda: self.menu_button.setChecked(False)
        )
        self.navigation.new_chat_requested.connect(self.start_new_chat)
        self.navigation.conversation_selected.connect(self.open_conversation)
        self.settings.back_requested.connect(self._show_assistant_page)
        self.settings.config_changed.connect(self.apply_config)
        self.prompt_bar.submitted.connect(self.submit_prompt)
        self.prompt_bar.attachment_requested.connect(self.choose_attachment)
        self.prompt_bar.microphone_toggled.connect(self._toggle_microphone)

    def _install_shortcuts(self) -> None:
        focus_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_shortcut.activated.connect(self.prompt_bar.focus_input)
        escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape_shortcut.activated.connect(self._close_drawers)

    def _toggle_navigation(self, visible: bool) -> None:
        self.navigation.setVisible(visible)

    def _show_settings_page(self) -> None:
        self.menu_button.setChecked(False)
        self.page_stack.setCurrentWidget(self.settings)

    def _show_assistant_page(self) -> None:
        self.page_stack.setCurrentWidget(self.assistant_page)

    def _close_drawers(self) -> None:
        self.menu_button.setChecked(False)
        self._show_assistant_page()

    def _toggle_microphone(self, listening: bool) -> None:
        self.orb.set_status("LISTENING" if listening else "ONLINE • READY")
        self.mode_badge.setText("●  LISTENING" if listening else "●  READY")

    def choose_attachment(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Attach a file")
        if not path:
            return
        self._attachment_path = path
        filename = path.replace("\\", "/").rsplit("/", 1)[-1]
        self.prompt_bar.input.setPlaceholderText(
            f"Attached: {filename} — ask a question…"
        )
        self.orb.set_status("ATTACHMENT READY")

    def submit_prompt(self, prompt: str) -> None:
        if self.current_conversation_id is None:
            self.current_conversation_id = self.conversation_store.create_conversation(
                self._title_from_prompt(prompt)
            )
        conversation_id = self.current_conversation_id
        self.conversation_store.add_message(conversation_id, "user", prompt)
        self._pending_counts[conversation_id] = (
            self._pending_counts.get(conversation_id, 0) + 1
        )
        self.conversation_view.add_message("user", prompt)
        self.conversation_view.show_pending()
        self._refresh_conversation_list()
        self._speech_stop_timer.stop()
        self.prompt_bar.set_busy(True)
        self.orb.set_speaking(True)
        self.orb.set_status("PROCESSING")
        self.mode_badge.setText("●  THINKING")
        self.ai_service.request(
            prompt,
            lambda response, saved_id=conversation_id: self._receive_response(
                saved_id, response
            ),
        )

    def _receive_response(self, conversation_id: str, response: str) -> None:
        self.conversation_store.add_message(conversation_id, "assistant", response)
        remaining = max(0, self._pending_counts.get(conversation_id, 1) - 1)
        if remaining:
            self._pending_counts[conversation_id] = remaining
        else:
            self._pending_counts.pop(conversation_id, None)
        self._refresh_conversation_list()
        if self.current_conversation_id != conversation_id:
            return

        self.conversation_view.hide_pending()
        self.conversation_view.add_message("assistant", response)
        if remaining:
            self.conversation_view.show_pending()
        self.prompt_bar.set_busy(remaining > 0)
        if not remaining:
            self.prompt_bar.focus_input()
        self.orb.set_status("SPEAKING")
        self.mode_badge.setText("●  SPEAKING")
        speaking_duration = max(1600, min(3800, len(response) * 18))
        self._speech_stop_timer.start(speaking_duration)

    def _finish_speaking(self) -> None:
        self.orb.set_speaking(False)
        self.orb.set_status("ONLINE • READY")
        self.mode_badge.setText("●  READY")

    def start_new_chat(self) -> None:
        self._show_assistant_page()
        self.current_conversation_id = None
        self._attachment_path = ""
        self._speech_stop_timer.stop()
        self.conversation_view.clear_messages()
        self.prompt_bar.set_busy(False)
        self.prompt_bar.input.clear()
        self.prompt_bar.input.setPlaceholderText("Ask me anything...")
        self.orb.set_speaking(False)
        self.orb.set_status("ONLINE • READY")
        self.mode_badge.setText("●  READY")
        self._refresh_conversation_list()
        self.menu_button.setChecked(False)
        self.prompt_bar.focus_input()

    def open_conversation(self, conversation_id: str) -> None:
        messages = self.conversation_store.get_messages(conversation_id)
        self.current_conversation_id = conversation_id
        self._attachment_path = ""
        self._speech_stop_timer.stop()
        self.orb.set_speaking(False)
        self.orb.set_status("ONLINE • READY")
        self.mode_badge.setText("●  READY")
        self.conversation_view.set_messages(messages)
        pending = self._pending_counts.get(conversation_id, 0) > 0
        if pending:
            self.conversation_view.show_pending()
        self.prompt_bar.set_busy(pending)
        self.prompt_bar.input.clear()
        self.prompt_bar.input.setPlaceholderText("Ask me anything...")
        self._refresh_conversation_list()
        self.menu_button.setChecked(False)
        if not pending:
            self.prompt_bar.focus_input()

    def _refresh_conversation_list(self) -> None:
        self.navigation.set_conversations(
            self.conversation_store.list_conversations(),
            self.current_conversation_id,
        )

    @staticmethod
    def _title_from_prompt(prompt: str) -> str:
        title = " ".join(prompt.split())
        return title if len(title) <= 38 else f"{title[:37].rstrip()}…"

    def apply_config(self, config: UIConfig, *, persist: bool = True) -> None:
        self.config = config
        self.theme = get_theme(config.theme_name, config.accent_name)
        self.setStyleSheet(build_stylesheet(self.theme))
        self.orb.apply_settings(self.theme, config)
        self.prompt_bar.apply_theme(self.theme)
        self.conversation_view.apply_theme(self.theme)
        self.navigation.apply_theme(self.theme)
        self.settings.apply_theme(self.theme)
        self.menu_button.set_theme(self.theme)
        self.settings_button.set_theme(self.theme)
        self.mode_badge.setStyleSheet(
            f"color: {self.theme.muted}; background: transparent; border: none; "
            "padding: 4px 8px; font-size: 10px; font-weight: 600;"
        )
        if persist:
            config.save()
