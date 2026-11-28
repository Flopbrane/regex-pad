"""未保存バックアップの管理処理を検証する。"""

from __future__ import annotations

from pathlib import Path

from fileio.unsaved_backup_manager import (
    UnsavedBackup,
    UnsavedBackupManager,
    UnsavedBackupSession,
)


def test_unsaved_backup_manager_saves_and_loads_backup(tmp_path: Path) -> None:
    """未保存バックアップの管理処理が保存するとともに、バックアップを読み込むことを確認する。"""
    manager = UnsavedBackupManager(tmp_path / "autosave" / "unsaved_backup.json")

    manager.save(
        UnsavedBackup(
            text="draft text",
            encoding="utf-8",
            save_file_path=tmp_path / "draft.txt",
        )
    )
    backup = manager.load()

    assert backup is not None
    assert backup.text == "draft text"
    assert backup.encoding == "utf-8"
    assert backup.save_file_path == tmp_path / "draft.txt"


def test_unsaved_backup_manager_returns_none_for_broken_json(tmp_path: Path) -> None:
    """未保存バックアップの管理処理がなしの用の壊れたのJSONを返すことを確認する。"""
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    backup_path.parent.mkdir(parents=True)
    backup_path.write_text("{", encoding="utf-8")

    backup = UnsavedBackupManager(backup_path).load()

    assert backup is None


def test_unsaved_backup_manager_saves_and_loads_session(tmp_path: Path) -> None:
    """未保存バックアップの管理処理が保存するとともに、セッションを読み込むことを確認する。"""
    manager = UnsavedBackupManager(tmp_path / "autosave" / "unsaved_backup.json")

    saved = manager.save_session(
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
    session = manager.load_session()

    assert saved
    assert session is not None
    assert session.current_index == 1
    assert [tab.text for tab in session.tabs] == ["first draft", "second draft"]
    assert [tab.encoding for tab in session.tabs] == ["utf-8", "cp932"]
    assert session.tabs[0].save_file_path == tmp_path / "first.txt"
    assert session.tabs[1].save_file_path is None


def test_unsaved_backup_manager_saves_history_snapshot(tmp_path: Path) -> None:
    """未保存バックアップの管理処理が履歴のスナップショットを保存することを確認する。"""
    manager = UnsavedBackupManager(tmp_path / "autosave" / "unsaved_backup.json")
    session = UnsavedBackupSession(
        tabs=[UnsavedBackup(text="history draft", encoding="utf-8")],
    )

    snapshot_path = manager.save_history_snapshot(session)
    snapshots = manager.history_snapshots()

    assert snapshot_path is not None
    assert snapshot_path.exists()
    assert snapshots == [snapshot_path]
    load_data = snapshot_path.read_text(encoding="utf-8")
    assert "history draft" in load_data


def test_unsaved_backup_manager_keeps_latest_ten_history_files(tmp_path: Path) -> None:
    """次の履歴保存で旧上限の履歴を整理し、最新の復元データと別ファイルを保持する。"""
    manager = UnsavedBackupManager(tmp_path / "autosave" / "unsaved_backup.json")
    session = UnsavedBackupSession(tabs=[UnsavedBackup(text="draft", encoding="utf-8")])
    assert manager.save_session(session)
    history_folder = manager.backup_path.parent / "history"
    history_folder.mkdir()
    old_snapshots = [
        history_folder / f"unsaved_backup-20000101-000000-{index:06d}.json"
        for index in range(50)
    ]
    for path in old_snapshots:
        path.write_bytes(manager.backup_path.read_bytes())
    unrelated = history_folder / "manual-backup.json"
    unrelated.write_text("keep", encoding="utf-8")

    new_snapshot = manager.save_history_snapshot(session)

    assert new_snapshot is not None
    assert manager.history_snapshots() == [new_snapshot, *reversed(old_snapshots[-9:])]
    assert set(history_folder.iterdir()) == {new_snapshot, unrelated, *old_snapshots[-9:]}
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert manager.load_session() == session


def test_unsaved_backup_manager_loads_history_snapshot_session(tmp_path: Path) -> None:
    """未保存バックアップの管理処理が履歴のスナップショットのセッションを読み込むことを確認する。"""
    manager = UnsavedBackupManager(tmp_path / "autosave" / "unsaved_backup.json")
    snapshot_path = manager.save_history_snapshot(
        UnsavedBackupSession(
            tabs=[UnsavedBackup(text="restorable history", encoding="utf-8")],
        )
    )

    assert snapshot_path is not None
    session = manager.load_session_from_path(snapshot_path)

    assert session is not None
    assert [tab.text for tab in session.tabs] == ["restorable history"]


def test_unsaved_backup_manager_clears_backup(tmp_path: Path) -> None:
    """未保存バックアップの管理処理がバックアップを消すことを確認する。"""
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    manager = UnsavedBackupManager(backup_path)
    manager.save(UnsavedBackup(text="draft text", encoding="utf-8"))

    manager.clear()

    assert not backup_path.exists()


def test_unsaved_backup_manager_ignores_replace_permission_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """未保存バックアップの管理処理が置換のアクセス権限エラーを無視することを確認する。"""
    backup_path = tmp_path / "autosave" / "unsaved_backup.json"
    manager = UnsavedBackupManager(backup_path)

    def deny_replace(self: Path, target: Path) -> Path:
        """バックアップを置き換えられない権限状態を再現する。"""
        _ = self, target
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "replace", deny_replace)

    saved = manager.save(UnsavedBackup(text="draft text", encoding="utf-8"))

    assert saved is False
    assert not backup_path.exists()
    assert list(backup_path.parent.glob("tmp*")) == []
