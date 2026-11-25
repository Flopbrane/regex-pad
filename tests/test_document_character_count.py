"""Verify local character counting across Qt edits and Unicode text."""

from __future__ import annotations

import random
from pathlib import Path

import pytest
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from editor.document_character_count import DocumentCharacterCount
from main import MainWindow


def _qt_position(text: str, python_position: int) -> int:
    return len(text[:python_position].encode("utf-16-le")) // 2


def test_character_count_tracks_multiline_unicode_edits_and_undo() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    editor = QPlainTextEdit()
    document = editor.document()
    document.setPlainText("あ😀\nsecond\n")
    counter = DocumentCharacterCount(document)
    document.contentsChange.connect(counter.apply_change)
    assert counter.count == len(document.toPlainText())

    randomizer = random.Random(29)
    for iteration in range(80):
        before = document.toPlainText()
        start = randomizer.randrange(len(before) + 1)
        end = randomizer.randrange(start, min(start + 3, len(before)) + 1)
        replacement = randomizer.choice(("", "x", "😀", "\n", "雨\n鳥"))
        cursor = QTextCursor(document)
        cursor.setPosition(_qt_position(before, start))
        cursor.setPosition(_qt_position(before, end), QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replacement)
        assert counter.count == len(document.toPlainText()), (
            iteration, repr(before), start, end, repr(replacement),
            counter.text_lengths, [document.findBlockByNumber(i).text() for i in range(document.blockCount())],
        )
        assert len(counter.text_lengths) == document.blockCount()

    while document.isUndoAvailable():
        document.undo()
        assert counter.count == len(document.toPlainText())

    document.setPlainText("replacement😀\nlast")
    assert counter.count == len(document.toPlainText())


def test_typing_updates_count_and_draft_title_without_full_text_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    assert app is not None
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("first😀\nsecond")

    def fail_full_read() -> str:
        raise AssertionError("full document read on typing")

    monkeypatch.setattr(window.editor, "toPlainText", fail_full_read)
    cursor = window.editor.textCursor()
    cursor.setPosition(0)
    cursor.insertText("雨")

    assert window._document_character_counts[window.editor].count == len("雨first😀\nsecond")
    assert window.tab_widget.tabText(0) == "*雨first😀"
    assert window.statusBar().currentMessage() == window.translator.text(
        "status.position", line=1, column=2, characters=len("雨first😀\nsecond"),
    )
