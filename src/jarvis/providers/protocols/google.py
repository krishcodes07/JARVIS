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

            in_thought = False
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                candidates = data.get("candidates", [])
                if not candidates:
                    continue
                parts = candidates[0].get("content", {}).get("parts", [])
                text = ""
                tool_calls: list[dict[str, Any]] = []
                for part in parts:
                    if "text" in part:
                        p_text = part["text"]
                        is_th = bool(part.get("thought"))
                        if is_th and not in_thought:
                            text += f"<think>\n{p_text}"
                            in_thought = True
                        elif not is_th and in_thought:
                            text += f"\n</think>\n{p_text}"
                            in_thought = False
                        else:
                            text += p_text
                    elif "functionCall" in part:
                        if in_thought:
                            text += "\n</think>\n"
                            in_thought = False
                        fc = part["functionCall"]
                        sig = self._extract_thought_signature(part, fc)
                        tc_dict: dict[str, Any] = {
                            "id": f"call_{fc['name']}",
                            "type": "function",
                            "function": {
                                "name": fc["name"],
                                "arguments": json.dumps(fc.get("args", {})),
                            },
                        }
                        if sig:
                            tc_dict["thought_signature"] = sig
                        tool_calls.append(tc_dict)

                finish_reason = candidates[0].get("finishReason")
                if finish_reason and in_thought:
                    text += "\n</think>\n"
                    in_thought = False

                if text or tool_calls or finish_reason:
                    yield StreamChunk(
                        content=text,
                        tool_calls=tool_calls,
                        finish_reason=finish_reason.lower() if finish_reason else None,
                    )

            if in_thought:
                yield StreamChunk(content="\n</think>\n")

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
        """Convert JSON schema to Google Gemini OpenAPI spec format.

        Google's REST API for Schema (google.ai.generativelanguage.v1beta.Schema) only accepts
        specific fields: type, format, description, nullable, enum, maxItems, minItems,
        properties, required, items, propertyOrdering.
        Unrecognized fields (like additionalProperties, $schema, title, default, etc.) will
        cause Google API to return 400 Bad Request ("Unknown name...").
        """
        if not isinstance(schema, dict):
            return {}

        schema_copy = dict(schema)

        # Handle anyOf / oneOf (e.g. Pydantic Optional fields: [{"type": "string"}, {"type": "null"}])
        is_nullable = schema_copy.get("nullable", False)
        for combo_key in ("anyOf", "oneOf"):
            if combo_key in schema_copy and isinstance(schema_copy[combo_key], list):
                subschemas = schema_copy.pop(combo_key)
                non_null = []
                for sub in subschemas:
                    if isinstance(sub, dict):
                        if sub.get("type") == "null":
                            is_nullable = True
                        else:
                            non_null.append(sub)
                if non_null:
                    merged = dict(non_null[0])
                    merged.update(schema_copy)
                    schema_copy = merged
                if is_nullable:
                    schema_copy["nullable"] = True

        # Handle allOf
        if "allOf" in schema_copy and isinstance(schema_copy["allOf"], list):
            subschemas = schema_copy.pop("allOf")
            for sub in subschemas:
                if isinstance(sub, dict):
                    merged = dict(sub)
                    merged.update(schema_copy)
                    schema_copy = merged

        # Allowed keys in Google Generative AI Schema proto
        allowed_keys = {
            "type",
            "format",
            "description",
            "nullable",
            "enum",
            "maxItems",
            "minItems",
            "properties",
            "required",
            "items",
            "propertyOrdering",
        }

        cleaned: dict[str, Any] = {}

        # Handle type list e.g. ["string", "null"]
        raw_type = schema_copy.get("type")
        if isinstance(raw_type, list):
            types = [t for t in raw_type if t != "null"]
            if "null" in raw_type:
                schema_copy["nullable"] = True
            schema_copy["type"] = types[0] if types else "string"

        for k, v in schema_copy.items():
            if k not in allowed_keys:
                continue

            if k == "type" and isinstance(v, str):
                cleaned[k] = v.upper()
            elif k == "properties" and isinstance(v, dict):
                cleaned[k] = {
                    prop_name: self._clean_schema(prop_schema)
                    for prop_name, prop_schema in v.items()
                    if isinstance(prop_schema, dict)
                }
            elif k == "items" and isinstance(v, dict):
                cleaned[k] = self._clean_schema(v)
            elif k == "enum" and isinstance(v, list):
                cleaned[k] = [str(x) for x in v]
            elif k == "required" and isinstance(v, list):
                cleaned[k] = [x for x in v if isinstance(x, str)]

            elif isinstance(v, dict):
                cleaned[k] = self._clean_schema(v)
            elif isinstance(v, list):
                cleaned[k] = [self._clean_schema(item) if isinstance(item, dict) else item for item in v]
            else:
                cleaned[k] = v

        if "properties" in cleaned or ("type" not in cleaned and "items" not in cleaned):
            cleaned.setdefault("type", "OBJECT")
        elif "items" in cleaned and "type" not in cleaned:
            cleaned["type"] = "ARRAY"

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
                part = {
                    "functionResponse": {
                        "name": tool_name,
                        "response": {"name": tool_name, "content": tool_content},
                    }
                }
                if contents and contents[-1].get("role") == "user" and any("functionResponse" in p for p in contents[-1].get("parts", [])):
                    contents[-1]["parts"].append(part)
                else:
                    contents.append({
                        "role": "user",
                        "parts": [part],
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

                        sig = (
                            tc.get("thought_signature")
                            or tc.get("thoughtSignature")
                            or fn.get("thought_signature")
                            or fn.get("thoughtSignature")
                        )

                        fc_obj: dict[str, Any] = {
                            "name": fn_name,
                            "args": args,
                        }
                        part_dict: dict[str, Any] = {
                            "functionCall": fc_obj
                        }
                        if sig:
                            part_dict["thoughtSignature"] = sig

                        parts.append(part_dict)

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
        gen_cfg: dict[str, Any] = {
            "temperature": config.temperature,
            "maxOutputTokens": config.max_tokens,
            "topP": config.top_p,
        }

        # Handle Gemini thinking configuration based on models.dev and config.thinking
        from jarvis.providers.models_dev import (
            get_model_info,
            has_configurable_reasoning,
        )

        model_info = get_model_info(config.model, config.provider_id or "google")

        if not config.thinking or config.reasoning_effort == "none":
            if has_configurable_reasoning(config.model, config.provider_id or "google", model_info):
                gen_cfg["thinkingConfig"] = {"thinkingBudget": 0}
            # For only-thinking models, do not set thinkingBudget: 0 to avoid breaking requests
        elif config.thinking:
            if has_configurable_reasoning(config.model, config.provider_id or "google", model_info):
                if config.thinking_budget is not None:
                    gen_cfg["thinkingConfig"] = {"thinkingBudget": config.thinking_budget}

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": gen_cfg,
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


    def _extract_thought_signature(
        self, part: dict[str, Any], fc: dict[str, Any]
    ) -> str | None:
        """Extract thought_signature / thoughtSignature if present."""
        return (
            part.get("thought_signature")
            or part.get("thoughtSignature")
            or fc.get("thought_signature")
            or fc.get("thoughtSignature")
        )

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
                if part.get("thought"):
                    content_parts.append(f"<think>\n{part['text']}\n</think>")
                else:
                    content_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                sig = self._extract_thought_signature(part, fc)
                tc_dict: dict[str, Any] = {
                    "id": f"call_{fc['name']}",
                    "type": "function",
                    "function": {
                        "name": fc["name"],
                        "arguments": json.dumps(fc.get("args", {})),
                    },
                }
                if sig:
                    tc_dict["thought_signature"] = sig
                tool_calls.append(tc_dict)

        usage_meta = data.get("usageMetadata", {})

        return GenerationResponse(
            content="\n".join(content_parts),
            role="assistant",
            tool_calls=tool_calls,
            finish_reason=candidate.get("finishReason", "").lower() if candidate.get("finishReason") else None,
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
                sig = self._extract_thought_signature(part, fc)
                tc_dict: dict[str, Any] = {
                    "id": f"call_{fc['name']}",
                    "type": "function",
                    "function": {
                        "name": fc["name"],
                        "arguments": json.dumps(fc.get("args", {})),
                    },
                }
                if sig:
                    tc_dict["thought_signature"] = sig
                tool_calls.append(tc_dict)

        finish_reason = candidates[0].get("finishReason")
        return StreamChunk(
            content=text,
            tool_calls=tool_calls,
            finish_reason=finish_reason.lower() if finish_reason else None,
        )
