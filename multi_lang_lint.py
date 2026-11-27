"""言語別の辞書と標準参照ファイルを検証する。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from json_lint import JsonLintIssue, lint_json_file

STANDARD_FILE_NAMES = (
    "standard_javascript.json",
    "standard_textscript.json",
    "standard_css.json",
    "standard_json.json",
    "html_tag_schema.json",
    "wordpress_block_schema.json",
)

REFERENCE_FILE_CONTRACTS = {
    "standard_javascript.json": ("language_id", "javascript", ()),
    "standard_textscript.json": ("language_id", "textscript", ()),
    "standard_css.json": (
        "language_id",
        "css",
        ("properties", "value_types", "known_typos"),
    ),
    "standard_json.json": (
        "language_id",
        "json",
        ("value_types", "literals", "unsupported_features"),
    ),
    "html_tag_schema.json": (
        "schema_id",
        "html_tags",
        ("global_attributes", "tags", "value_types"),
    ),
    "wordpress_block_schema.json": (
        "schema_id",
        "wordpress_core_blocks",
        ("shared_attributes", "blocks", "value_types"),
    ),
}


def standard_file_names() -> tuple[str, ...]:
    """対応する標準ファイルの名前を返す。"""
    return STANDARD_FILE_NAMES


def lint_standard_files(standards_path: Path) -> tuple[JsonLintIssue, ...]:
    """標準参照ファイルの内容を検証する。"""
    issues: list[JsonLintIssue] = []
    for file_name in STANDARD_FILE_NAMES:
        load_file_path = standards_path / file_name
        if not load_file_path.exists():
            issues.append(
                JsonLintIssue(
                    load_file_path,
                    "Standard reference file is missing.",
                )
            )
            continue
        file_issues = lint_json_file(load_file_path)
        issues.extend(file_issues)
        if not file_issues:
            issues.extend(_lint_reference_contract(load_file_path))
    return tuple(issues)


def _lint_reference_contract(load_file_path: Path) -> tuple[JsonLintIssue, ...]:
    """同梱の参照ファイルに識別子と必須のデータ集合があるかを確認する。"""
    contract = REFERENCE_FILE_CONTRACTS.get(load_file_path.name)
    if contract is None:
        return ()
    identifier_key, expected_identifier, required_collections = contract
    load_data: Any = json.loads(load_file_path.read_text(encoding="utf-8"))
    if not isinstance(load_data, dict):
        return (JsonLintIssue(load_file_path, "Reference root must be an object."),)

    issues: list[JsonLintIssue] = []
    if load_data.get(identifier_key) != expected_identifier:
        issues.append(
            JsonLintIssue(
                load_file_path,
                f"{identifier_key} must be {expected_identifier!r}.",
            )
        )
    for collection_name in required_collections:
        collection = load_data.get(collection_name)
        if not isinstance(collection, dict | list) or not collection:
            issues.append(
                JsonLintIssue(
                    load_file_path,
                    f"{collection_name} must be a non-empty object or array.",
                )
            )
    return tuple(issues)


def lint_dictionary_plugin(
    load_file_path: Path,
    standards_path: Path | None = None,
) -> tuple[JsonLintIssue, ...]:
    """挿入辞書と関連する標準ファイルを検証する。"""
    issues = list(lint_json_file(load_file_path))
    if standards_path is not None:
        issues.extend(lint_standard_files(standards_path))
    return tuple(issues)
