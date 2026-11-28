"""段落の構造・明示的な属性の照合と、自由な装飾の扱いを検証する。"""

from __future__ import annotations

import os
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from localization.translator import Translator
from main import MainWindow
from search.html_typo_lint import lint_html_typos


def paragraph(attributes: str, html: str) -> str:
    """テスト用のWordPress段落ブロックを組み立てる。"""
    return f"<!-- wp:paragraph {attributes} -->\n{html}\n<!-- /wp:paragraph -->"


@pytest.mark.parametrize("with_underline", [False, True])
def test_matching_font_size_is_not_a_block_error(with_underline: bool) -> None:
    """一致するの文字サイズがしないのブロックのエラーになることを確認する。"""
    inline = "<u>本文</u>" if with_underline else "本文"
    source = paragraph('{"fontSize":"medium"}', f'<p class="extra has-medium-font-size">{inline}</p>')
    messages = lint_html_typos(source)
    assert messages == []


def test_font_size_attribute_without_class_is_only_a_suspicion() -> None:
    """文字サイズの属性（クラスなし）が可能性の指摘にとどまるになることを確認する。"""
    messages = lint_html_typos(paragraph('{"fontSize":"medium"}', '<p class="custom">本文</p>'))
    finding = next(item for item in messages if item.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch")
    assert (finding.severity, finding.diagnostic_kind, finding.line_number) == (
        "warning", "attribute_html_suspect", 1
    )
    assert finding.values and finding.values["attribute_value"] == "medium"


def test_font_class_without_attribute_is_allowed() -> None:
    """HTML側にだけある文字サイズのクラスを許容する。"""
    assert not lint_html_typos(paragraph("", '<p class="custom has-medium-font-size">本文</p>'))


def test_moved_size_to_strong_keeps_plain_underline_without_warning() -> None:
    """警告を省いた場合、移動されたサイズのへのstrongタグがプレーンテキストの下線を保持することを確認する。"""
    source = paragraph("", '<p><strong style="font-size:20px"><u>本文</u></strong></p>')
    assert not lint_html_typos(source)


def test_nested_size_is_allowed() -> None:
    """段落内の部分的な文字サイズの指定を許容する。"""
    source = paragraph('{"fontSize":"medium"}', '<p class="has-medium-font-size"><strong style="font-size:20px">本文</strong></p>')
    assert not lint_html_typos(source)


def test_styled_underline_is_allowed_with_and_without_paragraph_font_size() -> None:
    """記事ごとの下線・文字色・背景色を警告しない。"""
    inline = '<u style="color:#653C20;background-color:#E9F6D2;font-size:20px">本文</u>'
    assert not lint_html_typos(paragraph("", f"<p>{inline}</p>"))
    assert not lint_html_typos(paragraph('{"fontSize":"medium"}', f'<p class="has-medium-font-size">{inline}</p>'))


def test_invalid_css_in_underline_is_reported_as_warning() -> None:
    """下線の装飾でも空の色、壊れた16進カラー、単位抜けは警告する。"""
    source = paragraph("", '<p><u style="color:;BACKGROUND-COLOR: #1234567;font-size:20">本文</u></p>')
    assert {
        (item.severity, item.message_key, item.line_number) for item in lint_html_typos(source)
    } == {
        ("warning", "css_lint.empty_value", 2),
        ("warning", "css_lint.invalid_color", 2),
        ("warning", "css_lint.missing_unit", 2),
    }


def test_unclosed_u_keeps_html_structure_diagnostic() -> None:
    """閉じられていないのuタグがHTMLの構造の診断を保持することを確認する。"""
    messages = lint_html_typos(paragraph("", "<p><u>本文</p>"))
    assert any(
        item.message_key == "html_typo_lint.inline_tag_unclosed_before_parent"
        and item.severity == "error"
        and item.diagnostic_kind == "html_syntax"
        for item in messages
    )


class _VisibleText(HTMLParser):
    """HTMLから本文と改行タグを数えるテスト用パーサー。"""
    def __init__(self) -> None:
        """本文の収集先と改行タグの件数を初期化する。"""
        super().__init__()
        self.text: list[str] = []
        self.breaks = 0

    def handle_data(self, data: str) -> None:
        """表示される本文を集める。"""
        self.text.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """開始タグのうち改行タグの件数を数える。"""
        if tag == "br":
            self.breaks += 1


def test_extension_before_after_fixture_preserves_text_and_breaks() -> None:
    """拡張前後の検証データで、本文と改行が保持されることを確認する。"""
    fixtures = Path(__file__).parent
    before = (fixtures / "paragraph_extension_before.wp_html").read_text(encoding="utf-8")
    after = (fixtures / "paragraph_extension_after.wp_html").read_text(encoding="utf-8")
    assert not lint_html_typos(before)
    assert not lint_html_typos(after)
    assert before.split("-->", 1)[0] == after.split("-->", 1)[0]
    assert '<p class="has-medium-font-size">' in before and '<p class="has-medium-font-size">' in after
    before_text, after_text = _VisibleText(), _VisibleText()
    before_text.feed(before)
    after_text.feed(after)
    assert "".join(before_text.text).split() == "".join(after_text.text).split()
    assert before_text.breaks == after_text.breaks == 5


@pytest.mark.parametrize("language", ["ja", "en"])
def test_new_diagnostics_have_translated_explanations(language: str) -> None:
    """新規の診断が翻訳済みの説明を持つことを確認する。"""
    translator = Translator(Path("resources"), language)
    source = paragraph('{"fontSize":"medium"}', '<p><u style="color:#1234567">本文</u></p>')
    items = lint_html_typos(source)
    assert {item.message_key for item in items} >= {"html_typo_lint.wordpress_block_attribute_html_mismatch", "css_lint.invalid_color"}
    for item in items:
        if item.diagnostic_kind:
            assert translator.text(f"grammar_check.kind.{item.diagnostic_kind}") != f"grammar_check.kind.{item.diagnostic_kind}"
        assert translator.text(item.message_key, **(item.values or {})) != item.message_key


def test_grammar_result_shows_diagnostic_kind(tmp_path: Path) -> None:
    """文法の結果が診断の種類を表示することを確認する。"""
    app = QApplication.instance() or QApplication(sys.argv)
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "backup.json",
    )
    source = paragraph('{"fontSize":"medium"}', '<p>本文</p>')
    finding = next(item for item in lint_html_typos(source) if item.diagnostic_kind)
    label = window._grammar_lint_message_text(finding)
    assert "[警告]" in label
    assert "fontSize" in label
    assert "medium" in label
