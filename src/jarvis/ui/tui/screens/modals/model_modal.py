"""
Model Selector Modal Screen — Dynamic provider & model browser (/models).
Loads cached models instantly, fetches live models from all providers, and tracks 5 recent models.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual import work
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from jarvis.ui.tui.utils import (
    handle_search_key_navigation,
    load_models_cache,
    load_recent_models,
    save_models_cache,
    save_recent_model,
)
from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class ModelModal(ModalScreen[dict[str, str] | None]):
    """Modal dialog for searching, filtering, and switching LLM models across all providers."""

    DEFAULT_CSS = """
    ModelModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }
    """

    def __init__(self, engine: JarvisEngine | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.dialog = ModalDialog(
            title="Select model",
            dialog_id="model-dialog",
            width=62,
            height="80%",
            show_search=True,
            search_placeholder="Search...",
            footer_text="↑↓ navigate   Enter select   Esc cancel",
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
        self._loading_timer = self.set_interval(0.3, self._animate_loading)
        self.populate_list()
        self.refresh_all_provider_models()

    def _animate_loading(self) -> None:
        if self._is_loading and self.is_mounted:
            self._loading_frame += 1
            self.populate_list(self.search_input.value if self.search_input else "")

    def on_unmount(self) -> None:
        if self._loading_timer:
            self._loading_timer.stop()
            self._loading_timer = None

    def on_key(self, event) -> None:
        """Delegate arrow keys and Enter from search input to the option list."""
        handle_search_key_navigation(event, self.search_input, self.option_list)

    def _get_active_provider(self) -> str:
        if self.engine and self.engine.config and self.engine.config.provider:
            return self.engine.config.provider.active
        return "openrouter"

    def _get_active_model(self) -> str:
        if self.engine and self.engine.config and self.engine.config.provider:
            return self.engine.config.provider.model
        return ""

    def _build_models_data(self) -> list[dict[str, Any]]:
        recent_list = load_recent_models()
        models_cache = load_models_cache()

        active_provider = self._get_active_provider().lower()
        active_model = self._get_active_model()

        all_entries: list[dict[str, Any]] = []

        # 1. Recent 5 Models
        if recent_list:
            for item in recent_list[:5]:
                mid = item.get("id", "")
                mprov = item.get("provider", "").lower()
                all_entries.append({
                    "id": mid,
                    "name": item.get("name", mid),
                    "provider": mprov,
                    "category": "Recently Used",
                    "active": (mprov == active_provider and mid == active_model),
                })

        # 2 & 3. Active Provider first, then other providers
        if self.engine and self.engine.provider_manager:
            all_defs = self.engine.provider_manager.registry.get_all()
        else:
            all_defs = {}

        sorted_prov_names = sorted(
            all_defs.keys(),
            key=lambda name: (0 if name.lower() == active_provider else 1, name.lower()),
        )

        for prov_name in sorted_prov_names:
            prov_def = all_defs[prov_name]
            disp_name = getattr(prov_def, "display_name", prov_name.title())
            is_active_prov = (prov_name.lower() == active_provider)
            category_title = f"Active: {disp_name}" if is_active_prov else disp_name

            cached = models_cache.get(prov_name.lower()) or [
                {"id": prov_def.default_model, "name": prov_def.default_model}
            ]

            for m in cached:
                mid = m.get("id", str(m))
                mname = m.get("name", mid)
                all_entries.append({
                    "id": mid,
                    "name": mname,
                    "provider": prov_name.lower(),
                    "category": category_title,
                    "active": (is_active_prov and mid == active_model),
                })

        return all_entries

    @work(exclusive=True)
    async def refresh_all_provider_models(self) -> None:
        """Asynchronously fetch live models from all providers and update disk cache."""
        try:
            self.models_data = self._build_models_data()
            if not self.engine or not self.engine.provider_manager:
                return

            all_defs = self.engine.provider_manager.registry.get_all()
            models_cache = load_models_cache()
            updated = False

            for prov_name in sorted(all_defs.keys()):
                try:
                    live_list = await self.engine.provider_manager.get_models(prov_name)
                    if live_list:
                        models_cache[prov_name.lower()] = [
                            {
                                "id": str(m.get("id") or str(m)),
                                "name": str(m.get("name") or m.get("id") or str(m)),
                            }
                            for m in live_list
                        ]
                        updated = True
                except Exception as e:
                    logger.debug(f"Could not refresh models for provider {prov_name}: {e}")

            if updated:
                save_models_cache(models_cache)
                self.models_data = self._build_models_data()
        finally:
            self._is_loading = False
            if self._loading_timer:
                self._loading_timer.stop()
                self._loading_timer = None
            if self.is_mounted:
                self.populate_list(self.search_input.value if self.search_input else "")

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
            msg = f"Fetching models {dots:<3}"
            t = Text(msg.center(54), style="bold #3b82f6")
            self.option_list.add_option(Option(t, disabled=True))
            return
        query = filter_text.strip().lower()

        current_category = ""
        seen_keys: set[str] = set()
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

            active_bullet = "• " if m.get("active") else "  "
            active_style = "bold #3b82f6" if m.get("active") else "white"

            name = m["name"][:34]
            prov = m["provider"]
            # Right-align provider within a fixed-width line
            fill = 52 - len(name) - len(prov)
            if fill < 1:
                fill = 1

            t = Text(no_wrap=True, overflow="ellipsis")
            t.append(active_bullet, style="bold #3b82f6")
            t.append(name, style=active_style)
            t.append(" " * fill, style="")
            t.append(prov, style="dim #737373")

            self.option_list.add_option(Option(t, id=option_key))

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
