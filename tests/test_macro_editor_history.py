"""マクロ定義全体の履歴とQtのドラッグ操作について回帰を確認する。"""

from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QMenu,
    QMessageBox,
)

from app_logging import AppLogger
from dialogs.macro_editor_controller import MacroEditorController
from dialogs.macro_editor_window import MacroEditorWindow
from dialogs.macro_run_preview_dialog import MacroRunPreviewDialog
from dialogs.regex_input_edit import RegexInputEdit
from localization.translator import Translator
from macro.editor_bridge import MacroEditorBridge
from macro.editor_data_model import MacroEditorDocumentData, MacroEditorStepData
from macro.json_loader import MacroJsonLoader
from macro.json_saver import MacroJsonSaver


@pytest.fixture
def editor(tmp_path, monkeypatch):
    """テストで操作するエディターを用意する。"""
    app = QApplication.instance() or QApplication([])
    model = MacroEditorDocumentData(
        macro_name="history",
        steps=[
            MacroEditorStepData(
                step_name="first", search_text="a", replacement_text="b"
            ),
            MacroEditorStepData(
                step_name="second", search_text="b", replacement_text="c"
            ),
            MacroEditorStepData(step_name="third", enabled=False),
        ],
    )
    destination = MacroJsonSaver().save(
        MacroEditorBridge.to_json_model(model), tmp_path / "macro.json"
    )
    window = MacroEditorWindow(Translator(Path("resources"), "ja"))
    controller = MacroEditorController(window, AppLogger(tmp_path / "logs"))
    assert controller.open_document(destination)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes
    )
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args: QMessageBox.StandardButton.Discard
    )
    window.show()
    app.processEvents()
    yield window, controller
    controller.session.modified = False
    window.close()
    window.deleteLater()
    app.processEvents()


@pytest.mark.parametrize(
    "operation", ["add", "duplicate", "delete", "up", "down", "drag"]
)
def test_each_structural_operation_undoes_and_redoes_exact_document(editor, operation):
    """各構造編集のUndoとRedoでプリセット定義が正確に再現されることを確認する。"""
    window, controller = editor
    controller.focus_diagnostic(1, "step_name")
    before = deepcopy(controller.session.document)
    if operation == "drag":
        assert window.tree.request_reorder(1, 0)
    else:
        window.step_buttons[operation].click()
    after = deepcopy(controller.session.document)
    selected_after = window.selected_step()
    assert before != after and controller.session.modified
    window.undo_action.trigger()
    assert controller.session.document == before
    assert window.selected_step() == 1
    assert not controller.session.modified
    window.redo_action.trigger()
    assert controller.session.document == after
    assert window.selected_step() == selected_after
    assert controller.session.modified


@pytest.mark.parametrize(
    "field,value",
    [
        ("step_name", "renamed"),
        ("search_text", "["),
        ("replacement_text", " \\g<1>\nＡ "),
        ("exclusion_text", "raw exclusion"),
        ("regular_expression", True),
        ("enabled", False),
        ("exclusion_enabled", True),
        ("replacement_enabled", False),
        ("unicode_normalize", True),
        ("append_dot_to_circled_number", True),
    ],
)
def test_step_field_history_retains_exact_text_and_nullable_controls(
    editor, field, value
):
    """手順の項目の履歴が完全に同じ文字列とnullを指定できるの入力部品を保持することを確認する。"""
    window, controller = editor
    before = deepcopy(controller.session.document)
    widget = window.step_editor.fields[field]
    if isinstance(widget, QCheckBox):
        widget.setChecked(value)
    elif isinstance(widget, QComboBox):
        widget.setCurrentIndex(widget.findData(value))
    elif isinstance(widget, RegexInputEdit):
        widget.setPlainText(str(value))
    else:
        widget.setText(str(value))
    after = deepcopy(controller.session.document)
    controller.undo_stack.undo()
    assert controller.session.document == before
    controller.undo_stack.redo()
    assert controller.session.document == after


@pytest.mark.parametrize("metadata", ["macro_name", "description"])
def test_metadata_keyboard_undo_and_redo_use_document_history(editor, metadata):
    """メタデータのキーボードのUndoとRedoの使用の文書の履歴を確認する。"""
    window, controller = editor
    widget = getattr(window, metadata)
    old = widget.text()
    widget.setFocus()
    widget.selectAll()
    QTest.keyClicks(widget, "new value")
    assert getattr(controller.session.document, metadata) == "new value"
    QTest.keyClick(widget, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert getattr(controller.session.document, metadata) == old
    QTest.keyClick(widget, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    assert getattr(controller.session.document, metadata) == "new value"


def test_regex_widget_shortcuts_do_not_use_a_separate_local_undo(editor):
    """正規表現のウィジェットのショートカットの行わないの使用の別々のローカルのUndoを確認する。"""
    window, controller = editor
    widget = cast(RegexInputEdit, window.step_editor.fields["search_text"])
    widget.setFocus()
    widget.selectAll()
    QTest.keyClicks(widget, "changed")
    controller.add_step()
    QTest.keyClick(
        window.step_editor.fields["search_text"],
        Qt.Key.Key_Z,
        Qt.KeyboardModifier.ControlModifier,
    )
    assert len(controller.session.document.steps) == 3
    QTest.keyClick(widget, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert controller.session.document.steps[0].search_text == "a"


def test_savepoint_undo_redo_and_failed_save_preserve_dirty_state(
    editor, tmp_path, monkeypatch
):
    """保存時点のUndo／Redoと失敗した保存の保持の未保存状態の状態を確認する。"""
    window, controller = editor
    window.macro_name.setText("saved name")
    assert controller.save()
    assert not controller.session.modified
    saved = deepcopy(controller.session.document)
    window.macro_name.setText("new name")
    assert controller.session.modified
    controller.undo_stack.undo()
    assert controller.session.document == saved and not controller.session.modified
    controller.undo_stack.undo()
    assert (
        controller.session.document.macro_name == "history"
        and controller.session.modified
    )
    controller.undo_stack.redo()
    assert not controller.session.modified
    controller.undo_stack.redo()
    assert controller.session.modified
    monkeypatch.setattr(
        QMessageBox, "critical", lambda *args: QMessageBox.StandardButton.Ok
    )
    assert not controller.save(tmp_path)
    assert controller.session.modified and controller.undo_stack.canUndo()


def test_new_and_successful_load_reset_history_but_failed_load_does_not(
    editor, tmp_path, monkeypatch
):
    """新規のと成功した読み込みのリセットの履歴の一方の失敗した読み込みの行わないことを確認する。"""
    window, controller = editor
    window.macro_name.setText("edited")
    count = controller.undo_stack.count()
    monkeypatch.setattr(
        QMessageBox, "critical", lambda *args: QMessageBox.StandardButton.Ok
    )
    assert not controller.open_document(tmp_path / "missing.json")
    assert controller.undo_stack.count() == count
    controller.new_document()
    assert not controller.undo_stack.canUndo() and not window.undo_action.isEnabled()
    assert controller.session.document.macro_name == ""
    assert controller.open_document(tmp_path / "macro.json")
    assert not controller.undo_stack.canUndo()
    assert controller.session.document.macro_name == "history"


def test_undo_new_edit_discards_redo_and_revalidation_follows_restored_input(editor):
    """Undoの後で編集するとRedo履歴が消え、復元した入力を改めて検証することを確認する。"""
    window, controller = editor
    field = cast(RegexInputEdit, window.step_editor.fields["search_text"])
    cast(QCheckBox, window.step_editor.fields["regular_expression"]).setChecked(True)
    controller.history.break_merge()
    field.setPlainText("[")
    controller.validate()
    assert not window.editor_actions["run"].isEnabled()
    controller.undo_stack.undo()
    assert controller.session.validation_result.is_valid
    assert window.editor_actions["run"].isEnabled()
    field.setPlainText("different")
    assert not controller.undo_stack.canRedo()


class InternalDrop(QDropEvent):
    """同じツリー内からのドラッグを表すテスト用ドロップイベント。"""
    def __init__(self, tree, position):
        """ドラッグ元のツリーを記録する。"""
        super().__init__(
            QPointF(position),
            Qt.DropAction.MoveAction,
            QMimeData(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.tree = tree

    def source(self):
        """ドロップ操作のドラッグ元を返す。"""
        return self.tree


@pytest.mark.parametrize("destination", ["above", "below", "root", "outside"])
def test_native_drop_event_moves_flat_step_and_is_undoable(editor, destination):
    """ドロップで同階層の手順を移動し、その操作をUndoで取り消せることを確認する。"""
    window, controller = editor
    tree = window.tree
    controller.focus_diagnostic(1, "step_name")
    root = tree.topLevelItem(0)
    assert root is not None
    before = deepcopy(controller.session.document)
    if destination == "above":
        position = tree.visualItemRect(root.child(0)).topLeft()
    elif destination == "below":
        position = tree.visualItemRect(root.child(2)).bottomLeft()
    elif destination == "root":
        position = tree.visualItemRect(root).center()
    else:
        position = tree.viewport().rect().bottomRight()
    event = InternalDrop(tree, position)
    tree.dropEvent(event)
    assert event.isAccepted()
    assert controller.session.document != before
    assert tree.topLevelItemCount() == 1
    for index in range(3):
        assert tree.topLevelItem(0).child(index).childCount() == 0
    controller.undo_stack.undo()
    assert controller.session.document == before


def test_external_drop_and_invalid_or_same_position_do_not_change_document(editor):
    """外部のドロップと不正なまたは同じ位置が文書を変更しないことを確認する。"""
    window, controller = editor
    before = deepcopy(controller.session.document)
    tree = window.tree
    event = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.MoveAction,
        QMimeData(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tree.dropEvent(event)
    assert not event.isAccepted()
    assert not tree.request_reorder(-1, 0)
    assert not tree.request_reorder(0, 0)
    assert not tree.request_reorder(0, 1)
    assert not tree.request_reorder(1, 99)
    assert controller.session.document == before and not controller.undo_stack.canUndo()


def test_drag_history_saved_reload_and_actual_runner_sequence(editor):
    """ドラッグの履歴の保存済みの再読込と実際の実行処理の順序を確認する。"""
    window, controller = editor
    assert window.tree.request_reorder(1, 0)
    assert controller.save()
    loaded = MacroJsonLoader().load(controller.session.save_file_path)
    assert [step.step_name for step in loaded.steps] == ["second", "first", "third"]
    preview = controller._manager().preview_macro(loaded, "a")
    assert preview.result.text == "b"
    controller.undo_stack.undo()
    restored = MacroEditorBridge.to_json_model(controller.session.document)
    assert controller._manager().preview_macro(restored, "a").result.text == "c"


def test_definition_history_does_not_undo_article_transform(tmp_path, monkeypatch):
    """定義の履歴の行わないのUndoの原稿の変換を確認する。"""
    from main import MainWindow

    app = QApplication.instance() or QApplication([])
    main = MainWindow(
        settings_path=tmp_path / "settings.json", restore_unsaved_backup=False
    )
    main.editor.setPlainText("a")
    main.editor.document().setModified(False)
    main.show_macro_editor()
    controller = main.macro_editor_controller
    assert controller is not None
    model = MacroEditorDocumentData(
        macro_name="test",
        steps=[MacroEditorStepData(search_text="a", replacement_text="b")],
    )
    destination = MacroJsonSaver().save(
        MacroEditorBridge.to_json_model(model), tmp_path / "macro.json"
    )
    assert controller.open_document(destination)
    controller.add_step()
    controller.undo_stack.undo()
    monkeypatch.setattr(
        MacroRunPreviewDialog, "exec", lambda dialog: QDialog.DialogCode.Accepted
    )
    controller.preview_execution()
    assert main.editor.toPlainText() == "b"
    controller.undo_stack.redo()
    assert main.editor.toPlainText() == "b"
    main.editor.undo()
    assert main.editor.toPlainText() == "a"
    controller.session.modified = False
    main.editor.document().setModified(False)
    main.close()
    app.processEvents()


@pytest.mark.parametrize("field", ["macro_name", "search_text"])
def test_native_context_menu_routes_to_shared_undo_redo(editor, monkeypatch, field):
    """標準のコンテキストメニューが共有のUndo／Redoに振り分けることを確認する。"""
    window, controller = editor
    controller.add_step()
    count = len(controller.session.document.steps)
    widget = (
        window.macro_name if field == "macro_name" else window.step_editor.fields[field]
    )
    watched = widget.viewport() if isinstance(widget, RegexInputEdit) else widget

    observed = []

    def choose_undo():
        """コンテキストメニューからUndoを実行する。"""
        menu = QApplication.activePopupWidget()
        if isinstance(menu, QMenu):
            try:
                observed.append(
                    menu.actions()[:2] == [window.undo_action, window.redo_action]
                )
                window.undo_action.trigger()
            finally:
                menu.close()

    QTimer.singleShot(0, choose_undo)
    event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse,
        watched.rect().center(),
        watched.mapToGlobal(watched.rect().center()),
    )
    assert window.eventFilter(watched, event)
    assert observed == [True]
    assert len(controller.session.document.steps) == count - 1
    assert window.redo_action.isEnabled()


def test_delete_all_steps_undo_restores_selection_and_validation(editor):
    """削除のすべての手順のUndoが選択範囲と検証を復元することを確認する。"""
    window, controller = editor
    for index in (2, 1, 0):
        controller.delete_step(index)
    assert not controller.session.document.steps
    assert not controller.session.validation_result.is_valid
    assert not window.step_editor.isEnabled()
    controller.undo_stack.undo()
    assert window.selected_step() == 0
    assert window.step_editor.isEnabled()
    assert controller.session.validation_result.is_valid
    controller.undo_stack.redo()
    assert not controller.session.document.steps


def test_cancelled_new_and_language_change_keep_history(editor, monkeypatch):
    """取り消した新規のと言語の変更の保持するの履歴を確認する。"""
    window, controller = editor
    window.macro_name.setText("keep")
    before = deepcopy(controller.session.document)
    count = controller.undo_stack.count()
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args: QMessageBox.StandardButton.Cancel
    )
    controller.new_document()
    assert controller.session.document == before
    assert controller.undo_stack.count() == count
    window.translator.set_language("en")
    window.retranslate_ui()
    controller.validate()
    assert controller.undo_stack.count() == count
    window.undo_action.trigger()
    assert controller.session.document.macro_name == "history"


def test_normalization_form_and_its_dependent_controls_restore_together(editor):
    """正規化のフォームとその依存するの入力部品の復元のまとめてを確認する。"""
    window, controller = editor
    normalize = cast(QCheckBox, window.step_editor.fields["unicode_normalize"])
    form = cast(QComboBox, window.step_editor.fields["unicode_normalize_form"])
    normalize.setChecked(True)
    form.setCurrentIndex(form.findData("NFKC"))
    before = deepcopy(controller.session.document)
    normalize.setChecked(False)
    controller.undo_stack.undo()
    assert controller.session.document == before
    assert form.currentData() == "NFKC" and form.isEnabled()
    assert not window.step_editor.fields["replacement_enabled"].isEnabled()


def test_close_discard_then_reopen_does_not_revive_unsaved_history(editor):
    """変更を破棄して閉じた場合、開き直しても未保存の編集履歴が復元されないことを確認する。"""
    window, controller = editor
    before = deepcopy(controller.session.document)
    controller.add_step()
    window.macro_name.setText("discard this")
    assert controller.session.modified
    assert window.close()
    window.show()
    assert controller.session.document == before
    assert not controller.session.modified
    assert not controller.undo_stack.canUndo()
