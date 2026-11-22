"""Behavioral regression checks for the structured macro editor."""

from pathlib import Path
from typing import cast

import pytest
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QMessageBox

from app_logging import AppLogger
from dialogs.macro_editor_controller import MacroEditorController
from dialogs.macro_editor_window import MacroEditorWindow
from dialogs.regex_input_edit import RegexInputEdit
from localization.translator import Translator
from macro.editor_bridge import MacroEditorBridge
from macro.editor_data_model import MacroEditorDocumentData, MacroEditorStepData
from macro.json_loader import MacroJsonLoader


@pytest.fixture
def editor(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    window = MacroEditorWindow(Translator(Path("resources"), "ja"))
    controller = MacroEditorController(window, AppLogger(tmp_path / "logs"))
    yield window, controller
    controller.session.modified = False
    controller.timer.stop()
    window.close()
    window.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("exclusion", [None, "", " \\d+\nＡ "])
@pytest.mark.parametrize("replacement", [None, "", " \\g<1>\nＢ "])
def test_bridge_roundtrip_preserves_null_empty_and_exact_text(exclusion, replacement):
    model = MacroJsonLoader(Path("macro")).load("macro_format_v1.json")
    model.steps[0].exclusion_text = exclusion
    model.steps[0].replacement_text = replacement
    assert (
        MacroEditorBridge.to_json_model(MacroEditorBridge.from_json_model(model))
        == model
    )


def test_form_retains_invalid_regex_and_diagnostic_navigation(editor):
    window, controller = editor
    window.macro_name.setText("test")
    fields = window.step_editor.fields
    cast(QCheckBox, fields["regular_expression"]).setChecked(True)
    cast(RegexInputEdit, fields["search_text"]).setPlainText("[")
    controller.validate()
    assert controller.session.document.steps[0].search_text == "["
    assert any(
        d.code == "invalid_search_regex"
        for d in controller.session.validation_result.errors
    )
    assert not window.editor_actions["save"].isEnabled()
    message_item = window.diagnostics.item(0, 3)
    assert message_item is not None
    assert "macro.validation." not in message_item.text()
    controller.focus_diagnostic(0, "search_text")
    assert window.selected_step() == 0
    assert cast(RegexInputEdit, fields["search_text"]).toPlainText() == "["


def test_boolean_options_are_checkboxes_and_keep_editor_history(editor):
    window, controller = editor
    fields = window.step_editor.fields
    boolean_names = (
        "enabled", "operation", "exclusion_enabled", "replacement_enabled",
        "regular_expression", "case_sensitive", "whole_word",
        "selected_only", "visible_only", "unicode_normalize",
        "append_dot_to_circled_number",
    )
    assert all(isinstance(fields[name], QCheckBox) for name in boolean_names)
    assert isinstance(fields["unicode_normalize_form"], QComboBox)

    checkbox = cast(QCheckBox, fields["case_sensitive"])
    checkbox.setChecked(True)
    assert controller.session.document.steps[0].case_sensitive is True
    controller.undo_stack.undo()
    assert checkbox.isChecked() is False
    controller.undo_stack.redo()
    assert checkbox.isChecked() is True


def test_heading_numbering_step_upgrades_format_and_is_saveable(editor, tmp_path):
    window, controller = editor
    window.macro_name.setText("Markdown numbering")
    operation = cast(QCheckBox, window.step_editor.fields["operation"])
    cast(RegexInputEdit, window.step_editor.fields["search_text"]).setPlainText("preserved")
    cast(RegexInputEdit, window.step_editor.fields["exclusion_text"]).setPlainText("excluded")
    cast(RegexInputEdit, window.step_editor.fields["replacement_text"]).setPlainText("replacement")
    operation.setChecked(True)
    assert controller.session.document.format_version == 3
    for name in ("search_text", "exclusion_text", "replacement_text"):
        assert not window.step_editor.fields[name].isEnabled()
    assert controller.validate() is not None
    destination = tmp_path / "headings.json"
    assert controller.save(destination)
    loaded = MacroJsonLoader().load(destination)
    assert loaded.steps[0].operation == "numbered_heading"
    operation.setChecked(False)
    assert cast(RegexInputEdit, window.step_editor.fields["search_text"]).toPlainText() == "preserved"


def test_step_operations_preserve_order_and_independent_data(editor, monkeypatch):
    window, controller = editor
    controller.session.document.steps[0].search_text = "first"
    controller.duplicate_step(0)
    controller.session.document.steps[1].search_text = "second"
    controller.move_step(1, -1)
    assert [s.search_text for s in controller.session.document.steps] == [
        "second",
        "first",
    ]
    assert controller.session.document.steps[0].step_name.endswith("_copy")
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a: QMessageBox.StandardButton.Yes
    )
    controller.delete_step(0)
    assert controller.session.document.steps[0].search_text == "first"
    controller.add_step()
    assert window.selected_step() == 1


def test_save_reload_and_warning_only_save(editor, tmp_path):
    window, controller = editor
    window.macro_name.setText("テスト")
    cast(RegexInputEdit, window.step_editor.fields["search_text"]).setPlainText(
        "before"
    )
    destination = tmp_path / "macro.json"
    assert controller.save(destination)
    assert not controller.session.modified
    model = MacroJsonLoader().load(destination)
    assert model.steps[0].replacement_text == ""
    assert model.steps[0].exclusion_text is None
    model.steps[0].enabled = False
    controller.session.document = MacroEditorBridge.from_json_model(model)
    controller._render_document()
    assert controller.save(destination)
    assert controller.session.validation_result.warnings
    assert controller.open_document(destination)
    assert MacroEditorBridge.to_json_model(
        controller.session.document
    ) == MacroJsonLoader().load(destination)


def test_load_and_save_failure_preserve_edits(editor, tmp_path, monkeypatch):
    window, controller = editor
    window.macro_name.setText("keep me")
    cast(RegexInputEdit, window.step_editor.fields["search_text"]).setPlainText(
        "before"
    )
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a: QMessageBox.StandardButton.Discard
    )
    monkeypatch.setattr(
        QMessageBox, "critical", lambda *a: QMessageBox.StandardButton.Ok
    )
    assert not controller.open_document(tmp_path / "missing.json")
    assert controller.session.document.macro_name == "keep me"
    assert controller.session.modified
    assert not controller.save(
        tmp_path
    )  # A directory cannot be replaced by a JSON file.
    assert controller.session.modified
    assert controller.session.save_file_path is None


def test_invalid_model_does_not_overwrite_file(editor, tmp_path, monkeypatch):
    _, controller = editor
    destination = tmp_path / "keep.json"
    destination.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a: QMessageBox.StandardButton.Ok
    )
    assert not controller.save(destination)
    assert destination.read_text(encoding="utf-8") == "keep"


def test_close_cancel_and_failed_save_keep_window_open(editor, monkeypatch):
    window, controller = editor
    window.show()
    window.macro_name.setText("modified")
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a: QMessageBox.StandardButton.Cancel
    )
    assert not window.close()
    assert window.isVisible()
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a: QMessageBox.StandardButton.Save
    )
    assert not window.close()
    assert controller.session.modified


def test_unicode_route_and_null_switches(editor):
    window, controller = editor
    fields = window.step_editor.fields
    cast(RegexInputEdit, fields["replacement_text"]).setPlainText("kept in form")
    cast(QCheckBox, fields["unicode_normalize"]).setChecked(True)
    form = cast(QComboBox, fields["unicode_normalize_form"])
    assert not form.isEditable()
    form.setCurrentIndex(form.findData("NFKC"))
    model = MacroEditorBridge.to_json_model(controller.session.document)
    assert model.steps[0].replacement_text is None
    assert model.steps[0].unicode_normalize_form == "NFKC"
    cast(QCheckBox, fields["unicode_normalize"]).setChecked(False)
    cast(QCheckBox, fields["replacement_enabled"]).setChecked(True)
    model = MacroEditorBridge.to_json_model(controller.session.document)
    assert model.steps[0].replacement_text == "kept in form"
    assert model.steps[0].unicode_normalize_form is None


def test_loading_semantic_error_preserves_values_for_correction(editor, tmp_path):
    from macro.json_saver import MacroJsonSaver

    _, controller = editor
    document = MacroEditorDocumentData(
        macro_name="invalid",
        steps=[
            MacroEditorStepData(search_text="[", regular_expression=True),
        ],
    )
    destination = MacroJsonSaver().save(
        MacroEditorBridge.to_json_model(document), tmp_path / "invalid.json"
    )
    assert controller.open_document(destination)
    assert controller.session.document.steps[0].search_text == "["
    assert not controller.session.validation_result.is_valid


def test_main_window_reuses_macro_editor_and_preserves_body(tmp_path):
    from main import MainWindow

    app = QApplication.instance() or QApplication([])
    main_window = MainWindow(settings_path=tmp_path / "config.json")
    main_window.editor.setPlainText("body stays here")
    main_window.editor.document().setModified(False)
    main_window.show_macro_editor()
    editor_window = main_window.macro_editor_window
    main_window.show_macro_editor()
    assert main_window.macro_editor_window is editor_window
    assert main_window.editor.toPlainText() == "body stays here"
    main_window.close()
    app.processEvents()


def test_input_value_error_returns_to_affected_field_without_losing_text(
    editor, monkeypatch
):
    from macro.editor_bridge import MacroEditorInputError

    window, controller = editor
    cast(RegexInputEdit, window.step_editor.fields["search_text"]).setPlainText(
        "keep raw text"
    )

    def fail_conversion(_document):
        raise MacroEditorInputError(0, "search_text", "input rejected")

    monkeypatch.setattr(MacroEditorBridge, "to_json_model", fail_conversion)
    assert controller.validate() is None
    assert controller.session.validation_result.errors[0].field_name == "search_text"
    assert window.step_editor.fields["search_text"].toolTip() == "input rejected"
    assert (
        cast(RegexInputEdit, window.step_editor.fields["search_text"]).toPlainText()
        == "keep raw text"
    )


def test_actions_emit_and_language_switch_keeps_edits(editor):
    window, controller = editor
    cast(RegexInputEdit, window.step_editor.fields["search_text"]).setPlainText(
        "exact \\d+\ntext"
    )
    window.editor_actions["validate"].trigger()
    window.translator.set_language("en")
    window.retranslate_ui()
    controller.validate()
    assert window.editor_actions["validate"].text() == "Validate"
    message_item = window.diagnostics.item(0, 3)
    assert message_item is not None
    assert "macro.validation." not in message_item.text()
    assert (
        cast(RegexInputEdit, window.step_editor.fields["search_text"]).toPlainText()
        == "exact \\d+\ntext"
    )
    assert controller.session.modified


def test_macro_editor_preferences_survive_main_window_restart(tmp_path):
    from main import MainWindow
    from settings.settings_manager import SettingsManager

    app = QApplication.instance() or QApplication([])
    settings_path = tmp_path / "config.json"
    main_window = MainWindow(settings_path=settings_path)
    main_window.show_macro_editor()
    assert main_window.macro_editor_controller is not None
    assert main_window.macro_editor_window is not None
    main_window.macro_editor_controller.session.macro_folder = tmp_path
    main_window.macro_editor_window.resize(980, 720)
    main_window.macro_editor_window.splitter.setSizes([270, 650])
    main_window.close()
    saved = SettingsManager(settings_path).load()
    assert saved.macro_folder == str(tmp_path)
    assert saved.macro_editor_geometry
    assert saved.macro_editor_splitter_state
    reopened = MainWindow(settings_path=settings_path)
    reopened.show_macro_editor()
    assert reopened.macro_editor_controller is not None
    assert reopened.macro_editor_controller.session.macro_folder == tmp_path
    reopened.close()
    app.processEvents()
