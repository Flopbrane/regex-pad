"""重複キーに関するエラーを失うことなく、マクロのJSONテキストを解析する。"""

import json
from typing import Any

from macro.json_bridge import MacroJsonBridge
from macro.json_data_model import MacroJsonData


class MacroJsonParseError(ValueError):
    """不正な形式のJSON、あるいはマクロを表現できない構造のError対応シンボル。"""

class MacroParser:
    """JSONテキストを ``MacroJsonData`` に変換する。"""
    @staticmethod
    def parse(load_text: str) -> MacroJsonData:
        """JSONテキストを ``MacroJsonData`` に変換する。"""
        try:
            data = json.loads(load_text, object_pairs_hook=MacroParser._unique_object)
            return MacroJsonBridge.from_dict(data)
        except (ValueError, TypeError) as error:
            raise MacroJsonParseError(str(error)) from error

    @staticmethod
    def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        """重複キーを検出するための ``object_pairs_hook``。"""
        data: dict[str, Any] = {}
        for key, value in pairs:
            if key in data:
                raise MacroJsonParseError(f"duplicate JSON key: {key}")
            data[key] = value
        return data
