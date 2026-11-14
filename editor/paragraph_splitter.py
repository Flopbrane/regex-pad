# pylint: disable=C0114,C0115,C0116,C0301
from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

from editor.paragraph_insert_rules import (
    ParagraphInsertDictionaryError,
    ParagraphInsertRule,
    ParagraphInsertRuleBook,
    TextReplacementRule,
    load_paragraph_insert_rule_book,
)
from search.search_engine import SearchEngine, SearchOptions

INSERT_SPACER_KEY = "insert_spacer"
INSERT_HTML_KEY = "insert_html"
DECORATED_BLOCK_KEY = "decorated_block"
DICTIONARY_ERROR_KEY = "paragraph_split.dictionary_error"
INVALID_RULE_KEY = "paragraph_split.invalid_rule"
SELECTION_PLACEHOLDER = "{selection}"
CURSOR_PLACEHOLDER = "{cursor}"


class ParagraphSplitError(ValueError):
    """Raised when paragraph insertion cannot be safely applied."""

    def __init__(
        self,
        message_key: str,
        values: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message_key)
        self.message_key = message_key
        self.values = values or {}


@dataclass(frozen=True)
class ParagraphBlock:
    """Represents one simple WordPress paragraph block in the text."""

    block_start: int
    block_end: int
    content_start: int
    content_end: int
    attributes: str = ""


@dataclass(frozen=True)
class ParagraphReplacement:
    """Represents the result of a paragraph replacement operation."""

    text: str
    cursor_position: int


@dataclass(frozen=True)
class ParagraphInsertLintResult:
    """Represents a read-only paragraph insertion check."""

    allowed: bool
    message_key: str = ""
    values: dict[str, str] | None = None


@dataclass(frozen=True)
class _BuiltBlock:
    text: str
    cursor_offset: int


@dataclass(frozen=True)
class _PreparedInsertion:
    block: ParagraphBlock
    selection_start: int
    selection_end: int
    rule: ParagraphInsertRule


def find_current_paragraph_block(
    text: str,
    cursor_pos: int,
    dictionaries_path: Path | None = None,
) -> ParagraphBlock | None:
    """Return the simple paragraph block containing cursor_pos, if available."""
    rule_book = _load_rule_book(dictionaries_path)
    block, _message_key = _find_paragraph_block(text, cursor_pos, rule_book)
    return block


def lint_paragraph_insertion(
    text: str,
    selection_start: int,
    selection_end: int,
    operation_key: str,
    dictionaries_path: Path | None = None,
) -> ParagraphInsertLintResult:
    """Check one paragraph insertion without modifying the source text."""
    try:
        rule_book = _load_rule_book(dictionaries_path)
        _prepare_insertion(
            text,
            selection_start,
            selection_end,
            operation_key,
            rule_book,
        )
    except ParagraphSplitError as error:
        return ParagraphInsertLintResult(False, error.message_key, error.values)
    return ParagraphInsertLintResult(True)


def build_paragraph_block(
    content: str,
    dictionaries_path: Path | None = None,
) -> str:
    """Build a paragraph block from the dictionary template."""
    return _build_paragraph_block(content, _load_rule_book(dictionaries_path))


def build_spacer_block(
    height: int = 32,
    dictionaries_path: Path | None = None,
) -> str:
    """Build a spacer block from the insert_spacer dictionary entry."""
    rule_book = _load_rule_book(dictionaries_path)
    rule = _operation(rule_book, INSERT_SPACER_KEY)
    return _render_operation(rule, "", {"height": str(height)}).text


def build_html_code_block(
    content: str = "",
    dictionaries_path: Path | None = None,
) -> str:
    """Build an HTML code block from the insert_html dictionary entry."""
    rule_book = _load_rule_book(dictionaries_path)
    rule = _operation(rule_book, INSERT_HTML_KEY)
    transformed = _transform_content(content, rule, rule_book)
    return _render_operation(rule, transformed).text


def build_decorated_block(
    content: str = "",
    dictionaries_path: Path | None = None,
) -> str:
    """Build a decorated block from the decorated_block dictionary entry."""
    rule_book = _load_rule_book(dictionaries_path)
    rule = _operation(rule_book, DECORATED_BLOCK_KEY)
    transformed = _transform_content(content, rule, rule_book)
    return _render_operation(rule, transformed).text


def split_paragraph_insert_spacer(
    text: str,
    cursor_pos: int,
    dictionaries_path: Path | None = None,
) -> ParagraphReplacement:
    return _apply_paragraph_insert_operation(
        text,
        cursor_pos,
        cursor_pos,
        INSERT_SPACER_KEY,
        dictionaries_path,
    )


def split_paragraph_insert_html(
    text: str,
    cursor_pos: int,
    dictionaries_path: Path | None = None,
) -> ParagraphReplacement:
    return _apply_paragraph_insert_operation(
        text,
        cursor_pos,
        cursor_pos,
        INSERT_HTML_KEY,
        dictionaries_path,
    )


def wrap_selection_as_code_block(
    text: str,
    selection_start: int,
    selection_end: int,
    dictionaries_path: Path | None = None,
) -> ParagraphReplacement:
    return _apply_paragraph_insert_operation(
        text,
        selection_start,
        selection_end,
        INSERT_HTML_KEY,
        dictionaries_path,
    )


def wrap_selection_as_decorated_block(
    text: str,
    selection_start: int,
    selection_end: int,
    dictionaries_path: Path | None = None,
) -> ParagraphReplacement:
    return _apply_paragraph_insert_operation(
        text,
        selection_start,
        selection_end,
        DECORATED_BLOCK_KEY,
        dictionaries_path,
    )


def _apply_paragraph_insert_operation(
    text: str,
    selection_start: int,
    selection_end: int,
    operation_key: str,
    dictionaries_path: Path | None,
) -> ParagraphReplacement:
    rule_book = _load_rule_book(dictionaries_path)
    prepared = _prepare_insertion(
        text,
        selection_start,
        selection_end,
        operation_key,
        rule_book,
    )
    selected_text = text[prepared.selection_start : prepared.selection_end]
    transformed = _transform_content(selected_text, prepared.rule, rule_book)
    inserted_block = _render_operation(prepared.rule, transformed)
    return _replace_current_paragraph_selection(
        text,
        prepared,
        inserted_block,
        rule_book,
    )


def _prepare_insertion(
    text: str,
    selection_start: int,
    selection_end: int,
    operation_key: str,
    rule_book: ParagraphInsertRuleBook,
) -> _PreparedInsertion:
    start = min(selection_start, selection_end)
    end = max(selection_start, selection_end)
    selection_was_empty = start == end
    block = _paragraph_block_for_range(text, start, end, rule_book)
    rule = _operation(rule_book, operation_key)

    if start != end and not rule.allow_nonempty_selection:
        raise ParagraphSplitError(rule.error_key)
    if selection_was_empty and rule.empty_requires_blank_line:
        start, end = _line_range_at_cursor(text, block, start)
    elif start != end and rule.expand_selection_to_lines:
        start, end = _expand_selection_to_content_lines(text, start, end, block)

    candidate = text[start:end]
    search_pattern = rule.empty_search if selection_was_empty else rule.search
    exclude_pattern = rule.empty_exclude if selection_was_empty else rule.exclude
    if not _search_rule_matches_entire_candidate(
        candidate,
        search_pattern,
        exclude_pattern,
        rule.key,
    ):
        raise ParagraphSplitError(rule.error_key)
    return _PreparedInsertion(block, start, end, rule)


def _find_paragraph_block(
    text: str,
    cursor_pos: int,
    rule_book: ParagraphInsertRuleBook,
) -> tuple[ParagraphBlock | None, str]:
    grammar = rule_book.grammar
    for block_match in re.finditer(
        grammar.paragraph_block_search,
        text,
        re.IGNORECASE | re.MULTILINE,
    ):
        if not block_match.start() <= cursor_pos <= block_match.end():
            continue
        body_start, body_end = block_match.span("body")
        body_text = text[body_start:body_end]
        paragraph_matches = list(re.finditer(
            grammar.paragraph_tag_search,
            body_text,
            re.IGNORECASE | re.MULTILINE,
        ))
        if len(paragraph_matches) != 1:
            return None, grammar.paragraph_structure_key
        paragraph_match = paragraph_matches[0]
        if (
            body_text[: paragraph_match.start()].strip()
            or body_text[paragraph_match.end() :].strip()
        ):
            return None, grammar.paragraph_structure_key
        content_start, content_end = paragraph_match.span("content")
        return ParagraphBlock(
            block_start=block_match.start(),
            block_end=block_match.end(),
            content_start=body_start + content_start,
            content_end=body_start + content_end,
            attributes=paragraph_match.group("attributes"),
        ), ""
    return None, grammar.not_available_key


def _paragraph_block_for_range(
    text: str,
    start: int,
    end: int,
    rule_book: ParagraphInsertRuleBook,
) -> ParagraphBlock:
    block, message_key = _find_paragraph_block(text, start, rule_book)
    if block is None:
        raise ParagraphSplitError(message_key)

    check_pos = max(start, end - 1)
    end_block, end_message_key = _find_paragraph_block(text, check_pos, rule_book)
    if end_block is None:
        raise ParagraphSplitError(end_message_key)
    if end_block != block:
        raise ParagraphSplitError(rule_book.grammar.cross_block_key)
    if start < block.content_start or end > block.content_end:
        raise ParagraphSplitError(rule_book.grammar.not_available_key)
    if block.attributes.strip():
        raise ParagraphSplitError(rule_book.grammar.paragraph_attributes_key)
    return block


def _line_range_at_cursor(
    text: str,
    block: ParagraphBlock,
    cursor_pos: int,
) -> tuple[int, int]:
    content = text[block.content_start : block.content_end]
    relative_pos = min(max(cursor_pos - block.content_start, 0), len(content))
    line_start = content.rfind("\n", 0, relative_pos) + 1
    line_end = content.find("\n", relative_pos)
    if line_end == -1:
        line_end = len(content)
    return block.content_start + line_start, block.content_start + line_end


def _expand_selection_to_content_lines(
    text: str,
    selection_start: int,
    selection_end: int,
    block: ParagraphBlock,
) -> tuple[int, int]:
    content = text[block.content_start : block.content_end]
    relative_start = selection_start - block.content_start
    relative_end = selection_end - block.content_start
    line_start = content.rfind("\n", 0, relative_start) + 1
    line_end_lookup = max(relative_start, relative_end - 1)
    line_end = content.find("\n", line_end_lookup)
    if line_end == -1:
        line_end = len(content)
    return block.content_start + line_start, block.content_start + line_end


def _replace_current_paragraph_selection(
    text: str,
    prepared: _PreparedInsertion,
    inserted_block: _BuiltBlock,
    rule_book: ParagraphInsertRuleBook,
) -> ParagraphReplacement:
    block = prepared.block
    before_content = text[block.content_start : prepared.selection_start]
    after_content = text[prepared.selection_end : block.content_end]
    before_block = _build_paragraph_block(before_content, rule_book)
    after_block = _build_paragraph_block(after_content, rule_book)
    replacement_text, cursor_offset = _join_split_blocks(
        before_block,
        inserted_block,
        after_block,
        rule_book.grammar.block_separator,
    )
    new_text = text[: block.block_start] + replacement_text + text[block.block_end :]
    return ParagraphReplacement(
        text=new_text,
        cursor_position=block.block_start + cursor_offset,
    )


def _join_split_blocks(
    before_block: str,
    inserted_block: _BuiltBlock,
    after_block: str,
    separator: str,
) -> tuple[str, int]:
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
            replacement_text += separator
        if piece_cursor_offset is not None:
            cursor_offset = len(replacement_text) + piece_cursor_offset
        replacement_text += piece
    return replacement_text, cursor_offset


def _build_paragraph_block(
    content: str,
    rule_book: ParagraphInsertRuleBook,
) -> str:
    clean_content = _clean_paragraph_edge_breaks(content, rule_book)
    if not clean_content:
        return ""
    return rule_book.grammar.paragraph_replacement.replace(
        SELECTION_PLACEHOLDER,
        clean_content,
    )


def _clean_paragraph_edge_breaks(
    content: str,
    rule_book: ParagraphInsertRuleBook,
) -> str:
    clean_content = content.strip()
    previous = None
    while clean_content != previous:
        previous = clean_content
        clean_content = _apply_text_rule(
            clean_content,
            rule_book.grammar.trim_leading_breaks,
        ).strip()
        clean_content = _apply_text_rule(
            clean_content,
            rule_book.grammar.trim_trailing_breaks,
        ).strip()
    return clean_content


def _transform_content(
    content: str,
    rule: ParagraphInsertRule,
    rule_book: ParagraphInsertRuleBook,
) -> str:
    if rule.content_transform == "none":
        return content
    clean_content = _clean_paragraph_edge_breaks(content, rule_book)
    code_text = _apply_text_rule(
        clean_content,
        rule_book.grammar.break_to_newline,
    ).strip()
    if rule.content_transform == "code":
        return escape(code_text, quote=False)
    if rule.content_transform == "decorated":
        lines = [line.strip() for line in code_text.splitlines()]
        compact_text = "\n".join(line for line in lines if line)
        return _apply_text_rule(
            compact_text,
            rule_book.grammar.newline_to_break,
        )
    raise ParagraphSplitError(
        INVALID_RULE_KEY,
        {"operation": rule.key, "error": rule.content_transform},
    )


def _apply_text_rule(source_text: str, rule: TextReplacementRule) -> str:
    try:
        result = SearchEngine().replace_all(
            source_text,
            rule.search,
            rule.replacement,
            SearchOptions(
                case_sensitive=False,
                regular_expression=True,
                exclusion_text=rule.exclude,
            ),
        )
    except re.error as error:
        raise ParagraphSplitError(
            INVALID_RULE_KEY,
            {"operation": "text_replacement", "error": str(error)},
        ) from error
    return result.text


def _search_rule_matches_entire_candidate(
    candidate: str,
    search_pattern: str,
    exclude_pattern: str,
    operation_key: str,
) -> bool:
    match_marker = "\uffffPARAGRAPH_INSERT_MATCH\uffff"
    try:
        result = SearchEngine().replace_all(
            candidate,
            search_pattern,
            match_marker,
            SearchOptions(
                case_sensitive=False,
                regular_expression=True,
                exclusion_text=exclude_pattern,
            ),
        )
    except re.error as error:
        raise ParagraphSplitError(
            INVALID_RULE_KEY,
            {"operation": operation_key, "error": str(error)},
        ) from error
    return result.count == 1 and result.text == match_marker


def _render_operation(
    rule: ParagraphInsertRule,
    selected_text: str,
    parameter_overrides: dict[str, str] | None = None,
) -> _BuiltBlock:
    parameters = dict(rule.default_parameters)
    if parameter_overrides:
        parameters.update(parameter_overrides)
    rendered_text = rule.replacement
    for key, value in parameters.items():
        rendered_text = rendered_text.replace(f"{{{key}}}", value)
    replacement_text = selected_text if selected_text else rule.empty_selection
    rendered_text = rendered_text.replace(SELECTION_PLACEHOLDER, replacement_text)
    cursor_offset = rendered_text.find(CURSOR_PLACEHOLDER)
    if cursor_offset == -1:
        raise ParagraphSplitError(
            INVALID_RULE_KEY,
            {"operation": rule.key, "error": "cursor placeholder"},
        )
    return _BuiltBlock(
        rendered_text.replace(CURSOR_PLACEHOLDER, ""),
        cursor_offset,
    )


def _load_rule_book(
    dictionaries_path: Path | None,
) -> ParagraphInsertRuleBook:
    try:
        return load_paragraph_insert_rule_book(dictionaries_path)
    except ParagraphInsertDictionaryError as error:
        raise ParagraphSplitError(
            DICTIONARY_ERROR_KEY,
            {"error": str(error)},
        ) from error


def _operation(
    rule_book: ParagraphInsertRuleBook,
    operation_key: str,
) -> ParagraphInsertRule:
    try:
        return rule_book.operation(operation_key)
    except ParagraphInsertDictionaryError as error:
        raise ParagraphSplitError(
            DICTIONARY_ERROR_KEY,
            {"error": str(error)},
        ) from error
