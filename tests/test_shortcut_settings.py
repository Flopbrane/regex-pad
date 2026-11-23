"""Portable shortcut editing, locked standard keys, and text insertion."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from dialogs.shortcut_settings_dialog import (
    ShortcutEditorDialog,
    ShortcutSettingsDialog,
    validate_shortcut_settings,
)
from localization.translator import Translator
from main import MainWindow
from settings.shortcut_settings import (
    ShortcutSettings,
    ShortcutSettingsError,
    TextShortcut,
    load_shortcut_settings,
    save_shortcut_settings,
)


@pytest.fixture
def app() -> QApplication:
    existing = QApplication.instance()
    return existing if isinstance(existing, QApplication) else QApplication([])


def test_shortcut_file_roundtrip_and_invalid_file_is_preserved(tmp_path: Path) -> None:
    save_file_path = tmp_path / "shortcutkey_ref.json"
    settings = ShortcutSettings(
        {"inline_underline": "Ctrl+Alt+U"},
        [TextShortcut("one", "定型文", "Ctrl+Alt+K", "一行目\n二行目")],
    )
    save_shortcut_settings(save_file_path, settings)
    assert load_shortcut_settings(save_file_path) == settings
    save_file_path.write_text("broken", encoding="utf-8")
    with pytest.raises(ShortcutSettingsError):
        load_shortcut_settings(save_file_path)
    assert save_file_path.read_text(encoding="utf-8") == "broken"


def test_failed_shortcut_replace_keeps_previous_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    save_file_path = tmp_path / "shortcutkey_ref.json"
    original = ShortcutSettings({}, [TextShortcut("one", "挨拶", "Ctrl+Alt+K", "こんにちは")])
    save_shortcut_settings(save_file_path, original)
    before = save_file_path.read_bytes()
    original_replace = Path.replace

    def fail_replace(source: Path, target: Path) -> Path:
        if target == save_file_path:
            raise OSError("blocked")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(ShortcutSettingsError, match="blocked"):
        save_shortcut_settings(save_file_path, ShortcutSettings({"find": "Ctrl+Alt+F"}, []))
    assert save_file_path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [save_file_path]


def test_standard_keys_are_read_only_and_collisions_are_rejected(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = app
    window = MainWindow(settings_path=tmp_path / "config.json", restore_unsaved_backup=False)
    dialog = ShortcutSettingsDialog(
        Translator(Path("resources"), "ja"), window._shortcut_action_info,
        ShortcutSettings(), window,
    )
    standard_row = next(
        row for row in range(dialog.table.rowCount())
        if (item := dialog.table.item(row, 0)) is not None
        and item.data(Qt.ItemDataRole.UserRole) == ("windows", "Ctrl+C")
    )
    dialog.table.selectRow(standard_row)
    assert not dialog.edit_button.isEnabled()
    assert not dialog.delete_button.isEnabled()
    status = dialog.table.item(standard_row, 3)
    assert status is not None and status.text() == "変更不可"
    standard_item = dialog.table.item(standard_row, 0)
    assert standard_item is not None
    assert standard_item.foreground().color().name() == "#4c3163"
    assert standard_item.background().color().name() == "#dedede"
    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda _parent, _title, message: warnings.append(message))
    assert not dialog._check_key("Ctrl+C")
    assert not dialog._check_key("Ctrl+F")
    assert not dialog._check_key("Meta+E")
    assert len(warnings) == 3

    for identifier, key in (
        ("new", "Ctrl+N"), ("open", "Ctrl+O"),
        ("save", "Ctrl+S"), ("save_as", "Ctrl+Shift+S"),
        ("find", "Ctrl+F"),
    ):
        assert window._shortcut_action_info[identifier].locked
        row = next(
            index for index in range(dialog.table.rowCount())
            if (item := dialog.table.item(index, 0)) is not None
            and item.data(Qt.ItemDataRole.UserRole) == ("app", identifier)
        )
        dialog.table.selectRow(row)
        assert not dialog.edit_button.isEnabled()
        key_item = dialog.table.item(row, 2)
        assert key_item is not None and key_item.text() == key
        for column in range(dialog.table.columnCount()):
            item = dialog.table.item(row, column)
            assert item is not None
            assert item.foreground().color().name() == "#4c3163"
            assert item.background().color().name() == "#dedede"

    editable_row = next(
        index for index in range(dialog.table.rowCount())
        if (item := dialog.table.item(index, 0)) is not None
        and item.data(Qt.ItemDataRole.UserRole) == ("app", "inline_underline")
    )
    editable_item = dialog.table.item(editable_row, 0)
    assert editable_item is not None
    assert editable_item.background().color().name() != "#dedede"
    assert validate_shortcut_settings(
        ShortcutSettings({"find": "Ctrl+Alt+F"}, []), window._shortcut_action_info
    ) == "shortcut.invalid_config"


def test_old_override_for_newly_fixed_key_keeps_other_custom_keys(
    app: QApplication, tmp_path: Path,
) -> None:
    _ = app
    save_file_path = tmp_path / "shortcutkey_ref.json"
    save_shortcut_settings(
        save_file_path,
        ShortcutSettings({"find": "Ctrl+Alt+F", "inline_underline": "Ctrl+Alt+U"}, []),
    )
    before = save_file_path.read_bytes()
    window = MainWindow(settings_path=tmp_path / "config.json", restore_unsaved_backup=False)
    assert not window.shortcut_settings_error
    assert window.find_action.shortcut().toString() == "Ctrl+F"
    assert window.inline_underline_action.shortcut().toString() == "Ctrl+Alt+U"
    assert save_file_path.read_bytes() == before


def test_add_and_edit_text_shortcut_in_dialog(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = app
    window = MainWindow(settings_path=tmp_path / "config.json", restore_unsaved_backup=False)
    dialog = ShortcutSettingsDialog(
        window.translator, window._shortcut_action_info, ShortcutSettings(), window
    )

    def fill_new(editor: ShortcutEditorDialog) -> QDialog.DialogCode:
        editor.name_edit.setText("あいさつ")
        editor.key_edit.setKeySequence(QKeySequence("Ctrl+Alt+K"))
        assert editor.text_edit is not None
        editor.text_edit.setPlainText("こんにちは\n")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ShortcutEditorDialog, "exec", fill_new)
    dialog.add_snippet()
    assert len(dialog.settings.snippets) == 1
    assert dialog.settings.snippets[0].text == "こんにちは\n"
    row = next(
        index for index in range(dialog.table.rowCount())
        if (item := dialog.table.item(index, 0)) is not None
        and item.data(Qt.ItemDataRole.UserRole)[0] == "snippet"
    )
    dialog.table.selectRow(row)
    assert dialog.edit_button.isEnabled()
    assert dialog.delete_button.isEnabled()

    def fill_edit(editor: ShortcutEditorDialog) -> QDialog.DialogCode:
        editor.key_edit.setKeySequence(QKeySequence("Ctrl+Alt+J"))
        assert editor.text_edit is not None
        editor.text_edit.setPlainText("こんばんは")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ShortcutEditorDialog, "exec", fill_edit)
    dialog.edit_selected()
    assert dialog.settings.snippets[0].shortcut == "Ctrl+Alt+J"
    assert dialog.settings.snippets[0].text == "こんばんは"

    app_row = next(
        index for index in range(dialog.table.rowCount())
        if (item := dialog.table.item(index, 0)) is not None
        and item.data(Qt.ItemDataRole.UserRole) == ("app", "inline_underline")
    )
    dialog.table.selectRow(app_row)

    def edit_app(editor: ShortcutEditorDialog) -> QDialog.DialogCode:
        editor.key_edit.setKeySequence(QKeySequence("Ctrl+Alt+U"))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ShortcutEditorDialog, "exec", edit_app)
    dialog.edit_selected()
    assert dialog.settings.overrides["inline_underline"] == "Ctrl+Alt+U"


def test_main_window_saves_and_restores_shortcut_actions_and_text(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = app
    config_path = tmp_path / "config.json"
    window = MainWindow(settings_path=config_path, restore_unsaved_backup=False)

    def accept_changes(dialog: ShortcutSettingsDialog) -> QDialog.DialogCode:
        dialog.settings.overrides["inline_underline"] = "Ctrl+Alt+U"
        dialog.settings.snippets.append(
            TextShortcut("greeting", "あいさつ", "Ctrl+Alt+K", "こんにちは")
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ShortcutSettingsDialog, "exec", accept_changes)
    window.show_shortcut_settings_dialog()
    save_file_path = tmp_path / "shortcutkey_ref.json"
    assert save_file_path.is_file()
    assert window.inline_underline_action.shortcut().toString() == "Ctrl+Alt+U"
    window.editor.setPlainText("before after")
    cursor = window.editor.textCursor()
    cursor.setPosition(len("before "))
    window.editor.setTextCursor(cursor)
    window._custom_shortcut_actions[0].trigger()
    assert window.editor.toPlainText() == "before こんにちはafter"

    before_cancel = save_file_path.read_bytes()
    monkeypatch.setattr(
        ShortcutSettingsDialog, "exec", lambda _dialog: QDialog.DialogCode.Rejected
    )
    window.show_shortcut_settings_dialog()
    assert save_file_path.read_bytes() == before_cancel

    reopened = MainWindow(settings_path=config_path, restore_unsaved_backup=False)
    assert reopened.inline_underline_action.shortcut().toString() == "Ctrl+Alt+U"
    assert reopened._custom_shortcut_actions[0].text() == "あいさつ"


def test_manual_collision_file_is_not_applied_or_overwritten(
    app: QApplication, tmp_path: Path,
) -> None:
    _ = app
    save_file_path = tmp_path / "shortcutkey_ref.json"
    save_shortcut_settings(
        save_file_path, ShortcutSettings({"inline_underline": "Ctrl+C"}, [])
    )
    before = save_file_path.read_bytes()
    window = MainWindow(
        settings_path=tmp_path / "config.json", restore_unsaved_backup=False
    )
    assert window.shortcut_settings_error
    assert window.inline_underline_action.shortcut().toString() == "Ctrl+U"
    assert save_file_path.read_bytes() == before
