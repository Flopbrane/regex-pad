"""Exercise local WordPress pair checks without a full lint on typing."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

import main as main_module
from main import MainWindow


def _replace_range(window: MainWindow, start: int, end: int, replacement: str) -> None:
    cursor = QTextCursor(window.editor.document())
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    cursor.insertText(replacement)


def test_broken_first_pair_does_not_adopt_later_sibling(
    tmp_path: Path, monkeypatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    source = (
        "<!-- wp:paragraph -->\n<p>first</p>\n<!-- /wp:paragraph -->\n"
        "<!-- wp:paragraph -->\n<p>second</p>\n<!-- /wp:paragraph -->"
    )
    window.editor.setPlainText(source)
    index = window._structure_indices[window.editor]
    assert len(index.pairs) == 2
    assert window.editor.grammar_issue_lines == []
    monkeypatch.setattr(
        window, "_lint_document",
        lambda _source: (_ for _ in ()).throw(AssertionError("full lint on typing")),
    )

    first_close = "<!-- /wp:paragraph -->"
    start = source.index(first_close)
    _replace_range(window, start, start + len(first_close), "")
    assert index.pairs[0].broken
    assert not index.pairs[1].broken
    assert window.editor.grammar_issue_lines == [1]

    _replace_range(window, start, start, first_close)
    assert not index.pairs[0].broken
    assert window.editor.grammar_issue_lines == []


def test_typing_inside_paragraph_keeps_pair_valid(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    source = "<!-- wp:paragraph -->\n<p>text</p>\n<!-- /wp:paragraph -->"
    window.editor.setPlainText(source)
    _replace_range(window, source.index("text") + 2, source.index("text") + 2, "X")
    assert window.editor.grammar_issue_lines == []


def test_typing_deleted_closing_comment_recovers_pair(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    source = "<!-- wp:paragraph -->\n<p>text</p>\n<!-- /wp:paragraph -->"
    window.editor.setPlainText(source)
    closing = "<!-- /wp:paragraph -->"
    start = source.index(closing)
    _replace_range(window, start, start + len(closing), "")
    assert window.editor.grammar_issue_lines == [1]
    for character in closing:
        _replace_range(window, start, start, character)
        start += 1
    assert window.editor.grammar_issue_lines == []


def test_html_lint_checks_only_changed_core_block(tmp_path: Path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    block = "<!-- wp:paragraph -->\n<p>text</p>\n<!-- /wp:paragraph -->\n"
    source = block * 100
    window.editor.setPlainText(source)
    scanned_lengths: list[int] = []
    original_lint = main_module.lint_html_typos

    def record_lint(text: str):
        scanned_lengths.append(len(text))
        return original_lint(text)

    monkeypatch.setattr(main_module, "lint_html_typos", record_lint)
    start = source.index("</p>")
    _replace_range(window, start, start + len("</p>"), "</span>")
    assert window.editor.grammar_issue_lines
    assert scanned_lengths and max(scanned_lengths) < len(block) * 2


def test_pasted_unclosed_block_is_marked_immediately(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    window.editor.setPlainText("<!-- wp:paragraph -->\n<p>text</p>")
    assert window.editor.grammar_issue_lines == [1]


def test_backup_timer_stops_when_window_closes(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    assert window.auto_save_timer.isActive()
    assert window.close()
    assert not window.auto_save_timer.isActive()


def test_self_closing_wordpress_block_keeps_its_shape(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    source = '<!-- wp:spacer {"height":"20px"} /-->'
    window.editor.setPlainText(source)
    _replace_range(window, source.index("20px"), source.index("20px") + 2, "30")
    assert window.editor.grammar_issue_lines == []
