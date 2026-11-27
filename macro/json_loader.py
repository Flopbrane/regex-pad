"""設定済みのファイルデータモデルに、擬似マクロのJSONファイルを読み込む。"""

from __future__ import annotations

from pathlib import Path

from macro.json_data_model import MacroJsonData
from macro.json_paths import default_macro_folder, resolve_macro_file_path
from macro.macro_parser import MacroParser


class MacroJsonLoadError(ValueError):
    """擬似マクロのJSONファイルを安全に読み込めない場合に発生します。"""

class MacroJsonLoader:
    """設定済みのフォルダからUTF-8 JSONを読み込む。"""

    def __init__(self, macro_folder: Path | None = None) -> None:
        """マクロJSONを読み込む基準フォルダーを設定する。"""
        self.macro_folder: Path = macro_folder or default_macro_folder()

    def load(self, load_file_path: str | Path) -> MacroJsonData:
        """絶対パス、または ``macro_folder`` からの相対パスを1つ読み込みます。"""

        try:
            resolved_load_file_path: Path = resolve_macro_file_path(
                load_file_path,
                self.macro_folder,
            )
            load_text: str = resolved_load_file_path.read_text(encoding="utf-8")
            return MacroParser.parse(load_text)
        except (
            MacroJsonLoadError,
            OSError,
            UnicodeError,
            TypeError,
            ValueError,
        ) as error:
            raise MacroJsonLoadError(
                f"検索/置換プリセットのJSONを読み込めません {load_file_path}: {error}"
            ) from error
