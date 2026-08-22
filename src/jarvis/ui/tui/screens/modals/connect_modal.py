"""
Connect Provider Modal Screen — Browse and connect 180+ LLM providers from models.dev (/connect).
Displays checkmarks (✓) for connected providers and opens API key entry dialog on selection.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual import work
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from jarvis.providers.models_dev import (
    get_provider_env_vars,
    is_provider_connected,
    load_models_dev_cache,
)
from jarvis.ui.tui.utils import handle_search_key_navigation
from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class ConnectModal(ModalScreen[dict[str, str] | None]):
    """Modal screen for searching and connecting to any provider from models.dev catalog."""

    DEFAULT_CSS = """
    ConnectModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }
    """

    def __init__(self, engine: JarvisEngine | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.dialog = ModalDialog(
            title="Connect a provider",
            dialog_id="connect-dialog",
            width=62,
            height="80%",
            show_search=True,
            search_placeholder="Search",
            footer_text="↑↓ navigate   Enter select   Esc cancel",
        )
        self.providers_data: list[dict[str, Any]] = []
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
        self._loading_timer = self.set_interval(0.1, self._animate_loading)
        self.populate_list()
        self.load_providers_async()

    def _animate_loading(self) -> None:
        if self._is_loading and self.is_mounted:
            self._loading_frame += 1
            self.populate_list(self.search_input.value if self.search_input else "")

    def on_unmount(self) -> None:
        if self._loading_timer:
            self._loading_timer.stop()
            self._loading_timer = None

    @work(exclusive=True)
    async def load_providers_async(self) -> None:
        try:
            await asyncio.to_thread(self.load_providers_data)
        finally:
            self._is_loading = False
            if self._loading_timer:
                self._loading_timer.stop()
                self._loading_timer = None
            if self.is_mounted:
                self.populate_list(self.search_input.value if self.search_input else "")

    def load_providers_data(self) -> None:
        cache = load_models_dev_cache()
        if not cache and self.engine and self.engine.provider_manager:
            cache = {
                k: v.raw for k, v in self.engine.provider_manager.registry.get_all().items()
            }

        data_list: list[dict[str, Any]] = []
        for pid, pdata in cache.items():
            pname = pdata.get("name") or pid
            env_vars = get_provider_env_vars(pid, pdata)
            connected = is_provider_connected(pid, pdata)
            data_list.append({
                "id": pid,
                "name": pname,
                "api_key_env": env_vars[0] if env_vars else f"{pid.upper()}_API_KEY",
                "env_vars": env_vars,
                "connected": connected,
                "raw": pdata,
            })

        # Sort alphabetically by provider name
        data_list.sort(key=lambda x: x["name"].lower())
        self.providers_data = data_list

    def on_key(self, event) -> None:
        """Delegate arrow keys and Enter from search input to option list."""
        handle_search_key_navigation(event, self.search_input, self.option_list)

    def on_input_changed(self, event: Input.Changed) -> None:
        self.populate_list(filter_text=event.value)

    def populate_list(self, filter_text: str = "") -> None:
        if not self.is_mounted:
            return
        self.option_list.clear_options()

        if self._is_loading:
            frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner = frames[self._loading_frame % len(frames)]
            for _ in range(4):
                self.option_list.add_option(Option(Text(""), disabled=True))
            msg = f"{spinner}  Loading providers..."
            t = Text(msg.center(54), style="bold #f97316")
            self.option_list.add_option(Option(t, disabled=True))
            return

        query = filter_text.strip().lower()

        # Section Header: "Providers"
        header_text = Text("\nProviders", style="bold #f97316")
        self.option_list.add_option(Option(header_text, disabled=True))

        filtered = []
        for p in self.providers_data:
            if query:
                if query not in p["name"].lower() and query not in p["id"].lower():
                    continue
            filtered.append(p)

        if not filtered:
            msg = Text("  No matching providers found", style="dim #737373")
            self.option_list.add_option(Option(msg, disabled=True))
            return

        for p in filtered:
            t = Text(no_wrap=True, overflow="ellipsis")
            if p["connected"]:
                t.append("✓ ", style="bold #10b981")
                t.append(p["name"], style="bold #ffffff")
            else:
                t.append("  ", style="")
                t.append(p["name"], style="#d1d5db")

            self.option_list.add_option(Option(t, id=p["id"]))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        selected_id = getattr(event, "option_id", None) or (
            event.option.id if getattr(event, "option", None) else None
        )
        if not selected_id:
            return

        found = next((p for p in self.providers_data if p["id"] == selected_id), None)
        if not found:
            return

        self.dismiss(found)

    def key_escape(self) -> None:
        self.dismiss(None)
