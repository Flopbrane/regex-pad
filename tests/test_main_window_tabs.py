"""メインウインドウのタブを検証する。"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

import main as main_module
from main import MainWindow
from settings.settings_manager import SettingsManager


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_new_file_adds_tab_without_clearing_current_text(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """消去時の現在の文字列を省いた場合、新規のファイルがタブを追加することを確認する。"""
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
    )
    window.editor.setPlainText("first document")

    window.new_file()

    assert window.tab_widget.count() == 2
    first_editor = window._editor_at(0)
    assert first_editor is not None
    assert first_editor.toPlainText() == "first document"
    assert window.editor.toPlainText() == ""


def test_main_window_uses_config_json_by_default(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """メインウインドウが既定の設定ファイルとしてconfig.jsonを使うことを確認する。"""
    _ = app
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(main_module, "default_config_path", lambda: config_path)

    window = MainWindow(restore_unsaved_backup=False)

    assert window.settings_manager.settings_path == config_path


def test_main_window_applies_config_colors_and_font_on_startup(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """メインウインドウが構成設定の色とフォントでの起動時のを適用することを確認する。"""
    _ = app
    settings_path = tmp_path / "config.json"
    SettingsManager(settings_path).save(
        word_wrap_enabled=False,
        line_numbers_enabled=True,
        ruler_enabled=False,
        visible_spaces_enabled=False,
        visible_tabs_enabled=False,
        visible_newlines_enabled=False,
        fixed_column_wrap_enabled=False,
        fixed_column_wrap_column=80,
        startup_restore_enabled=True,
        language_code="ja",
        default_encoding="utf-8",
        newline_code="lf",
        window_width=900,
        window_height=650,
        font_family="Meiryo",
        font_size=14,
        editor_background_color="#101820",
        editor_text_color="#f5f7fa",
        html_tag_color="#33ccff",
        wordpress_core_block_color="#99aabb",
    )

    window = MainWindow(settings_path=settings_path, restore_unsaved_backup=False)

    assert window.font_family == "Meiryo"
    assert window.font_size == 14
    assert window.editor.font().family() == "Meiryo"
    assert window.editor.font().pointSize() == 14
    assert window.editor.editor_background_color == "#101820"
    assert window.editor.editor_text_color == "#f5f7fa"
    assert window.editor.html_tag_color == "#33ccff"
    assert window.editor.wordpress_core_block_color == "#99aabb"


def test_unsaved_tab_title_uses_first_line(app: QApplication, tmp_path: Path) -> None:
    """未保存のタブのタイトルが先頭行を使うことを確認する。"""
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
    )

    window.editor.setPlainText("draft title\nbody")
    window.editor.document().setModified(True)
    window._update_tab_titles()

    assert window.tab_widget.tabText(0) == "*draft title"


def test_duplicate_tab_copies_text_as_unsaved_tab(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """タブを複製すると、同じ本文を持つ未保存のタブが開くことを確認する。"""
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
    )
    window.editor.setPlainText("backup draft\nbody")

    duplicate_editor = window.duplicate_tab(0)

    assert duplicate_editor is not None
    assert window.tab_widget.count() == 2
    assert duplicate_editor.toPlainText() == "backup draft\nbody"
    assert duplicate_editor.document().isModified()
    assert window.tab_widget.tabText(1) == "*backup draft"


def test_tab_width_setting_is_applied_to_new_tabs(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """タブ幅の設定が新規のタブが適用されることを確認する。"""
    _ = app
    settings_path = tmp_path / "settings.json"
    SettingsManager(settings_path).save(
        word_wrap_enabled=False,
        line_numbers_enabled=True,
        ruler_enabled=False,
        visible_spaces_enabled=False,
        visible_tabs_enabled=False,
        visible_newlines_enabled=False,
        fixed_column_wrap_enabled=False,
        fixed_column_wrap_column=80,
        startup_restore_enabled=True,
        language_code="ja",
        default_encoding="utf-8",
        newline_code="lf",
        window_width=900,
        window_height=650,
        tab_width=8,
    )
    window = MainWindow(settings_path=settings_path)

    expected_width = window.editor.fontMetrics().horizontalAdvance(" ") * 8
    assert window.editor.tabStopDistance() == expected_width

    window.new_file()

    assert window.editor.tabStopDistance() == expected_width


def test_close_tab_autosaves_unsaved_changes_without_prompt(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """閉じる操作のタブのを自動保存するの未保存の変更（確認画面なし）を確認する。"""
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
    )
    window.editor.setPlainText("discard me")
    window.editor.document().setModified(True)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: pytest.fail("unsaved prompt should not open"),
    )

    closed = window.close_tab(0)

    assert closed
    assert window.tab_widget.count() == 1
    assert window.editor.toPlainText() == ""


def test_close_tab_stops_when_autosave_fails(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """自動保存が失敗するの場合、閉じる操作のタブが停止することを確認する。"""
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
    )
    window.editor.setPlainText("keep me")
    window.editor.document().setModified(True)
    monkeypatch.setattr(
        window.unsaved_backup_manager,
        "save_session",
        lambda session: False,
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: pytest.fail("unsaved prompt should not open"),
    )
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )

    closed = window.close_tab(0)

    assert not closed
    assert window.tab_widget.count() == 1
    assert window.editor.toPlainText() == "keep me"


def test_move_tab_to_new_window_moves_text_and_removes_source_tab(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """移動のタブのへの新規のウインドウが文字列を移動するとともに、元のタブを取り除くことを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("compare this\nbody")

    new_window = window.move_tab_to_new_window(0)

    assert new_window is not None
    assert new_window.editor.toPlainText() == "compare this\nbody"
    assert window.editor.toPlainText() == ""
    assert len(window.tab_windows) == 1


def test_move_tab_to_new_window_stops_when_autosave_fails(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """自動保存が失敗するの場合、移動のタブのへの新規のウインドウが停止することを確認する。"""
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
    )
    window.editor.setPlainText("keep in source")
    window.editor.document().setModified(True)
    monkeypatch.setattr(
        window.unsaved_backup_manager,
        "save_session",
        lambda session: False,
    )
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )

    new_window = window.move_tab_to_new_window(0)

    assert new_window is None
    assert window.tab_widget.count() == 1
    assert window.editor.toPlainText() == "keep in source"
    assert window.tab_windows == []


def test_each_window_has_uuid_and_child_window_is_registered(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """各ウインドウがUUIDと子要素のウインドウの登録済みのを持つことを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("child window source")

    new_window = window.move_tab_to_new_window(0)

    assert new_window is not None
    assert uuid.UUID(window.window_id)
    assert uuid.UUID(new_window.window_id)
    assert new_window.window_id != window.window_id
    assert window.child_windows[new_window.window_id] is new_window
