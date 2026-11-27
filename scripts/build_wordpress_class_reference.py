"""WordPressのクラスとHTMLタグの対応を記録したLinter用参照を生成する。

同梱のWordPressコアCSSと、実際の業務サイトで保存されたCSS・HTMLからJSONを生成する。CSSセレクターは参考情報として扱う。クラスとタグの組み合わせを拒否する厳格な根拠には、別途確認したWordPressコアの保存出力を使う。
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZipFile

CLASS_NAME_PATTERN = re.compile(r"\.([A-Za-z_][A-Za-z0-9_-]*)")
TAG_NAME_PATTERN = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)")
CLASS_ATTRIBUTE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
MAX_EVIDENCE_PER_CLASS = 4
CORE_SEMANTIC_TAG_RELATIONSHIPS: dict[str, tuple[set[str], list[str]]] = {
    "has-fixed-layout": (
        {"table"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/table-save",
            "wordpress/wp-includes/blocks/table/block.json#selectors.root",
        ],
    ),
    "wp-block-table": (
        {"figure"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/table-save",
            "wordpress/wp-includes/blocks/table/block.json#selectors.root",
        ],
    ),
    "wp-block-group": (
        {"article", "aside", "div", "footer", "header", "main", "section"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/group-save",
            "wordpress/wp-includes/blocks/group/block.json#attributes.tagName",
        ],
    ),
    "wp-block-buttons": (
        {"div"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/buttons-save",
            "wordpress/wp-includes/blocks/buttons/block.json#allowedBlocks",
        ],
    ),
    "wp-block-button": (
        {"div"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/button-save",
            "wordpress/wp-includes/blocks/button/block.json#selectors.root",
        ],
    ),
    "wp-block-button__link": (
        {"a", "button"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/button-save",
            "wordpress/wp-includes/blocks/button/block.json#attributes.tagName",
        ],
    ),
    "wp-block-quote": (
        {"blockquote"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/quote-save",
            "wordpress/wp-includes/blocks/quote/block.json#value.selector",
        ],
    ),
    "wp-block-pullquote": (
        {"figure"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/pullquote-save",
            "wordpress/wp-includes/blocks/pullquote/block.json#save-root",
        ],
    ),
    "wp-block-accordion": (
        {"div"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/accordion-save",
            "wordpress/wp-includes/blocks/accordion/block.json#allowedBlocks",
        ],
    ),
    "wp-block-accordion-item": (
        {"div"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/accordion-item-save",
            "wordpress/wp-includes/blocks/accordion-item/block.json#parent",
        ],
    ),
    "wp-block-accordion-heading": (
        {"h1", "h2", "h3", "h4", "h5", "h6"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/accordion-heading-save",
            "wordpress/wp-includes/blocks/accordion/block.json#attributes.headingLevel",
        ],
    ),
    "wp-block-accordion-heading__toggle": (
        {"button"},
        ["wordpress/wp-includes/js/dist/block-library.js#core/accordion-heading-save"],
    ),
    "wp-block-accordion-heading__toggle-title": (
        {"span"},
        ["wordpress/wp-includes/js/dist/block-library.js#core/accordion-heading-save"],
    ),
    "wp-block-accordion-heading__toggle-icon": (
        {"span"},
        ["wordpress/wp-includes/js/dist/block-library.js#core/accordion-heading-save"],
    ),
    "wp-block-accordion-panel": (
        {"div"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/accordion-panel-save",
            "wordpress/wp-includes/blocks/accordion-panel/block.json#parent",
        ],
    ),
    "wp-block-columns": (
        {"div"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/columns-save",
            "wordpress/wp-includes/blocks/columns/block.json#allowedBlocks",
        ],
    ),
    "wp-block-column": (
        {"div"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/column-save",
            "wordpress/wp-includes/blocks/column/block.json#parent",
        ],
    ),
    "wp-block-separator": (
        {"div", "hr"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/separator-save",
            "wordpress/wp-includes/blocks/separator/block.json#attributes.tagName",
        ],
    ),
    "has-alpha-channel-opacity": (
        {"div", "hr"},
        [
            "wordpress/wp-includes/js/dist/block-library.js#core/separator-save",
            "wordpress/wp-includes/blocks/separator/block.json#attributes.opacity",
        ],
    ),
}


@dataclass
class ClassEvidence:
    """クラス名ごとに、根拠となるセレクターとHTMLを集める。"""

    explicit_tags: set[str] = field(default_factory=set)
    observed_html_tags: set[str] = field(default_factory=set)
    source_groups: set[str] = field(default_factory=set)
    semantic_tags: set[str] = field(default_factory=set)
    semantic_sources: set[str] = field(default_factory=set)
    selector_evidence: set[tuple[str, str, str | None]] = field(default_factory=set)
    html_evidence: set[tuple[str, str]] = field(default_factory=set)
    has_unrestricted_selector: bool = False


class _ClassHtmlParser(HTMLParser):
    """HTMLのタグとクラスの組み合わせを集めるためのパーサー。"""
    def __init__(self, source: str, source_group: str, classes: dict[str, ClassEvidence]) -> None:
        """クラスに対するHTMLの根拠を記録する。"""
        super().__init__(convert_charrefs=True)
        self.source = source
        self.source_group = source_group
        self.classes = classes

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """開始タグで使われたクラスを集める。"""
        self._record(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """自己終了タグで使われたクラスを集める。"""
        self._record(tag, attrs)

    def _record(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """HTMLで観測したタグとクラスの組み合わせを記録する。"""
        class_value = next((value for name, value in attrs if name.lower() == "class"), None)
        if not class_value:
            return
        clean_tag = tag.lower()
        for class_name in class_value.split():
            if not CLASS_ATTRIBUTE_PATTERN.fullmatch(class_name):
                continue
            evidence = self.classes[class_name]
            evidence.observed_html_tags.add(clean_tag)
            evidence.source_groups.add(self.source_group)
            evidence.html_evidence.add((self.source, clean_tag))


def _iter_css_rule_preludes(css_text: str) -> Iterable[str]:
    """宣言値をセレクターと解釈せず、CSSルールの開始部分を順に返す。"""
    buffer: list[str] = []
    index = 0
    quote: str | None = None
    in_comment = False
    while index < len(css_text):
        character = css_text[index]
        following = css_text[index + 1] if index + 1 < len(css_text) else ""
        if in_comment:
            if character == "*" and following == "/":
                in_comment = False
                index += 2
                continue
            index += 1
            continue
        if quote is not None:
            if character == "\\" and following:
                index += 2
                continue
            if character == quote:
                quote = None
            buffer.append(character)
            index += 1
            continue
        if character == "/" and following == "*":
            in_comment = True
            index += 2
            continue
        if character in {'"', "'"}:
            quote = character
            buffer.append(character)
            index += 1
            continue
        if character == "{":
            prelude = "".join(buffer).strip()
            buffer.clear()
            if prelude and not prelude.startswith("@"):
                yield prelude
            index += 1
            continue
        if character in "};":
            buffer.clear()
            index += 1
            continue
        buffer.append(character)
        index += 1


def _split_selectors(prelude: str) -> list[str]:
    """CSSのセレクター一覧を個別のセレクターに分ける。"""
    selectors: list[str] = []
    current: list[str] = []
    round_depth = 0
    square_depth = 0
    for character in prelude:
        if character == "(":
            round_depth += 1
        elif character == ")" and round_depth:
            round_depth -= 1
        elif character == "[":
            square_depth += 1
        elif character == "]" and square_depth:
            square_depth -= 1
        if character == "," and round_depth == 0 and square_depth == 0:
            selector = "".join(current).strip()
            if selector:
                selectors.append(selector)
            current.clear()
            continue
        current.append(character)
    selector = "".join(current).strip()
    if selector:
        selectors.append(selector)
    return selectors


def _compound_for_class(selector: str, class_start: int) -> str:
    """指定クラスを含むセレクター部分を取り出す。"""
    start = class_start
    while start > 0 and not selector[start - 1].isspace() and selector[start - 1] not in ">+~":
        start -= 1
    end = class_start
    while end < len(selector) and not selector[end].isspace() and selector[end] not in ">+~":
        end += 1
    return selector[start:end]


def _explicit_tag_for_class(selector: str, class_match: re.Match[str]) -> str | None:
    """指定クラスに対する明示的なHTMLタグを取得する。"""
    compound = _compound_for_class(selector, class_match.start())
    tag_match = TAG_NAME_PATTERN.match(compound)
    if tag_match is None:
        return None
    return tag_match.group(1).lower()


def _record_css(
    css_text: str,
    source: str,
    source_group: str,
    classes: dict[str, ClassEvidence],
) -> None:
    """CSSセレクターからクラスとタグの対応を記録する。"""
    for prelude in _iter_css_rule_preludes(css_text):
        for selector in _split_selectors(prelude):
            for class_match in CLASS_NAME_PATTERN.finditer(selector):
                class_name = class_match.group(1)
                evidence = classes[class_name]
                tag = _explicit_tag_for_class(selector, class_match)
                if tag is None:
                    evidence.has_unrestricted_selector = True
                else:
                    evidence.explicit_tags.add(tag)
                evidence.source_groups.add(source_group)
                evidence.selector_evidence.add((source, selector, tag))


def _decode_source(load_data: bytes) -> str:
    """入力ファイルのバイト列をテキストへ変換する。"""
    for encoding in ("utf-8-sig", "cp932"):
        try:
            return load_data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return load_data.decode("utf-8", errors="replace")


def _wordpress_css_members(load_file: ZipFile) -> list[str]:
    """WordPressのアーカイブから参照するCSSファイルを選ぶ。"""
    members: list[str] = []
    for name in load_file.namelist():
        if not name.endswith(".css") or name.endswith(("-rtl.css", ".min.css")):
            continue
        if name.startswith("wordpress/wp-includes/blocks/"):
            members.append(name)
            continue
        if name in {
            "wordpress/wp-includes/css/dist/block-library/elements.css",
            "wordpress/wp-includes/css/dist/block-library/style.css",
            "wordpress/wp-includes/css/dist/block-library/theme.css",
        }:
            members.append(name)
    return sorted(members)


def _read_wordpress_core(
    wordpress_zip: Path,
    classes: dict[str, ClassEvidence],
) -> list[str]:
    """WordPressコアのCSSからクラスの参考情報を集める。"""
    with ZipFile(wordpress_zip) as load_file:
        members = _wordpress_css_members(load_file)
        for member in members:
            _record_css(
                _decode_source(load_file.read(member)),
                member,
                "wordpress_core_css",
                classes,
            )
    return members


def _read_sample(sample_dir: Path, classes: dict[str, ClassEvidence]) -> tuple[list[str], list[str]]:
    """サイトの保存例からクラスの情報を集める。"""
    css_files: list[str] = []
    html_files: list[str] = []
    for load_file_path in sorted(path for path in sample_dir.rglob("*") if path.is_file()):
        suffix = load_file_path.suffix.lower()
        source = load_file_path.relative_to(sample_dir).as_posix()
        if suffix == ".css":
            css_files.append(source)
            _record_css(
                _decode_source(load_file_path.read_bytes()),
                source,
                "business_sample_css",
                classes,
            )
        elif suffix in {".html", ".htm", ".wp_html"}:
            html_files.append(source)
            parser = _ClassHtmlParser(source, "business_sample_html", classes)
            parser.feed(_decode_source(load_file_path.read_bytes()))
            parser.close()
    return css_files, html_files


def _read_extra_html(
    html_paths: list[Path],
    classes: dict[str, ClassEvidence],
    source_root: Path | None,
) -> list[str]:
    """追加のHTML例からタグとクラスの組み合わせを集める。"""
    sources: list[str] = []
    for load_file_path in html_paths:
        source = _path_label(load_file_path, source_root)
        sources.append(source)
        parser = _ClassHtmlParser(source, "verified_wordpress_html", classes)
        parser.feed(_decode_source(load_file_path.read_bytes()))
        parser.close()
    return sources


def _path_label(load_file_path: Path, source_root: Path | None) -> str:
    """根拠ファイルの位置を表示用に整える。"""
    candidate_roots = [source_root, Path.cwd()] if source_root is not None else [Path.cwd()]
    for candidate_root in candidate_roots:
        try:
            return load_file_path.resolve().relative_to(candidate_root.resolve()).as_posix()
        except ValueError:
            continue
    return load_file_path.as_posix()


def _class_entry(evidence: ClassEvidence) -> dict[str, object]:
    """集めた根拠からクラス参照の項目を作る。"""
    strict = bool(evidence.semantic_tags)
    strict_tags = evidence.semantic_tags or evidence.explicit_tags
    selectors = sorted(
        evidence.selector_evidence,
        key=lambda item: (item[0], item[1], item[2] or ""),
    )
    selector_sources = sorted({source for source, _selector, _tag in selectors})
    html_items = sorted(evidence.html_evidence)
    html_sources = sorted({source for source, _tag in html_items})
    entry: dict[str, object] = {
        "tag_scope": "strict" if strict else "advisory",
        "allowed_tags": sorted(strict_tags) if strict else ["*"],
        "selector_tags": sorted(evidence.explicit_tags),
        "observed_html_tags": sorted(evidence.observed_html_tags),
        "source_groups": sorted(evidence.source_groups),
        "selector_evidence_count": len(selectors),
        "selector_source_count": len(selector_sources),
        "selector_sources": selector_sources[:MAX_EVIDENCE_PER_CLASS],
        "html_evidence_count": len(html_items),
        "html_source_count": len(html_sources),
        "html_sources": html_sources[:MAX_EVIDENCE_PER_CLASS],
        "semantic_sources": sorted(evidence.semantic_sources),
    }
    return entry


def build_reference(
    wordpress_zip: Path,
    sample_dir: Path,
    extra_html: list[Path],
    source_root: Path | None = None,
) -> dict[str, object]:
    """収集した根拠をまとめてLinterの参照データを構築する。"""
    classes: dict[str, ClassEvidence] = defaultdict(ClassEvidence)
    wordpress_members = _read_wordpress_core(wordpress_zip, classes)
    sample_css, sample_html = _read_sample(sample_dir, classes)
    verified_html = _read_extra_html(extra_html, classes, source_root)
    for class_name, (tags, sources) in CORE_SEMANTIC_TAG_RELATIONSHIPS.items():
        evidence = classes[class_name]
        evidence.semantic_tags.update(tags)
        evidence.semantic_sources.update(sources)
        evidence.source_groups.add("wordpress_core_save")
    class_entries = {
        class_name: _class_entry(classes[class_name])
        for class_name in sorted(classes)
    }
    strict_count = sum(
        entry["tag_scope"] == "strict" for entry in class_entries.values()
    )
    return {
        "schema_version": 1,
        "generated_date": datetime.now(
            tz=timezone(timedelta(hours=9)),
        ).date().isoformat(),
        "policy": {
            "strict": "The relationship was confirmed in WordPress core save output and may be checked by the Linter.",
            "advisory": "CSS selectors and observed HTML provide reference evidence only; selector_tags and observed_html_tags are not an exhaustive allowlist.",
            "unknown_classes": "Custom classes are valid and are not warned about merely because they are absent from this reference.",
        },
        "sources": {
            "wordpress_zip": _path_label(wordpress_zip, source_root),
            "wordpress_core_css_files": wordpress_members,
            "business_sample_dir": _path_label(sample_dir, source_root),
            "business_sample_css_files": sample_css,
            "business_sample_html_files": sample_html,
            "verified_wordpress_html_files": verified_html,
        },
        "summary": {
            "class_count": len(class_entries),
            "strict_class_count": strict_count,
            "advisory_class_count": len(class_entries) - strict_count,
        },
        "classes": class_entries,
    }


def _parse_args() -> argparse.Namespace:
    """参照生成コマンドの引数を解析する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wordpress-zip", type=Path, required=True)
    parser.add_argument("--sample-dir", type=Path, required=True)
    parser.add_argument("--extra-html", type=Path, action="append", default=[])
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """コマンドラインの指定に従って参照データを出力する。"""
    args = _parse_args()
    reference = build_reference(
        args.wordpress_zip,
        args.sample_dir,
        args.extra_html,
        args.source_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_data = json.dumps(reference, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(save_data, encoding="utf-8")
    summary = reference["summary"]
    if not isinstance(summary, dict):
        raise TypeError("generated reference summary must be an object")
    print(
        f"wrote {args.output}: {summary['class_count']} classes "
        f"({summary['strict_class_count']} strict, "
        f"{summary['advisory_class_count']} advisory)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
