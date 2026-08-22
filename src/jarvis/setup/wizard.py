"""
JARVIS Interactive Setup & Onboarding Wizard.

Runs interactively on first startup or via ``python main.py --setup`` /
``python setup.py``. Screen clearing between steps, arrow-key navigation (↑/↓),
live typing search, and a fully dynamic models.dev catalog.

Nothing here is hardcoded: providers, models, embedding models and TTS voices are
all discovered at runtime, every credential and model is validated with a real
call before it is written, and the result is a validated
:class:`~jarvis.core.config.JarvisConfig` saved through its own schema — so new
config fields appear automatically instead of silently going missing.

Steps:
1. Assistant identity
2. Primary AI provider & API key
3. Primary AI model
4. Long-term memory extraction provider & model
5. Vector memory embedding backend (local or remote)
6. Voice provider & voice selection
7. Default user interface
8. Review & save
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from jarvis.core.config import JarvisConfig, get_jarvis_home, save_api_key_to_env
from jarvis.providers.models_dev import (
    format_env_var_label,
    get_embedding_models,
    get_provider_env_vars,
    is_provider_connected,
    load_models_dev_cache,
)
from jarvis.setup.validation import (
    CheckResult,
    check_api_key,
    check_embedding,
    check_extraction_model,
    check_local_embedding,
)

console = Console()

TOTAL_STEPS = 8

# Sentinel choice id: not a real model, so the selector hides its "(id)" suffix.
_LOCAL_EMBEDDING = "__local__"


# ═══════════════════════════════════════════════════════════════
# Terminal selector
# ═══════════════════════════════════════════════════════════════


async def interactive_select(
    title: str,
    items: list[tuple[str, str]],
    default_index: int = 0,
    max_visible: int = 10,
) -> tuple[str, str] | None:
    """Interactive list selector with ↑/↓ navigation and live filter search.

    Args:
        title: Heading shown above the list.
        items: ``(id, label)`` pairs to choose from.
        default_index: Initially highlighted row.
        max_visible: Rows visible at once.

    Returns:
        The chosen ``(id, label)`` pair, or None if cancelled with Esc.
    """
    search_query = ""
    selected_idx = default_index
    scroll_offset = 0

    def get_filtered_items() -> list[tuple[str, str]]:
        if not search_query.strip():
            return items
        q = search_query.strip().lower()
        return [it for it in items if q in it[0].lower() or q in it[1].lower()]

    def render_content() -> StyleAndTextTuples:
        nonlocal selected_idx, scroll_offset
        filtered = get_filtered_items()

        if not filtered:
            return [
                ("class:title", f"\n {title}\n\n"),
                ("class:search", f"  🔍 Search: {search_query}█\n\n"),
                ("class:dim", "  No matches found. Press Backspace to edit search.\n"),
            ]

        selected_idx = max(0, min(selected_idx, len(filtered) - 1))

        # Adjust viewport scroll window
        if selected_idx < scroll_offset:
            scroll_offset = selected_idx
        elif selected_idx >= scroll_offset + max_visible:
            scroll_offset = selected_idx - max_visible + 1

        visible = filtered[scroll_offset : scroll_offset + max_visible]

        text: StyleAndTextTuples = [
            ("class:title", f"\n {title}\n\n"),
            ("class:search", f"  🔍 Search / Filter: {search_query}█\n"),
            (
                "class:hint",
                "  [↑/↓ Navigate | Type to Filter | Backspace Delete"
                " | Enter Select | Esc Cancel]\n\n",
            ),
        ]

        for i, (item_id, item_label) in enumerate(visible):
            actual_idx = scroll_offset + i
            suffix = "" if item_id.startswith("__") else f"({item_id})"
            if actual_idx == selected_idx:
                text.append(("class:pointer", "  ❯ "))  # noqa: RUF001
                text.append(("class:selected", f"{item_label:<46} "))
                text.append(("class:dim", f"{suffix}\n"))
            else:
                text.append(("class:dim", "    "))
                text.append(("class:normal", f"{item_label:<46} "))
                text.append(("class:dim", f"{suffix}\n"))

        shown_to = min(scroll_offset + len(visible), len(filtered))
        text.append(
            (
                "class:dim",
                f"\n  Showing {scroll_offset + 1}–{shown_to} of {len(filtered)} items\n",  # noqa: RUF001
            )
        )
        return text

    kb = KeyBindings()

    @kb.add("up")
    def _(event: Any) -> None:
        nonlocal selected_idx
        if selected_idx > 0:
            selected_idx -= 1

    @kb.add("down")
    def _(event: Any) -> None:
        nonlocal selected_idx
        if selected_idx < len(get_filtered_items()) - 1:
            selected_idx += 1

    @kb.add("pageup")
    def _(event: Any) -> None:
        nonlocal selected_idx
        selected_idx = max(0, selected_idx - max_visible)

    @kb.add("pagedown")
    def _(event: Any) -> None:
        nonlocal selected_idx
        selected_idx = min(len(get_filtered_items()) - 1, selected_idx + max_visible)

    @kb.add("backspace")
    def _(event: Any) -> None:
        nonlocal search_query, selected_idx
        if bool(search_query):
            search_query = search_query[:-1]
            selected_idx = 0

    @kb.add("escape")
    def _(event: Any) -> None:
        event.app.exit(result=None)

    @kb.add("enter")
    def _(event: Any) -> None:
        filtered = get_filtered_items()
        if filtered and 0 <= selected_idx < len(filtered):
            event.app.exit(result=filtered[selected_idx])
        else:
            event.app.exit(result=None)

    @kb.add("<any>")
    def _(event: Any) -> None:
        nonlocal search_query, selected_idx
        if event.data and len(event.data) == 1 and event.data.isprintable():
            search_query += event.data
            selected_idx = 0

    style = Style.from_dict(
        {
            "title": "bold #38bdf8",
            "search": "bold #facc15",
            "hint": "italic #94a3b8",
            "pointer": "bold #38bdf8",
            "selected": "bold #4ade80",
            "normal": "#f8fafc",
            "dim": "#64748b",
        }
    )

    layout = Layout(HSplit([Window(content=FormattedTextControl(text=render_content))]))
    app: Application[tuple[str, str] | None] = Application(
        layout=layout, key_bindings=kb, style=style, full_screen=False
    )
    return await app.run_async()


# ═══════════════════════════════════════════════════════════════
# Dynamic catalog helpers
# ═══════════════════════════════════════════════════════════════


def _provider_label(pid: str, pdata: dict[str, Any], connected: bool) -> str:
    """Human label for a provider row, annotated with key state and model count."""
    name = str(pdata.get("name") or pid)
    count = len(pdata.get("models") or {})
    mark = "✓ key set" if connected else "no key"
    return f"{name}  [{mark}, {count} models]"


def _rank_providers(
    catalog: dict[str, Any],
    provider_ids: list[str] | None = None,
    prefer: str = "",
) -> list[tuple[str, str]]:
    """Rank providers for selection without any hardcoded favourites list.

    Ordering: an explicitly preferred provider first, then providers whose
    credentials are already present, then the rest by catalog breadth (model
    count) and name. This surfaces what the user can actually use today while
    staying entirely catalog-driven.

    Args:
        catalog: The models.dev catalog.
        provider_ids: Restrict to these ids (e.g. only embedding providers).
        prefer: Provider id to pin to the top.

    Returns:
        ``(provider_id, label)`` pairs in display order.
    """
    ids = provider_ids if provider_ids is not None else list(catalog)
    rows: list[tuple[int, int, str, str, str]] = []

    for pid in ids:
        pdata = catalog.get(pid) or {}
        connected = is_provider_connected(pid, pdata)
        label = _provider_label(pid, pdata, connected)
        if pid == prefer:
            label = f"{label}  ← same as primary"
        rank = 0 if pid == prefer else (1 if connected else 2)
        breadth = -len(pdata.get("models") or {})
        rows.append((rank, breadth, str(pdata.get("name") or pid).lower(), pid, label))

    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    return [(pid, label) for _, _, _, pid, label in rows]


def _model_sort_key(mid: str, minfo: dict[str, Any]) -> tuple[int, str, str]:
    """Sort models newest-first, since release date is the only ordering signal."""
    release = str(minfo.get("release_date") or "")
    # Missing dates sort last rather than pretending to be ancient or brand new.
    return (0 if release else 1, _invert_date(release), mid.lower())


def _invert_date(release: str) -> str:
    """Map an ISO date to a string that sorts descending (newest first)."""
    if not release:
        return ""
    return "".join(str(9 - int(ch)) if ch.isdigit() else ch for ch in release)


def _model_label(mid: str, minfo: dict[str, Any]) -> str:
    """Human label for a model row, with context window and release date."""
    name = str(minfo.get("name") or mid)
    bits: list[str] = []

    context = (minfo.get("limit") or {}).get("context")
    if isinstance(context, (int, float)) and context > 0:
        bits.append(f"{int(context) // 1000}k ctx")
    if minfo.get("reasoning") is True:
        bits.append("reasoning")
    if minfo.get("tool_call") is True:
        bits.append("tools")
    release = str(minfo.get("release_date") or "")
    if release:
        bits.append(release)

    return f"{name}  [{', '.join(bits)}]" if bits else name


def _model_choices(models: dict[str, Any]) -> list[tuple[str, str]]:
    """Build a ranked ``(model_id, label)`` list from a catalog model mapping."""
    entries = [
        (mid, minfo if isinstance(minfo, dict) else {})
        for mid, minfo in (models or {}).items()
    ]
    entries.sort(key=lambda pair: _model_sort_key(pair[0], pair[1]))
    return [(mid, _model_label(mid, minfo)) for mid, minfo in entries]


def _output_limit(catalog: dict[str, Any], provider_id: str, model_id: str) -> int | None:
    """Read a model's max output tokens from the catalog, if published."""
    minfo = ((catalog.get(provider_id) or {}).get("models") or {}).get(model_id)
    if not isinstance(minfo, dict):
        return None
    output = (minfo.get("limit") or {}).get("output")
    if isinstance(output, (int, float)) and output > 0:
        return int(output)
    return None


# ═══════════════════════════════════════════════════════════════
# Credential collection
# ═══════════════════════════════════════════════════════════════


async def _collect_credentials(
    provider_id: str,
    catalog: dict[str, Any],
    *,
    validate: bool = True,
) -> bool:
    """Prompt for, persist and live-validate a provider's credentials.

    Existing keys are kept unless the user chooses to replace them. Validation
    uses a free model-list request, so it costs no tokens.

    Args:
        provider_id: The models.dev provider id.
        catalog: The models.dev catalog.
        validate: Whether to verify the credentials with a live request.

    Returns:
        True if credentials are present (and valid, when validated).
    """
    pdata = catalog.get(provider_id) or {}
    pname = str(pdata.get("name") or provider_id)
    env_vars = get_provider_env_vars(provider_id, pdata, filter_synonyms=True)

    for env_var in env_vars:
        label = format_env_var_label(env_var)
        existing = os.getenv(env_var, "").strip()

        # If this env_var isn't set, check if a known synonym is already set
        if not existing and "API_KEY" in env_var.upper():
            all_synonyms = get_provider_env_vars(provider_id, pdata, filter_synonyms=False)
            for syn in all_synonyms:
                if syn != env_var and "API_KEY" in syn.upper():
                    syn_val = os.getenv(syn, "").strip()
                    if syn_val:
                        existing = syn_val
                        env_var = syn
                        label = format_env_var_label(env_var)
                        break

        if existing:
            masked = f"{existing[:4]}…{existing[-4:]}" if len(existing) > 10 else "set"
            console.print(f"[green]✓ {env_var} is already configured ({masked}).[/green]")
            if not Confirm.ask(f"Replace the existing {label}?", default=False):
                continue

        value = Prompt.ask(f"Enter your {label} ([cyan]{env_var}[/cyan])", password=True).strip()
        if value:
            save_api_key_to_env(env_var, value)
            console.print(f"[green]✓ {env_var} saved.[/green]")
        elif existing:
            console.print("[dim]Keeping the existing value.[/dim]")
        else:
            console.print(
                f"[yellow]⚠ Skipped {env_var}. Add it later with /connect"
                " or in ~/.jarvis/.env.[/yellow]"
            )

    if not is_provider_connected(provider_id, pdata):
        console.print(f"[yellow]⚠ {pname} has no usable credentials yet.[/yellow]")
        return False

    if not validate:
        return True

    console.print()
    with console.status(f"[cyan]Verifying {pname} credentials…[/cyan]"):
        result = await check_api_key(provider_id)

    _report(result)
    if not result.ok and not Confirm.ask("Continue with these credentials anyway?", default=False):
        return await _collect_credentials(provider_id, catalog, validate=validate)
    return result.ok


def _report(result: CheckResult) -> None:
    """Print a check result as a single coloured line."""
    if result.ok:
        console.print(f"[green]✓ {result.message}[/green]")
    else:
        console.print(f"[red]✗ {result.message}[/red]")


# ═══════════════════════════════════════════════════════════════
# Embedding backend selection
# ═══════════════════════════════════════════════════════════════


async def _download_local_model() -> CheckResult:
    """Download (if needed) and test the bundled local embedding model."""
    from jarvis.memory.vector.local_embedder import get_model_name, is_model_downloaded

    with contextlib.suppress(Exception):
        if is_model_downloaded():
            with console.status("[cyan]Testing the local embedding model…[/cyan]"):
                return await check_local_embedding()

    model_name = "the local embedding model"
    with contextlib.suppress(Exception):
        model_name = get_model_name()

    with Progress(
        TextColumn("[cyan]Downloading {task.description}[/cyan]"),
        BarColumn(),
        DownloadColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(model_name, total=None)

        def on_progress(downloaded: int, total: int) -> None:
            # Called from the download worker thread; rich guards its own state.
            progress.update(task, completed=downloaded, total=total or None)

        return await check_local_embedding(on_progress)


async def _choose_embedding(
    catalog: dict[str, Any],
    primary_provider_id: str,
) -> tuple[str, str, str]:
    """Choose and verify how embeddings will be produced.

    Returns:
        ``(embedding_backend, embedding_provider, embedding_model)`` ready to be
        written to the config. An empty provider and model means the bundled
        local model.
    """
    from jarvis.memory.vector.local_embedder import get_model_name, is_model_downloaded

    local_name = "all-MiniLM-L6-v2"
    with contextlib.suppress(Exception):
        local_name = get_model_name()
    downloaded = False
    with contextlib.suppress(Exception):
        downloaded = is_model_downloaded()

    embedding_providers = [
        pid for pid, pdata in catalog.items() if get_embedding_models(pid, pdata)
    ]

    local_note = "already downloaded" if downloaded else "~80 MB one-time download"
    choices = [
        (
            _LOCAL_EMBEDDING,
            f"Local — {local_name}, no API key, works offline [{local_note}] (Recommended)",
        )
    ]
    if embedding_providers:
        choices.append(
            (
                "remote",
                f"Remote provider — higher quality, needs an API key "
                f"[{len(embedding_providers)} providers available]",
            )
        )

    console.print(
        "[dim]Embeddings power semantic recall and the knowledge base. Only "
        f"{len(embedding_providers)} of the {len(catalog)} catalog providers expose an "
        "embeddings endpoint, so the bundled local model is the safe default.[/dim]\n"
    )

    choice = await interactive_select("Select Embedding Backend", choices, default_index=0)
    mode = choice[0] if choice else _LOCAL_EMBEDDING

    if mode == _LOCAL_EMBEDDING:
        if not downloaded and not Confirm.ask(
            "Download the local embedding model now?", default=True
        ):
            console.print(
                "[yellow]⚠ Deferred. It will download automatically the first time "
                "memory is used.[/yellow]"
            )
            return "local", "", ""
        result = await _download_local_model()
        _report(result)
        if not result.ok:
            console.print(
                "[yellow]⚠ Saving anyway — JARVIS will retry the download on first use.[/yellow]"
            )
        return "local", "", ""

    # ── Remote embedding provider ──
    console.clear()
    console.print("[bold yellow]Remote Embedding Provider[/bold yellow]")
    console.print("[dim]Only providers that publish embedding models are listed.[/dim]")

    provider_choice = await interactive_select(
        "Select Embedding Provider",
        _rank_providers(catalog, embedding_providers, prefer=primary_provider_id),
        default_index=0,
    )
    if not provider_choice:
        console.print("[yellow]Cancelled — using the local model instead.[/yellow]")
        return "local", "", ""

    provider_id = provider_choice[0]
    pdata = catalog.get(provider_id) or {}
    pname = str(pdata.get("name") or provider_id)

    console.clear()
    console.print(f"[bold cyan]Embedding Provider: {pname}[/bold cyan]\n")
    if not is_provider_connected(provider_id, pdata):
        await _collect_credentials(provider_id, catalog, validate=False)

    model_choice = await interactive_select(
        f"Select Embedding Model ({pname})",
        _model_choices(get_embedding_models(provider_id, pdata)),
        default_index=0,
    )
    if not model_choice:
        console.print("[yellow]Cancelled — using the local model instead.[/yellow]")
        return "local", "", ""

    model_id = model_choice[0]

    console.print()
    with console.status(f"[cyan]Testing embeddings with {model_id}…[/cyan]"):
        result = await check_embedding(provider_id, model_id)
    _report(result)

    if result.ok:
        # "auto" still degrades to local if the provider later breaks, so a
        # verified remote setup never turns into dead vector memory.
        return "auto", provider_id, model_id

    fallback = await interactive_select(
        "Embeddings failed — what now?",
        [
            (_LOCAL_EMBEDDING, "Use the bundled local model instead (Recommended)"),
            ("retry", "Pick a different provider or model"),
            ("keep", "Keep this setting anyway (falls back to local at runtime)"),
        ],
        default_index=0,
    )
    action = fallback[0] if fallback else _LOCAL_EMBEDDING

    if action == "retry":
        console.clear()
        return await _choose_embedding(catalog, primary_provider_id)
    if action == "keep":
        return "auto", provider_id, model_id

    result = await _download_local_model()
    _report(result)
    return "local", "", ""


# ═══════════════════════════════════════════════════════════════
# Voice selection
# ═══════════════════════════════════════════════════════════════


async def _edge_voice_choices() -> list[tuple[str, str]]:
    """Fetch the live Edge TTS voice list, English locales first."""
    try:
        import edge_tts

        voices = await edge_tts.list_voices()
    except Exception as e:
        console.print(f"[yellow]⚠ Could not fetch the Edge TTS voice list: {e}[/yellow]")
        return []

    rows: list[tuple[int, str, str, str]] = []
    for voice in voices:
        short = voice.get("ShortName") or ""
        if not short:
            continue
        locale = voice.get("Locale") or ""
        gender = voice.get("Gender") or ""
        friendly = (
            short.split("-")[-1]
            .replace("Neural", "")
            .replace("Multilingual", " Multilingual")
        )
        personalities = ", ".join(
            (voice.get("VoiceTag") or {}).get("VoicePersonalities") or []
        )
        detail = " · ".join(bit for bit in (gender, locale, personalities) if bit)
        # English first, then other locales alphabetically.
        rows.append((0 if locale.startswith("en-") else 1, locale, short, f"{friendly} ({detail})"))

    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    return [(short, label) for _, _, short, label in rows]


async def _elevenlabs_voice_choices() -> list[tuple[str, str]]:
    """Fetch the user's ElevenLabs voices with their API key."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        return []

    try:
        import httpx

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": api_key}
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as e:
        console.print(f"[yellow]⚠ Could not fetch ElevenLabs voices: {e}[/yellow]")
        return []

    choices: list[tuple[str, str]] = []
    for voice in payload.get("voices") or []:
        voice_id = str(voice.get("voice_id") or "")
        if not voice_id:
            continue
        labels = voice.get("labels") or {}
        detail = " · ".join(
            str(v)
            for v in (labels.get("gender"), labels.get("accent"), labels.get("description"))
            if v
        )
        name = str(voice.get("name") or voice_id)
        choices.append((voice_id, f"{name} ({detail})" if detail else name))

    return choices


async def _choose_voice(config: JarvisConfig) -> None:
    """Configure the voice subsystem in place on *config*."""
    if not Confirm.ask("Enable voice output (text-to-speech)?", default=True):
        config.voice.enabled = False
        console.print("[dim]Voice disabled. Enable it later with /voice or in jarvis.yaml.[/dim]")
        return

    config.voice.enabled = True

    provider_choice = await interactive_select(
        "Select Voice Provider",
        [
            ("edge_tts", "Edge TTS — free Microsoft neural voices, no API key (Recommended)"),
            ("elevenlabs", "ElevenLabs — ultra-realistic voices, requires an API key"),
        ],
        default_index=0,
    )
    provider = provider_choice[0] if provider_choice else "edge_tts"
    config.voice.tts.provider = provider

    if provider == "elevenlabs":
        console.clear()
        console.print("[bold yellow]ElevenLabs Configuration[/bold yellow]")
        if not os.getenv("ELEVENLABS_API_KEY", "").strip():
            key = Prompt.ask("Enter your ELEVENLABS_API_KEY", password=True).strip()
            if key:
                save_api_key_to_env("ELEVENLABS_API_KEY", key)

        with console.status("[cyan]Fetching your ElevenLabs voices…[/cyan]"):
            voices = await _elevenlabs_voice_choices()

        if voices:
            selection = await interactive_select("Select ElevenLabs Voice", voices, default_index=0)
            if selection:
                config.voice.tts.voice = selection[0]
        else:
            config.voice.tts.voice = Prompt.ask(
                "Enter an ElevenLabs Voice ID", default=config.voice.tts.voice
            ).strip() or config.voice.tts.voice
        return

    with console.status("[cyan]Fetching available Edge TTS voices…[/cyan]"):
        voices = await _edge_voice_choices()

    if not voices:
        console.print(f"[dim]Keeping the default voice '{config.voice.tts.voice}'.[/dim]")
        return

    default_index = next(
        (i for i, (vid, _) in enumerate(voices) if vid == config.voice.tts.voice), 0
    )
    selection = await interactive_select(
        "Select Voice", voices, default_index=default_index, max_visible=12
    )
    if selection:
        config.voice.tts.voice = selection[0]


# ═══════════════════════════════════════════════════════════════
# Wizard
# ═══════════════════════════════════════════════════════════════


def _header(step: int, title: str, context: str = "") -> None:
    """Clear the screen and print a step header."""
    console.clear()
    if context:
        console.print(f"[bold cyan]{context}[/bold cyan]\n")
    console.print(f"[bold yellow]Step {step}/{TOTAL_STEPS}: {title}[/bold yellow]")


async def run_setup_wizard() -> bool:
    """Run the interactive onboarding wizard.

    Returns:
        True if a configuration was written, False if the user cancelled or the
        provider catalog could not be loaded.
    """
    console.clear()
    with console.status("[cyan]Loading the models.dev provider catalog…[/cyan]"):
        catalog = load_models_dev_cache()

    if not catalog:
        console.print(
            "[red]✗ Could not load the provider catalog from models.dev.[/red]\n"
            "[dim]Check your internet connection and try again.[/dim]"
        )
        return False

    # Every default comes from the schema, so new config fields are picked up
    # automatically instead of being dropped by a hand-written template.
    config = JarvisConfig()

    # ── Step 1: Identity ──
    console.print(
        Panel.fit(
            "[bold cyan]⚡ JARVIS — First-Time Setup[/bold cyan]\n"
            f"[dim]{len(catalog)} providers loaded. Everything below is verified"
            " before it is saved.[/dim]",
            border_style="cyan",
        )
    )
    console.print()
    console.print(f"[bold yellow]Step 1/{TOTAL_STEPS}: Assistant Identity[/bold yellow]")
    assistant_name = (
        Prompt.ask("What do you want to name your assistant?", default=config.jarvis.name).strip()
        or config.jarvis.name
    )
    config.jarvis.name = assistant_name

    # ── Step 2: Primary provider ──
    _header(2, "Primary AI Provider", f"Assistant: {assistant_name}")
    console.print(
        "[dim]Providers with credentials already configured are listed first. "
        "Type to search all providers.[/dim]"
    )

    provider_choice = await interactive_select(
        "Select Primary AI Provider", _rank_providers(catalog), default_index=0
    )
    if not provider_choice:
        console.print("[yellow]Setup cancelled.[/yellow]")
        return False

    primary_provider_id = provider_choice[0]
    primary_data = catalog.get(primary_provider_id) or {}
    primary_provider_name = str(primary_data.get("name") or primary_provider_id)

    _header(
        2,
        f"API Key for {primary_provider_name}",
        f"Assistant: {assistant_name}  |  Provider: {primary_provider_name}",
    )
    console.print()
    primary_connected = await _collect_credentials(primary_provider_id, catalog)

    # ── Step 3: Primary model ──
    while True:
        _header(
            3,
            f"Primary Model for {primary_provider_name}",
            f"Assistant: {assistant_name}  |  Provider: {primary_provider_name}",
        )
        console.print("[dim]Newest models first. Type to search.[/dim]")

        model_items = _model_choices(primary_data.get("models") or {})
        if not model_items:
            console.print(
                f"[yellow]⚠ The catalog lists no models for {primary_provider_name}.[/yellow]"
            )
            manual = Prompt.ask("Enter the model id to use", default=config.provider.model).strip()
            primary_model_id = manual or config.provider.model
        else:
            model_choice = await interactive_select(
                f"Select Primary Model ({primary_provider_name})", model_items, default_index=0
            )
            if not model_choice:
                console.print("[yellow]Setup cancelled.[/yellow]")
                return False
            primary_model_id = model_choice[0]

        config.provider.active = primary_provider_id
        config.provider.model = primary_model_id
        output_limit = _output_limit(catalog, primary_provider_id, primary_model_id)
        if output_limit:
            config.provider.max_tokens = output_limit

        if primary_connected:
            console.print()
            with console.status(f"[cyan]Testing {primary_model_id}…[/cyan]"):
                result = await check_extraction_model(primary_provider_id, primary_model_id)
            _report(result)
            if not result.ok and not Confirm.ask("Keep this model anyway?", default=True):
                continue

        break

    # ── Step 4: Long-term memory ──
    _header(
        4,
        "Long-Term Memory Extraction",
        f"Primary LLM: {primary_provider_name} ({primary_model_id})",
    )
    console.print(
        "[dim]JARVIS extracts durable facts and preferences from conversations with an LLM. "
        "A small, fast model is usually the best choice here.[/dim]\n"
    )

    if Confirm.ask(
        f"Use {primary_provider_name} / {primary_model_id} for long-term memory?", default=True
    ):
        # Empty means "follow the active provider", so the pair can never drift
        # apart later if the primary provider changes.
        config.memory.long_term.provider = ""
        config.memory.long_term.model = ""
        memory_provider_id, memory_model_id = primary_provider_id, primary_model_id
    else:
        console.clear()
        console.print("[bold yellow]Long-Term Memory Provider[/bold yellow]")
        mem_choice = await interactive_select(
            "Select Memory Provider",
            _rank_providers(catalog, prefer=primary_provider_id),
            default_index=0,
        )
        memory_provider_id = mem_choice[0] if mem_choice else primary_provider_id
        mem_data = catalog.get(memory_provider_id) or {}
        mem_name = str(mem_data.get("name") or memory_provider_id)

        console.clear()
        console.print(f"[bold cyan]Memory Provider: {mem_name}[/bold cyan]\n")
        if memory_provider_id != primary_provider_id and not is_provider_connected(
            memory_provider_id, mem_data
        ):
            await _collect_credentials(memory_provider_id, catalog, validate=False)

        mem_models = _model_choices(mem_data.get("models") or {})
        mem_model_choice = (
            await interactive_select(f"Select Memory Model ({mem_name})", mem_models)
            if mem_models
            else None
        )
        memory_model_id = mem_model_choice[0] if mem_model_choice else primary_model_id

        console.print()
        with console.status(f"[cyan]Testing {memory_model_id} on {mem_name}…[/cyan]"):
            result = await check_extraction_model(memory_provider_id, memory_model_id)
        _report(result)

        if result.ok or Confirm.ask("Keep this memory model anyway?", default=False):
            config.memory.long_term.provider = memory_provider_id
            config.memory.long_term.model = memory_model_id
        else:
            console.print(
                "[yellow]⚠ Falling back to the primary model for memory extraction.[/yellow]"
            )
            config.memory.long_term.provider = ""
            config.memory.long_term.model = ""
            memory_provider_id, memory_model_id = primary_provider_id, primary_model_id

    # ── Step 5: Embeddings ──
    _header(5, "Vector / Semantic Memory Embeddings", f"Assistant: {assistant_name}")
    backend, embed_provider, embed_model = await _choose_embedding(catalog, primary_provider_id)
    config.memory.vector.embedding_backend = backend
    config.memory.vector.embedding_provider = embed_provider
    config.memory.vector.embedding_model = embed_model

    # ── Step 6: Voice ──
    _header(6, "Voice & Text-to-Speech", f"Assistant: {assistant_name}")
    console.print()
    await _choose_voice(config)

    # ── Step 7: Default UI ──
    _header(7, "Default User Interface", f"Assistant: {assistant_name}")
    console.print()
    ui_choice = await interactive_select(
        "Select Default Interface",
        [
            ("tui", "TUI — rich terminal interface with modals and split views (Recommended)"),
            ("web", "Web — browser application"),
            ("gui", "GUI — native desktop window"),
        ],
        default_index=0,
    )
    config.ui.default = ui_choice[0] if ui_choice else config.ui.default

    # ── Step 8: Review & save ──
    console.clear()
    console.print(f"[bold yellow]Step 8/{TOTAL_STEPS}: Review & Save[/bold yellow]\n")

    config_file = get_jarvis_home() / "config" / "jarvis.yaml"
    if backend == "local":
        embedding_summary = "Local bundled model (no API key)"
    else:
        embedding_summary = f"{embed_model} via {embed_provider}"

    table = Table(title=f"📋 {assistant_name} Configuration", border_style="cyan")
    table.add_column("Setting", style="bold yellow")
    table.add_column("Value", style="bold white")
    table.add_row("Assistant Name", assistant_name)
    table.add_row("Primary Provider", f"{primary_provider_name} ({primary_provider_id})")
    table.add_row("Primary Model", primary_model_id)
    table.add_row("Max Output Tokens", str(config.provider.max_tokens))
    table.add_row(
        "Memory Extraction",
        f"{memory_model_id} via {memory_provider_id}"
        + (" (follows active provider)" if not config.memory.long_term.provider else ""),
    )
    table.add_row("Embeddings", embedding_summary)
    table.add_row(
        "Voice",
        f"{config.voice.tts.provider} · {config.voice.tts.voice}"
        if config.voice.enabled
        else "disabled",
    )
    table.add_row("Default UI", config.ui.default.upper())
    table.add_row("Config File", str(config_file))
    table.add_row("Environment File", str(get_jarvis_home() / ".env"))
    console.print(table)
    console.print()

    if not Confirm.ask("Save configuration and complete setup?", default=True):
        console.print("[yellow]Setup cancelled. Nothing was written.[/yellow]")
        return False

    # Saved through the schema, so the file always matches what JARVIS can load.
    config.save(config_file)

    console.clear()
    console.print(
        Panel.fit(
            f"[bold green]🎉 {assistant_name} is ready![/bold green]\n\n"
            f"[bold white]🚀 Start {assistant_name}:[/bold white]\n"
            f"   [cyan]python main.py[/cyan]\n\n"
            f"[bold white]💬 Run a messaging bridge:[/bold white]\n"
            f"   [cyan]python main.py --connector telegram[/cyan]\n\n"
            "[bold white]🔌 Connect MCP servers (Gmail, Telegram…):[/bold white]\n"
            "   [cyan]python main.py --connect gmail[/cyan]"
            " [dim]or open /mcp inside the TUI[/dim]\n\n"
            f"[bold white]⚙️  Re-run this wizard anytime:[/bold white]\n"
            f"   [cyan]python main.py --setup[/cyan]",
            border_style="green",
        )
    )
    return True


if __name__ == "__main__":
    asyncio.run(run_setup_wizard())
