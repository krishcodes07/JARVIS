"""
Discord Connector — Full-featured bridge connecting JARVIS with Discord servers and direct messages.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jarvis.connectors.base import BaseConnector
from jarvis.connectors.discord.formatter import markdown_to_discord_markdown, split_discord_message
from jarvis.connectors.models import InboundMessage

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class DiscordConnector(BaseConnector):
    """Discord Gateway bridge for JARVIS.

    Enables chatting with JARVIS via Discord bot with full conversational memory,
    allowlist authorization (users, channels, guilds), built-in commands (/start, /reset, /status, /mcp, /models),
    live thinking indicators, tool execution status updates, clean markdown formatting,
    file attachments, and automatic long-message chunking.
    """

    name: str = "discord"

    def __init__(self, config: JarvisConfig, engine: JarvisEngine) -> None:
        super().__init__(config, engine)
        self._client: Any = None
        self._client_task: asyncio.Task[None] | None = None
        self._bot_user: Any = None

    @property
    def is_enabled(self) -> bool:
        """Check whether Discord connector is enabled in configuration and has a bot token."""
        if not self.config or not hasattr(self.config, "connectors"):
            return False
        return (
            self.config.connectors.enabled
            and self.config.connectors.discord.enabled
            and bool(self._get_bot_token())
        )

    def _get_bot_token(self) -> str:
        """Get Discord bot token from config or environment."""
        token = ""
        if self.config and hasattr(self.config, "connectors"):
            token = self.config.connectors.discord.bot_token or ""
        if not token:
            token = os.getenv("DISCORD_BOT_TOKEN", "")
        return token.strip()

    def _get_allowed_users(self) -> list[str | int]:
        """Fetch allowed users list from configuration."""
        if self.config and hasattr(self.config, "connectors"):
            return self.config.connectors.discord.allowed_users or []
        return []

    def _get_allowed_channels(self) -> list[str | int]:
        """Fetch allowed channels list from configuration."""
        if self.config and hasattr(self.config, "connectors"):
            return self.config.connectors.discord.allowed_channels or []
        return []

    def _get_allowed_guilds(self) -> list[str | int]:
        """Fetch allowed guilds list from configuration."""
        if self.config and hasattr(self.config, "connectors"):
            return self.config.connectors.discord.allowed_guilds or []
        return []

    def is_channel_allowed(self, channel_id: str | int) -> bool:
        """Check if a Discord channel is allowed."""
        allowed = self._get_allowed_channels()
        if not allowed:
            return True
        return str(channel_id) in [str(c) for c in allowed]

    def is_guild_allowed(self, guild_id: str | int | None) -> bool:
        """Check if a Discord guild is allowed (DMs have None guild_id and are allowed)."""
        if guild_id is None:
            return True
        allowed = self._get_allowed_guilds()
        if not allowed:
            return True
        return str(guild_id) in [str(g) for g in allowed]

    async def start(self) -> None:
        """Initialize Discord client, connect to Gateway, and register event listeners."""
        if self._running:
            logger.info("Discord connector is already running.")
            return

        ok, err_msg = self.check_credentials()
        if not ok:
            logger.error(err_msg)
            self._last_error = f"{self.env_var_name} is not set."
            self._error_count += 1
            raise ValueError(err_msg)

        token = self._get_bot_token()

        try:
            import discord
        except ImportError as e:
            raise ImportError("discord.py is not installed. Install it with 'pip install discord.py'.") from e

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        self._client = discord.Client(intents=intents)

        ready_event = asyncio.Event()

        @self._client.event
        async def on_ready() -> None:
            self._running = True
            self._connected_at = datetime.now(UTC)
            self._bot_user = self._client.user
            logger.info(f"Connected to Discord Gateway as @{self._client.user} (ID: {self._client.user.id})")
            ready_event.set()
            try:
                activity = discord.Activity(type=discord.ActivityType.listening, name="to your commands | JARVIS")
                await self._client.change_presence(activity=activity)
            except Exception as e:
                logger.debug(f"Failed to set Discord presence: {e}")

        @self._client.event
        async def on_message(message: discord.Message) -> None:
            await self._handle_message(message)

        # Start Discord Gateway client in a background task
        self._client_task = asyncio.create_task(
            self._client.start(token),
            name="jarvis_discord_client",
        )

        try:
            # Wait up to 20 seconds for on_ready to fire
            await asyncio.wait_for(ready_event.wait(), timeout=20.0)
            logger.info("Discord connector initialized and ready.")
        except TimeoutError:
            logger.warning("Discord client connection timed out waiting for ready event. Continuing in background...")

    async def stop(self) -> None:
        """Gracefully disconnect and close Discord client."""
        if not self._running and not self._client:
            return

        self._running = False
        logger.info("Stopping Discord connector...")

        if self._client and not self._client.is_closed():
            try:
                await self._client.close()
            except Exception as e:
                logger.debug(f"Error closing Discord client: {e}")
            self._client = None

        if self._client_task and not self._client_task.done():
            self._client_task.cancel()
            try:
                await self._client_task
            except asyncio.CancelledError:
                pass
            self._client_task = None

        logger.info("Discord connector stopped.")

    async def _get_channel_target(self, chat_id: str) -> Any:
        """Resolve a Discord channel or user DM target."""
        if not self._client:
            return None
        try:
            channel_id_int = int(chat_id)
            channel = self._client.get_channel(channel_id_int)
            if not channel:
                channel = await self._client.fetch_channel(channel_id_int)
            return channel
        except Exception as e:
            logger.debug(f"Failed to fetch Discord channel {chat_id}: {e}")
            try:
                # Try fetching as direct message user
                user = self._client.get_user(int(chat_id)) or await self._client.fetch_user(int(chat_id))
                if user:
                    return await user.create_dm()
            except Exception as e2:
                logger.debug(f"Failed to fetch Discord user DM {chat_id}: {e2}")
        return None

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_to_message_id: str | None = None,
        parse_mode: str | None = None,
    ) -> bool:
        """Send a message (or multiple chunks if too long) to a Discord channel."""
        if not self._client or not self._running:
            logger.warning("Cannot send message: Discord connector is not running.")
            return False

        channel = await self._get_channel_target(chat_id)
        if not channel:
            logger.error(f"[Discord] Could not find channel {chat_id} to send message.")
            return False

        max_len = 2000
        if self.config and hasattr(self.config, "connectors"):
            max_len = self.config.connectors.discord.max_message_length or 2000

        formatted_text = markdown_to_discord_markdown(text)
        chunks = split_discord_message(formatted_text, max_length=max_len)
        success = True

        for idx, chunk in enumerate(chunks):
            try:
                ref = None
                if reply_to_message_id and idx == 0:
                    import discord
                    try:
                        ref = discord.MessageReference(message_id=int(reply_to_message_id), channel_id=channel.id)
                    except Exception:
                        ref = None
                await channel.send(chunk, reference=ref)
                self._messages_sent += 1
            except Exception as e:
                logger.error(f"[Discord] Failed to send message chunk to channel {chat_id}: {e}")
                success = False

        return success

    async def send_file(
        self,
        chat_id: str,
        file_path: str | Path,
        caption: str | None = None,
        reply_to_message_id: str | None = None,
    ) -> bool:
        """Send a file, document, or image to a Discord channel."""
        if not self._client or not self._running:
            logger.warning("Cannot send file: Discord connector is not running.")
            return False

        channel = await self._get_channel_target(chat_id)
        if not channel:
            logger.error(f"[Discord] Could not find channel {chat_id} to send file.")
            return False

        import discord

        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                logger.error(f"[Discord] File not found: {file_path}")
                return False

            d_file = discord.File(str(path_obj), filename=path_obj.name)
            formatted_caption = markdown_to_discord_markdown(caption) if caption else None

            ref = None
            if reply_to_message_id:
                try:
                    ref = discord.MessageReference(message_id=int(reply_to_message_id), channel_id=channel.id)
                except Exception:
                    ref = None

            await channel.send(content=formatted_caption, file=d_file, reference=ref)
            self._messages_sent += 1
            return True
        except Exception as e:
            logger.error(f"[Discord] Failed to send file {file_path} to channel {chat_id}: {e}")
            self._error_count += 1
            self._last_error = str(e)
            return False

    async def _handle_message(self, message: Any) -> None:
        """Process an incoming message from Discord."""
        # 1. Ignore bot's own messages and messages from other bots
        if message.author.bot:
            return

        text = message.content.strip()
        if not text and not message.attachments:
            return

        # 2. Check if bot was mentioned in a server channel or if it's a DM
        is_dm = message.guild is None
        bot_user = self._client.user if self._client else None
        is_mentioned = bot_user and (bot_user in message.mentions or f"<@{bot_user.id}>" in text or f"<@!{bot_user.id}>" in text)

        # In servers, clean the bot mention from the prompt
        if is_mentioned and bot_user:
            text = text.replace(f"<@{bot_user.id}>", "").replace(f"<@!{bot_user.id}>", "").strip()

        # In server channels, only respond if mentioned or in an explicitly allowed channel
        if not is_dm and not is_mentioned and not self._get_allowed_channels():
            return

        user_id = str(message.author.id)
        username = message.author.name
        full_name = message.author.display_name
        chat_id = str(message.channel.id)
        message_id = str(message.id)
        guild_id = str(message.guild.id) if message.guild else None

        inbound = InboundMessage(
            connector=self.name,
            user_id=user_id,
            chat_id=chat_id,
            username=username,
            full_name=full_name,
            text=text,
            message_id=message_id,
            raw_payload={"guild_id": guild_id},
        )

        self._messages_received += 1
        logger.info(f"[Discord] Received message from @{username} ({user_id}) in channel {chat_id}: {text[:60]!r}")

        # 3. Authorization check (User, Channel, Guild)
        if not self.is_user_allowed(user_id=user_id, username=username):
            logger.warning(f"[Discord] Unauthorized user {user_id} (@{username}) attempted to access JARVIS.")
            if is_dm or is_mentioned:
                await message.reply(
                    "⛔ **Access Denied**: Your Discord account is not authorized to interact with this JARVIS instance."
                )
            return

        if not self.is_channel_allowed(chat_id):
            return

        if not self.is_guild_allowed(guild_id):
            return

        # 4. Built-in command check (/start, /help, /reset, /status, /mcp, /models)
        cmd_output = await self.handle_builtin_command(inbound)
        if cmd_output:
            formatted_cmd = markdown_to_discord_markdown(cmd_output)
            chunks = split_discord_message(formatted_cmd, max_length=2000)
            for idx, chunk in enumerate(chunks):
                if idx == 0:
                    await message.reply(chunk)
                else:
                    await message.channel.send(chunk)
            self._messages_sent += len(chunks)
            return

        # 5. Stream AI generation with live typing & status message
        session_id = self.get_session_id(chat_id)

        placeholder_msg: Any = None
        try:
            placeholder_msg = await message.reply("⏳ *Generating response...*")
        except Exception as e:
            logger.debug(f"[Discord] Failed to send initial status message: {e}")

        # Status update tracking
        current_status_text = "⏳ *Generating response...*"
        is_thinking = False
        stream_buffer = ""

        async def update_status(new_text: str) -> None:
            nonlocal current_status_text
            if new_text != current_status_text and placeholder_msg:
                current_status_text = new_text
                try:
                    await placeholder_msg.edit(content=new_text)
                except Exception as e:
                    logger.debug(f"[Discord] Failed to edit status message: {e}")

        # Callback when JARVIS invokes a tool
        async def on_tool_call(tool_name: str, tool_args: dict[str, Any]) -> None:
            await update_status(f"🔧 **Calling `{tool_name}` tool...**")

        # Callback when tool execution completes
        async def on_tool_result(tool_name: str, result: str) -> None:
            await update_status(f"⚡ **Processing output from `{tool_name}`...**")

        send_typing = True
        if self.config and hasattr(self.config, "connectors"):
            send_typing = self.config.connectors.discord.send_typing

        # Typing background loop
        typing_task = None
        if send_typing:
            async def _typing_worker() -> None:
                while True:
                    try:
                        async with message.channel.typing():
                            await asyncio.sleep(8)
                    except (asyncio.CancelledError, Exception):
                        break
            typing_task = asyncio.create_task(_typing_worker(), name="jarvis_discord_typing")

        try:
            chunks: list[str] = []
            async for chunk in self.engine.stream_chat(
                inbound.text,
                session_id=session_id,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            ):
                chunks.append(chunk)
                stream_buffer += chunk

                if not is_thinking and re.search(r"<(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>", stream_buffer, re.IGNORECASE):
                    is_thinking = True
                    await update_status("💭 **Thinking...**")

                if is_thinking:
                    close_match = re.search(r"</(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>", stream_buffer, re.IGNORECASE)
                    if close_match:
                        is_thinking = False
                        stream_buffer = stream_buffer[close_match.end():]

            final_response = "".join(chunks).strip()
            if not final_response:
                final_response = "*(Empty response generated)*"

            # Auto-format markdown into Discord markdown
            formatted_response = markdown_to_discord_markdown(final_response)

            # Deliver response (edit placeholder or send chunks)
            max_len = 2000
            if self.config and hasattr(self.config, "connectors"):
                max_len = self.config.connectors.discord.max_message_length or 2000

            response_chunks = split_discord_message(formatted_response, max_length=max_len)

            if placeholder_msg:
                try:
                    await placeholder_msg.edit(content=response_chunks[0])
                    self._messages_sent += 1
                except Exception as e:
                    logger.debug(f"[Discord] Failed to edit placeholder message: {e}")
                    await message.reply(response_chunks[0])
                    self._messages_sent += 1

                for extra_chunk in response_chunks[1:]:
                    await message.channel.send(extra_chunk)
                    self._messages_sent += 1
            else:
                for idx, chunk in enumerate(response_chunks):
                    if idx == 0:
                        await message.reply(chunk)
                    else:
                        await message.channel.send(chunk)
                    self._messages_sent += 1

        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error(f"[Discord] Error processing message from user {user_id}: {e}", exc_info=True)
            err_text = f"❌ **Error**: An unexpected error occurred while processing your request: `{e}`"
            if placeholder_msg:
                try:
                    await placeholder_msg.edit(content=err_text)
                except Exception:
                    await message.reply(err_text)
            else:
                await message.reply(err_text)
        finally:
            if typing_task and not typing_task.done():
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass
