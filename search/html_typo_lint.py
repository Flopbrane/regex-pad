from __future__ import annotations

import json
import re
import unicodedata
from bisect import bisect_left
from dataclasses import dataclass
from difflib import get_close_matches
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from json_lint import lint_json_fragment
from search.css_lint import (
    CssLintIssue,
    lint_inline_style,
    lint_stylesheet,
    parse_inline_style_values,
)

LINT_REFERENCE_PATH = Path(__file__).resolve().parent.parent / "dictionaries" / "lint_reference.json"
BLOCK_COMMENT_PATTERN = re.compile(
    r"<!--\s*(/)?\s*wp:([a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)?)"
    r"(?:\s+((?:(?!-->)[\s\S])*?))?\s*(/)?\s*-->",
)
HTML_TAG_TOKEN_PATTERN = re.compile(
    r"<\s*(/)?\s*([A-Za-z][A-Za-z0-9:-]*)(?:\s[^<>]*)?(/)?\s*>",
    re.IGNORECASE,
)
HTML_ATTRIBUTE_ASSIGNMENT_PATTERN = re.compile(
    r'''([A-Za-z_:][A-Za-z0-9_:.-]*)\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+)''',
)
ATTRIBUTE_EXAMPLE_TAGS = {"code", "pre", "textarea", "script", "style", "title", "xmp"}
FULL_WIDTH_HTML_SYNTAX_SUGGESTIONS = {
    "＜": "<",
    "＞": ">",
    "＝": "=",
    "＂": '"',
    "＇": "'",
    "／": "/",
}

DEFAULT_WORDPRESS_CORE_BLOCKS = {
    "accordion",
    "accordion-heading",
    "accordion-item",
    "accordion-panel",
    "audio",
    "button",
    "buttons",
    "code",
    "column",
    "columns",
    "cover",
    "details",
    "embed",
    "file",
    "gallery",
    "group",
    "heading",
    "html",
    "image",
    "list",
    "list-item",
    "media-text",
    "more",
    "nextpage",
    "paragraph",
    "preformatted",
    "quote",
    "separator",
    "shortcode",
    "spacer",
    "table",
    "verse",
    "video",
}
DEFAULT_HTML_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "ul",
}
DEFAULT_HTML_ATTRIBUTES = {
    "alt",
    "aria-hidden",
    "aria-label",
    "class",
    "controls",
    "datetime",
    "decoding",
    "fetchpriority",
    "height",
    "href",
    "id",
    "loop",
    "muted",
    "open",
    "placeholder",
    "playsinline",
    "poster",
    "preload",
    "rel",
    "role",
    "sizes",
    "src",
    "srcset",
    "style",
    "target",
    "title",
    "type",
    "width",
}
DEFAULT_ALLOWED_ATTRIBUTE_PREFIXES = ("aria-", "data-")
DEFAULT_GLOBAL_HTML_ATTRIBUTES = {
    "aria-hidden",
    "aria-label",
    "class",
    "data",
    "id",
    "lang",
    "role",
    "style",
    "tabindex",
    "title",
}
DEFAULT_HTML_ATTRIBUTES_BY_TAG = {
    "a": {"download", "href", "hreflang", "referrerpolicy", "rel", "target", "type"},
    "audio": {
        "autoplay",
        "controls",
        "loop",
        "muted",
        "preload",
        "src",
    },
    "blockquote": {"cite"},
    "button": {"disabled", "name", "type", "value"},
    "col": {"span"},
    "colgroup": {"span"},
    "code": set(),
    "div": set(),
    "em": set(),
    "figcaption": set(),
    "figure": set(),
    "h1": set(),
    "h2": set(),
    "h3": set(),
    "h4": set(),
    "h5": set(),
    "h6": set(),
    "iframe": {
        "allow",
        "allowfullscreen",
        "height",
        "loading",
        "name",
        "referrerpolicy",
        "src",
        "srcdoc",
        "width",
    },
    "img": {
        "alt",
        "crossorigin",
        "decoding",
        "fetchpriority",
        "height",
        "loading",
        "referrerpolicy",
        "sizes",
        "src",
        "srcset",
        "usemap",
        "width",
    },
    "li": {"value"},
    "ol": {"reversed", "start", "type"},
    "p": set(),
    "q": {"cite"},
    "span": set(),
    "source": {"height", "media", "sizes", "src", "srcset", "type", "width"},
    "strong": set(),
    "td": {"colspan", "headers", "rowspan"},
    "th": {"abbr", "colspan", "headers", "rowspan", "scope"},
    "time": {"datetime"},
    "track": {"default", "kind", "label", "src", "srclang"},
    "video": {
        "autoplay",
        "controls",
        "height",
        "loop",
        "muted",
        "playsinline",
        "poster",
        "preload",
        "src",
        "width",
    },
}
COMMON_HTML_ATTRIBUTE_TYPOS = {
    "calss": "class",
    "clas": "class",
    "decodng": "decoding",
    "fetchprority": "fetchpriority",
    "herf": "href",
    "hrfe": "href",
    "scr": "src",
    "scrset": "srcset",
    "sies": "sizes",
    "sryle": "style",
    "stlye": "style",
    "styel": "style",
    "taget": "target",
    "taret": "target",
    "titel": "title",
}
RESTRICTED_HTML_TAG_REASONS = {
    "script": "arbitrary JavaScript",
    "style": "embedded CSS",
    "iframe": "external embed",
    "object": "external object/embed",
    "embed": "external object/embed",
    "form": "form submission",
    "input": "form control",
    "textarea": "form control",
    "select": "form control",
    "button": "form or script control",
    "canvas": "JavaScript drawing surface",
}
RESTRICTED_HTML_ATTRIBUTE_PREFIXES = ("on",)
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
INLINE_TAGS = {
    "a",
    "b",
    "code",
    "em",
    "i",
    "mark",
    "small",
    "span",
    "strong",
    "u",
}
INLINE_PARENT_BOUNDARY_TAGS = {
    "blockquote",
    "dd",
    "div",
    "dt",
    "figcaption",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "p",
    "pre",
    "td",
    "th",
}
ESCAPED_FRAGMENT_IGNORED_WORDPRESS_BLOCKS = {"code", "html"}
NON_NESTABLE_WORDPRESS_BLOCKS = {
    "code",
    "heading",
    "list-item",
    "paragraph",
    "separator",
    "spacer",
}
STRUCTURAL_HTML_TAGS = {
    "blockquote",
    "article",
    "aside",
    "code",
    "div",
    "footer",
    "figcaption",
    "figure",
    "header",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}
PARAGRAPH_BREAKING_TAGS = (
    STRUCTURAL_HTML_TAGS - {"code"}
) | {"address", "details", "dialog", "dl", "fieldset", "form", "hr", "menu"}
WORDPRESS_REQUIRED_PARENTS = {"list-item": "list", "column": "columns"}
WORDPRESS_ALLOWED_CHILDREN = {"list": {"list-item"}, "columns": {"column"}}
WORDPRESS_NON_CONTAINER_BLOCKS = {"paragraph", "heading", "separator", "spacer", "image"}
WORDPRESS_HTML_SHAPES = {
    "paragraph": {"p"},
    "heading": {f"h{level}" for level in range(1, 7)},
    "list": {"ul", "ol"},
    "list-item": {"li"},
}
COMMON_WORDPRESS_BLOCK_ATTRIBUTES = {
    "align",
    "anchor",
    "backgroundColor",
    "className",
    "fontSize",
    "gradient",
    "lock",
    "metadata",
    "style",
    "textColor",
}
WORDPRESS_BLOCK_ATTRIBUTE_ALLOWLISTS = {
    "button": COMMON_WORDPRESS_BLOCK_ATTRIBUTES
    | {
        "linkTarget",
        "placeholder",
        "rel",
        "tagName",
        "text",
        "textAlign",
        "title",
        "url",
        "width",
    },
    "heading": COMMON_WORDPRESS_BLOCK_ATTRIBUTES | {"content", "level", "placeholder"},
    "image": COMMON_WORDPRESS_BLOCK_ATTRIBUTES
    | {
        "alt",
        "aspectRatio",
        "caption",
        "height",
        "href",
        "id",
        "linkClass",
        "linkDestination",
        "linkTarget",
        "rel",
        "scale",
        "sizeSlug",
        "title",
        "url",
        "width",
    },
    "list": COMMON_WORDPRESS_BLOCK_ATTRIBUTES | {"ordered", "reversed", "start", "type"},
    "paragraph": COMMON_WORDPRESS_BLOCK_ATTRIBUTES
    | {"content", "direction", "dropCap", "placeholder"},
    "separator": COMMON_WORDPRESS_BLOCK_ATTRIBUTES | {"opacity"},
    "spacer": COMMON_WORDPRESS_BLOCK_ATTRIBUTES | {"height", "width"},
}
WORDPRESS_BLOCK_ATTRIBUTE_TYPE_RULES = {
    ("heading", "level"): "integer",
    ("paragraph", "dropCap"): "boolean",
}
WORDPRESS_BLOCK_ATTRIBUTE_VALUE_RULES = {
    ("paragraph", "align"): {"left", "center", "right"},
}
DECORATED_BLOCKS_BETTER_AS_HTML = {"group", "preformatted"}


@dataclass(frozen=True)
class HtmlTypoLintMessage:
    severity: str
    message_key: str
    line_number: int
    values: dict[str, str] | None = None

    @property
    def message(self) -> str:
        if not self.values:
            return self.message_key
        values = ", ".join(self.values.values())
        return f"{self.message_key}: {values}"


@dataclass(frozen=True)
class LintReferenceCache:
    wordpress_core_blocks: set[str]
    wordpress_block_attributes: dict[str, set[str]]
    html_tags: set[str]
    html_attributes: set[str]
    html_attributes_by_tag: dict[str, set[str]]
    global_html_attributes: set[str]
    allowed_attribute_prefixes: tuple[str, ...]


@dataclass(frozen=True)
class _LintToken:
    position: int
    line_number: int
    name: str
    token_type: str


@dataclass
class _WordPressBlockStackItem:
    name: str
    body_start: int
    open_line: int
    attributes: dict[str, Any]
    attributes_valid: bool
    pair_id: int
    parent_pair_id: int | None
    depth: int
    open_position: int
    body_end: int | None = None
    close_line: int | None = None
    close_end: int | None = None
    self_closing: bool = False
    boundary_valid: bool = True
    has_children: bool = False
    affected_start: int | None = None


_ParsedWordPressBlockAttributes = tuple[dict[str, Any], bool, int | None]


def lint_html_typos(load_data: str) -> list[HtmlTypoLintMessage]:
    suppressed_ranges = _contaminated_wordpress_separator_body_ranges(load_data)
    html_lint_data = _mask_ranges(
        load_data,
        suppressed_ranges,
    )
    # Collect live HTML once. WP block checks slice this inventory by source position.
    html_tokens = _html_tag_tokens(html_lint_data)
    wordpress_tokens = _wordpress_block_tokens(load_data)
    # Keep enclosing WP diagnostics first on the same line (for example a broken
    # separator); the final result remains ordered by source line.
    messages = _lint_token_inventories(html_lint_data, html_tokens, wordpress_tokens)
    messages.extend(_lint_wordpress_block_typos(load_data))
    messages.extend(_lint_wordpress_block_structure(load_data, html_tokens))
    messages.extend(_lint_known_fragile_typos(load_data))
    messages.extend(_lint_full_width_html_syntax(load_data))
    messages.extend(_lint_embedded_stylesheets(load_data))
    parser = HtmlTypoLintParser(load_data, suppressed_ranges)
    parser.feed(load_data)
    parser.close()
    messages.extend(parser.messages)
    # A child block and its container can expose the same broken HTML tag.
    unique_messages: dict[tuple[Any, ...], HtmlTypoLintMessage] = {}
    for message in messages:
        signature = (
            message.severity, message.message_key, message.line_number,
            tuple(sorted((message.values or {}).items())),
        )
        unique_messages.setdefault(signature, message)
    boundary_keys = {
        "html_typo_lint.missing_wordpress_closing_block",
        "html_typo_lint.missing_wordpress_html_closing_block",
        "html_typo_lint.mismatched_wordpress_block",
        "html_typo_lint.unexpected_wordpress_closing_block",
    }
    crossing_tags = {
        (message.line_number, (message.values or {}).get("tag"))
        for message in messages
        if message.message_key == "html_typo_lint.html_crosses_wordpress_boundary"
    }
    return sorted(
        (message for message in unique_messages.values()
         if not (message.message_key == "html_typo_lint.missing_html_closing_tag"
                 and (message.line_number, (message.values or {}).get("tag")) in crossing_tags)),
        key=lambda message: (message.line_number, message.message_key not in boundary_keys,
                             message.severity != "error"),
    )


def _lint_token_inventories(
    load_data: str,
    html_tokens: list[_LintToken],
    wordpress_tokens: list[_LintToken],
) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    messages.extend(
        _lint_wordpress_block_comment_count(
            wordpress_tokens,
            "paragraph",
            "html_typo_lint.count_mismatch_wordpress_paragraph",
        )
    )
    messages.extend(
        _lint_wordpress_block_comment_count(
            wordpress_tokens,
            "html",
            "html_typo_lint.count_mismatch_wordpress_html",
        )
    )
    messages.extend(
        _lint_html_tag_count(
            html_tokens,
            "p",
            "html_typo_lint.count_mismatch_p",
        )
    )
    messages.extend(
        _lint_html_tag_count(
            html_tokens,
            "pre",
            "html_typo_lint.count_mismatch_pre",
        )
    )
    messages.extend(
        _lint_html_tag_count(
            html_tokens,
            "code",
            "html_typo_lint.count_mismatch_code",
        )
    )
    messages.extend(_lint_non_nestable_html_tag(html_tokens, "code"))
    messages.extend(_lint_html_content_model(html_tokens))
    messages.extend(_lint_html_tag_structure(html_tokens, STRUCTURAL_HTML_TAGS))
    messages.extend(_lint_orphan_html_lines_outside_wordpress_blocks(load_data))
    return messages


def _lint_wordpress_block_comment_count(
    tokens: list[_LintToken],
    name: str,
    message_key: str,
) -> list[HtmlTypoLintMessage]:
    return _lint_token_count(
        name,
        [token for token in tokens if token.name == name],
        message_key,
    )


def _lint_html_tag_count(
    tokens: list[_LintToken],
    name: str,
    message_key: str,
) -> list[HtmlTypoLintMessage]:
    return _lint_token_count(
        name,
        [token for token in tokens if token.name == name],
        message_key,
    )


def _lint_token_count(
    name: str,
    tokens: list[_LintToken],
    message_key: str,
) -> list[HtmlTypoLintMessage]:
    tokens = [token for token in tokens if token.token_type != "self_close"]
    open_count = sum(1 for token in tokens if token.token_type == "open")
    close_count = sum(1 for token in tokens if token.token_type == "close")
    if open_count == close_count:
        return []

    first_problem_token = _first_count_problem_token(tokens, open_count, close_count)
    return [
        HtmlTypoLintMessage(
            "warning",
            message_key,
            first_problem_token.line_number if first_problem_token else 1,
            {
                "name": name,
                "open_count": str(open_count),
                "close_count": str(close_count),
            },
        )
    ]


def _first_count_problem_token(
    tokens: list[_LintToken],
    open_count: int,
    close_count: int,
) -> _LintToken | None:
    balance = 0
    last_open_token: _LintToken | None = None
    last_close_token: _LintToken | None = None
    for token in sorted(tokens, key=lambda item: item.position):
        if token.token_type == "open":
            if open_count > close_count and balance > 0:
                return token
            balance += 1
            last_open_token = token
        else:
            balance -= 1
            last_close_token = token
        if balance < 0:
            return token
    if open_count > close_count:
        return last_open_token
    return last_close_token


def _lint_non_nestable_html_tag(
    tokens: list[_LintToken],
    name: str,
) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    open_tokens: list[_LintToken] = []
    for token in sorted(tokens, key=lambda item: item.position):
        if token.name != name:
            continue
        if token.token_type == "close":
            if open_tokens:
                open_tokens.pop()
            continue
        if token.token_type != "open":
            continue
        if open_tokens:
            messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.nested_html_tag",
                    token.line_number,
                    {"tag": name},
                )
            )
        open_tokens.append(token)
    return messages


def _lint_html_tag_structure(
    tokens: list[_LintToken],
    tag_names: set[str],
) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    open_tokens: list[_LintToken] = []
    for token in sorted(tokens, key=lambda item: item.position):
        if token.name not in tag_names or token.token_type == "self_close":
            continue
        if token.token_type == "open":
            open_tokens.append(token)
            continue

        matching_index = _last_open_html_tag_index(open_tokens, token.name)
        if matching_index is None:
            messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.unexpected_html_closing_tag",
                    token.line_number,
                    {"tag": token.name},
                )
            )
            continue
        if matching_index != len(open_tokens) - 1:
            expected_token = open_tokens[-1]
            messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.mismatched_html_tag",
                    token.line_number,
                    {
                        "open_tag": expected_token.name,
                        "close_tag": token.name,
                    },
                )
            )
        del open_tokens[matching_index]

    for token in open_tokens:
        messages.append(
            HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.missing_html_closing_tag",
                token.line_number,
                {"tag": token.name},
            )
        )
    return messages


def _lint_html_content_model(tokens: list[_LintToken]) -> list[HtmlTypoLintMessage]:
    """Check a small, explicit content model on live HTML, across WP wrappers."""
    messages: list[HtmlTypoLintMessage] = []
    open_tokens: list[_LintToken] = []
    for token in tokens:
        if token.token_type == "close":
            matching_index = _last_open_html_tag_index(open_tokens, token.name)
            if matching_index is not None:
                del open_tokens[matching_index:]
            continue
        open_names = {item.name for item in open_tokens}
        if token.name in {"p", "a"} and token.name in open_names:
            messages.append(HtmlTypoLintMessage(
                "warning", "html_typo_lint.nested_html_tag", token.line_number,
                {"tag": token.name},
            ))
        elif "p" in open_names and token.name in PARAGRAPH_BREAKING_TAGS:
            messages.append(HtmlTypoLintMessage(
                "warning", "html_typo_lint.invalid_html_child", token.line_number,
                {"parent": "p", "tag": token.name},
            ))
        if token.name == "li" and (
            not open_tokens or open_tokens[-1].name not in {"ul", "ol", "menu"}
        ):
            messages.append(HtmlTypoLintMessage(
                "warning", "html_typo_lint.invalid_html_parent", token.line_number,
                {"tag": "li", "parent": "ul / ol / menu"},
            ))
        if token.token_type == "open" and token.name not in VOID_TAGS:
            open_tokens.append(token)
    return messages


def _last_open_html_tag_index(
    open_tokens: list[_LintToken],
    tag_name: str,
) -> int | None:
    for index in range(len(open_tokens) - 1, -1, -1):
        if open_tokens[index].name == tag_name:
            return index
    return None


def _lint_orphan_html_lines_outside_wordpress_blocks(
    load_data: str,
) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    block_depth = 0
    for line_number, line in enumerate(load_data.splitlines(), start=1):
        stripped_line = line.strip()
        if block_depth == 0:
            if re.fullmatch(r"<p\s*>\s*</p\s*>", stripped_line, re.IGNORECASE):
                messages.append(
                    HtmlTypoLintMessage(
                        "warning",
                        "html_typo_lint.empty_paragraph_outside_wordpress_block",
                        line_number,
                    )
                )
            if re.fullmatch(r"<br\s*/?\s*>", stripped_line, re.IGNORECASE):
                messages.append(
                    HtmlTypoLintMessage(
                        "warning",
                        "html_typo_lint.break_outside_wordpress_block",
                        line_number,
                    )
                )
        for block_match in BLOCK_COMMENT_PATTERN.finditer(line):
            if block_match.group(1):
                block_depth = max(0, block_depth - 1)
            elif not block_match.group(4):
                block_depth += 1
    return messages


def _lint_known_fragile_typos(load_data: str) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    line_starts = _line_start_positions(load_data)
    ignored_ranges = _wordpress_block_body_ranges(
        load_data,
        ESCAPED_FRAGMENT_IGNORED_WORDPRESS_BLOCKS,
    )
    ordinary_checks = (
        (r"<\\p\s*>", "html_typo_lint.invalid_p_closing_tag"),
    )
    for pattern, message_key in ordinary_checks:
        for match in re.finditer(pattern, load_data, re.IGNORECASE):
            messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    message_key,
                    _line_number_at(match.start(), line_starts),
                )
            )
    for match in re.finditer(r"/code&gt;", load_data, re.IGNORECASE):
        if _position_in_ranges(match.start(), ignored_ranges):
            continue
        messages.append(
            HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.escaped_code_close_fragment",
                _line_number_at(match.start(), line_starts),
            )
        )
    return messages


def _lint_full_width_html_syntax(load_data: str) -> list[HtmlTypoLintMessage]:
    """Report full-width punctuation used as live HTML tag syntax."""
    messages: list[HtmlTypoLintMessage] = []
    line_starts = _line_start_positions(load_data)
    ignored_ranges = _html_example_body_ranges(load_data)
    ignored_ranges.extend(
        (match.start(), match.end())
        for match in re.finditer(r"<!--[\s\S]*?-->", load_data)
    )

    for start, end in _html_tag_like_ranges(load_data):
        if _position_in_ranges(start, ignored_ranges):
            continue
        quote: str | None = None
        reported_symbols: set[str] = set()
        reported_space = False
        for position in range(start, end):
            character = load_data[position]
            if quote is not None:
                if character == quote:
                    quote = None
                continue
            if character in {'"', "'"}:
                quote = character
                continue
            if character == "　":
                if not reported_space:
                    messages.append(HtmlTypoLintMessage(
                        "warning",
                        "html_typo_lint.full_width_html_space",
                        _line_number_at(position, line_starts),
                    ))
                    reported_space = True
                continue
            suggestion = FULL_WIDTH_HTML_SYNTAX_SUGGESTIONS.get(character)
            if suggestion is None or character in reported_symbols:
                continue
            messages.append(HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.full_width_html_syntax",
                _line_number_at(position, line_starts),
                {"symbol": character, "suggestion": suggestion},
            ))
            reported_symbols.add(character)
    return messages


def _html_example_body_ranges(load_data: str) -> list[tuple[int, int]]:
    tag_names = "|".join(sorted(ATTRIBUTE_EXAMPLE_TAGS))
    pattern = re.compile(
        rf"<({tag_names})\b[^>]*>([\s\S]*?)</\1\s*>",
        re.IGNORECASE,
    )
    return [
        (match.start(2), match.end(2))
        for match in pattern.finditer(load_data)
    ]


def _html_tag_like_ranges(load_data: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    position = 0
    while position < len(load_data):
        if load_data[position] not in {"<", "＜"} or not _looks_like_html_tag_start(
            load_data,
            position,
        ):
            position += 1
            continue

        start = position
        quote: str | None = None
        position += 1
        scan_limit = min(len(load_data), start + 4096)
        while position < scan_limit:
            character = load_data[position]
            if quote is not None:
                if character == quote:
                    quote = None
                position += 1
                continue
            if character in {'"', "'"}:
                quote = character
                position += 1
                continue
            if character in {">", "＞"}:
                position += 1
                break
            if character in {"<", "＜"}:
                break
            position += 1
        ranges.append((start, position))
        if position == start:
            position += 1
    return ranges


def _looks_like_html_tag_start(load_data: str, position: int) -> bool:
    candidate_position = position + 1
    while candidate_position < len(load_data) and load_data[candidate_position].isspace():
        candidate_position += 1
    if candidate_position < len(load_data) and load_data[candidate_position] in {"/", "／"}:
        candidate_position += 1
        while candidate_position < len(load_data) and load_data[candidate_position].isspace():
            candidate_position += 1
    if candidate_position >= len(load_data):
        return False
    normalized_character = unicodedata.normalize("NFKC", load_data[candidate_position])
    return len(normalized_character) == 1 and normalized_character.isascii() and normalized_character.isalpha()


def _wordpress_block_body_ranges(
    load_data: str,
    block_names: set[str],
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    block_stack: list[tuple[str, int]] = []
    for block_match in BLOCK_COMMENT_PATTERN.finditer(load_data):
        is_closing = bool(block_match.group(1))
        block_name = _normalize_block_name(block_match.group(2))
        if not is_closing:
            if block_match.group(4):
                continue
            block_stack.append((block_name, block_match.end()))
            continue
        if not block_stack:
            continue
        matching_index = next((
            index for index in range(len(block_stack) - 1, -1, -1)
            if block_stack[index][0] == block_name
        ), None)
        if matching_index is None:
            continue
        _, open_end = block_stack[matching_index]
        del block_stack[matching_index:]
        if block_name in block_names:
            ranges.append((open_end, block_match.start()))
    return ranges


def _contaminated_wordpress_separator_body_ranges(load_data: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for start, end in _wordpress_block_body_ranges(load_data, {"separator"}):
        block_body = load_data[start:end]
        if re.search(r"</?code(?:\s|>)", block_body, re.IGNORECASE):
            ranges.append((start, end))
    return ranges


def _mask_ranges(load_data: str, ranges: list[tuple[int, int]]) -> str:
    if not ranges:
        return load_data

    characters = list(load_data)
    for start, end in ranges:
        for index in range(start, end):
            if characters[index] != "\n":
                characters[index] = " "
    return "".join(characters)


def _position_in_ranges(position: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in ranges)


def _lint_embedded_stylesheets(load_data: str) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    pattern = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(load_data):
        css_text = match.group(1)
        line_offset = load_data.count("\n", 0, match.start(1))
        messages.extend(
            _css_issue_to_html(issue, line_offset)
            for issue in lint_stylesheet(css_text)
        )
    return messages


def _css_issue_to_html(
    issue: CssLintIssue,
    line_offset: int = 0,
) -> HtmlTypoLintMessage:
    return HtmlTypoLintMessage(
        issue.severity,
        issue.message_key,
        issue.line_number + line_offset,
        issue.values,
    )


def _wordpress_block_tokens(load_data: str) -> list[_LintToken]:
    line_starts = _line_start_positions(load_data)
    tokens: list[_LintToken] = []
    for block_match in BLOCK_COMMENT_PATTERN.finditer(load_data):
        block_name = _normalize_block_name(block_match.group(2))
        tokens.append(
            _LintToken(
                position=block_match.start(),
                line_number=_line_number_at(block_match.start(), line_starts),
                name=block_name,
                token_type=(
                    "close" if block_match.group(1)
                    else "self_close" if block_match.group(4) else "open"
                ),
            )
        )
    return tokens


def _html_tag_tokens(
    load_data: str,
    line_number_offset: int = 0,
) -> list[_LintToken]:
    collector = _HtmlTagTokenCollector(
        _line_start_positions(load_data),
        line_number_offset,
    )
    collector.feed(load_data)
    collector.close()
    return collector.tokens


def _position_from_parser_pos(
    line_starts: list[int],
    line_number: int,
    column_number: int,
) -> int:
    if line_number <= 0 or line_number > len(line_starts):
        return 0
    return line_starts[line_number - 1] + column_number


def _load_lint_reference() -> dict[str, Any]:
    try:
        data = json.loads(LINT_REFERENCE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _reference_list(
    reference_data: dict[str, Any],
    key: str,
    fallback: list[str],
) -> list[str]:
    values = reference_data.get(key)
    if not isinstance(values, list):
        return fallback

    result = [value.strip().lower() for value in values if isinstance(value, str) and value.strip()]
    if not result:
        return fallback
    return result


def _reference_set(
    reference_data: dict[str, Any],
    key: str,
    fallback: set[str],
) -> set[str]:
    return set(_reference_list(reference_data, key, sorted(fallback)))


def _reference_attribute_map(
    reference_data: dict[str, Any],
    key: str,
    fallback: dict[str, set[str]],
) -> dict[str, set[str]]:
    values = reference_data.get(key)
    if not isinstance(values, dict):
        return fallback

    result: dict[str, set[str]] = {}
    for block_name, attributes in values.items():
        if not isinstance(block_name, str) or not isinstance(attributes, list):
            continue
        clean_block_name = block_name.strip().lower()
        clean_attributes = {
            attribute.strip()
            for attribute in attributes
            if isinstance(attribute, str) and attribute.strip()
        }
        if clean_block_name and clean_attributes:
            result[clean_block_name] = clean_attributes
    return result or fallback


def _reference_string_map(
    reference_data: dict[str, Any],
    key: str,
    fallback: dict[str, set[str]],
) -> dict[str, set[str]]:
    values = reference_data.get(key)
    if not isinstance(values, dict):
        return fallback

    result: dict[str, set[str]] = {}
    for item_name, item_values in values.items():
        if not isinstance(item_name, str) or not isinstance(item_values, list):
            continue
        clean_name = item_name.strip().lower()
        clean_values = {
            value.strip().lower()
            for value in item_values
            if isinstance(value, str) and value.strip()
        }
        if clean_name:
            result[clean_name] = clean_values
    return result or fallback


def _build_lint_reference_cache() -> LintReferenceCache:
    reference_data = _load_lint_reference()
    return LintReferenceCache(
        wordpress_core_blocks=_reference_set(
            reference_data,
            "wordpress_core_blocks",
            DEFAULT_WORDPRESS_CORE_BLOCKS,
        ),
        wordpress_block_attributes=_reference_attribute_map(
            reference_data,
            "wordpress_block_attributes",
            WORDPRESS_BLOCK_ATTRIBUTE_ALLOWLISTS,
        ),
        html_tags=_reference_set(reference_data, "html_tags", DEFAULT_HTML_TAGS),
        html_attributes=_reference_set(
            reference_data,
            "html_attributes",
            DEFAULT_HTML_ATTRIBUTES,
        ),
        html_attributes_by_tag=_reference_string_map(
            reference_data,
            "html_attributes_by_tag",
            DEFAULT_HTML_ATTRIBUTES_BY_TAG,
        ),
        global_html_attributes=_reference_set(
            reference_data,
            "global_html_attributes",
            DEFAULT_GLOBAL_HTML_ATTRIBUTES,
        ),
        allowed_attribute_prefixes=tuple(
            _reference_list(
                reference_data,
                "allowed_attribute_prefixes",
                list(DEFAULT_ALLOWED_ATTRIBUTE_PREFIXES),
            )
        ),
    )


LINT_REFERENCE_CACHE = _build_lint_reference_cache()
KNOWN_WORDPRESS_CORE_BLOCKS = LINT_REFERENCE_CACHE.wordpress_core_blocks
KNOWN_WORDPRESS_BLOCK_ATTRIBUTES = LINT_REFERENCE_CACHE.wordpress_block_attributes
KNOWN_HTML_TAGS = LINT_REFERENCE_CACHE.html_tags
KNOWN_HTML_ATTRIBUTES = LINT_REFERENCE_CACHE.html_attributes
KNOWN_HTML_ATTRIBUTES_BY_TAG = LINT_REFERENCE_CACHE.html_attributes_by_tag
KNOWN_GLOBAL_HTML_ATTRIBUTES = LINT_REFERENCE_CACHE.global_html_attributes
ALLOWED_HTML_ATTRIBUTE_PREFIXES = LINT_REFERENCE_CACHE.allowed_attribute_prefixes


def _lint_wordpress_block_typos(load_data: str) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    line_starts = _line_start_positions(load_data)
    for block_match in BLOCK_COMMENT_PATTERN.finditer(load_data):
        block_name = _normalize_block_name(block_match.group(2))
        if "/" in block_name or block_name in KNOWN_WORDPRESS_CORE_BLOCKS:
            continue

        suggestion = _find_closest_word(block_name, KNOWN_WORDPRESS_CORE_BLOCKS)
        values = {"block": block_name}
        if suggestion:
            values["suggestion"] = suggestion
        messages.append(
            HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.unknown_wordpress_block",
                _line_number_at(block_match.start(), line_starts),
                values,
            )
        )
    return messages


def _lint_wordpress_block_structure(
    load_data: str,
    html_tokens: list[_LintToken],
) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    line_starts = _line_start_positions(load_data)
    block_stack: list[_WordPressBlockStackItem] = []
    block_spans: list[_WordPressBlockStackItem] = []
    children_by_parent: dict[int, list[_WordPressBlockStackItem]] = {}
    paragraph_prefix_lines: dict[str, int] = {}
    html_positions = [token.position for token in html_tokens]

    for block_match in BLOCK_COMMENT_PATTERN.finditer(load_data):
        is_closing = bool(block_match.group(1))
        block_name = _normalize_block_name(block_match.group(2))
        line_number = _line_number_at(block_match.start(), line_starts)

        if not is_closing:
            if block_stack:
                block_stack[-1].has_children = True
                if block_stack[-1].affected_start is None:
                    block_stack[-1].affected_start = line_number
            messages.extend(_lint_wordpress_parent_child(block_name, block_stack, line_number))
            if (
                not block_match.group(4)
                and block_stack
                and block_stack[-1].name == block_name
                and block_name in NON_NESTABLE_WORDPRESS_BLOCKS
            ):
                unclosed = block_stack.pop()
                unclosed.boundary_valid = False
                unclosed.body_end = block_match.start()
                messages.append(_missing_wordpress_block_message(
                    unclosed, line_starts, len(load_data), repair_line=line_number,
                ))
            (
                block_attributes,
                block_attributes_valid,
                attributes_error_line_number,
            ) = _parse_wordpress_block_attributes(
                block_match.group(3),
                block_match.start(3) if block_match.group(3) is not None else -1,
                line_starts,
                line_number,
            )
            if not block_attributes_valid:
                messages.append(
                    HtmlTypoLintMessage(
                        "warning",
                        "html_typo_lint.invalid_wordpress_block_attributes",
                        attributes_error_line_number or line_number,
                        {"block": block_name},
                    )
                )
            if block_attributes_valid:
                messages.extend(
                    _lint_unknown_wordpress_block_attributes(
                        block_name,
                        block_attributes,
                        line_number,
                    )
                )
                messages.extend(
                    _lint_wordpress_block_attribute_semantics(
                        block_name,
                        block_attributes,
                        line_number,
                    )
                )
            if block_stack and block_stack[-1].name == "html":
                messages.append(
                    HtmlTypoLintMessage(
                        "warning",
                        "html_typo_lint.wordpress_html_contains_block_comment",
                        line_number,
                    )
                )
            span = _WordPressBlockStackItem(
                name=block_name, body_start=block_match.end(), open_line=line_number,
                attributes=block_attributes, attributes_valid=block_attributes_valid,
                pair_id=len(block_spans),
                parent_pair_id=block_stack[-1].pair_id if block_stack else None,
                depth=len(block_stack), open_position=block_match.start(),
                self_closing=bool(block_match.group(4)),
            )
            block_spans.append(span)
            if span.parent_pair_id is not None:
                children_by_parent.setdefault(span.parent_pair_id, []).append(span)
            if block_match.group(4):
                span.body_end = block_match.end()
                span.close_line = line_number
                span.close_end = block_match.end()
                continue
            block_stack.append(span)
            continue

        if not block_stack:
            messages.append(
                HtmlTypoLintMessage(
                    "error",
                    "html_typo_lint.unexpected_wordpress_closing_block",
                    line_number,
                    {"block": block_name, "affected_start": str(line_number),
                     "affected_end": str(_line_number_at(len(load_data), line_starts))},
                )
            )
            continue

        open_block = block_stack[-1]
        open_block_name = open_block.name
        open_end = open_block.body_start
        open_line_number = open_block.open_line
        block_attributes = open_block.attributes
        block_attributes_valid = open_block.attributes_valid
        if open_block_name != block_name:
            messages.append(
                HtmlTypoLintMessage(
                    "error",
                    "html_typo_lint.mismatched_wordpress_block",
                    line_number,
                    {"open_block": open_block_name, "close_block": block_name},
                )
            )
            matching_index = _last_open_wordpress_block_index(block_stack, block_name)
            if matching_index is None:
                open_block.boundary_valid = False
                continue
            for unclosed_block in reversed(block_stack[matching_index + 1 :]):
                unclosed_block.boundary_valid = False
                unclosed_block.body_end = block_match.start()
                messages.append(_missing_wordpress_block_message(
                    unclosed_block, line_starts, block_match.start(),
                ))
            block_stack[matching_index].boundary_valid = False
            block_stack[matching_index].body_end = block_match.start()
            block_stack[matching_index].close_line = line_number
            block_stack[matching_index].close_end = block_match.end()
            del block_stack[matching_index:]
            continue

        block_stack.pop()
        open_block.body_end = block_match.start()
        open_block.close_line = line_number
        open_block.close_end = block_match.end()
        block_body = load_data[open_end : block_match.start()]
        body_tokens = html_tokens[
            bisect_left(html_positions, open_end):
            bisect_left(html_positions, block_match.start())
        ]
        root_collector = None
        # Check only this block's own HTML. A child's HTML must not create a
        # parent shape/attribute cascade, while independent parent errors remain.
        child_ranges = [
            (child.open_position, child.close_end or block_match.start())
            for child in children_by_parent.get(open_block.pair_id, [])
        ]
        own_body = _mask_ranges(block_body, [
            (start - open_end, end - open_end) for start, end in child_ranges
        ])
        own_tokens = (
            [token for token in body_tokens if not _position_in_ranges(token.position, child_ranges)]
            if block_name == "paragraph" else body_tokens
        )
        suppress_body = not open_block.boundary_valid
        if block_name in WORDPRESS_HTML_SHAPES and not suppress_body:
            root_collector = _BlockRootCollector()
            root_collector.feed(own_body)
            root_collector.close()
            messages.extend(_lint_wordpress_block_html_shape(
                block_name, root_collector, open_line_number,
                _line_number_at(open_end, line_starts) - 1,
            ))
        if block_name == "paragraph" and not suppress_body:
            messages.extend(
                _lint_wordpress_paragraph_body(
                    own_body,
                    open_end,
                    line_starts,
                    open_line_number,
                    own_tokens,
                    suppress_missing_p=bool(root_collector and root_collector.root_tags
                                            and not any(tag == "p" for tag, _ in root_collector.root_tags)),
                )
            )
            paragraph_key = _paragraph_duplicate_key(own_body)
            if paragraph_key:
                previous_line = paragraph_prefix_lines.get(paragraph_key)
                if previous_line is not None:
                    messages.append(
                        HtmlTypoLintMessage(
                            "warning",
                            "html_typo_lint.duplicate_wordpress_paragraph",
                            open_line_number,
                            {"previous_line": str(previous_line)},
                        )
                    )
                else:
                    paragraph_prefix_lines[paragraph_key] = open_line_number
        if block_name == "separator":
            messages.extend(
                _lint_wordpress_separator_body(
                    own_body,
                    open_end,
                    line_starts,
                    open_line_number,
                )
            )
        if block_name in DECORATED_BLOCKS_BETTER_AS_HTML:
            messages.extend(
                _lint_decorated_wordpress_block_should_use_html(
                    block_name,
                    own_body,
                    open_end,
                    line_starts,
                    open_line_number,
                    block_attributes,
                )
            )
        if block_name != "separator":
            messages.extend(
                _lint_html_tag_structure(
                    body_tokens,
                    STRUCTURAL_HTML_TAGS,
                )
            )
        if block_attributes_valid and not suppress_body:
            messages.extend(
                _lint_wordpress_block_attribute_html_consistency(
                    block_name,
                    block_attributes,
                    own_body,
                    open_line_number,
                    root_collector,
                )
            )

    for block in block_stack:
        block.boundary_valid = False
        block.body_end = len(load_data)
        messages.append(_missing_wordpress_block_message(block, line_starts, len(load_data)))
    messages.extend(_lint_html_wordpress_boundaries(block_spans, html_tokens))
    return messages


def _lint_wordpress_parent_child(
    block_name: str,
    block_stack: list[_WordPressBlockStackItem],
    line_number: int,
) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    parent = block_stack[-1].name if block_stack else ""
    required_parent = WORDPRESS_REQUIRED_PARENTS.get(block_name)
    # A repeated non-nestable opener is already diagnosed as a missing close;
    # check its repaired sibling context rather than cascading a parent error.
    required_parent_context = (
        block_stack[-2].name if parent == block_name
        and block_name in NON_NESTABLE_WORDPRESS_BLOCKS and len(block_stack) > 1 else parent
    )
    if required_parent and required_parent_context != required_parent:
        messages.append(HtmlTypoLintMessage(
            "error", "html_typo_lint.invalid_wordpress_parent", line_number,
            {"block": block_name, "parent": required_parent},
        ))
    if parent in WORDPRESS_NON_CONTAINER_BLOCKS or (
        parent in WORDPRESS_ALLOWED_CHILDREN
        and block_name not in WORDPRESS_ALLOWED_CHILDREN[parent]
    ):
        message_key = (
            "html_typo_lint.wordpress_paragraph_contains_html_block"
            if parent == "paragraph" and block_name == "html"
            else "html_typo_lint.invalid_wordpress_child"
        )
        messages.append(HtmlTypoLintMessage(
            "error" if block_name in KNOWN_WORDPRESS_CORE_BLOCKS else "warning",
            message_key, line_number,
            {"block": block_name, "parent": parent} if block_name != "html" or parent != "paragraph" else None,
        ))
    return messages


def _last_open_wordpress_block_index(
    block_stack: list[_WordPressBlockStackItem],
    block_name: str,
) -> int | None:
    for index in range(len(block_stack) - 1, -1, -1):
        if block_stack[index].name == block_name:
            return index
    return None


def _missing_wordpress_block_message(
    block: _WordPressBlockStackItem,
    line_starts: list[int],
    range_end: int,
    *,
    repair_line: int | None = None,
) -> HtmlTypoLintMessage:
    block_name = block.name
    message_key = "html_typo_lint.missing_wordpress_closing_block"
    if block_name == "html":
        message_key = "html_typo_lint.missing_wordpress_html_closing_block"
    return HtmlTypoLintMessage(
        "error",
        message_key,
        repair_line or block.open_line,
        {"block": block_name,
         "affected_start": str(block.affected_start or block.open_line),
         "affected_end": str(_line_number_at(range_end, line_starts))},
    )


def _lint_html_wordpress_boundaries(
    spans: list[_WordPressBlockStackItem], tokens: list[_LintToken],
) -> list[HtmlTypoLintMessage]:
    """Find HTML opened inside a block but still open at its explicit boundary.

    A container's surrounding HTML is outside its child's body, so remains valid.
    Invalid WP boundaries are handled by the primary block-stack diagnostics.
    """
    boundaries = sorted(
        (span for span in spans if span.boundary_valid and not span.self_closing
         and span.body_end is not None),
        key=lambda span: span.body_end if span.body_end is not None else -1,
    )
    open_tags: list[_LintToken] = []
    reported: set[int] = set()
    messages: list[HtmlTypoLintMessage] = []
    token_index = 0
    for span in boundaries:
        assert span.body_end is not None
        while token_index < len(tokens) and tokens[token_index].position < span.body_end:
            token = tokens[token_index]
            token_index += 1
            if token.token_type == "open" and token.name not in VOID_TAGS:
                open_tags.append(token)
            elif token.token_type == "close":
                match_index = next((i for i in range(len(open_tags) - 1, -1, -1)
                                    if open_tags[i].name == token.name), None)
                if match_index is not None:
                    del open_tags[match_index:]
        for token in open_tags:
            if token.position < span.body_start or token.position in reported:
                continue
            reported.add(token.position)
            messages.append(HtmlTypoLintMessage(
                "error", "html_typo_lint.html_crosses_wordpress_boundary", token.line_number,
                {"tag": token.name, "block": span.name,
                 "boundary_line": str(span.close_line)},
            ))
    return messages


def _parse_wordpress_block_attributes(
    attributes_text: str | None,
    attributes_start_position: int,
    line_starts: list[int],
    fallback_line_number: int,
) -> _ParsedWordPressBlockAttributes:
    if attributes_text is None:
        return {}, True, None
    attributes_text = attributes_text.strip()
    if not attributes_text:
        return {}, True, None
    attributes_line_number = _line_number_at(
        attributes_start_position,
        line_starts,
    )
    attributes_column_number = _column_number_at(
        attributes_start_position,
        line_starts,
    )
    json_issues = lint_json_fragment(
        attributes_text,
        start_line_number=attributes_line_number,
        start_column_number=attributes_column_number,
        require_container=True,
    )
    if json_issues:
        return {}, False, json_issues[0].line_number
    block_attributes = json.loads(attributes_text)
    if not isinstance(block_attributes, dict):
        return {}, False, attributes_line_number
    return block_attributes, True, None


def _lint_unknown_wordpress_block_attributes(
    block_name: str,
    block_attributes: dict[str, Any],
    line_number: int,
) -> list[HtmlTypoLintMessage]:
    allowed_attributes = KNOWN_WORDPRESS_BLOCK_ATTRIBUTES.get(block_name)
    if allowed_attributes is None:
        return []

    messages: list[HtmlTypoLintMessage] = []
    for attribute in block_attributes:
        if attribute in allowed_attributes:
            continue
        values = {"block": block_name, "attribute": attribute}
        suggestion = _find_closest_word(attribute, allowed_attributes)
        if suggestion:
            values["suggestion"] = suggestion
        messages.append(
            HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.unknown_wordpress_block_attribute",
                line_number,
                values,
            )
        )
    return messages


def _lint_wordpress_block_attribute_semantics(
    block_name: str,
    block_attributes: dict[str, Any],
    line_number: int,
) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    allowed_attributes = KNOWN_WORDPRESS_BLOCK_ATTRIBUTES.get(block_name)
    for attribute, value in block_attributes.items():
        if allowed_attributes is not None and attribute not in allowed_attributes:
            continue

        expected_type = WORDPRESS_BLOCK_ATTRIBUTE_TYPE_RULES.get(
            (block_name, attribute)
        )
        if expected_type and not _wordpress_attribute_value_has_type(
            value,
            expected_type,
        ):
            messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.invalid_wordpress_block_attribute_type",
                    line_number,
                    {
                        "block": block_name,
                        "attribute": attribute,
                        "expected_type": expected_type,
                        "actual_value": _wordpress_attribute_value_text(value),
                    },
                )
            )

        allowed_values = WORDPRESS_BLOCK_ATTRIBUTE_VALUE_RULES.get(
            (block_name, attribute)
        )
        if allowed_values is None:
            continue
        if not isinstance(value, str):
            messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.invalid_wordpress_block_attribute_type",
                    line_number,
                    {
                        "block": block_name,
                        "attribute": attribute,
                        "expected_type": "string",
                        "actual_value": _wordpress_attribute_value_text(value),
                    },
                )
            )
            continue
        if value in allowed_values:
            continue
        values = {
            "block": block_name,
            "attribute": attribute,
            "allowed_values": ", ".join(sorted(allowed_values)),
            "actual_value": _wordpress_attribute_value_text(value),
        }
        suggestion = _find_closest_word(value, allowed_values)
        if suggestion:
            values["suggestion"] = suggestion
        messages.append(
            HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.invalid_wordpress_block_attribute_value",
                line_number,
                values,
            )
        )
    return messages


def _wordpress_attribute_value_has_type(value: Any, expected_type: str) -> bool:
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "string":
        return isinstance(value, str)
    return True


def _wordpress_attribute_value_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _lint_wordpress_block_attribute_html_consistency(
    block_name: str,
    block_attributes: dict[str, Any],
    block_body: str,
    line_number: int,
    root_collector: _BlockRootCollector | None = None,
) -> list[HtmlTypoLintMessage]:
    if block_name == "paragraph" and root_collector is not None:
        return _lint_wordpress_paragraph_attributes(block_attributes, root_collector, line_number)
    if block_name == "heading" and root_collector is not None:
        return _lint_wordpress_heading_level_consistency(
            block_attributes,
            root_collector,
            line_number,
        )
    if block_name == "spacer":
        return _lint_wordpress_spacer_height_consistency(
            block_attributes,
            block_body,
            line_number,
        )
    if block_name == "image":
        return _lint_wordpress_image_size_consistency(
            block_attributes,
            block_body,
            line_number,
        )
    return []


def _lint_wordpress_block_html_shape(
    block_name: str, collector: _BlockRootCollector, line_number: int,
    body_line_offset: int = 0,
) -> list[HtmlTypoLintMessage]:
    expected_tags = WORDPRESS_HTML_SHAPES[block_name]
    if (
        len(collector.root_tags) == 1
        and collector.root_tags[0][0] in expected_tags
        and not collector.has_root_text
    ):
        return []
    return [HtmlTypoLintMessage(
        "error", "html_typo_lint.wordpress_block_html_shape",
        body_line_offset + collector.first_content_line if collector.first_content_line else line_number,
        {"block": block_name, "tag": " / ".join(sorted(expected_tags))},
    )]


def _lint_wordpress_paragraph_attributes(
    block_attributes: dict[str, Any], collector: _BlockRootCollector, line_number: int,
) -> list[HtmlTypoLintMessage]:
    if len(collector.root_tags) != 1 or collector.root_tags[0][0] != "p":
        return []
    html_attributes = collector.root_tags[0][1]
    style_text = html_attributes.get("style", "")
    if any(issue.severity == "error" for issue in lint_inline_style(style_text)):
        return []  # CSS syntax diagnostics take priority over consistency guesses.
    html_style = parse_inline_style_values(style_text)
    if html_style is None:
        return []
    block_style = block_attributes.get("style", {})
    if not isinstance(block_style, dict):
        return []
    messages: list[HtmlTypoLintMessage] = []
    # Only registered, direct paragraph properties are checked. Inline children,
    # theme CSS, spacing/borders and arbitrary custom classes are not inferred.
    style_rules = {
        "typography": {
            "fontWeight": "font-weight", "fontStyle": "font-style",
            "fontSize": "font-size", "lineHeight": "line-height",
            "letterSpacing": "letter-spacing", "textDecoration": "text-decoration",
            "textTransform": "text-transform",
        },
        "color": {"text": "color", "background": "background-color"},
    }
    for section, rules in style_rules.items():
        section_values = block_style.get(section, {})
        if not isinstance(section_values, dict):
            continue
        for attribute, css_property in rules.items():
            expected = section_values.get(attribute)
            actual = html_style.get(css_property)
            # Preset attributes serialize through classes rather than inline CSS.
            preset_attribute = {
                "font-size": "fontSize", "color": "textColor",
                "background-color": "backgroundColor",
            }.get(css_property)
            if preset_attribute and block_attributes.get(preset_attribute):
                continue
            if expected is None and actual is None:
                continue
            if isinstance(expected, bool) or (
                not isinstance(expected, (str, int, float)) and expected is not None
            ):
                continue
            expected_text = str(expected) if expected is not None else "(absent)"
            actual_text = actual if actual is not None else "(absent)"
            if _normalize_css_value(_wordpress_style_value(expected_text)) != _normalize_css_value(actual_text):
                messages.append(_wordpress_attribute_html_mismatch_message(
                    line_number, "paragraph", f"style.{section}.{attribute}",
                    expected_text, f"{css_property}:{actual_text}",
                ))
    classes = set(html_attributes.get("class", "").split())
    for attribute, prefix, suffix in (
        ("textColor", "has-", "-color"),
        ("backgroundColor", "has-", "-background-color"),
        ("fontSize", "has-", "-font-size"),
    ):
        value = block_attributes.get(attribute)
        if isinstance(value, str) and f"{prefix}{value}{suffix}" not in classes:
            messages.append(_wordpress_attribute_html_mismatch_message(
                line_number, "paragraph", attribute, value,
                html_attributes.get("class", "(absent)"),
            ))
    return messages


def _wordpress_style_value(value: str) -> str:
    # Gutenberg's style engine converts preset references to CSS variables.
    if value.startswith("var:"):
        return "var(--wp--" + value[4:].replace("|", "--") + ")"
    return value


def _lint_wordpress_heading_level_consistency(
    block_attributes: dict[str, Any],
    collector: _BlockRootCollector,
    line_number: int,
) -> list[HtmlTypoLintMessage]:
    level = block_attributes.get("level")
    if level is None:
        level = 2
    if not isinstance(level, int) or isinstance(level, bool):
        return []
    if len(collector.root_tags) != 1:
        return []
    heading_tag = collector.root_tags[0][0]
    if heading_tag not in {f"h{number}" for number in range(1, 7)}:
        return []
    html_level = heading_tag[1:]
    if str(level) == html_level:
        return []
    return [
        _wordpress_attribute_html_mismatch_message(
            line_number,
            "heading",
            "level",
            str(level),
            f"h{html_level}",
        )
    ]


def _lint_wordpress_spacer_height_consistency(
    block_attributes: dict[str, Any],
    block_body: str,
    line_number: int,
) -> list[HtmlTypoLintMessage]:
    height = block_attributes.get("height")
    if not isinstance(height, str):
        return []
    height_match = re.search(
        r"\bheight\s*:\s*([^;\"']+)",
        block_body,
        re.IGNORECASE,
    )
    if height_match is None:
        return []
    html_height = _normalize_css_value(height_match.group(1))
    attribute_height = _normalize_css_value(height)
    if attribute_height == html_height:
        return []
    return [
        _wordpress_attribute_html_mismatch_message(
            line_number,
            "spacer",
            "height",
            height,
            height_match.group(1).strip(),
        )
    ]


def _lint_wordpress_image_size_consistency(
    block_attributes: dict[str, Any],
    block_body: str,
    line_number: int,
) -> list[HtmlTypoLintMessage]:
    size_slug = block_attributes.get("sizeSlug")
    if not isinstance(size_slug, str):
        return []
    size_class_match = re.search(
        r'\bclass\s*=\s*["\'][^"\']*\bsize-([a-zA-Z0-9_-]+)\b',
        block_body,
        re.IGNORECASE,
    )
    if size_class_match is None:
        return []
    html_size = size_class_match.group(1)
    if size_slug.lower() == html_size.lower():
        return []
    return [
        _wordpress_attribute_html_mismatch_message(
            line_number,
            "image",
            "sizeSlug",
            size_slug,
            f"size-{html_size}",
        )
    ]


def _wordpress_attribute_html_mismatch_message(
    line_number: int,
    block: str,
    attribute: str,
    attribute_value: str,
    html_value: str,
) -> HtmlTypoLintMessage:
    return HtmlTypoLintMessage(
        "warning",
        "html_typo_lint.wordpress_block_attribute_html_mismatch",
        line_number,
        {
            "block": block,
            "attribute": attribute,
            "attribute_value": attribute_value,
            "html_value": html_value,
        },
    )


def _normalize_css_value(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())


def _lint_wordpress_paragraph_body(
    block_body: str,
    body_start_position: int,
    line_starts: list[int],
    line_number: int,
    tokens: list[_LintToken],
    *,
    suppress_missing_p: bool = False,
) -> list[HtmlTypoLintMessage]:
    messages: list[HtmlTypoLintMessage] = []
    p_open = next((token for token in tokens if token.name == "p" and token.token_type == "open"), None)
    p_close = next((token for token in tokens if token.name == "p" and token.token_type == "close"), None)
    div_open = next((token for token in tokens if token.name == "div" and token.token_type == "open"), None)
    if p_open is None and not suppress_missing_p:
        messages.append(
            HtmlTypoLintMessage(
                "error",
                "html_typo_lint.wordpress_paragraph_missing_p_open",
                _first_body_content_line_number(
                    block_body,
                    body_start_position,
                    line_starts,
                    line_number,
                ),
            )
        )
    if p_close is None and not suppress_missing_p:
        messages.append(
            HtmlTypoLintMessage(
                "error",
                "html_typo_lint.wordpress_paragraph_missing_p_close",
                p_open.line_number if p_open else _first_body_content_line_number(
                    block_body, body_start_position, line_starts, line_number,
                ),
            )
        )
    if div_open is not None:
        messages.append(
            HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.wordpress_paragraph_contains_div",
                div_open.line_number,
            )
        )
    return messages


def _lint_wordpress_separator_body(
    block_body: str,
    body_start_position: int,
    line_starts: list[int],
    line_number: int,
) -> list[HtmlTypoLintMessage]:
    code_match = re.search(r"</?code(?:\s|>)", block_body, re.IGNORECASE)
    if code_match is None:
        return []
    return [
        HtmlTypoLintMessage(
            "error",
            "html_typo_lint.wordpress_separator_contains_code",
            _match_line_number(code_match, body_start_position, line_starts, line_number),
        )
    ]


def _lint_decorated_wordpress_block_should_use_html(
    block_name: str,
    block_body: str,
    body_start_position: int,
    line_starts: list[int],
    line_number: int,
    block_attributes: dict[str, Any],
) -> list[HtmlTypoLintMessage]:
    """Warn when fragile WordPress blocks are used for styled decoration."""
    messages: list[HtmlTypoLintMessage] = []
    if "style" in block_attributes:
        messages.append(
            HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.wordpress_decorated_block_should_use_html",
                line_number,
                {"block": block_name},
            )
        )

    style_match = re.search(
        r"<[A-Za-z][A-Za-z0-9:-]*\b[^>]*\sstyle\s*=",
        block_body,
        re.IGNORECASE,
    )
    if style_match is not None:
        style_line_number = _match_line_number(
            style_match,
            body_start_position,
            line_starts,
            line_number,
        )
        if not any(message.line_number == style_line_number for message in messages):
            messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.wordpress_decorated_block_should_use_html",
                    style_line_number,
                    {"block": block_name},
                )
            )
    return messages


def _first_body_content_line_number(
    block_body: str,
    body_start_position: int,
    line_starts: list[int],
    fallback_line_number: int,
) -> int:
    content_match = re.search(r"\S", block_body)
    return _match_line_number(
        content_match,
        body_start_position,
        line_starts,
        fallback_line_number,
    )


def _match_line_number(
    match: re.Match[str] | None,
    body_start_position: int,
    line_starts: list[int],
    fallback_line_number: int,
) -> int:
    if match is None:
        return fallback_line_number
    return _line_number_at(body_start_position + match.start(), line_starts)


def _paragraph_duplicate_key(block_body: str) -> str:
    without_comments = BLOCK_COMMENT_PATTERN.sub(" ", block_body)
    without_tags = re.sub(r"<[^<>]+>", " ", without_comments)
    text = unescape(without_tags)
    normalized_text = re.sub(r"\s+", "", text)
    if len(normalized_text) < 30:
        return ""
    return normalized_text[:30]


def _line_start_positions(load_data: str) -> list[int]:
    return [0] + [
        match.end()
        for match in re.finditer(r"\n", load_data)
    ]


def _line_number_at(position: int, line_starts: list[int]) -> int:
    line_number = 1
    for index, line_start in enumerate(line_starts, start=1):
        if line_start > position:
            break
        line_number = index
    return line_number


def _column_number_at(position: int, line_starts: list[int]) -> int:
    line_number = _line_number_at(position, line_starts)
    return position - line_starts[line_number - 1] + 1


def _normalize_block_name(block_name: str) -> str:
    clean_block_name = block_name.strip().lower()
    if clean_block_name.startswith("core/"):
        return clean_block_name.removeprefix("core/")
    return clean_block_name


def _find_closest_word(word: str, choices: set[str]) -> str | None:
    matches = get_close_matches(word, sorted(choices), n=1, cutoff=0.72)
    if not matches:
        return None
    return matches[0]


def _is_known_html_attribute(attr_name: str) -> bool:
    if attr_name in KNOWN_HTML_ATTRIBUTES:
        return True
    return any(attr_name.startswith(prefix) for prefix in ALLOWED_HTML_ATTRIBUTE_PREFIXES)


def _is_global_html_attribute(attr_name: str) -> bool:
    if attr_name in KNOWN_GLOBAL_HTML_ATTRIBUTES:
        return True
    return any(attr_name.startswith(prefix) for prefix in ALLOWED_HTML_ATTRIBUTE_PREFIXES)


def _is_wordpress_accordion_toggle_button(tag: str, attrs: dict[str, str]) -> bool:
    if tag != "button" or attrs.get("type", "").lower() != "button":
        return False
    class_names = set(attrs.get("class", "").split())
    return "wp-block-accordion-heading__toggle" in class_names


def _lint_html_attribute_continuation(
    load_data: str,
    tag: str,
    start: int,
    end: int,
    break_ranges: dict[int, int],
    line_starts: list[int],
) -> HtmlTypoLintMessage | None:
    """Inspect only the body prefix after a parser-confirmed complete start tag."""
    position = start
    first_attribute: tuple[str, int] | None = None
    while position < end:
        if load_data[position].isspace():
            position += 1
            continue
        if position in break_ranges and first_attribute is not None:
            position = break_ranges[position]
            continue
        if load_data[position] == ">":
            if first_attribute is not None:
                break
            # An isolated delimiter immediately after a completed opener is
            # suspicious. Comparisons, prose and delimiters inside real tags
            # never enter this case.
            prefix = load_data[start:position]
            line_suffix = load_data[position + 1:end].split("\n", 1)[0]
            if "\n" in prefix and not prefix.strip() and not line_suffix.strip():
                return HtmlTypoLintMessage(
                    "warning", "html_typo_lint.unexpected_html_tag_close_delimiter",
                    _line_number_at(position, line_starts), {"tag": tag},
                )
            return None
        attribute_match = HTML_ATTRIBUTE_ASSIGNMENT_PATTERN.match(load_data, position, end)
        if attribute_match is None:
            return None
        attribute = attribute_match.group(1).lower()
        if not (_is_known_html_attribute(attribute) or _is_global_html_attribute(attribute)):
            return None
        if first_attribute is None:
            first_attribute = (attribute, position)
        position = attribute_match.end()

    if first_attribute is None:
        return None
    attribute, attribute_position = first_attribute
    if position == end and "\n" not in load_data[start:attribute_position]:
        # A lone inline attribute example is ordinary body text. A complete
        # attribute-only continuation on following lines is a stronger signal.
        return None
    contains_break = any(attribute_position <= item < position for item in break_ranges)
    key = (
        "html_typo_lint.malformed_html_attribute_continuation" if contains_break
        else "html_typo_lint.html_attribute_outside_opening_tag"
    )
    return HtmlTypoLintMessage(
        "warning", key, _line_number_at(attribute_position, line_starts),
        {"tag": tag, "attribute": attribute},
    )


class HtmlTypoLintParser(HTMLParser):
    def __init__(
        self,
        load_data: str = "",
        suppressed_ranges: list[tuple[int, int]] | None = None,
    ) -> None:
        super().__init__(convert_charrefs=False)
        self.messages: list[HtmlTypoLintMessage] = []
        self.inline_stack: list[tuple[str, int, int]] = []
        self.inline_boundaries: list[str] = []
        self.line_starts = _line_start_positions(load_data)
        self.suppressed_ranges = suppressed_ranges or []
        self.reported_unknown_html_tags: set[tuple[int, str]] = set()
        self.load_data = load_data
        self.attribute_opening: tuple[str, int] | None = None
        self.attribute_break_ranges: dict[int, int] = {}
        self.attribute_example_tags: list[str] = []

    def _parser_position(self) -> int:
        line_number, column_number = self.getpos()
        return _position_from_parser_pos(self.line_starts, line_number, column_number)

    def _flush_attribute_continuation(self, end: int | None = None) -> None:
        opening = self.attribute_opening
        self.attribute_opening = None
        break_ranges = self.attribute_break_ranges
        self.attribute_break_ranges = {}
        if opening is None:
            return
        tag, start = opening
        message = _lint_html_attribute_continuation(
            self.load_data, tag, start, self._parser_position() if end is None else end,
            break_ranges, self.line_starts,
        )
        if message is not None:
            self.messages.append(message)

    def _track_attribute_start(self, tag: str, *, self_closing: bool = False) -> None:
        position = self._parser_position()
        start_tag_text = self.get_starttag_text() or ""
        if tag == "br" and self.attribute_opening is not None:
            self.attribute_break_ranges[position] = position + len(start_tag_text)
            return
        self._flush_attribute_continuation(position)
        if self._is_suppressed_inline_position():
            return
        if not self_closing and tag in ATTRIBUTE_EXAMPLE_TAGS:
            self.attribute_example_tags.append(tag)
        if self_closing or self.attribute_example_tags:
            return
        self.attribute_opening = (tag, position + len(start_tag_text))

    def handle_comment(self, data: str) -> None:
        self._flush_attribute_continuation()

    def handle_decl(self, decl: str) -> None:
        self._flush_attribute_continuation()

    def handle_pi(self, data: str) -> None:
        self._flush_attribute_continuation()

    def _is_suppressed_inline_position(self) -> bool:
        line_number, column_number = self.getpos()
        return bool(self.suppressed_ranges) and _position_in_ranges(
            _position_from_parser_pos(self.line_starts, line_number, column_number),
            self.suppressed_ranges,
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._track_attribute_start(tag)
        self._lint_tag_and_attrs(tag, attrs)
        if self._is_suppressed_inline_position():
            return
        clean_tag = tag.lower()
        if clean_tag in VOID_TAGS:
            return
        if clean_tag in INLINE_PARENT_BOUNDARY_TAGS:
            self.inline_boundaries.append(clean_tag)
        if clean_tag in INLINE_TAGS:
            self.inline_stack.append((clean_tag, self.getpos()[0], len(self.inline_boundaries)))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._track_attribute_start(tag, self_closing=True)
        self._lint_tag_and_attrs(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        self._flush_attribute_continuation()
        if not self._is_suppressed_inline_position() and tag in self.attribute_example_tags:
            index = len(self.attribute_example_tags) - 1 - self.attribute_example_tags[::-1].index(tag)
            del self.attribute_example_tags[index:]
        clean_tag = tag.lower()
        line_number = self.getpos()[0]
        self._lint_unknown_html_tag(clean_tag, line_number)
        if not self._is_suppressed_inline_position():
            self._lint_inline_endtag(clean_tag, line_number)

    def close(self) -> None:
        super().close()
        self._flush_attribute_continuation(len(self.load_data))
        self._lint_unclosed_inline_tags_at_document_end()

    def _lint_tag_and_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        clean_tag = tag.lower()
        line_number = self.getpos()[0]
        self._lint_unknown_html_tag(clean_tag, line_number)
        attrs_dict = {name.lower(): value or "" for name, value in attrs}
        self._lint_restricted_html_tag(clean_tag, attrs_dict, line_number)
        self._lint_unknown_html_attrs(clean_tag, attrs_dict, line_number)
        self._lint_unexpected_html_attrs_for_tag(clean_tag, attrs_dict, line_number)
        self._lint_restricted_html_attrs(clean_tag, attrs_dict, line_number)
        if "style" in attrs_dict:
            self.messages.extend(
                _css_issue_to_html(issue)
                for issue in lint_inline_style(attrs_dict["style"], line_number)
            )

    def _lint_inline_endtag(self, tag: str, line_number: int) -> None:
        if tag in INLINE_TAGS:
            self._close_inline_tag(tag, line_number)
            return
        if tag in INLINE_PARENT_BOUNDARY_TAGS:
            self._lint_unclosed_inline_tags_before_parent(tag)

    def _close_inline_tag(self, tag: str, line_number: int) -> None:
        if self.inline_stack and self.inline_stack[-1][0] == tag:
            self.inline_stack.pop()
            return

        matching_index = next(
            (
                index
                for index in range(len(self.inline_stack) - 1, -1, -1)
                if self.inline_stack[index][0] == tag
            ),
            None,
        )
        if matching_index is None:
            self.messages.append(HtmlTypoLintMessage(
                "warning", "html_typo_lint.unexpected_inline_closing_tag", line_number,
                {"tag": tag},
            ))
            return

        expected_tag = self.inline_stack[-1][0]
        self.messages.append(
            HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.inline_tag_closing_order",
                line_number,
                {"tag": expected_tag, "closing_tag": tag},
            )
        )
        del self.inline_stack[matching_index]

    def _lint_unclosed_inline_tags_before_parent(self, parent_tag: str) -> None:
        boundary_index = next((
            index for index in range(len(self.inline_boundaries) - 1, -1, -1)
            if self.inline_boundaries[index] == parent_tag
        ), None)
        if boundary_index is None:
            return
        while self.inline_stack and self.inline_stack[-1][2] > boundary_index:
            tag, line_number, _ = self.inline_stack.pop()
            self.messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.inline_tag_unclosed_before_parent",
                    line_number,
                    {"tag": tag, "parent": parent_tag},
                )
            )
        del self.inline_boundaries[boundary_index:]

    def _lint_unclosed_inline_tags_at_document_end(self) -> None:
        while self.inline_stack:
            tag, line_number, _ = self.inline_stack.pop()
            self.messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.inline_tag_unclosed_at_document_end",
                    line_number,
                    {"tag": tag},
                )
            )

    def _lint_unknown_html_tag(self, tag: str, line_number: int) -> None:
        if tag in KNOWN_HTML_TAGS or "-" in tag or ":" in tag:
            return
        report_key = (line_number, tag)
        if report_key in self.reported_unknown_html_tags:
            return
        self.reported_unknown_html_tags.add(report_key)

        suggestion = _find_closest_word(tag, KNOWN_HTML_TAGS)
        values = {"tag": tag}
        if suggestion:
            values["suggestion"] = suggestion
        self.messages.append(
            HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.unknown_html_tag",
                line_number,
                values,
            )
        )

    def _lint_restricted_html_tag(
        self,
        tag: str,
        attrs: dict[str, str],
        line_number: int,
    ) -> None:
        reason = RESTRICTED_HTML_TAG_REASONS.get(tag)
        if reason is None:
            return
        if _is_wordpress_accordion_toggle_button(tag, attrs):
            return
        self.messages.append(
            HtmlTypoLintMessage(
                "warning",
                "html_typo_lint.restricted_html_tag",
                line_number,
                {"tag": tag, "reason": reason},
            )
        )

    def _lint_unknown_html_attrs(
        self,
        tag: str,
        attrs: dict[str, str],
        line_number: int,
    ) -> None:
        for attr_name, attr_value in attrs.items():
            if _is_known_html_attribute(attr_name):
                continue

            suggestion = COMMON_HTML_ATTRIBUTE_TYPOS.get(attr_name)
            if suggestion is None:
                suggestion = _find_closest_word(attr_name, KNOWN_HTML_ATTRIBUTES)
            values = {"tag": tag, "attribute": attr_name, "value": attr_value}
            if suggestion:
                values["suggestion"] = suggestion
            self.messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.unknown_html_attribute",
                    line_number,
                    values,
                )
            )

    def _lint_unexpected_html_attrs_for_tag(
        self,
        tag: str,
        attrs: dict[str, str],
        line_number: int,
    ) -> None:
        allowed_attributes = KNOWN_HTML_ATTRIBUTES_BY_TAG.get(tag)
        if allowed_attributes is None:
            return

        for attr_name in attrs:
            if not _is_known_html_attribute(attr_name):
                continue
            if _is_global_html_attribute(attr_name):
                continue
            if attr_name in allowed_attributes:
                continue
            self.messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.unexpected_html_attribute_for_tag",
                    line_number,
                    {"tag": tag, "attribute": attr_name},
                )
            )

    def _lint_restricted_html_attrs(
        self,
        tag: str,
        attrs: dict[str, str],
        line_number: int,
    ) -> None:
        for attr_name in attrs:
            if not attr_name.startswith(RESTRICTED_HTML_ATTRIBUTE_PREFIXES):
                continue
            self.messages.append(
                HtmlTypoLintMessage(
                    "warning",
                    "html_typo_lint.restricted_html_attribute",
                    line_number,
                    {
                        "tag": tag,
                        "attribute": attr_name,
                        "reason": "inline JavaScript event handler",
                    },
                )
            )


class _BlockRootCollector(HTMLParser):
    """Read real root elements without treating comments or escaped code as tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root_tags: list[tuple[str, dict[str, str]]] = []
        self.open_tags: list[str] = []
        self.has_root_text = False
        self.first_content_line: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._record_root(tag, attrs)
        if tag not in VOID_TAGS:
            self.open_tags.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._record_root(tag, attrs)

    def _record_root(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self.open_tags:
            if self.first_content_line is None:
                self.first_content_line = self.getpos()[0]
            self.root_tags.append((tag, {name: value or "" for name, value in attrs}))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.open_tags) - 1, -1, -1):
            if self.open_tags[index] == tag:
                del self.open_tags[index:]
                break

    def handle_data(self, data: str) -> None:
        if not self.open_tags and data.strip():
            self.has_root_text = True
            if self.first_content_line is None:
                self.first_content_line = self.getpos()[0] + data[:len(data) - len(data.lstrip())].count("\n")


class _HtmlTagTokenCollector(HTMLParser):
    def __init__(self, line_starts: list[int], line_number_offset: int = 0) -> None:
        super().__init__(convert_charrefs=False)
        self.line_starts = line_starts
        self.line_number_offset = line_number_offset
        self.tokens: list[_LintToken] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._append_token(tag, "open")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._append_token(tag, "self_close")

    def handle_endtag(self, tag: str) -> None:
        self._append_token(tag, "close")

    def _append_token(self, tag: str, token_type: str) -> None:
        line_number, column_number = self.getpos()
        self.tokens.append(
            _LintToken(
                position=_position_from_parser_pos(
                    self.line_starts,
                    line_number,
                    column_number,
                ),
                line_number=line_number + self.line_number_offset,
                name=tag.lower(),
                token_type=token_type,
            )
        )
