"""色見本の検出、描画位置、クリックによる編集を確認する。"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from pytest import MonkeyPatch

import editor.text_editor as text_editor_module
from dialogs.inline_color_dialog import InlineColorDialog
from editor.inline_color import ColorContext, find_colors
from editor.text_editor import InlineColorData, TextEditor
from main import MainWindow
from settings.settings_manager import SettingsManager


def test_css_and_html_color_contexts() -> None:
    css = '#aabbcc { border:1px solid #A1b2C3; background:url(#123456); color:#12345678; }'
    found, _, _ = find_colors(css, ColorContext.HTML, 0, stylesheet=True)
    assert found == [(css.index("#A1b2C3"), "#A1b2C3")]
    html = '<a id="#aabbcc" href="#123456" style="color:#A1b2C3">本文</a>'
    found, _, _ = find_colors(html, ColorContext.HTML, 0, stylesheet=False)
    assert found == [(html.index("#A1b2C3"), "#A1b2C3")]
    for opener, fragment in (
        ("<!--", html),
        ("<script>", html),
        ("<style>/*", "color:#123456;"),
        ('<p title="', "style='color:#123456'"),
    ):
        _, context, depth = find_colors(opener, ColorContext.HTML, 0, stylesheet=False)
        assert not find_colors(fragment, context, depth, stylesheet=False)[0]


def test_swatch_spacing_is_display_only_and_updates_after_edit() -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    editor = TextEditor()
    source = '😀<p style="color:#112233;">本文</p>'
    editor.setPlainText(source)
    editor.resize(550, 150)
    editor.set_inline_color_preview(True, stylesheet=False)
    editor.show()
    app.processEvents()
    swatches = list(editor._visible_inline_colors(editor.viewport().rect()))
    assert len(swatches) == 1
    rect, start, code = swatches[0]
    assert start == source.index(code) + 1  # astral character occupies two UTF-16 units
    assert editor.viewport().grab().toImage().pixelColor(rect.center()).name() == code
    assert editor.toPlainText() == source
    assert not editor.document().isModified()
    assert not editor.document().isUndoAvailable()
    editor.set_inline_color_preview(False, stylesheet=False)
    assert not isinstance(editor.document().firstBlock().userData(), InlineColorData)
    editor.set_inline_color_preview(True, stylesheet=False)
    cursor = editor.textCursor()
    cursor.setPosition(start)
    cursor.deleteChar()
    assert not list(editor._visible_inline_colors(editor.viewport().rect()))


def test_scrolling_and_wrapping_keep_swatches_on_their_visual_line() -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    editor = TextEditor()
    editor.setPlainText(" " * 80 + "color:#112233;" + "\n" + "\n".join(["color:#223344;"] * 50))
    editor.resize(300, 150)
    editor.set_word_wrap_enabled(False)
    editor.set_inline_color_preview(True, stylesheet=True)
    editor.show()
    app.processEvents()
    assert "#112233" not in [code for _, _, code in editor._visible_inline_colors(editor.viewport().rect())]
    horizontal = editor.horizontalScrollBar()
    horizontal.setValue(horizontal.maximum())
    app.processEvents()
    assert "#112233" in [code for _, _, code in editor._visible_inline_colors(editor.viewport().rect())]
    editor.set_word_wrap_enabled(True)
    app.processEvents()
    rect, _, _ = next(item for item in editor._visible_inline_colors(editor.viewport().rect()) if item[2] == "#112233")
    assert editor.viewport().grab().toImage().pixelColor(rect.center()).name() == "#112233"


def test_edit_and_scroll_do_not_redetect_colors_across_the_document(monkeypatch: MonkeyPatch) -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    editor = TextEditor()
    editor.set_inline_color_preview(True, stylesheet=True)
    editor.setPlainText("color:#112233;\n" * 2000)
    editor.show()
    app.processEvents()
    calls: list[str] = []

    def find_colors_in_changed_block(text: str, context: ColorContext, depth: int, *, stylesheet: bool):
        calls.append(text)
        return find_colors(text, context, depth, stylesheet=stylesheet)

    monkeypatch.setattr(text_editor_module, "find_colors", find_colors_in_changed_block)
    editor.insertPlainText(" ")
    editor.verticalScrollBar().setValue(1000)
    app.processEvents()
    assert calls == [" color:#112233;"]


def test_click_apply_cancel_and_stale_target(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    assert not window.inline_color_preview_enabled
    def enable_swatches() -> None:
        options = window.options_dialog
        assert options is not None
        options.inline_color_preview_checkbox.setChecked(True)
        options.accept()

    QTimer.singleShot(0, enable_swatches)
    window.show_options_dialog()
    assert SettingsManager(tmp_path / "settings.json").load().inline_color_preview_enabled
    editor = window.editor
    source = '<p style="color:#112233; background-color:#112233;">本文</p>'
    editor.setPlainText(source)
    window.resize(1100, 400)
    window.show()
    app.processEvents()

    def open_picker() -> InlineColorDialog:
        rect, _, _ = list(editor._visible_inline_colors(editor.viewport().rect()))[1]
        QTest.mouseClick(editor.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
        dialog = next(item for item in window.findChildren(InlineColorDialog) if item.isVisible())
        assert dialog.currentColor().name() == "#112233"
        return dialog

    dialog = open_picker()
    dialog.setCurrentColor(QColor("#abcdef"))
    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons is not None
    apply = buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert apply is not None and apply.text() in {"適用", "Apply"}
    apply.click()
    changed = source.replace("background-color:#112233", "background-color:#ABCDEF")
    assert editor.toPlainText() == changed
    editor.undo()
    assert editor.toPlainText() == source
    editor.redo()
    assert editor.toPlainText() == changed
    editor.undo()

    dialog = open_picker()
    dialog.setCurrentColor(QColor("#abcdef"))
    dialog.reject()
    assert editor.toPlainText() == source

    dialog = open_picker()
    dialog.accept()
    assert editor.toPlainText() == source and editor.document().isRedoAvailable()

    dialog = open_picker()
    editor.insertPlainText("X")
    edited = editor.toPlainText()
    dialog.setCurrentColor(QColor("#abcdef"))
    dialog.accept()
    assert editor.toPlainText() == edited
    window.hide()
