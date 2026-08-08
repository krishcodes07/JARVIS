"""
Theme Modal Screen — Browse, search, and live preview TUI color themes (/theme).
Matches design of reference screenshot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.text import Text
from textual import on
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from jarvis.ui.tui.theme import THEME_REGISTRY, TUITheme, apply_theme, get_theme
from jarvis.ui.tui.utils import handle_search_key_navigation
from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class ThemeModal(ModalScreen[str | None]):
    """Modal dialog for searching, previewing, and switching TUI color themes."""

    DEFAULT_CSS = """
    ThemeModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }
    """

    def __init__(self, engine: JarvisEngine | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.dialog = ModalDialog(
            title="Themes",
            dialog_id="theme-dialog",
            width=58,
            height="80%",
            show_search=True,
            search_placeholder="Search",
            footer_text="↑↓ preview   Enter select   Esc cancel",
        )
        self.themes_list: list[TUITheme] = sorted(
            list(THEME_REGISTRY.values()), key=lambda t: t.id.lower()
        )
        self.current_matching_themes: list[TUITheme] = list(self.themes_list)
        self._initial_theme_id: str = "jarvis"
        self._current_preview_theme_id: str = ""

    @property
    def search_input(self) -> Input | None:
        return self.dialog.search_input

    @property
    def option_list(self) -> OptionList:
        return self.dialog.option_list

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        self._initial_theme_id = self._get_active_theme_id()
        self._current_preview_theme_id = self._initial_theme_id
        if self.search_input:
            self.search_input.focus()
        self.call_after_refresh(self.populate_list, "")

    def _get_active_theme_id(self) -> str:
        if self.engine and self.engine.config and self.engine.config.ui:
            return self.engine.config.ui.tui.theme.lower()
        if hasattr(self.app, "theme") and self.app.theme:
            return str(self.app.theme).lower()
        return "jarvis"

    def preview_highlighted_theme(self) -> None:
        """Apply theme preview corresponding to the currently highlighted OptionList item."""
        if not self.is_mounted or self.option_list.highlighted is None:
            return
        idx = self.option_list.highlighted
        if 0 <= idx < len(self.current_matching_themes):
            theme_id = self.current_matching_themes[idx].id
            if theme_id != self._current_preview_theme_id:
                self._current_preview_theme_id = theme_id
                apply_theme(self.app, theme_id)

    def on_key(self, event) -> None:
        """Delegate arrow keys and Enter from search input to option list."""
        handle_search_key_navigation(event, self.search_input, self.option_list)

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        if self.search_input and event.input == self.search_input:
            self.populate_list(filter_text=event.value)

    def populate_list(self, filter_text: str = "") -> None:
        if not self.is_mounted:
            return
        self.option_list.clear_options()

        query = (filter_text or "").strip().lower()
        active_id = self._current_preview_theme_id or self._get_active_theme_id()

        matching_themes = [
            t for t in self.themes_list
            if not query or query in t.id.lower() or query in t.display_name.lower()
        ]
        self.current_matching_themes = matching_themes

        if not matching_themes:
            empty_txt = Text("  No matching themes", style="dim #737373")
            self.option_list.add_option(Option(empty_txt, disabled=True))
            return

        active_idx = 0
        for i, theme in enumerate(matching_themes):
            is_active = (
                theme.id.lower() == active_id
                or (theme.id == "jarvis" and active_id in ("default", "jarvis", "opencode"))
            )
            if is_active:
                active_idx = i
            bullet = "● " if is_active else "  "

            item_text = "jarvis (default)" if theme.id == "jarvis" else theme.id

            t = Text(no_wrap=True, overflow="ellipsis")
            t.append(bullet, style="bold #3b82f6" if is_active else "dim #737373")
            t.append(item_text, style="bold white" if is_active else "white")

            self.option_list.add_option(Option(t, id=theme.id))

        if len(matching_themes) > 0:
            self.option_list.highlighted = active_idx

    @on(OptionList.OptionHighlighted)
    def on_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Live preview the highlighted theme on navigation."""
        self.preview_highlighted_theme()

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = self.option_list.highlighted
        if idx is not None and 0 <= idx < len(self.current_matching_themes):
            theme_obj = self.current_matching_themes[idx]
            # 1. Apply selected theme
            apply_theme(self.app, theme_obj.id)

            # 2. Persist to config & jarvis.yaml
            if self.engine and self.engine.config:
                self.engine.config.ui.tui.theme = theme_obj.id
                self.engine.config.save()

            # 3. Toast notification
            toast_fn = getattr(self.app.screen, "show_toast", None)
            if toast_fn:
                toast_fn(
                    f"Switched TUI theme to: {theme_obj.display_name}",
                    title="Theme Switched",
                    style="success",
                )

            self.dismiss(theme_obj.id)
            return

        self.dismiss(None)

    def key_escape(self) -> None:
        """Revert back to the initial theme on cancel."""
        if self._initial_theme_id:
            apply_theme(self.app, self._initial_theme_id)
        self.dismiss(None)
