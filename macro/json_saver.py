"""Safely save pseudo-macro file data models as UTF-8 JSON."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from macro.json_bridge import MacroJsonBridge, MacroJsonBridgeError
from macro.json_data_model import MacroJsonData
from macro.json_paths import default_macro_folder, resolve_macro_file_path


class MacroJsonSaveError(OSError):
    """Raised when a pseudo-macro JSON file cannot be saved safely."""


class MacroJsonSaver:
    """Write UTF-8 JSON atomically to a configurable pseudo-macro folder."""

    def __init__(self, macro_folder: Path | None = None) -> None:
        self.macro_folder = macro_folder or default_macro_folder()

    def save(
        self,
        save_data: MacroJsonData,
        save_file_path: str | Path,
    ) -> Path:
        """Save a model and return the resolved destination path."""
        temporary_file_path: Path | None = None
        try:
            resolved_save_file_path = resolve_macro_file_path(
                save_file_path,
                self.macro_folder,
            )
            json_data = MacroJsonBridge.to_dict(save_data)
            resolved_save_file_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="\n",
                dir=resolved_save_file_path.parent,
                delete=False,
            ) as temporary_file:
                json.dump(json_data, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.write("\n")
                temporary_file.flush()
                temporary_file_path = Path(temporary_file.name)

            temporary_file_path.replace(resolved_save_file_path)
            return resolved_save_file_path
        except (OSError, TypeError, ValueError, MacroJsonBridgeError) as error:
            if temporary_file_path is not None:
                try:
                    temporary_file_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise MacroJsonSaveError(
                f"cannot save pseudo-macro JSON {save_file_path}: {error}"
            ) from error
