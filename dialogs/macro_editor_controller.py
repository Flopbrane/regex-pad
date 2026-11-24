"""Coordinate macro editing, validation and safe file operations."""

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QFileDialog, QMessageBox

from app_logging import AppLogger
from dialogs.macro_editor_history import MacroEditorHistory
from dialogs.macro_editor_window import MacroEditorWindow
from macro.editor_bridge import MacroEditorBridge, MacroEditorInputError
from macro.editor_data_model import MacroEditorDocumentData, MacroEditorStepData
from macro.editor_session import MacroEditorSession
from macro.json_bridge import MacroJsonBridge
from macro.json_data_model import MacroJsonData
from macro.json_loader import MacroJsonLoadError
from macro.json_saver import MacroJsonSaveError
from macro.macro_manager import MacroManager, MacroValidationError
from macro.validation_types import (
    MacroDiagnostic,
    MacroDiagnosticSeverity,
    MacroValidationResult,
)


class MacroEditorController(QObject):
    execution_requested = Signal(object)

    def __init__(self, window: MacroEditorWindow, logger: AppLogger) -> None:
        super().__init__(window)
        self.window = window
        self.logger = logger
        self.session = MacroEditorSession()
        self._saved_document = deepcopy(self.session.document)
        self.undo_stack = QUndoStack(self)
        self.history = MacroEditorHistory(self.undo_stack, self._restore_history)
        self.undo_stack.canUndoChanged.connect(window.undo_action.setEnabled)
        self.undo_stack.canRedoChanged.connect(window.redo_action.setEnabled)
        self.undo_stack.indexChanged.connect(self._update_dirty)
        window.undo_requested.connect(self.undo_stack.undo)
        window.redo_requested.connect(self.undo_stack.redo)
        window.tree.step_reorder_requested.connect(self.reorder_step)
        self._loading = False
        window.confirm_close = self._confirm_close
        window.new_requested.connect(self.new_document)
        window.open_requested.connect(self.open_document)
        window.save_requested.connect(self.save)
        window.save_as_requested.connect(lambda: self.save(save_as=True))
        window.validate_requested.connect(self.validate)
        window.preview_requested.connect(self.preview)
        window.run_requested.connect(self.preview_execution)
        window.folder_requested.connect(self.choose_folder)
        window.step_add_requested.connect(self.add_step)
        window.step_duplicate_requested.connect(self.duplicate_step)
        window.step_delete_requested.connect(self.delete_step)
        window.step_move_requested.connect(self.move_step)
        window.tree.currentItemChanged.connect(self._selection_changed)
        window.step_editor.step_changed.connect(self._step_changed)
        window.macro_name.textChanged.connect(self._metadata_changed)
        window.description.textChanged.connect(self._metadata_changed)
        window.diagnostics.diagnostic_activated.connect(self.focus_diagnostic)
        self._render_document()

    def _text(self, name: str, **values: object) -> str:
        return self.window.translator.text("macro.editor." + name, **values)

    def _render_document(self, selected: int = 0) -> None:
        self._loading = True
        document = self.session.document
        self.window.macro_name.setText(document.macro_name)
        self.window.description.setText(document.description)
        self.window.version.setCurrentIndex(
            self.window.version.findData(document.format_version)
        )
        self.validate()
        self.window.render_tree(self.session, selected)
        self._selection_changed()
        self._loading = False

    def _selection_changed(self, *_args: object) -> None:
        self.history.break_merge()
        index = self.window.selected_step()
        valid = 0 <= index < len(self.session.document.steps)
        self.window.step_editor.setEnabled(valid)
        for name in ("duplicate", "delete", "up", "down"):
            self.window.step_buttons[name].setEnabled(valid)
        if valid:
            self.window.step_editor.set_step(self.session.document.steps[index])

    def _metadata_changed(self, *_args: object) -> None:
        if self._loading:
            return
        before = deepcopy(self.session.document)
        self.session.document.macro_name = self.window.macro_name.text()
        self.session.document.description = self.window.description.text()
        key = (
            "macro_name"
            if before.macro_name != self.session.document.macro_name
            else "description"
        )
        selected = self.window.selected_step()
        self.history.record(before, self.session.document, selected, selected, key)
        self._modified()

    def _step_changed(self, step: MacroEditorStepData) -> None:
        index = self.window.selected_step()
        if index >= 0 and not self._loading:
            before = deepcopy(self.session.document)
            changed = [
                name
                for name in step.__dataclass_fields__
                if getattr(before.steps[index], name) != getattr(step, name)
            ]
            self.session.document.steps[index] = step
            if step.operation == "numbered_heading":
                self.session.document.format_version = 3
                self.window.version.setCurrentIndex(self.window.version.findData(3))
            elif any((step.case_sensitive, step.whole_word, step.selected_only, step.visible_only)) and self.session.document.format_version < 2:
                self.session.document.format_version = 2
                self.window.version.setCurrentIndex(self.window.version.findData(2))
            key = f"step:{index}:{','.join(changed)}"
            self.history.record(before, self.session.document, index, index, key)
            self._modified()

    def _restore_history(
        self, document: MacroEditorDocumentData, selected: int
    ) -> None:
        self.session.document = document
        self.session.modified = document != self._saved_document
        self._render_document(selected)

    def _update_dirty(self, *_args: object) -> None:
        self.session.modified = self.session.document != self._saved_document
        self.window.update_status(self.session)

    def _reset_history(self) -> None:
        self._saved_document = deepcopy(self.session.document)
        self.history.break_merge()
        self.undo_stack.clear()
        self.undo_stack.setClean()
        self.session.modified = False

    def _modified(self) -> None:
        self.session.modified = self.session.document != self._saved_document
        self.window.render_tree(self.session, self.window.selected_step())
        # Disable saving until the current input has passed validation.
        self.window.editor_actions["save"].setEnabled(False)
        self.window.editor_actions["save_as"].setEnabled(False)
        self.window.editor_actions["run"].setEnabled(False)
        self.validate()

    def validate(self) -> MacroJsonData | None:
        try:
            prepared = self._manager().prepare_macro(
                MacroEditorBridge.to_json_model(self.session.document)
            )
            model = prepared.model
            self.session.validation_result = prepared.validation
        except MacroEditorInputError as error:
            self.session.validation_result = MacroValidationResult(
                (
                    MacroDiagnostic(
                        MacroDiagnosticSeverity.ERROR,
                        "editor_input",
                        "macro.editor.input_error",
                        error.step_index,
                        error.field_name,
                        {"error": str(error)},
                    ),
                )
            )
            model = None
            self.focus_diagnostic(error.step_index, error.field_name)
            self.window.step_editor.focus_field(error.field_name, str(error))
        except Exception as error:  # The Qt boundary must preserve the current edit.
            self.logger.exception(
                error,  # noqa: TRY401 - AppLogger requires the exception object.
                "Macro editor validation failed",
                action="macro_editor_validate",
            )
            self.session.validation_result = MacroValidationResult(
                (
                    MacroDiagnostic(
                        MacroDiagnosticSeverity.ERROR,
                        "editor_internal",
                        "macro.editor.input_error",
                        values={"error": str(error)},
                    ),
                )
            )
            model = None
        self.window.diagnostics.set_result(self.session.validation_result)
        self.window.render_tree(self.session, self.window.selected_step())
        return model

    def focus_diagnostic(self, index: int, field_name: str) -> None:
        if index < 0:
            widget = {
                "macro_name": self.window.macro_name,
                "format_version": self.window.version,
            }.get(field_name)
            if widget is not None:
                widget.setFocus()
            else:
                self.window.tree.setFocus()
            return
        root = self.window.tree.topLevelItem(0)
        if root is not None and 0 <= index < root.childCount():
            item = root.child(index)
            if item is not None:
                self.window.tree.setCurrentItem(item)
            self.window.step_editor.focus_field(field_name)

    def add_step(self) -> None:
        before = deepcopy(self.session.document)
        selected = self.window.selected_step()
        steps = self.session.document.steps
        position = self.window.selected_step() + 1
        number = len(steps) + 1
        while any(step.step_name == f"step_{number}" for step in steps):
            number += 1
        steps.insert(position, MacroEditorStepData(step_name=f"step_{number}"))
        self._structural_change(before, selected, position)

    def append_captured_step(self, step: MacroEditorStepData) -> None:
        """Add captured Find/Replace conditions to the open preset definition."""
        before = deepcopy(self.session.document)
        selected = self.window.selected_step()
        steps = self.session.document.steps
        captured = deepcopy(step)
        if (
            self.session.save_file_path is None
            and len(steps) == 1
            and steps[0] == MacroEditorStepData()
        ):
            captured.step_name = steps[0].step_name
            steps[0] = captured
            position = 0
        else:
            number = len(steps) + 1
            while any(existing.step_name == f"step_{number}" for existing in steps):
                number += 1
            captured.step_name = f"step_{number}"
            position = len(steps)
            steps.append(captured)
        self.session.document.format_version = 2
        self._structural_change(before, selected, position)

    def duplicate_step(self, index: int) -> None:
        steps = self.session.document.steps
        if not 0 <= index < len(steps):
            return
        before = deepcopy(self.session.document)
        selected = self.window.selected_step()
        step = deepcopy(steps[index])
        step.step_name += "_copy"
        while any(other.step_name == step.step_name for other in steps):
            step.step_name += "_copy"
        steps.insert(index + 1, step)
        self._structural_change(before, selected, index + 1)

    def delete_step(self, index: int) -> None:
        steps = self.session.document.steps
        if not 0 <= index < len(steps):
            return
        if (
            QMessageBox.question(
                self.window,
                self._text("delete"),
                self._text("confirm_delete"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        before = deepcopy(self.session.document)
        selected = self.window.selected_step()
        del steps[index]
        self._structural_change(before, selected, min(index, len(steps) - 1))

    def move_step(self, index: int, offset: int) -> None:
        self.reorder_step(index, index + offset)

    def reorder_step(self, index: int, destination: int) -> None:
        steps = self.session.document.steps
        if (
            0 <= index < len(steps)
            and 0 <= destination < len(steps)
            and index != destination
        ):
            before = deepcopy(self.session.document)
            selected = self.window.selected_step()
            steps.insert(destination, steps.pop(index))
            self._structural_change(before, selected, destination)

    def _structural_change(
        self, before: MacroEditorDocumentData, before_selection: int, selected: int
    ) -> None:
        self.history.record(before, self.session.document, before_selection, selected)
        self.session.modified = self.session.document != self._saved_document
        self._render_document(selected)

    def confirm_discard(self) -> bool:
        if not self.session.modified:
            return True
        answer = QMessageBox.warning(
            self.window,
            self._text("title"),
            self._text("unsaved"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def _confirm_close(self) -> bool:
        if not self.confirm_discard():
            return False
        if self.session.modified:
            # The main window reuses this modeless editor after it is hidden.
            # Discard must not revive unsaved edits/history on the next Show.
            self.session.document = deepcopy(self._saved_document)
            self._reset_history()
            self._render_document()
        return True

    def new_document(self) -> None:
        if self.confirm_discard():
            self.start_document(MacroEditorDocumentData())

    def start_document(
        self, document: MacroEditorDocumentData, *, needs_save: bool = False
    ) -> None:
        """Start an unsaved definition without writing a JSON file yet."""
        self.session = MacroEditorSession(
            document=deepcopy(document), macro_folder=self.session.macro_folder
        )
        self._reset_history()
        if needs_save:
            self._saved_document = MacroEditorDocumentData()
            self.session.modified = self.session.document != self._saved_document
        self._render_document()

    def open_document(self, load_file_path: Path | None = None) -> bool:
        if not self.confirm_discard():
            return False
        if load_file_path is None:
            name, _ = QFileDialog.getOpenFileName(
                self.window,
                self._text("open"),
                str(self.session.macro_folder),
                "JSON (*.json)",
            )
            if not name:
                return False
            load_file_path = Path(name)
        try:
            prepared = self._manager().load_macro(load_file_path)
            document = MacroEditorBridge.from_json_model(prepared.model)
        except (MacroJsonLoadError, ValueError, TypeError) as error:
            self._io_error(error)
            return False
        self.session = MacroEditorSession(
            document=document,
            load_file_path=load_file_path,
            save_file_path=load_file_path,
            macro_folder=self.session.macro_folder,
        )
        self._reset_history()
        self._render_document()
        return True

    def save(
        self, save_file_path: Path | None = None, *, save_as: bool = False
    ) -> bool:
        model = self.validate()
        if model is None or not self.session.validation_result.is_valid:
            QMessageBox.warning(
                self.window, self._text("save"), self._text("cannot_save")
            )
            return False
        destination = save_file_path or (
            None if save_as else self.session.save_file_path
        )
        if destination is None:
            name, _ = QFileDialog.getSaveFileName(
                self.window,
                self._text("save_as"),
                str(
                    self.session.save_file_path
                    or self.session.macro_folder / "macro.json"
                ),
                "JSON (*.json)",
            )
            if not name:
                return False
            destination = Path(name)
        try:
            destination = self._manager().save_macro(model, destination)
        except MacroValidationError as error:
            self.session.validation_result = error.validation
            self.window.diagnostics.set_result(error.validation)
            self.window.update_status(self.session)
            return False
        except MacroJsonSaveError as error:
            self._io_error(error)
            return False
        self.session.save_file_path = destination
        self._saved_document = deepcopy(self.session.document)
        self.history.break_merge()
        self.undo_stack.setClean()
        self.session.modified = False
        self.window.update_status(self.session)
        return True

    def choose_folder(self) -> None:
        name = QFileDialog.getExistingDirectory(
            self.window, self._text("folder"), str(self.session.macro_folder)
        )
        if name:
            self.session.macro_folder = Path(name)
            self.window.update_status(self.session)

    def _manager(self) -> MacroManager:
        return MacroManager(self.session.macro_folder)

    def preview_execution(self) -> None:
        model = self.validate()
        if model is not None and self.session.validation_result.is_valid:
            self.execution_requested.emit(model)

    def preview(self) -> None:
        import json

        from PySide6.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout

        model = self.validate()
        if model is None:
            return
        dialog = QDialog(self.window)
        dialog.setWindowTitle(self._text("preview"))
        dialog.resize(700, 550)
        layout = QVBoxLayout(dialog)
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(
            json.dumps(MacroJsonBridge.to_dict(model), ensure_ascii=False, indent=2)
        )
        layout.addWidget(editor)
        dialog.exec()
        dialog.deleteLater()

    def _io_error(self, error: Exception) -> None:
        self.logger.exception(
            error, "Macro editor file operation failed", action="macro_editor_io"
        )
        QMessageBox.critical(
            self.window, self._text("title"), self._text("io_error", error=str(error))
        )
