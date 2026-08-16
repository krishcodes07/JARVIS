"""
Telegram Bot API Client — Lightweight async HTTP client using httpx.
"""

from __future__ import annotations

import logging
from typing import Any, cast
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class TelegramClientError(Exception):
    """Base exception for Telegram Bot API errors."""
    pass


class TelegramClient:
    """Asynchronous client for interacting with the official Telegram Bot API."""

    def __init__(self, bot_token: str, base_url: str = "https://api.telegram.org") -> None:
        self.bot_token = bot_token.strip()
        self.api_url = f"{base_url.rstrip('/')}/bot{self.bot_token}"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create reusable async httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0))
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_me(self) -> dict[str, Any]:
        """Test bot token and get bot identity info."""
        client = await self._get_client()
        url = f"{self.api_url}/getMe"
        try:
            resp = await client.get(url)
            data = resp.json()
            if not isinstance(data, dict) or not data.get("ok"):
                desc = data.get("description", "Unknown error") if isinstance(data, dict) else "Invalid response"
                raise TelegramClientError(f"getMe failed: {desc}")
            return cast(dict[str, Any], data.get("result", {}))
        except httpx.HTTPError as e:
            raise TelegramClientError(f"HTTP error communicating with Telegram: {e}") from e

    async def get_updates(
        self,
        offset: int | None = None,
        timeout: int = 30,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Long poll for new incoming updates."""
        client = await self._get_client()
        url = f"{self.api_url}/getUpdates"
        payload: dict[str, Any] = {
            "timeout": timeout,
            "limit": limit,
            "allowed_updates": ["message"],
        }
        if offset is not None:
            payload["offset"] = offset

        try:
            # Long-polling requires a timeout slightly longer than the server timeout
            req_timeout = httpx.Timeout(timeout + 15.0, connect=10.0)
            resp = await client.post(url, json=payload, timeout=req_timeout)
            data = resp.json()
            if not isinstance(data, dict) or not data.get("ok"):
                if isinstance(data, dict):
                    logger.warning(f"getUpdates returned error: {data.get('description')}")
                return []
            result = data.get("result", [])
            return cast(list[dict[str, Any]], result if isinstance(result, list) else [])
        except httpx.TimeoutException:
            # Normal long-polling timeout with no updates
            return []
        except httpx.HTTPError as e:
            logger.warning(f"Network error in getUpdates: {e}")
            return []

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        parse_mode: str | None = "Markdown",
        reply_to_message_id: str | int | None = None,
    ) -> dict[str, Any] | None:
        """Send a text message to a chat, with automatic plain-text fallback if markdown parsing fails."""
        client = await self._get_client()
        url = f"{self.api_url}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        try:
            resp = await client.post(url, json=payload)
            data = resp.json()

            if isinstance(data, dict) and data.get("ok"):
                return cast(dict[str, Any], data.get("result", {}))

            description = data.get("description", "") if isinstance(data, dict) else ""
            # If markdown parsing fails, fallback to unformatted plain text
            if parse_mode and "can't parse entities" in description.lower():
                logger.debug("Markdown parsing error in Telegram sendMessage, falling back to plain text.")
                payload.pop("parse_mode", None)
                retry_resp = await client.post(url, json=payload)
                retry_data = retry_resp.json()
                if isinstance(retry_data, dict) and retry_data.get("ok"):
                    return cast(dict[str, Any], retry_data.get("result", {}))

            logger.error(f"Telegram sendMessage failed: {description}")
            return None
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
            return None

    async def edit_message_text(
        self,
        chat_id: str | int,
        message_id: str | int,
        text: str,
        parse_mode: str | None = "Markdown",
    ) -> dict[str, Any] | None:
        """Edit an existing message's text in a chat, with automatic plain-text fallback on parse errors."""
        client = await self._get_client()
        url = f"{self.api_url}/editMessageText"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            resp = await client.post(url, json=payload)
            data = resp.json()

            if isinstance(data, dict) and data.get("ok"):
                return cast(dict[str, Any], data.get("result", {}))

            description = data.get("description", "") if isinstance(data, dict) else ""
            # Ignore harmless "message is not modified" error from Telegram
            if "message is not modified" in description.lower():
                return {}

            # If markdown parsing fails, fallback to unformatted plain text
            if parse_mode and "can't parse entities" in description.lower():
                logger.debug("Markdown parsing error in Telegram editMessageText, falling back to plain text.")
                payload.pop("parse_mode", None)
                retry_resp = await client.post(url, json=payload)
                retry_data = retry_resp.json()
                if isinstance(retry_data, dict) and retry_data.get("ok"):
                    return cast(dict[str, Any], retry_data.get("result", {}))

            logger.warning(f"Telegram editMessageText failed: {description}")
            return None
        except Exception as e:
            logger.warning(f"Failed to edit Telegram message {message_id} in {chat_id}: {e}")
            return None

    async def delete_message(self, chat_id: str | int, message_id: str | int) -> bool:
        """Delete a message from a chat."""
        client = await self._get_client()
        url = f"{self.api_url}/deleteMessage"
        payload = {"chat_id": chat_id, "message_id": message_id}
        try:
            resp = await client.post(url, json=payload)
            data = resp.json()
            return isinstance(data, dict) and bool(data.get("ok"))
        except Exception:
            return False

    async def send_photo(
        self,
        chat_id: str | int,
        photo: str | Path | bytes,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_to_message_id: str | int | None = None,
    ) -> dict[str, Any] | None:
        """Send a photo to a chat (file path or raw bytes)."""
        return await self._send_media_file(
            endpoint="sendPhoto",
            file_field="photo",
            chat_id=chat_id,
            file_input=photo,
            default_filename="photo.jpg",
            caption=caption,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_video(
        self,
        chat_id: str | int,
        video: str | Path | bytes,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_to_message_id: str | int | None = None,
    ) -> dict[str, Any] | None:
        """Send a video to a chat (file path or raw bytes)."""
        return await self._send_media_file(
            endpoint="sendVideo",
            file_field="video",
            chat_id=chat_id,
            file_input=video,
            default_filename="video.mp4",
            caption=caption,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_audio(
        self,
        chat_id: str | int,
        audio: str | Path | bytes,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_to_message_id: str | int | None = None,
    ) -> dict[str, Any] | None:
        """Send an audio file to a chat (file path or raw bytes)."""
        return await self._send_media_file(
            endpoint="sendAudio",
            file_field="audio",
            chat_id=chat_id,
            file_input=audio,
            default_filename="audio.mp3",
            caption=caption,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_document(
        self,
        chat_id: str | int,
        document: str | Path | bytes,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_to_message_id: str | int | None = None,
    ) -> dict[str, Any] | None:
        """Send a document or general file to a chat (file path or raw bytes)."""
        return await self._send_media_file(
            endpoint="sendDocument",
            file_field="document",
            chat_id=chat_id,
            file_input=document,
            default_filename="document.bin",
            caption=caption,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_file_auto(
        self,
        chat_id: str | int,
        file_path: str | Path,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_to_message_id: str | int | None = None,
    ) -> dict[str, Any] | None:
        """Automatically choose send_photo, send_video, send_audio, or send_document based on file extension."""
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            logger.warning(f"File does not exist: {file_path}")
            return None

        ext = path.suffix.lower()
        if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
            return await self.send_photo(
                chat_id=chat_id,
                photo=path,
                caption=caption,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
            )
        elif ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
            return await self.send_video(
                chat_id=chat_id,
                video=path,
                caption=caption,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
            )
        elif ext in (".mp3", ".wav", ".ogg", ".m4a", ".flac"):
            return await self.send_audio(
                chat_id=chat_id,
                audio=path,
                caption=caption,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
            )
        else:
            return await self.send_document(
                chat_id=chat_id,
                document=path,
                caption=caption,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
            )

    async def _send_media_file(
        self,
        endpoint: str,
        file_field: str,
        chat_id: str | int,
        file_input: str | Path | bytes,
        default_filename: str,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_to_message_id: str | int | None = None,
    ) -> dict[str, Any] | None:
        """Internal helper to upload and send multipart media files to Telegram."""
        client = await self._get_client()
        url = f"{self.api_url}/{endpoint}"

        if isinstance(file_input, (str, Path)):
            path = Path(file_input)
            if not path.exists() or not path.is_file():
                logger.warning(f"File not found for Telegram upload: {file_input}")
                return None
            filename = path.name
            file_bytes = path.read_bytes()
        else:
            filename = default_filename
            file_bytes = file_input

        data: dict[str, Any] = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if reply_to_message_id:
            data["reply_to_message_id"] = str(reply_to_message_id)

        files = {file_field: (filename, file_bytes)}

        try:
            resp = await client.post(url, data=data, files=files, timeout=httpx.Timeout(60.0, connect=10.0))
            resp_data = resp.json()

            if isinstance(resp_data, dict) and resp_data.get("ok"):
                return cast(dict[str, Any], resp_data.get("result", {}))

            desc = resp_data.get("description", "") if isinstance(resp_data, dict) else ""
            # Fallback to plain text caption if parse error
            if parse_mode and "can't parse entities" in desc.lower():
                data.pop("parse_mode", None)
                retry_files = {file_field: (filename, file_bytes)}
                retry_resp = await client.post(url, data=data, files=retry_files, timeout=httpx.Timeout(60.0, connect=10.0))
                retry_data = retry_resp.json()
                if isinstance(retry_data, dict) and retry_data.get("ok"):
                    return cast(dict[str, Any], retry_data.get("result", {}))

            logger.warning(f"Telegram {endpoint} failed: {desc}")
            return None
        except Exception as e:
            logger.error(f"Failed to execute Telegram {endpoint} for {chat_id}: {e}")
            return None

    async def send_chat_action(self, chat_id: str | int, action: str = "typing") -> bool:
        """Send a chat action indicator (e.g. 'typing')."""
        client = await self._get_client()
        url = f"{self.api_url}/sendChatAction"
        payload = {"chat_id": chat_id, "action": action}
        try:
            resp = await client.post(url, json=payload, timeout=httpx.Timeout(5.0))
            data = resp.json()
            return bool(data.get("ok", False))
        except Exception:
            return False
