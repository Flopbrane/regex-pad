"""段落挿入の規則を検証する。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from editor.paragraph_insert_rules import (
    ParagraphInsertDictionaryError,
    load_paragraph_insert_rule_book,
)
from localization.translator import Translator


def test_default_dictionary_registers_context_menu_operation_keys() -> None:
    """既定の辞書がコンテキストメニューの操作のキーを登録することを確認する。"""
    load_file_path = Path("dictionaries/paragraph_insert_dict.json")
    load_data = json.loads(load_file_path.read_text(encoding="utf-8"))

    assert set(load_data["operations"]) == {
        "insert_spacer",
        "insert_html",
        "decorated_block",
    }
    for operation in load_data["operations"].values():
        assert {"search", "exclude", "replacement"} <= operation.keys()


def test_default_dictionary_is_valid_and_keeps_output_text_out_of_python() -> None:
    """既定の辞書が正しいになるとともに、出力の文字列の外のPythonを保持することを確認する。"""
    rule_book = load_paragraph_insert_rule_book()

    assert rule_book.operation("insert_spacer").replacement.startswith("<!-- wp:spacer")
    assert rule_book.operation("insert_html").replacement.startswith("<!-- wp:html")
    assert rule_book.operation("decorated_block").replacement.startswith("<!-- wp:html")
    assert rule_book.render_shortcut("inline_underline", "文章") == (
        '<u style="">文章</u>', len('<u style="">文章')
    )
    assert rule_book.render_shortcut("inline_strong", "text") == (
        "<strong>text</strong>", len("<strong>text")
    )
    literal = "{cursor} and {value}"
    assert rule_book.render_shortcut("inline_underline", literal) == (
        f'<u style="">{literal}</u>', len('<u style="">') + len(literal)
    )

    source = Path("editor/paragraph_splitter.py").read_text(encoding="utf-8")
    assert "<!-- wp:" not in source
    assert "<pre" not in source
    assert "ここでは" not in source


def test_user_dictionary_folder_without_paragraph_dictionary_uses_bundled_fallback(
    tmp_path: Path,
) -> None:
    """ユーザー辞書のフォルダー（段落の辞書なし）が同梱の代替のを使うことを確認する。"""
    rule_book = load_paragraph_insert_rule_book(tmp_path)

    assert rule_book.load_file_path == Path("dictionaries/paragraph_insert_dict.json").resolve()


def test_old_user_dictionary_and_narrow_shortcut_override(tmp_path: Path) -> None:
    """古いのユーザー辞書と幅の狭いのショートカットの上書き設定を確認する。"""
    load_data = json.loads(
        Path("dictionaries/paragraph_insert_dict.json").read_text(encoding="utf-8")
    )
    load_data.pop("shortcut_insertions")
    load_file_path = tmp_path / "paragraph_insert_dict.json"
    load_file_path.write_text(json.dumps(load_data, ensure_ascii=False), encoding="utf-8")
    assert load_paragraph_insert_rule_book(tmp_path).render_shortcut("inline_underline", "A")[0] == '<u style="">A</u>'

    load_data["shortcut_insertions"] = {"inline_underline": '<u class="custom">{selection}{cursor}</u>'}
    load_file_path.write_text(json.dumps(load_data, ensure_ascii=False), encoding="utf-8")
    book = load_paragraph_insert_rule_book(tmp_path)
    assert book.render_shortcut("inline_underline", "A")[0] == '<u class="custom">A</u>'
    assert book.render_shortcut("inline_strong", "A")[0] == "<strong>A</strong>"


def test_shortcut_template_must_keep_selection_and_cursor(tmp_path: Path) -> None:
    """ショートカットのテンプレートの必須の保持するの選択範囲とカーソルを確認する。"""
    load_data = json.loads(
        Path("dictionaries/paragraph_insert_dict.json").read_text(encoding="utf-8")
    )
    load_data["shortcut_insertions"]["inline_underline"] = "<u>{selection}</u>"
    (tmp_path / "paragraph_insert_dict.json").write_text(
        json.dumps(load_data, ensure_ascii=False), encoding="utf-8"
    )
    with pytest.raises(ParagraphInsertDictionaryError, match="inline_underline"):
        load_paragraph_insert_rule_book(tmp_path)


def test_invalid_replacement_without_cursor_is_rejected(tmp_path: Path) -> None:
    """不正なの置換（カーソルなし）が拒否されたになることを確認する。"""
    load_data = json.loads(
        Path("dictionaries/paragraph_insert_dict.json").read_text(encoding="utf-8")
    )
    load_data["operations"]["insert_spacer"]["replacement"] = "invalid"
    (tmp_path / "paragraph_insert_dict.json").write_text(
        json.dumps(load_data, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ParagraphInsertDictionaryError, match="cursor"):
        load_paragraph_insert_rule_book(tmp_path)


def test_invalid_dictionary_with_unknown_placeholder_is_rejected(tmp_path: Path) -> None:
    """不正なの辞書（未登録のプレースホルダーあり）が拒否されたになることを確認する。"""
    load_data = json.loads(
        Path("dictionaries/paragraph_insert_dict.json").read_text(encoding="utf-8")
    )
    load_data["operations"]["insert_spacer"]["replacement"] += "{heigth}"
    (tmp_path / "paragraph_insert_dict.json").write_text(
        json.dumps(load_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(ParagraphInsertDictionaryError, match="heigth"):
        load_paragraph_insert_rule_book(tmp_path)


@pytest.mark.parametrize("language", ["ja", "en"])
def test_paragraph_insertion_linter_messages_are_available(language: str) -> None:
    """段落の挿入の文法チェッカーのメッセージが利用できることを確認する。"""
    translator = Translator(Path("resources"), language)
    keys = {
        "paragraph_split.dictionary_error": {"error": "sample"},
        "paragraph_split.invalid_rule": {"operation": "sample", "error": "sample"},
        "paragraph_split.not_available": {},
        "paragraph_split.cross_block": {},
        "paragraph_split.paragraph_attributes": {},
        "paragraph_split.paragraph_structure": {},
        "paragraph_split.insert_spacer_not_available": {},
        "paragraph_split.insert_html_not_available": {},
        "paragraph_split.decorated_block_not_available": {},
    }

    for key, values in keys.items():
        assert translator.text(key, **values) != key


def test_pyinstaller_spec_collects_paragraph_insert_dictionary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PyInstallerのspecファイルのを集めるの段落挿入の辞書を確認する。"""
    monkeypatch.setenv("REGEXPAD_SKIP_WORDPRESS_RUNTIME", "1")
    spec_path = Path("regex-pad.spec")
    spec_prefix = spec_path.read_text(encoding="utf-8").split("a = Analysis", maxsplit=1)[0]
    namespace: dict[str, object] = {"SPECPATH": str(spec_path.resolve().parent)}

    exec(spec_prefix, namespace)  # noqa: S102 - Verify the project-owned spec data list.

    app_datas = namespace["app_datas"]
    assert isinstance(app_datas, list)
    assert (
        "dictionaries/paragraph_insert_dict.json",
        "dictionaries",
    ) in app_datas
