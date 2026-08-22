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
information from a conversation that is worth remembering across future sessions.

BE SELECTIVE. Only write a memory when it is genuinely important and will matter
again later. Do NOT save random, trivial, or one-off things (casual remarks,
small talk, daily status updates, ordinary questions, or generic answers).

Save only information that is ALL of:
- Durable (true beyond this conversation)
- High-value (knowing it later genuinely helps the user)
- Personal, actionable, or factual (user preferences, identity, background,
  long-term instructions, project conventions, important facts)

Categories:
- "fact"       — factual information about the user or their world
- "preference" — user likes/dislikes or style preferences
- "instruction"— long-term instructions or rules to follow
- "identity"   — who the user is (name, job, background)
- "project"    — details about the user's projects or codebases

Return STRICTLY a JSON array. Each item must have:
- "content": the memory text (1-2 sentences, self-contained)
- "category": one of fact, preference, instruction, identity, project
- "key": a short snake_case identifier (e.g. "user_prefers_dark_mode")

Most important thing if their was no important information etc. in the session then dont create any memories and return empty array.
Already-stored memories are listed below. Do NOT re-save anything that is already
covered by an existing memory, and do NOT create near-duplicates. If the new
conversation only confirms existing memories, return an empty array.

Existing memories:
{existing}

Conversation:
"""


class MemoryExtractor:
    """Extracts key facts, preferences, and instructions from conversations.

    Uses the active LLM provider to identify information worth remembering
    long-term and returns it in a structured form ready for storage.
    """

    def __init__(self, provider: BaseProvider, model: str) -> None:
        self._provider = provider
        self._model = model

    async def extract(
        self,
        messages: list[dict[str, Any]],
        existing_memories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract memorable facts from a conversation segment.

        Args:
            messages: Recent conversation messages to analyze.
            existing_memories: Contents of already-stored memories, used to
                avoid writing duplicates.

        Returns:
            List of extracted memories with 'content', 'category', and 'key'.
            Empty if there is nothing worth remembering.

        Raises:
            MemoryExtractionError: If the LLM call fails (bad model id, missing
                API key, provider error). Swallowing this would make long-term
                memory look permanently empty with no explanation.
        """
        conversation_text = self._serialize_messages(messages)
        if not conversation_text.strip():
            return []

        existing_text = (
            "\n".join(f"- {m}" for m in existing_memories)
            if existing_memories
            else "(none)"
        )
        system_prompt = _EXTRACTION_PROMPT.format(existing=existing_text)

        prompt_messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=conversation_text),
        ]
        config = GenerationConfig(
            model=self._model,
            temperature=0.2,
            max_tokens=1024,
        )

        try:
            response = await self._provider.generate(prompt_messages, config)
        except Exception as e:
            raise MemoryExtractionError(
                f"Memory extraction call failed for model '{self._model}': {e}"
            ) from e

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
        """Parse the LLM's JSON response into a list of memories."""
        if not content:
            return []

        cleaned = self._extract_json(content)
        if not cleaned:
            logger.warning("No JSON found in extraction response.")
            return []

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse extraction JSON: {e}")
            return []

        if not isinstance(data, list):
            logger.warning("Extraction response was not a JSON array.")
            return []

        memories: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            memory_content = item.get("content")
            if not memory_content or not isinstance(memory_content, str):
                continue
            memories.append({
                "content": memory_content.strip(),
                "category": item.get("category", "fact"),
                "key": self._slugify(item.get("key") or memory_content[:40]),
            })
        return memories

    @staticmethod
    def _extract_json(content: str) -> str:
        """Extract the first JSON array from the LLM response."""
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            return match.group(0)
        return ""

    @staticmethod
    def _slugify(value: str) -> str:
        """Convert a string into a snake_case key."""
        slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        return slug[:80] or "memory"
