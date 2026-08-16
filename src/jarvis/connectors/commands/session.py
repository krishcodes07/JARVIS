"""
Session Commands — Modular bot commands for managing multi-turn conversation sessions.
"""

from __future__ import annotations

import uuid

from jarvis.connectors.commands.models import BaseCommand, CommandContext


class SessionCommand(BaseCommand):
    """Command to list, switch, create, and delete conversation sessions."""

    name: str = "session"
    aliases: list[str] = ["sessions", "s"]
    description: str = "Manage conversation sessions (list, switch, create, delete)."
    usage: str = "/session [list | <id> | load <id> | new [name] | delete <id>]"
    category: str = "Session"

    async def execute(self, ctx: CommandContext) -> str:
        """Handle /session command routing."""
        chat_id = ctx.chat_id
        active_id = ctx.connector.get_session_id(chat_id)
        args = ctx.args
        memory_mgr = ctx.engine.memory_manager

        if not memory_mgr or not memory_mgr.conversation:
            return "⚠️ Conversation memory is currently disabled in JARVIS configuration."

        store = memory_mgr.conversation
        prefix = f"{ctx.connector.name}_{chat_id}"

        # 1. No arguments or 'list' -> List all sessions for this chat
        if not args or args[0].lower() in ("list", "ls", "all"):
            sessions = await store.list_sessions_info(prefix=prefix)
            if not sessions:
                # Ensure active session file exists and display it
                await store.create_session(active_id)
                return (
                    f"📁 **Active Session:** `{active_id}` *(Empty)*\n\n"
                    f"💡 *Start chatting to save messages, or create a new session with* `/new`."
                )

            lines = ["📁 **Your Conversation Sessions**:\n"]
            for s in sessions:
                sid = s["session_id"]
                is_active = sid == active_id
                marker = "🔹 **[Active]**" if is_active else "📄"
                count = s.get("message_count", 0)
                title = s.get("title", "(Empty session)")
                lines.append(f"{marker} `{sid}`\n   • **Preview:** {title}\n   • **Messages:** {count}\n")

            lines.append(
                "────────────────\n"
                "💡 **Commands**:\n"
                "• Switch session: `/session <id>`\n"
                "• Start new session: `/new` or `/session new [name]`\n"
                "• Delete a session: `/session delete <id>`\n"
                "• Clear/reset to new session: `/clear`"
            )
            return "\n".join(lines)

        subcmd = args[0].lower()

        # 2. Subcommand: 'new' or 'create'
        if subcmd in ("new", "create", "start"):
            custom_name = args[1].strip() if len(args) > 1 else ""
            if custom_name:
                clean_name = "".join(c for c in custom_name if c.isalnum() or c in ("-", "_"))
                new_session_id = f"{prefix}_{clean_name}"
            else:
                new_session_id = f"{prefix}_{uuid.uuid4().hex[:6]}"

            ctx.connector.set_session_id(chat_id, new_session_id)
            await store.create_session(new_session_id)
            return (
                f"✨ **New Session Created**\n\n"
                f"• **Active Session:** `{new_session_id}`\n"
                f"• **Storage File:** `{new_session_id}.json`\n\n"
                f"Previous sessions are preserved and accessible via `/session`."
            )

        # 3. Subcommand: 'delete', 'del', 'remove', 'rm'
        if subcmd in ("delete", "del", "remove", "rm"):
            if len(args) < 2:
                return "⚠️ **Usage**: `/session delete <session_id>`"

            target_id = args[1].strip()
            # If user typed just suffix, resolve to full prefix_suffix
            if not target_id.startswith(prefix) and not target_id.startswith(f"{ctx.connector.name}_"):
                resolved_id = f"{prefix}_{target_id}"
            else:
                resolved_id = target_id

            await store.delete(resolved_id)

            # If the deleted session was currently active, switch to a fresh new session
            if resolved_id == active_id:
                new_session_id = f"{prefix}_{uuid.uuid4().hex[:6]}"
                ctx.connector.set_session_id(chat_id, new_session_id)
                await store.create_session(new_session_id)
                return (
                    f"🗑️ **Session Deleted**: `{resolved_id}`\n"
                    f"Activated fresh new session: `{new_session_id}`"
                )

            return f"🗑️ **Session Deleted**: `{resolved_id}`"

        # 4. Subcommand: 'load' or direct session ID
        target_id = args[1].strip() if subcmd == "load" and len(args) > 1 else args[0].strip()
        if not target_id.startswith(prefix) and not target_id.startswith(f"{ctx.connector.name}_"):
            resolved_id = f"{prefix}_{target_id}"
        else:
            resolved_id = target_id

        ctx.connector.set_session_id(chat_id, resolved_id)
        await store.create_session(resolved_id)
        msgs = await store.retrieve(resolved_id)
        msg_count = len(msgs)

        return (
            f"✅ **Active Session Switched**\n\n"
            f"• **Active Session:** `{resolved_id}`\n"
            f"• **Loaded Messages:** **{msg_count}**\n\n"
            f"You can continue the conversation where you left off!"
        )


class NewSessionCommand(BaseCommand):
    """Shortcut command to immediately create, activate, and persist a new conversation session."""

    name: str = "new"
    aliases: list[str] = ["n"]
    description: str = "Start a fresh conversation session with a new session file."
    usage: str = "/new [optional_name]"
    category: str = "Session"

    async def execute(self, ctx: CommandContext) -> str:
        """Create and switch to a new session file."""
        chat_id = ctx.chat_id
        prefix = f"{ctx.connector.name}_{chat_id}"
        args = ctx.args

        custom_name = args[0].strip() if args else ""
        if custom_name:
            clean_name = "".join(c for c in custom_name if c.isalnum() or c in ("-", "_"))
            new_session_id = f"{prefix}_{clean_name}"
        else:
            new_session_id = f"{prefix}_{uuid.uuid4().hex[:6]}"

        ctx.connector.set_session_id(chat_id, new_session_id)
        memory_mgr = ctx.engine.memory_manager
        if memory_mgr and memory_mgr.conversation:
            await memory_mgr.conversation.create_session(new_session_id)

        return (
            f"✨ **New Session Started**\n\n"
            f"• **Session ID:** `{new_session_id}`\n"
            f"• **File:** `{new_session_id}.json`\n\n"
            f"All previous conversations remain saved on disk and accessible via `/session`."
        )


class ClearSessionCommand(BaseCommand):
    """Shortcut command to clear the conversation and start a fresh session file."""

    name: str = "clear"
    aliases: list[str] = ["reset", "c"]
    description: str = "Reset the conversation by activating a clean new session file."
    usage: str = "/clear"
    category: str = "Session"

    async def execute(self, ctx: CommandContext) -> str:
        """Switch to a clean new session and save file."""
        chat_id = ctx.chat_id
        prefix = f"{ctx.connector.name}_{chat_id}"
        old_session_id = ctx.connector.get_session_id(chat_id)
        new_session_id = f"{prefix}_{uuid.uuid4().hex[:6]}"

        ctx.connector.set_session_id(chat_id, new_session_id)
        memory_mgr = ctx.engine.memory_manager
        if memory_mgr and memory_mgr.conversation:
            await memory_mgr.conversation.create_session(new_session_id)

        return (
            f"🧹 **Session Cleared & Reset**\n\n"
            f"• **Fresh Active Session:** `{new_session_id}`\n"
            f"• **Storage File:** `{new_session_id}.json`\n\n"
            f"*(Previous session `{old_session_id}` is saved and accessible via `/session`)*."
        )
