"""確認した候補を元の文書にまとめて適用する。"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, Slot
from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import QTabWidget, QWidget
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
    translator: Translator, parent: QWidget, tabs: QTabWidget,
) -> None:
    """元の文書に結び付いた修復画面を開く。"""
    for previous in parent.findChildren(CoreBlockRepairDialog):
        previous.close()
    dialog = CoreBlockRepairDialog([], target, translator, parent)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    _RepairSession(dialog, editor, current_editor, tabs)
    dialog.show()


class _RepairSession(QObject):
    """画面の寿命内で元文書のスナップショットと修復操作を管理する。"""

    def __init__(
        self, dialog: CoreBlockRepairDialog, editor: TextEditor,
        current_editor: Callable[[], TextEditor | None], tabs: QTabWidget,
    ) -> None:
        """元タブと文書の変更を監視し、最初の候補を表示する。"""
        super().__init__(dialog)
        self.dialog = dialog
        self.editor = editor
        self.current_editor = current_editor
        self.document = editor.document()
        self.revision = -1
        self.source = ""
        self.document.contentsChanged.connect(self.invalidate)
        self.document.destroyed.connect(self.invalidate)
        editor.destroyed.connect(self.invalidate)
        tabs.currentChanged.connect(self.invalidate)
        dialog.refresh_button.clicked.connect(self.refresh)
        dialog.apply_button.clicked.connect(self.apply)
        self.refresh()

    def _target_available(self) -> bool:
        """元タブが表示され、同じ編集可能な文書が残っているか確認する。"""
        return (
            isValid(self.editor) and isValid(self.document)
            and self.current_editor() is self.editor and self.editor.document() is self.document
            and not self.editor.isReadOnly() and self.document.isUndoRedoEnabled()
        )

    @Slot()
    def invalidate(self) -> None:
        """本文やタブが変わった時点で、古い候補の適用を止める。"""
        self.dialog.invalidate(self._target_available())

    @Slot()
    def refresh(self) -> None:
        """利用者の操作を受けて候補を更新する。"""
        self._refresh()

    def _refresh(self, applied: bool = False) -> None:
        """元の本文を取り直し、修復候補を再計算する。"""
        if not self._target_available():
            self.invalidate()
            return
        self.revision = self.document.revision()
        self.source = _source(self.document)
        self.dialog.set_candidates(find_core_block_repairs(self.source), applied)

    @Slot()
    def apply(self) -> None:
        """選択した候補を1回のUndoで適用し、残る候補を更新する。"""
        if not self.dialog.fresh:
            return
        selected = self.dialog.selected_repairs()
        if not selected:
            return
        if (
            not self._target_available() or self.document.revision() != self.revision
            or _source(self.document) != self.source
            or not apply_repairs(self.document, self.source, selected)
        ):
            self.invalidate()
            return
        self._refresh(applied=True)


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
