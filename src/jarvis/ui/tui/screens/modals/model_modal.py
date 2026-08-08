"""
Model Selector Modal Screen — Dynamic provider & model browser (/models).
Displays ONLY connected providers and their models from models.dev database catalog.
Supports Ctrl+A shortcut to open Connect Provider modal and auto-scrolls to connected providers.
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

from jarvis.providers.models_dev import is_provider_connected, load_models_dev_cache
from jarvis.ui.tui.utils import (
    handle_search_key_navigation,
    load_recent_models,
    save_recent_model,
)
from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class ModelModal(ModalScreen[dict[str, str] | None]):
    """Modal dialog for searching, filtering, and switching LLM models across connected providers."""

    DEFAULT_CSS = """
    ModelModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }
    """

    def __init__(
        self,
        engine: JarvisEngine | None = None,
        initial_provider: str | None = None,
        only_provider: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.target_scroll_provider: str | None = initial_provider
        self.only_provider: str | None = only_provider.strip().lower() if only_provider else None

        title_text = "Select model"
        if self.only_provider:
            cache = load_models_dev_cache()
            pdata = cache.get(self.only_provider) or {}
            prov_disp = pdata.get("name") or self.only_provider.title()
            title_text = f"Select {prov_disp} model"

        self.dialog = ModalDialog(
            title=title_text,
            dialog_id="model-dialog",
            width=62,
            height="80%",
            show_search=True,
            search_placeholder="Search...",
            footer_text="Connect Provider ctrl+a",
        )
        self.models_data: list[dict[str, Any]] = []
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
        self.load_models_async()

    def _animate_loading(self) -> None:
        if self._is_loading and self.is_mounted:
            self._loading_frame += 1
            self.populate_list(self.search_input.value if self.search_input else "")

    def on_unmount(self) -> None:
        if self._loading_timer:
            self._loading_timer.stop()
            self._loading_timer = None

    @work(exclusive=True)
    async def load_models_async(self) -> None:
        try:
            self.models_data = await asyncio.to_thread(self._build_models_data)
        finally:
            self._is_loading = False
            if self._loading_timer:
                self._loading_timer.stop()
                self._loading_timer = None
            if self.is_mounted:
                self.populate_list(self.search_input.value if self.search_input else "")

    def refresh_models_list(self) -> None:
        self._is_loading = True
        self._loading_frame = 0
        if not self._loading_timer:
            self._loading_timer = self.set_interval(0.1, self._animate_loading)
        self.populate_list()
        self.load_models_async()

    def on_key(self, event) -> None:
        """Handle Ctrl+A shortcut to open Connect Provider modal or delegate navigation keys."""
        is_ctrl_a = (
            event.key in ("ctrl+a", "ctrl+A")
            or (getattr(event, "character", None) in ("a", "A") and getattr(event, "ctrl", False))
        )
        if is_ctrl_a:
            self.action_open_connect()
            event.prevent_default()
            event.stop()
            return

        handle_search_key_navigation(event, self.search_input, self.option_list)

    def action_open_connect(self) -> None:
        from jarvis.ui.tui.screens.modals.api_key_modal import ApiKeyModal
        from jarvis.ui.tui.screens.modals.connect_modal import ConnectModal

        def on_connect_done(selected_provider: dict[str, Any] | None) -> None:
            if selected_provider and isinstance(selected_provider, dict) and "id" in selected_provider:
                prov_id = selected_provider["id"]
                prov_name = selected_provider["name"]
                api_key_env = selected_provider.get("api_key_env") or f"{prov_id.upper()}_API_KEY"

                def on_api_key_done(saved_provider_id: str | None) -> None:
                    if saved_provider_id:
                        screen = getattr(self.app, "screen", None)
                        if screen and hasattr(screen, "action_open_models"):
                            screen.action_open_models(only_provider=saved_provider_id)
                        elif hasattr(self.app, "action_open_models"):
                            self.app.action_open_models(only_provider=saved_provider_id)

                def open_api_key_screen() -> None:
                    screen = getattr(self.app, "screen", None)
                    app_obj = screen if screen and hasattr(screen, "push_screen") else self.app
                    app_obj.push_screen(
                        ApiKeyModal(
                            provider_id=prov_id,
                            provider_name=prov_name,
                            api_key_env=api_key_env,
                            engine=self.engine,
                        ),
                        on_api_key_done,
                    )

                if hasattr(self.app, "set_timer"):
                    self.app.set_timer(0.05, open_api_key_screen)
                else:
                    open_api_key_screen()

        self.dismiss(None)
        self.app.push_screen(ConnectModal(engine=self.engine), on_connect_done)

    def _get_active_provider(self) -> str:
        if self.engine and self.engine.config and self.engine.config.provider:
            return self.engine.config.provider.active
        return "groq"

    def _get_active_model(self) -> str:
        if self.engine and self.engine.config and self.engine.config.provider:
            return self.engine.config.provider.model
        return ""

    def _build_models_data(self) -> list[dict[str, Any]]:
        recent_list = load_recent_models()
        cache = load_models_dev_cache()

        active_provider = self._get_active_provider().lower()
        active_model = self._get_active_model()

        all_entries: list[dict[str, Any]] = []

        # Find all connected providers from models.dev database
        connected_providers: dict[str, dict[str, Any]] = {}
        for pid, pdata in cache.items():
            if is_provider_connected(pid, pdata):
                connected_providers[pid.lower()] = pdata

        # Add fallback/active provider if engine has provider_manager
        if self.engine and self.engine.provider_manager:
            for pid, pdef in self.engine.provider_manager.registry.get_all().items():
                if pdef.is_connected and pid.lower() not in connected_providers:
                    connected_providers[pid.lower()] = pdef.raw

        # If only_provider filter is specified (e.g. right after connecting a provider)
        if self.only_provider:
            filter_key = self.only_provider.strip().lower()
            matching_key = next((k for k in connected_providers if k == filter_key), None)

            if not matching_key:
                matching_key = next(
                    (k for k in connected_providers if k.startswith(filter_key) or filter_key.startswith(k)),
                    None,
                )

            if not matching_key:
                for pid, pdata in cache.items():
                    if pid.lower() == filter_key:
                        connected_providers[pid.lower()] = pdata
                        matching_key = pid.lower()
                        break

            if matching_key:
                connected_providers = {matching_key: connected_providers[matching_key]}
            elif filter_key in cache:
                connected_providers = {filter_key: cache[filter_key]}

        # 1. Recent Models (only for connected providers, and match only_provider if specified)
        if recent_list:
            for item in recent_list[:5]:
                mid = item.get("id", "")
                mprov = item.get("provider", "").lower()
                if self.only_provider:
                    if mprov != self.only_provider and self.only_provider not in mprov:
                        continue
                if mprov in connected_providers or not connected_providers:
                    all_entries.append({
                        "id": mid,
                        "name": item.get("name", mid),
                        "provider": mprov,
                        "category": "Recently Used",
                        "active": (mprov == active_provider and mid == active_model),
                    })

        # Sort connected provider names, active provider first
        sorted_prov_names = sorted(
            connected_providers.keys(),
            key=lambda name: (0 if name.lower() == active_provider else 1, name.lower()),
        )

        for prov_name in sorted_prov_names:
            pdata = connected_providers[prov_name]
            disp_name = pdata.get("name") or prov_name.title()
            is_active_prov = (prov_name.lower() == active_provider)
            category_title = f"Active: {disp_name}" if is_active_prov else disp_name

            raw_models = pdata.get("models") or {}
            model_items = []
            if isinstance(raw_models, dict) and raw_models:
                for mid, mdata in raw_models.items():
                    mname = mdata.get("name") if isinstance(mdata, dict) else str(mdata)
                    model_items.append({"id": mid, "name": mname or mid})
            else:
                default_m = pdata.get("default_model") or prov_name
                model_items.append({"id": default_m, "name": default_m})

            for m in model_items:
                mid = m["id"]
                mname = m["name"]
                all_entries.append({
                    "id": mid,
                    "name": mname,
                    "provider": prov_name.lower(),
                    "category": category_title,
                    "active": (is_active_prov and mid == active_model),
                })

        return all_entries

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
            msg = f"{spinner}  Loading models..."
            t = Text(msg.center(54), style="bold #3b82f6")
            self.option_list.add_option(Option(t, disabled=True))
            return

        query = filter_text.strip().lower()

        if not self.models_data:
            msg = Text("No connected providers found. Press Ctrl+A to connect.", style="bold #f97316")
            self.option_list.add_option(Option(msg, disabled=True))
            return

        current_category = ""
        seen_keys: set[str] = set()
        target_option_index: int | None = None
        current_option_idx = 0

        target_prov = (self.target_scroll_provider or "").strip().lower()

        for m in self.models_data:
            if query:
                match_name = query in m["name"].lower()
                match_prov = query in m["provider"].lower()
                match_id = query in m["id"].lower()
                if not (match_name or match_prov or match_id):
                    continue

            option_key = f"{m['provider']}::{m['id']}"
            if option_key in seen_keys:
                continue
            seen_keys.add(option_key)

            cat = m["category"]
            if cat != current_category:
                current_category = cat
                header_text = Text(f"\n{cat}", style="bold #3b82f6")
                self.option_list.add_option(Option(header_text, disabled=True))
                current_option_idx += 1

            active_bullet = "• " if m.get("active") else "  "
            active_style = "bold #3b82f6" if m.get("active") else "white"

            name = m["name"][:34]
            prov = m["provider"]
            fill = 52 - len(name) - len(prov)
            if fill < 1:
                fill = 1

            t = Text(no_wrap=True, overflow="ellipsis")
            t.append(active_bullet, style="bold #3b82f6")
            t.append(name, style=active_style)
            t.append(" " * fill, style="")
            t.append(prov, style="dim #737373")

            self.option_list.add_option(Option(t, id=option_key))

            if target_prov and m["provider"].lower() == target_prov and target_option_index is None:
                target_option_index = current_option_idx

            current_option_idx += 1

        # Scroll to target provider if specified
        if target_option_index is not None and self.option_list.option_count > target_option_index:
            try:
                self.option_list.highlighted = target_option_index
                if hasattr(self.option_list, "scroll_to_highlight"):
                    self.option_list.scroll_to_highlight(top=True)
            except Exception as e:
                logger.debug(f"Could not scroll to target provider: {e}")
            self.target_scroll_provider = None

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        selected_key = getattr(event, "option_id", None) or (
            event.option.id if getattr(event, "option", None) else None
        )
        if selected_key:
            if "::" in selected_key:
                prov, mid = selected_key.split("::", 1)
            else:
                prov, mid = "", selected_key

            found = next(
                (m for m in self.models_data if m["id"] == mid and (not prov or m["provider"] == prov)),
                None,
            )
            if found:
                save_recent_model(found)
                self.dismiss(found)
                return
            else:
                item = {
                    "id": mid,
                    "name": mid,
                    "provider": prov or self._get_active_provider(),
                }
                save_recent_model(item)
                self.dismiss(item)
                return
        self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
