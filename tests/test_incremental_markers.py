"""UTF-16編集位置の変換と検索マーカーの局所更新を検証する。"""

from __future__ import annotations

import os
import random
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from main import MainWindow
from search.incremental_markers import IndexedSource


def test_indexed_source_updates_unicode_and_newline_positions() -> None:
    """索引付きの原文がUnicodeと改行の位置を更新することを確認する。"""
    source = IndexedSource("😀 a\nb\n")
    assert source.replace(3, 1, "XY\n") == (2, 3, 2)
    assert source.text == "😀 XY\n\nb\n"
    assert source.python_position(6) == 5
    assert source.replace(6, 1, "") == (5, 6, -1)
    assert source.text == "😀 XY\nb\n"
    assert source.python_position(6) == 5


def test_indexed_source_matches_full_utf16_offsets_after_mixed_edits() -> None:
    """混在するが編集する後、索引付きの原文が全体のUTF-16の位置オフセットに一致することを確認する。"""
    random_source = random.Random(318)
    text = "a\n😀b\n終わり"
    index = IndexedSource(text)
    for _ in range(120):
        start = random_source.randrange(len(text) + 1)
        end = random_source.randrange(start, len(text) + 1)
        replacement = random_source.choice(("", "x", "😀", "\n", "漢\n"))
        qt_start = len(text[:start].encode("utf-16-le")) // 2
        qt_removed = len(text[start:end].encode("utf-16-le")) // 2
        assert index.replace(qt_start, qt_removed, replacement) == (
            start, end, len(replacement) - (end - start)
        )
        text = text[:start] + replacement + text[end:]
        assert index.text == text
        for position in range(len(text) + 1):
            expected_qt = len(text[:position].encode("utf-16-le")) // 2
            assert index.qt_position(position) == expected_qt
            assert index.python_position(expected_qt) == position


def test_literal_search_edit_rescans_only_changed_neighborhood(
    tmp_path: Path, monkeypatch,
) -> None:
    """単純文字列検索の編集がだけの変更された周辺を再走査することを確認する。"""
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    source = "😀 target\n" + "padding\n" * 1000
    window.editor.setPlainText(source)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("target")
    assert [match.text for match in window.editor.search_matches] == ["target"]

    scanned_lengths: list[int] = []
    original_find_all = window.search_engine.find_all

    def record_scan(text: str, *args, **kwargs):
        """検索の再走査へ渡された範囲を記録する。"""
        scanned_lengths.append(len(text))
        return original_find_all(text, *args, **kwargs)

    monkeypatch.setattr(window.search_engine, "find_all", record_scan)
    cursor = window.editor.textCursor()
    cursor.setPosition(window.editor.text_position_to_cursor_position(source.index("target") + 2))
    window.editor.setTextCursor(cursor)
    cursor.insertText("X")
    assert window.editor.search_matches == []
    assert scanned_lengths and max(scanned_lengths) < 100

    cursor = window.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText("target")
    current_text = window.editor.toPlainText()
    assert [match.text for match in window.editor.search_matches] == ["target"]
    assert all(
        current_text[match.start:match.end] == match.text
        for match in window.editor.search_matches
    )
    assert max(scanned_lengths) < 100


@pytest.mark.parametrize("whole_word", [False, True])
def test_literal_markers_match_full_search_after_mixed_edits(
    tmp_path: Path, whole_word: bool,
) -> None:
    """リテラルのマーカーの一致の全体の検索後の混在するが編集することを確認する。"""
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    window.editor.setPlainText("ab😀x\n" * 40)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("ab")
    dialog.whole_word_check_box.setChecked(whole_word)
    rng = random.Random(90)
    for iteration in range(50):
        before = window.editor.toPlainText()
        start = rng.randrange(len(before) + 1)
        end = rng.randrange(start, min(len(before), start + 4) + 1)
        replacement = rng.choice(("", "a", "b", "ab", "😀", "\n"))
        cursor = QTextCursor(window.editor.document())
        cursor.setPosition(len(before[:start].encode("utf-16-le")) // 2)
        cursor.setPosition(
            len(before[:end].encode("utf-16-le")) // 2,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.insertText(replacement)
        after = window.editor.toPlainText()
        expected = window.search_engine.find_all(
            after, "ab", dialog.current_search_options(), max_matches=2000
        )
        assert [(match.start, match.end) for match in window.editor.search_matches] == [
            (match.start, match.end) for match in expected
        ], (iteration, start, end, replacement, repr(after))
