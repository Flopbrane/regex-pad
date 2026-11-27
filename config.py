"""ポータブル設定の保存先と旧形式からの移行を扱う。"""

from __future__ import annotations

import shutil
from pathlib import Path

from app_logging import get_logger
from portable_runtime import app_base_dir

CONFIG_FILE_NAME = "config.json"
LEGACY_SETTINGS_FILE_NAME = "settings.json"


def default_config_path(base_dir: Path | None = None) -> Path:
    """ポータブル設定ファイルの既定パスを返す。"""
    return (base_dir or app_base_dir()) / CONFIG_FILE_NAME


def legacy_settings_path(base_dir: Path | None = None) -> Path:
    """config.json移行前の設定ファイルのパスを返す。"""
    return (base_dir or app_base_dir()) / LEGACY_SETTINGS_FILE_NAME


def migrate_legacy_settings_if_needed(
    config_path: Path,
    legacy_path: Path | None = None,
) -> None:
    """config.jsonが存在しない場合に、旧settings.jsonをコピーする。"""
    source_path = legacy_path or config_path.with_name(LEGACY_SETTINGS_FILE_NAME)
    if config_path.exists() or not source_path.exists():
        return

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, config_path)
    except OSError as error:
        get_logger()(
            error,
            "Legacy settings migration failed",
            action="migrate_legacy_settings",
            context={
                "load_file_path": source_path,
                "save_file_path": config_path,
            },
        )
        return
