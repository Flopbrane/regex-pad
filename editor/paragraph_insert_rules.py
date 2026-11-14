from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PARAGRAPH_INSERT_DICTIONARY_FILE_NAME = "paragraph_insert_dict.json"
DEFAULT_DICTIONARIES_PATH = Path(__file__).resolve().parent.parent / "dictionaries"
REQUIRED_OPERATION_KEYS = {"insert_spacer", "insert_html", "decorated_block"}
SUPPORTED_CONTENT_TRANSFORMS = {"none", "code", "decorated"}


class ParagraphInsertDictionaryError(ValueError):
    """Raised when the paragraph-insertion dictionary is invalid."""


@dataclass(frozen=True)
class TextReplacementRule:
    search: str
    exclude: str
    replacement: str


@dataclass(frozen=True)
class ParagraphGrammarRules:
    paragraph_block_search: str
    paragraph_tag_search: str
    paragraph_replacement: str
    block_separator: str
    trim_leading_breaks: TextReplacementRule
    trim_trailing_breaks: TextReplacementRule
    break_to_newline: TextReplacementRule
    newline_to_break: TextReplacementRule
    not_available_key: str
    cross_block_key: str
    paragraph_attributes_key: str
    paragraph_structure_key: str


@dataclass(frozen=True)
class ParagraphInsertRule:
    key: str
    search: str
    exclude: str
    empty_search: str
    empty_exclude: str
    replacement: str
    content_transform: str
    allow_nonempty_selection: bool
    expand_selection_to_lines: bool
    empty_requires_blank_line: bool
    empty_selection: str
    error_key: str
    default_parameters: dict[str, str]


@dataclass(frozen=True)
class ParagraphInsertRuleBook:
    load_file_path: Path
    grammar: ParagraphGrammarRules
    operations: dict[str, ParagraphInsertRule]

    def operation(self, key: str) -> ParagraphInsertRule:
        try:
            return self.operations[key]
        except KeyError as error:
            raise ParagraphInsertDictionaryError(
                f"operation key is not registered: {key!r} ({self.load_file_path})"
            ) from error


def paragraph_insert_dictionary_path(
    dictionaries_path: Path | None = None,
) -> Path:
    """Resolve the active paragraph-insertion dictionary with a bundled fallback."""
    if dictionaries_path is not None:
        candidate = dictionaries_path / PARAGRAPH_INSERT_DICTIONARY_FILE_NAME
        if candidate.is_file():
            return candidate
    return DEFAULT_DICTIONARIES_PATH / PARAGRAPH_INSERT_DICTIONARY_FILE_NAME


def load_paragraph_insert_rule_book(
    dictionaries_path: Path | None = None,
) -> ParagraphInsertRuleBook:
    load_file_path = paragraph_insert_dictionary_path(dictionaries_path)
    try:
        load_data = json.loads(load_file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ParagraphInsertDictionaryError(
            f"cannot read {load_file_path}: {error}"
        ) from error
    root = _require_object(load_data, "root", load_file_path)
    if root.get("schema_version") != 1:
        raise ParagraphInsertDictionaryError(
            f"schema_version must be 1 ({load_file_path})"
        )

    grammar_data = _require_object(root.get("grammar"), "grammar", load_file_path)
    paragraph_block = _text_rule(grammar_data, "paragraph_block", load_file_path)
    paragraph_tag = _text_rule(grammar_data, "paragraph_tag", load_file_path)
    _validate_named_groups(
        paragraph_block.search,
        {"body"},
        "grammar.paragraph_block.search",
        load_file_path,
    )
    _validate_named_groups(
        paragraph_tag.search,
        {"attributes", "content"},
        "grammar.paragraph_tag.search",
        load_file_path,
    )
    paragraph_replacement = _require_string(
        grammar_data.get("paragraph_replacement"),
        "grammar.paragraph_replacement",
        load_file_path,
    )
    if paragraph_replacement.count("{selection}") != 1:
        raise ParagraphInsertDictionaryError(
            f"grammar.paragraph_replacement must contain one {{selection}} ({load_file_path})"
        )

    messages = _require_object(grammar_data.get("messages"), "grammar.messages", load_file_path)
    grammar = ParagraphGrammarRules(
        paragraph_block_search=paragraph_block.search,
        paragraph_tag_search=paragraph_tag.search,
        paragraph_replacement=paragraph_replacement,
        block_separator=_require_string(
            grammar_data.get("block_separator"),
            "grammar.block_separator",
            load_file_path,
        ),
        trim_leading_breaks=_text_rule(grammar_data, "trim_leading_breaks", load_file_path),
        trim_trailing_breaks=_text_rule(grammar_data, "trim_trailing_breaks", load_file_path),
        break_to_newline=_text_rule(grammar_data, "break_to_newline", load_file_path),
        newline_to_break=_text_rule(grammar_data, "newline_to_break", load_file_path),
        not_available_key=_message_key(messages, "not_available", load_file_path),
        cross_block_key=_message_key(messages, "cross_block", load_file_path),
        paragraph_attributes_key=_message_key(
            messages,
            "paragraph_attributes",
            load_file_path,
        ),
        paragraph_structure_key=_message_key(
            messages,
            "paragraph_structure",
            load_file_path,
        ),
    )

    operations_data = _require_object(root.get("operations"), "operations", load_file_path)
    missing_keys = REQUIRED_OPERATION_KEYS - operations_data.keys()
    if missing_keys:
        raise ParagraphInsertDictionaryError(
            f"missing operation keys {sorted(missing_keys)!r} ({load_file_path})"
        )
    operations = {
        key: _operation_rule(key, value, load_file_path)
        for key, value in operations_data.items()
    }
    return ParagraphInsertRuleBook(load_file_path, grammar, operations)


def _text_rule(
    parent: dict[str, Any],
    key: str,
    load_file_path: Path,
) -> TextReplacementRule:
    value = _require_object(parent.get(key), f"grammar.{key}", load_file_path)
    rule = TextReplacementRule(
        search=_require_nonempty_string(
            value.get("search"),
            f"grammar.{key}.search",
            load_file_path,
        ),
        exclude=_require_string(value.get("exclude", ""), f"grammar.{key}.exclude", load_file_path),
        replacement=_require_string(
            value.get("replacement", ""),
            f"grammar.{key}.replacement",
            load_file_path,
        ),
    )
    _validate_pattern(rule.search, f"grammar.{key}.search", load_file_path)
    if rule.exclude:
        _validate_pattern(rule.exclude, f"grammar.{key}.exclude", load_file_path)
    return rule


def _operation_rule(
    key: str,
    value: Any,
    load_file_path: Path,
) -> ParagraphInsertRule:
    data = _require_object(value, f"operations.{key}", load_file_path)
    selection = _require_object(
        data.get("selection"),
        f"operations.{key}.selection",
        load_file_path,
    )
    search = _require_nonempty_string(
        data.get("search"),
        f"operations.{key}.search",
        load_file_path,
    )
    exclude = _require_string(
        data.get("exclude", ""),
        f"operations.{key}.exclude",
        load_file_path,
    )
    empty_search = _require_nonempty_string(
        selection.get("empty_search", search),
        f"operations.{key}.selection.empty_search",
        load_file_path,
    )
    empty_exclude = _require_string(
        selection.get("empty_exclude", exclude),
        f"operations.{key}.selection.empty_exclude",
        load_file_path,
    )
    replacement = _require_string(
        data.get("replacement"),
        f"operations.{key}.replacement",
        load_file_path,
    )
    transform = _require_string(
        data.get("content_transform"),
        f"operations.{key}.content_transform",
        load_file_path,
    )
    if transform not in SUPPORTED_CONTENT_TRANSFORMS:
        raise ParagraphInsertDictionaryError(
            f"unsupported content_transform {transform!r} for {key!r} ({load_file_path})"
        )
    if replacement.count("{cursor}") != 1:
        raise ParagraphInsertDictionaryError(
            f"operations.{key}.replacement must contain one {{cursor}} ({load_file_path})"
        )
    _validate_pattern(search, f"operations.{key}.search", load_file_path)
    if exclude:
        _validate_pattern(exclude, f"operations.{key}.exclude", load_file_path)
    _validate_pattern(
        empty_search,
        f"operations.{key}.selection.empty_search",
        load_file_path,
    )
    if empty_exclude:
        _validate_pattern(
            empty_exclude,
            f"operations.{key}.selection.empty_exclude",
            load_file_path,
        )

    parameters_data = _require_object(
        data.get("default_parameters", {}),
        f"operations.{key}.default_parameters",
        load_file_path,
    )
    default_parameters = {
        parameter_key: _require_string(
            parameter_value,
            f"operations.{key}.default_parameters.{parameter_key}",
            load_file_path,
        )
        for parameter_key, parameter_value in parameters_data.items()
    }
    _validate_operation_placeholders(
        replacement,
        default_parameters,
        key,
        load_file_path,
    )
    return ParagraphInsertRule(
        key=key,
        search=search,
        exclude=exclude,
        empty_search=empty_search,
        empty_exclude=empty_exclude,
        replacement=replacement,
        content_transform=transform,
        allow_nonempty_selection=_require_bool(
            selection.get("allow_nonempty"),
            f"operations.{key}.selection.allow_nonempty",
            load_file_path,
        ),
        expand_selection_to_lines=_require_bool(
            selection.get("expand_to_lines"),
            f"operations.{key}.selection.expand_to_lines",
            load_file_path,
        ),
        empty_requires_blank_line=_require_bool(
            selection.get("empty_requires_blank_line"),
            f"operations.{key}.selection.empty_requires_blank_line",
            load_file_path,
        ),
        empty_selection=_require_string(
            data.get("empty_selection", ""),
            f"operations.{key}.empty_selection",
            load_file_path,
        ),
        error_key=_require_string(
            data.get("error_key"),
            f"operations.{key}.error_key",
            load_file_path,
        ),
        default_parameters=default_parameters,
    )


def _validate_pattern(pattern: str, field: str, load_file_path: Path) -> None:
    try:
        re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    except re.error as error:
        raise ParagraphInsertDictionaryError(
            f"invalid regular expression in {field}: {error} ({load_file_path})"
        ) from error


def _validate_operation_placeholders(
    replacement: str,
    default_parameters: dict[str, str],
    operation_key: str,
    load_file_path: Path,
) -> None:
    placeholders = set(re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", replacement))
    supported = {"selection", "cursor", *default_parameters}
    unknown = placeholders - supported
    if unknown:
        raise ParagraphInsertDictionaryError(
            f"operations.{operation_key}.replacement has unknown placeholders "
            f"{sorted(unknown)!r} ({load_file_path})"
        )


def _validate_named_groups(
    pattern: str,
    required_groups: set[str],
    field: str,
    load_file_path: Path,
) -> None:
    compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    missing = required_groups - compiled.groupindex.keys()
    if missing:
        raise ParagraphInsertDictionaryError(
            f"{field} is missing named groups {sorted(missing)!r} ({load_file_path})"
        )


def _message_key(
    messages: dict[str, Any],
    key: str,
    load_file_path: Path,
) -> str:
    return _require_string(messages.get(key), f"grammar.messages.{key}", load_file_path)


def _require_object(value: Any, field: str, load_file_path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ParagraphInsertDictionaryError(
            f"{field} must be an object ({load_file_path})"
        )
    return value


def _require_string(value: Any, field: str, load_file_path: Path) -> str:
    if not isinstance(value, str):
        raise ParagraphInsertDictionaryError(
            f"{field} must be a string ({load_file_path})"
        )
    return value


def _require_nonempty_string(value: Any, field: str, load_file_path: Path) -> str:
    result = _require_string(value, field, load_file_path)
    if not result:
        raise ParagraphInsertDictionaryError(
            f"{field} must not be empty ({load_file_path})"
        )
    return result


def _require_bool(value: Any, field: str, load_file_path: Path) -> bool:
    if not isinstance(value, bool):
        raise ParagraphInsertDictionaryError(
            f"{field} must be true or false ({load_file_path})"
        )
    return value
