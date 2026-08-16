"""
Telegram Connector — Full-featured bridge connecting JARVIS with Telegram Messenger.
"""

from __future__ import annotations

import asyncio
import html
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jarvis.connectors.base import BaseConnector
from jarvis.connectors.models import InboundMessage
from jarvis.connectors.telegram.client import TelegramClient, TelegramClientError
from jarvis.connectors.telegram.formatter import markdown_to_telegram_html

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class TelegramConnector(BaseConnector):
    """Telegram Messenger bridge for JARVIS.

    Enables chatting with JARVIS via Telegram bot with full conversational memory,
    allowlist authorization, built-in commands (/start, /reset, /status), typing indicators,
    automatic Telegram HTML formatting, media file dispatching, and automatic long-message chunking.
    """

    name: str = "telegram"

    def __init__(self, config: JarvisConfig, engine: JarvisEngine) -> None:
        super().__init__(config, engine)
        self._client: TelegramClient | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._bot_info: dict[str, Any] = {}
        self._bot_id: str | None = None
        self._bot_username: str | None = None
        self._last_offset: int | None = None

    @property
    def is_enabled(self) -> bool:
        """Check if Telegram connector is enabled in configuration."""
        if not self.config or not hasattr(self.config, "connectors"):
            return False
        return self.config.connectors.enabled and self.config.connectors.telegram.enabled

    def _get_bot_token(self) -> str:
        """Retrieve Telegram bot token from config or environment."""
        token = ""
        if self.config and hasattr(self.config, "connectors"):
            token = self.config.connectors.telegram.bot_token or ""
        if not token:
            token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        return token.strip()

    def _get_allowed_users(self) -> list[str | int]:
        """Fetch allowed users list from configuration."""
        if self.config and hasattr(self.config, "connectors"):
            return self.config.connectors.telegram.allowed_users or []
        return []

    async def start(self) -> None:
        """Initialize Telegram client, verify bot token, and start polling loop."""
        if self._running:
            logger.info("Telegram connector is already running.")
            return

        token = self._get_bot_token()
        if not token:
            raise ValueError(
                "Telegram bot token is not configured. Set 'connectors.telegram.bot_token' "
                "in jarvis.yaml or TELEGRAM_BOT_TOKEN environment variable."
            )

        self._client = TelegramClient(bot_token=token)

        try:
            self._bot_info = await self._client.get_me()
            self._bot_id = str(self._bot_info.get("id", ""))
            self._bot_username = self._bot_info.get("username", "")
            bot_username = self._bot_username or "UnknownBot"
            logger.info(f"Connected to Telegram Bot API as @{bot_username} (ID: {self._bot_id})")
        except TelegramClientError as e:
            self._last_error = str(e)
            self._error_count += 1
            await self._client.close()
            self._client = None
            raise

        self._running = True
        self._connected_at = datetime.now(timezone.utc)
        self._poll_task = asyncio.create_task(self._poll_loop(), name="jarvis_telegram_poller")
        logger.info("Telegram connector polling started successfully.")

    async def stop(self) -> None:
        """Stop polling and close Telegram client."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping Telegram connector...")

        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        if self._client:
            await self._client.close()
            self._client = None

        logger.info("Telegram connector stopped.")

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_to_message_id: str | None = None,
        parse_mode: str | None = "HTML",
    ) -> bool:
        """Send a message (or multiple chunks if too long) to a Telegram chat with automatic HTML formatting."""
        if not self._client or not self._running:
            logger.warning("Cannot send message: Telegram connector is not running.")
            return False

        max_len = 4000
        if self.config and hasattr(self.config, "connectors"):
            max_len = self.config.connectors.telegram.max_message_length or 4000

        # Auto-format markdown into clean Telegram HTML unless raw mode requested
        formatted_text = markdown_to_telegram_html(text) if parse_mode == "HTML" else text
        chunks = self.split_message(formatted_text, max_length=max_len)
        success = True

        for idx, chunk in enumerate(chunks):
            # Reply to original message only on the first chunk
            reply_id = reply_to_message_id if idx == 0 else None
            res = await self._client.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode="HTML" if parse_mode else None,
                reply_to_message_id=reply_id,
            )
            if res:
                self._messages_sent += 1
            else:
                success = False

        return success

    async def send_file(
        self,
        chat_id: str,
        file_path: str | Path,
        caption: str | None = None,
        reply_to_message_id: str | None = None,
    ) -> bool:
        """Send a local file, image, video, audio, or document to a Telegram chat."""
        if not self._client or not self._running:
            logger.warning("Cannot send file: Telegram connector is not running.")
            return False

        formatted_caption = markdown_to_telegram_html(caption) if caption else None
        res = await self._client.send_file_auto(
            chat_id=chat_id,
            file_path=file_path,
            caption=formatted_caption,
            parse_mode="HTML",
            reply_to_message_id=reply_to_message_id,
        )
        if res:
            self._messages_sent += 1
            return True
        return False

    async def _poll_loop(self) -> None:
        """Background long-polling loop for Telegram updates."""
        timeout = 30
        if self.config and hasattr(self.config, "connectors"):
            timeout = self.config.connectors.telegram.polling_timeout or 30

        consecutive_errors = 0

        while self._running:
            try:
                if not self._client:
                    break

                updates = await self._client.get_updates(
                    offset=self._last_offset,
                    timeout=timeout,
                )

                consecutive_errors = 0

                for update in updates:
                    update_id = update.get("update_id")
                    if update_id is not None:
                        self._last_offset = update_id + 1

                    if "message" in update:
                        asyncio.create_task(
                            self._handle_message_update(update["message"]),
                            name=f"jarvis_tg_msg_{update_id}",
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                self._error_count += 1
                self._last_error = str(e)
                logger.error(f"Error in Telegram polling loop: {e}")
                backoff = min(2 ** consecutive_errors, 30)
                await asyncio.sleep(backoff)

    async def _handle_message_update(self, msg_dict: dict[str, Any]) -> None:
        """Process an individual incoming message from Telegram."""
        raw_text = msg_dict.get("text") or msg_dict.get("caption")
        if not raw_text:
            return

        chat = msg_dict.get("chat", {})
        chat_id = str(chat.get("id"))
        chat_type = chat.get("type", "private")
        from_user = msg_dict.get("from", {})
        user_id = str(from_user.get("id"))
        username = from_user.get("username")
        first_name = from_user.get("first_name", "")
        last_name = from_user.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip() or None
        message_id = str(msg_dict.get("message_id"))

        is_group = chat_type in ("group", "supergroup")
        bot_username = (self._bot_username or "").lower()
        bot_id = self._bot_id or ""

        # Check if message is a reply to the bot
        reply_to_msg = msg_dict.get("reply_to_message", {})
        reply_to_from = reply_to_msg.get("from", {})
        is_reply_to_bot = bool(bot_id) and str(reply_to_from.get("id")) == bot_id

        # Check if bot is mentioned in text
        is_mentioned = False
        if bot_username and f"@{bot_username}" in raw_text.lower():
            is_mentioned = True

        for entity in msg_dict.get("entities", []) or []:
            if entity.get("type") == "mention":
                offset = entity.get("offset", 0)
                length = entity.get("length", 0)
                mention_text = raw_text[offset : offset + length].lower().lstrip("@")
                if bot_username and mention_text == bot_username:
                    is_mentioned = True

        is_command = raw_text.startswith("/")

        # In groups/supergroups, ignore general chatter unless addressed to the bot
        if is_group and not is_command and not is_mentioned and not is_reply_to_bot:
            return

        # Clean bot mention and bot username suffix in commands
        text = raw_text
        if bot_username:
            # Clean /command@bot_username -> /command
            text = re.sub(rf"(/[\w]+)@{re.escape(bot_username)}", r"\1", text, flags=re.IGNORECASE)
            # Remove @bot_username mention from text
            text = re.sub(rf"@{re.escape(bot_username)}\b", "", text, flags=re.IGNORECASE).strip()

        if not text:
            return

        inbound = InboundMessage(
            connector=self.name,
            user_id=user_id,
            chat_id=chat_id,
            username=username,
            full_name=full_name,
            text=text,
            message_id=message_id,
            raw_payload=msg_dict,
        )

        self._messages_received += 1
        logger.info(f"[Telegram] Received message from @{username or user_id} in chat {chat_id} ({chat_type}): {text[:60]!r}")

        # 1. Authorization check
        if not self.is_user_allowed(user_id=user_id, username=username):
            logger.warning(f"[Telegram] Unauthorized user {user_id} (@{username}) attempted to access JARVIS.")
            if not is_group or is_mentioned or is_reply_to_bot:
                await self.send_message(
                    chat_id=chat_id,
                    text="⛔ <b>Access Denied</b>: Your Telegram account is not authorized to interact with this JARVIS instance.",
                    reply_to_message_id=message_id,
                    parse_mode="HTML",
                )
            return

        # 2. Built-in command check (/start, /help, /reset, /status)
        cmd_output = await self.handle_builtin_command(inbound)
        if cmd_output:
            await self.send_message(
                chat_id=chat_id,
                text=cmd_output,
                reply_to_message_id=message_id,
                parse_mode="HTML",
            )
            return

        # 3. Stream AI Engine generation with typing indicator & live status message
        session_id = self.get_session_id(chat_id)
        typing_task = None
        send_typing = True
        if self.config and hasattr(self.config, "connectors"):
            send_typing = self.config.connectors.telegram.send_typing

        if send_typing:
            typing_task = asyncio.create_task(self._typing_loop(chat_id))

        # Send initial status placeholder message
        status_msg_id: str | None = None
        if self._client:
            status_msg = await self._client.send_message(
                chat_id=chat_id,
                text="⏳ <i>Generating response...</i>",
                reply_to_message_id=message_id,
                parse_mode="HTML",
            )
            if status_msg and "message_id" in status_msg:
                status_msg_id = str(status_msg["message_id"])

        # Status message tracking
        current_status_text = "⏳ <i>Generating response...</i>"
        is_thinking = False
        stream_buffer = ""

        async def update_status(new_text: str) -> None:
            nonlocal current_status_text
            if new_text != current_status_text and status_msg_id and self._client:
                current_status_text = new_text
                try:
                    await self._client.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg_id,
                        text=new_text,
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.debug(f"[Telegram] Failed to update status message: {e}")

        # Callback when JARVIS invokes a tool
        async def on_tool_call(tool_name: str, tool_args: dict[str, Any]) -> None:
            tool_display = html.escape(tool_name)
            await update_status(f"🔧 <b>Calling <code>{tool_display}</code> tool...</b>")

        # Callback when tool execution completes
        async def on_tool_result(tool_name: str, result: str) -> None:
            tool_display = html.escape(tool_name)
            await update_status(f"⚡ <b>Processing output from <code>{tool_display}</code>...</b>")

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

                if not is_thinking and "<think>" in stream_buffer:
                    is_thinking = True
                    await update_status("💭 <b>Thinking...</b>")

                if is_thinking and "</think>" in stream_buffer:
                    is_thinking = False
                    idx = stream_buffer.find("</think>")
                    stream_buffer = stream_buffer[idx + len("</think>"):]

            final_response = "".join(chunks).strip()
            if not final_response:
                final_response = "<i>(Empty response generated)</i>"

            # Auto-format markdown into clean Telegram HTML
            html_response = markdown_to_telegram_html(final_response)

            # Deliver final response (edit placeholder or send chunks)
            max_len = 4000
            if self.config and hasattr(self.config, "connectors"):
                max_len = self.config.connectors.telegram.max_message_length or 4000

            response_chunks = self.split_message(html_response, max_length=max_len)

            if status_msg_id and self._client:
                edit_res = await self._client.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_msg_id,
                    text=response_chunks[0],
                    parse_mode="HTML",
                )
                if not edit_res:
                    await self._client.send_message(
                        chat_id=chat_id,
                        text=response_chunks[0],
                        parse_mode="HTML",
                        reply_to_message_id=message_id,
                    )
                else:
                    self._messages_sent += 1

                # Send subsequent chunks if output was >4000 characters
                for extra_chunk in response_chunks[1:]:
                    await self._client.send_message(
                        chat_id=chat_id,
                        text=extra_chunk,
                        parse_mode="HTML",
                    )
            else:
                await self.send_message(
                    chat_id=chat_id,
                    text=final_response,
                    reply_to_message_id=message_id,
                    parse_mode="HTML",
                )

        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error(f"[Telegram] Error processing AI chat for {chat_id}: {e}", exc_info=True)
            err_msg = f"⚠️ <b>JARVIS Error</b>: An unexpected error occurred while processing your request:\n<code>{html.escape(str(e))}</code>"
            if status_msg_id and self._client:
                await self._client.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_msg_id,
                    text=err_msg,
                    parse_mode="HTML",
                )
            else:
                await self.send_message(
                    chat_id=chat_id,
                    text=err_msg,
                    reply_to_message_id=message_id,
                    parse_mode="HTML",
                )
        finally:
            if typing_task and not typing_task.done():
                typing_task.cancel()

    async def _typing_loop(self, chat_id: str) -> None:
        """Periodically trigger the 'typing' action in Telegram while AI is thinking/tool-calling."""
        try:
            while self._running:
                if self._client:
                    await self._client.send_chat_action(chat_id, "typing")
                await asyncio.sleep(4.5)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Error in Telegram typing loop: {e}")

