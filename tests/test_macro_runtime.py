"""実際のマクロ処理の組み合わせを実行し、変更が確定される境界を検証する。"""

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from macro.json_bridge import MacroJsonBridge
from macro.json_data_model import MacroJsonData, MacroJsonStepData
from macro.macro_manager import MacroManager, MacroValidationError
from macro.macro_model import MacroCompiler
from macro.macro_parser import MacroJsonParseError, MacroParser
from macro.macro_runner import MacroRunner
from search.search_engine import SearchEngine, SearchOptions


def step(
    name: str = "step", search: str = "a", replacement: str | None = "b", **values: Any
):
    """テストで使うマクロの手順を組み立てる。"""
    fields: dict[str, Any] = {
        "step_name": name,
        "enabled": True,
        "regular_expression": False,
        "unicode_normalize": False,
        "unicode_normalize_form": None,
        "append_dot_to_circled_number": False,
        "search_text": search,
        "exclusion_text": None,
        "replacement_text": replacement,
    }
    fields.update(values)
    return MacroJsonStepData(**fields)


def model(*steps):
    """テストで使うマクロ定義を組み立てる。"""
    return MacroJsonData(1, "test macro", "description", steps or (step(),))


def test_steps_are_sequential_and_compilation_is_detached_and_frozen():
    """手順が順次処理するとコンパイル結果の独立したと固定されたであることを確認する。"""
    original = model(step("first", "a", "b"), step("second", "b", "c"))
    prepared = MacroCompiler.prepare(original)
    original.steps[0].replacement_text = "changed after preparation"
    assert prepared.definition is not None
    with pytest.raises(FrozenInstanceError):
        prepared.definition.steps[0].replacement_text = "mutate"  # pyright: ignore[reportAttributeAccessIssue]
    result = MacroRunner().run(prepared.definition, "a b")
    assert result.succeeded and result.text == "c c"
    assert [report.replacements for report in result.steps] == [1, 2]


def test_disabled_invalid_step_is_skipped_and_reports_zero():
    """無効にした不正な手順を飛ばし、処理件数がゼロになることを確認する。"""
    result = MacroManager().execute_macro(
        model(
            step("disabled", "[", None, enabled=False, regular_expression=True),
            step("active", "a", "b"),
        ),
        "a",
    )
    assert result.succeeded and result.text == "b"
    assert not result.steps[0].enabled and result.steps[0].replacements == 0


def test_exclusion_counts_and_capture_references_are_shared_with_search_engine():
    """除外がとの取り込みの参照資料のの共有の（検索のエンジンあり）を数えることを確認する。"""
    result = MacroManager().execute_macro(
        model(
            step(
                search=r"item-(\d+)",
                replacement=r"$1\n",
                regular_expression=True,
                exclusion_text="item-01",
            )
        ),
        "item-01 item-20",
    )
    assert result.succeeded and result.text == "item-01 20\n"
    assert (
        result.steps[0].matches,
        result.steps[0].excluded,
        result.steps[0].replacements,
    ) == (2, 1, 1)


def test_unicode_normalization_and_circled_number_dot():
    """Unicodeの正規化と丸数字のピリオドを確認する。"""
    result = MacroManager().execute_macro(
        model(
            step(
                search="[Ａ-Ｚ①]",
                replacement=None,
                regular_expression=True,
                unicode_normalize=True,
                unicode_normalize_form="NFKC",
                append_dot_to_circled_number=True,
            )
        ),
        "Ａ①ｱ",
    )
    assert result.succeeded and result.text == "A1.ｱ"


@pytest.mark.parametrize("replacement", [r"\2", r"${missing}", r"\q"])
def test_bad_replacement_is_rejected_even_without_matches(replacement):
    """不正な置換が拒否されたの場合でも（一致箇所なし）になることを確認する。"""
    result = MacroManager().execute_macro(
        model(
            step(
                search="(a)",
                replacement=replacement,
                regular_expression=True,
            )
        ),
        "no matching characters",
    )
    assert not result.succeeded
    assert result.text == result.original_text
    assert any(d.code == "invalid_replacement" for d in result.validation.errors)


@pytest.mark.parametrize("pattern", ["^", "a*", "(?=a)", r"\b"])
def test_zero_width_is_rejected_statically_or_on_the_actual_step_input(pattern):
    """幅ゼロの一致が事前検証または手順への実際の入力で拒否されることを確認する。"""
    result = MacroManager().execute_macro(
        model(
            step(
                search=pattern,
                replacement="x",
                regular_expression=True,
            )
        ),
        "a",
    )
    assert not result.succeeded and result.text == "a"
    assert any(d.code == "zero_width_search" for d in result.validation.errors)


def test_failure_after_first_step_returns_original_text_without_partial_output():
    """一部の出力を省いた場合、失敗後の最初の手順が元の文字列を返すことを確認する。"""
    result = MacroManager().execute_macro(
        model(
            step("first", "a", "b"),
            step("later", "(?=b)", "x", regular_expression=True),
        ),
        "a",
    )
    assert not result.succeeded
    assert result.original_text == result.text == "a"
    assert result.steps[0].replacements == 1
    assert result.validation.errors[0].step_index == 1


def test_no_matches_and_warning_only_macro_do_not_change_text():
    """一致がない場合と警告だけのマクロ実行で本文が変わらないことを確認する。"""
    preview = MacroManager().preview_macro(model(step(search="missing")), "a")
    assert preview.result.succeeded and not preview.can_apply
    assert preview.result.validation.information[0].code == "no_matches"
    preview = MacroManager().preview_macro(model(step(enabled=False)), "a")
    assert preview.result.succeeded and preview.result.validation.warnings
    assert not preview.can_apply


def test_manager_load_validate_save_and_source_preservation(tmp_path):
    """管理処理の読み込みの検証の保存と原文の保持を確認する。"""
    manager = MacroManager(tmp_path)
    source = model(step(search=" \\a\nＡ ", replacement=""))
    destination = manager.save_macro(source, "macro.json")
    assert destination == tmp_path / "macro.json"
    prepared = manager.load_macro("macro.json")
    assert prepared.model == source
    assert manager.validate_macro(source).is_valid
    original_bytes = destination.read_bytes()
    source.steps[0].search_text = ""
    with pytest.raises(MacroValidationError):
        manager.save_macro(source, "macro.json")
    assert destination.read_bytes() == original_bytes


def test_parser_supports_text_input_and_rejects_duplicate_keys():
    """パーサーが文字列の入力欄に対応するとともに、重複キーを拒否することを確認する。"""
    original = model()
    assert MacroParser.parse(json.dumps(MacroJsonBridge.to_dict(original))) == original
    with pytest.raises(MacroJsonParseError, match="duplicate JSON key"):
        MacroParser.parse('{"a": 1, "a": 2}')


@pytest.mark.parametrize("exclusion", ["", "[a]"])
def test_literal_backslashes_do_not_become_regex_replacement_references(exclusion):
    """リテラルのバックスラッシュが置換時のグループ参照に変わらないことを確認する。"""
    replacement = r"C:\new\g<1>\n"
    options = SearchOptions(exclusion_text=exclusion)
    engine = SearchEngine()
    result = engine.replace_all("[a] a", "a", replacement, options)
    expected = (
        "[a] " + replacement if exclusion else "[" + replacement + "] " + replacement
    )
    assert result.text == expected
    assert engine.preview_replacement("a", "a", replacement).text == replacement


def test_runtime_diagnostics_have_complete_translations():
    """実行時の診断で使う翻訳キーに不足がないことを確認する。"""
    from localization.translator import Translator

    keys = [
        "macro.validation.zero_width_search",
        "macro.validation.invalid_replacement",
        "macro.runtime.zero_width_search",
        "macro.runtime.step_failed",
        "macro.runtime.no_matches",
    ]
    for language in ("ja", "en"):
        translator = Translator(Path("resources"), language)
        for key in keys:
            assert translator.text(key, error="detail") != key
