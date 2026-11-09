from __future__ import annotations

import pytest

from unicode_normalize import NormalizationForm, normalize_matched_text


@pytest.mark.parametrize(
    ("source_text", "expected_text"),
    [("①", "1."), ("②", "2."), ("⑩", "10."), ("⑳", "20.")],
)
def test_nfkc_can_append_dot_to_supported_circled_number(
    source_text: str,
    expected_text: str,
) -> None:
    assert normalize_matched_text(source_text, "NFKC", True) == expected_text


@pytest.mark.parametrize("form", ["NFC", "NFD"])
def test_canonical_forms_do_not_append_dot_to_unchanged_circled_number(
    form: NormalizationForm,
) -> None:
    assert normalize_matched_text("①", form, True) == "①"


def test_dot_is_not_appended_to_non_circled_matches() -> None:
    assert normalize_matched_text("１２３", "NFKC", True) == "123"
    assert normalize_matched_text("ＡＢＣ", "NFKC", True) == "ABC"


def test_normalize_matched_text_handles_empty_and_multiline_text() -> None:
    assert normalize_matched_text("", "NFKC", True) == ""
    assert normalize_matched_text("①\n②", "NFKC", True) == "1\n2"
