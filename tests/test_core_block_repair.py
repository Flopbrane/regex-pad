"""候補選択と、確認済みの文書だけに適用する条件を検証する。"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

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


def test_menu_preview_and_selected_apply_in_one_undo(app: QApplication, tmp_path: Path, monkeypatch) -> None:
    """メニューから修復をプレビューでき、選んだ修復を1回のUndoで元に戻せることを確認する。"""
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    source = f"{HEADING}\n{PARAGRAPH}\n{LIST}"
    window.editor.setPlainText(source)

    def review(dialog: CoreBlockRepairDialog):
        """修復候補を選択または取り消し、画面の応答をテストする。"""
        assert not dialog.apply_button.isEnabled()
        assert dialog.before.toPlainText() == HEADING.splitlines()[0]
        assert '"level":3' in dialog.after.toPlainText()
        assert window.editor.document().toRawText().replace("\u2029", "\n") == source
        dialog.list.item(0).setCheckState(Qt.CheckState.Checked)
        dialog.list.item(3).setCheckState(Qt.CheckState.Checked)
        assert dialog.apply_button.isEnabled()
        dialog.apply_button.click()
        return dialog.result()

    monkeypatch.setattr(CoreBlockRepairDialog, "exec", review)
    assert window.core_block_repair_action in window.search_menu.actions()
    window.core_block_repair_action.trigger()
    document = window.editor.document()
    expected = source.replace('"align":"left"', '"align":"left","level":3').replace("<ul>", '<ul class="wp-block-list">')
    assert document.toRawText().replace("\u2029", "\n") == expected
    window.editor.undo()
    assert document.toRawText().replace("\u2029", "\n") == source


@pytest.mark.parametrize("change", ["tab", "revision", "cancel"])
def test_original_target_is_rechecked(app: QApplication, tmp_path: Path, monkeypatch, change: str) -> None:
    """元の対象が再確認したになることを確認する。"""
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "backup.json",
        restore_unsaved_backup=False,
    )
    editor = window.editor
    editor.setPlainText(HEADING)
    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda _parent, _title, text: warnings.append(text))

    def review(dialog: CoreBlockRepairDialog):
        """修復候補を選択または取り消し、画面の応答をテストする。"""
        dialog.list.item(0).setCheckState(Qt.CheckState.Checked)
        if change == "revision":
            editor.insertPlainText(" ")
            editor.undo()  # Even when original text is restored, the preview is stale.
        elif change == "tab":
            window.new_file()
        return QDialog.DialogCode.Rejected if change == "cancel" else QDialog.DialogCode.Accepted

    monkeypatch.setattr(CoreBlockRepairDialog, "exec", review)
    window.show_core_block_repair()
    assert editor.toPlainText() == HEADING
    assert bool(warnings) == (change != "cancel")
