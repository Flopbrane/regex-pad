from __future__ import annotations

import shutil
from pathlib import Path

from app_logging import get_logger
from portable_runtime import app_base_dir

CONFIG_FILE_NAME = "config.json"
LEGACY_SETTINGS_FILE_NAME = "settings.json"


def default_config_path(base_dir: Path | None = None) -> Path:
    """Return the default portable config file path."""
    return (base_dir or app_base_dir()) / CONFIG_FILE_NAME


def legacy_settings_path(base_dir: Path | None = None) -> Path:
    """Return the old settings file path used before config.json."""
    return (base_dir or app_base_dir()) / LEGACY_SETTINGS_FILE_NAME


def migrate_legacy_settings_if_needed(
    config_path: Path,
    legacy_path: Path | None = None,
) -> None:
    """Copy old settings.json into config.json when config.json does not exist yet."""
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
