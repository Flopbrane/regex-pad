"""正規表現ヘルプの内容を検証する。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from search.search_engine import SearchEngine, SearchOptions

FIELDS = {
    "section", "topic", "search", "replacement", "input",
    "match", "result", "explanation", "mode",
}
SECTIONS_EN = [
    "Search: basics", "Search: advanced", "Replacement: basics",
    "Replacement: advanced", "Search + replacement examples",
]
SECTIONS_JA = [
    "検索：基本形", "検索：応用形", "置換：基本形",
    "置換：応用形", "検索と置換の組み合わせ例",
]


def load_items(language: str) -> list[dict[str, str]]:
    """指定された言語の正規表現ヘルプ項目を読み込む。"""
    load_file_path = Path(f"resources/regex_help_{language}.json")
    return json.loads(load_file_path.read_text(encoding="utf-8"))


def test_languages_have_matching_examples_and_five_sections() -> None:
    """言語が一致するの例と5つの区分を持つことを確認する。"""
    english_items = load_items("en")
    japanese_items = load_items("ja")
    assert len(english_items) == len(japanese_items) >= 30
    assert list(dict.fromkeys(item["section"] for item in english_items)) == SECTIONS_EN
    assert list(dict.fromkeys(item["section"] for item in japanese_items)) == SECTIONS_JA
    for english, japanese in zip(english_items, japanese_items, strict=True):
        assert set(english) == set(japanese) == FIELDS
        for field in ("search", "replacement", "input", "match", "result", "mode"):
            assert english[field] == japanese[field]
        assert english["topic"] and japanese["topic"]
        assert english["explanation"] and japanese["explanation"]
        re.compile(english["search"], re.MULTILINE)


def test_every_replacement_example_matches_actual_regex_pad_result() -> None:
    """すべての置換の例が実際の正規表現の補うの結果に一致することを確認する。"""
    engine = SearchEngine()
    for item in load_items("en"):
        if item["mode"] != "replace":
            continue
        result = engine.replace_all(
            item["input"],
            item["search"],
            item["replacement"],
            SearchOptions(regular_expression=True),
        )
        assert result.text == item["result"], item["topic"]


def test_invalid_replacement_and_normalization_are_explained_accurately() -> None:
    """不正な置換と正規化が説明済みの正確にであることを確認する。"""
    items = load_items("en")
    invalid = next(item for item in items if item["mode"] == "invalid")
    with pytest.raises(re.error, match="bad escape"):
        SearchEngine().replace_all(
            invalid["input"], invalid["search"], invalid["replacement"],
            SearchOptions(regular_expression=True),
        )
    normalized = next(item for item in items if item["mode"] == "normalization")
    result = SearchEngine().replace_all(
        normalized["input"], normalized["search"], "",
        SearchOptions(regular_expression=True, unicode_normalize=True),
    )
    assert result.text == normalized["result"]


def test_capture_reuse_and_headings_are_explicit_in_both_languages() -> None:
    """取り込みの再利用と見出しが明示的な内の両方の言語であることを確認する。"""
    english_items = load_items("en")
    japanese_items = load_items("ja")
    for items, marker in ((english_items, "reuse"), (japanese_items, "再利用")):
        group_row = next(item for item in items if item["replacement"] == r"## \1")
        assert marker in group_row["explanation"]
        assert group_row["result"].startswith("## 12")
        heading_row = next(item for item in items if item["input"].startswith("1. Plan"))
        assert heading_row["result"] == "## 1. Plan\n## 2. Review"
        invalid_row = next(item for item in items if item["mode"] == "invalid")
        assert r"\d" in invalid_row["explanation"]
        assert r"\g<1>" in invalid_row["explanation"]


def test_unicode_normalization_guides_still_describe_the_dedicated_route() -> None:
    """Unicodeの正規化が引き続きの説明するの専用の経路へ案内することを確認する。"""
    english_readme = Path("README.md").read_text(encoding="utf-8")
    japanese_readme = Path("README_jp.md").read_text(encoding="utf-8")
    for form in ("NFC", "NFD", "NFKC", "NFKD"):
        assert form in english_readme
        assert form in japanese_readme
    assert "[①-⑳]" in english_readme
    assert "[①-⑳]" in japanese_readme
