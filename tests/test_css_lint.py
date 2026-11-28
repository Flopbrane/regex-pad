"""CSSの文法チェックを検証する。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from main import MainWindow
from search.css_lint import lint_inline_style, lint_stylesheet


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def _message_keys(css_text: str) -> set[str]:
    """CSS診断から比較用のメッセージキーだけを取り出す。"""
    return {issue.message_key for issue in lint_inline_style(css_text)}


def test_inline_style_accepts_common_wordpress_article_css() -> None:
    """インラインのCSSが共通のWordPressの原稿のCSSを受け入れることを確認する。"""
    issues = lint_inline_style(
        "display:inline-block; border:1px solid #999; padding:16px; "
        "margin:2em auto; color:var(--wp--preset--color--contrast)"
    )

    assert issues == []


def test_inline_style_detects_property_and_unit_typos() -> None:
    """インラインのCSSがプロパティと単位の表記ミスを検出することを確認する。"""
    issues = lint_inline_style("text-aling:center; margin:2en 0")

    assert [(issue.message_key, issue.values) for issue in issues] == [
        (
            "css_lint.known_property_typo",
            {"property": "text-aling", "suggestion": "text-align"},
        ),
        ("css_lint.known_unit_typo", {"unit": "en", "suggestion": "em"}),
    ]


def test_inline_style_detects_missing_colon_and_semicolon() -> None:
    """インラインのCSSが不足したコロンとセミコロンを検出することを確認する。"""
    assert "css_lint.missing_colon" in _message_keys("color red")
    assert "css_lint.missing_semicolon" in _message_keys(
        "color:red padding:10px"
    )


def test_inline_style_detects_unclosed_quote_and_parenthesis() -> None:
    """インラインのCSSが閉じられていないの引用符と括弧を検出することを確認する。"""
    message_keys = _message_keys('background-image:url("sample.png); color:red')

    assert "css_lint.unclosed_quote" in message_keys
    assert "css_lint.missing_closing_parenthesis" in message_keys


def test_inline_style_detects_invalid_keyword_range_and_hex_notation() -> None:
    """色の判定を省いた場合、インラインのCSSが不正なキーワードと範囲を検出することを確認する。"""
    message_keys = _message_keys(
        "display:blick; color:#zzzzzz; opacity:1.5; z-index:front"
    )

    assert "css_lint.invalid_keyword" in message_keys
    assert "css_lint.invalid_color" in message_keys
    assert "css_lint.value_out_of_range" in message_keys
    assert "css_lint.invalid_integer" in message_keys


def test_stylesheet_warns_about_empty_colors_bad_hex_and_unitless_font_size() -> None:
    """色の空欄・不正な16進カラー・文字サイズの単位抜けを警告する。"""
    issues = lint_stylesheet(
        "p {\n"
        "  color: ;\n"
        "  Background-color: ;\n"
        "  font-size: 20;\n"
        "  background: url(icons.svg#section-name), linear-gradient(#1234, #1234567);\n"
        "}"
    )
    assert [(issue.severity, issue.message_key, issue.line_number) for issue in issues] == [
        ("warning", "css_lint.empty_value", 2),
        ("warning", "css_lint.empty_value", 3),
        ("warning", "css_lint.missing_unit", 4),
        ("warning", "css_lint.invalid_color", 5),
    ]
    assert issues[-1].values == {"property": "background", "value": "#1234567"}


def test_inline_style_keeps_valid_color_formats_and_url_fragments() -> None:
    """標準の16進カラー形式、色名、変数、URLのフラグメントを許容する。"""
    assert not lint_inline_style(
        'color:var(--article-color);background-color:rebeccapurple;'
        'background:url("icons.svg#layer-name"),linear-gradient(#abc,#aabb,#AABBCC,#aabbccDD);'
        'font-size:0'
    )


@pytest.mark.parametrize(
    "style_text",
    [
        "{cursor}",
        "color:{cursor}",
        "background-color: {cursor}; padding:10px",
    ],
)
def test_inline_style_accepts_editable_cursor_placeholder(style_text: str) -> None:
    """インラインのCSSが編集可能なカーソルのプレースホルダーを受け入れることを確認する。"""
    assert lint_inline_style(style_text) == []


def test_inline_style_keeps_real_syntax_checks_around_cursor_placeholder() -> None:
    """カーソル用のプレースホルダーがあっても、周囲のCSS構文を検査することを確認する。"""
    assert "css_lint.missing_colon" in _message_keys("broken {cursor}")


def test_inline_style_accepts_custom_properties_and_final_declaration_without_semicolon() -> None:
    """セミコロンを省いた場合、インラインのCSSがカスタムのプロパティと最終のCSS宣言を受け入れることを確認する。"""
    assert lint_inline_style("--note-color:#abcdef; color:var(--note-color)") == []


def test_inline_style_accepts_css_comment_and_reports_unclosed_comment_line() -> None:
    """CSSコメントを受け付け、閉じられていないコメントは該当行を報告することを確認する。"""
    assert lint_inline_style("color:red; /* note */ padding:10px") == []

    issues = lint_inline_style("color:red;\n/* open", start_line_number=10)

    assert any(
        issue.message_key == "css_lint.unclosed_comment"
        and issue.line_number == 11
        for issue in issues
    )


def test_inline_style_reports_full_width_symbol_and_missing_unit() -> None:
    """インラインのCSSが全角の記号と不足した単位を報告することを確認する。"""
    issues = lint_inline_style("color：red; width:10")
    message_keys = {issue.message_key for issue in issues}

    assert "css_lint.full_width_symbol" in message_keys
    assert "css_lint.missing_unit" in message_keys


def test_inline_style_reports_duplicate_property() -> None:
    """インラインのCSSが重複したプロパティを報告することを確認する。"""
    issues = lint_inline_style("color:red; color:blue")

    duplicate = next(
        issue for issue in issues if issue.message_key == "css_lint.duplicate_property"
    )
    assert duplicate.severity == "info"
    assert duplicate.values == {"property": "color", "previous_line": "1"}


def test_stylesheet_checks_nested_media_declaration_blocks() -> None:
    """スタイルシートが入れ子のメディアのCSS宣言のブロックを検査することを確認する。"""
    issues = lint_stylesheet(
        "@media (min-width: 40em) {\n"
        "  .note {\n"
        "    display: blick;\n"
        "  }\n"
        "}"
    )

    invalid_keyword = next(
        issue for issue in issues if issue.message_key == "css_lint.invalid_keyword"
    )
    assert invalid_keyword.line_number == 3


def test_stylesheet_detects_braces_comments_and_unknown_at_rule() -> None:
    """スタイルシート内の波括弧、コメント、未登録のアットルールを検出することを確認する。"""
    message_keys = {
        issue.message_key
        for issue in lint_stylesheet("@medai screen { .note { color:red; } } } /* open")
    }

    assert "css_lint.unknown_at_rule" in message_keys
    assert "css_lint.unexpected_closing_brace" in message_keys
    assert "css_lint.unclosed_comment" in message_keys


def test_stylesheet_reports_missing_closing_brace() -> None:
    """スタイルシートが不足した終了の波括弧を報告することを確認する。"""
    issues = lint_stylesheet(".note {\n  color:red;")

    assert any(
        issue.message_key == "css_lint.missing_closing_brace"
        and issue.line_number == 1
        for issue in issues
    )


def test_stylesheet_reports_missing_opening_brace_and_unclosed_quote() -> None:
    """スタイルシートが不足した開始の波括弧と閉じられていないの引用符を報告することを確認する。"""
    missing_brace_keys = {
        issue.message_key for issue in lint_stylesheet(".note color:red;")
    }
    unclosed_quote_keys = {
        issue.message_key
        for issue in lint_stylesheet('.note { content:"open; color:red; }')
    }

    assert "css_lint.missing_opening_brace" in missing_brace_keys
    assert "css_lint.unclosed_quote" in unclosed_quote_keys


def test_main_window_uses_stylesheet_lint_for_css_file(app: QApplication) -> None:
    """メインウインドウがスタイルシートの文法チェックの用のCSSのファイルを使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.current_save_file_path = Path("sample.css")

    issues = window._lint_document(".note {\n  display:blick;\n}")

    invalid_keyword = next(
        issue for issue in issues if issue.message_key == "css_lint.invalid_keyword"
    )
    assert invalid_keyword.line_number == 2
    assert "display" in window._html_typo_lint_message_text(invalid_keyword)
