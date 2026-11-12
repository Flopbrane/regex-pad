# pylint: disable=C0114,C0115,C0116,C0301
from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

from editor.tag_insert import wordpress_tag_snippet

PARAGRAPH_BLOCK_PATTERN: re.Pattern[str] = re.compile(
    r"<!--\s+wp:paragraph\s+-->(.*?)<!--\s+/wp:paragraph\s+-->",
    re.DOTALL | re.IGNORECASE,
)
PARAGRAPH_TAG_PATTERN: re.Pattern[str] = re.compile(
    r"<p\b[^>]*>(.*?)</p>",
    re.DOTALL | re.IGNORECASE,
)
LEADING_BREAK_PATTERN: re.Pattern[str] = re.compile(r"^(?:\s*<br\s*/?>\s*)+", re.IGNORECASE)
TRAILING_BREAK_PATTERN: re.Pattern[str] = re.compile(r"(?:\s*<br\s*/?>\s*)+$", re.IGNORECASE)
INFO_FRAME_LABEL_KEY = "tag.wordpress.info_frame_block"


class ParagraphSplitError(ValueError):
    """Raised when paragraph splitting cannot be safely applied."""


@dataclass(frozen=True)
class ParagraphBlock:
    """Represents a WordPress paragraph block in the text."""
    block_start: int
    block_end: int
    content_start: int
    content_end: int


@dataclass(frozen=True)
class ParagraphReplacement:
    """Represents the result of a paragraph replacement operation."""
    text: str
    cursor_position: int


@dataclass(frozen=True)
class _BuiltBlock:
    """Represents a built block with text and cursor offset."""
    text: str
    cursor_offset: int


def find_current_paragraph_block(text: str, cursor_pos: int) -> ParagraphBlock | None:
    """Return the wp:paragraph block containing cursor_pos, if it is simple."""
    for match in PARAGRAPH_BLOCK_PATTERN.finditer(text):
        block_start = match.start()
        block_end = match.end()
        if not block_start <= cursor_pos <= block_end:
            continue

        paragraph_match = PARAGRAPH_TAG_PATTERN.search(match.group(0))
        if paragraph_match is None:
            return None

        return ParagraphBlock(
            block_start=block_start,
            block_end=block_end,
            content_start=block_start + paragraph_match.start(1),
            content_end=block_start + paragraph_match.end(1),
        )
    return None


def build_paragraph_block(content: str) -> str:
    """Build a WordPress paragraph block, or an empty string for empty content."""
    clean_content = _clean_paragraph_edge_breaks(content)
    if not clean_content:
        return ""
    return (
        "<!-- wp:paragraph -->\n"
        f"<p>{clean_content}</p>\n"
        "<!-- /wp:paragraph -->"
    )


def build_spacer_block(height: int = 32) -> str:
    """Build a WordPress spacer block with the specified height."""
    return (
        f'<!-- wp:spacer {{"height":"{height}px"}} -->\n'
        f'<div style="height:{height}px" aria-hidden="true" '
        'class="wp-block-spacer"></div>\n'
        "<!-- /wp:spacer -->"
    )


def build_html_code_block(content: str = "") -> str:
    """Build a WordPress HTML code block with the specified content."""
    escaped_content = escape(_code_text_from_paragraph_content(content), quote=False)
    code_text = escaped_content if escaped_content else "\n"
    block_text = (
        "<!-- wp:html -->\n"
        "<pre\n"
        '    class="wp-block-code"\n'
        '    style="display:inline-block; border:1px solid #999; padding:16px; '
        'border-radius:8px; background-color:#f9f9f9;"\n'
        f"><code>{code_text}</code></pre>\n"
        "<!-- /wp:html -->"
    )
    return block_text


def build_decorated_block(
    content: str = "",
    dictionaries_path: Path | None = None,
) -> str:
    """Build the WordPress info-frame block from the active tag dictionary."""
    return _build_decorated_block(content, dictionaries_path).text


def split_paragraph_insert_spacer(text: str, cursor_pos: int) -> ParagraphReplacement:
    """Insert a spacer block at the cursor position, splitting the current paragraph."""
    block: ParagraphBlock = _paragraph_block_for_range(text, cursor_pos, cursor_pos)
    start: int
    end: int
    start, end = _blank_line_range_at_cursor(text, block, cursor_pos)
    return _replace_current_paragraph_selection(
        text,
        start,
        end,
        _BuiltBlock(build_spacer_block(), len(build_spacer_block())),
    )


def split_paragraph_insert_html(text: str, cursor_pos: int) -> ParagraphReplacement:
    """Insert an HTML code block at the cursor position, splitting the current paragraph."""
    block: ParagraphBlock = _paragraph_block_for_range(text, cursor_pos, cursor_pos)
    start: int
    end: int
    start, end = _blank_line_range_at_cursor(text, block, cursor_pos)
    html_block: str = build_html_code_block()
    cursor_offset: int = html_block.index("<code>\n") + len("<code>\n")
    return _replace_current_paragraph_selection(
        text,
        start,
        end,
        _BuiltBlock(html_block, cursor_offset),
    )


def wrap_selection_as_code_block(
    text: str,
    selection_start: int,
    selection_end: int,
) -> ParagraphReplacement:
    """Wrap the selected text as a WordPress HTML code block, replacing the current paragraph selection."""
    selection_start, selection_end = _expand_selection_to_content_lines(
        text,
        selection_start,
        selection_end,
    )
    selected_text = _selected_text(text, selection_start, selection_end)
    html_block = build_html_code_block(selected_text)
    cursor_offset = html_block.index("</code>")
    return _replace_current_paragraph_selection(
        text,
        selection_start,
        selection_end,
        _BuiltBlock(html_block, cursor_offset),
    )


def wrap_selection_as_decorated_block(
    text: str,
    selection_start: int,
    selection_end: int,
    dictionaries_path: Path | None = None,
) -> ParagraphReplacement:
    """Wrap the selected text as a WordPress HTML decorated block, replacing the current paragraph selection."""
    selection_start, selection_end = _expand_selection_to_content_lines(
        text,
        selection_start,
        selection_end,
    )
    selected_text = _selected_text(text, selection_start, selection_end)
    decorated_block = _build_decorated_block(selected_text, dictionaries_path)
    return _replace_current_paragraph_selection(
        text,
        selection_start,
        selection_end,
        decorated_block,
    )


def _build_decorated_block(
    content: str,
    dictionaries_path: Path | None,
) -> _BuiltBlock:
    """Render the dictionary-backed info frame and retain its cursor position."""
    try:
        snippet = wordpress_tag_snippet(INFO_FRAME_LABEL_KEY, dictionaries_path)
    except (OSError, TypeError, ValueError) as error:
        raise ParagraphSplitError(
            f"枠組み指定の辞書を読み込めません: {error}"
        ) from error
    body = _decorated_text_from_paragraph_content(content)
    rendered_text, cursor_offset = snippet.render(body)
    return _BuiltBlock(rendered_text, cursor_offset)


def _replace_current_paragraph_selection(
    text: str,
    selection_start: int,
    selection_end: int,
    inserted_block: _BuiltBlock,
) -> ParagraphReplacement:
    """Replace the current paragraph selection with the inserted block, returning the new text and cursor position."""
    start: int = min(selection_start, selection_end)
    end: int = max(selection_start, selection_end)
    block: ParagraphBlock = _paragraph_block_for_range(text, start, end)
    before_content: str = text[block.content_start:start]
    after_content: str = text[end:block.content_end]
    before_block: str = build_paragraph_block(before_content)
    after_block: str = build_paragraph_block(after_content)
    replacement_text: str
    cursor_offset: int
    replacement_text, cursor_offset = _join_split_blocks(
        before_block,
        inserted_block,
        after_block,
    )
    new_text: str = text[: block.block_start] + replacement_text + text[block.block_end :]
    return ParagraphReplacement(
        text=new_text,
        cursor_position=block.block_start + cursor_offset,
    )


def _paragraph_block_for_range(text: str, start: int, end: int) -> ParagraphBlock:
    """Return the wp:paragraph block containing the range [start, end), or raise an error if not valid."""
    block: ParagraphBlock | None = find_current_paragraph_block(text, start)
    if block is None:
        raise ParagraphSplitError("現在の位置では段落分割できません。")

    check_pos: int = max(start, end - 1)
    end_block: ParagraphBlock | None = find_current_paragraph_block(text, check_pos)
    if end_block != block:
        raise ParagraphSplitError(
            "選択範囲が複数ブロックにまたがっているため、処理を中止しました。"
        )

    if start < block.content_start or end > block.content_end:
        raise ParagraphSplitError("現在の位置では段落分割できません。")
    return block


def _blank_line_range_at_cursor(
    text: str,
    block: ParagraphBlock,
    cursor_pos: int,
) -> tuple[int, int]:
    """Return the range of the blank line at the cursor position within the paragraph block, or raise an error if not valid."""
    content = text[block.content_start : block.content_end]
    relative_pos = min(max(cursor_pos - block.content_start, 0), len(content))
    line_start = content.rfind("\n", 0, relative_pos) + 1
    line_end = content.find("\n", relative_pos)
    if line_end == -1:
        line_end = len(content)

    if content[line_start:line_end].strip():
        raise ParagraphSplitError(
            "スペーサー挿入は、ユーザーが改行して作った空行で右クリックしてください。"
        )
    return block.content_start + line_start, block.content_start + line_end


def _expand_selection_to_content_lines(
    text: str,
    selection_start: int,
    selection_end: int,
) -> tuple[int, int]:
    """Expand the selection to include entire lines of content within the paragraph block."""
    start = min(selection_start, selection_end)
    end = max(selection_start, selection_end)
    if start == end:
        return start, end

    block: ParagraphBlock = _paragraph_block_for_range(text, start, end)
    content = text[block.content_start : block.content_end]
    relative_start = start - block.content_start
    relative_end = end - block.content_start
    line_start = content.rfind("\n", 0, relative_start) + 1
    line_end_lookup = max(relative_start, relative_end - 1)
    line_end = content.find("\n", line_end_lookup)
    if line_end == -1:
        line_end = len(content)
    return block.content_start + line_start, block.content_start + line_end


def _join_split_blocks(
    before_block: str,
    inserted_block: _BuiltBlock,
    after_block: str,
) -> tuple[str, int]:
    """Join the before, inserted, and after blocks into a single replacement text, returning the new text and cursor offset."""
    pieces: list[tuple[str, int | None]] = []
    if before_block:
        pieces.append((before_block, None))
    pieces.append((inserted_block.text, inserted_block.cursor_offset))
    if after_block:
        pieces.append((after_block, None))

    replacement_text = ""
    cursor_offset = 0
    for index, (piece, piece_cursor_offset) in enumerate(pieces):
        if index > 0:
            replacement_text += "\n\n"
        if piece_cursor_offset is not None:
            cursor_offset = len(replacement_text) + piece_cursor_offset
        replacement_text += piece
    return replacement_text, cursor_offset


def _selected_text(text: str, selection_start: int, selection_end: int) -> str:
    """Return the text within the specified selection range."""
    start = min(selection_start, selection_end)
    end = max(selection_start, selection_end)
    return text[start:end]


def _clean_paragraph_edge_breaks(content: str) -> str:
    """Remove leading and trailing <br> tags from the paragraph content."""
    clean_content = content.strip()
    previous = None
    while clean_content != previous:
        previous = clean_content
        clean_content = LEADING_BREAK_PATTERN.sub("", clean_content).strip()
        clean_content = TRAILING_BREAK_PATTERN.sub("", clean_content).strip()
    return clean_content


def _code_text_from_paragraph_content(content: str) -> str:
    """Extract the code text from the paragraph content, replacing <br> tags with newlines."""
    clean_content = _clean_paragraph_edge_breaks(content)
    return re.sub(r"\s*<br\s*/?>\s*", "\n", clean_content, flags=re.IGNORECASE).strip()


def _decorated_text_from_paragraph_content(content: str) -> str:
    """Extract the decorated text from the paragraph content, replacing <br> tags with <br>."""
    code_text = _code_text_from_paragraph_content(content)
    if not code_text:
        return ""
    lines = [line.strip() for line in code_text.splitlines()]
    return "<br>\n".join(line for line in lines if line)
