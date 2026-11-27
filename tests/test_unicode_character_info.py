"""Unicode文字情報の取得と表示対象を確認する。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import QApplication

from editor.unicode_character_info import character_at_cursor, inspect_character
from main import MainWindow


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance() or QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_unicode_character_attributes() -> None:
    circled = inspect_character("①")
    assert (circled.code_point, circled.name, circled.category, circled.nfkc) == (
        "U+2460", "CIRCLED DIGIT ONE", "No", "1"
    )
    assert inspect_character("😀").code_point == "U+1F600"
    assert inspect_character("\n").name is None
    with pytest.raises(ValueError):
        inspect_character("ab")


@pytest.mark.parametrize(
    ("source", "position", "expected"),
    [
        ("か\u3099", 2, "\u3099"),
        ("😀", 2, "😀"),
        ("😀", 1, "😀"),
        ("a\u00a0b", 1, "\u00a0"),
        ("a\u2028b", 1, "\u2028"),
        ("a\nb", 1, "\n"),
    ],
)
def test_code_point_at_utf16_position(
    app: QApplication, source: str, position: int, expected: str,
) -> None:
    document = QTextDocument()
    document.setPlainText(source)
    cursor = QTextCursor(document)
    cursor.setPosition(position)
    assert character_at_cursor(cursor) == expected


def test_dialog_uses_selection_then_cursor_without_editing(
    app: QApplication, tmp_path: Path
) -> None:
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "backup.json",
    )
    source = "A😀①\n"
    window.editor.setPlainText(source)
    cursor = window.editor.textCursor()
    cursor.setPosition(1)
    cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    assert window.unicode_character_info_action in window.view_menu.actions()
    window.unicode_character_info_action.trigger()
    dialog = window.unicode_character_info_dialog
    assert dialog is not None
    assert dialog.info is not None
    assert dialog.info.code_point == "U+1F600"
    assert dialog.from_selection
    assert window.editor.textCursor().selectedText() == "😀"

    cursor = window.editor.textCursor()
    cursor.clearSelection()
    cursor.setPosition(3)
    window.editor.setTextCursor(cursor)
    window.show_unicode_character_info_dialog()
    dialog = window.unicode_character_info_dialog
    assert dialog is not None and dialog.info is not None
    assert dialog.info.code_point == "U+2460"
    assert dialog.value_labels[4].text() == "'1'"
    assert not dialog.from_selection

    window.editor.moveCursor(QTextCursor.MoveOperation.End)
    window.show_unicode_character_info_dialog()
    dialog = window.unicode_character_info_dialog
    assert dialog is not None and dialog.info is not None
    assert dialog.info.code_point == "U+000A"
    window.set_language("en")
    assert dialog.windowTitle() == "Unicode Character Information"
    assert window.editor.toPlainText() == source


def test_empty_document_has_no_character(app: QApplication, tmp_path: Path) -> None:
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "backup.json",
    )
    window.show_unicode_character_info_dialog()
    dialog = window.unicode_character_info_dialog
    assert dialog is not None
    assert dialog.info is None
