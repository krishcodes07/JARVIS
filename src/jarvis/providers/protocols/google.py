"""
Google-Compatible Protocol — Handles Google Gemini / Vertex AI API.

Implements the Google Generative AI API with support for:
- Text generation
- Streaming
- Tool use (function calling)
- Vision (image inputs)
- Embeddings
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from jarvis.core.exceptions import ProviderError
from jarvis.providers.base import (
    BaseProvider,
    GenerationConfig,
    GenerationResponse,
    Message,
    StreamChunk,
)

logger = logging.getLogger(__name__)


class GoogleProvider(BaseProvider):
    """Google Gemini API protocol implementation.

    Handles the Google Generative AI API format, which differs
    significantly from OpenAI:
    - Uses 'parts' instead of 'content'
    - Different role names ('model' instead of 'assistant')
    - API key passed as query parameter
    - Function declarations format for tools
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(api_key, base_url, extra_headers)
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={
                "Content-Type": "application/json",
                **self.extra_headers,
            },
            params={"key": api_key},
            timeout=httpx.Timeout(120.0, connect=10.0),
        )

    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig,
    ) -> GenerationResponse:
        """Generate using the Google Generative AI API."""
        system_instruction, contents = self._format_contents(messages)
        payload = self._build_payload(system_instruction, contents, config)

        url = f"/models/{config.model}:generateContent"
        response = await self._client.post(url, json=payload)
        if response.is_error:
            try:
                err_data = response.json()
                err_msg = err_data.get("error", {}).get("message", response.text)
            except Exception:
                err_msg = response.text
            logger.error(f"Google API error ({response.status_code}): {err_msg}")
            raise ProviderError(f"Google API Error ({response.status_code}): {err_msg}")

        data = response.json()
        return self._parse_response(data)

    async def stream(
        self,
        messages: list[Message],
        config: GenerationConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream using the Google Generative AI API."""
        system_instruction, contents = self._format_contents(messages)
        payload = self._build_payload(system_instruction, contents, config)

        url = f"/models/{config.model}:streamGenerateContent"
        async with self._client.stream(
            "POST", url, json=payload, params={"alt": "sse"}
        ) as response:
            if response.is_error:
                error_bytes = await response.aread()
                try:
                    err_data = json.loads(error_bytes.decode())
                    err_msg = err_data.get("error", {}).get("message", error_bytes.decode())
                except Exception:
                    err_msg = error_bytes.decode()
                logger.error(f"Google Stream API error ({response.status_code}): {err_msg}")
                raise ProviderError(f"Google API Error ({response.status_code}): {err_msg}")

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                chunk = self._parse_stream_chunk(data)
                if chunk:
                    yield chunk

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """Generate embeddings using the Google Embeddings API."""
        results: list[list[float]] = []
        for text in texts:
            payload = {
                "model": f"models/{model}",
                "content": {"parts": [{"text": text}]},
            }
            response = await self._client.post(
                f"/models/{model}:embedContent", json=payload
            )
            response.raise_for_status()
            data = response.json()
            results.append(data["embedding"]["values"])
        return results

    async def list_models(self) -> list[dict[str, Any]]:
        """Fetch available Gemini models dynamically from the Google GET /models API endpoint."""
        try:
            response = await self._client.get("/models")
            response.raise_for_status()
            data = response.json()
            models_raw = data.get("models", [])
            results: list[dict[str, Any]] = []
            for item in models_raw:
                if isinstance(item, dict):
                    full_name = item.get("name", "")
                    if full_name.startswith("models/"):
                        clean_id = full_name.replace("models/", "")
                    else:
                        clean_id = full_name
                    display_name = item.get("displayName", clean_id)
                    results.append({"id": clean_id, "name": display_name})
            if results:
                return sorted(results, key=lambda x: x["id"])
        except Exception as e:
            logger.warning(f"Failed to fetch Google models via API: {e}")

        return [
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
        ]

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    # ─── Private helpers ──────────────────────────────────────

    def _clean_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Convert schema type strings to uppercase and clean for Google OpenAPI specs."""
        if not isinstance(schema, dict):
            return schema

        cleaned: dict[str, Any] = {}
        for k, v in schema.items():
            if k in ("$schema", "title"):
                continue
            if k == "type" and isinstance(v, str):
                cleaned[k] = v.upper()
            elif isinstance(v, dict):
                cleaned[k] = self._clean_schema(v)
            elif isinstance(v, list):
                cleaned[k] = [self._clean_schema(item) if isinstance(item, dict) else item for item in v]
            else:
                cleaned[k] = v

        if "type" not in cleaned:
            cleaned["type"] = "OBJECT"

        return cleaned

    def _format_contents(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """Convert messages to Google's 'contents' format.

        Returns:
            Tuple of (system_instruction, contents).
        """
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == "system":
                text = msg.content if isinstance(msg.content, str) else str(msg.content)
                system_parts.append(text)
            elif msg.role == "tool":
                tool_name = msg.name or "tool"
                tool_content = msg.content if isinstance(msg.content, str) else str(msg.content)
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": tool_name,
                            "response": {"name": tool_name, "content": tool_content},
                        }
                    }],
                })
            else:
                role = "model" if msg.role == "assistant" else "user"
                parts: list[dict[str, Any]] = []

                if msg.role == "assistant" and msg.tool_calls:
                    for tc in msg.tool_calls:
                        fn = tc.get("function", {})
                        fn_name = fn.get("name", "")
                        args_raw = fn.get("arguments", {})
                        if isinstance(args_raw, str):
                            try:
                                args = json.loads(args_raw)
                            except Exception:
                                args = {"input": args_raw}
                        else:
                            args = args_raw or {}
                        parts.append({
                            "functionCall": {
                                "name": fn_name,
                                "args": args,
                            }
                        })

                text = msg.content if isinstance(msg.content, str) else str(msg.content)
                if text:
                    parts.insert(0, {"text": text})
                elif not parts:
                    parts.append({"text": ""})

                contents.append({
                    "role": role,
                    "parts": parts,
                })

        system_instruction = "\n\n".join(system_parts) if system_parts else None
        return system_instruction, contents

    def _build_payload(
        self,
        system_instruction: str | None,
        contents: list[dict[str, Any]],
        config: GenerationConfig,
    ) -> dict[str, Any]:
        """Build the Google API request payload."""
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.temperature,
                "maxOutputTokens": config.max_tokens,
                "topP": config.top_p,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        if config.tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": self._clean_schema(tool.parameters) if tool.parameters else {"type": "OBJECT", "properties": {}},
                        }
                        for tool in config.tools
                    ]
                }
            ]

        return payload

    def _parse_response(self, data: dict[str, Any]) -> GenerationResponse:
        """Parse Google API response into normalized format."""
        candidates = data.get("candidates", [])
        if not candidates:
            return GenerationResponse(content="", finish_reason="error")

        candidate = candidates[0]
        content_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for part in candidate.get("content", {}).get("parts", []):
            if "text" in part:
                content_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "id": f"call_{fc['name']}",
                    "type": "function",
                    "function": {
                        "name": fc["name"],
                        "arguments": json.dumps(fc.get("args", {})),
                    },
                })

        usage_meta = data.get("usageMetadata", {})

        return GenerationResponse(
            content="\n".join(content_parts),
            role="assistant",
            tool_calls=tool_calls,
            finish_reason=candidate.get("finishReason", "").lower(),
            usage={
                "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
            },
            raw=data,
        )

    def _parse_stream_chunk(self, data: dict[str, Any]) -> StreamChunk | None:
        """Parse a Google streaming chunk."""
        candidates = data.get("candidates", [])
        if not candidates:
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        text = ""
        tool_calls: list[dict[str, Any]] = []
        for part in parts:
            if "text" in part:
                text += part["text"]
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "id": f"call_{fc['name']}",
                    "type": "function",
                    "function": {
                        "name": fc["name"],
                        "arguments": json.dumps(fc.get("args", {})),
                    },
                })

        finish_reason = candidates[0].get("finishReason")
        return StreamChunk(
            content=text,
            tool_calls=tool_calls,
            finish_reason=finish_reason.lower() if finish_reason else None,
        )
