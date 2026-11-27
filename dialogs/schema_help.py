"""同梱スキーマから操作ヘルプ用の参考表を作る。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HelpTopic = tuple[str, str]

_TEXT = {
    "en": {
        "html_title": "HTML Tag / Attribute Table",
        "html_intro": (
            "This table is generated from `html_tag_schema.json`. "
            "Global attributes and `aria-` / `data-` attributes may be used in "
            "addition to the tag-specific attributes shown below."
        ),
        "tag_attributes": "Tag-Specific Attributes",
        "global_attributes": "Global Attributes",
        "tag": "Tag",
        "attribute": "Attribute",
        "rule": "Type / Allowed Values",
        "description": "Description",
        "required": "Required",
        "yes": "Yes",
        "no": "No",
        "none": "None",
        "void_tags": "Void tags",
        "prefixes": "Additional allowed prefixes",
        "css_title": "CSS Property Table",
        "css_intro": (
            "This table is generated from `standard_css.json` and is also used "
            "by CSS syntax checks for HTML style attributes and .css files."
        ),
        "properties": "Properties",
        "property": "Property",
        "known_typos": "Known Typo Corrections",
        "incorrect": "Incorrect",
        "correction": "Correction",
        "units": "Units",
        "category": "Category",
        "values": "Values",
        "wp_title": "WordPress Block JSON Table",
        "wp_intro": (
            "This initial table is generated from `wordpress_block_schema.json`. "
            "It lists known block attributes and their value constraints. Some "
            "content attributes are read from saved HTML rather than written in "
            "the block-comment JSON, so also check the saved markup."
        ),
        "block_attributes": "Block Attributes",
        "shared_attributes": "Shared Attribute Candidates",
        "block": "Block",
        "coverage": "Coverage",
        "load_error": "The schema table could not be loaded",
    },
    "ja": {
        "html_title": "HTMLタグ・属性表",
        "html_intro": (
            "この表は `html_tag_schema.json` から自動生成しています。"
            "タグ固有属性に加えて、グローバル属性と `aria-` / `data-` 属性を使用できます。"
        ),
        "tag_attributes": "タグ固有属性",
        "global_attributes": "グローバル属性",
        "tag": "タグ",
        "attribute": "属性",
        "rule": "型・使用可能な値",
        "description": "解説",
        "required": "必須",
        "yes": "はい",
        "no": "いいえ",
        "none": "なし",
        "void_tags": "終了タグを持たないタグ",
        "prefixes": "追加で使用可能な接頭辞",
        "css_title": "CSSプロパティ表",
        "css_intro": (
            "この表は `standard_css.json` から自動生成しています。"
            "HTMLのstyle属性と.cssファイルのCSS文法チェックでも同じ辞書を使用します。"
        ),
        "properties": "プロパティ",
        "property": "プロパティ",
        "known_typos": "既知のTypo修正候補",
        "incorrect": "誤りの候補",
        "correction": "修正候補",
        "units": "単位",
        "category": "分類",
        "values": "値",
        "wp_title": "WordPressブロックJSON表",
        "wp_intro": (
            "この初期表は `wordpress_block_schema.json` から自動生成しています。"
            "既知のブロック属性と値の制約を確認できます。contentなど、ブロックコメントの"
            "JSONではなく保存HTMLから読み取られる属性もあるため、保存HTMLとの整合性も確認してください。"
        ),
        "block_attributes": "ブロック固有属性",
        "shared_attributes": "共有属性候補",
        "block": "ブロック",
        "coverage": "収録範囲",
        "load_error": "スキーマ表を読み込めませんでした",
    },
}


def load_schema_help_topics(
    standards_path: Path,
    language_code: str,
) -> tuple[HelpTopic, HelpTopic, HelpTopic]:
    """同梱のスキーマからHTML、CSS、WordPressの参考項目をそれぞれ生成する。"""
    language = "en" if language_code == "en" else "ja"
    html_topic = _load_topic(
        standards_path / "html_tag_schema.json",
        language,
        "html",
    )
    css_topic = _load_topic(
        standards_path / "standard_css.json",
        language,
        "css",
    )
    wordpress_topic = _load_topic(
        standards_path / "wordpress_block_schema.json",
        language,
        "wordpress",
    )
    return html_topic, css_topic, wordpress_topic


def _load_topic(
    load_file_path: Path,
    language: str,
    schema_kind: str,
) -> HelpTopic:
    """指定の参照資料を読み込み、ヘルプ項目を作る。"""
    text = _TEXT[language]
    title_keys = {
        "html": "html_title",
        "css": "css_title",
        "wordpress": "wp_title",
    }
    title = text[title_keys[schema_kind]]
    try:
        load_data: Any = json.loads(load_file_path.read_text(encoding="utf-8"))
        if not isinstance(load_data, dict):
            raise TypeError("schema root must be an object")
        if schema_kind == "html":
            return title, _build_html_topic(load_data, language)
        if schema_kind == "css":
            return title, _build_css_topic(load_data, language)
        return title, _build_wordpress_topic(load_data, language)
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        return title, f"# {title}\n\n{text['load_error']}: `{error}`"


def _build_html_topic(schema: dict[str, Any], language: str) -> str:
    """HTMLタグと属性の参考表を組み立てる。"""
    text = _TEXT[language]
    lines = [
        f"# {text['html_title']}",
        "",
        text["html_intro"],
        "",
        f"## {text['tag_attributes']}",
        "",
        _table_header(
            text["tag"],
            text["attribute"],
            text["rule"],
            text["description"],
            text["required"],
        ),
    ]
    tags = _require_dict(schema, "tags")
    for tag_name in sorted(tags):
        tag_data = _as_dict(tags[tag_name])
        attributes = _as_dict(tag_data.get("attributes", {}))
        required_attributes = set(_as_list(tag_data.get("required_attributes", [])))
        if not attributes:
            lines.append(
                _table_row(
                    _code(f"<{tag_name}>"),
                    text["none"],
                    "-",
                    _format_html_tag_description(tag_name, tag_data, language),
                    text["no"],
                )
            )
            continue
        for attribute_name in sorted(attributes):
            attribute_data = _as_dict(attributes[attribute_name])
            lines.append(
                _table_row(
                    _code(f"<{tag_name}>"),
                    _code(attribute_name),
                    _format_rule(attribute_data),
                    _format_html_attribute_description(
                        tag_name,
                        attribute_name,
                        attribute_data,
                        language,
                    ),
                    text["yes"] if attribute_name in required_attributes else text["no"],
                )
            )

    lines.extend(
        [
            "",
            f"## {text['global_attributes']}",
            "",
            _table_header(text["attribute"], text["rule"], text["description"]),
        ]
    )
    global_attributes = _require_dict(schema, "global_attributes")
    for attribute_name in sorted(global_attributes):
        attribute_data = _as_dict(global_attributes[attribute_name])
        lines.append(
            _table_row(
                _code(attribute_name),
                _format_rule(attribute_data),
                _format_html_attribute_description(
                    None,
                    attribute_name,
                    attribute_data,
                    language,
                ),
            )
        )

    void_tags = ", ".join(_code(tag) for tag in _as_list(schema.get("void_tags", [])))
    prefixes = ", ".join(
        _code(prefix) for prefix in _as_list(schema.get("allowed_attribute_prefixes", []))
    )
    lines.extend(
        [
            "",
            f"- {text['void_tags']}: {void_tags or '-'}",
            f"- {text['prefixes']}: {prefixes or '-'}",
        ]
    )
    return "\n".join(lines)


def _build_css_topic(schema: dict[str, Any], language: str) -> str:
    """CSSプロパティの参考表を組み立てる。"""
    text = _TEXT[language]
    lines = [
        f"# {text['css_title']}",
        "",
        text["css_intro"],
        "",
        f"## {text['properties']}",
        "",
        _table_header(text["property"], text["rule"], text["description"]),
    ]
    properties = _require_dict(schema, "properties")
    for property_name in sorted(properties):
        property_data = _as_dict(properties[property_name])
        lines.append(
            _table_row(
                _code(property_name),
                _format_rule(property_data),
                _format_css_property_description(property_name, property_data, language),
            )
        )

    known_typos = _require_dict(schema, "known_typos")
    lines.extend(
        [
            "",
            f"## {text['known_typos']}",
            "",
            _table_header(text["category"], text["incorrect"], text["correction"]),
        ]
    )
    for typo_category in ("property_names", "units"):
        typo_items = _as_dict(known_typos.get(typo_category, {}))
        for incorrect, correction in sorted(typo_items.items()):
            lines.append(
                _table_row(
                    _code(typo_category),
                    _code(str(incorrect)),
                    _code(str(correction)),
                )
            )

    lines.extend(
        [
            "",
            f"## {text['units']}",
            "",
            _table_header(text["category"], text["values"]),
        ]
    )
    units = _require_dict(schema, "units")
    for unit_category in sorted(units):
        unit_values = ", ".join(_code(str(value)) for value in _as_list(units[unit_category]))
        lines.append(_table_row(_code(unit_category), unit_values))
    return "\n".join(lines)


def _build_wordpress_topic(schema: dict[str, Any], language: str) -> str:
    """WordPressブロックと属性の参考表を組み立てる。"""
    text = _TEXT[language]
    coverage = str(schema.get("coverage", "-"))
    lines = [
        f"# {text['wp_title']}",
        "",
        text["wp_intro"],
        "",
        f"- {text['coverage']}: `{_escape_cell(coverage)}`",
        "",
        f"## {text['block_attributes']}",
        "",
        _table_header(text["block"], text["attribute"], text["rule"], text["description"]),
    ]
    blocks = _require_dict(schema, "blocks")
    for block_name in sorted(blocks):
        block_data = _as_dict(blocks[block_name])
        attributes = _as_dict(block_data.get("attributes", {}))
        if not attributes:
            lines.append(
                _table_row(
                    _code(f"wp:{block_name}"),
                    text["none"],
                    "-",
                    _format_wordpress_block_description(block_name, block_data, language),
                )
            )
            continue
        for attribute_name in sorted(attributes):
            attribute_data = _as_dict(attributes[attribute_name])
            lines.append(
                _table_row(
                    _code(f"wp:{block_name}"),
                    _code(attribute_name),
                    _format_rule(attribute_data),
                    _format_wordpress_attribute_description(
                        block_name,
                        attribute_name,
                        attribute_data,
                        language,
                    ),
                )
            )

    lines.extend(
        [
            "",
            f"## {text['shared_attributes']}",
            "",
            _table_header(text["attribute"], text["rule"], text["description"]),
        ]
    )
    shared_attributes = _require_dict(schema, "shared_attributes")
    for attribute_name in sorted(shared_attributes):
        attribute_data = _as_dict(shared_attributes[attribute_name])
        lines.append(
            _table_row(
                _code(attribute_name),
                _format_rule(attribute_data),
                _format_wordpress_attribute_description(
                    None,
                    attribute_name,
                    attribute_data,
                    language,
                ),
            )
        )
    return "\n".join(lines)


def _format_rule(rule: dict[str, Any]) -> str:
    """スキーマの検証規則を表示用に整える。"""
    raw_types = rule.get("type", rule.get("value_types", "unknown"))
    type_names = raw_types if isinstance(raw_types, list) else [raw_types]
    parts = [" / ".join(_code(str(type_name)) for type_name in type_names)]

    enum_values = rule.get("enum", rule.get("values", rule.get("keywords")))
    if isinstance(enum_values, list) and enum_values:
        parts.append(" / ".join(_code(str(value)) for value in enum_values))
    if "minimum" in rule:
        parts.append(f">= {_code(str(rule['minimum']))}")
    if "maximum" in rule:
        parts.append(f"<= {_code(str(rule['maximum']))}")
    if "item_type" in rule:
        parts.append(f"items: {_code(str(rule['item_type']))}")
    if "value_type" in rule:
        parts.append(f"value: {_code(str(rule['value_type']))}")
    if "default" in rule:
        parts.append(f"default: {_code(str(rule['default']))}")
    if rule.get("allow_empty") is True:
        parts.append("empty: OK")
    return "; ".join(parts)


def _localized_schema_description(rule: dict[str, Any], language: str) -> str | None:
    """指定言語のスキーマ説明を取得する。"""
    localized_key = f"description_{language}"
    description = rule.get(localized_key, rule.get("description"))
    if isinstance(description, str) and description.strip():
        return description.strip()
    return None


def _format_html_tag_description(
    tag_name: str,
    tag_data: dict[str, Any],
    language: str,
) -> str:
    """HTMLタグの説明を表示用に整える。"""
    description = _localized_schema_description(tag_data, language)
    if description is not None:
        return description
    if language == "en":
        return f"`<{tag_name}>` has no tag-specific attributes in this reference."
    return f"`<{tag_name}>` に、この表で確認するタグ固有属性はありません。"


def _format_html_attribute_description(
    tag_name: str | None,
    attribute_name: str,
    rule: dict[str, Any],
    language: str,
) -> str:
    """HTML属性の説明を表示用に整える。"""
    description = _localized_schema_description(rule, language)
    if description is not None:
        return description
    if language == "en":
        return _english_html_attribute_description(tag_name, attribute_name)
    return _japanese_html_attribute_description(tag_name, attribute_name)


def _english_html_attribute_description(
    tag_name: str | None,
    attribute_name: str,
) -> str:
    """HTML属性の英語の補足説明を取得する。"""
    descriptions = {
        "abbr": "Provides an abbreviated label for a table header cell.",
        "alt": "Provides alternative text for an image or media source.",
        "aria-hidden": "Hides the element from assistive technologies when true.",
        "aria-label": "Provides an accessible label for assistive technologies.",
        "autoplay": "Starts media playback automatically when allowed by the browser.",
        "cite": "Points to a source URL for a quotation.",
        "class": "Adds one or more class names for CSS or scripts.",
        "colspan": "Makes a table cell span multiple columns.",
        "controls": "Shows browser-provided audio or video controls.",
        "crossorigin": "Controls cross-origin loading behavior.",
        "data": "Stores custom data for scripts or CSS selectors.",
        "datetime": "Stores a machine-readable date or time.",
        "decoding": "Hints how the browser should decode an image.",
        "download": "Suggests downloading the linked resource.",
        "fetchpriority": "Hints the loading priority of a resource.",
        "headers": "Associates a table cell with header cell IDs.",
        "height": "Sets the rendered height.",
        "href": "Sets the destination URL for a link or linked resource.",
        "hreflang": "Describes the language of the linked resource.",
        "id": "Gives the element a unique page-local identifier.",
        "lang": "Declares the language of the element content.",
        "loading": "Controls eager or lazy loading.",
        "loop": "Repeats media playback.",
        "media": "Limits a source or resource to matching media conditions.",
        "muted": "Starts media with audio muted.",
        "placeholder": "Shows helper text before the user enters content.",
        "preload": "Hints how much media should be loaded in advance.",
        "referrerpolicy": "Controls referrer information sent with requests.",
        "rel": "Describes the relationship to a linked resource.",
        "reversed": "Displays an ordered list in descending order.",
        "role": "Declares the element's accessibility role.",
        "rowspan": "Makes a table cell span multiple rows.",
        "scope": "Specifies which cells a table header applies to.",
        "sizes": "Describes image display sizes for responsive images.",
        "src": "Sets the source URL for embedded media.",
        "srcset": "Lists image candidates for responsive images.",
        "start": "Sets the starting number of an ordered list.",
        "style": "Adds inline CSS declarations to the element.",
        "tabindex": "Controls keyboard tab navigation order.",
        "target": "Controls where a linked URL opens.",
        "title": "Adds advisory text for the element.",
        "type": "Specifies a type or format for the element.",
        "usemap": "Associates an image with an image map.",
        "value": "Sets a value such as an ordered-list item number.",
        "width": "Sets the rendered width.",
    }
    if attribute_name in descriptions:
        return descriptions[attribute_name]
    if attribute_name.startswith("aria-"):
        return "Adds accessibility metadata for assistive technologies."
    if attribute_name.startswith("data-"):
        return "Stores custom data for scripts or CSS selectors."
    if tag_name is None:
        return f"Sets the global HTML `{attribute_name}` attribute."
    return f"Sets the `{attribute_name}` attribute on `<{tag_name}>`."


def _japanese_html_attribute_description(
    tag_name: str | None,
    attribute_name: str,
) -> str:
    """HTML属性の日本語の補足説明を取得する。"""
    descriptions = {
        "abbr": "表見出しセルの省略ラベルを指定します。",
        "alt": "画像やメディアの代替テキストを指定します。",
        "aria-hidden": "true の時、支援技術から要素を隠します。",
        "aria-label": "支援技術向けのラベルを指定します。",
        "autoplay": "ブラウザが許可する場合にメディアを自動再生します。",
        "cite": "引用元のURLを指定します。",
        "class": "CSSやスクリプトで使うクラス名を指定します。",
        "colspan": "表セルを横方向に複数列へまたがらせます。",
        "controls": "音声や動画の操作ボタンを表示します。",
        "crossorigin": "外部リソース読み込み時のCORS設定を指定します。",
        "data": "スクリプトやCSSセレクタ用の独自データを持たせます。",
        "datetime": "機械判読できる日付や時刻を指定します。",
        "decoding": "画像のデコード方法のヒントを指定します。",
        "download": "リンク先をダウンロード対象として扱うヒントを指定します。",
        "fetchpriority": "リソース読み込み優先度のヒントを指定します。",
        "headers": "表セルに対応する見出しセルIDを指定します。",
        "height": "表示上の高さを指定します。",
        "href": "リンク先や参照先のURLを指定します。",
        "hreflang": "リンク先リソースの言語を指定します。",
        "id": "ページ内で一意の識別子を指定します。",
        "lang": "要素内容の言語を指定します。",
        "loading": "画像などを即時読み込みまたは遅延読み込みにします。",
        "loop": "メディアを繰り返し再生します。",
        "media": "適用するメディア条件を指定します。",
        "muted": "メディアの音声をミュート状態にします。",
        "placeholder": "入力前に表示する補助テキストを指定します。",
        "preload": "メディアを事前にどこまで読み込むか指定します。",
        "referrerpolicy": "リクエスト時に送る参照元情報を制御します。",
        "rel": "リンク先との関係を指定します。",
        "reversed": "番号付きリストを降順表示にします。",
        "role": "アクセシビリティ上の役割を指定します。",
        "rowspan": "表セルを縦方向に複数行へまたがらせます。",
        "scope": "表見出しがどのセル範囲に対応するか指定します。",
        "sizes": "レスポンシブ画像の表示サイズ候補を指定します。",
        "src": "埋め込みメディアの参照URLを指定します。",
        "srcset": "レスポンシブ画像の候補を指定します。",
        "start": "番号付きリストの開始番号を指定します。",
        "style": "要素へ直接CSSを指定します。",
        "tabindex": "キーボードのタブ移動順を指定します。",
        "target": "リンク先を開く場所を指定します。",
        "title": "要素に補足説明テキストを付けます。",
        "type": "要素の種類や形式を指定します。",
        "usemap": "画像にイメージマップを関連付けます。",
        "value": "番号付きリスト項目などの値を指定します。",
        "width": "表示上の幅を指定します。",
    }
    if attribute_name in descriptions:
        return descriptions[attribute_name]
    if attribute_name.startswith("aria-"):
        return "支援技術向けのアクセシビリティ情報を指定します。"
    if attribute_name.startswith("data-"):
        return "スクリプトやCSSセレクタ用の独自データを持たせます。"
    if tag_name is None:
        return f"HTMLのグローバル属性 `{attribute_name}` を指定します。"
    return f"`<{tag_name}>` の `{attribute_name}` 属性を指定します。"


def _format_wordpress_block_description(
    block_name: str,
    block_data: dict[str, Any],
    language: str,
) -> str:
    """WordPressブロックの説明を表示用に整える。"""
    description = _localized_schema_description(block_data, language)
    if description is not None:
        return description
    if language == "en":
        return f"`wp:{block_name}` has no block-specific JSON attributes here."
    return f"`wp:{block_name}` に、この表で確認するブロック固有JSON属性はありません。"


def _format_wordpress_attribute_description(
    block_name: str | None,
    attribute_name: str,
    rule: dict[str, Any],
    language: str,
) -> str:
    """WordPress属性の説明を表示用に整える。"""
    description = _localized_schema_description(rule, language)
    if description is not None:
        return description
    if language == "en":
        return _english_wordpress_attribute_description(block_name, attribute_name)
    return _japanese_wordpress_attribute_description(block_name, attribute_name)


def _english_wordpress_attribute_description(
    block_name: str | None,
    attribute_name: str,
) -> str:
    """WordPress属性の英語の補足説明を取得する。"""
    descriptions = {
        "align": "Sets block alignment such as wide, full, left, or center.",
        "alt": "Stores alternative text for an image block.",
        "anchor": "Sets the block's HTML anchor ID.",
        "aspectRatio": "Stores the image aspect ratio setting.",
        "backgroundColor": "Stores the named background color preset.",
        "body": "Stores table body row data.",
        "caption": "Stores caption text.",
        "className": "Adds a custom CSS class to the block.",
        "content": "Stores the block's editable content text.",
        "direction": "Sets text direction.",
        "dropCap": "Enables or disables the paragraph drop cap.",
        "focalPoint": "Stores the focal point for cropped media.",
        "fontSize": "Stores the named font-size preset.",
        "foot": "Stores table footer row data.",
        "gradient": "Stores the named gradient preset.",
        "hasFixedLayout": "Uses fixed-width table layout when true.",
        "head": "Stores table header row data.",
        "height": "Stores height for blocks or media.",
        "href": "Stores a link URL.",
        "id": "Stores a related media or entity ID.",
        "imageFill": "Crops media to fill the media-text area when true.",
        "isDecorative": "Marks an image as decorative.",
        "isStackedOnMobile": "Stacks columns on smaller screens when true.",
        "level": "Sets the heading level.",
        "levelOptions": "Limits selectable heading levels.",
        "lightbox": "Stores image lightbox settings.",
        "linkClass": "Adds a CSS class to the generated link.",
        "linkDestination": "Sets where an image or media link points.",
        "linkTarget": "Sets how the generated link opens.",
        "lock": "Stores block locking settings.",
        "mediaAlt": "Stores alternative text for the media item.",
        "mediaId": "Stores the selected media item ID.",
        "mediaLink": "Stores the media attachment page URL.",
        "mediaPosition": "Sets the media side in a media-text block.",
        "mediaSizeSlug": "Stores the selected media size name.",
        "mediaType": "Stores whether the media is an image or video.",
        "mediaUrl": "Stores the selected media URL.",
        "mediaWidth": "Sets the media area width percentage.",
        "metadata": "Stores editor metadata for the block.",
        "opacity": "Sets the separator visual style.",
        "ordered": "Uses an ordered list when true.",
        "placeholder": "Stores editor placeholder text.",
        "rel": "Stores link relationship text.",
        "reversed": "Displays an ordered list in reverse order.",
        "scale": "Sets how image content fits its box.",
        "sizeSlug": "Stores the selected image size name.",
        "start": "Sets the starting number for an ordered list.",
        "style": "Stores block style settings as an object.",
        "tagName": "Sets the HTML tag used by the block wrapper.",
        "templateLock": "Controls whether inner blocks can be moved or edited.",
        "textColor": "Stores the named text color preset.",
        "title": "Stores title text.",
        "type": "Stores a list or block variant type.",
        "url": "Stores a media or link URL.",
        "useFeaturedImage": "Uses the featured image as media when true.",
        "values": "Stores list item markup.",
        "verticalAlignment": "Sets vertical alignment inside the block.",
        "width": "Stores width for blocks or media.",
    }
    if attribute_name in descriptions:
        return descriptions[attribute_name]
    if block_name is None:
        return f"Sets shared WordPress block attribute `{attribute_name}`."
    return f"Sets `{attribute_name}` on `wp:{block_name}`."


def _japanese_wordpress_attribute_description(
    block_name: str | None,
    attribute_name: str,
) -> str:
    """WordPress属性の日本語の補足説明を取得する。"""
    descriptions = {
        "align": "wide/full/left/center などのブロック配置を指定します。",
        "alt": "画像ブロックの代替テキストを保存します。",
        "anchor": "ブロックのHTMLアンカーIDを指定します。",
        "aspectRatio": "画像の縦横比設定を保存します。",
        "backgroundColor": "背景色プリセット名を保存します。",
        "body": "テーブル本文の行データを保存します。",
        "caption": "キャプション文字列を保存します。",
        "className": "ブロックに追加CSSクラスを付けます。",
        "content": "ブロックの編集可能な本文を保存します。",
        "direction": "文字方向を指定します。",
        "dropCap": "段落のドロップキャップを有効または無効にします。",
        "focalPoint": "切り抜き表示時の焦点位置を保存します。",
        "fontSize": "フォントサイズプリセット名を保存します。",
        "foot": "テーブルフッターの行データを保存します。",
        "gradient": "グラデーションプリセット名を保存します。",
        "hasFixedLayout": "true の時、固定幅テーブルレイアウトにします。",
        "head": "テーブルヘッダーの行データを保存します。",
        "height": "ブロックやメディアの高さを保存します。",
        "href": "リンクURLを保存します。",
        "id": "関連するメディアやエンティティのIDを保存します。",
        "imageFill": "true の時、メディアを領域いっぱいに切り抜きます。",
        "isDecorative": "画像を装飾目的として扱うかを保存します。",
        "isStackedOnMobile": "true の時、モバイル幅でカラムを縦積みにします。",
        "level": "見出しレベルを指定します。",
        "levelOptions": "選択可能な見出しレベルを制限します。",
        "lightbox": "画像ライトボックス設定を保存します。",
        "linkClass": "生成されるリンクにCSSクラスを付けます。",
        "linkDestination": "画像やメディアリンクのリンク先を指定します。",
        "linkTarget": "生成されるリンクの開き方を指定します。",
        "lock": "ブロックのロック設定を保存します。",
        "mediaAlt": "メディア項目の代替テキストを保存します。",
        "mediaId": "選択したメディア項目IDを保存します。",
        "mediaLink": "メディア添付ページURLを保存します。",
        "mediaPosition": "メディアとテキストの左右位置を指定します。",
        "mediaSizeSlug": "選択したメディアサイズ名を保存します。",
        "mediaType": "メディアが画像か動画かを保存します。",
        "mediaUrl": "選択したメディアURLを保存します。",
        "mediaWidth": "メディア領域の幅割合を指定します。",
        "metadata": "ブロックのエディター用メタ情報を保存します。",
        "opacity": "区切り線の見た目を指定します。",
        "ordered": "true の時、番号付きリストにします。",
        "placeholder": "エディター上のプレースホルダー文字列を保存します。",
        "rel": "リンクのrel文字列を保存します。",
        "reversed": "番号付きリストを逆順表示にします。",
        "scale": "画像を枠内にどう収めるかを指定します。",
        "sizeSlug": "選択した画像サイズ名を保存します。",
        "start": "番号付きリストの開始番号を指定します。",
        "style": "ブロックのスタイル設定をオブジェクトで保存します。",
        "tagName": "ブロック外側に使うHTMLタグ名を指定します。",
        "templateLock": "内部ブロックの移動や編集制限を指定します。",
        "textColor": "文字色プリセット名を保存します。",
        "title": "タイトル文字列を保存します。",
        "type": "リストやブロックの種類を保存します。",
        "url": "メディアやリンクURLを保存します。",
        "useFeaturedImage": "true の時、アイキャッチ画像をメディアとして使います。",
        "values": "リスト項目のマークアップを保存します。",
        "verticalAlignment": "ブロック内の縦方向の揃え方を指定します。",
        "width": "ブロックやメディアの幅を保存します。",
    }
    if attribute_name in descriptions:
        return descriptions[attribute_name]
    if block_name is None:
        return f"共有WordPressブロック属性 `{attribute_name}` を指定します。"
    return f"`wp:{block_name}` の `{attribute_name}` 属性を指定します。"


def _format_css_property_description(
    property_name: str,
    rule: dict[str, Any],
    language: str,
) -> str:
    """CSSプロパティの説明を表示用に整える。"""
    description = _localized_schema_description(rule, language)
    if description is not None:
        return description

    if language == "en":
        return _english_css_property_description(property_name)
    return _japanese_css_property_description(property_name)


def _english_css_property_description(property_name: str) -> str:
    """CSSプロパティの英語の補足説明を取得する。"""
    descriptions = {
        "aspect-ratio": "Sets the preferred width-to-height ratio of a box.",
        "background": "Sets multiple background values at once.",
        "background-color": "Sets the background color.",
        "border": "Sets border width, style, and color at once.",
        "border-collapse": "Controls whether table borders are shared or separated.",
        "box-shadow": "Adds shadow around an element box.",
        "box-sizing": "Controls whether width and height include padding and borders.",
        "caption-side": "Places a table caption before or after the table.",
        "clear": "Controls whether floated elements may sit beside this element.",
        "color": "Sets the text color.",
        "cursor": "Sets the mouse cursor shown over the element.",
        "display": "Controls the element's layout type.",
        "float": "Moves the element to the left or right so text can flow around it.",
        "font-family": "Sets the font family.",
        "font-size": "Sets the text size.",
        "font-style": "Sets italic or normal font style.",
        "font-weight": "Sets text weight such as boldness.",
        "gap": "Sets spacing between rows and columns in flex or grid layouts.",
        "height": "Sets the element height.",
        "justify-content": "Distributes items along the main axis.",
        "letter-spacing": "Sets spacing between characters.",
        "line-height": "Sets the height of each line of text.",
        "list-style": "Sets list marker style, position, and image at once.",
        "object-fit": "Controls how replaced content such as images fits its box.",
        "object-position": "Positions replaced content such as images inside its box.",
        "opacity": "Sets transparency.",
        "overflow": "Controls how overflowing content is clipped or scrolled.",
        "overflow-wrap": "Controls line breaking for long words.",
        "position": "Sets how the element is positioned.",
        "table-layout": "Controls how table column widths are calculated.",
        "text-align": "Aligns inline content horizontally.",
        "text-decoration": "Sets text decoration such as underline at once.",
        "text-indent": "Sets indentation of the first line.",
        "transform": "Applies visual transforms such as rotate, scale, or translate.",
        "vertical-align": "Aligns inline or table-cell content vertically.",
        "visibility": "Shows or hides the element while keeping its layout space.",
        "white-space": "Controls how spaces and line breaks are handled.",
        "width": "Sets the element width.",
        "word-break": "Controls line breaking inside words.",
        "word-spacing": "Sets spacing between words.",
        "z-index": "Controls stacking order for positioned elements.",
    }
    if property_name in descriptions:
        return descriptions[property_name]
    if property_name.startswith("align-"):
        return "Aligns items inside flex or grid layouts."
    if property_name.startswith("background-"):
        return "Sets one part of the element background."
    if property_name.startswith("border-"):
        return "Sets one part of the element border."
    if property_name.startswith("column-"):
        return "Sets spacing or sizing for columns."
    if property_name.startswith("flex-"):
        return "Controls one part of flexbox layout."
    if property_name.startswith("grid-template-"):
        return "Defines rows or columns in a grid layout."
    if property_name.startswith("list-style-"):
        return "Sets one part of list marker display."
    if property_name.startswith("margin"):
        return "Sets outer spacing around the element."
    if property_name.startswith(("max-", "min-")):
        return "Sets a size limit for the element."
    if property_name.startswith("overflow-"):
        return "Controls overflow on one axis."
    if property_name.startswith("padding"):
        return "Sets inner spacing inside the element."
    if property_name in {"top", "right", "bottom", "left"}:
        return "Sets an offset for a positioned element."
    if property_name.startswith("text-decoration-"):
        return "Sets one part of text decoration."
    return f"Sets the CSS `{property_name}` value."


def _japanese_css_property_description(property_name: str) -> str:
    """CSSプロパティの日本語の補足説明を取得する。"""
    descriptions = {
        "aspect-ratio": "要素の横幅と高さの比率を指定します。",
        "background": "背景に関する値をまとめて指定します。",
        "background-color": "背景色を指定します。",
        "border": "枠線の太さ・種類・色をまとめて指定します。",
        "border-collapse": "表の枠線を重ねるか、分離するかを指定します。",
        "box-shadow": "要素の周囲に影を付けます。",
        "box-sizing": "width/heightに余白や枠線を含めるかを指定します。",
        "caption-side": "表のキャプション位置を指定します。",
        "clear": "floatした要素の回り込みを解除する位置を指定します。",
        "color": "文字色を指定します。",
        "cursor": "要素上にマウスを置いた時のカーソル形状を指定します。",
        "display": "要素の表示形式やレイアウト種別を指定します。",
        "float": "要素を左右に寄せ、文字などを回り込ませます。",
        "font-family": "使用するフォントを指定します。",
        "font-size": "文字サイズを指定します。",
        "font-style": "斜体など、文字のスタイルを指定します。",
        "font-weight": "文字の太さを指定します。",
        "gap": "flex/gridの行・列の間隔を指定します。",
        "height": "要素の高さを指定します。",
        "justify-content": "主軸方向の配置や余白配分を指定します。",
        "letter-spacing": "文字と文字の間隔を指定します。",
        "line-height": "行の高さを指定します。",
        "list-style": "リストマーカーの種類・位置などをまとめて指定します。",
        "object-fit": "画像などを枠内にどう収めるかを指定します。",
        "object-position": "画像などを枠内のどこに配置するかを指定します。",
        "opacity": "透明度を指定します。",
        "overflow": "はみ出した内容を表示・非表示・スクロールにするかを指定します。",
        "overflow-wrap": "長い単語の折り返し方法を指定します。",
        "position": "要素の配置方法を指定します。",
        "table-layout": "表の列幅計算方法を指定します。",
        "text-align": "行内の文字やインライン要素の横位置を指定します。",
        "text-decoration": "下線などの文字装飾をまとめて指定します。",
        "text-indent": "最初の行の字下げ量を指定します。",
        "transform": "回転・拡大縮小・移動などの変形を指定します。",
        "vertical-align": "インライン要素や表セル内の縦位置を指定します。",
        "visibility": "領域を残したまま表示・非表示を切り替えます。",
        "white-space": "空白や改行の扱いを指定します。",
        "width": "要素の幅を指定します。",
        "word-break": "単語内での改行方法を指定します。",
        "word-spacing": "単語間の間隔を指定します。",
        "z-index": "重なり順を指定します。",
    }
    if property_name in descriptions:
        return descriptions[property_name]
    if property_name.startswith("align-"):
        return "flex/grid内の揃え方を指定します。"
    if property_name.startswith("background-"):
        return "背景に関する個別の値を指定します。"
    if property_name.startswith("border-"):
        return "枠線に関する個別の値を指定します。"
    if property_name.startswith("column-"):
        return "段組みや列の間隔を指定します。"
    if property_name.startswith("flex-"):
        return "flexレイアウトの個別設定を指定します。"
    if property_name.startswith("grid-template-"):
        return "gridレイアウトの行または列を定義します。"
    if property_name.startswith("list-style-"):
        return "リストマーカー表示の個別設定を指定します。"
    if property_name.startswith("margin"):
        return "要素の外側の余白を指定します。"
    if property_name.startswith(("max-", "min-")):
        return "要素サイズの上限または下限を指定します。"
    if property_name.startswith("overflow-"):
        return "横方向または縦方向のはみ出しを指定します。"
    if property_name.startswith("padding"):
        return "要素の内側の余白を指定します。"
    if property_name in {"top", "right", "bottom", "left"}:
        return "position指定時の配置オフセットを指定します。"
    if property_name.startswith("text-decoration-"):
        return "文字装飾の個別設定を指定します。"
    return f"CSSプロパティ `{property_name}` の値を指定します。"


def _table_header(*labels: str) -> str:
    """参考表の見出しと区切り行を作る。"""
    return "\n".join(
        (
            _table_row(*labels),
            _table_row(*("---" for _label in labels)),
        )
    )


def _table_row(*values: str) -> str:
    """セルの値から参考表の行を作る。"""
    return "| " + " | ".join(_escape_cell(value) for value in values) + " |"


def _code(value: str) -> str:
    """文字列をインラインコードとして表示できる形にする。"""
    return f"`{value.replace('`', '\\`')}`"


def _escape_cell(value: str) -> str:
    """表のセル内の記号が区切りとして扱われないようにする。"""
    return value.replace("|", "\\|").replace("\n", "<br>")


def _require_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    """入力値が辞書であることを確認して返す。"""
    value = data[key]
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be an object")
    return value


def _as_dict(value: Any) -> dict[str, Any]:
    """値が辞書ならその値を返し、それ以外は空の辞書を返す。"""
    if not isinstance(value, dict):
        raise TypeError("schema entry must be an object")
    return value


def _as_list(value: Any) -> list[Any]:
    """値がリストならその値を返し、それ以外は空のリストを返す。"""
    if not isinstance(value, list):
        raise TypeError("schema entry must be an array")
    return value
