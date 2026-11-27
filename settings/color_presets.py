"""ポータブルアプリの編集可能な文字色と背景色の候補を読み込む。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portable_runtime import app_base_dir, bundled_base_dir

COLOR_PRESETS_FILE_NAME = "color_presets.json"


class ColorPresetConfigError(ValueError):
    """有効な色の候補設定を読み込めない場合に発生する。"""


@dataclass(frozen=True)
class ColorPreset:
    """日英の表示名を持つCSS色の候補1件を表す。"""

    identifier: str
    name_ja: str
    name_en: str
    value: str
    shortcuts: tuple[str, ...] = ()

    def display_name(self, language_code: str) -> str:
        """指定言語で色候補の表示名を返す。"""
        return self.name_en if language_code == "en" else self.name_ja


@dataclass(frozen=True)
class ColorPresetCatalog:
    """JSONから読み込んだ文字色と背景色の候補をまとめる。"""

    text_colors: tuple[ColorPreset, ...]
    background_colors: tuple[ColorPreset, ...]
    source_path: Path


def load_color_preset_catalog(
    editable_path: Path | None = None,
    bundled_default_path: Path | None = None,
) -> ColorPresetCatalog:
    """編集可能な色の候補一覧を読み込み、必要なら同梱の既定JSONを使う。"""
    editable_path = editable_path or app_base_dir() / COLOR_PRESETS_FILE_NAME
    bundled_default_path = bundled_default_path or (
        bundled_base_dir() / "resources" / COLOR_PRESETS_FILE_NAME
    )
    if not editable_path.exists() and bundled_default_path.exists():
        _copy_default_safely(bundled_default_path, editable_path)

    attempted_paths: list[Path] = []
    for load_path in (editable_path, bundled_default_path):
        resolved_path = load_path.resolve()
        if resolved_path in attempted_paths or not load_path.exists():
            continue
        attempted_paths.append(resolved_path)
        try:
            return _load_catalog(load_path)
        except (ColorPresetConfigError, OSError, json.JSONDecodeError):
            continue

    raise ColorPresetConfigError(
        "A valid color_presets.json could not be loaded from the app or bundle folder."
    )


def _copy_default_safely(source_path: Path, save_file_path: Path) -> None:
    """書き込み途中のJSONが公開されないように、同梱の既定値をコピーする。"""
    try:
        save_file_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{save_file_path.stem}-",
            suffix=".tmp",
            dir=save_file_path.parent,
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            shutil.copyfile(source_path, temporary_path)
            temporary_path.replace(save_file_path)
        finally:
            temporary_path.unlink(missing_ok=True)
    except OSError:
        return


def _load_catalog(load_file_path: Path) -> ColorPresetCatalog:
    """JSONファイルから色候補一覧を読み込んで検証する。"""
    load_data: Any = json.loads(load_file_path.read_text(encoding="utf-8"))
    if not isinstance(load_data, dict):
        raise ColorPresetConfigError("The color preset root must be an object.")
    text_colors = _parse_preset_list(load_data.get("text_colors"), "text_colors")
    background_colors = _parse_preset_list(
        load_data.get("background_colors"),
        "background_colors",
    )
    if not text_colors or not background_colors:
        raise ColorPresetConfigError("Both color preset lists must contain entries.")
    return ColorPresetCatalog(text_colors, background_colors, load_file_path)


def _parse_preset_list(load_data: object, field_name: str) -> tuple[ColorPreset, ...]:
    """JSON内の色候補の一覧を検証してモデルに変換する。"""
    if not isinstance(load_data, list):
        raise ColorPresetConfigError(f"{field_name} must be an array.")
    presets: list[ColorPreset] = []
    identifiers: set[str] = set()
    for item in load_data:
        if not isinstance(item, dict):
            raise ColorPresetConfigError(f"Each {field_name} entry must be an object.")
        identifier = _required_string(item, "id")
        if identifier in identifiers:
            raise ColorPresetConfigError(f"Duplicate color preset id: {identifier}")
        identifiers.add(identifier)
        names = item.get("name")
        if not isinstance(names, dict):
            raise ColorPresetConfigError(f"Preset {identifier} requires localized names.")
        shortcut_data = item.get("shortcuts", [])
        if not isinstance(shortcut_data, list) or not all(
            isinstance(shortcut, str) and shortcut.strip()
            for shortcut in shortcut_data
        ):
            raise ColorPresetConfigError(f"Preset {identifier} has invalid shortcuts.")
        presets.append(
            ColorPreset(
                identifier=identifier,
                name_ja=_required_string(names, "ja"),
                name_en=_required_string(names, "en"),
                value=_required_string(item, "value"),
                shortcuts=tuple(shortcut_data),
            )
        )
    return tuple(presets)


def _required_string(load_data: dict[str, object], field_name: str) -> str:
    """必須項目を空でない文字列として読み取る。"""
    value = load_data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ColorPresetConfigError(f"{field_name} must be a non-empty string.")
    return value.strip()
