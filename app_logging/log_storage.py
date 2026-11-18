"""Best-effort JSONL persistence for application log records."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def append_log_record(save_file_path: Path, save_data: dict[str, Any]) -> bool:
    """Append one JSON record without allowing logger failures to stop the app."""
    try:
        save_file_path.parent.mkdir(parents=True, exist_ok=True)
        with save_file_path.open("a", encoding="utf-8", newline="\n") as log_file:
            log_file.write(json.dumps(save_data, ensure_ascii=False) + "\n")
    except (OSError, TypeError, ValueError) as error:
        print(f"[LOGGER ERROR] {error}", file=sys.stderr)
        return False
    return True
