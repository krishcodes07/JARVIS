"""
Telegram Message Formatter — Converts standard LLM Markdown into clean Telegram-compliant HTML.
"""

from __future__ import annotations

import html
import re


def _extract_and_format_tables(text: str, table_blocks: list[str]) -> str:
    """Extract Markdown tables and convert them to formatted monospace pre blocks for Telegram."""
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
                escaped_table = html.escape(table_str, quote=False)
                idx = len(table_blocks)
                table_blocks.append(f"<pre><code>{escaped_table}</code></pre>")
                new_lines.append(f"\x00TABLEBLOCK{idx}\x00")
                i = j
                continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines)


def markdown_to_telegram_html(text: str) -> str:
    """Convert standard LLM Markdown text into valid Telegram HTML format.

    Handles:
    - Code blocks (fenced ```lang ... ```) with HTML escaping
    - Tables (Markdown | ... |) aligned into monospace pre blocks
    - Inline code (`...`) with HTML escaping
    - Bold (**text** or __text__)
    - Italic (*text* or _text_)
    - Strikethrough (~~text~~)
    - Underline (<u>text</u> or __text__)
    - Markdown links [text](url) -> <a href="url">text</a>
    - Headers (# Header -> <b>Header</b>)
    - Blockquotes (> text -> <blockquote>text</blockquote>)
    - Bullet points (* or - -> •)
    - Horizontal rules (--- -> ──────────────)

    Args:
        text: Raw markdown text from LLM.

    Returns:
        Telegram-compliant HTML string.
    """
    if not text:
        return ""

    code_blocks: list[str] = []
    inline_codes: list[str] = []
    think_blocks: list[str] = []
    table_blocks: list[str] = []

    # 0. Extract and format <think>...</think> blocks as expandable blockquotes
    def _save_think_block(match: re.Match[str]) -> str:
        thought_content = match.group(1).strip()
        if not thought_content:
            return ""
        formatted_thought = markdown_to_telegram_html(thought_content)
        idx = len(think_blocks)
        tag = f"<blockquote expandable>💭 <b>Thought</b>\n{formatted_thought}</blockquote>\n\n"
        think_blocks.append(tag)
        return f"\x00THINKBLOCK{idx}\x00"

    processed = re.sub(
        r"<(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>(.*?)(?:</(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>|$)",
        _save_think_block,
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # 1. Extract and protect fenced code blocks using non-colliding null byte tokens
    def _save_code_block(match: re.Match[str]) -> str:
        lang = match.group(1).strip() if match.group(1) else ""
        code = match.group(2)
        escaped_code = html.escape(code.rstrip())
        idx = len(code_blocks)
        if lang:
            tag = f'<pre><code class="language-{html.escape(lang)}">{escaped_code}</code></pre>'
        else:
            tag = f"<pre><code>{escaped_code}</code></pre>"
        code_blocks.append(tag)
        return f"\x00CODEBLOCK{idx}\x00"

    processed = re.sub(
        r"```([a-zA-Z0-9_\-\+]*)\n?(.*?)```",
        _save_code_block,
        processed,
        flags=re.DOTALL,
    )

    # 2. Extract and protect inline code `code` using non-colliding null byte tokens
    def _save_inline_code(match: re.Match[str]) -> str:
        code = match.group(1)
        escaped_code = html.escape(code)
        idx = len(inline_codes)
        inline_codes.append(f"<code>{escaped_code}</code>")
        return f"\x00INLINECODE{idx}\x00"

    processed = re.sub(r"`([^`\n]+)`", _save_inline_code, processed)

    # 3. Extract and format Markdown tables into aligned monospace pre blocks
    processed = _extract_and_format_tables(processed, table_blocks)

    # 4. HTML escape normal text (prevents unescaped < > & in general text from breaking Telegram parser)
    processed = html.escape(processed, quote=False)

    # 5. Headers: convert # Header -> <b>Header</b>
    processed = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", processed, flags=re.MULTILINE)

    # 6. Bold: **bold** or __bold__ (word boundary safe)
    processed = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", processed, flags=re.DOTALL)
    processed = re.sub(r"(?<![a-zA-Z0-9])__(.+?)__(?![a-zA-Z0-9])", r"<b>\1</b>", processed, flags=re.DOTALL)

    # 7. Italic: *italic* or _italic_ (be careful with isolated underscores)
    processed = re.sub(r"(?<![a-zA-Z0-9\*])\*([^\*\n]+?)\*(?![a-zA-Z0-9\*])", r"<i>\1</i>", processed)
    processed = re.sub(r"(?<![a-zA-Z0-9_])_([^_\n]+?)_(?![a-zA-Z0-9_])", r"<i>\1</i>", processed)

    # 8. Strikethrough: ~~text~~
    processed = re.sub(r"~~(.+?)~~", r"<s>\1</s>", processed, flags=re.DOTALL)

    # 9. Markdown Links: [text](url) -> <a href="url">text</a>
    def _format_link(match: re.Match[str]) -> str:
        link_text = match.group(1)
        url = match.group(2)
        url_clean = html.unescape(url)
        return f'<a href="{html.escape(url_clean)}">{link_text}</a>'

    processed = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _format_link, processed)

    # 10. Blockquotes: > quote
    def _format_blockquote(match: re.Match[str]) -> str:
        content = match.group(1)
        return f"<blockquote>{content}</blockquote>"

    processed = re.sub(r"^&gt;\s*(.+)$", _format_blockquote, processed, flags=re.MULTILINE)

    # 11. Lists & Rules
    processed = re.sub(r"^[\*\-\+]\s+", "• ", processed, flags=re.MULTILINE)
    processed = re.sub(r"^(?:---|___|\*\*\*)$", "────────────────", processed, flags=re.MULTILINE)

    # 12. Restore inline code
    for idx, inline_html in enumerate(inline_codes):
        placeholder = f"\x00INLINECODE{idx}\x00"
        processed = processed.replace(placeholder, inline_html)

    # 13. Restore code blocks
    for idx, block_html in enumerate(code_blocks):
        placeholder = f"\x00CODEBLOCK{idx}\x00"
        processed = processed.replace(placeholder, block_html)

    # 14. Restore table blocks
    for idx, table_html in enumerate(table_blocks):
        placeholder = f"\x00TABLEBLOCK{idx}\x00"
        processed = processed.replace(placeholder, table_html)

    # 15. Restore think blocks
    for idx, think_html in enumerate(think_blocks):
        placeholder = f"\x00THINKBLOCK{idx}\x00"
        processed = processed.replace(placeholder, think_html)

    return processed
