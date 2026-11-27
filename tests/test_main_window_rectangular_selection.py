"""メインウインドウの矩形選択を検証する。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from main import MainWindow

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_main_window_copies_selected_text_as_rectangle(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """メインウインドウから選択範囲を矩形としてコピーできることを確認する。"""
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
        restore_unsaved_backup=False,
    )
    window.editor.setPlainText("abcd\nwxyz\n1234")
    cursor = window.editor.textCursor()
    cursor.setPosition(window.editor.text_position_to_cursor_position(1))
    cursor.setPosition(
        window.editor.text_position_to_cursor_position(13),
        QTextCursor.MoveMode.KeepAnchor,
    )
    window.editor.setTextCursor(cursor)

    window.copy_rectangular_selection()

    assert app.clipboard().text() == "bc\nxy\n23"
