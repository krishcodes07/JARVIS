"""
Discord Message Formatter — Converts LLM Markdown and Thoughts into Discord-compliant Markdown.
"""

from __future__ import annotations

import re


def _format_markdown_tables(text: str, table_blocks: list[str]) -> str:
    """Extract Markdown tables and convert them to formatted monospace code blocks for Discord."""
    lines = text.split("\n")
    new_lines: list[str] = []
    i = 0
    n = len(lines)

    def _is_separator(line_str: str) -> bool:
        s = line_str.strip()
        if not s or "|" not in s or "-" not in s:
            return False
        return all(c in "-|: \t" for c in s)

    def _is_row(line_str: str) -> bool:
        s = line_str.strip()
        return bool(s and "|" in s)

    def _parse_cells(line_str: str) -> list[str]:
        s = line_str.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        return [c.strip() for c in s.split("|")]

    while i < n:
        line = lines[i]
        # Check if line i and line i+1 form a table header + separator
        if i + 1 < n and _is_row(line) and _is_separator(lines[i + 1]):
            header_cells = _parse_cells(line)
            sep_cells = _parse_cells(lines[i + 1])
            data_rows: list[list[str]] = []
            j = i + 2
            while j < n and _is_row(lines[j]) and not _is_separator(lines[j]):
                data_rows.append(_parse_cells(lines[j]))
                j += 1

            num_cols = max(len(header_cells), max((len(r) for r in data_rows), default=0))
            if num_cols > 0:
                alignments: list[str] = []
                for c in range(num_cols):
                    if c < len(sep_cells):
                        sc = sep_cells[c]
                        if sc.startswith(":") and sc.endswith(":"):
                            alignments.append("center")
                        elif sc.endswith(":"):
                            alignments.append("right")
                        else:
                            alignments.append("left")
                    else:
                        alignments.append("left")

                col_widths: list[int] = []
                for c in range(num_cols):
                    h_len = len(header_cells[c]) if c < len(header_cells) else 0
                    d_len = max((len(r[c]) for r in data_rows if c < len(r)), default=0)
                    col_widths.append(max(h_len, d_len, 1))

                def _pad(val: str, width: int, align: str) -> str:
                    if align == "center":
                        return val.center(width)
                    elif align == "right":
                        return val.rjust(width)
                    return val.ljust(width)

                header_line = " │ ".join(
                    _pad(header_cells[c] if c < len(header_cells) else "", col_widths[c], alignments[c])
                    for c in range(num_cols)
                )
                sep_line = "─┼─".join("─" * col_widths[c] for c in range(num_cols))
                formatted_rows = [header_line, sep_line]
                for r in data_rows:
                    row_line = " │ ".join(
                        _pad(r[c] if c < len(r) else "", col_widths[c], alignments[c])
                        for c in range(num_cols)
                    )
                    formatted_rows.append(row_line)

                table_str = "\n".join(formatted_rows)
                idx = len(table_blocks)
                table_blocks.append(f"```text\n{table_str}\n```")
                new_lines.append(f"\x00TABLEBLOCK{idx}\x00")
                i = j
                continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines)


def markdown_to_discord_markdown(text: str) -> str:
    """Convert standard LLM Markdown text into clean Discord-compliant Markdown.

    Handles:
    - Thoughts (<think>...</think>) into Discord expandable spoiler blockquotes
    - Tables (| ... |) aligned into clean monospace ```text code blocks
    - Fenced code blocks and inline code preservation
    - Clean whitespace trimming

    Args:
        text: Raw markdown text from LLM.

    Returns:
        Discord-formatted markdown string.
    """
    if not text:
        return ""

    code_blocks: list[str] = []
    think_blocks: list[str] = []
    table_blocks: list[str] = []

    # 0. Extract and format <think>...</think> blocks
    def _save_think_block(match: re.Match[str]) -> str:
        thought_content = match.group(1).strip()
        if not thought_content:
            return ""
        # Format thought inner text recursively
        formatted_thought = markdown_to_discord_markdown(thought_content)
        # In Discord, spoiler tags ||...|| make text click-to-reveal
        # Format each line inside blockquote
        quoted_lines = "\n> ".join(formatted_thought.split("\n"))
        tag = f"> 💭 **Thought**\n> ||{quoted_lines}||\n\n"
        idx = len(think_blocks)
        think_blocks.append(tag)
        return f"\x00THINKBLOCK{idx}\x00"

    processed = re.sub(
        r"<think>(.*?)(?:</think>|$)",
        _save_think_block,
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # 1. Extract and protect fenced code blocks
    def _save_code_block(match: re.Match[str]) -> str:
        idx = len(code_blocks)
        code_blocks.append(match.group(0))
        return f"\x00CODEBLOCK{idx}\x00"

    processed = re.sub(
        r"```[a-zA-Z0-9_\-\+]*\n?.*?```",
        _save_code_block,
        processed,
        flags=re.DOTALL,
    )

    # 2. Extract and format Markdown tables
    processed = _format_markdown_tables(processed, table_blocks)

    # 3. Restore code blocks
    for idx, block_code in enumerate(code_blocks):
        placeholder = f"\x00CODEBLOCK{idx}\x00"
        processed = processed.replace(placeholder, block_code)

    # 4. Restore table blocks
    for idx, table_code in enumerate(table_blocks):
        placeholder = f"\x00TABLEBLOCK{idx}\x00"
        processed = processed.replace(placeholder, table_code)

    # 5. Restore think blocks
    for idx, think_text in enumerate(think_blocks):
        placeholder = f"\x00THINKBLOCK{idx}\x00"
        processed = processed.replace(placeholder, think_text)

    return processed.strip()


def split_discord_message(text: str, max_length: int = 2000) -> list[str]:
    """Split a long Discord message into chunks within the Discord character limit.

    Args:
        text: Formatted text to split.
        max_length: Maximum characters per chunk (default 2000).

    Returns:
        List of message chunk strings.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while len(remaining) > max_length:
        # Try to split at a paragraph boundary
        split_idx = remaining.rfind("\n\n", 0, max_length)
        if split_idx == -1 or split_idx < max_length // 3:
            # Try to split at a single line break
            split_idx = remaining.rfind("\n", 0, max_length)
        if split_idx == -1 or split_idx < max_length // 3:
            # Try to split at a space
            split_idx = remaining.rfind(" ", 0, max_length)
        if split_idx == -1:
            # Hard split if no suitable whitespace found
            split_idx = max_length

        chunk = remaining[:split_idx].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_idx:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks or [text]
