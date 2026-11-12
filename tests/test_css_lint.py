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
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def _message_keys(css_text: str) -> set[str]:
    return {issue.message_key for issue in lint_inline_style(css_text)}


def test_inline_style_accepts_common_wordpress_article_css() -> None:
    issues = lint_inline_style(
        "display:inline-block; border:1px solid #999; padding:16px; "
        "margin:2em auto; color:var(--wp--preset--color--contrast)"
    )

    assert issues == []


def test_inline_style_detects_property_and_unit_typos() -> None:
    issues = lint_inline_style("text-aling:center; margin:2en 0")

    assert [(issue.message_key, issue.values) for issue in issues] == [
        (
            "css_lint.known_property_typo",
            {"property": "text-aling", "suggestion": "text-align"},
        ),
        ("css_lint.known_unit_typo", {"unit": "en", "suggestion": "em"}),
    ]


def test_inline_style_detects_missing_colon_and_semicolon() -> None:
    assert "css_lint.missing_colon" in _message_keys("color red")
    assert "css_lint.missing_semicolon" in _message_keys(
        "color:red padding:10px"
    )


def test_inline_style_detects_unclosed_quote_and_parenthesis() -> None:
    message_keys = _message_keys('background-image:url("sample.png); color:red')

    assert "css_lint.unclosed_quote" in message_keys
    assert "css_lint.missing_closing_parenthesis" in message_keys


def test_inline_style_detects_invalid_keyword_and_range_without_color_judgment() -> None:
    message_keys = _message_keys(
        "display:blick; color:#zzzzzz; opacity:1.5; z-index:front"
    )

    assert "css_lint.invalid_keyword" in message_keys
    assert "css_lint.invalid_color" not in message_keys
    assert "css_lint.value_out_of_range" in message_keys
    assert "css_lint.invalid_integer" in message_keys


@pytest.mark.parametrize(
    "style_text",
    [
        "{cursor}",
        "color:{cursor}",
        "background-color: {cursor}; padding:10px",
    ],
)
def test_inline_style_accepts_editable_cursor_placeholder(style_text: str) -> None:
    assert lint_inline_style(style_text) == []


def test_inline_style_keeps_real_syntax_checks_around_cursor_placeholder() -> None:
    assert "css_lint.missing_colon" in _message_keys("broken {cursor}")


def test_inline_style_accepts_custom_properties_and_final_declaration_without_semicolon() -> None:
    assert lint_inline_style("--note-color:#abcdef; color:var(--note-color)") == []


def test_inline_style_accepts_css_comment_and_reports_unclosed_comment_line() -> None:
    assert lint_inline_style("color:red; /* note */ padding:10px") == []

    issues = lint_inline_style("color:red;\n/* open", start_line_number=10)

    assert any(
        issue.message_key == "css_lint.unclosed_comment"
        and issue.line_number == 11
        for issue in issues
    )


def test_inline_style_reports_full_width_symbol_and_missing_unit() -> None:
    issues = lint_inline_style("color：red; width:10")
    message_keys = {issue.message_key for issue in issues}

    assert "css_lint.full_width_symbol" in message_keys
    assert "css_lint.missing_unit" in message_keys


def test_inline_style_reports_duplicate_property() -> None:
    issues = lint_inline_style("color:red; color:blue")

    duplicate = next(
        issue for issue in issues if issue.message_key == "css_lint.duplicate_property"
    )
    assert duplicate.severity == "info"
    assert duplicate.values == {"property": "color", "previous_line": "1"}


def test_stylesheet_checks_nested_media_declaration_blocks() -> None:
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
    message_keys = {
        issue.message_key
        for issue in lint_stylesheet("@medai screen { .note { color:red; } } } /* open")
    }

    assert "css_lint.unknown_at_rule" in message_keys
    assert "css_lint.unexpected_closing_brace" in message_keys
    assert "css_lint.unclosed_comment" in message_keys


def test_stylesheet_reports_missing_closing_brace() -> None:
    issues = lint_stylesheet(".note {\n  color:red;")

    assert any(
        issue.message_key == "css_lint.missing_closing_brace"
        and issue.line_number == 1
        for issue in issues
    )


def test_stylesheet_reports_missing_opening_brace_and_unclosed_quote() -> None:
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
    _ = app
    window = MainWindow()
    window.current_save_file_path = Path("sample.css")

    issues = window._lint_document(".note {\n  display:blick;\n}")

    invalid_keyword = next(
        issue for issue in issues if issue.message_key == "css_lint.invalid_keyword"
    )
    assert invalid_keyword.line_number == 2
    assert "display" in window._html_typo_lint_message_text(invalid_keyword)
