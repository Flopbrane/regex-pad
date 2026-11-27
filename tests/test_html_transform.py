"""HTML変換を検証する。"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QMenu

from main import MainWindow
from search.search_engine import SearchOptions


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def select_text(window: MainWindow, start: int, end: int) -> None:
    """テスト対象の文字列をエディターで選択する。"""
    cursor = window.editor.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)


def test_html_escape_selected_text_preserves_quotes_and_japanese(
    app: QApplication,
) -> None:
    """HTMLのエスケープの選択文字列が引用符と日本語を維持することを確認する。"""
    _ = app
    window = MainWindow()
    source_text = '前 <h1 class="title">タイトル & 本文</h1> 後'
    window.editor.setPlainText(source_text)
    select_text(window, 2, len(source_text) - 2)

    window.escape_selected_html()

    assert window.editor.toPlainText() == (
        '前 &lt;h1 class="title"&gt;タイトル &amp; 本文&lt;/h1&gt; 後'
    )


def test_html_unescape_selected_text(app: QApplication) -> None:
    """HTMLのエスケープ解除の選択文字列を確認する。"""
    _ = app
    window = MainWindow()
    source_text = "前 &lt;h1&gt;タイトル&lt;/h1&gt; 後"
    window.editor.setPlainText(source_text)
    select_text(window, 2, len(source_text) - 2)

    window.unescape_selected_html()

    assert window.editor.toPlainText() == "前 <h1>タイトル</h1> 後"


def test_html_escape_changes_only_selection_and_can_be_undone(
    app: QApplication,
) -> None:
    """選択範囲だけがHTMLエスケープされ、Undoで復元できることを確認する。"""
    _ = app
    window = MainWindow()
    source_text = "keep <p>本文</p> keep"
    window.editor.setPlainText(source_text)
    select_text(window, len("keep "), len("keep <p>本文</p>"))

    window.escape_selected_html()

    assert window.editor.toPlainText() == "keep &lt;p&gt;本文&lt;/p&gt; keep"

    window.undo_action.trigger()

    assert window.editor.toPlainText() == source_text


def test_wordpress_code_block_escapes_multiline_indented_html(
    app: QApplication,
) -> None:
    """WordPressのコードブロックが複数行のインデント付きのHTMLをエスケープすることを確認する。"""
    _ = app
    window = MainWindow()
    source_text = "before\n  <h2>タイトル</h2>\n  <p>本文です。</p>\nafter"
    selected_text = "  <h2>タイトル</h2>\n  <p>本文です。</p>"
    window.editor.setPlainText(source_text)
    start = len("before\n")
    select_text(window, start, start + len(selected_text))

    window.wrap_selected_as_wordpress_code_block()

    assert window.editor.toPlainText() == (
        "before\n"
        "<!-- wp:html -->\n"
        "<pre\n"
        '    class="wp-block-code"\n'
        '    style="display: inline-block; border: 1px solid #999; '
        "padding: 16px; border-radius: 8px; background-color: #f9f9f9;\"\n"
        "><code>"
        "  &lt;h2&gt;タイトル&lt;/h2&gt;\n"
        "  &lt;p&gt;本文です。&lt;/p&gt;"
        "</code></pre>\n"
        "<!-- /wp:html -->"
        "\nafter"
    )


def test_wordpress_complex_blocks_converts_selected_markdown_table(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WordPressの複雑ながに変換するの選択中のMarkdownの表を拒否することを確認する。"""
    _ = app
    window = MainWindow()
    source_text = "before\n| Purpose | AI |\n|---|---|\n| B-roll | Runway |\nafter"
    selected_text = "| Purpose | AI |\n|---|---|\n| B-roll | Runway |"
    window.editor.setPlainText(source_text)
    start = len("before\n")
    select_text(window, start, start + len(selected_text))

    def fake_convert(load_data: str) -> str:
        """Markdown変換の結果や失敗をテスト用に再現する。"""
        assert load_data == selected_text
        return "<!-- wp:table -->\n<table></table>\n<!-- /wp:table -->"

    monkeypatch.setattr(
        "main.convert_complex_markdown_blocks_to_wordpress_html",
        fake_convert,
    )

    window.convert_selected_markdown_blocks_to_wordpress_blocks()

    assert window.editor.toPlainText() == (
        "before\n<!-- wp:table -->\n<table></table>\n<!-- /wp:table -->\nafter"
    )


def test_wordpress_table_transform_converts_selected_markdown_table(
    app: QApplication,
) -> None:
    """選択したMarkdownの表がWordPressのテーブルブロックに変換されることを確認する。"""
    _ = app
    window = MainWindow()
    source_text = "before\n| Purpose | AI |\n|---|---|\n| B-roll | Runway |\nafter"
    selected_text = "| Purpose | AI |\n|---|---|\n| B-roll | Runway |"
    window.editor.setPlainText(source_text)
    start = len("before\n")
    select_text(window, start, start + len(selected_text))

    window.convert_selected_markdown_tables_to_wordpress_tables()

    editor_text = window.editor.toPlainText()
    assert "<!-- wp:table -->" in editor_text
    assert "<th>Purpose</th><th>AI</th>" in editor_text
    assert "<td>B-roll</td><td>Runway</td>" in editor_text


def test_wordpress_table_transform_replaces_whole_paragraph_block(
    app: QApplication,
) -> None:
    """WordPressの表の変換が段落ブロック全体を置き換えることを確認する。"""
    _ = app
    window = MainWindow()
    source_text = (
        "before\n"
        "<!-- wp:paragraph -->\n"
        "<p>| Purpose | AI |\n|---|---|\n| B-roll | Runway |</p>\n"
        "<!-- /wp:paragraph -->\n"
        "after"
    )
    selected_text = "| Purpose | AI |\n|---|---|\n| B-roll | Runway |"
    window.editor.setPlainText(source_text)
    start = source_text.index(selected_text)
    select_text(window, start, start + len(selected_text))

    window.convert_selected_markdown_tables_to_wordpress_tables()

    editor_text = window.editor.toPlainText()
    assert "<!-- wp:paragraph -->" not in editor_text
    assert "<!-- wp:table -->" in editor_text
    assert "<td>B-roll</td><td>Runway</td>" in editor_text


def test_wordpress_table_transform_rejects_partial_paragraph_selection(
    app: QApplication,
) -> None:
    """WordPressの表の変換が一部の段落の選択範囲を拒否することを確認する。"""
    _ = app
    window = MainWindow()
    source_text = (
        "<!-- wp:paragraph -->\n"
        "<p>Intro\n| Purpose | AI |\n|---|---|\n| B-roll | Runway |</p>\n"
        "<!-- /wp:paragraph -->"
    )
    selected_text = "| Purpose | AI |\n|---|---|\n| B-roll | Runway |"
    window.editor.setPlainText(source_text)
    start = source_text.index(selected_text)
    select_text(window, start, start + len(selected_text))

    window.convert_selected_markdown_tables_to_wordpress_tables()

    assert window.editor.toPlainText() == source_text
    assert "段落" in window.statusBar().currentMessage()


def test_wordpress_complex_blocks_converts_selected_markdown_list(
    app: QApplication,
) -> None:
    """WordPressの複雑ながに変換するの選択中のMarkdownのリストを拒否することを確認する。"""
    _ = app
    window = MainWindow()
    source_text = "before\n- Runway\n- Kling\nafter"
    selected_text = "- Runway\n- Kling"
    window.editor.setPlainText(source_text)
    start = len("before\n")
    select_text(window, start, start + len(selected_text))

    window.convert_selected_markdown_blocks_to_wordpress_blocks()

    assert "<!-- wp:list -->" in window.editor.toPlainText()
    assert "<li>Runway</li>" in window.editor.toPlainText()
    assert "<li>Kling</li>" in window.editor.toPlainText()


def test_wordpress_list_transform_converts_selected_markdown_list(
    app: QApplication,
) -> None:
    """WordPressのリストの変換が選択中のMarkdownのリストに変換することを確認する。"""
    _ = app
    window = MainWindow()
    source_text = "before\n1. Runway\n2. Kling\nafter"
    selected_text = "1. Runway\n2. Kling"
    window.editor.setPlainText(source_text)
    start = len("before\n")
    select_text(window, start, start + len(selected_text))

    window.convert_selected_markdown_lists_to_wordpress_lists()

    editor_text = window.editor.toPlainText()
    assert '<!-- wp:list {"ordered":true} -->' in editor_text
    assert "<li>Runway</li>" in editor_text
    assert "<li>Kling</li>" in editor_text


def test_wordpress_list_frame_transform_uses_current_frame_settings(
    app: QApplication,
) -> None:
    """WordPressのリストの枠の変換が現在の枠の設定を使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.frame_alignment = "right"
    window.frame_outer_spacing = "2em 0 3em 0"
    window.frame_background_color = "#FFFBDE"
    window.frame_text_color = "#222222"
    source_text = "before\n- **Runway**\n- Kling\nafter"
    selected_text = "- **Runway**\n- Kling"
    window.editor.setPlainText(source_text)
    start = len("before\n")
    select_text(window, start, start + len(selected_text))

    window.wordpress_list_frame_transform_action.trigger()

    editor_text = window.editor.toPlainText()
    assert editor_text.count("<!-- wp:html -->") == 1
    assert "wp:list" not in editor_text
    assert "<ul" not in editor_text
    assert "<li" not in editor_text
    assert "<strong>Runway</strong>" in editor_text
    assert "・</span> <strong>Runway</strong>" in editor_text
    assert "text-align: right; margin: 2em 0 3em 0;" in editor_text
    assert "background-color: #FFFBDE" in editor_text
    assert "color: #222222" in editor_text


def test_wordpress_complex_blocks_failure_keeps_selection_text(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WordPressの複雑なが失敗の保持するの選択範囲の文字列を拒否することを確認する。"""
    _ = app
    window = MainWindow()
    source_text = "before\nplain text\nafter"
    selected_text = "plain text"
    window.editor.setPlainText(source_text)
    start = len("before\n")
    select_text(window, start, start + len(selected_text))

    def fake_convert(load_data: str) -> str:
        """Markdown変換の結果や失敗をテスト用に再現する。"""
        assert load_data == selected_text
        from editor.wordpress_markdown_converter import WordPressMarkdownConversionError

        raise WordPressMarkdownConversionError("not a table")

    monkeypatch.setattr(
        "main.convert_complex_markdown_blocks_to_wordpress_html",
        fake_convert,
    )

    window.convert_selected_markdown_blocks_to_wordpress_blocks()

    assert window.editor.toPlainText() == source_text
    assert "not a table" in window.statusBar().currentMessage()


def test_html_transform_does_nothing_without_selection(app: QApplication) -> None:
    """HTML変換のの何もない（選択範囲なし）を確認する。"""
    _ = app
    window = MainWindow()
    source_text = "<h1>タイトル</h1>"
    window.editor.setPlainText(source_text)
    window.editor.moveCursor(QTextCursor.MoveOperation.Start)

    window.escape_selected_html()

    assert window.editor.toPlainText() == source_text
    assert "選択" in window.statusBar().currentMessage()


def test_html_transform_context_menu_is_available(app: QApplication) -> None:
    """HTML変換のコンテキストメニューが利用できることを確認する。"""
    _ = app
    window = MainWindow()
    context_menu = window._create_editor_context_menu()

    html_transform_menu: QMenu | None = None
    paragraph_split_menu: QMenu | None = None
    for action in context_menu.actions():
        child_menu = action.menu()
        if (
            isinstance(child_menu, QMenu)
            and child_menu.title() == window.translator.text("action.html_transform")
        ):
            html_transform_menu = child_menu
        if (
            isinstance(child_menu, QMenu)
            and child_menu.title() == window.translator.text("paragraph_split.menu")
        ):
            paragraph_split_menu = child_menu

    assert html_transform_menu is not None
    assert [action.text() for action in html_transform_menu.actions()] == [
        "HTMLエスケープ",
        "HTMLエスケープ解除",
        "",
        "WordPressコードブロック化",
    ]
    assert paragraph_split_menu is not None
    paragraph_action_texts = [action.text() for action in paragraph_split_menu.actions()]
    assert paragraph_action_texts[-5:] == [
        "",
        "表変換",
        "リスト変換",
        "リストを枠囲みに変換",
        "Markdown表/リストをWordPressブロック化",
    ]


def test_html_transform_does_not_break_regex_search(app: QApplication) -> None:
    """HTML変換の行わないの区切りの正規表現の検索を確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("<h1>タイトル</h1>")
    select_text(window, 0, len("<h1>タイトル</h1>"))
    window.escape_selected_html()

    window.find_next("タイトル", SearchOptions())

    assert window.editor.textCursor().selectedText() == "タイトル"
