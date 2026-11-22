"""Portable storage for user shortcuts and plain-text insertion snippets."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


class ShortcutSettingsError(ValueError):
    """Raised when shortcut settings cannot be read or saved safely."""


@dataclass(frozen=True, slots=True)
class TextShortcut:
    """One named plain-text snippet with a keyboard shortcut."""

    identifier: str
    name: str
    shortcut: str
    text: str


@dataclass(slots=True)
class ShortcutSettings:
    """Editable app-action overrides and user-created snippets."""

    overrides: dict[str, str] = field(default_factory=dict)
    snippets: list[TextShortcut] = field(default_factory=list)


def load_shortcut_settings(load_file_path: Path) -> ShortcutSettings:
    """Read settings, using empty defaults only when the file is absent."""
    if not load_file_path.exists():
        return ShortcutSettings()
    try:
        load_data = json.loads(load_file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ShortcutSettingsError(f"Cannot read {load_file_path}: {error}") from error
    if not isinstance(load_data, dict) or load_data.get("version") != 1:
        raise ShortcutSettingsError("Shortcut settings require version 1.")
    raw_overrides = load_data.get("overrides")
    raw_snippets = load_data.get("snippets")
    if not isinstance(raw_overrides, dict) or not isinstance(raw_snippets, list):
        raise ShortcutSettingsError("Shortcut settings have invalid sections.")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in raw_overrides.items()):
        raise ShortcutSettingsError("Shortcut overrides must be strings.")
    snippets: list[TextShortcut] = []
    identifiers: set[str] = set()
    for item in raw_snippets:
        if not isinstance(item, dict) or set(item) != {"id", "name", "shortcut", "text"}:
            raise ShortcutSettingsError("A text shortcut has invalid fields.")
        if not all(isinstance(item[key], str) for key in item):
            raise ShortcutSettingsError("Text shortcut fields must be strings.")
        if not item["id"] or not item["name"].strip() or not item["shortcut"] or not item["text"]:
            raise ShortcutSettingsError("Text shortcut name, key and text are required.")
        if item["id"] in identifiers:
            raise ShortcutSettingsError("Duplicate text shortcut identifier.")
        identifiers.add(item["id"])
        snippets.append(TextShortcut(item["id"], item["name"], item["shortcut"], item["text"]))
    return ShortcutSettings(dict(raw_overrides), snippets)


def save_shortcut_settings(save_file_path: Path, save_data: ShortcutSettings) -> None:
    """Atomically replace the local JSON file after all data is prepared."""
    payload = {
        "version": 1,
        "overrides": save_data.overrides,
        "snippets": [
            {"id": item.identifier, "name": item.name, "shortcut": item.shortcut, "text": item.text}
            for item in save_data.snippets
        ],
    }
    temporary_path: Path | None = None
    try:
        save_file_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", suffix=".tmp",
            prefix=f".{save_file_path.stem}-", dir=save_file_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(payload, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        temporary_path.replace(save_file_path)
    except OSError as error:
        raise ShortcutSettingsError(f"Cannot save {save_file_path}: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
