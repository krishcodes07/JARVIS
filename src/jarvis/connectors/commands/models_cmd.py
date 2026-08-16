"""
Models Command — Dynamic model and provider management (/models, /model).
Allows browsing connected providers, inspecting available models, and switching models at runtime.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from jarvis.connectors.commands.models import BaseCommand, CommandContext

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ModelCommand(BaseCommand):
    """Command to browse providers, list models, and switch the active model."""

    name: str = "model"
    aliases: list[str] = ["models", "m"]
    description: str = "View connected providers, list models, or switch the active model."
    usage: str = "/model [list [provider] | <model_name> | switch <provider> [model]]"
    category: str = "Models"

    async def execute(self, ctx: CommandContext) -> str:
        """Handle /model command execution."""
        pm = ctx.engine.provider_manager
        config = ctx.engine.config
        if not pm or not config:
            return "⚠️ Provider manager or engine configuration is not available."

        active_provider = config.provider.active
        active_model = ctx.engine.last_used_model or config.provider.model
        args = ctx.args

        # 1. No args -> Show active model + connected providers summary
        if not args:
            connected = pm.registry.list_connected()
            if not connected:
                return (
                    f"🤖 **Active Model:** `{active_model}` (Provider: `{active_provider}`)\n\n"
                    "⚠️ No other connected providers found with valid API keys.\n"
                    "Configure API keys in `.env` or `jarvis.yaml`."
                )

            lines = [
                f"🤖 **Current Active Model**: `{active_model}`\n"
                f"⚡ **Active Provider**: `{active_provider}`\n",
                "🔌 **Connected Providers**:\n",
            ]

            for p in connected:
                is_active = p.name.lower() == active_provider.lower()
                marker = "🔹 **[Active]**" if is_active else "🟢"
                models_count = len(p.models) if p.models else 1
                lines.append(
                    f"{marker} **{p.display_name or p.name.title()}** (`{p.name}`)\n"
                    f"   • Default Model: `{p.default_model or 'N/A'}`\n"
                    f"   • Available Models: {models_count}\n"
                )

            lines.append(
                "────────────────\n"
                "💡 **Commands**:\n"
                "• View provider models: `/model list <provider>`\n"
                "• Switch active model: `/model <model_name>`\n"
                "• Switch provider: `/model switch <provider> [model]`"
            )
            return "\n".join(lines)

        subcmd = args[0].lower()

        # 2. Subcommand: 'list' or 'ls'
        if subcmd in ("list", "ls"):
            target_prov = args[1].lower() if len(args) > 1 else active_provider
            return await self._render_provider_models(pm, target_prov, active_model)

        # 3. Subcommand: 'switch' -> /models switch <provider> [model]
        if subcmd == "switch":
            if len(args) < 2:
                return "⚠️ **Usage**: `/models switch <provider_name> [model_name]`"
            target_prov = args[1].lower()
            target_model = args[2] if len(args) > 2 else ""
            return await self._switch_provider_and_model(ctx, target_prov, target_model)

        # 4. Check if args[0] is a known provider name (e.g. /models anthropic)
        if subcmd in pm.registry:
            if len(args) > 1:
                # /models openai gpt-4o -> switch
                return await self._switch_provider_and_model(ctx, subcmd, args[1])
            # Just provider name -> list its models
            return await self._render_provider_models(pm, subcmd, active_model)

        # 5. Direct model switch (e.g. /models gpt-4o or /models claude-3-5-sonnet)
        target_model_name = args[0]
        return await self._switch_model_auto(ctx, target_model_name)

    async def _render_provider_models(self, pm: Any, provider_name: str, active_model: str) -> str:
        """Render markdown list of models for a specific provider."""
        try:
            pdef = pm.registry.get(provider_name)
        except Exception:
            connected_names = ", ".join(f"`{p.name}`" for p in pm.registry.list_connected())
            return (
                f"⚠️ Provider `{provider_name}` not found in registry.\n\n"
                f"Available connected providers: {connected_names}"
            )

        models = await pm.get_models(provider_name)
        if not models and pdef.models:
            models = [
                {"id": mid, "name": mdata.get("name", mid) if isinstance(mdata, dict) else str(mdata)}
                for mid, mdata in pdef.models.items()
            ]

        if not models:
            return (
                f"📁 **Provider**: `{pdef.display_name or provider_name}`\n"
                f"Default Model: `{pdef.default_model or 'N/A'}`\n\n"
                f"No specific model catalog entries found. You can set any model using:\n"
                f"`/model switch {provider_name} <model_name>`"
            )

        lines = [
            f"📁 **Available Models for {pdef.display_name or provider_name.title()}** (`{provider_name}`):\n"
        ]

        for m in models:
            mid = m["id"]
            mname = m.get("name") or mid
            is_cur = mid.lower() == active_model.lower()
            marker = "🔹 **[Active]**" if is_cur else "•"
            lines.append(f"{marker} `{mid}` — {mname}")

        lines.append(
            "\n────────────────\n"
            f"💡 *To switch to one of these models:* `/model {models[0]['id']}`"
        )
        return "\n".join(lines)

    async def _switch_provider_and_model(
        self, ctx: CommandContext, provider_name: str, model_name: str = ""
    ) -> str:
        """Switch both provider and model."""
        pm = ctx.engine.provider_manager
        config = ctx.engine.config
        if not pm or not config:
            return "⚠️ Provider manager or engine configuration is not available."

        try:
            pdef = pm.registry.get(provider_name)
        except Exception:
            return f"⚠️ Provider `{provider_name}` is not registered."

        if not pdef.is_connected:
            return (
                f"⚠️ Provider `{provider_name}` is missing its API key (`{pdef.api_key_env}`).\n"
                "Please configure the key in your environment or configuration."
            )

        try:
            await pm.switch_provider(provider_name)
            config.provider.active = provider_name

            chosen_model = model_name or pdef.default_model or config.provider.model
            config.provider.model = chosen_model

            return (
                f"✅ **Provider & Model Switched Successfully**\n\n"
                f"• **Active Provider:** `{provider_name}` ({pdef.display_name or provider_name.title()})\n"
                f"• **Active Model:** `{chosen_model}`\n"
                f"• **Protocol:** `{pdef.protocol}`"
            )
        except Exception as e:
            logger.error(f"Failed to switch provider to {provider_name}: {e}", exc_info=True)
            return f"⚠️ Failed to switch provider to `{provider_name}`: {e}"

    async def _switch_model_auto(self, ctx: CommandContext, model_name: str) -> str:
        """Auto-detect provider for a model or switch model on active provider."""
        pm = ctx.engine.provider_manager
        config = ctx.engine.config
        if not pm or not config:
            return "⚠️ Provider manager or engine configuration is not available."

        active_prov = config.provider.active

        # 1. Search connected providers to see if this model belongs to any
        for p in pm.registry.list_connected():
            if p.models and (model_name in p.models or any(m.lower() == model_name.lower() for m in p.models)):
                if p.name.lower() != active_prov.lower():
                    # Switch provider first
                    await pm.switch_provider(p.name)
                    config.provider.active = p.name
                config.provider.model = model_name
                return (
                    f"✅ **Model Switched to: `{model_name}`**\n\n"
                    f"• **Provider:** `{p.name}` ({p.display_name or p.name.title()})\n"
                    f"• **Status:** Active & Ready"
                )

        # 2. Fallback: switch model directly on current active provider
        config.provider.model = model_name
        return (
            f"✅ **Model Switched to: `{model_name}`**\n\n"
            f"• **Provider:** `{active_prov}`\n"
            f"• **Status:** Active & Ready"
        )
