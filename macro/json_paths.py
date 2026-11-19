"""Path resolution shared by pseudo-macro JSON loading and saving."""

from __future__ import annotations

from pathlib import Path

from portable_runtime import app_base_dir


def default_macro_folder() -> Path:
    """Return the default user-editable pseudo-macro folder."""
    return app_base_dir() / "macro"


def resolve_macro_file_path(
    file_path: str | Path,
    macro_folder: Path,
) -> Path:
    """Resolve an absolute path or a path contained by ``macro_folder``."""
    requested_path = Path(file_path)
    if requested_path.is_absolute():
        return requested_path.resolve()

    resolved_folder = macro_folder.resolve()
    resolved_path = (resolved_folder / requested_path).resolve()
    if not resolved_path.is_relative_to(resolved_folder):
        raise ValueError(
            f"relative macro path must stay inside the macro folder: {file_path}"
        )
    return resolved_path
