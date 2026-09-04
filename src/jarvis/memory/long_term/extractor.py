"""
Long-Term Memory Extractor — Extracts memorable facts from conversations.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from jarvis.providers.base import BaseProvider, GenerationConfig, Message

logger = logging.getLogger(__name__)


class MemoryExtractionError(RuntimeError):
    """Raised when the extraction LLM call itself fails.

    Distinguishes a broken configuration (bad model id, missing key, provider
    outage) from the ordinary case of the model deciding there is nothing worth
    remembering, which returns an empty list.
    """

_EXTRACTION_PROMPT = """You are JARVIS's long-term memory system. Your job is to identify
information from a conversation that is worth remembering, updating, or deleting across future sessions.

BE SELECTIVE. Only operate on memories when it is genuinely important and will matter
again later. Do NOT save random, trivial, or one-off things (casual remarks,
small talk, daily status updates, ordinary questions, or generic answers).

Memories must be ALL of:
- Durable (true beyond this conversation)
- High-value (knowing it later genuinely helps the user)
- Personal, actionable, or factual (user preferences, identity, background,
  long-term instructions, project conventions, important facts)

Categories:
- "fact"        — factual information about the user or their world
- "preference"  — user likes/dislikes or style preferences
- "instruction" — long-term instructions or rules to follow
- "identity"    — who the user is (name, job, background)
- "project"     — details about the user's projects or codebases

Operations you can perform:
1. "add": Create a NEW memory when durable, high-value information appears that is NOT covered by existing memories.
   Each item must have:
   - "action": "add"
   - "key": short descriptive snake_case identifier (e.g. "favorite_ide")
   - "content": the memory text (1-2 sentences, self-contained)
   - "category": one of fact, preference, instruction, identity, project

2. "edit": EDIT an existing memory when the conversation updates, corrects, or replaces information in it.
   Each item must have:
   - "action": "edit"
   - "key": the exact key of the existing memory being modified
   - "content": the updated memory text (1-2 sentences, self-contained)
   - "category": (optional) updated category

3. "delete": DELETE an existing memory when the user explicitly asks to forget or remove something, or when an existing fact/preference/project is cancelled, abandoned, or no longer true.
   Each item must have:
   - "action": "delete"
   - "key": the exact key of the existing memory to remove

Important Rules:
- If there is NO new information, no updates, and no deletions needed, return an empty array `[]`.
- Do NOT re-save or create near-duplicates of existing memories.
- For "edit" and "delete", "key" MUST match one of the keys in Existing memories below.
- Return STRICTLY a valid JSON array of operation objects.
- Output ONLY the raw JSON. Do NOT include any explanations, notes, or markdown text before or after the JSON.

Existing memories:
{existing}

Conversation:
"""


class MemoryExtractor:
    """Extracts key facts, preferences, and instructions from conversations.

    Uses the active LLM provider to identify information worth remembering,
    updating, or deleting long-term and returns operations ready for storage.
    """

    def __init__(self, provider: BaseProvider, model: str) -> None:
        self._provider = provider
        self._model = model

    async def extract(
        self,
        messages: list[dict[str, Any]],
        existing_memories: list[dict[str, Any]] | list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract memorable operations (add, edit, delete) from a conversation segment.

        Args:
            messages: Recent conversation messages to analyze.
            existing_memories: Already-stored memories with keys and contents,
                used to match existing memories for edit/delete or avoid duplicates.

        Returns:
            List of memory operations with 'action' ("add", "edit", "delete"),
            'key', and where applicable 'content' and 'category'.
            Empty if there is nothing worth remembering or updating.

        Raises:
            MemoryExtractionError: If the LLM call fails (bad model id, missing
                API key, provider error).
        """
        conversation_text = self._serialize_messages(messages)
        if not conversation_text.strip():
            return []

        existing_lines: list[str] = []
        if existing_memories:
            for m in existing_memories:
                if isinstance(m, dict):
                    key = m.get("key", "")
                    content = m.get("content", "")
                    category = m.get("category", "")
                    cat_info = f" [{category}]" if category else ""
                    existing_lines.append(f"- key: {key}{cat_info} -> {content}")
                else:
                    existing_lines.append(f"- {m}")
        existing_text = "\n".join(existing_lines) if existing_lines else "(none)"
        system_prompt = _EXTRACTION_PROMPT.format(existing=existing_text)

        prompt_messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=conversation_text),
        ]
        config = GenerationConfig(
            model=self._model,
            temperature=0.2,
            max_tokens=1024,
            thinking=False,
        )

        try:
            response = await self._provider.generate(prompt_messages, config)
        except Exception as e:
            raise MemoryExtractionError(
                f"Memory extraction call failed for model '{self._model}': {e}"
            ) from e

        logger.debug("Raw memory extraction response: %r", response.content[:300])
        return self._parse_response(response.content)

    def _serialize_messages(self, messages: list[dict[str, Any]]) -> str:
        """Format conversation messages into readable text."""
        parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        return "\n".join(parts)

    def _parse_response(self, content: str) -> list[dict[str, Any]]:
        """Parse the LLM's JSON response into a list of memory operations."""
        if not content or not content.strip():
            return []

        data = self._deserialize_json(content)
        if data is None:
            logger.warning("Could not find or parse JSON in extraction response: %r", content[:200])
            return []

        raw_items: list[dict[str, Any]] = []
        if isinstance(data, list):
            raw_items = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            found_grouped = False
            for action_key in ("add", "edit", "delete", "update", "remove"):
                if action_key in data and isinstance(data[action_key], list):
                    found_grouped = True
                    for sub in data[action_key]:
                        if isinstance(sub, dict):
                            item = dict(sub)
                            item.setdefault("action", action_key)
                            raw_items.append(item)
                        elif isinstance(sub, str) and action_key in ("delete", "remove"):
                            raw_items.append({"action": "delete", "key": sub})
            if not found_grouped:
                for list_key in ("operations", "memories", "actions", "results"):
                    if list_key in data and isinstance(data[list_key], list):
                        raw_items.extend(
                            [item for item in data[list_key] if isinstance(item, dict)]
                        )
                        found_grouped = True
                        break
            if not found_grouped:
                if "action" in data or "content" in data or "key" in data:
                    raw_items.append(data)

        operations: list[dict[str, Any]] = []
        for item in raw_items:
            raw_action = str(item.get("action", "")).strip().lower()
            if raw_action in ("delete", "remove", "drop", "forget"):
                action = "delete"
            elif raw_action in ("edit", "update", "modify", "change", "replace"):
                action = "edit"
            elif raw_action in ("add", "create", "insert", "new", "save"):
                action = "add"
            else:
                action = "add"

            if action == "delete":
                raw_key = item.get("key")
                if not raw_key or not isinstance(raw_key, str) or not raw_key.strip():
                    continue
                operations.append({
                    "action": "delete",
                    "key": self._slugify(raw_key),
                })
            elif action == "edit":
                raw_key = item.get("key")
                raw_content = item.get("content")
                if not raw_key or not isinstance(raw_key, str) or not raw_key.strip():
                    continue
                if not raw_content or not isinstance(raw_content, str) or not raw_content.strip():
                    continue
                operations.append({
                    "action": "edit",
                    "key": self._slugify(raw_key),
                    "content": raw_content.strip(),
                    "category": item.get("category", "fact"),
                })
            else:  # add
                raw_content = item.get("content")
                if not raw_content or not isinstance(raw_content, str) or not raw_content.strip():
                    continue
                raw_key = item.get("key") or raw_content[:40]
                operations.append({
                    "action": "add",
                    "key": self._slugify(raw_key),
                    "content": raw_content.strip(),
                    "category": item.get("category", "fact"),
                })

        return operations

    @staticmethod
    def _deserialize_json(content: str) -> Any:
        """Robustly extract and deserialize JSON from model output.

        Handles:
        - Reasoning tags (<think>...</think>)
        - Markdown code fences (```json ... ```)
        - Trailing explanation text or commentary (prevents Extra Data JSON errors)
        - Newline-delimited JSON objects
        """
        if not content or not content.strip():
            return None

        # Remove reasoning tags if model emitted chain of thought
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE).strip()
        if not cleaned:
            return None

        # 1. Try markdown code fences first
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if fence_match:
            candidate = fence_match.group(1).strip()
            try:
                return json.loads(candidate)
            except Exception:
                pass

        # 2. Try direct load
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        decoder = json.JSONDecoder()
        start_bracket = cleaned.find("[")
        start_brace = cleaned.find("{")

        # 3. If array comes first (or only array exists), decode array
        if start_bracket != -1 and (start_brace == -1 or start_bracket < start_brace):
            try:
                obj, _ = decoder.raw_decode(cleaned[start_bracket:])
                if isinstance(obj, list):
                    return obj
            except Exception:
                pass

        # 4. Check for multiple newline-separated JSON objects
        if cleaned.count("{") > 1:
            items = []
            idx = 0
            while idx < len(cleaned):
                brace_pos = cleaned.find("{", idx)
                if brace_pos == -1:
                    break
                try:
                    obj, end_pos = decoder.raw_decode(cleaned[brace_pos:])
                    if isinstance(obj, dict):
                        items.append(obj)
                    idx = brace_pos + max(1, end_pos)
                except Exception:
                    idx = brace_pos + 1
            if len(items) > 1:
                return items

        # 5. Decode single dict from first {
        if start_brace != -1:
            try:
                obj, _ = decoder.raw_decode(cleaned[start_brace:])
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

        # 6. Any bracket fallback
        if start_bracket != -1:
            try:
                obj, _ = decoder.raw_decode(cleaned[start_bracket:])
                if isinstance(obj, list):
                    return obj
            except Exception:
                pass

        return None

    @staticmethod
    def _slugify(value: str) -> str:
        """Convert a string into a snake_case key."""
        slug = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")
        return slug[:80] or "memory"
