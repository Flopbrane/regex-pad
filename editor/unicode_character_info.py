"""選択文字の Unicode 属性を読み取り専用で取得する。"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class UnicodeCharacterInfo:
    character: str
    code_point: str
    name: str | None
    category: str
    nfkc: str


def inspect_character(character: str) -> UnicodeCharacterInfo:
    """単一の Unicode コードポイントについて標準ライブラリの情報を返す。"""
    if len(character) != 1:
        raise ValueError("Expected exactly one Unicode character")
    return UnicodeCharacterInfo(
        character=character,
        code_point=f"U+{ord(character):04X}",
        name=unicodedata.name(character, None),
        category=unicodedata.category(character),
        nfkc=unicodedata.normalize("NFKC", character),
    )
