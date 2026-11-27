"""現在のタブと未保存タブのウインドウタイトル、保存名の候補を検証する。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog

from main import MainWindow
from settings.settings_manager import SettingsManager


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance() or QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_title_shows_active_full_path_and_setting_persists(
    app: QApplication, tmp_path: Path,
) -> None:
    """タイトルが有効な全体のパスと設定のを永続化するを表示することを確認する。"""
    _ = app
    settings_path = tmp_path / "settings.json"
    window = MainWindow(settings_path=settings_path, restore_unsaved_backup=False)
    first = tmp_path / "one.md"
    second = tmp_path / "nested" / "two.md"
    window._set_current_file_state(first)
    window._update_window_title()
    assert str(first) in window.windowTitle()

    window.create_editor_tab("content", save_file_path=second)
    assert str(second) in window.windowTitle()
    window.tab_widget.setCurrentIndex(0)
    assert str(first) in window.windowTitle()

    window.show_full_path_in_title = False
    window._update_window_title()
    assert window.windowTitle() == "one.md - Regex-Pad"
    window._save_settings()
    assert SettingsManager(settings_path).load().show_full_path_in_title is False
    window.close()


@pytest.mark.parametrize(
    ("first_line", "suggestion"),
    [
        ("今日の記事", "今日の記事.md"),
        ("", "無題.md"),
        ("A/B:C?", "A_B_C_.md"),
        ("CON", "_CON.md"),
    ],
)
def test_unsaved_first_line_is_selected_in_save_dialog(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    first_line: str, suggestion: str,
) -> None:
    """未保存の先頭行が選択中の内の保存画面になることを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText(first_line + "\n本文")
    selected_names: list[str] = []

    def inspect_dialog(dialog: QFileDialog) -> QFileDialog.DialogCode:
        """保存画面の現在のファイル名候補と選択状態を確認する。"""
        selected_names.extend(dialog.selectedFiles())
        return QFileDialog.DialogCode.Rejected

    monkeypatch.setattr(QFileDialog, "exec", inspect_dialog)
    save_file_path, _encoding = window._get_save_file_path()
    assert save_file_path is None
    assert selected_names and Path(selected_names[0]).name == suggestion
    window.close()


def test_options_dialog_exposes_full_path_checkbox(app: QApplication) -> None:
    """設定画面のを公開するの全体のパスのチェックボックスを確認する。"""
    _ = app
    from dialogs.options_dialog import OptionsDialog
    from localization.translator import Translator
    from settings.settings_manager import EditorSettings

    dialog = OptionsDialog(Translator(Path("resources"), "ja"), EditorSettings())
    assert dialog.show_full_path_checkbox.text() == "フルパスを表示する"
    assert dialog.show_full_path_checkbox.isChecked()
    dialog.show_full_path_checkbox.setChecked(False)
    assert dialog.values().show_full_path_in_title is False


def test_options_choice_updates_title_and_saved_setting(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """オプションの選択がタイトルと保存済みの設定を更新することを確認する。"""
    _ = app
    from dialogs.options_dialog import OptionsDialog

    settings_path = tmp_path / "settings.json"
    window = MainWindow(settings_path=settings_path, restore_unsaved_backup=False)
    window._set_current_file_state(tmp_path / "article.md")
    window._update_window_title()

    def choose_short_name(dialog: OptionsDialog) -> OptionsDialog.DialogCode:
        """設定画面でタイトルの短いファイル名表示を選ぶ。"""
        dialog.show_full_path_checkbox.setChecked(False)
        return OptionsDialog.DialogCode.Accepted

    monkeypatch.setattr(OptionsDialog, "exec", choose_short_name)
    window.show_options_dialog()
    assert window.windowTitle() == "article.md - Regex-Pad"
    assert SettingsManager(settings_path).load().show_full_path_in_title is False
    window.close()
