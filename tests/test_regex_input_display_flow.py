"""正規表現の入力欄の表示の操作手順を検証する。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from dialogs.regex_input_edit import REGEX_TOKEN_COLOR
from main import MainWindow


def _process_delayed_ui_events(delay_ms: int = 75) -> None:
    """テスト対象の遅延処理が実行されるまでQtイベントを処理する。"""
    loop = QEventLoop()
    QTimer.singleShot(delay_ms, loop.quit)
    loop.exec()
    QApplication.processEvents()


def _highlighted_fragments(edit) -> list[str]:
    """入力欄で色付けされた断片を取得する。"""
    edit.highlighter.rehighlight()
    QApplication.processEvents()
    block = edit.document().firstBlock()
    text = block.text()
    return [
        text[format_range.start : format_range.start + format_range.length]
        for format_range in block.layout().formats()
        if format_range.format.foreground().color() == REGEX_TOKEN_COLOR
    ]


def test_replace_all_then_second_regex_input_keeps_display_and_regex_colors(
    tmp_path: Path,
) -> None:
    """全置換の続いての2番目の正規表現の入力欄が表示と正規表現の色を保持することを確認する。"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    assert isinstance(app, QApplication)

    load_file_path = tmp_path / "replace_flow_sample.txt"
    load_file_path.write_text("line-001\nline-002\n", encoding="utf-8")

    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText(load_file_path.read_text(encoding="utf-8"))
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None

    dialog = window.find_replace_dialog
    dialog.regular_expression_check_box.setChecked(True)
    dialog.find_text_edit.setText(r"line-(\d+)")
    dialog.replace_text_edit.setText(r"item-\1")

    assert dialog.find_text_edit.text() == r"line-(\d+)"
    assert dialog.replace_text_edit.text() == r"item-\1"
    assert r"(\d+)" in _highlighted_fragments(dialog.find_text_edit)
    assert r"\1" in _highlighted_fragments(dialog.replace_text_edit)

    dialog.replace_all_button.click()
    _process_delayed_ui_events()

    assert window.editor.toPlainText() == "item-001\nitem-002\n"
    assert dialog.preview_table.rowCount() == 0
    assert dialog.find_text_edit.hasFocus()
    assert dialog.find_text_edit.text() == r"line-(\d+)"
    assert dialog.replace_text_edit.text() == r"item-\1"
    assert not dialog.find_text_edit.hasSelectedText()
    assert not dialog.replace_text_edit.hasSelectedText()

    dialog.find_text_edit.setText(r"\nitem-\d+")

    assert dialog.find_text_edit.text() == r"\nitem-\d+"

    dialog.replace_text_edit.setFocus()
    QApplication.processEvents()

    assert dialog.find_text_edit.text() == r"\nitem-\d+"
    assert not dialog.find_text_edit.hasSelectedText()

    dialog.find_text_edit.setFocus()
    QApplication.processEvents()

    assert dialog.find_text_edit.text() == r"\nitem-\d+"
    assert dialog.find_text_edit.toPlainText() == r"\nitem-\d+"
    assert dialog.find_text_edit.highlighter.enabled is True
    highlighted = _highlighted_fragments(dialog.find_text_edit)
    assert r"\n" in highlighted
    assert r"\d+" in highlighted

    dialog.replace_text_edit.setText(r"\nrow")
    dialog.replace_all_button.click()
    _process_delayed_ui_events()

    assert window.editor.toPlainText() == "item-001\nrow\n"
    assert dialog.find_text_edit.hasFocus()
    assert dialog.find_text_edit.text() == r"\nitem-\d+"
    assert dialog.replace_text_edit.text() == r"\nrow"
    assert not dialog.find_text_edit.hasSelectedText()
    assert not dialog.replace_text_edit.hasSelectedText()
