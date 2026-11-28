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
SPACING_PRESET = re.compile(r"var\(--wp--preset--spacing--([a-z0-9-]+)\)")
REVERSE_LENGTH = re.compile(r"(?:0|[0-9]+(?:\.[0-9]+)?px)")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
REPAIR_BLOCKS = ROOT_CLASSES.keys() | WORDPRESS_SERIALIZATION_RULES.keys()
_MISSING = object()
_JSON_DECODER = json.JSONDecoder()

_Tag = tuple[int, str, str, dict[str, str]]


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
    root: _Tag | None = None
    children: list[_Tag] = field(default_factory=list)
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
            else:
                if len(block.tags) == 1 and block.name in {"button", "accordion-heading"}:
                    raw = self.get_starttag_text()
                    if raw is None or len({name for name, _ in attrs}) != len(attrs):
                        block.valid = False
                    else:
                        block.children.append((
                            self._position(), tag, raw, {name: value or "" for name, value in attrs},
                        ))
                if tag not in VOID_TAGS:
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
        elif tag in VOID_TAGS:
            self.handle_starttag(tag, attrs)

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
        current = current.get(key, _MISSING)
        if current is _MISSING:
            return _MISSING
    return current


def _style_values(style_text: str) -> dict[str, str] | None:
    """一意に読み取れる有効なインライン宣言を返す。"""
    values = parse_inline_style_values(style_text)
    names = re.findall(r"(?:^|;)\s*([\w-]+)\s*:", style_text.lower())
    if (
        values is None or "{cursor}" in style_text or lint_inline_style(style_text)
        or len(names) != len(values)
    ):
        return None
    return values


def _css_value(mapping: dict[str, Any], data: dict[str, Any]) -> str | None:
    """JSONに対応する安全なCSS値を返す。"""
    expected = _nested(data, mapping["json_path"])
    if isinstance(expected, bool) or not isinstance(expected, (int, float, str)):
        return None
    value = str(expected).strip()
    if mapping.get("value_transform") == "wordpress_preset_variable" and (preset := PRESET.fullmatch(value)):
        value = f"var(--wp--preset--{preset[1]}--{preset[2]})"
    if mapping["css_property"] == "text-decoration" and value in {"underline", "line-through", "none"}:
        return value
    return value if SAFE_CSS.fullmatch(value) else None


def _class_additions(
    rule: dict[str, Any], data: dict[str, Any], existing: str, required: list[str], target: str,
) -> list[str]:
    """保存例で検証したクラスを、既存の指定と競合しない範囲で補う。"""
    if "{cursor}" in existing:
        return []
    tokens = set(existing.split())
    classes = dict.fromkeys(required)
    for mapping in rule.get("attribute_class_rules", []):
        if mapping.get("html_target", "root") != target:
            continue
        value = _nested(data, mapping["json_path"])
        if "equals" in mapping:
            if value is not mapping["equals"]:
                continue
        elif not isinstance(value, str) or not value.strip():
            continue
        templates = mapping["class_templates"]
        generated: list[str] = []
        for template in templates:
            if "{value}" not in template:
                generated.append(template)
            elif isinstance(value, str) and SLUG.fullmatch(value):
                name = template.format(value=value)
                pattern = re.escape(template).replace(re.escape("{value}"), SLUG.pattern)
                comparable = tokens - {"has-text-color", "has-link-color"}
                if template == "has-{value}-color":
                    comparable = {token for token in comparable if not token.endswith("-background-color")}
                if any(token != name and re.fullmatch(pattern, token) for token in comparable):
                    break
                generated.append(name)
            else:
                break
        else:
            classes.update(dict.fromkeys(generated))
    return [token for token in classes if token not in tokens]


def _tag_additions(
    name: str, attrs: dict[str, str], data: dict[str, Any], target: str = "root",
) -> tuple[list[str], dict[str, str]]:
    """ルートまたは検証済みの子要素に追加できるクラスとCSS宣言を求める。"""
    rule = WORDPRESS_SERIALIZATION_RULES.get(name, {})
    target_rule = rule if target == "root" else rule["element_targets"][target]
    required = list(target_rule.get("required_classes", []))
    fallback_class = ROOT_CLASSES.get(name, (set(), ""))[1] if target == "root" else ""
    if fallback_class:
        required.append(fallback_class)
    classes = _class_additions(rule, data, attrs.get("class", ""), required, target)
    style = _style_values(attrs.get("style", ""))
    if style is None:
        return classes, {}
    declarations: dict[str, str] = {}
    for mapping in rule.get("style_rules", []):
        if mapping.get("html_target", "root") != target:
            continue
        key = mapping["css_property"]
        family = "font" if key.startswith(("font-", "line-height")) else key.split("-")[0]
        if "all" in style or any(
            existing.split("-")[0] == family or (family == "font" and existing == "line-height")
            for existing in style
        ):
            continue
        value = _css_value(mapping, data)
        if value is not None and not lint_inline_style(f"{key}:{value}"):
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


def _extend_json_object(raw: str, additions: dict[str, Any]) -> str:
    """既存JSONの表記を残し、足りないキーだけを該当オブジェクトに追記する。"""
    edits: list[tuple[int, int, str]] = []
    missing = additions.copy()
    cursor = 1
    while cursor < len(raw) - 1:
        key_start = cursor + len(raw[cursor:]) - len(raw[cursor:].lstrip())
        if raw[key_start] == "}":
            break
        key, key_end = _JSON_DECODER.raw_decode(raw, key_start)
        value_start = raw.index(":", key_end) + 1
        value_start += len(raw[value_start:]) - len(raw[value_start:].lstrip())
        _, value_end = _JSON_DECODER.raw_decode(raw, value_start)
        if key in missing:
            edits.append((value_start, value_end, _extend_json_object(raw[value_start:value_end], missing.pop(key))))
        cursor = value_end + len(raw[value_end:]) - len(raw[value_end:].lstrip())
        if raw[cursor] != ",":
            break
        cursor += 1
    if missing:
        closing = len(raw[:-1].rstrip())
        comma = "," if raw[1:closing].strip() else ""
        edits.append((closing, closing, comma + json.dumps(missing, separators=(",", ":"))[1:-1]))
    for start, end, text in reversed(edits):
        raw = raw[:start] + text + raw[end:]
    return raw


def _json_repair(block: _Block, line: int, additions: dict[str, Any], details: tuple[str, ...], reason: str) -> RepairCandidate:
    """コメントの変更前後を、追加する属性とともに候補にまとめる。"""
    opening = block.opening.group()
    if raw := block.opening[3]:
        start, end = block.opening.span(3)
        after = opening[:start] + _extend_json_object(raw, additions) + opening[end:]
    else:
        start = len(opening[:-3].rstrip())
        after = opening[:start] + " " + json.dumps(additions, separators=(",", ":")) + opening[start:]
    return RepairCandidate(block.name, line, block.start, opening, after, details, reason)


def _reverse_style_repair(block: _Block, line: int, attrs: dict[str, str], data: dict[str, Any]) -> RepairCandidate | None:
    """GroupとParagraphの明示的な長さをCSSから不足JSONに戻す。"""
    if block.name not in {"group", "paragraph"}:
        return None
    if block.name == "group" and "wp-block-group" not in attrs.get("class", "").split():
        return None
    rule = WORDPRESS_SERIALIZATION_RULES[block.name]
    style = _style_values(attrs.get("style", ""))
    if not style or "all" in style:
        return None
    families = ("border", "margin", "padding") if block.name == "group" else ("border",)
    mappings = {mapping["css_property"]: mapping for mapping in rule["style_rules"]}
    additions: dict[str, Any] = {}
    details: list[str] = []
    for family in families:
        values = {key: value for key, value in style.items() if key.split("-")[0] == family}
        if not values or values.keys() - mappings.keys():
            continue
        if "border-width" in values and any(
            key in values for key in ("border-top-width", "border-right-width", "border-bottom-width", "border-left-width")
        ):
            continue
        if any(
            _nested(data, mappings[key]["json_path"]) is not _MISSING
            and _css_value(mappings[key], data) != value for key, value in values.items()
        ):
            continue
        if family == "border" and block.name == "paragraph":
            sides = ("top", "right", "bottom", "left")
            if (
                ("border-width" in values and any(_nested(data, f"style.border.{side}.width") is not _MISSING for side in sides))
                or ("border-width" not in values and _nested(data, "style.border.width") is not _MISSING)
            ):
                continue
        for key, value in values.items():
            path = mappings[key]["json_path"]
            if _nested(data, path) is not _MISSING:
                continue
            preset = SPACING_PRESET.fullmatch(value) if family != "border" else None
            if preset:
                value = f"var:preset|spacing|{preset[1]}"
            elif not REVERSE_LENGTH.fullmatch(value):
                continue
            target = additions
            parts = path.split(".")
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = value
            details.append(f"JSON: {path} = {value}")
    if not additions:
        return None
    return _json_repair(block, line, additions, tuple(details), "reverse_style")


def _element_repairs(block: _Block, line: int, attrs: dict[str, str], data: dict[str, Any]) -> list[RepairCandidate]:
    """保存例と同じ一意の子要素を見つけ、その属性を補う。"""
    rule = WORDPRESS_SERIALIZATION_RULES.get(block.name, {})
    if not set(rule.get("required_classes", [])).issubset(attrs.get("class", "").split()):
        return []
    if len(block.children) != 1:
        return []
    position, tag, raw, child_attrs = block.children[0]
    classes = child_attrs.get("class", "").split()
    if block.name == "button" and tag in {"a", "button"} and "wp-block-button__link" in classes:
        new_classes, styles = _tag_additions(block.name, child_attrs, data, "link")
        additions = {}
        if new_classes:
            additions["class"] = " ".join(new_classes)
        if styles:
            additions["style"] = ";".join(f"{key}:{value}" for key, value in styles.items())
        return _tag_repairs(block.name, line, position, raw, child_attrs, additions)
    if (
        block.name == "accordion-heading" and tag == "button"
        and "wp-block-accordion-heading__toggle" in classes and "type" not in child_attrs
    ):
        return _tag_repairs(block.name, line, position, raw, child_attrs, {"type": "button"})
    return []


def _empty_style_repair(block: _Block, line: int, position: int, raw: str) -> RepairCandidate | None:
    """Groupの空のstyle属性を、他の属性を保持したまま削除する候補を作る。"""
    tag = re.match(r"<[^\s/>]+", raw)
    if tag is None:
        return None
    cursor = tag.end()
    while (match := ATTRIBUTE.match(raw, cursor)) is not None:
        if match[1].lower() == "style" and (match[2] == "" or match[3] == ""):
            start, end = match.span()
            return RepairCandidate(
                block.name, line, position + start, raw[start:end], "", ("style",), "empty_style",
                preview_before=raw, preview_after=raw[:start] + raw[end:],
            )
        cursor = match.end()
    return None


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
    errors = sorted(
        item.line_number for item in lint_html_typos(source)
        if item.severity == "error" and item.message_key != "html_typo_lint.wordpress_group_empty_root_style"
    )
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
        rule = WORDPRESS_SERIALIZATION_RULES.get(block.name, {})
        if tag not in rule.get("root_tags", ROOT_CLASSES.get(block.name, (set(), ""))[0]):
            continue
        body = source[position + len(raw):end].rstrip()
        if not body.lower().endswith(f"</{tag}>"):
            continue
        if block.name == "table" and (
            block.tables != 1 or re.match(r"\s*<table\b", body, re.IGNORECASE) is None
        ):
            continue
        classes, styles = _tag_additions(block.name, attrs, data)
        additions: dict[str, str] = {}
        if classes:
            additions["class"] = " ".join(classes)
        if styles:
            additions["style"] = ";".join(f"{key}:{value}" for key, value in styles.items())
        candidates.extend(_tag_repairs(block.name, line, position, raw, attrs, additions))
        candidates.extend(_element_repairs(block, line, attrs, data))
        if reverse := _reverse_style_repair(block, line, attrs, data):
            candidates.append(reverse)
        if (
            block.name == "group" and not styles and attrs.get("style") == ""
            and "wp-block-group" in attrs.get("class", "").split()
            and isinstance(data.get("layout"), dict)
            and not any(_nested(data, mapping["json_path"]) is not _MISSING for mapping in rule["style_rules"])
            and (empty_style := _empty_style_repair(block, line, position, raw))
        ):
            candidates.append(empty_style)
        if (
            block.name == "heading" and tag in {"h3", "h4", "h5", "h6"}
            and "level" not in data and "wp-block-heading" in attrs.get("class", "").split()
        ):
            candidates.append(_json_repair(block, line, {"level": int(tag[1])}, (f'JSON: "level":{tag[1]}',), "level"))
    return sorted(candidates, key=lambda item: item.start)

