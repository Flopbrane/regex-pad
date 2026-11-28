"""候補選択と、確認済みの文書だけに適用する条件を検証する。"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication

from dialogs.core_block_repair_controller import apply_repairs
from dialogs.core_block_repair_dialog import CoreBlockRepairDialog
from main import MainWindow
from search.core_block_repair import find_core_block_repairs
from search.html_typo_lint import lint_html_typos

HEADING = '<!-- wp:heading {"align":"left"} -->\n<h3 class="wp-block-heading">見出し😀</h3>\n<!-- /wp:heading -->'
PARAGRAPH = (
    '<!-- wp:paragraph {"fitText":true,"style":{"typography":{"fontWeight":"700"}}} -->\n'
    "<p class='custom' title='a\u00a0b'>段落</p>\n<!-- /wp:paragraph -->"
)
LIST = "<!-- wp:list -->\n<ul><li>項目</li></ul>\n<!-- /wp:list -->"
TABLE = "<!-- wp:table -->\n<figure><table><tbody><tr><td>セル</td></tr></tbody></table></figure>\n<!-- /wp:table -->"


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance() or QApplication([])
    assert isinstance(application, QApplication)
    return application


def test_verified_json_class_and_style_candidates() -> None:
    """確認済みのJSONのクラスとスタイルの候補を確認する。"""
    source = f"{HEADING}\n{PARAGRAPH}\n{LIST}\n{TABLE}"
    heading, paragraph_class, paragraph_style, listing, table = find_core_block_repairs(source)
    assert heading.after == '<!-- wp:heading {"align":"left","level":3} -->'
    assert paragraph_class.preview_after == "<p class='custom has-fit-text' title='a\u00a0b'>"
    assert paragraph_style.preview_after == '<p class=\'custom\' title=\'a\u00a0b\' style="font-weight:700">'
    assert listing.preview_after == '<ul class="wp-block-list">'
    assert table.preview_after == '<figure class="wp-block-table">'
    ordered = (heading, paragraph_class, paragraph_style, listing, table)
    for candidate in ordered:
        assert candidate.before == source[candidate.start:candidate.end]
    result = source
    for candidate in reversed(ordered):
        result = result[:candidate.start] + candidate.after + result[candidate.end:]
    assert not find_core_block_repairs(result)
    assert not [item for item in lint_html_typos(result) if item.severity == "error"]


@pytest.mark.parametrize("source", [
    HEADING.replace('"align":"left"', '"level":4'),
    HEADING.replace('"align":"left"', '"align":"left","align":"right"'),
    HEADING.replace('"align":"left"', '"unknown":NaN'),
    HEADING.replace("</h3>", "</h2>"),
    HEADING.replace("<!-- /wp:heading -->", "<!-- /wp:paragraph -->"),
    f"<!-- wp:html -->\n{HEADING}\n<!-- /wp:html -->",
    f"<textarea>{HEADING}</textarea>",
    f"<![unknown]>\n{HEADING}",
    TABLE.replace("</figure>", "</figure><figure>別要素</figure>"),
    PARAGRAPH.replace("'custom'", "'custom has-fit-text' style='font:normal 16px serif'"),
])
def test_uncertain_or_conflicting_sources_have_no_candidates(source: str) -> None:
    """根拠が曖昧なまたは競合するの入力原稿がなしの候補を持つことを確認する。"""
    assert find_core_block_repairs(source) == []


@pytest.mark.parametrize(("fixture", "removed", "reason", "expected"), [
    ("group_block_decorated_correct", '"top":"var:preset|spacing|20",', "reverse_style", '"top":"var:preset|spacing|20"'),
    ("paragraph_block_decorated_correct", '"top":{"width":"4px"},', "reverse_style", '"top":{"width":"4px"}'),
    ("button_block_decorated_correct", ' style="border-width:4px"', "style", 'style="border-width:4px"'),
    ("button_block_decorated_correct", " wp-element-button", "class", "wp-element-button"),
    ("accordion_block_border_correct", 'type="button" ', "type", 'type="button"'),
])
def test_saved_examples_support_new_candidates(fixture: str, removed: str, reason: str, expected: str) -> None:
    """保存例の片側だけを変更し、根拠のある候補が一つ出ることを確認する。"""
    original = Path(__file__).with_name(f"{fixture}.wp_html").read_text(encoding="utf-8")
    assert not find_core_block_repairs(original)
    assert removed in original
    source = original.replace(removed, "", 1)
    candidate, = find_core_block_repairs(source)
    assert candidate.reason == reason
    assert expected in (candidate.preview_after or candidate.after)
    repaired = source[:candidate.start] + candidate.after + source[candidate.end:]
    assert not find_core_block_repairs(repaired)
    assert not [item for item in lint_html_typos(repaired) if item.severity == "error"]


def test_group_empty_style_candidate_only_removes_attribute() -> None:
    """空のstyleだけを削除し、正常な保存例と同じソースへ戻す。"""
    original = Path(__file__).with_name("group_block_flex_nowrap_empty_style_broken.wp_html").read_text(encoding="utf-8")
    candidate, = find_core_block_repairs(original)
    assert candidate.reason == "empty_style"
    assert candidate.before == ' style=""'
    assert candidate.after == ""
    repaired = original[:candidate.start] + candidate.after + original[candidate.end:]
    assert not find_core_block_repairs(repaired)
    assert not [item for item in lint_html_typos(repaired) if item.severity == "error"]


@pytest.mark.parametrize("source", [
    (
        '<!-- wp:paragraph {"style":{"border":{"top":{"width":"5px"}}}} -->\n'
        '<p style="border-top-width:4px;border-right-width:2px">本文</p>\n<!-- /wp:paragraph -->'
    ),
    '<!-- wp:paragraph -->\n<p style="border-width:1px;border-width:2px">本文</p>\n<!-- /wp:paragraph -->',
    '<!-- wp:paragraph {"style":null} -->\n<p style="border-width:1px">本文</p>\n<!-- /wp:paragraph -->',
    '<!-- wp:paragraph -->\n<p style="border:2px solid red;border-left-width:1px">本文</p>\n<!-- /wp:paragraph -->',
    '<!-- wp:paragraph {"textColor":"accent-1"} -->\n<p class="has-accent-2-color">本文</p>\n<!-- /wp:paragraph -->',
])
def test_existing_conflicting_or_ambiguous_attributes_are_preserved(source: str) -> None:
    """同一系統の競合や不明な属性から書き換え候補を作らないことを確認する。"""
    assert not find_core_block_repairs(source)


def test_overlapping_or_stale_ranges_apply_nothing(app: QApplication) -> None:
    """重複するまたは古くなったの範囲の適用の何もないことを確認する。"""
    document = QTextDocument()
    document.setPlainText(HEADING + "\n" + LIST)
    source = document.toPlainText()
    first, second = find_core_block_repairs(source)
    assert not apply_repairs(document, source, [first, first])
    assert not apply_repairs(document, source, [first, replace(second, before="<ol>")])
    assert document.toPlainText() == source
    assert not document.isUndoAvailable()


def test_menu_preview_and_selected_apply_in_one_undo(app: QApplication, tmp_path: Path) -> None:
    """メニューから修復をプレビューでき、選んだ修復を1回のUndoで元に戻せることを確認する。"""
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    source = f"{HEADING}\n{PARAGRAPH}\n{LIST}"
    window.editor.setPlainText(source)

    assert window.core_block_repair_action in window.search_menu.actions()
    window.core_block_repair_action.trigger()
    dialog = window.findChild(CoreBlockRepairDialog)
    assert dialog is not None and dialog.isVisible() and not dialog.isModal()
    assert not dialog.apply_button.isEnabled()
    assert dialog.before.toPlainText() == HEADING.splitlines()[0]
    assert '"level":3' in dialog.after.toPlainText()
    document = window.editor.document()
    assert document.toRawText().replace("\u2029", "\n") == source
    dialog.list.item(0).setCheckState(Qt.CheckState.Checked)
    dialog.list.item(3).setCheckState(Qt.CheckState.Checked)
    assert dialog.apply_button.isEnabled()
    dialog.apply_button.click()
    expected = source.replace('"align":"left"', '"align":"left","level":3').replace("<ul>", '<ul class="wp-block-list">')
    assert document.toRawText().replace("\u2029", "\n") == expected
    assert dialog.isVisible()
    assert [item.reason for item in dialog.candidates] == ["class", "style"]
    assert not dialog.selected_repairs()
    assert not dialog.apply_button.isEnabled()
    window.editor.undo()
    assert document.toRawText().replace("\u2029", "\n") == source
    assert not dialog.list.isEnabled()


@pytest.mark.parametrize("change", ["tab", "revision"])
def test_original_target_is_rechecked(app: QApplication, tmp_path: Path, change: str) -> None:
    """元の対象が再確認したになることを確認する。"""
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    editor = window.editor
    editor.setPlainText(HEADING)
    window.show_core_block_repair()
    dialog = window.findChild(CoreBlockRepairDialog)
    assert dialog is not None
    dialog.list.item(0).setCheckState(Qt.CheckState.Checked)
    assert dialog.apply_button.isEnabled()
    if change == "revision":
        editor.insertPlainText(" ")
        editor.undo()
    else:
        window.new_file()
        assert not dialog.refresh_button.isEnabled()
        window.tab_widget.setCurrentIndex(0)
    assert not dialog.apply_button.isEnabled()
    assert not dialog.list.isEnabled()
    assert not dialog.before.toPlainText()
    assert editor.toPlainText() == HEADING
    assert dialog.refresh_button.isEnabled()
    dialog.refresh_button.click()
    assert dialog.list.isEnabled()
    assert not dialog.selected_repairs()
    dialog.list.item(0).setCheckState(Qt.CheckState.Checked)
    dialog.apply_button.click()
    assert '"level":3' in editor.toPlainText()
    assert not dialog.candidates


def test_refresh_after_apply_discovers_newly_eligible_heading(app: QApplication, tmp_path: Path) -> None:
    """クラス補完後に初めて成立する候補を、その場で再計算する。"""
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    editor = window.editor
    editor.setPlainText(HEADING.replace(' class="wp-block-heading"', ""))
    window.show_core_block_repair()
    dialog = window.findChild(CoreBlockRepairDialog)
    assert dialog is not None
    assert [item.reason for item in dialog.candidates] == ["class"]
    dialog.list.item(0).setCheckState(Qt.CheckState.Checked)
    dialog.apply_button.click()
    assert [item.reason for item in dialog.candidates] == ["level"]
    assert not dialog.apply_button.isEnabled()
    assert '"level":3' in dialog.after.toPlainText()
    window.new_file()
    window.tab_widget.removeTab(0)
    editor.deleteLater()
    app.processEvents()
    assert not dialog.apply_button.isEnabled()
    assert not dialog.refresh_button.isEnabled()
