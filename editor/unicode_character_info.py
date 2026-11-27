"""選択文字の Unicode 属性を読み取り専用で取得する。"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QTextCursor


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


def character_at_cursor(cursor: QTextCursor) -> str | None:
    """Qtの位置から、書記素の境界にかかわらず1コードポイントを取得する。"""
    document = cursor.document()
    end = document.characterCount() - 1  # Qtの文末には本文外の区切りがある。
    if end <= 0:
        return None
    position = min(cursor.selectionStart(), end - 1)
    character = document.characterAt(position)
    code = ord(character)
    if 0xDC00 <= code <= 0xDFFF and position > 0:
        previous = ord(document.characterAt(position - 1))
        if 0xD800 <= previous <= 0xDBFF:
            return chr(0x10000 + ((previous - 0xD800) << 10) + (code - 0xDC00))
    if 0xD800 <= code <= 0xDBFF and position + 1 < end:
        following = ord(document.characterAt(position + 1))
        if 0xDC00 <= following <= 0xDFFF:
            return chr(0x10000 + ((code - 0xD800) << 10) + (following - 0xDC00))
    # QTextDocumentでは段落境界をU+2029で表す。エディター上では改行として扱う。
    return "\n" if character == "\u2029" else character
