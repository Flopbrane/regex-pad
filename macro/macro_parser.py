"""Parse macro JSON text without losing duplicate-key errors."""

import json
from typing import Any

from macro.json_bridge import MacroJsonBridge
from macro.json_data_model import MacroJsonData


class MacroJsonParseError(ValueError):
    """Malformed JSON or a structure that cannot represent a macro."""


class MacroParser:
    @staticmethod
    def parse(load_text: str) -> MacroJsonData:
        try:
            data = json.loads(load_text, object_pairs_hook=MacroParser._unique_object)
            return MacroJsonBridge.from_dict(data)
        except (ValueError, TypeError) as error:
            raise MacroJsonParseError(str(error)) from error

    @staticmethod
    def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for key, value in pairs:
            if key in data:
                raise MacroJsonParseError(f"duplicate JSON key: {key}")
            data[key] = value
        return data
