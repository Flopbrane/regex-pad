"""Load pseudo-macro JSON files into the configured file data model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from macro.json_bridge import MacroJsonBridge, MacroJsonBridgeError
from macro.json_data_model import MacroJsonData
from macro.json_paths import default_macro_folder, resolve_macro_file_path


class MacroJsonLoadError(ValueError):
    """Raised when a pseudo-macro JSON file cannot be loaded safely."""


class MacroJsonLoader:
    """Read UTF-8 JSON from a configurable pseudo-macro folder."""

    def __init__(self, macro_folder: Path | None = None) -> None:
        self.macro_folder: Path = macro_folder or default_macro_folder()

    def load(self, load_file_path: str | Path) -> MacroJsonData:
        """Load one absolute path or a path relative to ``macro_folder``."""
        try:
            resolved_load_file_path: Path = resolve_macro_file_path(
                load_file_path,
                self.macro_folder,
            )
            load_text: str = resolved_load_file_path.read_text(encoding="utf-8")
            load_data = json.loads(
                load_text,
                object_pairs_hook=self._object_without_duplicate_keys,
            )
            return MacroJsonBridge.from_dict(load_data)
        except (
            MacroJsonLoadError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            MacroJsonBridgeError,
            TypeError,
            ValueError,
        ) as error:
            raise MacroJsonLoadError(
                f"cannot load pseudo-macro JSON {load_file_path}: {error}"
            ) from error

    @staticmethod
    def _object_without_duplicate_keys(
        pairs: list[tuple[str, Any]],
    ) -> dict[str, Any]:
        load_data: dict[str, Any] = {}
        for key, value in pairs:
            if key in load_data:
                raise MacroJsonLoadError(f"duplicate JSON key: {key}")
            load_data[key] = value
        return load_data
