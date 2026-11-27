"""メインウインドウのバックアップを検証する。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from fileio.unsaved_backup_manager import (
    UnsavedBackup,
    UnsavedBackupManager,
    UnsavedBackupSession,
)
from main import MainWindow
from portable_runtime import app_base_dir
from settings.settings_manager import SettingsManager


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_main_window_restores_unsaved_backup_when_accepted(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """承認されたの場合、メインウインドウが未保存バックアップを復元することを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    UnsavedBackupManager(backup_path).save(
        UnsavedBackup(text="draft text", encoding="utf-8")
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
    )

    assert window.editor.toPlainText() == "draft text"
    assert window.editor.document().isModified()


def test_main_window_restores_unsaved_backup_session_when_accepted(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """承認されたの場合、メインウインドウが未保存バックアップのセッションを復元することを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    UnsavedBackupManager(backup_path).save_session(
        UnsavedBackupSession(
            tabs=[
                UnsavedBackup(
                    text="first draft",
                    encoding="utf-8",
                    save_file_path=tmp_path / "first.txt",
                ),
                UnsavedBackup(
                    text="second draft",
                    encoding="cp932",
                    save_file_path=None,
                ),
            ],
            current_index=1,
        )
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
    )
    first_editor = window._editor_at(0)
    second_editor = window._editor_at(1)

    assert first_editor is not None
    assert second_editor is not None
    assert window.tab_widget.count() == 2
    assert first_editor.toPlainText() == "first draft"
    assert second_editor.toPlainText() == "second draft"
    assert first_editor.document().isModified()
    assert second_editor.document().isModified()
    assert window.tab_widget.currentIndex() == 1
    assert window.current_encoding == "cp932"


def test_main_window_keeps_unsaved_backup_when_restore_is_declined(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """復元が拒まれたになるの場合、メインウインドウが未保存バックアップを保持することを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    UnsavedBackupManager(backup_path).save(
        UnsavedBackup(text="draft text", encoding="utf-8")
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
    )

    assert window.editor.toPlainText() == ""
    assert backup_path.exists()


def test_main_window_skips_unsaved_backup_restore_when_option_is_disabled(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """設定項目が無効になるの場合、メインウインドウが未保存バックアップの復元を省くことを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    settings_path = tmp_path / "settings.json"
    UnsavedBackupManager(backup_path).save(
        UnsavedBackup(text="draft text", encoding="utf-8")
    )
    SettingsManager(settings_path).save(
        word_wrap_enabled=False,
        line_numbers_enabled=True,
        ruler_enabled=False,
        visible_spaces_enabled=False,
        visible_tabs_enabled=False,
        visible_newlines_enabled=False,
        fixed_column_wrap_enabled=False,
        fixed_column_wrap_column=80,
        startup_restore_enabled=False,
        language_code="ja",
        default_encoding="utf-8",
        newline_code="lf",
        window_width=900,
        window_height=650,
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: pytest.fail("restore dialog should not open"),
    )

    window = MainWindow(
        settings_path=settings_path,
        unsaved_backup_path=backup_path,
    )

    assert window.editor.toPlainText() == ""
    assert backup_path.exists()


def test_main_window_saves_and_clears_unsaved_backup(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """メインウインドウが保存するとともに、未保存バックアップを消すことを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
    )
    window.editor.setPlainText("draft text")
    window.editor.document().setModified(True)

    window._save_unsaved_backup()

    assert backup_path.exists()

    window._save_to_path(tmp_path / "saved.txt")

    assert not backup_path.exists()


def test_main_window_saves_session_for_all_modified_tabs(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """メインウインドウがセッションの用のすべての変更済みのタブを保存することを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
    )
    first_save_file_path = tmp_path / "first.txt"
    window._set_current_file_state(first_save_file_path, "utf-8")
    window.editor.setPlainText("first draft")
    window.editor.document().setModified(True)
    second_editor = window.create_editor_tab(
        text="second draft",
        encoding="cp932",
        modified=True,
    )
    second_editor.document().setModified(True)

    window._save_unsaved_backup()
    session = UnsavedBackupManager(backup_path).load_session()

    assert session is not None
    assert session.current_index == 1
    assert [tab.text for tab in session.tabs] == ["first draft", "second draft"]
    assert session.tabs[0].save_file_path == first_save_file_path
    assert session.tabs[1].save_file_path is None
    assert [tab.encoding for tab in session.tabs] == ["utf-8", "cp932"]


def test_reload_action_has_no_keyboard_shortcut(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """再読込の操作がなしのキー操作を持つことを確認する。"""
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
    )

    assert window.reload_action.shortcut().isEmpty()


def test_reload_file_cancel_keeps_modified_text_after_backup(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """バックアップ後、再読込のファイルのキャンセルが変更済みの文字列を保持することを確認する。"""
    _ = app
    load_file_path = tmp_path / "sample.txt"
    load_file_path.write_text("saved text", encoding="utf-8")
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
        restore_unsaved_backup=False,
    )
    window._set_current_file_state(load_file_path, "utf-8")
    window.editor.setPlainText("draft text")
    window.editor.document().setModified(True)

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    window.reload_file()
    session = UnsavedBackupManager(backup_path).load_session()

    assert window.editor.toPlainText() == "draft text"
    assert window.editor.document().isModified()
    assert load_file_path.read_text(encoding="utf-8") == "saved text"
    assert session is not None
    assert [tab.text for tab in session.tabs] == ["draft text"]


def test_main_window_saves_empty_modified_tab_to_unsaved_session(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """メインウインドウが空の変更済みのタブのへの未保存のセッションを保存することを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
    )
    window.editor.setPlainText("draft")
    window.editor.setPlainText("")
    window.editor.document().setModified(True)

    assert window._save_unsaved_backup()
    session = UnsavedBackupManager(backup_path).load_session()

    assert session is not None
    assert [tab.text for tab in session.tabs] == [""]


def test_main_window_saves_history_snapshot_for_timed_auto_backup(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """メインウインドウが履歴のスナップショットの用の定期の自動のバックアップを保存することを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
    )
    window.editor.setPlainText("snapshot draft")
    window.editor.document().setModified(True)

    assert window._save_unsaved_backup_snapshot()
    manager = UnsavedBackupManager(backup_path)
    latest_session = manager.load_session()
    snapshots = manager.history_snapshots()

    assert latest_session is not None
    assert [tab.text for tab in latest_session.tabs] == ["snapshot draft"]
    assert len(snapshots) == 1
    assert "snapshot draft" in snapshots[0].read_text(encoding="utf-8")


def test_main_window_cancels_close_tab_when_autosave_fails_before_confirmation(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """確認前の自動保存に失敗すると、タブを閉じる操作を取り消すことを確認する。"""
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
    )
    window.editor.setPlainText("must keep")
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
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: pytest.fail("save confirmation should not open"),
    )

    assert not window.close_tab(0)
    assert window.tab_widget.count() == 1
    assert window.editor.toPlainText() == "must keep"


def test_main_window_saving_one_tab_preserves_other_modified_tab_backup(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """メインウインドウの保存時の1件のタブが別の変更済みのタブのバックアップを維持することを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
    )
    first_editor = window.editor
    first_editor.setPlainText("first draft")
    first_editor.document().setModified(True)
    second_editor = window.create_editor_tab(text="second draft", modified=True)
    second_editor.document().setModified(True)
    window.tab_widget.setCurrentIndex(0)

    assert window._save_to_path(tmp_path / "first.txt")
    session = UnsavedBackupManager(backup_path).load_session()

    assert session is not None
    assert [tab.text for tab in session.tabs] == ["second draft"]


def test_main_window_duplicate_tab_is_added_to_unsaved_session(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """メインウインドウの重複したタブが追加されたへの未保存のセッションになることを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
    )
    window.editor.setPlainText("source draft")
    window.editor.document().setModified(True)

    window.duplicate_tab(0)
    session = UnsavedBackupManager(backup_path).load_session()

    assert session is not None
    assert [tab.text for tab in session.tabs] == ["source draft", "source draft"]


def test_main_window_closing_discarded_tab_updates_unsaved_session(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """メインウインドウの終了の破棄されたタブが未保存のセッションを更新することを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
    )
    first_editor = window.editor
    first_editor.setPlainText("discarded draft")
    first_editor.document().setModified(True)
    window.create_editor_tab(text="kept draft", modified=True)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: pytest.fail("unsaved prompt should not open"),
    )

    assert window.close_tab(0)
    session = UnsavedBackupManager(backup_path).load_session()

    assert session is not None
    assert [tab.text for tab in session.tabs] == ["kept draft"]


def test_main_window_saves_existing_file_backup_before_overwrite(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """上書き前、メインウインドウが既存のファイルのバックアップを保存することを確認する。"""
    _ = app
    save_file_path = tmp_path / "saved.txt"
    save_file_path.write_text("old text", encoding="utf-8")
    backup_folder = tmp_path / "backup"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
        restore_unsaved_backup=False,
    )
    window.backup_folder = str(backup_folder)
    window.file_backup_manager = window.file_backup_manager.__class__(
        window._file_backup_folder_for_folder(window.backup_folder)
    )
    window._set_current_file_state(save_file_path, "utf-8")
    window.editor.setPlainText("new text")
    window.editor.document().setModified(True)

    assert window._save_to_path(save_file_path)

    backups = window.file_backup_manager.backups_for_file(save_file_path)
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "old text"
    assert save_file_path.read_text(encoding="utf-8") == "new text"


def test_main_window_default_backup_paths_are_under_internal_folder(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """メインウインドウの既定のバックアップのパスが内部データ用フォルダーであることを確認する。"""
    _ = app
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        restore_unsaved_backup=False,
    )

    assert window.unsaved_backup_manager.backup_path == (
        app_base_dir() / "_internal" / "autosave" / "unsaved_backup.json"
    )
    assert window.file_backup_manager.backup_root == app_base_dir() / "_internal" / "backup"


def test_main_window_custom_backup_folder_is_used_as_file_backup_root(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """設定で指定したフォルダーがファイルバックアップの保存先になることを確認する。"""
    _ = app
    backup_folder = tmp_path / "custom-backup"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        restore_unsaved_backup=False,
    )

    assert window._file_backup_folder_for_folder(str(backup_folder)) == backup_folder
    assert window._unsaved_backup_path() == (
        app_base_dir() / "_internal" / "autosave" / "unsaved_backup.json"
    )


def test_main_window_uses_configured_auto_backup_interval(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """メインウインドウが設定済みの自動のバックアップの間隔を使うことを確認する。"""
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
        auto_backup_interval_minutes=5,
    )

    window = MainWindow(
        settings_path=settings_path,
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
        restore_unsaved_backup=False,
    )

    assert window.auto_backup_interval_minutes == 5
    assert window.auto_save_timer.interval() == 5 * 60 * 1000
    assert window.auto_save_timer.isActive()
    window.editor.setPlainText("unsaved draft")
    backup = UnsavedBackupManager(tmp_path / "autosave" / "unsaved_backup.json")
    assert backup.load_session() is not None


def test_main_window_restores_file_backup_into_editor(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """メインウインドウがファイルのバックアップへのエディターを復元することを確認する。"""
    _ = app
    save_file_path = tmp_path / "saved.txt"
    save_file_path.write_text("backup text", encoding="utf-8")
    backup_folder = tmp_path / "backup"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
        restore_unsaved_backup=False,
    )
    window.backup_folder = str(backup_folder)
    window.file_backup_manager = window.file_backup_manager.__class__(
        window._file_backup_folder_for_folder(window.backup_folder)
    )
    window.file_backup_manager.backup_existing_file(save_file_path)
    save_file_path.write_text("current disk text", encoding="utf-8")
    window._set_current_file_state(save_file_path, "utf-8")
    window.editor.setPlainText("current editor text")
    window.editor.document().setModified(False)

    def select_first_backup(*args, **kwargs) -> tuple[str, bool]:
        """復元候補の先頭をテスト用に選択する。"""
        labels = args[3]
        return labels[0], True

    monkeypatch.setattr(QInputDialog, "getItem", select_first_backup)

    window.restore_file_backup()

    assert window.editor.toPlainText() == "backup text"
    assert window.editor.document().isModified()
    assert save_file_path.read_text(encoding="utf-8") == "current disk text"


def test_main_window_autosaves_modified_text_before_file_backup_restore(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """バックアップから復元する前に、編集中の内容を自動保存することを確認する。"""
    _ = app
    save_file_path = tmp_path / "saved.txt"
    save_file_path.write_text("backup text", encoding="utf-8")
    backup_folder = tmp_path / "backup"
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=tmp_path / "autosave" / "unsaved_backup.json",
        restore_unsaved_backup=False,
    )
    window.backup_folder = str(backup_folder)
    window.file_backup_manager = window.file_backup_manager.__class__(
        window._file_backup_folder_for_folder(window.backup_folder)
    )
    window.file_backup_manager.backup_existing_file(save_file_path)
    window._set_current_file_state(save_file_path, "utf-8")
    window.editor.setPlainText("do not replace")
    window.editor.document().setModified(True)
    saved_sessions: list[list[str]] = []
    original_save_session = window.unsaved_backup_manager.save_session

    def capture_save_session(session: UnsavedBackupSession) -> bool:
        """復元前に保存された未保存セッションを記録する。"""
        saved_sessions.append([tab.text for tab in session.tabs])
        return original_save_session(session)

    def select_first_backup(*args, **kwargs) -> tuple[str, bool]:
        """復元候補の先頭をテスト用に選択する。"""
        labels = args[3]
        return labels[0], True

    monkeypatch.setattr(
        window.unsaved_backup_manager,
        "save_session",
        capture_save_session,
    )
    monkeypatch.setattr(QInputDialog, "getItem", select_first_backup)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: pytest.fail("unsaved prompt should not open"),
    )

    window.restore_file_backup()

    assert saved_sessions[0] == ["do not replace"]
    assert saved_sessions[-1] == ["backup text"]
    assert window.editor.toPlainText() == "backup text"
    assert window.editor.document().isModified()


def test_main_window_restores_unsaved_backup_history_from_restore_menu(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """メインウインドウが未保存バックアップの履歴のからの復元のメニューを復元することを確認する。"""
    _ = app
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    manager = UnsavedBackupManager(backup_path)
    manager.save_history_snapshot(
        UnsavedBackupSession(
            tabs=[
                UnsavedBackup(text="first recovered draft", encoding="utf-8"),
                UnsavedBackup(text="second recovered draft", encoding="cp932"),
            ],
            current_index=1,
        )
    )
    window = MainWindow(
        settings_path=tmp_path / "settings.json",
        unsaved_backup_path=backup_path,
        restore_unsaved_backup=False,
    )
    window.editor.setPlainText("current risky draft")
    window.editor.document().setModified(True)

    def select_history_backup(*args, **kwargs) -> tuple[str, bool]:
        """復元一覧から履歴バックアップを選択する。"""
        labels = args[3]
        history_label = next(
            label for label in labels if "history" in label.lower() or "履歴" in label
        )
        return history_label, True

    monkeypatch.setattr(QInputDialog, "getItem", select_history_backup)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: pytest.fail("unsaved prompt should not open"),
    )

    window.restore_file_backup()
    first_editor = window._editor_at(0)
    second_editor = window._editor_at(1)

    assert first_editor is not None
    assert second_editor is not None
    assert first_editor.toPlainText() == "first recovered draft"
    assert second_editor.toPlainText() == "second recovered draft"
    assert window.tab_widget.currentIndex() == 1
    assert window.current_encoding == "cp932"
