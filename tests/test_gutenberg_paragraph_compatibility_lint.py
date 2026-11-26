"""段落の静的診断と拡張機能の観察結果を区別する。"""

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
    return f"<!-- wp:paragraph {attributes} -->\n{html}\n<!-- /wp:paragraph -->"


@pytest.mark.parametrize("with_underline", [False, True])
def test_matching_font_size_is_not_a_block_error(with_underline: bool) -> None:
    inline = "<u>本文</u>" if with_underline else "本文"
    source = paragraph('{"fontSize":"medium"}', f'<p class="extra has-medium-font-size">{inline}</p>')
    messages = lint_html_typos(source)
    assert not [item for item in messages if item.severity in {"error", "warning"}]
    if with_underline:
        assert any(item.diagnostic_kind == "visual_edit_compatibility" for item in messages)


def test_font_size_attribute_without_class_is_only_a_suspicion() -> None:
    messages = lint_html_typos(paragraph('{"fontSize":"medium"}', '<p class="custom">本文</p>'))
    finding = next(item for item in messages if item.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch")
    assert (finding.severity, finding.diagnostic_kind, finding.line_number) == (
        "warning", "attribute_html_suspect", 1
    )
    assert finding.values and finding.values["attribute_value"] == "medium"


def test_font_class_without_attribute_is_only_a_suspicion() -> None:
    messages = lint_html_typos(paragraph("", '<p class="custom has-medium-font-size">本文</p>'))
    finding = next(item for item in messages if item.message_key == "html_typo_lint.paragraph_font_class_without_attribute")
    assert (finding.severity, finding.diagnostic_kind, finding.line_number) == (
        "warning", "attribute_html_suspect", 2
    )
    assert finding.values == {"block_line": "1", "class_name": "has-medium-font-size"}


def test_moved_size_to_strong_keeps_plain_underline_without_warning() -> None:
    source = paragraph("", '<p><strong style="font-size:20px"><u>本文</u></strong></p>')
    assert not lint_html_typos(source)


def test_nested_size_is_an_editing_note() -> None:
    source = paragraph('{"fontSize":"medium"}', '<p class="has-medium-font-size"><strong style="font-size:20px">本文</strong></p>')
    messages = lint_html_typos(source)
    assert [(item.severity, item.diagnostic_kind) for item in messages] == [
        ("info", "visual_edit_compatibility")
    ]


def test_u_style_extension_warning_is_independent_of_paragraph_font_size() -> None:
    for attributes, html in (
        ("", '<p><u style="color:red">本文</u></p>'),
        ('{"fontSize":"medium"}', '<p class="has-medium-font-size"><u style="color:red">本文</u></p>'),
    ):
        messages = lint_html_typos(paragraph(attributes, html))
        finding = next(item for item in messages if item.message_key == "html_typo_lint.paragraph_u_style_extension_warning")
        assert (finding.severity, finding.diagnostic_kind, finding.line_number) == (
            "warning", "extension_unknown_inline_format", 2
        )
        assert finding.values == {"block_line": "1", "style": "color:red"}


def test_u_style_in_html_block_is_not_paragraph_warning() -> None:
    messages = lint_html_typos('<!-- wp:html --><u style="color:red">本文</u><!-- /wp:html -->')
    assert not any(item.message_key == "html_typo_lint.paragraph_u_style_extension_warning" for item in messages)


def test_unclosed_u_keeps_html_structure_diagnostic() -> None:
    messages = lint_html_typos(paragraph("", "<p><u>本文</p>"))
    assert any(
        item.message_key == "html_typo_lint.inline_tag_unclosed_before_parent"
        and item.severity == "error"
        and item.diagnostic_kind == "html_syntax"
        for item in messages
    )


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.breaks = 0

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.breaks += 1


def test_extension_before_after_fixture_preserves_text_and_breaks() -> None:
    fixtures = Path(__file__).parent
    before = (fixtures / "paragraph_extension_before.wp_html").read_text(encoding="utf-8")
    after = (fixtures / "paragraph_extension_after.wp_html").read_text(encoding="utf-8")
    before_messages = lint_html_typos(before)
    assert len([item for item in before_messages if item.message_key == "html_typo_lint.paragraph_u_style_extension_warning"]) == 2
    assert not [item for item in lint_html_typos(after) if item.message_key == "html_typo_lint.paragraph_u_style_extension_warning"]
    assert before.split("-->", 1)[0] == after.split("-->", 1)[0]
    assert '<p class="has-medium-font-size">' in before and '<p class="has-medium-font-size">' in after
    before_text, after_text = _VisibleText(), _VisibleText()
    before_text.feed(before)
    after_text.feed(after)
    assert "".join(before_text.text).split() == "".join(after_text.text).split()
    assert before_text.breaks == after_text.breaks == 5


@pytest.mark.parametrize("language", ["ja", "en"])
def test_new_diagnostics_have_translated_explanations(language: str) -> None:
    translator = Translator(Path("resources"), language)
    source = paragraph('{"fontSize":"medium"}', '<p class="has-medium-font-size"><u style="color:red">本文</u></p>')
    for item in lint_html_typos(source):
        if item.diagnostic_kind:
            assert translator.text(f"grammar_check.kind.{item.diagnostic_kind}") != f"grammar_check.kind.{item.diagnostic_kind}"
            assert translator.text(item.message_key, **(item.values or {})) != item.message_key


def test_grammar_result_shows_diagnostic_kind(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "backup.json",
    )
    source = paragraph("", '<p><u style="color:red">本文</u></p>')
    finding = next(item for item in lint_html_typos(source) if item.diagnostic_kind)
    label = window._grammar_lint_message_text(finding)
    assert "[警告]" in label
    assert "[VS Code拡張機能の互換性]" in label
    assert "color:red" in label
