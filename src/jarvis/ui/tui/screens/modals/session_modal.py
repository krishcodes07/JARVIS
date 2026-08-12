"""
Sessions Modal Screen — Floating dialog for managing and switching sessions (/sessions).
Reads real session JSON files from get_sessions_dir() (~/.jarvis/workspace/sessions) and matches Image 2 design.

Supports:
- Keyboard navigation (up/down from search)
- Delete session (Ctrl+D)
- Rename session (Ctrl+R)
- Pin/Unpin session (Ctrl+F)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from rich.text import Text
from textual import on
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from jarvis.core.paths import get_sessions_dir
from jarvis.ui.tui.utils import (
    format_date_group,
    handle_search_key_navigation,
    load_pinned_sessions,
    save_pinned_sessions,
    truncate_text,
)
from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


from textual import work

class SessionModal(ModalScreen[str | None]):
    """Modal dialog for session management, searching, and switching."""

    DEFAULT_CSS = """
    SessionModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }
    """

    def __init__(self, engine: JarvisEngine | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.dialog = ModalDialog(
            title="Sessions",
            dialog_id="session-dialog",
            width=66,
            height="80%",
            show_search=True,
            search_placeholder="Search sessions...",
            footer_text="pin ctrl+f   delete ctrl+d   rename ctrl+r",
        )
        self.sessions_data: list[dict] = []
        self.pinned_sessions: set[str] = load_pinned_sessions()
        self._is_loading: bool = True
        self._loading_timer = None
        self._loading_frame: int = 0

    @property
    def search_input(self) -> Input | None:
        return self.dialog.search_input

    @property
    def option_list(self) -> OptionList:
        return self.dialog.option_list

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        if self.search_input:
            self.search_input.focus()
        self._is_loading = True
        self._loading_frame = 0
        self._loading_timer = self.set_interval(0.3, self._animate_loading)
        self.populate_list()
        self.load_sessions_async()

    def _animate_loading(self) -> None:
        if self._is_loading and self.is_mounted:
            self._loading_frame += 1
            self.populate_list(self.search_input.value if self.search_input else "")

    def on_unmount(self) -> None:
        if self._loading_timer:
            self._loading_timer.stop()
            self._loading_timer = None

    @work(exclusive=True)
    async def load_sessions_async(self) -> None:
        try:
            self.sessions_data = self.load_real_sessions()
            import asyncio
            await asyncio.sleep(0.15)
        finally:
            self._is_loading = False
            if self._loading_timer:
                self._loading_timer.stop()
                self._loading_timer = None
            if self.is_mounted:
                self.populate_list(self.search_input.value if self.search_input else "")

    def on_key(self, event) -> None:
        """Delegate arrow keys and Enter from search input to the option list."""
        handle_search_key_navigation(event, self.search_input, self.option_list)

    def _get_highlighted_session_id(self) -> str | None:
        """Get the session ID of the currently highlighted option."""
        highlighted = self.option_list.highlighted
        if highlighted is not None:
            option = self.option_list.get_option_at_index(highlighted)
            option_id = option.id if option and option.id else None
            if option_id and not option_id.startswith("grp-"):
                return option_id
        return None

    def key_ctrl_d(self) -> None:
        """Delete the highlighted session with confirmation dialog."""
        sid = self._get_highlighted_session_id()
        if not sid or sid == "new":
            return

        from jarvis.ui.tui.screens.modals.confirm_modal import ConfirmModal

        def on_confirmed(confirmed: bool | None) -> None:
            if not confirmed:
                return

            conv_path = get_sessions_dir() / f"{sid}.json"
            if conv_path.exists():
                try:
                    os.remove(conv_path)
                    from jarvis.core.snapshot import FileSnapshotManager
                    FileSnapshotManager().clear_session(sid)
                    logger.info(f"Deleted session file: {conv_path}")
                except Exception as e:
                    logger.warning(f"Could not delete session {sid}: {e}")
                    return

            # If active session was deleted, reset active engine session and main screen UI
            if self.engine and self.engine.session and self.engine.session.session_id == sid:
                from jarvis.core.session import Session
                self.engine.session = Session(engine=self.engine)
                try:
                    main_screen = self.app.screen
                    if hasattr(main_screen, "chat_view"):
                        getattr(main_screen, "chat_view").clear_messages()
                    if hasattr(main_screen, "header"):
                        getattr(main_screen, "header").show_header()
                    if hasattr(main_screen, "prompt_box"):
                        getattr(main_screen, "prompt_box").show_hints()
                    toast_fn = getattr(main_screen, "show_toast", None)
                    if toast_fn:
                        toast_fn(
                            f"Active session '{sid}' deleted. Started new session.",
                            title="Session Reset",
                            style="info",
                        )
                except Exception:
                    pass

            # Remove from pinned if it was pinned
            if sid in self.pinned_sessions:
                self.pinned_sessions.discard(sid)
                save_pinned_sessions(self.pinned_sessions)

            # Refresh
            self.sessions_data = self.load_real_sessions()
            self.populate_list(self.search_input.value if self.search_input else "")

        self.app.push_screen(
            ConfirmModal(
                message=f"Delete session '{sid}'?",
                title="Confirm Session Deletion",
                confirm_label="Yes, delete session",
            ),
            on_confirmed,
        )

    def key_ctrl_r(self) -> None:
        """Rename the highlighted session by updating its first user message."""
        sid = self._get_highlighted_session_id()
        if not sid or sid == "new":
            return

        # Use the search input value as the new name
        if not self.search_input:
            return

        new_name = self.search_input.value.strip()
        if not new_name:
            # Show hint in search box
            self.search_input.placeholder = "Type new name, then press Ctrl+R"
            return

        conv_path = get_sessions_dir() / f"{sid}.json"
        if not conv_path.exists():
            return

        try:
            with open(conv_path, encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                # Insert/update a metadata entry at the beginning for the display name
                meta_found = False
                for msg in data:
                    if msg.get("role") == "system" and msg.get("_session_title"):
                        msg["_session_title"] = new_name
                        meta_found = True
                        break
                if not meta_found:
                    data.insert(0, {
                        "role": "system",
                        "content": "",
                        "_session_title": new_name,
                    })

                with open(conv_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                logger.info(f"Renamed session {sid} to: {new_name}")

            # Clear search and refresh
            self.search_input.value = ""
            self.search_input.placeholder = "Search sessions..."
            self.sessions_data = self.load_real_sessions()
            self.populate_list()

        except Exception as e:
            logger.warning(f"Could not rename session {sid}: {e}")

    def key_ctrl_f(self) -> None:
        """Toggle pin/unpin for the highlighted session."""
        sid = self._get_highlighted_session_id()
        if not sid or sid == "new":
            return

        if sid in self.pinned_sessions:
            self.pinned_sessions.discard(sid)
        else:
            self.pinned_sessions.add(sid)

        save_pinned_sessions(self.pinned_sessions)

        # Refresh to show pin status change
        self.sessions_data = self.load_real_sessions()
        self.populate_list(self.search_input.value if self.search_input else "")

    def load_real_sessions(self) -> list[dict]:
        """Scan get_sessions_dir() for real JSON session files."""
        sessions: list[dict] = []
        sessions.append(
            {"id": "new", "title": "+ Create New Session", "date_group": "Actions", "active": False}
        )

        conv_dir = get_sessions_dir()
        if not conv_dir.exists():
            return sessions

        files = sorted(conv_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")

        active_sid = (
            self.engine.session.session_id
            if (self.engine and self.engine.session)
            else None
        )

        pinned_entries: list[dict] = []
        regular_entries: list[dict] = []

        for p in files:
            sid = p.stem
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=UTC)
            date_group = format_date_group(mtime, today_str)

            title = f"New session - {mtime.strftime('%Y-%m-%dT%H:%M:%S')}"
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # Check for explicit session title first
                        for msg in data:
                            if msg.get("role") == "system" and msg.get("_session_title"):
                                title = truncate_text(msg["_session_title"], max_length=48)
                                break
                        else:
                            # Fall back to first user message
                            for msg in data:
                                if msg.get("role") == "user" and msg.get("content"):
                                    first_prompt = msg["content"].strip().split("\n")[0]
                                    title = truncate_text(first_prompt, max_length=48)
                                    break
            except Exception:
                pass

            is_active = (sid == active_sid)
            is_pinned = (sid in self.pinned_sessions)

            entry = {
                "id": sid,
                "title": title,
                "date_group": date_group,
                "agent": "JARVIS",
                "active": is_active,
                "pinned": is_pinned,
            }

            if is_pinned:
                pinned_entries.append(entry)
            else:
                regular_entries.append(entry)

        # Add pinned sessions first under their own group
        for entry in pinned_entries:
            entry["date_group"] = "📌 Pinned"
            sessions.append(entry)

        # Then add regular sessions
        sessions.extend(regular_entries)

        return sessions

    def on_input_changed(self, event: Input.Changed) -> None:
        self.populate_list(filter_text=event.value)

    def populate_list(self, filter_text: str = "") -> None:
        if not self.is_mounted:
            return
        self.option_list.clear_options()

        if self._is_loading:
            dots = "." * ((self._loading_frame % 3) + 1)
            for _ in range(4):
                self.option_list.add_option(Option(Text(""), disabled=True))
            msg = f"Loading sessions {dots:<3}"
            t = Text(msg.center(58), style="bold #818cf8")
            self.option_list.add_option(Option(t, disabled=True))
            return

        query = filter_text.strip().lower()

        current_group = ""
        for s in self.sessions_data:
            if query and query not in s["title"].lower():
                continue

            group = s["date_group"]
            if group != current_group:
                current_group = group
                header_text = Text(f"\n{group}", style="bold #818cf8")
                self.option_list.add_option(Option(header_text, disabled=True, id=f"grp-{group}"))

            t = Text(no_wrap=True, overflow="ellipsis")
            if s["id"] == "new":
                t.append(f"  {s['title']}", style="bold #f97316")
            else:
                is_active = s.get("active", False)
                is_pinned = s.get("pinned", False)

                # Active marker
                prefix = "✓ " if is_active else "  "
                style_title = "white"
                t.append(prefix, style="bold #22c55e" if is_active else "")
                title_str = s['title']
                if len(title_str) > 36:
                    title_str = title_str[:33] + "..."
                t.append(f"{title_str:<38}", style=style_title)

                # Right-side info
                info_parts = []
                if is_pinned:
                    info_parts.append("📌")
                if "agent" in s:
                    info_parts.append(s["agent"])
                if info_parts:
                    t.append(f" {'  '.join(info_parts)}", style="dim #64748b")

            self.option_list.add_option(Option(t, id=s["id"]))

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        selected_id = getattr(event, "option_id", None) or (
            event.option.id if getattr(event, "option", None) else None
        )
        if selected_id and not str(selected_id).startswith("grp-"):
            self.dismiss(str(selected_id))

    def key_escape(self) -> None:
        self.dismiss(None)
