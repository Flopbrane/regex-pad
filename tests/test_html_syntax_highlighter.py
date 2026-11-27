"""HTMLの構文の構文の色付け処理を検証する。"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QTextBlock, QTextCursor
from PySide6.QtWidgets import QApplication

from editor.text_editor import TextEditor


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance() or QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def color_at(block: QTextBlock, position: int) -> str | None:
    """指定位置に適用された構文色を取得する。"""
    qt_position = len(block.text()[:position].encode("utf-16-le")) // 2
    for span in block.layout().formats():
        if span.start <= qt_position < span.start + span.length:
            return span.format.foreground().color().name()
    return None


def make_editor(app: QApplication, source: str) -> TextEditor:
    """指定された原稿を持つテスト用のエディターを作る。"""
    _ = app
    editor = TextEditor()
    editor.setPlainText(source)
    editor.document().setModified(False)
    editor.html_highlighter.rehighlight()
    return editor


@pytest.mark.parametrize("source,tag_lines,body_line", [
    ('<div style="\nbackground-color: #ffeecc;\ncolor: #333333;\n">\nTEST\n</div>', [0, 1, 2, 3, 5], 4),
    ('<img\n    src="test.jpg"\n    alt="test"\n    style="\n        width: 80%;\n        display: block;\n    "\n>\nTEST', list(range(8)), 8),
])
def test_multiline_tags_color_whole_opener_and_preserve_body(
    app: QApplication, source: str, tag_lines: list[int], body_line: int,
) -> None:
    """複数行のタグの色の全体の開始記号と保持の本文を確認する。"""
    editor = make_editor(app, source)
    for line in tag_lines:
        block = editor.document().findBlockByNumber(line)
        assert all(color_at(block, i) == editor.html_tag_color for i in range(len(block.text())))
    block = editor.document().findBlockByNumber(body_line)
    assert all(color_at(block, i) is None for i in range(len(block.text())))
    assert editor.toPlainText() == source
    assert not editor.document().isModified()


@pytest.mark.parametrize("quote", ['"', "'"])
def test_greater_than_inside_quoted_attribute_does_not_close_tag(app: QApplication, quote: str) -> None:
    """より大きい内の引用符で囲まれたの属性がタグを閉じないことを確認する。"""
    source = f'<div title={quote}first >\nsecond >{quote}\n>BODY</div>TAIL'
    editor = make_editor(app, source)
    second = editor.document().findBlockByNumber(1)
    assert all(color_at(second, i) == editor.html_tag_color for i in range(len(second.text())))
    last = editor.document().findBlockByNumber(2)
    assert color_at(last, 0) == editor.html_tag_color
    assert color_at(last, 1) is None
    assert color_at(last, 5) == editor.html_tag_color
    assert color_at(last, len(last.text()) - 1) is None


def test_multiple_single_line_tags_and_configured_colors(app: QApplication) -> None:
    """複数の1行のタグと設定済みの色を確認する。"""
    editor = make_editor(app, '<p>A<br />B</p>TAIL')
    editor.set_editor_colors(background_color="#ffffff", text_color="#202124", html_tag_color="#ad1234")
    block = editor.document().firstBlock()
    for position in (0, 2, 4, 9, 11, 14):
        assert color_at(block, position) == "#ad1234"
    for position in (3, 10, 15, 18):
        assert color_at(block, position) is None


@pytest.mark.parametrize("source", [
    '1 < 2 and &lt;div&gt; displayed',
    '<!-- ordinary comment with <div> and >\n<p>still a comment</p> -->\nBODY',
])
def test_display_text_and_ordinary_comments_do_not_start_tag_state(app: QApplication, source: str) -> None:
    """表示の文字列と通常のコメントの行わないの開始タグの状態を確認する。"""
    editor = make_editor(app, source)
    block = editor.document().firstBlock()
    while block.isValid():
        assert not block.layout().formats()
        block = block.next()


def test_wordpress_comments_retain_their_color_and_do_not_color_body(app: QApplication) -> None:
    """WordPressコメント自体の色を保ち、その色付けが本文に及ばないことを確認する。"""
    source = '<!-- wp:paragraph {\n"placeholder":"<div> >"\n} -->\n<p>BODY</p>\n<!-- /wp:paragraph -->'
    editor = make_editor(app, source)
    editor.html_highlighter.set_core_block_color("#8844aa")
    for line in (0, 1, 2, 4):
        block = editor.document().findBlockByNumber(line)
        assert all(color_at(block, i) == "#8844aa" for i in range(len(block.text())))
    paragraph = editor.document().findBlockByNumber(3)
    assert color_at(paragraph, 0) == editor.html_tag_color
    assert color_at(paragraph, 3) is None


def test_comment_like_text_inside_attribute_keeps_tag_color(app: QApplication) -> None:
    """属性値内のコメントに似た文字列でタグの色付けが変わらないことを確認する。"""
    editor = make_editor(app, '<div title="<!-- wp:html -->\nvalue >">BODY</div>')
    block = editor.document().findBlockByNumber(1)
    assert color_at(block, 7) == editor.html_tag_color
    assert color_at(block, 9) is None


def test_empty_lines_preserve_multiline_quote_state(app: QApplication) -> None:
    """空の行の保持の複数行の引用符の状態を確認する。"""
    editor = make_editor(app, '<div title="\n\nvalue >\n">BODY')
    block = editor.document().findBlockByNumber(2)
    assert all(color_at(block, i) == editor.html_tag_color for i in range(len(block.text())))
    assert color_at(block.next(), 2) is None


def test_editing_opening_quote_updates_following_blocks(app: QApplication) -> None:
    """編集中の開始の引用符が直後のブロックを更新することを確認する。"""
    editor = make_editor(app, '<div title="\nvalue >\n">\nBODY')
    cursor = QTextCursor(editor.document())
    cursor.setPosition(len('<div title='))
    cursor.deleteChar()
    app.processEvents()
    second = editor.document().findBlockByNumber(1)
    assert color_at(second, 6) == editor.html_tag_color
    third = second.next()
    assert all(color_at(third, i) is None for i in range(len(third.text())))


def test_disable_and_enable_clear_and_restore_multiline_formats(app: QApplication) -> None:
    """無効化で複数行の色付けが消え、再び有効化すると元に戻ることを確認する。"""
    editor = make_editor(app, '<div\n title="value >"\n>BODY')
    editor.html_highlighter.set_enabled(False)
    block = editor.document().firstBlock()
    while block.isValid():
        assert not block.layout().formats()
        block = block.next()
    editor.html_highlighter.set_enabled(True)
    assert color_at(editor.document().findBlockByNumber(1), 0) == editor.html_tag_color
    assert color_at(editor.document().findBlockByNumber(2), 1) is None


def test_non_bmp_text_before_tag_uses_qt_utf16_positions(app: QApplication) -> None:
    """非の基本多言語面の文字列前のタグがQtのUTF-16の位置を使うことを確認する。"""
    editor = make_editor(app, '😊<div\n title="😊 >"\n>本文</div>')
    first = editor.document().firstBlock()
    assert color_at(first, 0) is None
    assert color_at(first, 1) == editor.html_tag_color
    second = first.next()
    assert all(color_at(second, i) == editor.html_tag_color for i in range(len(second.text())))
    third = second.next()
    assert color_at(third, 1) is None
    assert color_at(third, 3) == editor.html_tag_color
