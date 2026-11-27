"""アプリの翻訳を検証する。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from localization.translator import Translator


def load_texts(language_code: str) -> dict[str, Any]:
    """指定された言語の翻訳データをテスト用に読み込む。"""
    return json.loads(
        Path(f"resources/app_text_{language_code}.json").read_text(encoding="utf-8")
    )


def test_app_translation_files_have_matching_keys() -> None:
    """アプリの翻訳のファイルが一致するキーを持つことを確認する。"""
    english_texts = load_texts("en")
    japanese_texts = load_texts("ja")

    assert set(japanese_texts) == set(english_texts)


def test_translator_formats_values() -> None:
    """翻訳処理が値の表記を整えることを確認する。"""
    translator = Translator(Path("resources"), "en")

    assert translator.text("status.position", line=2, column=3, characters=10) == (
        "Line 2, Column 3 | Characters 10"
    )


def test_translator_keeps_literal_braces_in_lint_messages() -> None:
    """翻訳処理がリテラルの波括弧内の文法チェックのメッセージを保持することを確認する。"""
    translator = Translator(Path("resources"), "en")

    assert translator.text(
        "html_typo_lint.invalid_wordpress_block_attributes",
        block="paragraph",
    ) == (
        "`wp:paragraph` has `{}` parameters that are not valid JSON. "
        "Check double quotes and commas."
    )


def test_japanese_translation_uses_readable_labels() -> None:
    """日本語の翻訳が読みやすいのラベルを使うことを確認する。"""
    translator = Translator(Path("resources"), "ja")

    assert translator.text("menu.search") == "検索(&S)"
    assert translator.text("find.regex") == "正規表現として検索する"
    assert translator.text("action.open_with_encoding") == "文字コードを指定して開く(&N)"
    assert translator.text("action.reload") == "読み直し(&R)"
