"""保存例に基づいて WordPress ブロックの追記候補を作る。"""

from __future__ import annotations

import json
import re
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from typing import Any

from search.css_lint import lint_inline_style, parse_inline_style_values
from search.html_typo_lint import (
    BLOCK_COMMENT_PATTERN,
    VOID_TAGS,
    WORDPRESS_SERIALIZATION_RULES,
    lint_html_typos,
)

ROOT_CLASSES = {
    "heading": ({"h2", "h3", "h4", "h5", "h6"}, "wp-block-heading"),
    "list": ({"ul", "ol"}, "wp-block-list"),
    "table": ({"figure"}, "wp-block-table"),
}
ATTRIBUTE = re.compile(r"""\s+([^\s=/<>"']+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|[^\s<>"'=`]+))?""")
SAFE_CSS = re.compile(r"(?:-?(?:\d+(?:\.\d+)?|\.\d+)(?:px|em|rem|ch|ex|vh|vw|%)?|var\(--wp--preset--[a-z0-9-]+--[a-z0-9-]+\)|normal|italic|oblique|bold|bolder|lighter|auto)")
PRESET = re.compile(r"var:preset\|([a-z0-9-]+)\|([a-z0-9-]+)")
REPAIR_BLOCKS = ROOT_CLASSES.keys() | WORDPRESS_SERIALIZATION_RULES.keys()


@dataclass(frozen=True)
class RepairCandidate:
    """修復候補の位置、変更前後の文字列と根拠を表す。"""
    block: str
    line: int
    start: int
    before: str
    after: str
    details: tuple[str, ...]
    reason: str
    preview_before: str | None = None
    preview_after: str | None = None

    @property
    def end(self) -> int:
        """候補が変更する範囲の終了位置を返す。"""
        return self.start + len(self.before)


@dataclass
class _Block:
    """修復候補を調べるためのブロック境界とHTML要素を保持する。"""
    name: str
    start: int
    opening: re.Match[str]
    root: tuple[int, str, str, dict[str, str]] | None = None
    tags: list[str] = field(default_factory=list)
    valid: bool = True
    tables: int = 0


class _BlockScanner(HTMLParser):
    """タグ属性中の疑似コメントを無視し、実際のブロック境界を得る。"""

    # Treat the content of HTML raw-text elements as text even if it looks like a block.
    CDATA_CONTENT_ELEMENTS = (  # pyright: ignore[reportGeneralTypeIssues]
        "script", "style", "textarea", "title", "xmp", "iframe", "noembed", "noframes",
    )

    def __init__(self, source: str, lines: list[int]) -> None:
        """原文と行の開始位置、ブロックの解析状態を初期化する。"""
        super().__init__()
        self.source = source
        self.lines = lines
        self.stack: list[_Block] = []
        self.completed: list[tuple[_Block, int]] = []

    def _position(self) -> int:
        """パーサーの現在位置を原文のオフセットに戻す。"""
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_comment(self, data: str) -> None:
        """WordPressの開始・終了コメントを対応付ける。"""
        match = BLOCK_COMMENT_PATTERN.fullmatch(f"<!--{data}-->")
        if match is None:
            return
        name = match[2].lower().removeprefix("core/")
        position = self._position()
        if not self.source.startswith(match.group(), position):
            return
        if self.stack and self.stack[-1].name == "html":
            if match[1] and name == "html":
                self.stack.pop()
            return
        if match[1]:
            if not self.stack or self.stack[-1].name != name:
                self.stack.clear()
            else:
                block = self.stack.pop()
                if block.root is not None and not block.tags and block.valid:
                    self.completed.append((block, position))
        elif not match[4]:
            self.stack.append(_Block(name, position, match))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """修復候補の対象となるHTML開始タグと入れ子の状態を記録する。"""
        if not self.stack:
            return
        block = self.stack[-1]
        if not block.valid or block.name not in REPAIR_BLOCKS:
            return
        if block.root is not None:
            if not block.tags:
                block.valid = False
            elif tag not in VOID_TAGS:
                block.tables += int(tag == "table")
                block.tags.append(tag)
            return
        position = self._position()
        if self.source[block.start + block.opening.end():position].strip():
            return
        if len({name for name, _ in attrs}) != len(attrs):
            return
        raw = self.get_starttag_text()
        if raw is not None and tag not in VOID_TAGS:
            block.root = position, tag, raw, {name: value or "" for name, value in attrs}
            block.tags.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """自己終了タグを調べ、通常のタグが途中で閉じていれば対象外とする。"""
        if self.stack and (not self.stack[-1].tags or tag not in VOID_TAGS):
            self.stack[-1].valid = False

    def handle_endtag(self, tag: str) -> None:
        """終了タグを開始タグと照合して要素の境界を追跡する。"""
        if self.stack and self.stack[-1].root is not None:
            block = self.stack[-1]
            if not block.tags or block.tags[-1] != tag:
                block.valid = False
            else:
                block.tags.pop()

    def handle_data(self, data: str) -> None:
        """外側にテキストがあるブロックを修復候補から外す。"""
        if self.stack and not self.stack[-1].tags and data.strip():
            self.stack[-1].valid = False


def _unique_json(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """同じ名前のキーが複数ないことを確かめて辞書を作る。"""
    attributes = dict(pairs)
    if len(attributes) != len(pairs):
        raise ValueError("duplicate attribute")
    return attributes


def _invalid_constant(value: str) -> None:
    """標準JSONにない数値定数を拒否する。"""
    raise ValueError(f"invalid JSON constant: {value}")


def _attributes(block: _Block) -> dict[str, Any] | None:
    """開始コメントのJSONからブロック属性を読み取る。"""
    try:
        data = json.loads(
            block.opening[3] or "{}", object_pairs_hook=_unique_json, parse_constant=_invalid_constant,
        )
    except (ValueError, RecursionError):
        return None
    return data if isinstance(data, dict) else None


def _nested(data: dict[str, Any], path: str) -> Any:
    """ドット区切りの属性パスを使って値を取得する。"""
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _root_additions(
    name: str, tag: str, attrs: dict[str, str], data: dict[str, Any],
) -> tuple[list[str], dict[str, str]]:
    """既存の指定を保持しながら追加できるクラスとCSS宣言を求める。"""
    rule = WORDPRESS_SERIALIZATION_RULES.get(name, {})
    fallback_tags, fallback_class = ROOT_CLASSES.get(name, (set(), ""))
    if tag not in rule.get("root_tags", fallback_tags):
        return [], {}
    required = list(rule.get("required_classes", []))
    if fallback_class:
        required.append(fallback_class)
    # fitText has a verified, unambiguous Boolean-to-class mapping.
    if name == "paragraph" and data.get("fitText") is True:
        required.append("has-fit-text")
    classes = [] if "{cursor}" in attrs.get("class", "") else [
        value for value in required if value not in attrs.get("class", "").split()
    ]
    existing_style = attrs.get("style", "")
    style = parse_inline_style_values(existing_style)
    if style is None or "{cursor}" in existing_style or lint_inline_style(existing_style):
        return classes, {}
    declarations: dict[str, str] = {}
    for mapping in rule.get("style_rules", []):
        if mapping.get("html_target", "root") != "root":
            continue
        key = mapping["css_property"]
        family = "font" if key.startswith(("font-", "line-height")) else key.split("-")[0]
        if "all" in style or any(
            existing.split("-")[0] == family or (family == "font" and existing == "line-height")
            for existing in style
        ):
            continue
        expected = _nested(data, mapping["json_path"])
        if isinstance(expected, bool) or not isinstance(expected, (int, float, str)):
            continue
        value = str(expected).strip()
        if mapping.get("value_transform") == "wordpress_preset_variable" and (preset := PRESET.fullmatch(value)):
            value = f"var(--wp--preset--{preset[1]}--{preset[2]})"
        if SAFE_CSS.fullmatch(value) and not lint_inline_style(f"{key}:{value}"):
            declarations[key] = value
    return classes, declarations


def _tag_repairs(
    block: str, line: int, position: int, raw: str, attrs: dict[str, str], additions: dict[str, str],
) -> list[RepairCandidate]:
    """class と style を別候補にし、元の属性と空白を残す。"""
    name = re.match(r"<[^\s/>]+", raw)
    if name is None:
        return []
    spans: dict[str, int] = {}
    cursor = name.end()
    while (match := ATTRIBUTE.match(raw, cursor)) is not None:
        for group in (2, 3):
            if match[group] is not None:
                spans[match[1].lower()] = match.end(group)
        cursor = match.end()
    if raw[cursor:].strip() != ">":
        return []
    candidates: list[RepairCandidate] = []
    for key, value in additions.items():
        encoded = escape(value, quote=True)
        if key in spans:
            existing = attrs[key]
            separator = (" " if key == "class" else ";") if existing.strip() else ""
            if key == "style" and existing.rstrip().endswith(";"):
                separator = ""
            offset = spans[key]
            replacement = separator + encoded + raw[offset]
        elif key in attrs:
            continue  # Do not alter an unquoted or valueless attribute.
        else:
            attribute = f' {key}="{encoded}"'
            if key == "class":
                offset = name.end() - 1
                replacement = raw[offset] + attribute
            else:
                offset = len(raw) - 1
                replacement = attribute + raw[offset]
        candidates.append(RepairCandidate(
            block, line, position + offset, raw[offset], replacement, (f"{key}: {value}",), key,
            preview_before=raw, preview_after=raw[:offset] + replacement + raw[offset + 1:],
        ))
    return candidates


def find_core_block_repairs(source: str) -> list[RepairCandidate]:
    """全文の構文診断と照合し、安全に追記できる候補だけを返す。"""
    lines = [0, *(match.end() for match in re.finditer("\n", source))]
    scanner = _BlockScanner(source, lines)
    try:
        scanner.feed(source)
        scanner.close()
    except AssertionError:
        # HTMLParser rejects unsupported marked sections, such as <![unknown]>.
        return []
    if not scanner.completed:
        return []
    errors = sorted(item.line_number for item in lint_html_typos(source) if item.severity == "error")
    candidates: list[RepairCandidate] = []
    for block, end in scanner.completed:
        line = bisect_right(lines, block.start)
        error_index = bisect_left(errors, line)
        if error_index < len(errors) and errors[error_index] <= bisect_right(lines, end):
            continue
        data = _attributes(block)
        if data is None or block.root is None:
            continue
        position, tag, raw, attrs = block.root
        body = source[position + len(raw):end].rstrip()
        if not body.lower().endswith(f"</{tag}>"):
            continue
        if block.name == "table" and (
            block.tables != 1 or re.match(r"\s*<table\b", body, re.IGNORECASE) is None
        ):
            continue
        classes, styles = _root_additions(block.name, tag, attrs, data)
        additions: dict[str, str] = {}
        if classes:
            additions["class"] = " ".join(classes)
        if styles:
            additions["style"] = ";".join(f"{key}:{value}" for key, value in styles.items())
        candidates.extend(_tag_repairs(block.name, line, position, raw, attrs, additions))
        if (
            block.name == "heading" and tag in {"h3", "h4", "h5", "h6"}
            and "level" not in data and "wp-block-heading" in attrs.get("class", "").split()
        ):
            opening = block.opening.group()
            addition = f'"level":{tag[1]}'
            if block.opening[3]:
                json_end = block.opening.end(3) - 1
                after = opening[:json_end] + ("," if data else "") + addition + opening[json_end:]
            else:
                after = opening[:-3].rstrip() + " {" + addition + "} -->"
            candidates.append(RepairCandidate(
                block.name, line, block.start, opening, after, (f"JSON: {addition}",), "level",
            ))
    return sorted(candidates, key=lambda item: item.start)

