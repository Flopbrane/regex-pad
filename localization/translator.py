"""言語別の翻訳辞書を読み込み、表示文字列を取得する。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Translator:
    """現在の言語に対応する画面の文言を提供する。"""
    def __init__(self, resources_path: Path, language_code: str = "ja") -> None:
        """翻訳リソースの場所と言語を設定する。"""
        self.resources_path = resources_path
        self.language_code = language_code
        self._texts = self._load_texts(language_code)

    def set_language(self, language_code: str) -> None:
        """使用言語を切り替えて翻訳を読み直す。"""
        self.language_code = language_code
        self._texts = self._load_texts(language_code)

    def text(self, key: str, **values: object) -> str:
        """翻訳キーから文言を取得し、指定値を埋め込む。"""
        text = str(self._texts.get(key, key))
        if values:
            return text.format(**values)
        return text

    def _load_texts(self, language_code: str) -> dict[str, Any]:
        """指定言語の翻訳辞書を読み込む。"""
        language_path = self.resources_path / f"app_text_{language_code}.json"
        if not language_path.exists():
            language_path = self.resources_path / "app_text_en.json"
        return json.loads(language_path.read_text(encoding="utf-8"))
