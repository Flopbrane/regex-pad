"""Path resolution shared by pseudo-macro JSON loading and saving."""

from __future__ import annotations

from pathlib import Path

from portable_runtime import app_base_dir


def default_macro_folder() -> Path:
    """Return the default local folder for saved search/replace presets."""
    return app_base_dir() / "macro" / "preset_json_files"


def configured_macro_folder(saved_folder: str | Path) -> Path:
    """Migrate the former default while retaining a custom folder choice."""
    legacy_default = app_base_dir() / "macro"
    if not saved_folder or Path(saved_folder).resolve() == legacy_default.resolve():
        return default_macro_folder()
    return Path(saved_folder)


def resolve_macro_file_path(
    file_path: str | Path,
    macro_folder: Path,
) -> Path:
    """Resolve an absolute path or a path contained by ``macro_folder``."""
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
