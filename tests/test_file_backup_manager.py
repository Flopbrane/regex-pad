"""ファイルのバックアップの管理処理を検証する。"""

from __future__ import annotations

from fileio.file_backup_manager import FileBackupManager


def test_file_backup_manager_creates_backup_for_existing_file(tmp_path) -> None:
    """ファイルのバックアップの管理処理がバックアップの用の既存のファイルを作ることを確認する。"""
    load_file_path = tmp_path / "article.txt"
    load_file_path.write_text("old text", encoding="utf-8")
    manager = FileBackupManager(tmp_path / "backups")

    backup_path = manager.backup_existing_file(load_file_path)

    assert backup_path is not None
    assert backup_path.read_text(encoding="utf-8") == "old text"
    assert manager.backups_for_file(load_file_path) == [backup_path]


def test_file_backup_manager_skips_missing_file(tmp_path) -> None:
    """ファイルのバックアップの管理処理が不足したファイルを省くことを確認する。"""
    load_file_path = tmp_path / "missing.txt"
    manager = FileBackupManager(tmp_path / "backups")

    backup_path = manager.backup_existing_file(load_file_path)

    assert backup_path is None
    assert manager.backups_for_file(load_file_path) == []


def test_file_backup_manager_keeps_only_latest_backup_per_file(tmp_path) -> None:
    """ファイルごとに最新のバックアップだけを保持することを確認する。"""
    first_file_path = tmp_path / "first.txt"
    second_file_path = tmp_path / "second.txt"
    manager = FileBackupManager(tmp_path / "backups")

    for index in range(25):
        first_file_path.write_text(f"first {index}", encoding="utf-8")
        manager.backup_existing_file(first_file_path, retention_count=20)
    second_file_path.write_text("second", encoding="utf-8")
    manager.backup_existing_file(second_file_path, retention_count=20)

    first_backups = manager.backups_for_file(first_file_path)
    second_backups = manager.backups_for_file(second_file_path)

    assert len(first_backups) == 1
    assert first_backups[0].read_text(encoding="utf-8") == "first 24"
    assert first_backups[0].name == "first.txt.latest.bak"
    assert len(second_backups) == 1
    assert second_backups[0].read_text(encoding="utf-8") == "second"
    assert second_backups[0].name == "second.txt.latest.bak"
