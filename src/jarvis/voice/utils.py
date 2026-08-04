"""Voice subsystem utility functions."""

from __future__ import annotations

import re


def strip_markdown_for_speech(text: str) -> str:
    """Strip markdown formatting syntax from text so TTS synthesizes clean natural speech.

    Removes markdown headers (#, ##), bold/italic asterisks (*, **), underscores (_, __),
    strikethrough (~~), code backticks (`), links, images, blockquotes (>), and bullet points (- * +).
    """
    if not text:
        return ""

    # Remove code blocks entirely ``` ... ```
    cleaned = re.sub(r"```[\s\S]*?```", "", text)
    # Inline code `code`: keep inner code text without backticks
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    # Remove HTML tags
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Image tags ![alt](url) -> alt
    cleaned = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", cleaned)
    # Links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    # Headers #, ##, ### at start of line
    cleaned = re.sub(r"^\s*#+\s*", "", cleaned, flags=re.MULTILINE)
    # Bold / italics ***word***, **word**, *word*
    cleaned = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", cleaned)
    # Bold / italics ___word___, __word__, _word_
    cleaned = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", cleaned)
    # Strikethrough ~~word~~
    cleaned = re.sub(r"~~(.*?)~~", r"\1", cleaned)
    # Blockquotes >
    cleaned = re.sub(r"^\s*>\s*", "", cleaned, flags=re.MULTILINE)
    # Bullet points -, *, + at start of line
    cleaned = re.sub(r"^\s*[\-\*\+]\s+", "", cleaned, flags=re.MULTILINE)
    # Numbered list markers 1., 2. at start of line
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)
    # Horizontal rules ---, ***, ___
    cleaned = re.sub(r"^\s*[\-\*_]{3,}\s*$", "", cleaned, flags=re.MULTILINE)
    # Strip any remaining stray markdown characters like #, *, _, ~, `
    cleaned = re.sub(r"#+", "", cleaned)
    cleaned = re.sub(r"[\*\_\~\`]+", "", cleaned)
    # Collapse multiple consecutive empty newlines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()
