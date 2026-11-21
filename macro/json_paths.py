"""JSONの読み込みおよび保存（疑似マクロによるもの）で共通して利用されるパス解決。"""

from __future__ import annotations

from pathlib import Path

from portable_runtime import app_base_dir


def default_macro_folder() -> Path:
    """検索・置換プリセットを保存するためのデフォルトのローカルフォルダーを返す。"""

    return app_base_dir() / "macro" / "preset_json_files"


def configured_macro_folder(saved_folder: str | Path) -> Path:
    """以前のデフォルトを移行しつつ、カスタムフォルダーの選択を保持。"""
    legacy_default: Path = app_base_dir() / "macro"
    if not saved_folder or Path(saved_folder).resolve() == legacy_default.resolve():
        return default_macro_folder()
    return Path(saved_folder)


def resolve_macro_file_path(
    file_path: str | Path,
    macro_folder: Path,
) -> Path:
    """``macro_folder`` に含まれる絶対パスまたは相対パスを解決。"""
    requested_path = Path(file_path)
    if requested_path.is_absolute():
        return requested_path.resolve()

    resolved_folder: Path = macro_folder.resolve()
    resolved_path: Path = (resolved_folder / requested_path).resolve()
    if not resolved_path.is_relative_to(resolved_folder):
        raise ValueError(
            f"relative macro path must stay inside the macro folder: {file_path}"
        )
    return resolved_path
