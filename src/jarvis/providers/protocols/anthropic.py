"""
Anthropic-Compatible Protocol — Handles Anthropic Claude API.

Implements the Anthropic Messages API with support for:
- Text generation
- Streaming
- Tool use (function calling)
- Vision (image inputs)
"""

from __future__ import annotations

import json
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


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API protocol implementation.

    Handles the Anthropic-specific message format, which differs
    from OpenAI in several ways:
    - System prompt is a separate parameter, not a message
    - Content blocks instead of plain strings
    - Different tool use format
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
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
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
        """Generate using the Anthropic Messages API."""
        system_prompt, formatted_messages = self._split_system(messages)
        payload = self._build_payload(system_prompt, formatted_messages, config, stream=False)

        response = await self._client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        return self._parse_response(data)

    async def stream(
        self,
        messages: list[Message],
        config: GenerationConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream using the Anthropic Messages API with SSE.

        Accumulates ``tool_use`` blocks across ``content_block_*`` events and
        emits them as OpenAI-format tool calls.
        """
        system_prompt, formatted_messages = self._split_system(messages)
        payload = self._build_payload(system_prompt, formatted_messages, config, stream=True)

        async with self._client.stream("POST", "/v1/messages", json=payload) as response:
            if response.is_error:
                error_bytes = await response.aread()
                try:
                    err_data = json.loads(error_bytes.decode())
                    err_msg = err_data.get("error", {}).get("message", error_bytes.decode())
                except Exception:
                    err_msg = error_bytes.decode()
                logger.error(f"Anthropic Stream API error ({response.status_code}): {err_msg}")
                from jarvis.core.exceptions import ProviderError
                raise ProviderError(f"Anthropic API Error ({response.status_code}): {err_msg}")

            tool_blocks: dict[int, dict[str, Any]] = {}
            thinking_blocks: set[int] = set()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                event_type = data.get("type", "")
                index = data.get("index", 0)

                if event_type == "content_block_start":
                    block = data.get("content_block", {})
                    if block.get("type") == "tool_use":
                        tool_blocks[index] = {
                            "id": block.get("id", f"tool_{index}"),
                            "name": block.get("name", ""),
                            "arguments": "",
                        }
                    elif block.get("type") == "thinking":
                        thinking_blocks.add(index)
                        yield StreamChunk(content="<think>\n")
                elif event_type == "content_block_delta":
                    delta = data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield StreamChunk(content=delta.get("text", ""))
                    elif delta.get("type") == "thinking_delta":
                        yield StreamChunk(content=delta.get("thinking", ""))
                    elif delta.get("type") == "input_json_delta" and index in tool_blocks:
                        tool_blocks[index]["arguments"] += delta.get("partial_json", "")
                elif event_type == "content_block_stop":
                    if index in thinking_blocks:
                        thinking_blocks.discard(index)
                        yield StreamChunk(content="\n</think>\n")
                    elif index in tool_blocks:
                        block = tool_blocks.pop(index)
                        yield StreamChunk(tool_calls=[{
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": block["arguments"],
                            },
                        }])
                elif event_type == "message_stop":
                    yield StreamChunk(finish_reason="stop")

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """Anthropic does not natively support embeddings."""
        raise NotImplementedError("Anthropic does not provide an embeddings API.")

    async def list_models(self) -> list[dict[str, Any]]:
        """Fetch available models dynamically from Anthropic GET /v1/models API endpoint."""
        try:
            response = await self._client.get("/v1/models")
            response.raise_for_status()
            data = response.json()
            models_raw = data.get("data", [])
            results = [
                {"id": m.get("id"), "name": m.get("display_name", m.get("id"))}
                for m in models_raw
                if isinstance(m, dict) and "id" in m
            ]
            if results:
                return sorted(results, key=lambda x: x["id"])
        except Exception as e:
            logger.warning(f"Failed to fetch Anthropic models via API: {e}")

        return [
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
            {"id": "claude-opus-4-20250514", "name": "Claude Opus 4"},
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
        ]

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    # ─── Private helpers ──────────────────────────────────────

    def _split_system(
        self, messages: list[Message]
    ) -> tuple[str, list[dict[str, Any]]]:
        """Separate system messages from conversation messages.

        Anthropic requires the system prompt as a separate parameter.
        """
        system_parts: list[str] = []
        formatted: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == "system":
                text = msg.content if isinstance(msg.content, str) else str(msg.content)
                system_parts.append(text)
            elif msg.role == "tool":
                call_id = msg.tool_call_id or f"call_{msg.name or 'tool'}"
                content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
                tool_res = {
                    "type": "tool_result",
                    "tool_use_id": call_id,
                    "content": content_str,
                }
                if formatted and formatted[-1].get("role") == "user" and isinstance(formatted[-1].get("content"), list):
                    formatted[-1]["content"].append(tool_res)
                else:
                    formatted.append({
                        "role": "user",
                        "content": [tool_res],
                    })
            else:
                formatted.append(self._format_message(msg))

        return "\n\n".join(system_parts), formatted

    def _build_payload(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        config: GenerationConfig,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Build the Anthropic API request payload."""
        payload: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": stream,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if config.tools:
            payload["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in config.tools
            ]

        # Handle Anthropic extended thinking based on models.dev and config.thinking
        from jarvis.providers.models_dev import (
            get_model_info,
            has_configurable_reasoning,
        )

        model_info = get_model_info(config.model, config.provider_id or "anthropic")

        if config.thinking is True and config.reasoning_effort != "none":
            if has_configurable_reasoning(config.model, config.provider_id or "anthropic", model_info):

                budget = config.thinking_budget or 2048
                # Anthropic API requires max_tokens > budget_tokens
                if payload["max_tokens"] <= budget:
                    payload["max_tokens"] = budget + 1024
                # Anthropic requires temperature to be 1.0 (or omitted) and top_p omitted when thinking is enabled
                payload.pop("temperature", None)
                payload.pop("top_p", None)
                payload["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": budget,
                }
        elif config.thinking is False:
            # When thinking is disabled, do not include thinking parameter if configurable
            pass

        return payload


    def _format_message(self, message: Message) -> dict[str, Any]:
        """Format a message for the Anthropic API."""
        if message.role == "assistant" and message.tool_calls:
            blocks: list[dict[str, Any]] = []
            text = message.content if isinstance(message.content, str) else str(message.content)
            if text:
                blocks.append({"type": "text", "text": text})

            for tc in message.tool_calls:
                fn = tc.get("function", {})
                args_raw = fn.get("arguments", {})
                if isinstance(args_raw, str):
                    try:
                        args = json.loads(args_raw)
                    except Exception:
                        args = {"input": args_raw}
                else:
                    args = args_raw or {}

                blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id", f"call_{fn.get('name', 'tool')}"),
                    "name": fn.get("name", "tool"),
                    "input": args,
                })
            return {"role": "assistant", "content": blocks}

        content_str = message.content if isinstance(message.content, str) else str(message.content)
        return {"role": message.role, "content": content_str}

    def _parse_response(self, data: dict[str, Any]) -> GenerationResponse:
        """Parse Anthropic response into normalized format."""
        content_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in data.get("content", []):
            if block["type"] == "text":
                content_parts.append(block["text"])
            elif block["type"] == "thinking":
                content_parts.append(f"<think>\n{block.get('thinking', '')}\n</think>")
            elif block["type"] == "tool_use":
                tool_calls.append({
                    "id": block["id"],
                    "type": "function",
                    "function": {
                        "name": block["name"],
                        "arguments": json.dumps(block["input"]),
                    },
                })

        return GenerationResponse(
            content="\n".join(content_parts),
            role="assistant",
            tool_calls=tool_calls,
            finish_reason=data.get("stop_reason"),
            usage={
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
            raw=data,
        )
