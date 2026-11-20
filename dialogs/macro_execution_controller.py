"""Bind one preview to its originating editor/document and apply in one Undo."""

from collections.abc import Callable

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget
from shiboken6 import isValid

from app_logging import AppLogger
from dialogs.macro_run_preview_dialog import MacroRunPreviewDialog
from editor.text_editor import TextEditor
from localization.translator import Translator
from macro.json_data_model import MacroJsonData
from macro.macro_manager import MacroManager
from macro.macro_preview import MacroPreview


class MacroExecutionController:
    def __init__(
        self,
        translator: Translator,
        logger: AppLogger,
        current_editor: Callable[[], TextEditor | None],
        editor_exists: Callable[[TextEditor], bool],
        target_label: Callable[[TextEditor], str],
        parent: QWidget,
    ) -> None:
        self.translator = translator
        self.logger = logger
        self.current_editor = current_editor
        self.editor_exists = editor_exists
        self.target_label = target_label
        self.parent = parent
        self.manager = MacroManager()

    def preview_and_apply(self, model: MacroJsonData) -> bool:
        editor = self.current_editor()
        if editor is None or not isValid(editor) or not self.editor_exists(editor):
            return False
        document = editor.document()
        revision = document.revision()
        source_text = editor.toPlainText()
        try:
            preview = self.manager.preview_macro(model, source_text)
        except Exception as error:  # noqa: BLE001 - Preserve the document at the Qt boundary.
            self._unexpected(error)
            return False
        dialog = MacroRunPreviewDialog(
            preview, self.translator, self.target_label(editor), self.parent
        )
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        dialog.deleteLater()
        if not accepted:
            return False
        if (
            not isValid(editor)
            or not isValid(document)
            or not self.editor_exists(editor)
            or self.current_editor() is not editor
            or editor.document() is not document
            or document.revision() != revision
            or editor.toPlainText() != source_text
            or editor.isReadOnly()
        ):
            QMessageBox.warning(
                self.parent,
                self.translator.text("macro.run.title"),
                self.translator.text("macro.run.stale"),
            )
            return False
        return self.apply_preview(editor, preview)

    @staticmethod
    def apply_preview(editor: TextEditor, preview: MacroPreview) -> bool:
        if (
            not preview.can_apply
            or editor.toPlainText() != preview.result.original_text
            or editor.isReadOnly()
        ):
            return False
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(preview.result.text)
        cursor.endEditBlock()
        editor.setTextCursor(cursor)
        return True

    def _unexpected(self, error: Exception) -> None:
        self.logger.exception(error, "Macro execution failed", action="macro_run")
        QMessageBox.critical(
            self.parent,
            self.translator.text("macro.run.title"),
            self.translator.text("macro.run.failed", error=str(error)),
        )
