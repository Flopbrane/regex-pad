"""入力中に全文検査をせず、WordPressのブロック対応を局所的に検査できることを確認する。"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

import main as main_module
from main import MainWindow


def _replace_range(window: MainWindow, start: int, end: int, replacement: str) -> None:
    """指定されたQtの範囲をテスト用の文字列で置き換える。"""
    cursor = QTextCursor(window.editor.document())
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    cursor.insertText(replacement)


def test_broken_first_pair_does_not_adopt_later_sibling(
    tmp_path: Path, monkeypatch,
) -> None:
    """壊れたの最初の対が後続の兄弟要素を誤って採用しないことを確認する。"""
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
    """入力中内の段落が対の正しいを保持することを確認する。"""
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


def test_moving_heading_tail_into_paragraph_removes_stale_red_band(tmp_path: Path, monkeypatch) -> None:
    """移動の見出しの後半への段落が古くなったの赤帯を取り除くことを確認する。"""
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    heading = (
        '<!-- wp:heading -->\n<h2 class="wp-block-heading">'
        "小見出しの前半 後半の文</h2>\n<!-- /wp:heading -->"
    )
    next_heading = '\n<!-- wp:heading -->\n<h2 class="wp-block-heading">次の見出し</h2>\n<!-- /wp:heading -->'
    window.editor.setPlainText(heading + next_heading)
    new_ending = (
        '</h2>\n<!-- /wp:heading -->\n\n<!-- wp:paragraph -->\n'
        '<p><span style="font-size: 26px;">後半の文</span></p>\n<!-- /wp:paragraph -->'
    )
    original_lint = window._lint_document
    monkeypatch.setattr(
        window, "_lint_document",
        lambda _source: (_ for _ in ()).throw(AssertionError("full lint on typing")),
    )
    start = heading.index(" 後半")
    _replace_range(window, start, len(heading), new_ending)
    edited = window.editor.toPlainText()
    assert edited == heading[:start] + new_ending + next_heading
    assert window.editor.grammar_issue_lines == []
    index = window._structure_indices[window.editor]
    assert index.pairs[0].close_start == edited.index("<!-- /wp:heading -->")
    assert index.pairs[1].close_start == edited.rindex("<!-- /wp:heading -->")
    assert original_lint(edited) == []
    window.editor.undo()
    assert window.editor.toPlainText() == heading + next_heading
    assert window.editor.grammar_issue_lines == []


def test_typing_deleted_closing_comment_recovers_pair(tmp_path: Path) -> None:
    """入力中の削除された終了のコメントの復旧するの対を確認する。"""
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
    """HTMLの文法チェックがだけの変更されたコアブロックを検査することを確認する。"""
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
        """文法チェックされた断片の長さを記録し、検査を続ける。"""
        scanned_lengths.append(len(text))
        return original_lint(text)

    monkeypatch.setattr(main_module, "lint_html_typos", record_lint)
    start = source.index("</p>")
    _replace_range(window, start, start + len("</p>"), "</span>")
    assert window.editor.grammar_issue_lines
    assert scanned_lengths and max(scanned_lengths) < len(block) * 2


def test_pasted_unclosed_block_is_marked_immediately(tmp_path: Path) -> None:
    """貼り付けられたの閉じられていないのブロックがマーカー付きのすぐにになることを確認する。"""
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
    """ウインドウが閉じるの場合、バックアップのタイマーが停止することを確認する。"""
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
    """自己終了のWordPressのブロックがその形を保持することを確認する。"""
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


def test_empty_color_value_waits_for_explicit_full_check(tmp_path: Path) -> None:
    """空の色指定は、明示的に全文を検査したときに診断されることを確認する。"""
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    source = (
        '<!-- wp:paragraph -->\n'
        '<p><mark style="color:#333333;">本文</mark></p>\n'
        '<!-- /wp:paragraph -->'
    )
    window.editor.setPlainText(source)
    start = source.index("#333333")
    _replace_range(window, start, start + len("#333333"), " ")
    assert window.editor.grammar_issue_lines == []
    assert any(
        issue.message_key == "css_lint.empty_value"
        for issue in window._lint_document(window.editor.toPlainText())
    )
