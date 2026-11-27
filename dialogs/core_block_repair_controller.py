"""確認した候補を元の文書にまとめて適用する。"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget
from shiboken6 import isValid

from dialogs.core_block_repair_dialog import CoreBlockRepairDialog
from editor.text_editor import TextEditor
from localization.translator import Translator
from search.core_block_repair import RepairCandidate, find_core_block_repairs


def _source(document: QTextDocument) -> str:
    """NBSPなどを保存したまま、Qt内部の段落境界を改行へ戻す。"""
    return document.toRawText().replace("\u2029", "\n")


def repair_core_blocks(
    editor: TextEditor, current_editor: Callable[[], TextEditor | None], target: str,
    translator: Translator, parent: QWidget,
) -> bool:
    """修復候補を確認し、元文書の状態が一致する場合に選択分を適用する。"""
    document = editor.document()
    revision = document.revision()
    source = _source(document)
    dialog = CoreBlockRepairDialog(find_core_block_repairs(source), target, translator, parent)
    try:
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        selected = dialog.selected_repairs()
    finally:
        dialog.deleteLater()
    if not selected:
        return False
    if (
        not isValid(editor) or not isValid(document) or current_editor() is not editor
        or editor.document() is not document or document.revision() != revision
        or editor.isReadOnly() or _source(document) != source
        or not apply_repairs(document, source, selected)
    ):
        QMessageBox.warning(parent, translator.text("core_repair.title"), translator.text("core_repair.stale"))
        return False
    return True


def apply_repairs(document: QTextDocument, source: str, repairs: list[RepairCandidate]) -> bool:
    """全候補の範囲を先に確認し、変更箇所を後ろから書き換える。"""
    if not document.isUndoRedoEnabled():
        return False
    cursor = QTextCursor(document)
    positions: list[tuple[int, int, str]] = []
    previous_end = qt_end = 0
    for repair in sorted(repairs, key=lambda item: item.start):
        if not (previous_end <= repair.start < repair.end <= len(source)):
            return False
        qt_start = qt_end + len(source[previous_end:repair.start].encode("utf-16-le")) // 2
        qt_end = qt_start + len(repair.before.encode("utf-16-le")) // 2
        if qt_end >= document.characterCount():
            return False
        cursor.setPosition(qt_start)
        cursor.setPosition(qt_end, QTextCursor.MoveMode.KeepAnchor)
        if cursor.selectedText().replace("\u2029", "\n") != repair.before:
            return False
        positions.append((qt_start, qt_end, repair.after))
        previous_end = repair.end
    if not positions:
        return False
    cursor.beginEditBlock()
    try:
        for start, end, replacement in reversed(positions):
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(replacement)
    finally:
        cursor.endEditBlock()
    return True
