"""
System Prompt Builder — Constructs the full system prompt for the LLM.

Combines persona, memory context, and tool descriptions into a
comprehensive system prompt.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class SystemPromptBuilder:
    """Builds the complete system prompt for JARVIS.

    The system prompt includes:
    1. JARVIS persona and behavior guidelines
    2. Relevant memory context
    3. Available tool descriptions
    """

    def build(
        self,
        persona: str = "",
        memory_context: str = "",
        tool_descriptions: str = "",
        capability_summary: str = "",
        **kwargs: Any,
    ) -> str:
        """Build the complete system prompt.

        Args:
            persona: JARVIS persona instructions.
            memory_context: Relevant memory context.
            tool_descriptions: Available tool descriptions.
            capability_summary: Summary of all available tool categories & meta capabilities.

        Returns:
            Complete system prompt string.
        """
        parts = [persona]
        date = datetime.now().strftime("%Y-%m-%d")

        parts.append(f"\n## Current Date\n{date}, always refer to this date only, dont use any previous year or anthing for your responses")
        if capability_summary:
            parts.append(f"\n## Capabilities & Tool Discovery\n{capability_summary}")

        if memory_context:
            parts.append(f"\n## Memory Context\n{memory_context}")

        if tool_descriptions:
            parts.append(f"\n## Active Loaded Tool Schemas\n{tool_descriptions}")

        return "\n\n".join(part for part in parts if part.strip())
