from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_KEYS = {
    "category",
    "label",
    "pattern",
    "description",
    "example_text",
    "usage_example",
    "matches",
    "replace_with",
    "replacement_result",
}


def load_help_items(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_english_and_japanese_help_have_matching_structure() -> None:
    english_items = load_help_items(Path("resources/regex_help_en.json"))
    japanese_items = load_help_items(Path("resources/regex_help_ja.json"))

    assert len(english_items) == len(japanese_items)
    for english_item, japanese_item in zip(english_items, japanese_items, strict=True):
        assert set(english_item) == REQUIRED_KEYS
        assert set(japanese_item) == REQUIRED_KEYS


def test_english_and_japanese_help_keep_same_regex_patterns() -> None:
    english_items = load_help_items(Path("resources/regex_help_en.json"))
    japanese_items = load_help_items(Path("resources/regex_help_ja.json"))

    english_patterns = [item["pattern"] for item in english_items]
    japanese_patterns = [item["pattern"] for item in japanese_items]

    assert japanese_patterns == english_patterns


def test_japanese_help_contains_readable_japanese_text() -> None:
    japanese_items = load_help_items(Path("resources/regex_help_ja.json"))

    assert japanese_items[0]["category"] == "位置"
    assert japanese_items[0]["label"] == "行の先頭"
    assert "位置" in japanese_items[0]["description"]


def test_help_contains_complex_and_office_samples() -> None:
    japanese_items = load_help_items(Path("resources/regex_help_ja.json"))
    labels_by_category = {
        str(item["category"]): {
            str(other_item["label"])
            for other_item in japanese_items
            if other_item["category"] == item["category"]
        }
        for item in japanese_items
    }

    assert "同じ単語が続く場所" in labels_by_category["複雑な組み合わせサンプル"]
    assert "電話番号" in labels_by_category["事務・計算・住所"]
    assert "CSVの列を並べ替える" in labels_by_category["置換サンプル"]
    assert "全角文字のみ" in labels_by_category["文字"]
    assert "日本語の句読点を全角スペースへ" in labels_by_category["組み合わせ"]
    assert "全角アルファベットを半角へ" in labels_by_category["組み合わせ"]
    assert "丸数字を通常の数字へ" in labels_by_category["Unicode正規化"]


def test_unicode_normalization_help_and_readmes_explain_the_dedicated_route() -> None:
    english_items = load_help_items(Path("resources/regex_help_en.json"))
    japanese_items = load_help_items(Path("resources/regex_help_ja.json"))
    english_item = next(
        item for item in english_items if item["pattern"] == "[①-⑳]"
    )
    japanese_item = next(
        item for item in japanese_items if item["pattern"] == "[①-⑳]"
    )

    assert "NFKC" in english_item["description"]
    assert "NFKD" in english_item["description"]
    assert "Unicode正規化置換" in japanese_item["description"]
    assert japanese_item["replacement_result"] == "1.朝 2.昼 10.まとめ"

    english_readme = Path("README.md").read_text(encoding="utf-8")
    japanese_readme = Path("README_jp.md").read_text(encoding="utf-8")
    for form in ("NFC", "NFD", "NFKC", "NFKD"):
        assert form in english_readme
        assert form in japanese_readme
    assert "[①-⑳]" in english_readme
    assert "[①-⑳]" in japanese_readme
