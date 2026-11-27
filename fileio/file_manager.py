"""テキストファイルの読込、保存と改行コードを扱う。"""

from __future__ import annotations

import tempfile
from pathlib import Path


class FileManager:
    """文字コードと改行を扱うテキストファイル操作。"""
    def load_text(self, load_file_path: Path, encoding: str = "utf-8") -> str:
        """指定された文字コードで本文を読み込む。"""
        return load_file_path.read_text(encoding=encoding)

    def save_text(
        self,
        save_file_path: Path,
        save_data: str,
        encoding: str = "utf-8",
        newline_code: str = "lf",
    ) -> None:
        """指定の文字コードと改行方式で本文を書き込む。"""
        save_file_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_save_data = self._normalize_newlines(save_data, newline_code)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding=encoding,
            newline="",
            dir=save_file_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_file.write(normalized_save_data)
            temporary_file.flush()
            temporary_file_path = Path(temporary_file.name)

        temporary_file_path.replace(save_file_path)

    def _normalize_newlines(self, save_data: str, newline_code: str) -> str:
        """本文の改行を指定形式にそろえる。"""
        normalized_data = save_data.replace("\r\n", "\n").replace("\r", "\n")
        if newline_code == "crlf":
            return normalized_data.replace("\n", "\r\n")
        if newline_code == "cr":
            return normalized_data.replace("\n", "\r")
        return normalized_data
