"""Markdownの見出し番号による連番付けとプリセットの保存を検証する。"""

from macro.editor_bridge import MacroEditorBridge
from macro.editor_data_model import MacroEditorDocumentData, MacroEditorStepData
from macro.json_bridge import MacroJsonBridge
from macro.macro_manager import MacroManager
from macro.markdown_heading_numbers import number_items_under_headings


def test_heading_switches_parent_and_preserves_unrelated_lines() -> None:
    """見出しの切り替えるの親要素とが無関係な行を維持することを確認する。"""
    source = (
        "1. before\n"
        "## 3. Plans\n"
        "1. first\n"
        "2. second\n"
        "```text\n1. example\n```\n"
        "## 4. Next\n"
        "1. third\n"
        "## Other heading\n"
        "2. ordinary list\n"
    )
    expected = (
        "1. before\n"
        "## 3. Plans\n"
        "## 3-1. first\n"
        "## 3-2. second\n"
        "```text\n1. example\n```\n"
        "## 4. Next\n"
        "## 4-1. third\n"
        "## Other heading\n"
        "2. ordinary list\n"
    )
    assert number_items_under_headings(source) == (expected, 3)


def test_heading_level_and_line_endings_are_preserved() -> None:
    """見出しレベルと行の改行形式が保持されたであることを確認する。"""
    source = "# 12. Chapter\r\n9. Child\r\n### 13. Next\r\n1. More"
    expected = "# 12. Chapter\r\n# 12-9. Child\r\n### 13. Next\r\n### 13-1. More"
    assert number_items_under_headings(source) == (expected, 2)


def test_existing_child_heading_keeps_its_parent_number() -> None:
    """既存の子要素の見出しがその親要素の番号を保持することを確認する。"""
    source = "## 3. Chapter\n## 3-1. Existing\n2. Remaining\n"
    expected = "## 3. Chapter\n## 3-1. Existing\n## 3-2. Remaining\n"
    assert number_items_under_headings(source) == (expected, 1)
    assert number_items_under_headings(expected) == (expected, 0)


def test_special_step_survives_json_roundtrip_and_runs_after_prior_step() -> None:
    """特殊な手順がJSONの往復変換が起きても動作するとともに、直前の手順後、実行することを確認する。"""
    document = MacroEditorDocumentData(
        format_version=3,
        macro_name="Markdown numbering",
        steps=[
            MacroEditorStepData(
                step_name="chapter", search_text="CHAPTER", replacement_text="## 3. Plans",
            ),
            MacroEditorStepData(step_name="items", operation="numbered_heading"),
        ],
    )
    model = MacroEditorBridge.to_json_model(document)
    restored = MacroJsonBridge.from_dict(MacroJsonBridge.to_dict(model))
    assert MacroEditorBridge.from_json_model(restored) == document
    result = MacroManager().execute_macro(restored, "CHAPTER\n1. first\n2. second")
    assert result.succeeded
    assert result.text == "## 3. Plans\n## 3-1. first\n## 3-2. second"
    assert result.steps[1].replacements == 2
