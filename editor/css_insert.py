"""CSS挿入メニューに表示する定型文を読み込み、検証する。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path

from editor.tag_insert import CURSOR_PLACEHOLDER, PLACEHOLDER_PATTERN
from portable_runtime import bundled_base_dir
from search.css_lint import parse_inline_style_values

CSS_INSERT_DICTIONARY = "css_insert_dict.json"
CSS_INSERT_CATEGORIES = ("text", "color", "spacing", "decoration", "layout", "user")


@dataclass(frozen=True)
class CssInsertSnippet:
    """メニューの表示名、挿入内容、カーソル位置を保持する。"""

    label: str
    label_key: str
    declaration: str
    cursor_offset: int
    category: str

    @property
    def identifier(self) -> str:
        """同梱項目との照合に使う表示キーまたは表示名を返す。"""
        return self.label_key or self.label


def parse_css_insert_snippets(data: object) -> tuple[CssInsertSnippet, ...]:
    """各項目に表示名と単一のCSS宣言があることを確認する。"""
    if not isinstance(data, list):
        raise TypeError("CSS insertion dictionary must be an array.")
    snippets: list[CssInsertSnippet] = []
    labels: set[str] = set()
    resources = bundled_base_dir() / "resources"
    translated_labels = set(json.loads((resources / "app_text_ja.json").read_text(encoding="utf-8"))) & set(
        json.loads((resources / "app_text_en.json").read_text(encoding="utf-8"))
    )
    for index, row in enumerate(data, 1):
        if not isinstance(row, dict) or row.keys() - {"label", "label_key", "template", "category"}:
            raise ValueError(f"CSS insertion entry {index} has invalid fields.")
        label, label_key, template = row.get("label", ""), row.get("label_key", ""), row.get("template")
        if (
            not isinstance(label, str) or not isinstance(label_key, str)
            or not (label.strip() or label_key.strip()) or not isinstance(template, str)
        ):
            raise ValueError(f"CSS insertion entry {index} needs a label and a template.")
        label, label_key = label.strip(), label_key.strip()
        if label_key and label_key not in translated_labels:
            raise ValueError(f"Unknown translation key: {label_key}")
        identifier = label_key or label
        if identifier in labels:
            raise ValueError(f"Duplicate CSS insertion label: {identifier}")
        labels.add(identifier)
        category = row.get("category", "user")
        if not isinstance(category, str) or category not in CSS_INSERT_CATEGORIES:
            raise ValueError(f"Unknown CSS insertion category: {category}")
        if (
            any(character in template for character in "\r\n")
            or template.count(CURSOR_PLACEHOLDER) > 1
            or any(match[1] != "cursor" for match in PLACEHOLDER_PATTERN.finditer(template))
        ):
            raise ValueError(f"Use at most one {{cursor}} in a single-line declaration: {identifier}")
        declaration = template.replace(CURSOR_PLACEHOLDER, "")
        values = parse_inline_style_values(declaration, reject_duplicates=True)
        if (
            not declaration.endswith(";") or not re.match(r"(?:--|-?[A-Za-z])[A-Za-z0-9_-]*\s*:", declaration)
            or values is None or len(values) != 1
        ):
            raise ValueError(f"Enter one CSS declaration ending in a semicolon: {identifier}")
        marker = template.find(CURSOR_PLACEHOLDER)
        snippets.append(CssInsertSnippet(
            label, label_key, declaration, marker if marker >= 0 else len(declaration), category,
        ))
    return tuple(snippets)


def load_css_insert_snippets(user_folder: Path | None = None) -> tuple[CssInsertSnippet, ...]:
    """同梱項目の分類を引き継ぎ、独自の項目をユーザー追加に分類する。"""
    bundled_path = bundled_base_dir() / "dictionaries" / CSS_INSERT_DICTIONARY
    bundled = parse_css_insert_snippets(json.loads(bundled_path.read_text(encoding="utf-8")))
    if user_folder is None:
        return bundled
    load_file_path = user_folder / CSS_INSERT_DICTIONARY
    if not load_file_path.is_file():
        return bundled
    user_snippets = parse_css_insert_snippets(json.loads(load_file_path.read_text(encoding="utf-8")))
    categories = {snippet.identifier: snippet.category for snippet in bundled}
    return tuple(
        replace(snippet, category=categories.get(snippet.identifier, "user"))
        for snippet in user_snippets
    )
