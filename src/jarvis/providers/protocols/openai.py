"""
OpenAI-Compatible Protocol — Handles OpenAI, Groq, NVIDIA, OpenRouter, Together, Mistral, DeepSeek, etc.

This single protocol implementation works with ANY provider that exposes
an OpenAI-compatible API (which is the vast majority of LLM providers).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from jarvis.providers.base import (
    BaseProvider,
    GenerationConfig,
    GenerationResponse,
    Message,
    StreamChunk,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI-compatible protocol implementation.

    Works with any provider that implements the OpenAI API spec:
    - OpenAI (api.openai.com)
    - Groq (api.groq.com)
    - NVIDIA NIM (integrate.api.nvidia.com)
    - OpenRouter (openrouter.ai)
    - Together AI (api.together.xyz)
    - Mistral (api.mistral.ai)
    - DeepSeek (api.deepseek.com)
    - Any other OpenAI-compatible endpoint
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
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                **self.extra_headers,
            },
            timeout=httpx.Timeout(120.0, connect=10.0),
        )

    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig,
    ) -> GenerationResponse:
        """Generate a completion using the OpenAI Chat Completions API."""
        payload = self._build_payload(messages, config, stream=False)

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        return self._parse_response(data)

    async def stream(
        self,
        messages: list[Message],
        config: GenerationConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a completion using SSE."""
        payload = self._build_payload(messages, config, stream=True)

        async with self._client.stream("POST", "/chat/completions", json=payload) as response:
            if response.is_error:
                error_bytes = await response.aread()
                try:
                    import json
                    err_data = json.loads(error_bytes.decode())
                    err_msg = err_data.get("error", {}).get("message", error_bytes.decode())
                except Exception:
                    err_msg = error_bytes.decode()
                logger.error(f"OpenAI Stream API error ({response.status_code}): {err_msg}")
                from jarvis.core.exceptions import ProviderError
                raise ProviderError(f"OpenAI API Error ({response.status_code}): {err_msg}")

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]  # Remove "data: " prefix
                if data_str.strip() == "[DONE]":
                    break

                import json
                data = json.loads(data_str)
                chunk = self._parse_stream_chunk(data)
                if chunk:
                    yield chunk

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """Generate embeddings using the OpenAI Embeddings API."""
        payload: dict[str, Any] = {
            "input": texts,
            "model": model,
        }
        # NVIDIA NIM embedding models require input_type ("passage" or "query")
        if "nvidia" in model.lower() or "nvidia" in str(self._client.base_url).lower():
            payload["input_type"] = "passage"

        response = await self._client.post("/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()

        return [item["embedding"] for item in data["data"]]

    async def list_models(self) -> list[dict[str, Any]]:
        """Fetch available models dynamically from the provider's GET /models API endpoint."""
        response = await self._client.get("/models")
        response.raise_for_status()
        data = response.json()
        models_raw = data.get("data", [])

        results: list[dict[str, Any]] = []
        for item in models_raw:
            if isinstance(item, dict):
                model_id = item.get("id")
                if model_id:
                    results.append({
                        "id": model_id,
                        "name": item.get("name", model_id),
                        "owned_by": item.get("owned_by", ""),
                    })
            elif isinstance(item, str):
                results.append({"id": item, "name": item})

        results.sort(key=lambda m: m["id"].lower())
        return results

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    # ─── Private helpers ──────────────────────────────────────

    def _build_payload(
        self,
        messages: list[Message],
        config: GenerationConfig,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Build the request payload."""
        payload: dict[str, Any] = {
            "model": config.model,
            "messages": [self._format_message(m) for m in messages],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": stream,
        }

        if config.stop:
            payload["stop"] = config.stop

        if config.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in config.tools
            ]

        return payload

    def _format_message(self, message: Message) -> dict[str, Any]:
        """Format a Message for the OpenAI API."""
        msg: dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }
        if message.name:
            msg["name"] = message.name
        if message.tool_calls:
            msg["tool_calls"] = message.tool_calls
        if message.tool_call_id:
            msg["tool_call_id"] = message.tool_call_id
        return msg

    def _parse_response(self, data: dict[str, Any]) -> GenerationResponse:
        """Parse the OpenAI API response into a normalized format."""
        choice = data["choices"][0]
        message = choice["message"]

        return GenerationResponse(
            content=message.get("content", "") or "",
            role=message.get("role", "assistant"),
            tool_calls=message.get("tool_calls", []),
            finish_reason=choice.get("finish_reason"),
            usage=data.get("usage", {}),
            raw=data,
        )

    def _parse_stream_chunk(self, data: dict[str, Any]) -> StreamChunk | None:
        """Parse a streaming chunk."""
        choices = data.get("choices", [])
        if not choices:
            return None

        delta = choices[0].get("delta", {})
        return StreamChunk(
            content=delta.get("content", "") or "",
            tool_calls=delta.get("tool_calls", []),
            finish_reason=choices[0].get("finish_reason"),
        )
