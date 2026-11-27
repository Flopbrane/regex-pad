"""複数の言語の文法チェックを検証する。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from json_lint import lint_json_file, lint_json_fragment, validate_json_file
from multi_lang_lint import (
    lint_dictionary_plugin,
    lint_standard_files,
    standard_file_names,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_json_lint_accepts_object_or_array(tmp_path: Path) -> None:
    """JSONの文法チェックがオブジェクトまたは配列を受け入れることを確認する。"""
    object_path = tmp_path / "object.json"
    array_path = tmp_path / "array.json"
    object_path.write_text('{"name": "sample"}', encoding="utf-8")
    array_path.write_text('[{"name": "sample"}]', encoding="utf-8")

    assert lint_json_file(object_path) == ()
    assert lint_json_file(array_path) == ()


def test_json_lint_rejects_invalid_json(tmp_path: Path) -> None:
    """JSONの文法チェックが不正なJSONを拒否することを確認する。"""
    load_file_path = tmp_path / "broken.json"
    load_file_path.write_text('{"name": ', encoding="utf-8")

    issues = lint_json_file(load_file_path)

    assert len(issues) == 1
    assert "Invalid JSON" in issues[0].message
    with pytest.raises(ValueError, match="Invalid JSON"):
        validate_json_file(load_file_path)


def test_json_lint_rejects_scalar_root(tmp_path: Path) -> None:
    """JSONの文法チェックがスカラーのルート要素を拒否することを確認する。"""
    load_file_path = tmp_path / "scalar.json"
    load_file_path.write_text('"sample"', encoding="utf-8")

    issues = lint_json_file(load_file_path)

    assert len(issues) == 1
    assert "object or an array" in issues[0].message


def test_json_lint_fragment_preserves_source_position() -> None:
    """JSONの文法チェックの断片が原文の位置を維持することを確認する。"""
    issues = lint_json_fragment(
        '{"level":\n}',
        start_line_number=12,
        start_column_number=18,
    )

    assert len(issues) == 1
    assert issues[0].line_number == 13
    assert issues[0].column_number == 1
    assert "line 13, column 1" in issues[0].message


def test_json_lint_fragment_can_require_container_root() -> None:
    """JSONの文法チェックの断片が必須とするのコンテナのルート要素が可能であることを確認する。"""
    issues = lint_json_fragment(
        '"sample"',
        start_line_number=5,
        start_column_number=9,
    )

    assert len(issues) == 1
    assert issues[0].line_number == 5
    assert issues[0].column_number == 9
    assert "object or an array" in issues[0].message


def test_multi_lang_standard_files_are_present_and_valid() -> None:
    """複数の言語の標準のファイルが存在すると正しいであることを確認する。"""
    standards_path = PROJECT_ROOT / "dictionaries" / "standards"

    assert standard_file_names() == (
        "standard_javascript.json",
        "standard_textscript.json",
        "standard_css.json",
        "standard_json.json",
        "html_tag_schema.json",
        "wordpress_block_schema.json",
    )
    assert lint_standard_files(standards_path) == ()


def _load_project_json(load_file_path: Path) -> dict[str, Any]:
    """リポジトリ内の参照JSONをテスト用に読み込む。"""
    load_data: Any = json.loads(load_file_path.read_text(encoding="utf-8"))
    assert isinstance(load_data, dict)
    return load_data


def test_css_standard_contains_properties_types_and_typo_repairs() -> None:
    """CSSの標準のがプロパティの型と表記ミスの修復を含むことを確認する。"""
    load_data = _load_project_json(
        PROJECT_ROOT / "dictionaries" / "standards" / "standard_css.json"
    )
    properties = load_data["properties"]
    value_types = set(load_data["value_types"])

    assert load_data["status"] == "active"
    assert len(properties) >= 70
    assert properties["display"]["keywords"] == [
        "block",
        "contents",
        "flex",
        "flow-root",
        "grid",
        "inline",
        "inline-block",
        "inline-flex",
        "inline-grid",
        "list-item",
        "none",
        "table",
    ]
    assert properties["margin"]["value_types"] == [
        "length_list",
        "length_or_auto",
        "percentage",
        "css_variable",
    ]
    assert load_data["known_typos"]["units"]["en"] == "em"
    assert load_data["known_typos"]["property_names"]["text-aling"] == "text-align"
    assert load_data["full_width_replacements"]["："] == ":"

    for property_data in properties.values():
        assert set(property_data["value_types"]) <= value_types
    for function_data in load_data["functions"].values():
        assert set(function_data["value_types"]) <= value_types


def test_json_standard_contains_syntax_hints_and_common_repairs() -> None:
    """JSONの標準のが構文のヒントと共通の修復を含むことを確認する。"""
    load_data = _load_project_json(
        PROJECT_ROOT / "dictionaries" / "standards" / "standard_json.json"
    )

    assert load_data["status"] == "active"
    assert load_data["root_types"] == ["object", "array"]
    assert set(load_data["literals"]) == {"true", "false", "null"}
    assert load_data["known_typos"]["True"] == "true"
    assert load_data["known_typos"]["None"] == "null"
    assert "trailing_commas" in load_data["unsupported_features"]
    assert load_data["full_width_replacements"]["｛"] == "{"


def test_html_tag_schema_matches_existing_reference_names() -> None:
    """HTMLタグのスキーマと既存の参照名が一致することを確認する。"""
    standards_path = PROJECT_ROOT / "dictionaries" / "standards"
    schema = _load_project_json(standards_path / "html_tag_schema.json")
    lint_reference = _load_project_json(
        PROJECT_ROOT / "dictionaries" / "lint_reference.json"
    )
    known_tags = set(lint_reference["html_tags"])
    known_global_attributes = set(lint_reference["global_html_attributes"])
    known_attributes_by_tag = lint_reference["html_attributes_by_tag"]
    schema_value_types = set(schema["value_types"])

    assert schema["status"] == "active"
    assert len(schema["tags"]) >= 30
    assert set(schema["allowed_attribute_prefixes"]) == set(
        lint_reference["allowed_attribute_prefixes"]
    )
    assert set(schema["global_attributes"]) <= known_global_attributes
    assert schema["tags"]["img"]["required_attributes"] == ["src", "alt"]
    assert schema["tags"]["img"]["attributes"]["alt"]["allow_empty"] is True
    assert schema["tags"]["th"]["attributes"]["scope"]["values"] == [
        "col",
        "colgroup",
        "row",
        "rowgroup",
    ]

    for tag_name, tag_data in schema["tags"].items():
        assert tag_name in known_tags
        schema_attribute_names = set(tag_data["attributes"])
        reference_attribute_names = set(known_attributes_by_tag.get(tag_name, []))
        assert schema_attribute_names <= reference_attribute_names
        assert set(tag_data["required_attributes"]) <= schema_attribute_names
        for attribute_data in tag_data["attributes"].values():
            assert attribute_data["type"] in schema_value_types
            if attribute_data["type"] == "enum":
                assert attribute_data["values"]

    assert set(schema["void_tags"]) <= set(schema["tags"])


def test_wordpress_block_schema_matches_existing_reference_names() -> None:
    """WordPressのブロックのスキーマが既存の参照名に一致することを確認する。"""
    standards_path = PROJECT_ROOT / "dictionaries" / "standards"
    schema = _load_project_json(standards_path / "wordpress_block_schema.json")
    lint_reference = _load_project_json(
        PROJECT_ROOT / "dictionaries" / "lint_reference.json"
    )
    known_blocks = set(lint_reference["wordpress_core_blocks"])
    known_attributes = lint_reference["wordpress_block_attributes"]
    schema_value_types = set(schema["value_types"])
    shared_attribute_names = set(schema["shared_attributes"])

    assert len(schema["blocks"]) == 23
    assert schema["blocks"]["heading"]["attributes"]["level"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 6,
        "default": 2,
    }
    assert schema["blocks"]["spacer"]["attributes"]["height"]["value_type"] == (
        "css_length"
    )
    assert schema["blocks"]["media-text"]["attributes"]["mediaWidth"][
        "maximum"
    ] == 100
    assert schema["blocks"]["separator"]["attributes"] == {
        "opacity": {"type": "string", "default": "alpha-channel"},
        "tagName": {"type": "string", "enum": ["div", "hr"], "default": "hr"},
    }

    for block_name, block_data in schema["blocks"].items():
        assert block_name in known_blocks
        schema_attribute_names = set(block_data["attributes"])
        reference_attribute_names = set(known_attributes[block_name])
        assert schema_attribute_names <= reference_attribute_names
        if block_data["include_shared_attributes"]:
            assert shared_attribute_names <= reference_attribute_names
        for attribute_data in block_data["attributes"].values():
            attribute_types = attribute_data["type"]
            if isinstance(attribute_types, str):
                attribute_types = [attribute_types]
            assert set(attribute_types) <= schema_value_types


def test_multi_lang_lint_checks_plugin_and_standards(tmp_path: Path) -> None:
    """複数の言語の文法チェックがプラグインと標準参照を検査することを確認する。"""
    load_file_path = tmp_path / "javascript.json"
    load_file_path.write_text('{"language_id": "javascript"}', encoding="utf-8")

    issues = lint_dictionary_plugin(
        load_file_path,
        PROJECT_ROOT / "dictionaries" / "standards",
    )

    assert issues == ()
