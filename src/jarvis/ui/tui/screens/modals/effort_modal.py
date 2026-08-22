"""
Effort Modal Screen — Select reasoning effort level for reasoning models (/effort).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual.screen import ModalScreen
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from jarvis.providers.models_dev import (
    get_model_effort_values,
    get_model_info,
    has_configurable_reasoning,
    is_only_thinking_model,
)
from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class EffortModal(ModalScreen[str | None]):
    """Modal dialog for selecting reasoning effort level."""

    DEFAULT_CSS = """
    EffortModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }

    #effort-dialog .modal-title-bar {
        margin-bottom: 1;
    }
    """


    def __init__(
        self,
        engine: JarvisEngine | None = None,
        available_efforts: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.dialog = ModalDialog(
            title="Reasoning Effort",
            dialog_id="effort-dialog",
            width=50,
            height=14,
            show_search=False,
            footer_text="↑↓ navigate   Enter select   Esc cancel",
        )
        self.available_efforts = available_efforts or []

    @property
    def option_list(self) -> OptionList:
        return self.dialog.option_list

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        self.populate_list()
        self.option_list.focus()

    def _get_current_effort(self) -> str:
        if self.engine and self.engine.config and self.engine.config.provider:
            if not self.engine.config.provider.thinking:
                return "none"
            return (self.engine.config.provider.reasoning_effort or "").lower()
        return ""


    def populate_list(self) -> None:
        self.option_list.clear_options()

        model_id = ""
        provider_id = ""
        if self.engine and self.engine.config and self.engine.config.provider:
            model_id = self.engine.config.provider.model
            provider_id = self.engine.config.provider.active

        efforts = list(self.available_efforts)
        if not efforts:
            efforts = get_model_effort_values(model_id, provider_id)

        if not efforts:
            # If not explicitly enumerated in models.dev, provide standard reasoning levels
            efforts = ["none", "low", "medium", "high", "max"]

        current_effort = self._get_current_effort()
        highlight_idx = 0

        for idx, effort_val in enumerate(efforts):
            is_active = (effort_val.lower() == current_effort) or (
                not current_effort and effort_val.lower() in ("medium", "high") and idx == 0
            )
            bullet = "• " if is_active else "  "
            style = "bold #3b82f6" if is_active else "white"

            t = Text(no_wrap=True)
            t.append(bullet, style="bold #3b82f6")
            t.append(effort_val.capitalize(), style=style)
            t.append(f"  ({effort_val})", style="dim #737373")

            self.option_list.add_option(Option(t, id=effort_val))
            if is_active:
                highlight_idx = idx

        if self.option_list.option_count > highlight_idx:
            self.option_list.highlighted = highlight_idx

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        selected_id = getattr(event, "option_id", None) or (
            event.option.id if getattr(event, "option", None) else None
        )
        self.dismiss(selected_id)

    def key_escape(self) -> None:
        self.dismiss(None)
