"""正規化を検証する。"""

from __future__ import annotations

import pytest

from normalise import apply_normalise_operation


@pytest.mark.parametrize(
    ("operation_id", "source_text", "expected_text", "expected_count"),
    [
        (
            "japanese_punctuation_to_fullwidth_space",
            "注意、確認。完了",
            "注意　確認　完了",
            2,
        ),
        (
            "halfwidth_katakana_to_fullwidth",
            "ﾊﾟｿｺﾝの練習",
            "パソコンの練習",
            1,
        ),
        (
            "fullwidth_space_to_halfwidth_space",
            "氏名　佐藤",
            "氏名 佐藤",
            1,
        ),
        (
            "fullwidth_digits_symbols_to_halfwidth",
            "価格：１，２００円！",
            "価格:1,200円!",
            2,
        ),
        (
            "fullwidth_alphabet_to_halfwidth",
            "ＷｏｒｄＰｒｅｓｓを使う",
            "WordPressを使う",
            1,
        ),
    ],
)
def test_apply_normalise_operation(
    operation_id: str,
    source_text: str,
    expected_text: str,
    expected_count: int,
) -> None:
    """適用の正規化の操作を確認する。"""
    result = apply_normalise_operation(source_text, operation_id)

    assert result.text == expected_text
    assert result.count == expected_count
