"""
API Key Modal Screen — Popup dialog for entering provider API key.
Matches openCode design: Header "API key", Input placeholder "API key", Footer "enter submit".
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.text import Text
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from jarvis.core.config import save_api_key_to_env

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class ApiKeyModal(ModalScreen[str | None]):
    """Modal popup dialog for configuring an API key for a specific provider."""

    DEFAULT_CSS = """
    ApiKeyModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }

    #api-key-card {
        width: 60;
        height: auto;
        background: $surface;
        padding: 1 2;
        border: none;
    }

    #api-key-header-row {
        layout: horizontal;
        height: 1;
        margin: 0 0 1 0;
    }

    #api-key-title {
        width: 1fr;
        color: $foreground;
        text-style: bold;
    }

    #api-key-esc {
        width: auto;
        color: $text-muted;
        text-style: dim;
    }

    #api-key-input {
        width: 1fr;
        height: 1;
        background: transparent !important;
        border: none !important;
        color: $foreground;
        margin: 0 0 1 0;
        padding: 0 !important;
    }

    #api-key-input:focus {
        background: transparent !important;
        border: none !important;
    }

    #api-key-footer {
        height: 1;
        margin: 1 0 0 0;
    }
    """

    def __init__(
        self,
        provider_id: str,
        provider_name: str,
        api_key_env: str,
        engine: JarvisEngine | None = None,
        title: str | None = None,
        placeholder: str | None = None,
        password: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.api_key_env = api_key_env
        self.engine = engine

        title_text = title if title else "API key"
        placeholder_text = placeholder if placeholder else "API key"

        self.title_widget = Static(title_text, id="api-key-title")
        self.esc_widget = Static("esc", id="api-key-esc")
        self.input_field = Input(
            placeholder=placeholder_text,
            password=password,
            id="api-key-input",
        )
        self.footer_widget = Static(self._build_footer(), id="api-key-footer")

    def _build_footer(self) -> Text:
        t = Text()
        t.append("enter ", style="bold #4f9eff")
        t.append("submit", style="dim #8ba1c0")
        return t

    def compose(self):
        with Vertical(id="api-key-card"):
            with Vertical(id="api-key-header-row"):
                yield self.title_widget
                yield self.esc_widget
            yield self.input_field
            yield self.footer_widget

    def on_mount(self) -> None:
        self.input_field.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        if val:
            try:
                save_api_key_to_env(self.api_key_env, val)
                logger.info(f"Saved API key for {self.provider_name} ({self.api_key_env})")
                self.dismiss(self.provider_id)
            except Exception as e:
                logger.error(f"Failed saving API key: {e}")
                self.dismiss(self.provider_id)
        else:
            self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
