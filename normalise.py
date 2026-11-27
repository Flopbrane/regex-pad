"""既定の文字列正規化操作を実行し、置換結果を作る。"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class NormaliseOperation:
    """画面で選択できる正規化操作を表す。"""
    operation_id: str
    label_key: str
    pattern: re.Pattern[str]
    replacement: str | Callable[[re.Match[str]], str]


@dataclass(frozen=True)
class NormaliseResult:
    """正規化後の本文と変更件数を保持する。"""
    text: str
    count: int


NORMALISE_OPERATIONS: tuple[NormaliseOperation, ...] = (
    NormaliseOperation(
        "japanese_punctuation_to_fullwidth_space",
        "normalise.operation.japanese_punctuation_to_fullwidth_space",
        re.compile("[、。]"),
        "　",
    ),
    NormaliseOperation(
        "halfwidth_katakana_to_fullwidth",
        "normalise.operation.halfwidth_katakana_to_fullwidth",
        re.compile("[ｦ-ﾟ]+"),
        lambda match: unicodedata.normalize("NFKC", match.group(0)),
    ),
    NormaliseOperation(
        "fullwidth_space_to_halfwidth_space",
        "normalise.operation.fullwidth_space_to_halfwidth_space",
        re.compile("　+"),
        " ",
    ),
    NormaliseOperation(
        "fullwidth_digits_symbols_to_halfwidth",
        "normalise.operation.fullwidth_digits_symbols_to_halfwidth",
        re.compile("[０-９！-／：-＠［-｀｛-～￥]+"),
        lambda match: unicodedata.normalize("NFKC", match.group(0)),
    ),
    NormaliseOperation(
        "fullwidth_alphabet_to_halfwidth",
        "normalise.operation.fullwidth_alphabet_to_halfwidth",
        re.compile("[Ａ-Ｚａ-ｚ]+"),
        lambda match: unicodedata.normalize("NFKC", match.group(0)),
    ),
)


def normalise_operations() -> tuple[NormaliseOperation, ...]:
    """利用できる正規化操作を返す。"""
    return NORMALISE_OPERATIONS


def apply_normalise_operation(text: str, operation_id: str) -> NormaliseResult:
    """指定された正規化操作を対象の文字列に適用する。"""
    operation = _operation_by_id(operation_id)
    normalised_text, count = operation.pattern.subn(operation.replacement, text)
    return NormaliseResult(normalised_text, count)


def _operation_by_id(operation_id: str) -> NormaliseOperation:
    """操作IDから正規化操作を取得する。"""
    for operation in NORMALISE_OPERATIONS:
        if operation.operation_id == operation_id:
            return operation
    raise ValueError(f"Unknown normalise operation: {operation_id}")
