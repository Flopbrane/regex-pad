"""構成設定を検証する。"""

from __future__ import annotations

import json
from pathlib import Path

from config import (
    default_config_path,
    legacy_settings_path,
    migrate_legacy_settings_if_needed,
)


def test_default_config_path_uses_config_json(tmp_path: Path) -> None:
    """既定の構成設定のパスが構成設定のJSONを使うことを確認する。"""
    assert default_config_path(tmp_path) == tmp_path / "config.json"
    assert legacy_settings_path(tmp_path) == tmp_path / "settings.json"


def test_migrate_legacy_settings_copies_settings_json_to_config_json(
    tmp_path: Path,
) -> None:
    """移行の旧形式の設定が設定のJSONのへの構成設定のJSONをコピーすることを確認する。"""
    legacy_path = tmp_path / "settings.json"
    config_path = tmp_path / "config.json"
    legacy_data = {"font_family": "Meiryo", "font_size": 14}
    legacy_path.write_text(json.dumps(legacy_data), encoding="utf-8")

    migrate_legacy_settings_if_needed(config_path, legacy_path)

    assert json.loads(config_path.read_text(encoding="utf-8")) == legacy_data
    assert legacy_path.exists()


def test_migrate_legacy_settings_does_not_overwrite_existing_config(
    tmp_path: Path,
) -> None:
    """移行の旧形式の設定が既存の構成設定を上書きしないことを確認する。"""
    legacy_path = tmp_path / "settings.json"
    config_path = tmp_path / "config.json"
    legacy_path.write_text(json.dumps({"font_size": 14}), encoding="utf-8")
    config_path.write_text(json.dumps({"font_size": 16}), encoding="utf-8")

    migrate_legacy_settings_if_needed(config_path, legacy_path)

    assert json.loads(config_path.read_text(encoding="utf-8")) == {"font_size": 16}
