from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path
from typing import Any

CSS_REFERENCE_PATH = (
    Path(__file__).resolve().parent.parent
    / "dictionaries"
    / "standards"
    / "standard_css.json"
)
PROPERTY_NAME_PATTERN = re.compile(r"^(?:--|-?[A-Za-z])[A-Za-z0-9_-]*$")
SIMPLE_KEYWORD_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
SIMPLE_NUMBER_PATTERN = re.compile(r"^[-+]?(?:\d+(?:\.\d*)?|\.\d+)$")
NUMBER_WITH_UNIT_PATTERN = re.compile(
    r"(?<![\w.-])[-+]?(?:\d+(?:\.\d*)?|\.\d+)([A-Za-z]+)\b"
)
PROPERTY_LIKE_PATTERN = re.compile(r"(?:^|\s)(--?[A-Za-z][\w-]*|[A-Za-z][\w-]*)\s*:")
AT_RULE_PATTERN = re.compile(r"@([A-Za-z][A-Za-z0-9-]*)")
CURSOR_PLACEHOLDER = "{cursor}"
CURSOR_PLACEHOLDER_CSS_VALUE = "var(--regex-pad-cursor)"


@dataclass(frozen=True)
class CssLintIssue:
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


@lru_cache(maxsize=1)
def _load_css_reference() -> dict[str, Any]:
    load_data: Any = json.loads(CSS_REFERENCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(load_data, dict):
        raise TypeError("CSS reference root must be an object")
    return load_data


def lint_inline_style(
    style_text: str,
    start_line_number: int = 1,
) -> list[CssLintIssue]:
    """Lint declarations from one HTML style attribute."""
    try:
        reference = _load_css_reference()
    except (OSError, json.JSONDecodeError, TypeError) as error:
        return [
            CssLintIssue(
                "error",
                "css_lint.reference_unavailable",
                start_line_number,
                {"error": str(error)},
            )
        ]
    style_text = _mask_cursor_placeholder(style_text)
    masked_text, messages = _mask_css_comments(style_text, start_line_number)
    messages.extend(
        _lint_inline_style_with_reference(masked_text, start_line_number, reference)
    )
    return sorted(messages, key=lambda issue: issue.line_number)


def parse_inline_style_values(style_text: str) -> dict[str, str] | None:
    """Read declarations using the same comment/quote/parenthesis rules as lint."""
    style_text = _mask_cursor_placeholder(style_text)
    masked_text, comment_issues = _mask_css_comments(style_text)
    declarations, syntax_issues = _split_declarations(masked_text, 1)
    if comment_issues or syntax_issues:
        return None
    values: dict[str, str] = {}
    for declaration, _ in declarations:
        if not declaration.strip():
            continue
        property_name, separator, value = declaration.partition(":")
        if not separator or not PROPERTY_NAME_PATTERN.fullmatch(property_name.strip()):
            return None
        values[property_name.strip().lower()] = value.strip()
    return values


def lint_stylesheet(css_text: str) -> list[CssLintIssue]:
    """Lint declaration blocks in a standalone stylesheet."""
    try:
        reference = _load_css_reference()
    except (OSError, json.JSONDecodeError, TypeError) as error:
        return [
            CssLintIssue(
                "error",
                "css_lint.reference_unavailable",
                1,
                {"error": str(error)},
            )
        ]

    masked_text, messages = _mask_css_comments(css_text)
    if (
        "{" not in masked_text
        and not masked_text.lstrip().startswith("@")
        and PROPERTY_LIKE_PATTERN.search(masked_text)
    ):
        property_match = PROPERTY_LIKE_PATTERN.search(masked_text)
        assert property_match is not None
        messages.append(
            CssLintIssue(
                "error",
                "css_lint.missing_opening_brace",
                _line_number_at(masked_text, property_match.start()),
            )
        )
    known_at_rules = set(_as_string_list(reference.get("at_rules", [])))
    for match in AT_RULE_PATTERN.finditer(masked_text):
        at_rule = match.group(1).lower()
        if at_rule not in known_at_rules:
            messages.append(
                CssLintIssue(
                    "warning",
                    "css_lint.unknown_at_rule",
                    _line_number_at(masked_text, match.start()),
                    {"at_rule": at_rule},
                )
            )

    stack: list[dict[str, int | bool]] = []
    quote: str | None = None
    quote_line = 1
    escaped = False
    line_number = 1
    for index, character in enumerate(masked_text):
        if character == "\n":
            line_number += 1
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
            quote_line = line_number
            continue
        if character == "{":
            if stack:
                stack[-1]["has_child"] = True
            stack.append(
                {
                    "content_start": index + 1,
                    "content_line": line_number,
                    "open_line": line_number,
                    "has_child": False,
                }
            )
            continue
        if character != "}":
            continue
        if not stack:
            messages.append(
                CssLintIssue(
                    "error",
                    "css_lint.unexpected_closing_brace",
                    line_number,
                )
            )
            continue
        block = stack.pop()
        if not bool(block["has_child"]):
            content_start = int(block["content_start"])
            messages.extend(
                _lint_inline_style_with_reference(
                    masked_text[content_start:index],
                    int(block["content_line"]),
                    reference,
                )
            )

    for block in stack:
        messages.append(
            CssLintIssue(
                "error",
                "css_lint.missing_closing_brace",
                int(block["open_line"]),
            )
        )
    if quote is not None:
        messages.append(CssLintIssue("error", "css_lint.unclosed_quote", quote_line))
    return sorted(messages, key=lambda issue: issue.line_number)


def _lint_inline_style_with_reference(
    style_text: str,
    start_line_number: int,
    reference: dict[str, Any],
) -> list[CssLintIssue]:
    messages = _lint_full_width_symbols(style_text, start_line_number, reference)
    declarations, structure_messages = _split_declarations(style_text, start_line_number)
    messages.extend(structure_messages)

    properties = _as_dict(reference.get("properties", {}))
    property_typos = _as_string_dict(
        _as_dict(reference.get("known_typos", {})).get("property_names", {})
    )
    unit_typos = _as_string_dict(
        _as_dict(reference.get("known_typos", {})).get("units", {})
    )
    global_keywords = set(_as_string_list(reference.get("global_keywords", [])))
    seen_properties: dict[str, int] = {}

    for declaration, line_number in declarations:
        messages.extend(
            _lint_declaration(
                declaration,
                line_number,
                properties,
                property_typos,
                unit_typos,
                global_keywords,
                seen_properties,
            )
        )
    return sorted(messages, key=lambda issue: issue.line_number)


def _split_declarations(
    style_text: str,
    start_line_number: int,
) -> tuple[list[tuple[str, int]], list[CssLintIssue]]:
    declarations: list[tuple[str, int]] = []
    messages: list[CssLintIssue] = []
    segment_start = 0
    segment_line = start_line_number
    line_number = start_line_number
    quote: str | None = None
    quote_line = start_line_number
    escaped = False
    parenthesis_lines: list[int] = []

    for index, character in enumerate(style_text):
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            if character == "\n":
                line_number += 1
            continue
        if character in {'"', "'"}:
            quote = character
            quote_line = line_number
        elif character == "(":
            parenthesis_lines.append(line_number)
        elif character == ")":
            if parenthesis_lines:
                parenthesis_lines.pop()
            else:
                messages.append(
                    CssLintIssue(
                        "error",
                        "css_lint.unexpected_closing_parenthesis",
                        line_number,
                    )
                )
        elif character in "{}":
            messages.append(
                CssLintIssue(
                    "error",
                    "css_lint.unexpected_brace_inline",
                    line_number,
                    {"symbol": character},
                )
            )
        elif character == ";" and not parenthesis_lines:
            declarations.append((style_text[segment_start:index], segment_line))
            segment_start = index + 1
            segment_line = line_number
        if character == "\n":
            line_number += 1

    declarations.append((style_text[segment_start:], segment_line))
    if quote is not None:
        messages.append(CssLintIssue("error", "css_lint.unclosed_quote", quote_line))
    for open_line in parenthesis_lines:
        messages.append(
            CssLintIssue("error", "css_lint.missing_closing_parenthesis", open_line)
        )
    return declarations, messages


def _lint_declaration(
    declaration: str,
    line_number: int,
    properties: dict[str, Any],
    property_typos: dict[str, str],
    unit_typos: dict[str, str],
    global_keywords: set[str],
    seen_properties: dict[str, int],
) -> list[CssLintIssue]:
    leading_whitespace_length = len(declaration) - len(declaration.lstrip())
    line_number += declaration[:leading_whitespace_length].count("\n")
    declaration = declaration.strip()
    if not declaration:
        return []
    if ":" not in declaration:
        return [
            CssLintIssue(
                "error",
                "css_lint.missing_colon",
                line_number,
                {"declaration": declaration},
            )
        ]

    raw_property_name, raw_value = declaration.split(":", 1)
    property_name = raw_property_name.strip().lower()
    value = raw_value.strip()
    messages: list[CssLintIssue] = []
    if not PROPERTY_NAME_PATTERN.fullmatch(property_name):
        return [
            CssLintIssue(
                "error",
                "css_lint.invalid_property_name",
                line_number,
                {"property": property_name},
            )
        ]
    if not value:
        return [
            CssLintIssue(
                "error",
                "css_lint.empty_value",
                line_number,
                {"property": property_name},
            )
        ]

    if property_name in seen_properties:
        messages.append(
            CssLintIssue(
                "info",
                "css_lint.duplicate_property",
                line_number,
                {
                    "property": property_name,
                    "previous_line": str(seen_properties[property_name]),
                },
            )
        )
    else:
        seen_properties[property_name] = line_number

    if property_name.startswith("--"):
        return messages

    typo_replacement = property_typos.get(property_name)
    if typo_replacement:
        messages.append(
            CssLintIssue(
                "warning",
                "css_lint.known_property_typo",
                line_number,
                {"property": property_name, "suggestion": typo_replacement},
            )
        )
        return messages

    lookup_name = _unprefixed_property_name(property_name)
    property_rule = properties.get(lookup_name)
    if not isinstance(property_rule, dict):
        suggestion = _closest_property(lookup_name, set(properties))
        values = {"property": property_name}
        message_key = "css_lint.unknown_property"
        if suggestion:
            values["suggestion"] = suggestion
            message_key = "css_lint.unknown_property_with_suggestion"
        messages.append(CssLintIssue("warning", message_key, line_number, values))
        return messages

    missing_separator_property = _property_after_missing_semicolon(
        value,
        set(properties),
        set(property_typos),
    )
    if missing_separator_property:
        messages.append(
            CssLintIssue(
                "error",
                "css_lint.missing_semicolon",
                line_number,
                {"property": missing_separator_property},
            )
        )

    messages.extend(_lint_known_unit_typos(value, line_number, unit_typos))
    messages.extend(
        _lint_property_value(
            lookup_name,
            value,
            property_rule,
            line_number,
            global_keywords,
        )
    )
    return messages


def _lint_property_value(
    property_name: str,
    value: str,
    property_rule: dict[str, Any],
    line_number: int,
    global_keywords: set[str],
) -> list[CssLintIssue]:
    clean_value = re.sub(r"\s*!important\s*$", "", value, flags=re.IGNORECASE).strip()
    lower_value = clean_value.lower()
    if lower_value in global_keywords or lower_value.startswith("var("):
        return []

    keywords = set(_as_string_list(property_rule.get("keywords", [])))
    if keywords and SIMPLE_KEYWORD_PATTERN.fullmatch(clean_value) and lower_value not in keywords:
        return [
            CssLintIssue(
                "warning",
                "css_lint.invalid_keyword",
                line_number,
                {
                    "property": property_name,
                    "value": clean_value,
                    "allowed_values": ", ".join(sorted(keywords)),
                },
            )
        ]

    value_types = set(_as_string_list(property_rule.get("value_types", [])))
    if property_name == "opacity":
        opacity_issue = _lint_opacity(clean_value, line_number)
        if opacity_issue is not None:
            return [opacity_issue]
    if (
        value_types == {"integer", "keyword", "css_variable"}
        and lower_value != "auto"
        and not re.fullmatch(r"[-+]?\d+", clean_value)
    ):
        return [
            CssLintIssue(
                "error",
                "css_lint.invalid_integer",
                line_number,
                {"property": property_name, "value": clean_value},
            )
        ]
    length_types = {"length", "length_list", "length_or_auto"}
    if (
        value_types & length_types
        and not value_types & {"number", "integer"}
        and SIMPLE_NUMBER_PATTERN.fullmatch(clean_value)
        and float(clean_value) != 0
    ):
        return [
            CssLintIssue(
                "warning",
                "css_lint.missing_unit",
                line_number,
                {"property": property_name, "value": clean_value},
            )
        ]
    return []


def _lint_opacity(value: str, line_number: int) -> CssLintIssue | None:
    try:
        if value.endswith("%"):
            numeric_value = float(value[:-1])
            valid = 0 <= numeric_value <= 100
        else:
            numeric_value = float(value)
            valid = 0 <= numeric_value <= 1
    except ValueError:
        return None
    if valid:
        return None
    return CssLintIssue(
        "error",
        "css_lint.value_out_of_range",
        line_number,
        {"property": "opacity", "value": value},
    )


def _lint_known_unit_typos(
    value: str,
    line_number: int,
    unit_typos: dict[str, str],
) -> list[CssLintIssue]:
    messages: list[CssLintIssue] = []
    for match in NUMBER_WITH_UNIT_PATTERN.finditer(value):
        unit = match.group(1).lower()
        suggestion = unit_typos.get(unit)
        if suggestion:
            messages.append(
                CssLintIssue(
                    "warning",
                    "css_lint.known_unit_typo",
                    line_number,
                    {"unit": unit, "suggestion": suggestion},
                )
            )
    return messages


def _mask_cursor_placeholder(style_text: str) -> str:
    """Keep editable cursor placeholders out of CSS syntax diagnostics."""
    if style_text.strip() == CURSOR_PLACEHOLDER:
        return ""
    return style_text.replace(CURSOR_PLACEHOLDER, CURSOR_PLACEHOLDER_CSS_VALUE)


def _lint_full_width_symbols(
    style_text: str,
    start_line_number: int,
    reference: dict[str, Any],
) -> list[CssLintIssue]:
    replacements = _as_string_dict(reference.get("full_width_replacements", {}))
    messages: list[CssLintIssue] = []
    for symbol, replacement in replacements.items():
        search_start = 0
        while True:
            position = style_text.find(symbol, search_start)
            if position < 0:
                break
            messages.append(
                CssLintIssue(
                    "warning",
                    "css_lint.full_width_symbol",
                    start_line_number + style_text.count("\n", 0, position),
                    {"symbol": symbol, "suggestion": replacement},
                )
            )
            search_start = position + len(symbol)
    return messages


def _mask_css_comments(
    css_text: str,
    start_line_number: int = 1,
) -> tuple[str, list[CssLintIssue]]:
    characters = list(css_text)
    messages: list[CssLintIssue] = []
    position = 0
    while position < len(css_text):
        start = css_text.find("/*", position)
        if start < 0:
            break
        end = css_text.find("*/", start + 2)
        if end < 0:
            messages.append(
                CssLintIssue(
                    "error",
                    "css_lint.unclosed_comment",
                    start_line_number + _line_number_at(css_text, start) - 1,
                )
            )
            end = len(css_text) - 2
        for index in range(start, min(end + 2, len(characters))):
            if characters[index] != "\n":
                characters[index] = " "
        position = end + 2
    return "".join(characters), messages


def _property_after_missing_semicolon(
    value: str,
    known_properties: set[str],
    typo_properties: set[str],
) -> str | None:
    for match in PROPERTY_LIKE_PATTERN.finditer(value):
        candidate = match.group(1).lower()
        if candidate in known_properties or candidate in typo_properties:
            return candidate
    return None


def _unprefixed_property_name(property_name: str) -> str:
    for prefix in ("-webkit-", "-moz-", "-ms-", "-o-"):
        if property_name.startswith(prefix):
            return property_name.removeprefix(prefix)
    return property_name


def _closest_property(property_name: str, choices: set[str]) -> str | None:
    matches = get_close_matches(property_name, sorted(choices), n=1, cutoff=0.72)
    return matches[0] if matches else None


def _line_number_at(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): str(item)
        for key, item in value.items()
        if isinstance(key, str) and isinstance(item, str)
    }


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]
