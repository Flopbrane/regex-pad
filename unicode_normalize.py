"""検索で一致した文字列にUnicode正規化を適用する機能を提供する。"""

from __future__ import annotations

import unicodedata
from typing import Literal

NormalizationForm = Literal["NFC", "NFD", "NFKC", "NFKD"]
NORMALIZATION_FORMS: tuple[NormalizationForm, ...] = ("NFC", "NFD", "NFKC", "NFKD")


def normalize_matched_text(
    matched_text: str,
    form: NormalizationForm = "NFKC",
    append_dot_to_circled_number: bool = False,
) -> str:
    """一致範囲の外を変更せずに、検索で一致した1箇所を正規化する。"""
    normalized_text: str = unicodedata.normalize(form, matched_text)
    if (
        append_dot_to_circled_number
        and len(matched_text) == 1
        and "①" <= matched_text <= "⑳"
        and form in ("NFKC", "NFKD")
    ):
        return f"{normalized_text}."
    return normalized_text
