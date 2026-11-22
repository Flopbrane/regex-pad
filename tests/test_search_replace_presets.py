"""Search/Replace preset capture, routing, and scoped execution."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from dialogs.macro_run_preview_dialog import MacroRunPreviewDialog
from macro.json_data_model import MacroJsonData, MacroJsonStepData
from macro.json_loader import MacroJsonLoader
from macro.json_saver import MacroJsonSaver
from macro.macro_manager import MacroManager
from main import MainWindow


@pytest.fixture
def window(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    main = MainWindow(
        settings_path=tmp_path / "settings.json", restore_unsaved_backup=False
    )
    yield main
    if main.macro_editor_controller is not None:
        main.macro_editor_controller.session.modified = False
        main.macro_editor_controller.timer.stop()
    for editor in main.tab_file_paths:
        editor.document().setModified(False)
    main.close()
    main.deleteLater()
    app.processEvents()


def _preset(*steps: MacroJsonStepData) -> MacroJsonData:
    return MacroJsonData(2, "sample", "", steps)


def _step(
    name: str, search: str, replacement: str, *,
    case_sensitive: bool = False, whole_word: bool = False,
    selected_only: bool = False, visible_only: bool = False,
) -> MacroJsonStepData:
    return MacroJsonStepData(
        name, True, False, False, None, False, search, None, replacement,
        case_sensitive=case_sensitive,
        whole_word=whole_word,
        selected_only=selected_only,
        visible_only=visible_only,
    )


def test_search_menu_has_four_preset_actions_and_no_macro_menu(window):
    assert [action.text() for action in window.preset_menu.actions()] == [
        "新規プリセット作成",
        "プリセットの呼び出し・実行",
        "プリセットの編集",
        "プリセットの削除",
    ]
    assert window.preset_menu.menuAction() in window.search_menu.actions()
    assert all(
        action.text() != "マクロ" for action in window.menuBar().actions()
    )


def test_find_dialog_captures_all_active_conditions_into_new_json(
    window, tmp_path: Path
):
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setPlainText("①")
    dialog.exclusion_text_edit.setPlainText("skip")
    dialog.replace_text_edit.setPlainText("dormant replacement")
    for checkbox in (
        dialog.case_sensitive_check_box,
        dialog.regular_expression_check_box,
        dialog.whole_word_check_box,
        dialog.selected_only_check_box,
        dialog.visible_only_check_box,
        dialog.unicode_normalize_check_box,
        dialog.append_dot_to_circled_number_check_box,
    ):
        checkbox.setChecked(True)
    dialog.preset_button.click()
    controller = window.macro_editor_controller
    assert controller is not None
    document = controller.session.document
    assert document.format_version == 2
    assert controller.session.save_file_path is None
    assert controller.session.modified
    step = document.steps[0]
    assert step.search_text == "①"
    assert step.exclusion_text == "skip"
    assert step.replacement_text == "dormant replacement"
    assert step.case_sensitive and step.regular_expression and step.whole_word
    assert step.selected_only and step.visible_only
    assert step.unicode_normalize and step.append_dot_to_circled_number
    controller.window.macro_name.setText("captured")
    save_file_path = tmp_path / "captured.json"
    assert controller.save(save_file_path)
    saved = MacroJsonLoader(tmp_path).load(save_file_path)
    saved_step = saved.steps[0]
    assert saved_step.search_text == "①"
    assert saved_step.exclusion_text == "skip"
    assert saved_step.replacement_text is None
    assert saved_step.replacement_input_text == "dormant replacement"
    assert saved_step.case_sensitive and saved_step.whole_word
    assert saved_step.selected_only and saved_step.visible_only
    assert controller.open_document(save_file_path)
    assert controller.session.document.steps[0].replacement_text == (
        "dormant replacement"
    )


def test_repeated_capture_appends_to_open_saved_preset(window, tmp_path: Path):
    save_file_path = MacroJsonSaver(tmp_path).save(
        _preset(_step("first", "a", "b")), tmp_path / "saved.json"
    )
    window.show_macro_editor()
    controller = window.macro_editor_controller
    assert controller is not None
    assert controller.open_document(save_file_path)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None

    for find_text, replacement_text in (("b", "c"), ("c", "d")):
        dialog.find_text_edit.setPlainText(find_text)
        dialog.replace_text_edit.setPlainText(replacement_text)
        dialog.preset_button.click()

    document = controller.session.document
    assert controller.session.save_file_path == save_file_path
    assert document.macro_name == "sample"
    assert [step.search_text for step in document.steps] == ["a", "b", "c"]
    assert [step.step_name for step in document.steps] == ["first", "step_2", "step_3"]
    assert controller.window.selected_step() == 2
    assert controller.session.modified
    controller.undo_stack.undo()
    assert [step.search_text for step in controller.session.document.steps] == ["a", "b"]
    controller.undo_stack.redo()
    assert [step.search_text for step in controller.session.document.steps] == ["a", "b", "c"]
    assert controller.save()
    saved = MacroJsonLoader(tmp_path).load(save_file_path)
    assert [step.search_text for step in saved.steps] == ["a", "b", "c"]


def test_capture_fills_pristine_new_editor_then_appends(window):
    window.new_search_preset()
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    controller = window.macro_editor_controller
    assert dialog is not None and controller is not None

    dialog.find_text_edit.setPlainText("first")
    dialog.preset_button.click()
    assert [step.search_text for step in controller.session.document.steps] == ["first"]
    controller.undo_stack.undo()
    assert controller.session.document.steps[0].search_text == ""
    controller.undo_stack.redo()
    dialog.find_text_edit.setPlainText("second")
    dialog.preset_button.click()
    assert [step.search_text for step in controller.session.document.steps] == [
        "first", "second"
    ]


def test_open_and_run_menu_loads_editor_before_execution(
    window, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    save_file_path = MacroJsonSaver(tmp_path).save(
        _preset(_step("first", "a", "b")), tmp_path / "saved.json"
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: (str(save_file_path), "JSON")
    )
    window.editor.setPlainText("a")
    window.run_search_preset()
    controller = window.macro_editor_controller
    assert controller is not None
    assert controller.session.load_file_path == save_file_path
    assert controller.window.editor_actions["run"].isEnabled()
    assert window.editor.toPlainText() == "a"


def test_delete_moves_a_valid_preset_to_recoverable_folder(
    window, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    save_file_path = MacroJsonSaver(tmp_path).save(
        _preset(_step("first", "a", "b")), tmp_path / "saved.json"
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: (str(save_file_path), "JSON")
    )
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes
    )
    window.delete_search_preset()
    assert not save_file_path.exists()
    archived = list((tmp_path / ".deleted_presets").glob("*.json"))
    assert len(archived) == 1
    assert MacroJsonLoader(tmp_path).load(archived[0]).macro_name == "sample"


def test_multistep_execution_uses_selected_visible_intersection_and_case_rules():
    scoped = _preset(
        _step("first", "a", "b", selected_only=True, visible_only=True),
        _step("second", "b", "c", selected_only=True),
    )
    result = MacroManager().execute_macro(
        scoped, "aa AA aa", selected_scope=(3, 5), visible_scope=(0, 8)
    )
    assert result.succeeded
    assert result.text == "aa cc aa"
    assert [step.replacements for step in result.steps] == [2, 2]
    assert MacroManager().execute_macro(scoped, "aa AA aa").text == "aa AA aa"

    whole_word = _preset(
        _step("case", "cat", "dog", case_sensitive=True, whole_word=True)
    )
    assert MacroManager().execute_macro(whole_word, "cat scatter CAT").text == (
        "dog scatter CAT"
    )


def test_scope_follows_an_earlier_unscoped_replacement():
    definition = _preset(
        _step("expand", "a", "zz"),
        _step("selected", "foo", "bar", selected_only=True),
    )
    result = MacroManager().execute_macro(
        definition, "a foo", selected_scope=(2, 5)
    )
    assert result.succeeded
    assert result.text == "zz bar"


def test_loaded_preset_executes_only_after_editor_preview_approval(
    window, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    save_file_path = MacroJsonSaver(tmp_path).save(
        _preset(_step("selected", "a", "b", selected_only=True)),
        tmp_path / "selected.json",
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: (str(save_file_path), "JSON")
    )
    window.editor.setPlainText("a a")
    cursor = window.editor.textCursor()
    cursor.setPosition(2)
    cursor.setPosition(3, cursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.run_search_preset()
    assert window.editor.toPlainText() == "a a"

    def approve(dialog: MacroRunPreviewDialog):
        assert dialog.after.toPlainText() == "a b"
        return dialog.DialogCode.Accepted

    monkeypatch.setattr(MacroRunPreviewDialog, "exec", approve)
    assert window.macro_editor_window is not None
    window.macro_editor_window.editor_actions["run"].trigger()
    assert window.editor.toPlainText() == "a b"
    window.editor.undo()
    assert window.editor.toPlainText() == "a a"
