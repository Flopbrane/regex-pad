"""未保存の文書を復元するためのバックアップを管理する。"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app_logging import LogLevel, get_logger


@dataclass(frozen=True)
class UnsavedBackup:
    """未保存の文書1件と復元に必要な情報を保持する。"""
    text: str
    encoding: str
    save_file_path: Path | None = None


@dataclass(frozen=True)
class UnsavedBackupSession:
    """複数の未保存文書を復元可能なセッションとしてまとめる。"""
    tabs: list[UnsavedBackup]
    current_index: int = 0


class UnsavedBackupManager:
    """復元用データと履歴スナップショットを読み書きする。"""
    HISTORY_RETENTION_COUNT = 50

    def __init__(self, backup_path: Path) -> None:
        """復元用データと履歴の保存先を設定する。"""
        self.backup_path = backup_path

    def load(self) -> UnsavedBackup | None:
        """現在の未保存バックアップから文書を読み込む。"""
        session = self.load_session()
        if session is None or not session.tabs:
            return None
        return session.tabs[min(max(session.current_index, 0), len(session.tabs) - 1)]

    def load_session(self) -> UnsavedBackupSession | None:
        """既定のパスから未保存セッションを読み込む。"""
        return self.load_session_from_path(self.backup_path)

    def load_session_from_path(self, load_file_path: Path) -> UnsavedBackupSession | None:
        """指定パスのバックアップをセッションとして読み込む。"""
        if not load_file_path.exists():
            return None

        try:
            load_data: dict[str, Any] = json.loads(
                load_file_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            get_logger().exception(
                error,
                "Unsaved backup could not be loaded",
                level=LogLevel.WARNING,
                action="load_unsaved_backup",
                context={"load_file_path": load_file_path},
            )
            return None

        tabs_data = load_data.get("tabs")
        if isinstance(tabs_data, list):
            tabs = [
                backup
                for tab_data in tabs_data
                if isinstance(tab_data, dict)
                for backup in [self._backup_from_data(tab_data)]
                if backup is not None
            ]
            if not tabs:
                return None
            current_index = load_data.get("current_index", 0)
            if not isinstance(current_index, int):
                current_index = 0
            return UnsavedBackupSession(
                tabs=tabs,
                current_index=min(max(current_index, 0), len(tabs) - 1),
            )

        backup = self._backup_from_data(load_data)
        if backup is None:
            return None
        return UnsavedBackupSession(tabs=[backup], current_index=0)

    def _backup_from_data(self, load_data: dict[str, Any]) -> UnsavedBackup | None:
        """保存情報を未保存文書のモデルに変換する。"""
        text = load_data.get("text")
        encoding = load_data.get("encoding")
        save_file_path = load_data.get("save_file_path")
        if not isinstance(text, str) or not isinstance(encoding, str):
            return None

        return UnsavedBackup(
            text=text,
            encoding=encoding,
            save_file_path=Path(save_file_path) if isinstance(save_file_path, str) else None,
        )

    def save(self, backup: UnsavedBackup) -> bool:
        """未保存文書1件をバックアップする。"""
        return self.save_session(UnsavedBackupSession(tabs=[backup]))

    def save_session(self, session: UnsavedBackupSession) -> bool:
        """複数文書の未保存セッションを保存する。"""
        return self._write_session(self.backup_path, session)

    def save_history_snapshot(self, session: UnsavedBackupSession) -> Path | None:
        """復元用の履歴スナップショットを保存する。"""
        if not session.tabs:
            return None

        history_folder = self.backup_path.parent / "history"
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        snapshot_path = history_folder / f"unsaved_backup-{timestamp}.json"
        if not self._write_session(snapshot_path, session):
            return None
        self._prune_history(history_folder)
        return snapshot_path

    def history_snapshots(self) -> list[Path]:
        """利用可能な履歴スナップショットを列挙する。"""
        history_folder = self.backup_path.parent / "history"
        if not history_folder.exists():
            return []
        return sorted(
            (item for item in history_folder.iterdir() if item.is_file()),
            key=lambda item: item.name,
            reverse=True,
        )

    def _write_session(
        self,
        save_file_path: Path,
        session: UnsavedBackupSession,
    ) -> bool:
        """未保存セッションを指定ファイルに書き出す。"""
        tabs = session.tabs
        if not tabs:
            self.clear()
            return True

        temporary_file_path: Path | None = None
        try:
            save_file_path.parent.mkdir(parents=True, exist_ok=True)
            save_data = {
                "version": 2,
                "current_index": min(max(session.current_index, 0), len(tabs) - 1),
                "tabs": [
                    {
                        "text": tab.text,
                        "encoding": tab.encoding,
                        "save_file_path": (
                            str(tab.save_file_path)
                            if tab.save_file_path is not None
                            else None
                        ),
                    }
                    for tab in tabs
                ],
            }
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=save_file_path.parent,
                delete=False,
            ) as temporary_file:
                json.dump(save_data, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.flush()
                temporary_file_path = Path(temporary_file.name)

            temporary_file_path.replace(save_file_path)
        except OSError as error:
            if temporary_file_path is not None:
                try:
                    temporary_file_path.unlink(missing_ok=True)
                except OSError as cleanup_error:
                    get_logger().exception(
                        cleanup_error,
                        "Temporary unsaved-backup file could not be removed",
                        level=LogLevel.WARNING,
                        action="cleanup_unsaved_backup_temp",
                        context={"save_file_path": temporary_file_path},
                    )
            get_logger()(
                error,
                "Unsaved backup could not be saved",
                action="save_unsaved_backup",
                context={"save_file_path": save_file_path},
            )
            return False
        return True

    def _prune_history(self, history_folder: Path) -> None:
        """保持条件を超えた履歴スナップショットを整理する。"""
        snapshots = self.history_snapshots()
        for snapshot_path in snapshots[self.HISTORY_RETENTION_COUNT :]:
            try:
                snapshot_path.unlink(missing_ok=True)
            except OSError as error:
                get_logger().exception(
                    error,
                    "Old unsaved-backup snapshot could not be removed",
                    level=LogLevel.WARNING,
                    action="prune_unsaved_backup_history",
                    context={"save_file_path": snapshot_path},
                )
                continue

    def clear(self) -> None:
        """現在の未保存バックアップを消す。"""
        try:
            self.backup_path.unlink(missing_ok=True)
        except OSError as error:
            get_logger().exception(
                error,
                "Unsaved backup could not be cleared",
                level=LogLevel.WARNING,
                action="clear_unsaved_backup",
                context={"save_file_path": self.backup_path},
            )
            return
