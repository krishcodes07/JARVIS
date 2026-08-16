"""
TUI Theme & Styling — Themes system for the JARVIS Terminal UI.
Supports opencode, dark, pink-city, palenight, one-dark, nord, monokai, nightowl,
osaka-jade, mercury, orng, dracula, gruvbox, solarized-dark, catppuccin-mocha,
tokyo-night, everforest, rose-pine, ayu-dark.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.app import App

logger = logging.getLogger(__name__)


@dataclass
class TUITheme:
    """TUI Theme definition holding color tokens."""

    id: str
    display_name: str
    description: str
    bg_color: str          # Main background
    card_bg: str           # User message / prompt box / card background
    text_color: str        # Text color
    dim_color: str         # Dim text color
    accent_primary: str    # Main accent color
    accent_secondary: str  # Secondary accent color
    user_border: str       # User card accent border
    prompt_border: str     # Prompt box accent border
    highlight_bg: str      # OptionList highlighted option background
    highlight_fg: str      # OptionList highlighted option text color
    logo_color: str        # Header ASCII logo style string


THEME_REGISTRY: dict[str, TUITheme] = {
    "jarvis": TUITheme(
        id="jarvis",
        display_name="jarvis (default)",
        description="Default JARVIS dark theme with blue & orange accents",
        bg_color="#000000",
        card_bg="#1e1e1e",
        text_color="#ffffff",
        dim_color="#737373",
        accent_primary="#3b82f6",
        accent_secondary="#f97316",
        user_border="#3b82f6",
        prompt_border="#3b82f6",
        highlight_bg="#2b2b2b",
        highlight_fg="#3b82f6",
        logo_color="bold #60a5fa",
    ),
    "dark": TUITheme(
        id="dark",
        display_name="Classic Dark",
        description="Minimalist deep charcoal theme with indigo accents",
        bg_color="#0f0f10",
        card_bg="#1a1a1c",
        text_color="#f1f1f5",
        dim_color="#6c6c7c",
        accent_primary="#6366f1",
        accent_secondary="#ec4899",
        user_border="#6366f1",
        prompt_border="#6366f1",
        highlight_bg="#272730",
        highlight_fg="#818cf8",
        logo_color="bold #818cf8",
    ),
    "pink-city": TUITheme(
        id="pink-city",
        display_name="Pink City",
        description="Neon pink & magenta cyberpunk theme",
        bg_color="#120914",
        card_bg="#1e1122",
        text_color="#fdf2f8",
        dim_color="#a27b9b",
        accent_primary="#ec4899",
        accent_secondary="#f43f5e",
        user_border="#ec4899",
        prompt_border="#f43f5e",
        highlight_bg="#331638",
        highlight_fg="#f472b6",
        logo_color="bold #f472b6",
    ),
    "palenight": TUITheme(
        id="palenight",
        display_name="Palenight",
        description="Material Palenight violet slate theme",
        bg_color="#1b1e2b",
        card_bg="#232837",
        text_color="#a6accd",
        dim_color="#676e95",
        accent_primary="#c792ea",
        accent_secondary="#82aaff",
        user_border="#c792ea",
        prompt_border="#82aaff",
        highlight_bg="#2d3345",
        highlight_fg="#c792ea",
        logo_color="bold #c792ea",
    ),
    "one-dark": TUITheme(
        id="one-dark",
        display_name="One Dark",
        description="Atom One Dark charcoal & cyan theme",
        bg_color="#1e222a",
        card_bg="#252b37",
        text_color="#abb2bf",
        dim_color="#5c6370",
        accent_primary="#61afef",
        accent_secondary="#98c379",
        user_border="#61afef",
        prompt_border="#61afef",
        highlight_bg="#2c3240",
        highlight_fg="#61afef",
        logo_color="bold #61afef",
    ),
    "nord": TUITheme(
        id="nord",
        display_name="Nord",
        description="Nordic arctic frost cyan theme",
        bg_color="#2e3440",
        card_bg="#3b4252",
        text_color="#eceff4",
        dim_color="#7b88a1",
        accent_primary="#88c0d0",
        accent_secondary="#81a1c1",
        user_border="#88c0d0",
        prompt_border="#88c0d0",
        highlight_bg="#434c5e",
        highlight_fg="#88c0d0",
        logo_color="bold #88c0d0",
    ),
    "monokai": TUITheme(
        id="monokai",
        display_name="Monokai",
        description="Classic Monokai warm magenta & green contrast theme",
        bg_color="#1e1f1c",
        card_bg="#272822",
        text_color="#f8f8f2",
        dim_color="#75715e",
        accent_primary="#f92672",
        accent_secondary="#a6e22e",
        user_border="#f92672",
        prompt_border="#f92672",
        highlight_bg="#3e3d32",
        highlight_fg="#f92672",
        logo_color="bold #f92672",
    ),
    "nightowl": TUITheme(
        id="nightowl",
        display_name="Night Owl",
        description="Night Owl midnight blue & amber theme",
        bg_color="#011627",
        card_bg="#0b253a",
        text_color="#d6deeb",
        dim_color="#5f7e97",
        accent_primary="#82aaff",
        accent_secondary="#ecc48d",
        user_border="#82aaff",
        prompt_border="#ecc48d",
        highlight_bg="#133451",
        highlight_fg="#82aaff",
        logo_color="bold #82aaff",
    ),
    "osaka-jade": TUITheme(
        id="osaka-jade",
        display_name="Osaka Jade",
        description="Tokyo / Osaka deep emerald jade theme",
        bg_color="#081412",
        card_bg="#102320",
        text_color="#ecfdf5",
        dim_color="#4a7a72",
        accent_primary="#10b981",
        accent_secondary="#34d399",
        user_border="#10b981",
        prompt_border="#10b981",
        highlight_bg="#173631",
        highlight_fg="#34d399",
        logo_color="bold #34d399",
    ),
    "mercury": TUITheme(
        id="mercury",
        display_name="Mercury",
        description="Sleek silver platinum monochrome theme",
        bg_color="#111115",
        card_bg="#1a1a22",
        text_color="#f8fafc",
        dim_color="#64748b",
        accent_primary="#e2e8f0",
        accent_secondary="#38bdf8",
        user_border="#94a3b8",
        prompt_border="#e2e8f0",
        highlight_bg="#282936",
        highlight_fg="#38bdf8",
        logo_color="bold #e2e8f0",
    ),
    "orng": TUITheme(
        id="orng",
        display_name="Orng",
        description="Electric orange & amber warmth theme",
        bg_color="#140c08",
        card_bg="#221610",
        text_color="#fff7ed",
        dim_color="#9a6c53",
        accent_primary="#ff6b00",
        accent_secondary="#f59e0b",
        user_border="#ff6b00",
        prompt_border="#ff6b00",
        highlight_bg="#362116",
        highlight_fg="#ff6b00",
        logo_color="bold #ff6b00",
    ),
    "dracula": TUITheme(
        id="dracula",
        display_name="Dracula",
        description="Classic Dracula purple & pink vampire theme",
        bg_color="#282a36",
        card_bg="#343746",
        text_color="#f8f8f2",
        dim_color="#6272a4",
        accent_primary="#bd93f9",
        accent_secondary="#ff79c6",
        user_border="#bd93f9",
        prompt_border="#ff79c6",
        highlight_bg="#44475a",
        highlight_fg="#bd93f9",
        logo_color="bold #bd93f9",
    ),
    "gruvbox": TUITheme(
        id="gruvbox",
        display_name="Gruvbox Dark",
        description="Retro warm gruvbox theme with orange & green accents",
        bg_color="#282828",
        card_bg="#3c3836",
        text_color="#ebdbb2",
        dim_color="#928374",
        accent_primary="#fe8019",
        accent_secondary="#b8bb26",
        user_border="#fe8019",
        prompt_border="#fabd2f",
        highlight_bg="#504945",
        highlight_fg="#fe8019",
        logo_color="bold #fabd2f",
    ),
    "solarized-dark": TUITheme(
        id="solarized-dark",
        display_name="Solarized Dark",
        description="Low-contrast Solarized theme with blue & cyan accents",
        bg_color="#002b36",
        card_bg="#073642",
        text_color="#839496",
        dim_color="#586e75",
        accent_primary="#268bd2",
        accent_secondary="#2aa198",
        user_border="#268bd2",
        prompt_border="#2aa198",
        highlight_bg="#0d4a58",
        highlight_fg="#268bd2",
        logo_color="bold #268bd2",
    ),
    "catppuccin-mocha": TUITheme(
        id="catppuccin-mocha",
        display_name="Catppuccin Mocha",
        description="Soft pastel Catppuccin Mocha theme with mauve & pink accents",
        bg_color="#1e1e2e",
        card_bg="#313244",
        text_color="#cdd6f4",
        dim_color="#6c7086",
        accent_primary="#cba6f7",
        accent_secondary="#f5c2e7",
        user_border="#cba6f7",
        prompt_border="#89b4fa",
        highlight_bg="#45475a",
        highlight_fg="#cba6f7",
        logo_color="bold #cba6f7",
    ),
    "tokyo-night": TUITheme(
        id="tokyo-night",
        display_name="Tokyo Night",
        description="Moody Tokyo Night theme with blue & purple accents",
        bg_color="#1a1b26",
        card_bg="#24283b",
        text_color="#c0caf5",
        dim_color="#565f89",
        accent_primary="#7aa2f7",
        accent_secondary="#bb9af7",
        user_border="#7aa2f7",
        prompt_border="#bb9af7",
        highlight_bg="#292e42",
        highlight_fg="#7aa2f7",
        logo_color="bold #7aa2f7",
    ),
    "everforest": TUITheme(
        id="everforest",
        display_name="Everforest",
        description="Warm forest-green Everforest theme",
        bg_color="#2d353b",
        card_bg="#343f44",
        text_color="#d3c6aa",
        dim_color="#7a8478",
        accent_primary="#a7c080",
        accent_secondary="#e69875",
        user_border="#a7c080",
        prompt_border="#e69875",
        highlight_bg="#3d484d",
        highlight_fg="#a7c080",
        logo_color="bold #a7c080",
    ),
    "rose-pine": TUITheme(
        id="rose-pine",
        display_name="Rosé Pine",
        description="Elegant Rosé Pine theme with rose & foam accents",
        bg_color="#191724",
        card_bg="#1f1d2e",
        text_color="#e0def4",
        dim_color="#6e6a86",
        accent_primary="#eb6f92",
        accent_secondary="#9ccfd8",
        user_border="#eb6f92",
        prompt_border="#9ccfd8",
        highlight_bg="#26233a",
        highlight_fg="#eb6f92",
        logo_color="bold #eb6f92",
    ),
    "ayu-dark": TUITheme(
        id="ayu-dark",
        display_name="Ayu Dark",
        description="Sleek Ayu Dark theme with amber & sky-blue accents",
        bg_color="#0a0e14",
        card_bg="#131721",
        text_color="#b3b1ad",
        dim_color="#4d5566",
        accent_primary="#ffb454",
        accent_secondary="#59c2ff",
        user_border="#ffb454",
        prompt_border="#59c2ff",
        highlight_bg="#1f2430",
        highlight_fg="#ffb454",
        logo_color="bold #ffb454",
    ),
    "synthwave84": TUITheme(
        id="synthwave84",
        display_name="Synthwave '84",
        description="Retro neon synthwave theme with hot pink & cyan glow",
        bg_color="#241b2f",
        card_bg="#2a2139",
        text_color="#f8f8f2",
        dim_color="#848bbd",
        accent_primary="#ff7edb",
        accent_secondary="#36f9f6",
        user_border="#ff7edb",
        prompt_border="#36f9f6",
        highlight_bg="#34294f",
        highlight_fg="#ff7edb",
        logo_color="bold #ff7edb",
    ),
    "cobalt2": TUITheme(
        id="cobalt2",
        display_name="Cobalt2",
        description="Deep blue Cobalt2 theme with bright yellow accents",
        bg_color="#193549",
        card_bg="#1f4662",
        text_color="#ffffff",
        dim_color="#5a7a94",
        accent_primary="#ffc600",
        accent_secondary="#0088ff",
        user_border="#ffc600",
        prompt_border="#0088ff",
        highlight_bg="#254b6d",
        highlight_fg="#ffc600",
        logo_color="bold #ffc600",
    ),
    "kanagawa": TUITheme(
        id="kanagawa",
        display_name="Kanagawa",
        description="Muted Japanese ukiyo-e inspired theme with wave blues",
        bg_color="#1f1f28",
        card_bg="#2a2a37",
        text_color="#dcd7ba",
        dim_color="#727169",
        accent_primary="#7e9cd8",
        accent_secondary="#e46876",
        user_border="#7e9cd8",
        prompt_border="#957fb8",
        highlight_bg="#363646",
        highlight_fg="#7e9cd8",
        logo_color="bold #7e9cd8",
    ),
    "horizon": TUITheme(
        id="horizon",
        display_name="Horizon",
        description="Warm sunset Horizon theme with coral & rose accents",
        bg_color="#1c1e26",
        card_bg="#232530",
        text_color="#e0e0e0",
        dim_color="#6c6f93",
        accent_primary="#e95678",
        accent_secondary="#fab795",
        user_border="#e95678",
        prompt_border="#fab795",
        highlight_bg="#2e303e",
        highlight_fg="#e95678",
        logo_color="bold #e95678",
    ),
    "oxocarbon": TUITheme(
        id="oxocarbon",
        display_name="Oxocarbon",
        description="IBM Carbon-inspired theme with magenta & mint accents",
        bg_color="#161616",
        card_bg="#212121",
        text_color="#f2f4f8",
        dim_color="#6f6f6f",
        accent_primary="#be95ff",
        accent_secondary="#3ddbd9",
        user_border="#be95ff",
        prompt_border="#3ddbd9",
        highlight_bg="#292929",
        highlight_fg="#be95ff",
        logo_color="bold #be95ff",
    ),
    "iceberg": TUITheme(
        id="iceberg",
        display_name="Iceberg",
        description="Cool muted blue Iceberg theme",
        bg_color="#161821",
        card_bg="#1e2132",
        text_color="#c6c8d1",
        dim_color="#6b7089",
        accent_primary="#84a0c6",
        accent_secondary="#a093c7",
        user_border="#84a0c6",
        prompt_border="#a093c7",
        highlight_bg="#272c42",
        highlight_fg="#84a0c6",
        logo_color="bold #84a0c6",
    ),
    "vesper": TUITheme(
        id="vesper",
        display_name="Vesper",
        description="Minimal near-black theme with a single warm amber accent",
        bg_color="#101010",
        card_bg="#1c1c1c",
        text_color="#ffffff",
        dim_color="#8a8a8d",
        accent_primary="#ffc799",
        accent_secondary="#e6b673",
        user_border="#ffc799",
        prompt_border="#ffc799",
        highlight_bg="#282828",
        highlight_fg="#ffc799",
        logo_color="bold #ffc799",
    ),
    "andromeda": TUITheme(
        id="andromeda",
        display_name="Andromeda",
        description="Vivid dark theme with electric green & purple accents",
        bg_color="#23262e",
        card_bg="#2e323b",
        text_color="#d5ced9",
        dim_color="#7f8490",
        accent_primary="#00e8c6",
        accent_secondary="#c74ded",
        user_border="#00e8c6",
        prompt_border="#c74ded",
        highlight_bg="#3a3f4b",
        highlight_fg="#00e8c6",
        logo_color="bold #00e8c6",
    ),
    "melange": TUITheme(
        id="melange",
        display_name="Melange",
        description="Warm earthy low-contrast theme with sandy tones",
        bg_color="#292522",
        card_bg="#34302c",
        text_color="#ece1d7",
        dim_color="#8a8580",
        accent_primary="#c77b62",
        accent_secondary="#82a29f",
        user_border="#c77b62",
        prompt_border="#82a29f",
        highlight_bg="#403a34",
        highlight_fg="#c77b62",
        logo_color="bold #c77b62",
    ),
    "solarized-light": TUITheme(
        id="solarized-light",
        display_name="Solarized Light",
        description="Low-contrast Solarized theme, light variant with blue & cyan accents",
        bg_color="#fdf6e3",
        card_bg="#eee8d5",
        text_color="#586e75",
        dim_color="#93a1a1",
        accent_primary="#268bd2",
        accent_secondary="#2aa198",
        user_border="#268bd2",
        prompt_border="#2aa198",
        highlight_bg="#e5dfc5",
        highlight_fg="#268bd2",
        logo_color="bold #268bd2",
    ),
}


def get_theme(theme_id: str | None) -> TUITheme:
    """Find registered TUITheme by id (case-insensitive). Defaults to 'jarvis'."""
    if not theme_id:
        return THEME_REGISTRY["jarvis"]
    clean = theme_id.strip().lower()
    if clean in ("default", "jarvis", "opencode"):
        return THEME_REGISTRY["jarvis"]
    return THEME_REGISTRY.get(clean, THEME_REGISTRY["jarvis"])


def register_all_themes(app: App) -> None:
    """Register all defined TUI themes with Textual app using native theme colors."""
    from textual.theme import Theme
    for theme_id, theme in THEME_REGISTRY.items():
        t_theme = Theme(
            name=theme.id,
            primary=theme.accent_primary,
            secondary=theme.accent_secondary,
            accent=theme.user_border or theme.accent_primary,
            foreground=theme.text_color,
            background=theme.bg_color,
            surface=theme.card_bg,
            panel=theme.card_bg,
            dark=True,
        )
        with contextlib.suppress(Exception):
            app.register_theme(t_theme)


JARVIS_CSS = """
Screen, MainScreen {
    background: $background;
    color: $foreground;
    layout: vertical;
}

/* ─── Header ─── */
#header-container {
    height: 1fr;
    content-align: center middle;
    align: center middle;
    margin: 0;
    padding: 0;
}

#header-container.hidden {
    display: none;
}

/* ─── Chat Scroll Area ─── */
#chat-scroll, ChatViewWidget {
    height: 1fr;
    border: none;
    padding: 1 1 1 1;
    overflow-y: auto;
    scrollbar-size-vertical: 0;
    scrollbar-size-horizontal: 0;
    background: $background;
}

/* User message card ─── */
.chat-message-user {
    background: $surface;
    color: $foreground;
    padding: 1 2;
    margin: 1 0 1 0;
    border-left: tall $primary;
}

/* Assistant message ─── */
.chat-message-jarvis {
    color: $foreground;
    padding: 0 2;
    margin: 1 0 0 0;
}

.assistant-footer-badge {
    color: $text-muted;
    padding: 0 2;
    margin: 0 0 1 0;
    text-style: dim;
}

.chat-thought-block {
    color: $secondary;
    text-style: bold;
    padding: 0 2;
    margin: 1 0 0 0;
}

/* ─── Thought Widget ─── */
ThoughtWidget {
    height: auto;
    margin: 0 0 0 2;
    padding: 0;
}

.thought-header {
    color: #d97706;
    height: 1;
}

.thought-header:hover {
    color: #fbbf24;
    text-style: underline;
}

.thought-content-block {
    color: #a3a3a3;
    padding: 0 0 0 2;
    margin: 0;
    display: none;
}

.thought-content-block.expanded {
    display: block;
}

/* ─── Tool Call Widget ─── */
ToolCallWidget {
    height: auto;
    margin: 0 0 0 2;
    padding: 0;
}

.tool-header {
    color: #a3a3a3;
    height: 1;
}

.tool-header:hover {
    color: #ffffff;
    text-style: underline;
}

.tool-output-block {
    color: #737373;
    padding: 0 0 0 2;
    margin: 0;
    display: none;
}

.tool-output-block.expanded {
    display: block;
}

.chat-tool-command {
    background: $surface;
    color: $foreground;
    padding: 1 2;
    margin: 1 0 0 0;
    border-left: tall $secondary;
}

.chat-tool-output {
    color: $text-muted;
    padding: 0 2;
    margin: 0 0 0 1;
    text-style: italic;
}

.chat-error-message {
    background: #2d1a1a;
    color: #ff9999;
    padding: 1 2;
    margin: 1 0 1 0;
    border-left: tall #ef4444;
}

/* ─── Modals ─── */
ModalScreen {
    align: center middle;
    background: rgba(0, 0, 0, 0.55);
}

ModalDialog {
    background: $surface;
}

/* ─── Command Popover ─── */
#command-popover {
    margin: 0 4 0 4;
    padding: 0 1;
    background: $surface;
    border-left: tall $primary;
    height: auto;
    display: none;
}

#command-popover.visible {
    display: block;
}

#popover-option-list {
    background: transparent;
    border: none;
    max-height: 8;
    padding: 0;
}

PromptBoxWidget {
    background: $surface;
    border: none;
    border-left: tall $primary;
    height: auto;
    margin: 0 1 0 1;
    padding: 1 2 1 2;
}

StatusBarWidget {
    height: 1;
    background: $background;
    color: $text-muted;
    border: none;
    margin: 0 1 1 1;
    padding: 0;
}

.modal-list-container {
    height: 1fr;
    min-height: 6;
    background: transparent;
}

.modal-list {
    height: 1fr;
    min-height: 6;
    background: transparent;
    border: none;
}

OptionList > .option-list--option {
    padding: 0 1;
    margin: 0;
}

OptionList > .option-list--option-highlighted {
    background: $primary 20%;
    color: $foreground;
    text-style: bold;
}
"""


def get_theme_css(theme_id: str | None = "jarvis") -> str:
    """Return default JARVIS theme CSS stylesheet."""
    return JARVIS_CSS


def apply_theme(app: App, theme_id: str) -> bool:
    """Dynamically switch and apply theme to a running Textual App."""
    theme = get_theme(theme_id)
    try:
        if not getattr(app, "_jarvis_themes_registered", False):
            register_all_themes(app)
            setattr(app, "_jarvis_themes_registered", True)

        app.theme = theme.id
        return True
    except Exception as e:
        logger.warning(f"Could not apply TUI theme '{theme_id}': {e}")
        return False