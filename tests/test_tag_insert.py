"""タグの挿入を検証する。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

from dialogs.tag_insert_dialog import TagInsertDialog
from editor.tag_insert import (
    TagSnippet,
    ordered_tag_snippet_groups,
    tag_snippet_category_key,
    tag_snippet_groups,
    wordpress_mode_keys,
)
from main import MainWindow

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_tag_snippet_renders_selection_and_cursor_position() -> None:
    """タグの定型文が選択範囲とカーソル位置を描画することを確認する。"""
    snippet = TagSnippet(
        "label",
        "hint",
        '<a href="{cursor}">{selection}</a>',
    )

    rendered_text, cursor_position = snippet.render("OpenAI")

    assert rendered_text == '<a href="">OpenAI</a>'
    assert cursor_position == len('<a href="')


def test_tag_snippet_uses_default_selection_when_text_is_not_selected() -> None:
    """文字列がしないの選択中のになるの場合、タグの定型文が既定の選択範囲を使うことを確認する。"""
    snippet = TagSnippet(
        "label",
        "hint",
        "<div>{selection}{cursor}</div>",
        default_selection="ここに本文を入れます。",
    )

    rendered_text, cursor_position = snippet.render("")

    assert rendered_text == "<div>ここに本文を入れます。</div>"
    assert cursor_position == len("<div>ここに本文を入れます。")


def test_insert_tag_menu_has_groups_and_parameter_hints(app: QApplication) -> None:
    """挿入のタグのメニューがグループとパラメーターのヒントを持つことを確認する。"""
    _ = app
    window = MainWindow()

    assert window.insert_tag_menu.title() == "タグ挿入(&T)"
    group_menus: list[QMenu] = []
    for action in window.insert_tag_menu.actions():
        child_menu = action.menu()
        if isinstance(child_menu, QMenu):
            group_menus.append(child_menu)

    assert [menu.title() for menu in group_menus] == [
        "HTML",
        "Markdown",
        "WordPress HTML",
    ]
    assert window.insert_tag_menu.toolTipsVisible()
    assert all(menu.toolTipsVisible() for menu in group_menus)
    html_category_menus = child_menus(group_menus[0])
    assert [menu.title() for menu in html_category_menus] == [
        "基本",
        "テキスト",
        "リンク / 画像",
        "レイアウト",
        "リスト",
        "コード",
        "ユーティリティ",
    ]
    first_html_action = html_category_menus[0].actions()[0]
    assert first_html_action.text() == "段落 <p>"
    assert "必須パラメータ" in first_html_action.statusTip()
    image_action = html_category_menus[2].actions()[2]
    assert image_action.text() == "画像 <img>"
    assert "src" in image_action.statusTip()
    assert "alt" in image_action.toolTip()
    assert "&lt;img&gt;" in image_action.toolTip()

    markdown_category_menus = child_menus(group_menus[1])
    assert [menu.title() for menu in markdown_category_menus] == [
        "テキスト",
        "リンク / 画像",
        "コード",
        "リスト",
        "レイアウト",
        "ユーティリティ",
    ]
    assert [action.text() for action in markdown_category_menus[0].actions()] == [
        "見出し1",
        "見出し2",
        "見出し3",
        "見出し4",
        "太字",
        "斜体",
        "取り消し線",
    ]

    wordpress_mode_menus = child_menus(group_menus[2])
    assert [menu.title() for menu in wordpress_mode_menus] == [
        "Normal",
        "企業・事業所",
        "Hi-security",
    ]


def test_insert_tag_menu_hides_tooltips_when_hover_hints_are_disabled(
    app: QApplication,
) -> None:
    """マウスを重ねたときのヒントが無効なであるの場合、挿入のタグのメニューがツールチップを非表示にすることを確認する。"""
    _ = app
    window = MainWindow()

    window.hover_hints_enabled = False
    window._rebuild_insert_tag_menu()

    group_menus = child_menus(window.insert_tag_menu)
    html_category_menus = child_menus(group_menus[0])
    first_html_action = html_category_menus[0].actions()[0]

    assert not window.insert_tag_menu.toolTipsVisible()
    assert not group_menus[0].toolTipsVisible()
    assert "必須パラメータ" not in first_html_action.toolTip()
    assert first_html_action.statusTip() == ""


def test_insert_tag_picker_shortcut_is_available(app: QApplication) -> None:
    """挿入のタグの選択画面のショートカットが利用できることを確認する。"""
    _ = app
    window = MainWindow()

    assert window.insert_tag_picker_action.shortcut().toString() == "Ctrl+Shift+T"
    assert window.insert_tag_picker_action.text() == "タグ挿入..."


def test_undo_redo_shortcuts_are_available(app: QApplication) -> None:
    """Undo／Redoのショートカットが利用できることを確認する。"""
    _ = app
    window = MainWindow()

    assert window.undo_action.shortcut().toString() == "Ctrl+Z"
    assert [shortcut.toString() for shortcut in window.redo_action.shortcuts()] == [
        "Ctrl+Y",
        "Ctrl+Shift+Z",
    ]


def test_line_break_insert_shortcuts_are_available(app: QApplication) -> None:
    """改行の挿入のショートカットが利用できることを確認する。"""
    _ = app
    window = MainWindow()

    assert window.insert_br_action.shortcut().toString() == "F8"
    assert window.insert_br_br_action.shortcut().toString() == "F9"
    assert window.insert_br_action.text() == "<br> を挿入"
    assert window.insert_br_br_action.text() == "<br><br> を挿入"
    assert window.insert_br_action in [
        action for action in window.edit_menu.actions()
    ]
    assert window.insert_br_br_action in [
        action for action in window.edit_menu.actions()
    ]


def test_inline_html_wrap_shortcuts_are_available(app: QApplication) -> None:
    """インラインのHTMLの折り返しのショートカットが利用できることを確認する。"""
    _ = app
    window = MainWindow()

    assert window.inline_strong_action.shortcut().toString() == "Ctrl+B"
    assert window.inline_underline_action.shortcut().toString() == "Ctrl+U"
    assert [
        shortcut.toString()
        for shortcut in window.inline_red_span_action.shortcuts()
    ] == ["Ctrl+Alt+1", "Ctrl+Alt+R"]
    assert {
        color_name: [shortcut.toString() for shortcut in action.shortcuts()]
        for color_name, action in window.inline_color_actions.items()
    } == {
        "red": ["Ctrl+Alt+1", "Ctrl+Alt+R"],
        "blue": ["Ctrl+Alt+2"],
        "green": ["Ctrl+Alt+3"],
        "orange": ["Ctrl+Alt+4"],
        "purple": ["Ctrl+Alt+5"],
        "pink": ["Ctrl+Alt+6"],
        "gray": ["Ctrl+Alt+7"],
    }
    assert window.inline_strong_action.text() == "選択範囲を <strong> で囲む"
    assert window.inline_underline_action.text() == "選択範囲を <u> で囲む"
    assert window.inline_red_span_action.text() == "赤文字 <span>"
    assert window.inline_color_actions["blue"].text() == "青文字 <span>"


def test_inline_html_wrap_actions_wrap_selected_text(app: QApplication) -> None:
    """インラインのHTMLの折り返しの操作の折り返しの選択文字列を確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("before target after")
    cursor = window.editor.textCursor()
    cursor.setPosition(len("before "))
    cursor.setPosition(len("before target"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)

    window.inline_strong_action.trigger()

    assert window.editor.toPlainText() == "before <strong>target</strong> after"
    assert window.editor.textCursor().position() == len("before <strong>target")

    window.undo_action.trigger()
    assert window.editor.toPlainText() == "before target after"

    cursor = window.editor.textCursor()
    cursor.setPosition(len("before "))
    cursor.setPosition(len("before target"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.inline_underline_action.trigger()
    assert window.editor.toPlainText() == 'before <u style="">target</u> after'
    assert window.editor.textCursor().position() == len('before <u style="">target')
    window.undo_action.trigger()
    assert window.editor.toPlainText() == "before target after"


def test_inline_html_wrap_actions_insert_pair_without_selection(
    app: QApplication,
) -> None:
    """インラインののHTMLの折り返しの操作の挿入の対（選択範囲なし）を確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("before after")
    cursor = window.editor.textCursor()
    cursor.setPosition(len("before "))
    window.editor.setTextCursor(cursor)

    window.inline_red_span_action.trigger()

    expected_text = 'before <span style="color: #d00000"></span>after'
    assert window.editor.toPlainText() == expected_text
    assert window.editor.textCursor().position() == len(
        'before <span style="color: #d00000">'
    )

    window.undo_action.trigger()
    cursor = window.editor.textCursor()
    cursor.setPosition(len("before "))
    window.editor.setTextCursor(cursor)
    window.inline_underline_action.trigger()
    assert window.editor.toPlainText() == 'before <u style=""></u>after'
    assert window.editor.textCursor().position() == len('before <u style="">')


def test_underline_shortcut_reads_selected_user_dictionary(
    app: QApplication, tmp_path: Path
) -> None:
    """下線のショートカットが選択中のユーザー辞書を読み取ることを確認する。"""
    _ = app
    load_data = json.loads(
        Path("dictionaries/paragraph_insert_dict.json").read_text(encoding="utf-8")
    )
    load_data["shortcut_insertions"]["inline_underline"] = (
        '<u class="personal">{selection}{cursor}</u>'
    )
    (tmp_path / "paragraph_insert_dict.json").write_text(
        json.dumps(load_data, ensure_ascii=False), encoding="utf-8"
    )
    window = MainWindow()
    window.user_dictionary_folder = str(tmp_path)
    window.editor.setPlainText("target")
    window.editor.selectAll()
    window.inline_underline_action.trigger()
    assert window.editor.toPlainText() == '<u class="personal">target</u>'


def test_inline_color_wrap_actions_wrap_selected_text(app: QApplication) -> None:
    """インライン色見本の折り返しの操作の折り返しの選択文字列を確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("before target after")
    cursor = window.editor.textCursor()
    cursor.setPosition(len("before "))
    cursor.setPosition(len("before target"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)

    window.inline_color_actions["blue"].trigger()

    assert (
        window.editor.toPlainText()
        == 'before <span style="color: #0057b8">target</span> after'
    )
    assert window.editor.textCursor().position() == len(
        'before <span style="color: #0057b8">target'
    )


def child_menus(menu: QMenu) -> list[QMenu]:
    """対象メニューの子メニューを取得する。"""
    menus: list[QMenu] = []
    for action in menu.actions():
        child_menu = action.menu()
        if isinstance(child_menu, QMenu):
            menus.append(child_menu)
    return menus


def test_editor_context_menu_has_tag_insert_actions(app: QApplication) -> None:
    """エディターのコンテキストメニューがタグの挿入の操作を持つことを確認する。"""
    _ = app
    window = MainWindow()
    context_menu = window._create_editor_context_menu()

    action_texts = [action.text() for action in context_menu.actions()]
    insert_tag_menu: QMenu | None = None
    inline_color_menu: QMenu | None = None
    css_insert_menu: QMenu | None = None
    child_menu_titles: list[str] = []
    for action in context_menu.actions():
        child_menu = action.menu()
        if isinstance(child_menu, QMenu):
            child_menu_titles.append(child_menu.title())
            if child_menu.title() == window.translator.text("action.insert_tag"):
                insert_tag_menu = child_menu
            if child_menu.title() == window.translator.text("action.inline_color_menu"):
                inline_color_menu = child_menu
            if child_menu.title() == window.translator.text("action.css_insert"):
                css_insert_menu = child_menu

    assert window.translator.text("action.insert_tag_picker") in action_texts
    assert isinstance(insert_tag_menu, QMenu)
    assert isinstance(inline_color_menu, QMenu)
    assert isinstance(css_insert_menu, QMenu)
    assert child_menu_titles[-5:] == [
        window.translator.text("paragraph_split.menu"),
        window.translator.text("action.insert_tag"),
        window.translator.text("action.inline_color_menu"),
        window.translator.text("action.css_insert"),
        window.translator.text("action.html_transform"),
    ]
    assert inline_color_menu.actions() == list(window.inline_color_actions.values())
    assert [action.text() for action in css_insert_menu.actions()] == [
        window.translator.text("action.css_insert_style_attribute"),
        window.translator.text("action.css_insert_color"),
        window.translator.text("action.css_insert_background_color"),
        window.translator.text("action.css_insert_font_size"),
        window.translator.text("action.css_insert_font_weight"),
        window.translator.text("action.css_insert_text_align"),
        window.translator.text("action.css_insert_margin"),
        window.translator.text("action.css_insert_padding"),
        window.translator.text("action.css_insert_border"),
        window.translator.text("action.css_insert_border_radius"),
        window.translator.text("action.css_insert_display_inline_block"),
    ]
    paragraph_split_menu = next(
        (
            child_menu
            for action in context_menu.actions()
            if isinstance((child_menu := action.menu()), QMenu)
            and child_menu.title() == "段落分割"
        ),
        None,
    )
    assert isinstance(paragraph_split_menu, QMenu)
    assert [action.text() for action in paragraph_split_menu.actions()] == [
        "スペーサー挿入",
        "HTML挿入",
        "枠組み指定",
        "",
        "表変換",
        "リスト変換",
        "リストを枠囲みに変換",
        "Markdown表/リストをWordPressブロック化",
    ]
    assert [menu.title() for menu in child_menus(insert_tag_menu)] == [
        "HTML",
        "Markdown",
        "WordPress HTML",
    ]


def test_css_insert_context_menu_actions_insert_editable_text(
    app: QApplication,
) -> None:
    """CSSの挿入のコンテキストメニューの操作の挿入の編集可能な文字列を確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("<p >Body</p>")
    cursor = window.editor.textCursor()
    cursor.setPosition(3)
    window.editor.setTextCursor(cursor)

    window.css_parameter_actions["style_attribute"].trigger()

    assert window.editor.toPlainText() == '<p style="">Body</p>'
    assert window.editor.textCursor().position() == len('<p style="')

    window.editor.setPlainText("")
    window.css_parameter_actions["background_color"].trigger()

    assert window.editor.toPlainText() == "background-color: ;"
    assert window.editor.textCursor().position() == len("background-color: ")
    assert isinstance(window.background_color_preset_menu, QMenu)
    window.background_color_preset_menu.close()


def test_background_color_preset_menu_replaces_only_the_value(
    app: QApplication,
) -> None:
    """背景色のプリセットのメニューがだけの値を置き換えることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText('<div style="">本文</div>')
    cursor = window.editor.textCursor()
    cursor.setPosition(len('<div style="'))
    window.editor.setTextCursor(cursor)

    window.css_parameter_actions["background_color"].trigger()

    menu = window.background_color_preset_menu
    assert isinstance(menu, QMenu)
    assert [action.data() for action in menu.actions()] == [
        "#FFE4E4",
        "#FFFBDE",
        "#F4FFDD",
        "#E2FFDF",
        "#DCFFF2",
        "#DBFFFE",
        "#D8E8FF",
        "#E8DDFF",
        "#FCDCFF",
    ]
    assert all(not action.icon().isNull() for action in menu.actions())

    menu.actions()[0].trigger()
    menu.close()

    assert window.editor.toPlainText() == (
        '<div style="background-color: #FFE4E4;">本文</div>'
    )
    assert window.editor.textCursor().position() == len(
        '<div style="background-color: #FFE4E4'
    )


def test_background_color_preset_menu_escape_keeps_manual_input_position(
    app: QApplication,
) -> None:
    """背景色のプリセットのメニューのエスケープが手動の入力欄の位置を保持することを確認する。"""
    _ = app
    window = MainWindow()

    window.css_parameter_actions["background_color"].trigger()

    menu = window.background_color_preset_menu
    assert isinstance(menu, QMenu)
    QTest.keyClick(menu, Qt.Key.Key_Escape)
    QApplication.processEvents()

    assert not menu.isVisible()
    assert window.editor.toPlainText() == "background-color: ;"
    assert window.editor.textCursor().position() == len("background-color: ")


def test_text_color_preset_menu_reuses_inline_shortcut_colors(
    app: QApplication,
) -> None:
    """文字色のプリセットメニューでインライン挿入のショートカットと同じ色を使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText('<span style="">本文</span>')
    cursor = window.editor.textCursor()
    cursor.setPosition(len('<span style="'))
    window.editor.setTextCursor(cursor)

    window.css_parameter_actions["color"].trigger()

    menu = window.text_color_preset_menu
    assert isinstance(menu, QMenu)
    assert [action.data() for action in menu.actions()] == [
        "#d00000",
        "#0057b8",
        "#008a3d",
        "#c85a00",
        "#7a3db8",
        "#c2185b",
        "#555555",
    ]
    assert all(not action.icon().isNull() for action in menu.actions())

    menu.actions()[1].trigger()
    menu.close()

    assert window.editor.toPlainText() == '<span style="color: #0057b8;">本文</span>'
    assert window.editor.textCursor().position() == len(
        '<span style="color: #0057b8'
    )
    assert [shortcut.toString() for shortcut in window.inline_color_actions["blue"].shortcuts()] == [
        "Ctrl+Alt+2"
    ]


def test_text_color_preset_menu_escape_keeps_manual_input_position(
    app: QApplication,
) -> None:
    """文字色のプリセットのメニューのエスケープが手動の入力欄の位置を保持することを確認する。"""
    _ = app
    window = MainWindow()

    window.css_parameter_actions["color"].trigger()

    menu = window.text_color_preset_menu
    assert isinstance(menu, QMenu)
    QTest.keyClick(menu, Qt.Key.Key_Escape)
    QApplication.processEvents()

    assert not menu.isVisible()
    assert window.editor.toPlainText() == "color: ;"
    assert window.editor.textCursor().position() == len("color: ")


def test_css_insert_style_attribute_stays_inside_opening_tag_after_tag_cursor(
    app: QApplication,
) -> None:
    """CSSの挿入のstyle属性の維持される内の開始タグ後のタグのカーソルを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("<div>本文</div>")
    cursor = window.editor.textCursor()
    cursor.setPosition(len("<div>"))
    window.editor.setTextCursor(cursor)

    window.css_parameter_actions["style_attribute"].trigger()

    assert window.editor.toPlainText() == '<div style="">本文</div>'
    assert window.editor.textCursor().position() == len('<div style="')


def test_css_insert_declaration_uses_existing_style_value(app: QApplication) -> None:
    """CSSの挿入のCSS宣言が既存のスタイルの値を使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText('<span style="">本文</span>')
    cursor = window.editor.textCursor()
    cursor.setPosition(len('<span style="'))
    window.editor.setTextCursor(cursor)

    window.css_parameter_actions["color"].trigger()

    assert window.editor.toPlainText() == '<span style="color: ;">本文</span>'
    assert window.editor.textCursor().position() == len('<span style="color: ')


def test_css_insert_declaration_creates_style_attribute_in_tag(
    app: QApplication,
) -> None:
    """CSSの挿入のCSS宣言がstyle属性内のタグを作ることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("<span>本文</span>")
    cursor = window.editor.textCursor()
    cursor.setPosition(len("<span>"))
    window.editor.setTextCursor(cursor)

    window.css_parameter_actions["color"].trigger()

    assert window.editor.toPlainText() == '<span style="color: ;">本文</span>'
    assert window.editor.textCursor().position() == len('<span style="color: ')


def test_tag_insert_dialog_filters_and_accepts_with_keyboard(
    app: QApplication,
) -> None:
    """タグの挿入のダイアログが絞り込むとともに、キーボードを受け入れることを確認する。"""
    _ = app
    window = MainWindow()
    dialog = TagInsertDialog(window.translator)
    dialog.set_snippet_groups(ordered_tag_snippet_groups(Path("sample.md")))

    dialog.search_edit.setText("コード")

    assert dialog.snippet_list.count() > 1
    assert "コード" in dialog.snippet_list.item(0).text()

    down_event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Down,
        Qt.KeyboardModifier.NoModifier,
    )
    assert dialog.eventFilter(dialog.search_edit, down_event)
    assert dialog.snippet_list.currentRow() == 1

    enter_event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Return,
        Qt.KeyboardModifier.NoModifier,
    )
    assert dialog.eventFilter(dialog.snippet_list, enter_event)
    selected_snippet = dialog.selected_choice()
    assert selected_snippet is not None
    assert selected_snippet.label_key.startswith("tag.markdown.code_block")


def test_tag_insert_dialog_updates_hint_on_hover(app: QApplication) -> None:
    """タグの挿入のダイアログがヒントでのマウスを重ねたときを更新することを確認する。"""
    _ = app
    window = MainWindow()
    dialog = TagInsertDialog(window.translator)
    dialog.set_snippet_groups(ordered_tag_snippet_groups(Path("sample.html")))

    item = dialog.snippet_list.item(0)
    assert item is not None
    assert dialog.hint_label.textFormat() == Qt.TextFormat.PlainText
    assert "&lt;p&gt;" in item.toolTip()

    dialog.hint_label.clear()
    dialog._handle_hovered_item(item)

    assert "<p>" in dialog.hint_label.text()
    assert "必須パラメータ" in dialog.hint_label.text()


def test_tag_group_order_prefers_current_file_extension(app: QApplication) -> None:
    """タグのグループの順序のを優先するの現在のファイルの拡張機能を確認する。"""
    _ = app
    window = MainWindow()

    window.current_save_file_path = Path("sample.md")
    assert child_menus_after_rebuild(window)[0].title() == "Markdown"

    window.current_save_file_path = Path("sample.html")
    assert child_menus_after_rebuild(window)[0].title() == "HTML"

    window.current_save_file_path = Path("sample.wp.html")
    assert child_menus_after_rebuild(window)[0].title() == "WordPress HTML"


def child_menus_after_rebuild(window: MainWindow) -> list[QMenu]:
    """メニューの再構築後に生成された子メニューを取得する。"""
    window._rebuild_insert_tag_menu()
    return child_menus(window.insert_tag_menu)


def test_ordered_tag_snippet_groups_prefers_extensions() -> None:
    """定型文のグループの並び順では拡張定義を優先することを確認する。"""
    assert ordered_tag_snippet_groups(Path("memo.md"))[0].label_key == (
        "tag.group.markdown"
    )
    assert ordered_tag_snippet_groups(Path("index.html"))[0].label_key == (
        "tag.group.html"
    )
    assert ordered_tag_snippet_groups(Path("article.wp.html"))[0].label_key == (
        "tag.group.wordpress_html"
    )


def test_insert_tag_snippet_wraps_selected_text(app: QApplication) -> None:
    """挿入のタグの定型文が選択文字列へ折り返すことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("hello")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    paragraph_snippet = tag_snippet_groups()[0].snippets[0]

    window.insert_tag_snippet(paragraph_snippet)

    assert window.editor.toPlainText() == "<p>hello</p>"
    assert window.editor.textCursor().position() == len("<p>hello")


def test_insert_tag_snippet_can_be_undone_and_redone(app: QApplication) -> None:
    """挿入のタグの定型文が元に戻したとやり直したが可能であることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("hello")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    paragraph_snippet = tag_snippet_groups()[0].snippets[0]

    window.insert_tag_snippet(paragraph_snippet)
    window.undo_action.trigger()

    assert window.editor.toPlainText() == "hello"

    window.redo_action.trigger()

    assert window.editor.toPlainText() == "<p>hello</p>"


def test_insert_line_break_actions_insert_fixed_html_text(
    app: QApplication,
) -> None:
    """改行挿入の操作で所定のHTML文字列を挿入することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("beforeafter")
    cursor = window.editor.textCursor()
    cursor.setPosition(len("before"))
    window.editor.setTextCursor(cursor)

    window.insert_br_action.trigger()
    window.insert_br_br_action.trigger()

    assert window.editor.toPlainText() == "before<br><br><br>after"
    assert window.editor.textCursor().position() == len("before<br><br><br>")

    window.undo_action.trigger()
    assert window.editor.toPlainText() == "before<br>after"
    window.undo_action.trigger()
    assert window.editor.toPlainText() == "beforeafter"


def test_insert_line_break_replaces_selected_text(app: QApplication) -> None:
    """挿入の改行が選択文字列を置き換えることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("before middle after")
    cursor = window.editor.textCursor()
    cursor.setPosition(len("before "))
    cursor.setPosition(len("before middle"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)

    window.insert_br_action.trigger()

    assert window.editor.toPlainText() == "before <br> after"


def test_insert_link_snippet_places_cursor_in_href(app: QApplication) -> None:
    """挿入のリンクの定型文がカーソル内のhref属性に配置することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("OpenAI")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    link_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[0].snippets
        if snippet.label_key == "tag.html.link"
    )

    window.insert_tag_snippet(link_snippet)

    assert window.editor.toPlainText() == '<a href="">OpenAI</a>'
    assert window.editor.textCursor().position() == len('<a href="')


def test_insert_html_image_snippet_uses_default_size_alignment_and_margin(
    app: QApplication,
) -> None:
    """挿入のHTMLの画像の定型文が既定のサイズの配置と余白を使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("画像の説明")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    image_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[0].snippets
        if snippet.label_key == "tag.html.image"
    )

    window.insert_tag_snippet(image_snippet)

    assert window.editor.toPlainText() == (
        '<img src="" '
        'style="width: 80%; display: block; margin: 2em auto 1.5em auto;" '
        'alt="画像の説明">'
    )
    assert window.editor.textCursor().position() == len('<img src="')


def test_html_snippets_are_loaded_from_json() -> None:
    """HTMLの定型文がJSONの状態でから読み込まれることを確認する。"""
    html_group = tag_snippet_groups()[0]

    assert html_group.label_key == "tag.group.html"
    assert len(html_group.snippets) == 35
    assert html_group.snippets[0].label_key == "tag.html.paragraph"
    assert html_group.snippets[-1].label_key == "tag.html.horizontal_rule"
    assert any(snippet.label_key == "tag.html.main" for snippet in html_group.snippets)
    assert any(snippet.label_key == "tag.html.form_basic" for snippet in html_group.snippets)


def test_tag_dictionary_rejects_empty_required_values(tmp_path: Path) -> None:
    """タグの辞書が空の必須の値を拒否することを確認する。"""
    write_tag_dictionary_files(
        tmp_path,
        html_items=[
            {
                "label_key": "",
                "hint_key": "tag.hint.html.paragraph",
                "template": "<p>{selection}{cursor}</p>",
            }
        ],
    )

    with pytest.raises(ValueError, match=r"non-empty.*html_dict\.json item #1"):
        tag_snippet_groups(tmp_path)


def test_tag_dictionary_rejects_missing_required_key(tmp_path: Path) -> None:
    """タグの辞書が不足した必須のキーを拒否することを確認する。"""
    write_tag_dictionary_files(
        tmp_path,
        html_items=[
            {
                "label_key": "tag.html.paragraph",
                "template": "<p>{selection}{cursor}</p>",
            }
        ],
    )

    with pytest.raises(ValueError, match=r"missing required key.*hint_key"):
        tag_snippet_groups(tmp_path)


def test_tag_dictionary_rejects_duplicated_label_key(tmp_path: Path) -> None:
    """タグの辞書が重複した表示名の翻訳キーを拒否することを確認する。"""
    write_tag_dictionary_files(
        tmp_path,
        html_items=[
            {
                "label_key": "tag.html.paragraph",
                "hint_key": "tag.hint.html.paragraph",
                "template": "<p>{selection}{cursor}</p>",
            },
            {
                "label_key": "tag.html.paragraph",
                "hint_key": "tag.hint.html.paragraph",
                "template": "<p>{selection}</p>",
            },
        ],
    )

    with pytest.raises(
        ValueError,
        match=r"duplicated label_key.*tag\.html\.paragraph.*item #2.*item #1",
    ):
        tag_snippet_groups(tmp_path)


def test_tag_dictionary_rejects_duplicated_cursor_placeholder(
    tmp_path: Path,
) -> None:
    """タグの辞書が重複したカーソルのプレースホルダーを拒否することを確認する。"""
    write_tag_dictionary_files(
        tmp_path,
        html_items=[
            {
                "label_key": "tag.html.paragraph",
                "hint_key": "tag.hint.html.paragraph",
                "template": "<p>{cursor}{selection}{cursor}</p>",
            }
        ],
    )

    with pytest.raises(ValueError, match=r"duplicated cursor.*html_dict\.json item #1"):
        tag_snippet_groups(tmp_path)


def test_tag_dictionary_rejects_unknown_placeholder(tmp_path: Path) -> None:
    """タグの辞書が未登録のプレースホルダーを拒否することを確認する。"""
    write_tag_dictionary_files(
        tmp_path,
        html_items=[
            {
                "label_key": "tag.html.paragraph",
                "hint_key": "tag.hint.html.paragraph",
                "template": "<p>{selected_text}</p>",
            }
        ],
    )

    with pytest.raises(ValueError, match=r"unknown placeholder.*html_dict\.json item #1"):
        tag_snippet_groups(tmp_path)


def test_tag_dictionary_rejects_broken_placeholder(tmp_path: Path) -> None:
    """タグの辞書が壊れたのプレースホルダーを拒否することを確認する。"""
    write_tag_dictionary_files(
        tmp_path,
        html_items=[
            {
                "label_key": "tag.html.paragraph",
                "hint_key": "tag.hint.html.paragraph",
                "template": "<p>{selection</p>",
            }
        ],
    )

    with pytest.raises(ValueError, match=r"broken placeholder.*selection"):
        tag_snippet_groups(tmp_path)


def test_tag_dictionary_accepts_structured_parameters(tmp_path: Path) -> None:
    """タグの辞書が構造化したパラメーターを受け入れることを確認する。"""
    write_tag_dictionary_files(
        tmp_path,
        html_items=[
            {
                "label_key": "tag.html.link",
                "hint_key": "tag.hint.html.link",
                "template": '<a href="{cursor}">{selection}</a>',
                "parameters": [
                    {
                        "name": "href",
                        "required": True,
                        "kind": "url",
                        "description_key": "tag.parameter.href",
                    }
                ],
            }
        ],
    )

    resources_path = tmp_path / "resources"
    resources_path.mkdir()
    write_app_text_files(
        resources_path,
        {
            "tag.html.link": "Link",
            "tag.hint.html.link": "Link hint",
            "tag.parameter.href": "Destination URL",
        },
    )

    snippet = tag_snippet_groups(tmp_path, resources_path)[0].snippets[0]

    assert snippet.parameters[0].name == "href"
    assert snippet.parameters[0].required is True
    assert snippet.parameters[0].kind == "url"
    assert snippet.parameters[0].description_key == "tag.parameter.href"


def test_tag_dictionary_rejects_invalid_parameters(tmp_path: Path) -> None:
    """タグの辞書が不正なパラメーターを拒否することを確認する。"""
    write_tag_dictionary_files(
        tmp_path,
        html_items=[
            {
                "label_key": "tag.html.paragraph",
                "hint_key": "tag.hint.html.paragraph",
                "template": "<p>{selection}{cursor}</p>",
                "parameters": [{"required": True}],
            }
        ],
    )

    with pytest.raises(ValueError, match=r"parameter requires non-empty name"):
        tag_snippet_groups(tmp_path)


def test_tag_dictionary_rejects_duplicated_parameter_names(tmp_path: Path) -> None:
    """タグの辞書が重複したパラメーターのに名前を付けるを拒否することを確認する。"""
    write_tag_dictionary_files(
        tmp_path,
        html_items=[
            {
                "label_key": "tag.html.image",
                "hint_key": "tag.hint.html.image",
                "template": '<img src="{cursor}" alt="{selection}">',
                "parameters": [
                    {"name": "src", "required": True},
                    {"name": "src", "required": False},
                ],
            }
        ],
    )

    with pytest.raises(ValueError, match=r"duplicated name 'src'"):
        tag_snippet_groups(tmp_path)


def test_tag_dictionary_translation_keys_exist() -> None:
    """タグの辞書の翻訳キーの存在することを確認する。"""
    snippets = [
        snippet
        for group in tag_snippet_groups()
        for snippet in group.snippets
    ]
    resource_paths = [
        PROJECT_ROOT / "resources" / "app_text_en.json",
        PROJECT_ROOT / "resources" / "app_text_ja.json",
    ]

    for resource_path in resource_paths:
        translations = json.loads(resource_path.read_text(encoding="utf-8"))
        missing_keys = [
            key
            for snippet in snippets
            for key in (snippet.label_key, snippet.hint_key)
            if key not in translations
        ]

        assert missing_keys == []


def test_tag_dictionary_rejects_missing_translation_key(tmp_path: Path) -> None:
    """タグの辞書が不足した翻訳キーを拒否することを確認する。"""
    dictionaries_path = tmp_path / "dictionaries"
    resources_path = tmp_path / "resources"
    dictionaries_path.mkdir()
    resources_path.mkdir()
    write_tag_dictionary_files(
        dictionaries_path,
        html_items=[
            {
                "label_key": "tag.html.custom_missing",
                "hint_key": "tag.hint.html.custom_missing",
                "template": "<p>{selection}{cursor}</p>",
            }
        ],
    )
    write_app_text_files(
        resources_path,
        extra_keys={
            "tag.html.custom_missing": "Custom",
        },
    )

    with pytest.raises(
        ValueError,
        match=r"app_text_ja\.json.*tag\.hint\.html\.custom_missing",
    ):
        tag_snippet_groups(dictionaries_path, resources_path)


def write_tag_dictionary_files(
    dictionaries_path: Path,
    html_items: list[dict[str, object]],
) -> None:
    """挿入テスト用のタグ辞書ファイルを作る。"""
    valid_item = {
        "label_key": "tag.html.paragraph",
        "hint_key": "tag.hint.html.paragraph",
        "template": "<p>{selection}{cursor}</p>",
    }
    (dictionaries_path / "html_dict.json").write_text(
        json.dumps(html_items),
        encoding="utf-8",
    )
    (dictionaries_path / "markdown_dict.json").write_text(
        json.dumps([valid_item]),
        encoding="utf-8",
    )
    (dictionaries_path / "wordpress_html_dict.json").write_text(
        json.dumps([valid_item]),
        encoding="utf-8",
    )


def write_app_text_files(
    resources_path: Path,
    extra_keys: dict[str, str] | None = None,
) -> None:
    """挿入テスト用の日英翻訳ファイルを作る。"""
    texts = {
        "tag.group.html": "HTML",
        "tag.group.markdown": "Markdown",
        "tag.group.wordpress_html": "WordPress HTML",
        "tag.html.paragraph": "Paragraph",
        "tag.hint.html.paragraph": "Paragraph hint",
    }
    if extra_keys:
        texts.update(extra_keys)
    for language_code in ("ja", "en"):
        (resources_path / f"app_text_{language_code}.json").write_text(
            json.dumps(texts),
            encoding="utf-8",
        )


def test_insert_html_div_places_cursor_in_style_parameter(app: QApplication) -> None:
    """HTMLのdiv要素を挿入すると、style属性の入力位置にカーソルが移ることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("content")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    div_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[0].snippets
        if snippet.label_key == "tag.html.div"
    )

    window.insert_tag_snippet(div_snippet)

    assert window.editor.toPlainText() == '<div style="">content</div>'
    assert window.editor.textCursor().position() == len('<div style="')


def test_markdown_snippets_are_loaded_from_json() -> None:
    """Markdownの定型文をJSONから読み込むことを確認する。"""
    markdown_group = tag_snippet_groups()[1]

    assert markdown_group.label_key == "tag.group.markdown"
    assert len(markdown_group.snippets) == 27
    assert markdown_group.snippets[0].label_key == "tag.markdown.heading1"
    assert markdown_group.snippets[-1].label_key == "tag.markdown.horizontal_rule"


def test_insert_markdown_code_block_places_cursor_after_opening_fence(
    app: QApplication,
) -> None:
    """開始のフェンス後、挿入のMarkdownのコードブロックがカーソルに配置することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("print('hello')")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    code_block_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[1].snippets
        if snippet.label_key == "tag.markdown.code_block"
    )

    window.insert_tag_snippet(code_block_snippet)

    assert window.editor.toPlainText() == "```\nprint('hello')\n```"
    assert window.editor.textCursor().position() == len("```")


def test_insert_markdown_python_code_block_uses_selected_language(
    app: QApplication,
) -> None:
    """挿入のMarkdownのPythonのコードブロックが選択中の言語を使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("print('hello')")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    python_code_block_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[1].snippets
        if snippet.label_key == "tag.markdown.code_block_python"
    )

    window.insert_tag_snippet(python_code_block_snippet)

    assert window.editor.toPlainText() == "```python\nprint('hello')\n```"
    assert window.editor.textCursor().position() == len("```python\nprint('hello')")


def test_wordpress_html_snippets_are_loaded_from_json() -> None:
    """WordPressのHTMLの定型文がJSONの状態でから読み込まれることを確認する。"""
    wordpress_group = tag_snippet_groups()[2]

    assert wordpress_group.label_key == "tag.group.wordpress_html"
    assert len(wordpress_group.snippets) == 32
    assert wordpress_group.snippets[0].label_key == "tag.wordpress.paragraph_block"
    assert wordpress_group.snippets[3].label_key == (
        "tag.wordpress.soft_subheading_paragraph"
    )
    assert wordpress_group.snippets[8].label_key == "tag.wordpress.html_code_box"
    assert wordpress_group.snippets[10].label_key == (
        "tag.wordpress.decorative_separator_block"
    )
    assert wordpress_group.snippets[13].label_key == "tag.wordpress.link_block"
    assert wordpress_group.snippets[14].label_key == (
        "tag.wordpress.custom_frame_block"
    )
    assert wordpress_group.snippets[17].label_key == (
        "tag.wordpress.important_frame_block"
    )
    assert wordpress_group.snippets[18].label_key == "tag.wordpress.table_block"
    assert wordpress_group.snippets[19].label_key == (
        "tag.wordpress.details_html_block"
    )
    assert wordpress_group.snippets[25].label_key == (
        "tag.wordpress.columns_2_text_block"
    )
    assert wordpress_group.snippets[26].label_key == (
        "tag.wordpress.columns_3_text_block"
    )
    assert wordpress_group.snippets[-2].label_key == "tag.wordpress.video_block"
    assert wordpress_group.snippets[-1].label_key == "tag.wordpress.audio_block"


def test_wordpress_media_snippets_use_media_category() -> None:
    """WordPressのメディアの定型文の使用のメディアの分類を確認する。"""
    wordpress_group = tag_snippet_groups()[2]

    media_categories = {
        tag_snippet_category_key(wordpress_group.label_key, snippet)
        for snippet in wordpress_group.snippets
        if snippet.label_key
        in {
            "tag.wordpress.image_block",
            "tag.wordpress.media_text_left_block",
            "tag.wordpress.video_block",
            "tag.wordpress.audio_block",
        }
    }

    assert media_categories == {"tag.category.media"}


def test_wordpress_link_snippet_uses_link_image_category() -> None:
    """WordPressのリンクの定型文がリンクの画像の分類を使うことを確認する。"""
    wordpress_group = tag_snippet_groups()[2]
    link_snippet = next(
        snippet
        for snippet in wordpress_group.snippets
        if snippet.label_key == "tag.wordpress.link_block"
    )

    assert tag_snippet_category_key(wordpress_group.label_key, link_snippet) == (
        "tag.category.link_image"
    )


def test_wordpress_soft_subheading_uses_text_category() -> None:
    """WordPressの表示上の小見出しが文字列の分類を使うことを確認する。"""
    wordpress_group = tag_snippet_groups()[2]
    subheading_snippet = next(
        snippet
        for snippet in wordpress_group.snippets
        if snippet.label_key == "tag.wordpress.soft_subheading_paragraph"
    )

    assert tag_snippet_category_key(
        wordpress_group.label_key,
        subheading_snippet,
    ) == "tag.category.text"


def test_wordpress_text_columns_and_article_parts_use_layout_category() -> None:
    """WordPressの文字列の列と原稿の部分の使用のレイアウトの分類を確認する。"""
    wordpress_group = tag_snippet_groups()[2]
    layout_snippets = [
        snippet
        for snippet in wordpress_group.snippets
        if snippet.label_key
        in {
            "tag.wordpress.decorative_separator_block",
            "tag.wordpress.table_block",
            "tag.wordpress.details_html_block",
            "tag.wordpress.columns_2_text_block",
            "tag.wordpress.columns_3_text_block",
        }
    ]

    assert [
        tag_snippet_category_key(wordpress_group.label_key, snippet)
        for snippet in layout_snippets
    ] == [
        "tag.category.layout",
        "tag.category.layout",
        "tag.category.layout",
        "tag.category.layout",
        "tag.category.layout",
    ]


def test_wordpress_custom_frame_uses_layout_category() -> None:
    """WordPressのカスタムの枠がレイアウトの分類を使うことを確認する。"""
    wordpress_group = tag_snippet_groups()[2]
    frame_snippets = [
        snippet
        for snippet in wordpress_group.snippets
        if snippet.label_key
        in {
            "tag.wordpress.custom_frame_block",
            "tag.wordpress.notice_frame_block",
            "tag.wordpress.info_frame_block",
            "tag.wordpress.important_frame_block",
        }
    ]

    assert [
        tag_snippet_category_key(wordpress_group.label_key, snippet)
        for snippet in frame_snippets
    ] == [
        "tag.category.layout",
        "tag.category.layout",
        "tag.category.layout",
        "tag.category.layout",
    ]


def test_wordpress_snippets_have_expected_mode_groups() -> None:
    """WordPressの定型文が期待値のモードのグループを持つことを確認する。"""
    snippets = {snippet.label_key: snippet for snippet in tag_snippet_groups()[2].snippets}

    assert wordpress_mode_keys(snippets["tag.wordpress.paragraph_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.image_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.link_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.soft_subheading_paragraph"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.custom_frame_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(
        snippets["tag.wordpress.decorative_separator_block"]
    ) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.notice_frame_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.info_frame_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.important_frame_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.table_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.details_html_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.columns_2_text_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.columns_3_text_block"]) == (
        "tag.wordpress_mode.normal",
        "tag.wordpress_mode.business",
        "tag.wordpress_mode.high_security",
    )
    assert wordpress_mode_keys(snippets["tag.wordpress.html_code_box"]) == (
        "tag.wordpress_mode.normal",
    )


def test_insert_wordpress_code_block_uses_pre_code_markup(
    app: QApplication,
) -> None:
    """挿入のWordPressのコードブロックがpreタグのコードのマークアップを使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("print('hello')")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    code_snippet = tag_snippet_groups()[2].snippets[6]

    window.insert_tag_snippet(code_snippet)

    assert window.editor.toPlainText() == (
        "<!-- wp:code -->\n"
        '<pre class="wp-block-code"><code>print(\'hello\')</code></pre>\n'
        "<!-- /wp:code -->"
    )
    assert window.editor.textCursor().position() == len(
        "<!-- wp:code -->\n"
        '<pre class="wp-block-code"><code>print(\'hello\')'
    )


def test_insert_wordpress_html_code_box_uses_custom_style(
    app: QApplication,
) -> None:
    """挿入のWordPressのHTMLのコードの枠がカスタムのスタイルを使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("sample")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    html_code_box_snippet = tag_snippet_groups()[2].snippets[8]

    window.insert_tag_snippet(html_code_box_snippet)

    assert "<!-- wp:html -->" in window.editor.toPlainText()
    assert 'class="wp-block-code"' in window.editor.toPlainText()
    assert "display: inline-block; border: 1px solid #999;" in (
        window.editor.toPlainText()
    )
    assert "\n><code>sample</code></pre>" in window.editor.toPlainText()


def test_insert_wordpress_link_block_places_cursor_in_href(
    app: QApplication,
) -> None:
    """挿入のWordPressのリンクのブロックがカーソル内のhref属性に配置することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("公式サイト")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    link_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.link_block"
    )

    window.insert_tag_snippet(link_snippet)

    assert window.editor.toPlainText() == (
        '<!-- wp:paragraph -->\n<p><a href="">公式サイト</a></p>\n'
        "<!-- /wp:paragraph -->"
    )
    assert window.editor.textCursor().position() == len(
        '<!-- wp:paragraph -->\n<p><a href="'
    )


def test_insert_wordpress_image_block_uses_default_size_alignment_and_margin(
    app: QApplication,
) -> None:
    """挿入のWordPressの画像のブロックが既定のサイズの配置と余白を使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("画像の説明")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    image_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.image_block"
    )

    window.insert_tag_snippet(image_snippet)

    editor_text = window.editor.toPlainText()
    assert editor_text == (
        '<!-- wp:image {"sizeSlug":"full","linkDestination":"none"} -->\n'
        '<figure class="wp-block-image size-full"><img src="" '
        'style="width: 80%; display: block; margin: 2em auto 1.5em auto;" '
        'alt="画像の説明"/></figure>\n'
        "<!-- /wp:image -->"
    )
    assert window.editor.textCursor().position() == len(
        '<!-- wp:image {"sizeSlug":"full","linkDestination":"none"} -->\n'
        '<figure class="wp-block-image size-full"><img src="'
    )


def test_insert_wordpress_soft_subheading_paragraph_avoids_h3_markup(
    app: QApplication,
) -> None:
    """挿入のWordPressの表示上の小見出しの段落のを避けるのh3のマークアップを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("最初からできなくても大丈夫です")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    subheading_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.soft_subheading_paragraph"
    )

    window.insert_tag_snippet(subheading_snippet)

    editor_text = window.editor.toPlainText()
    assert editor_text == (
        "<!-- wp:paragraph -->\n"
        '<p><span style="font-size: 1.08em; font-weight: bold;">'
        "最初からできなくても大丈夫です"
        "</span></p>\n"
        "<!-- /wp:paragraph -->"
    )
    assert "<h3" not in editor_text
    assert "wp:heading" not in editor_text
    assert window.editor.textCursor().position() == editor_text.index("</span>")


def test_insert_wordpress_custom_frame_block_has_editable_style_parameters(
    app: QApplication,
) -> None:
    """挿入のWordPressのカスタムの枠ブロックが編集可能なスタイルのパラメーターを持つことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("重要なお知らせ")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    frame_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.custom_frame_block"
    )

    window.insert_tag_snippet(frame_snippet)

    editor_text = window.editor.toPlainText()
    assert editor_text.count("<!-- wp:html -->") == 1
    assert editor_text.count("<!-- /wp:html -->") == 1
    assert "<!-- wp:group -->" not in editor_text
    assert "<!-- wp:paragraph -->" not in editor_text
    assert 'text-align: left; margin: 1.5em 0 2em 0;">' in editor_text
    assert "display: inline-block;" in editor_text
    assert "max-width: 100%;" in editor_text
    source_style = frame_snippet.template.split('<div style="', 1)[1].split('">', 1)[0]
    for property_name in ("border", "border-left", "padding", "border-radius"):
        declaration = next(
            part.strip() for part in source_style.split(";")
            if part.strip().startswith(f"{property_name}:")
        )
        assert f"{declaration};" in editor_text
    assert "background-color: #fffaf0;" in editor_text
    assert "color: #333333;" in editor_text
    assert "text-align: left;" in editor_text
    assert "\n重要なお知らせ\n</div>" in editor_text
    assert window.editor.textCursor().position() == editor_text.index("\n</div>")


def test_insert_wordpress_decorative_separator_uses_html_block_parameters(
    app: QApplication,
) -> None:
    """挿入のWordPressの装飾用の区切りがHTMLのブロックのパラメーターを使うことを確認する。"""
    _ = app
    window = MainWindow()
    separator_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.decorative_separator_block"
    )

    window.insert_tag_snippet(separator_snippet)

    editor_text = window.editor.toPlainText()
    assert editor_text.count("<!-- wp:html -->") == 1
    assert editor_text.count("<!-- /wp:html -->") == 1
    assert "<!-- wp:separator -->" not in editor_text
    assert "--separator-line-style: solid;" in editor_text
    assert "--separator-thickness: 4px;" in editor_text
    assert "--separator-color: #79b7d8;" in editor_text
    assert (
        "--separator-gradient: linear-gradient(90deg, #79b7d8 0%, #f0b84a 100%);"
        in editor_text
    )
    assert "height: var(--separator-thickness);" in editor_text
    assert "background: var(--separator-gradient);" in editor_text
    assert 'aria-hidden="true"' in editor_text
    assert [parameter.name for parameter in separator_snippet.parameters] == [
        "line_style",
        "thickness",
        "color",
        "gradient",
    ]


def test_insert_wordpress_frame_block_keeps_multiline_selection_in_single_html_block(
    app: QApplication,
) -> None:
    """挿入のWordPressの枠ブロックが複数行の選択範囲内の単一のHTMLのブロックを保持することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("1行目\nSecond line\n三行目")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    frame_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.custom_frame_block"
    )

    window.insert_tag_snippet(frame_snippet)

    editor_text = window.editor.toPlainText()
    assert editor_text.count("<!-- wp:html -->") == 1
    assert editor_text.count("<!-- /wp:html -->") == 1
    assert "\n1行目\nSecond line\n三行目\n</div>" in editor_text
    assert "<!-- wp:paragraph -->" not in editor_text
    assert "wp:preformatted" not in editor_text


def test_insert_wordpress_frame_block_without_selection_keeps_matching_tags(
    app: QApplication,
) -> None:
    """挿入のWordPressの枠ブロック（選択範囲なし）が一致するのタグを保持することを確認する。"""
    _ = app
    window = MainWindow()
    frame_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.custom_frame_block"
    )

    window.insert_tag_snippet(frame_snippet)

    editor_text = window.editor.toPlainText()
    assert editor_text.startswith(
        "<!-- wp:html -->\n"
        '<div style="text-align: left; margin: 1.5em 0 2em 0;">\n'
        '<div style="display: inline-block; max-width: 100%; '
    )
    assert editor_text.count("<div style=") == 2
    assert frame_snippet.default_selection in editor_text
    assert editor_text.endswith("\n</div>\n</div>\n<!-- /wp:html -->")
    assert window.editor.textCursor().position() == editor_text.index("\n</div>")
    assert "wp:preformatted" not in editor_text


def test_insert_wordpress_frame_presets_keep_distinct_border_styles(
    app: QApplication,
) -> None:
    """挿入のWordPressの枠のプリセットの保持するの異なるの境界線のスタイルを確認する。"""
    _ = app
    snippets = {snippet.label_key: snippet for snippet in tag_snippet_groups()[2].snippets}

    frame_keys = (
        "tag.wordpress.notice_frame_block",
        "tag.wordpress.info_frame_block",
        "tag.wordpress.important_frame_block",
    )
    borders: set[str] = set()
    for label_key in frame_keys:
        snippet = snippets[label_key]
        source_style = snippet.template.split('<div style="', 1)[1].split('">', 1)[0]
        border = next(
            part.strip() for part in source_style.split(";")
            if part.strip().startswith("border:")
        )
        borders.add(border)
        window = MainWindow()
        window.editor.setPlainText("本文")
        cursor = window.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        window.editor.setTextCursor(cursor)

        window.insert_tag_snippet(snippet)

        editor_text = window.editor.toPlainText()
        assert editor_text.count("<!-- wp:html -->") == 1
        assert editor_text.count("<!-- /wp:html -->") == 1
        assert "\n本文\n</div>" in editor_text
        assert "<!-- wp:group -->" not in editor_text
        assert 'text-align: left; margin: 1.5em 0 2em 0;">' in editor_text
        assert f"{border};" in editor_text
        assert "background-color: #fffaf0;" in editor_text
        assert "color: #333333;" in editor_text
    assert len(borders) == len(frame_keys)


def test_insert_wordpress_frame_uses_configured_alignment_and_display(
    app: QApplication,
) -> None:
    """挿入のWordPressの枠が設定済みの配置と表示を使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.frame_alignment = "right"
    window.frame_display = "grid"
    window.frame_outer_spacing = "2em 0 3em 0"
    window.frame_background_color = "#f0f9ff"
    window.frame_text_color = "#14384f"
    window.editor.setPlainText("中央に置く短い枠")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    frame_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.custom_frame_block"
    )

    window.insert_tag_snippet(frame_snippet)

    editor_text = window.editor.toPlainText()
    assert '<div style="text-align: right; margin: 2em 0 3em 0;">' in editor_text
    assert "display: grid;" in editor_text
    assert "width: 100%;" in editor_text
    assert "box-sizing: border-box;" in editor_text
    assert "background-color: #f0f9ff;" in editor_text
    assert "color: #14384f;" in editor_text
    assert "text-align: left;" in editor_text
    assert "\n中央に置く短い枠\n</div>\n</div>" in editor_text


def test_insert_wordpress_two_column_text_block(app: QApplication) -> None:
    """挿入のWordPressの2つの列の文字列のブロックを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("1段目")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    two_column_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.columns_2_text_block"
    )

    window.insert_tag_snippet(two_column_snippet)

    editor_text = window.editor.toPlainText()
    assert editor_text.count("<!-- wp:column -->") == 2
    assert "<p>1段目</p>" in editor_text
    assert "<p>ここに2段目の文章を入力します。</p>" in editor_text
    assert window.editor.textCursor().position() == editor_text.index("</p>")


def test_insert_wordpress_three_column_text_block(app: QApplication) -> None:
    """挿入のWordPressの3列の文字列のブロックを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("1段目")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    three_column_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.columns_3_text_block"
    )

    window.insert_tag_snippet(three_column_snippet)

    editor_text = window.editor.toPlainText()
    assert editor_text.count("<!-- wp:column -->") == 3
    assert "<p>1段目</p>" in editor_text
    assert "<p>ここに2段目の文章を入力します。</p>" in editor_text
    assert "<p>ここに3段目の文章を入力します。</p>" in editor_text


def test_insert_wordpress_table_block(app: QApplication) -> None:
    """挿入のWordPressの表ブロックを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("料金")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    table_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.table_block"
    )

    window.insert_tag_snippet(table_snippet)

    editor_text = window.editor.toPlainText()
    assert editor_text.startswith("<!-- wp:table -->")
    assert editor_text.endswith("<!-- /wp:table -->")
    assert '<figure class="wp-block-table">' in editor_text
    assert "<th>項目</th><th>内容</th>" in editor_text
    assert "<td>料金</td><td></td>" in editor_text
    assert window.editor.textCursor().position() == editor_text.index("</td>")


def test_insert_wordpress_details_html_block_keeps_single_html_block(
    app: QApplication,
) -> None:
    """WordPressの詳細欄を挿入してもHTMLブロックが一つにまとまることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("詳しい説明")
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    details_snippet = next(
        snippet
        for snippet in tag_snippet_groups()[2].snippets
        if snippet.label_key == "tag.wordpress.details_html_block"
    )

    window.insert_tag_snippet(details_snippet)

    editor_text = window.editor.toPlainText()
    assert editor_text.count("<!-- wp:html -->") == 1
    assert editor_text.count("<!-- /wp:html -->") == 1
    assert "<details>" in editor_text
    assert "<summary></summary>" in editor_text
    assert "\n詳しい説明\n</div>" in editor_text
    assert "<!-- wp:paragraph -->" not in editor_text
    assert window.editor.textCursor().position() == editor_text.index("</summary>")
