"""擬似マクロファイルデータモデルを、UTF-8形式のJSONとして安全に保存する。"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from macro.json_bridge import MacroJsonBridge, MacroJsonBridgeError
from macro.json_data_model import MacroJsonData
from macro.json_paths import default_macro_folder, resolve_macro_file_path


class MacroJsonSaveError(OSError):
    """擬似マクロのJSONファイルを安全に保存できない場合に発生します。"""


class MacroJsonSaver:
    """UTF-8 JSONを設定可能な擬似マクロフォルダにアトミックに書き込む。"""

    def __init__(self, macro_folder: Path | None = None) -> None:
        self.macro_folder: Path = macro_folder or default_macro_folder()

    def save(
        self,
        save_data: MacroJsonData,
        save_file_path: str | Path,
    ) -> Path:
        """モデルを保存し、確定した保存先パスを返す。"""

        temporary_file_path: Path | None = None
        try:
            resolved_save_file_path: Path = resolve_macro_file_path(
                save_file_path,
                self.macro_folder,
            )
            json_data: dict[str, object] = MacroJsonBridge.to_dict(save_data)
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
                f"検索/置換プリセットのJSONを保存できません {save_file_path}: {error}"
            ) from error
