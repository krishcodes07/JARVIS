"""Voice subsystem utility functions."""

from __future__ import annotations

import re

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # geometric shapes extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows-c
    "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    "\U0001FB00-\U0001FBFF"  # symbols for legacy computing
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # enclosed characters
    "\U00002600-\U000026FF"  # miscellaneous symbols
    "\U00002300-\U000023FF"  # miscellaneous technical
    "\U00002B00-\U00002BFF"  # miscellaneous symbols and arrows
    "\U0000200D"              # zero width joiner
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0001F3FB-\U0001F3FF"  # skin tone modifiers
    "]+",
    flags=re.UNICODE,
)


def strip_markdown_for_speech(text: str) -> str:
    """Strip markdown formatting syntax, emojis, and thinking/reasoning blocks from text
    so TTS synthesizes clean natural speech without speaking internal thoughts or emojis.

    Removes:
    - Thinking/reasoning tags (<think>...</think>, <thought>...</thought>, <reasoning>...</reasoning>, and salted variants)
    - Code blocks (``` ... ```)
    - Inline code backticks (`code` -> code)
    - General HTML tags
    - Markdown headers (#, ##), bold/italic asterisks (*, **), underscores (_, __)
    - Strikethrough (~~), links, images, blockquotes (>), and bullet/numbered list markers
    - Emojis and pictorial symbols
    """
    if not text:
        return ""

    # Remove thinking / reasoning blocks entirely (<think>...</think>, <thought>...</thought>, etc.)
    cleaned = re.sub(
        r"<(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>(.*?)(?:</(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>|$)",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Remove details/summary thought blocks if any
    cleaned = re.sub(
        r"<details[^>]*>\s*<summary[^>]*>.*?</summary>(.*?)</details>",
        "",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Remove code blocks entirely ``` ... ```
    cleaned = re.sub(r"```[\s\S]*?```", "", cleaned)
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
    # Strip emojis and symbols
    cleaned = EMOJI_PATTERN.sub("", cleaned)
    # Clean up any leftover multiple spaces on lines
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    # Clean up spaces before punctuation
    cleaned = re.sub(r"\s+([,.?!;:])", r"\1", cleaned)
    # Collapse multiple consecutive empty newlines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


