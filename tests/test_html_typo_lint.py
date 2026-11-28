"""HTMLの表記ミスの文法チェックを検証する。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from localization.translator import Translator
from search.html_typo_lint import lint_html_typos

MALFORMED_OPENING_KEYS = {
    "html_typo_lint.html_attribute_outside_opening_tag",
    "html_typo_lint.unexpected_html_tag_close_delimiter",
    "html_typo_lint.malformed_html_attribute_continuation",
}
FULL_WIDTH_HTML_SYNTAX_KEYS = {
    "html_typo_lint.full_width_html_syntax",
    "html_typo_lint.full_width_html_space",
}
QUALIFICATION_ARTICLE_CASE = (
    Path(__file__).parent / "fixtures" / "linter_cases" / "qualification_article_20261023"
)


@pytest.mark.parametrize("attribute", [
    "style", "class", "id", "title", "role", "href", "src", "alt", "width", "height",
    "aria-hidden", "aria-describedby", "data-note", "lang",
])
@pytest.mark.parametrize("value", ['"example"', "'example'", "example"])
def test_lint_reports_attribute_outside_completed_opener(attribute: str, value: str) -> None:
    """文法チェックが属性の外の完了した開始記号を報告することを確認する。"""
    source = f'<!-- wp:html -->\n<div>\n  {attribute}={value}\n>\nBody\n</div>\n<!-- /wp:html -->'
    findings = [message for message in lint_html_typos(source) if message.message_key in MALFORMED_OPENING_KEYS]
    assert [(message.message_key, message.line_number, message.values) for message in findings] == [
        ("html_typo_lint.html_attribute_outside_opening_tag", 3, {"tag": "div", "attribute": attribute}),
    ]


@pytest.mark.parametrize("tag", ["div", "span", "p", "a", "img", "section"])
def test_lint_checks_orphan_attributes_in_plain_html(tag: str) -> None:
    """文法チェックが孤立した属性内のプレーンテキストのHTMLを検査することを確認する。"""
    source = f'<{tag}>\nstyle="color:red"\n>\nBody'
    assert any(
        message.message_key == "html_typo_lint.html_attribute_outside_opening_tag"
        and message.line_number == 2
        and message.values == {"tag": tag, "attribute": "style"}
        for message in lint_html_typos(source)
    )


def test_lint_reports_attribute_only_continuation_without_extra_delimiter() -> None:
    """追加の区切り記号を省いた場合、文法チェックが属性だけの続きを報告することを確認する。"""
    source = '<div>\nstyle="color:red"\n</div>'
    assert any(
        message.message_key == "html_typo_lint.html_attribute_outside_opening_tag"
        and message.line_number == 2 for message in lint_html_typos(source)
    )


def test_lint_consolidates_br_attribute_continuation_at_first_attribute() -> None:
    """brタグの属性が続く場合、最初の属性の位置に診断をまとめることを確認する。"""
    source = '<!-- wp:html -->\n<div>\nstyle="color:red"<br><br>\naria-hidden="true"<br><br>\n></div>\n<!-- /wp:html -->'
    findings = [message for message in lint_html_typos(source) if message.message_key in MALFORMED_OPENING_KEYS]
    assert [(message.message_key, message.line_number, message.values) for message in findings] == [
        ("html_typo_lint.malformed_html_attribute_continuation", 3, {"tag": "div", "attribute": "style"}),
    ]


@pytest.mark.parametrize("break_tag", ["<br>", "<br/>", "<BR />"])
def test_lint_recognizes_live_break_tokens_in_attribute_continuation(break_tag: str) -> None:
    """継続する属性内の改行トークンを文法チェックで認識できることを確認する。"""
    source = f'<div>\nstyle="color:red"{break_tag}\n>\nBody</div>'
    assert any(
        message.message_key == "html_typo_lint.malformed_html_attribute_continuation"
        for message in lint_html_typos(source)
    )


def test_lint_reports_contextual_stray_tag_delimiter() -> None:
    """文法チェックが文脈に応じたの孤立したタグの区切り記号を報告することを確認する。"""
    source = '<!-- wp:html -->\n<div>\n>\nBody\n</div>\n<!-- /wp:html -->'
    findings = [message for message in lint_html_typos(source) if message.message_key in MALFORMED_OPENING_KEYS]
    assert [(message.message_key, message.line_number) for message in findings] == [
        ("html_typo_lint.unexpected_html_tag_close_delimiter", 3),
    ]


@pytest.mark.parametrize("source", [
    '<div style="color:red">text</div>',
    '<div\n style="color:red"\n aria-hidden="true"\n>\ntext\n</div>',
    '<div\n title="a > b and <br>"\n style="color:red"\n>\ntext\n</div>',
    '<div style="color:red">\nline 1<br><br>\nline 2\n</div>',
    '<div>line 1<br><br>\nline 2\n</div>',
    '<p>Use style="color:red" in a tag.</p>',
    '<p>style="color:red"</p>',
    '<div>\nAn example follows:\nstyle="color:red"\n>\n</div>',
    '<p>The comparison is 3 > 2.</p>',
    '<div>\n> comparison text\n</div>',
    '<div>\nunknown-setting="value"\n>\nBody</div>',
    '<code>&lt;div&gt;\nstyle="color:red"\n&gt;&lt;/div&gt;</code>',
    '<pre><code>&lt;div style="color:red"&gt;</code></pre>',
    '<!-- <div>\nstyle="color:red"\n>\n</div> -->',
    '<div><!-- example -->\nstyle="color:red"\n>\n</div>',
    '<div>\nstyle="color:red"\n<br>normal body text</div>',
    '<div/>\nstyle="color:red"\n>',
    '<div\n style="color:red"\n',
    '<div>\nstyle="color:red"\n&lt;br&gt;\n&gt;\n</div>',
    '<!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Title</h2><!-- /wp:heading -->',
    '<!-- wp:heading {"level":4} --><h4 class="wp-block-heading">Title</h4><!-- /wp:heading -->',
])
def test_lint_preserves_valid_markup_and_attribute_prose(source: str) -> None:
    """文法チェックが正しいのマークアップと属性の本文を維持することを確認する。"""
    assert not any(message.message_key in MALFORMED_OPENING_KEYS for message in lint_html_typos(source))


@pytest.mark.parametrize("wrapper", ["code", "pre", "textarea", "script", "style"])
def test_orphan_attribute_rules_ignore_display_and_raw_text_regions(wrapper: str) -> None:
    """孤立した属性の規則の無視の表示と生の文字列の領域を確認する。"""
    source = f'<{wrapper}><div>\nstyle="color:red"<br>\n>\n</div></{wrapper}>'
    assert not any(message.message_key in MALFORMED_OPENING_KEYS for message in lint_html_typos(source))


def test_orphan_attribute_state_resumes_after_code_region() -> None:
    """コードの領域後、孤立した属性の状態が再開することを確認する。"""
    source = '<code>&lt;div&gt;</code>\n<div>\nstyle="color:red"\n>\n</div>'
    assert [
        message.line_number for message in lint_html_typos(source)
        if message.message_key in MALFORMED_OPENING_KEYS
    ] == [3]


def test_orphan_attribute_quoted_values_do_not_end_at_embedded_delimiters() -> None:
    """孤立した属性の引用符で囲まれたの値の行わないの末尾での組み込みの区切り記号を確認する。"""
    source = '<div>\ntitle="a > b"\nstyle="color:red"\n>\nBody</div>'
    findings = [message for message in lint_html_typos(source) if message.message_key in MALFORMED_OPENING_KEYS]
    assert len(findings) == 1 and findings[0].line_number == 2
    assert findings[0].values == {"tag": "div", "attribute": "title"}


def test_orphan_attribute_detection_does_not_stop_after_first_broken_element() -> None:
    """孤立した属性の検出の行わないの停止後の最初の壊れたの要素を確認する。"""
    source = '<div>\nstyle="color:red"\n>\nA</div>\n<section>\ndata-note="x"\n>\nB</section>'
    assert [
        message.line_number for message in lint_html_typos(source)
        if message.message_key in MALFORMED_OPENING_KEYS
    ] == [2, 6]


def test_separator_code_cascade_does_not_suppress_following_orphan_attribute() -> None:
    """区切りのコードの連鎖の行わないの抑制の直後の孤立した属性を確認する。"""
    source = (
        '<!-- wp:separator -->\n<hr class="wp-block-separator"><code><code>\n'
        '<!-- /wp:separator -->\n<!-- wp:html -->\n<div>\nstyle="color:red"\n>\nBody</div>\n<!-- /wp:html -->'
    )
    assert [
        message.line_number for message in lint_html_typos(source)
        if message.message_key in MALFORMED_OPENING_KEYS
    ] == [6]


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_orphan_attribute_source_lines_and_read_only_behavior(newline: str) -> None:
    """孤立した属性の原文の行と読み取り専用の動作を確認する。"""
    source = newline.join(['<!-- wp:html -->', '<div>', '  STYLE="color:red"', '>', '</div>', '<!-- /wp:html -->'])
    original = source
    findings = [message for message in lint_html_typos(source) if message.message_key in MALFORMED_OPENING_KEYS]
    assert len(findings) == 1 and findings[0].line_number == 3
    assert findings[0].values == {"tag": "div", "attribute": "style"}
    assert source == original


def test_qualification_article_broken_sample_reports_all_11_malformed_openers() -> None:
    """修飾の原稿の壊れたのサンプルがすべての11の壊れたの開始記号を報告することを確認する。"""
    source = (QUALIFICATION_ARTICLE_CASE / "broken.wp_html").read_text(encoding="utf-8-sig")
    findings = [message for message in lint_html_typos(source) if message.message_key in MALFORMED_OPENING_KEYS]
    assert [message.line_number for message in findings] == [22, 82, 109, 127, 151, 211, 288, 361, 430, 496, 523]
    assert sum(message.message_key.endswith("malformed_html_attribute_continuation") for message in findings) == 3


def test_qualification_article_fixed_sample_has_no_malformed_opening_findings() -> None:
    """修飾の原稿の固定のサンプルがなしの壊れたの開始の指摘を持つことを確認する。"""
    source = (QUALIFICATION_ARTICLE_CASE / "fixed.wp_html").read_text(encoding="utf-8-sig")
    assert not any(message.message_key in MALFORMED_OPENING_KEYS for message in lint_html_typos(source))


@pytest.mark.parametrize("language", ["ja", "en"])
@pytest.mark.parametrize("key", sorted(MALFORMED_OPENING_KEYS))
def test_malformed_opening_messages_have_formattable_translations(language: str, key: str) -> None:
    """壊れたの開始のメッセージが整形できるの翻訳を持つことを確認する。"""
    translator = Translator(Path("resources"), language)
    message = translator.text(key, tag="div", attribute="style")
    assert message != key
    assert "<div>" in message
    assert "{tag}" not in message and "{attribute}" not in message


def test_lint_reports_full_width_html_open_delimiter() -> None:
    """HTMLの開始区切りに全角文字を使うと診断することを確認する。"""
    source = '＜span style="color: #65FFCD">文章</span>'
    findings = [
        message for message in lint_html_typos(source)
        if message.message_key == "html_typo_lint.full_width_html_syntax"
    ]
    assert [(message.line_number, message.values) for message in findings] == [
        (1, {"symbol": "＜", "suggestion": "<"}),
    ]


def test_lint_reports_full_width_html_syntax_punctuation() -> None:
    """文法チェックが全角のHTMLの構文の句読点を報告することを確認する。"""
    source = "＜／span＞"
    findings = [
        message for message in lint_html_typos(source)
        if message.message_key == "html_typo_lint.full_width_html_syntax"
    ]
    assert [message.values for message in findings] == [
        {"symbol": "＜", "suggestion": "<"},
        {"symbol": "／", "suggestion": "/"},
        {"symbol": "＞", "suggestion": ">"},
    ]


def test_lint_reports_full_width_space_in_core_block_html_tag() -> None:
    """文法チェックが全角の空白内のコアブロックのHTMLのタグを報告することを確認する。"""
    source = (
        '<!-- wp:paragraph -->\n<p　class="has-text-color">文章</p>\n'
        '<!-- /wp:paragraph -->'
    )
    findings = [
        message for message in lint_html_typos(source)
        if message.message_key == "html_typo_lint.full_width_html_space"
    ]
    assert [(message.line_number, message.values) for message in findings] == [(2, None)]


@pytest.mark.parametrize("source", [
    '<span title="日本語　文章">本文</span>',
    '<code>＜span style＝＂color:red＂＞見本＜／span＞</code>',
    '<pre>＜div　class＝＂sample＂＞見本＜／div＞</pre>',
    '<!-- ＜span　style＝＂color:red＂＞コメント内の見本 -->',
    '<span style="color: #65FFCD">文章</span>',
])
def test_lint_does_not_report_full_width_html_syntax_in_values_or_examples(
    source: str,
) -> None:
    """文法チェックの行わないの報告の全角のHTMLの構文内の値または例を確認する。"""
    assert not any(
        message.message_key in FULL_WIDTH_HTML_SYNTAX_KEYS
        for message in lint_html_typos(source)
    )


@pytest.mark.parametrize("language", ["ja", "en"])
def test_full_width_html_messages_have_formattable_translations(language: str) -> None:
    """全角のHTMLのメッセージが整形できるの翻訳を持つことを確認する。"""
    translator = Translator(Path("resources"), language)
    syntax_message = translator.text(
        "html_typo_lint.full_width_html_syntax",
        symbol="＜",
        suggestion="<",
    )
    space_message = translator.text("html_typo_lint.full_width_html_space")
    assert syntax_message != "html_typo_lint.full_width_html_syntax"
    assert "＜" in syntax_message and "<" in syntax_message
    assert "U+3000" in space_message and "U+0020" in space_message


@pytest.mark.parametrize("tag", ["strong", "span", "mark", "em", "a", "b", "i", "small", "code"])
@pytest.mark.parametrize("prefix", ["", "<em>"])
def test_lint_reports_unmatched_inline_close(tag: str, prefix: str) -> None:
    """文法チェックが対応のないインラインの閉じる操作を報告することを確認する。"""
    if prefix == "<em>" and tag == "em":
        prefix = "<strong>"
    messages = lint_html_typos(f"<p>{prefix}Body\n</{tag}></p>")
    assert any(
        message.message_key == "html_typo_lint.unexpected_inline_closing_tag"
        and message.line_number == 2
        and message.values == {"tag": tag}
        for message in messages
    )


@pytest.mark.parametrize("level", range(1, 7))
@pytest.mark.parametrize("wordpress", [False, True])
def test_lint_checks_heading_pairs(level: int, wordpress: bool) -> None:
    """文法チェックが見出しの対応する組を検査することを確認する。"""
    html = f"<h{level}>Heading</h{level % 6 + 1}>"
    if wordpress:
        html = f"<!-- wp:heading -->{html}<!-- /wp:heading -->"
    assert any(
        message.message_key == "html_typo_lint.unexpected_html_closing_tag"
        for message in lint_html_typos(html)
    )


@pytest.mark.parametrize(
    ("html", "key"),
    [
        ("<p>outer<p>inner</p></p>", "nested_html_tag"),
        ('<a href="#a"><span><a href="#b">Link</a></span></a>', "nested_html_tag"),
        ("<p><span><div>Body</div></span></p>", "invalid_html_child"),
        ("<li>Body</li>", "invalid_html_parent"),
        ("<ul><div><li>Body</li></div></ul>", "invalid_html_parent"),
        ("<!-- wp:list-item --><li>Body</li><!-- /wp:list-item -->", "invalid_wordpress_parent"),
        ("<!-- wp:column --><div></div><!-- /wp:column -->", "invalid_wordpress_parent"),
        (
            (
                '<!-- wp:button --><div class="wp-block-button"><a '
                'class="wp-block-button__link wp-element-button">Button</a></div>'
                '<!-- /wp:button -->'
            ),
            "invalid_wordpress_parent",
        ),
        (
            (
                '<!-- wp:accordion-item --><div class="wp-block-accordion-item"></div>'
                '<!-- /wp:accordion-item -->'
            ),
            "invalid_wordpress_parent",
        ),
        (
            (
                '<!-- wp:accordion-heading --><h3 class="wp-block-accordion-heading">'
                '<button type="button" class="wp-block-accordion-heading__toggle">'
                '<span class="wp-block-accordion-heading__toggle-title">Title</span>'
                "</button></h3><!-- /wp:accordion-heading -->"
            ),
            "invalid_wordpress_parent",
        ),
        (
            (
                '<!-- wp:accordion-panel --><div role="region" '
                'class="wp-block-accordion-panel"></div><!-- /wp:accordion-panel -->'
            ),
            "invalid_wordpress_parent",
        ),
        (
            (
                "<!-- wp:paragraph --><p>Body</p><!-- wp:image -->"
                '<figure><img src="x.jpg" alt=""></figure><!-- /wp:image --><!-- /wp:paragraph -->'
            ),
            "invalid_wordpress_child",
        ),
        (
            "<!-- wp:paragraph --><p>One</p><p>Two</p><!-- /wp:paragraph -->",
            "wordpress_block_html_shape",
        ),
        ("<!-- wp:heading --><p>Body</p><!-- /wp:heading -->", "wordpress_block_html_shape"),
        (
            (
                '<!-- wp:paragraph {"style":{"typography":{"fontWeight":"bold"}}} -->'
                '<p>Body</p><!-- /wp:paragraph -->'
            ),
            "wordpress_block_attribute_html_mismatch",
        ),
    ],
)
def test_reported_lint_gaps(html: str, key: str) -> None:
    """報告された文法チェックの欠落を確認する。"""
    assert any(message.message_key == f"html_typo_lint.{key}" for message in lint_html_typos(html))


@pytest.mark.parametrize(
    "comment",
    [
        "<!-- wp:latest-posts /-->",
        '<!-- wp:latest-posts {"postsToShow":4} /-->',
        '<!-- wp:my-plugin/widget {"url":"https://example.com/"} /-->',
        "<!-- wp:core/latest-posts/-->",
    ],
)
def test_lint_accepts_wordpress_self_closing_comments(comment: str) -> None:
    """文法チェックがWordPressの自己終了のコメントを受け入れることを確認する。"""
    assert lint_html_typos(comment) == []


@pytest.mark.parametrize(
    "html",
    [
        '<a href="#"><div><p>Block link</p></div></a>',
        "<ul><li>Outer<ol><li>Inner</li></ol></li></ul>",
        "<menu><li>Item</li></menu>",
        "<p>&lt;p&gt;&lt;p&gt;Displayed code&lt;/p&gt;&lt;/p&gt;</p>",
        (
            '<!-- wp:paragraph {"style":{"typography":{"fontWeight":"700"}}} -->'
            '<p style="font-weight:700">Body</p><!-- /wp:paragraph -->'
        ),
        (
            '<!-- wp:paragraph --><p><span style="font-weight:bold">Inline</span></p>'
            '<!-- /wp:paragraph -->'
        ),
    ],
)
def test_lint_preserves_valid_html_around_reported_gaps(html: str) -> None:
    """文法チェックが正しいのHTMLの周辺の報告された欠落を維持することを確認する。"""
    assert lint_html_typos(html) == []


@pytest.mark.parametrize(
    ("attributes", "html", "mismatch"),
    [
        ({"style": {"typography": {"fontWeight": "700"}}}, '<p style="font-weight:400">Text</p>', True),
        ({"style": {"typography": {"fontWeight": "700"}}}, "<p>Text</p>", True),
        ({}, '<p style="font-weight:700">Text</p>', False),
        ({}, '<p style="font-style:italic">Text</p>', False),
        ({}, '<p style="color:#ff0000">Text</p>', False),
        ({"style": {"color": {"text": "#ff0000"}}}, '<p style="color:#ff0000">Text</p>', False),
        ({"style": {"typography": {"lineHeight": 1.5}}}, '<p style="line-height:1.5">Text</p>', False),
        (
            {"style": {"typography": {"fontSize": "var:preset|font-size|large"}}},
            '<p style="font-size:var(--wp--preset--font-size--large)">Text</p>',
            False,
        ),
        ({"textColor": "primary"}, '<p class="has-primary-color has-text-color">Text</p>', False),
        ({"textColor": "primary"}, '<p class="has-secondary-color has-text-color">Text</p>', False),
        ({"backgroundColor": "base"}, '<p class="has-base-background-color has-background">Text</p>', False),
        ({"fontSize": "large"}, '<p class="has-large-font-size">Text</p>', False),
        ({"fontSize": "large"}, '<p class="has-small-font-size">Text</p>', True),
        ({}, '<p style="--note: \'font-weight:bold\';">Text</p>', False),
        ({}, '<p style="/* font-weight:bold; */ margin:0">Text</p>', False),
        ({}, '<p><span style="color:red">Inline</span></p>', False),
        # CSS owns syntax errors; do not add speculative consistency warnings.
        ({}, '<p style="font-weight:">Text</p>', False),
    ],
)
def test_paragraph_style_and_preset_consistency(
    attributes: dict[str, object], html: str, mismatch: bool,
) -> None:
    """段落のスタイルとプリセットの整合性を確認する。"""
    text = f"<!-- wp:paragraph {json.dumps(attributes)} -->{html}<!-- /wp:paragraph -->"
    messages = lint_html_typos(text)
    assert any(
        message.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        for message in messages
    ) is mismatch


def test_block_checks_require_known_html_tags_without_rejecting_additional_markup() -> None:
    """JSONで指定した見出しと、Buttonの必須の子要素を確認する。"""
    heading = '<!-- wp:heading {"level":3} --><h3 class="wp-block-heading"><u>Title</u></h3><!-- /wp:heading -->'
    assert lint_html_typos(heading) == []
    assert lint_html_typos(heading.replace(' {"level":3}', "")) == []
    messages = lint_html_typos(heading.replace("h3", "h2"))
    assert any((item.values or {}).get("attribute") == "level" for item in messages)

    button = (
        '<!-- wp:buttons --><div class="wp-block-buttons"><!-- wp:button -->'
        '<div class="wp-block-button"><span>Text</span></div>'
        '<!-- /wp:button --></div><!-- /wp:buttons -->'
    )
    messages = lint_html_typos(button)
    assert any((item.values or {}).get("attribute") == "link.tag" for item in messages)


@pytest.mark.parametrize(
    "html",
    [
        (
            "<!-- wp:list --><ul><!-- wp:list-item --><li>Outer"
            "<!-- wp:list --><ol><!-- wp:list-item --><li>Inner</li>"
            "<!-- /wp:list-item --></ol><!-- /wp:list --></li>"
            "<!-- /wp:list-item --></ul><!-- /wp:list -->"
        ),
        (
            '<!-- wp:columns --><div class="wp-block-columns"><!-- wp:column -->'
            '<div class="wp-block-column">'
            "<!-- wp:paragraph --><p>Column text</p><!-- /wp:paragraph -->"
            "</div><!-- /wp:column --></div><!-- /wp:columns -->"
        ),
        (
            '<!-- wp:group --><div class="wp-block-group"><!-- wp:latest-posts /-->'
            "<!-- wp:paragraph --><p>Following text</p><!-- /wp:paragraph -->"
            "</div><!-- /wp:group -->"
        ),
    ],
)
def test_valid_wordpress_containers_keep_both_stacks_balanced(html: str) -> None:
    """正しいのWordPressのコンテナの保持するの両方のスタックの対応が取れたを確認する。"""
    assert lint_html_typos(html) == []


def test_invalid_json_in_self_closing_block_does_not_open_a_block() -> None:
    """不正なJSON内の自己終了のブロックの行わないの開く操作のブロックを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:latest-posts {"postsToShow":} /-->\n'
        '<!-- wp:paragraph --><p>Following text</p><!-- /wp:paragraph -->'
    )
    assert [message.message_key for message in messages] == [
        "html_typo_lint.invalid_wordpress_block_attributes",
    ]


def test_self_closing_paragraph_does_not_affect_pair_counts() -> None:
    """自己終了の段落ブロックが開始・終了コメントの対の集計に影響しないことを確認する。"""
    assert lint_html_typos("<!-- wp:paragraph /-->") == []


def test_html_outside_wordpress_blocks_is_still_checked() -> None:
    """WordPressブロックの外にあるHTMLも検査対象になることを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:paragraph --><p>Body</p><!-- /wp:paragraph -->\n<div>'
    )
    assert any(
        message.message_key == "html_typo_lint.missing_html_closing_tag"
        and message.line_number == 2
        for message in messages
    )


def test_nested_containers_do_not_duplicate_the_same_html_diagnostic() -> None:
    """入れ子のコンテナの行わないの重複した同じHTMLの診断を確認する。"""
    messages = lint_html_typos(
        '<!-- wp:group --><section><!-- wp:html -->\n<div>Body\n'
        '<!-- /wp:html --></section><!-- /wp:group -->'
    )
    assert sum(
        message.message_key == "html_typo_lint.html_crosses_wordpress_boundary"
        and message.values == {"tag": "div", "block": "html", "boundary_line": "3"}
        for message in messages
    ) == 1


@pytest.mark.parametrize("block,tag", [("paragraph", "p"), ("heading", "h2")])
def test_html_in_comments_cannot_fake_a_wordpress_root(block: str, tag: str) -> None:
    """HTML内のコメントのできないの偽のWordPressのルート要素を確認する。"""
    messages = lint_html_typos(f"<!-- wp:{block} --><!-- <{tag}>Fake</{tag}> --><!-- /wp:{block} -->")
    assert any(
        message.message_key == "html_typo_lint.wordpress_block_html_shape"
        for message in messages
    )


def test_heading_consistency_ignores_tags_in_comments() -> None:
    """見出しの整合性がタグ内のコメントを無視することを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:heading {"level":3} --><!-- <h3>fake</h3> -->'
        '<h2>Real</h2><!-- /wp:heading -->'
    )
    assert any(
        message.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        for message in messages
    )


def test_repeated_nested_code_reports_each_inner_opening() -> None:
    """繰り返されるの入れ子のコードが各内側の開始を報告することを確認する。"""
    messages = lint_html_typos("<code><code>One</code><code>Two</code></code>")
    # Identical diagnostics on the same line are intentionally displayed once.
    assert any(message.message_key == "html_typo_lint.nested_html_tag" for message in messages)
    messages = lint_html_typos("<code>\n<code>One</code>\n<code>Two</code>\n</code>")
    assert [message.line_number for message in messages if message.message_key == "html_typo_lint.nested_html_tag"] == [2, 3]


def test_wrong_wordpress_closing_comment_does_not_destroy_ignored_body_range() -> None:
    """誤ったのWordPressの終了のコメントの行わないの破棄の無視された本文の範囲を確認する。"""
    messages = lint_html_typos(
        '<!-- wp:html --><div>&lt;code&gt;/code&gt;</div>\n'
        '<!-- /wp:paragraph -->\n<!-- /wp:html -->'
    )
    assert any(message.message_key == "html_typo_lint.mismatched_wordpress_block" for message in messages)
    assert not any(message.message_key == "html_typo_lint.escaped_code_close_fragment" for message in messages)


@pytest.mark.parametrize("language", ["ja", "en"])
def test_new_lint_messages_have_formattable_translations(language: str) -> None:
    """新規の文法チェックのメッセージが整形できるの翻訳を持つことを確認する。"""
    translator = Translator(Path("resources"), language)
    sources = [
        '<p>Body</strong></p>',
        '<p><div>Body</div></p>',
        '<li>Item</li>',
        '<!-- wp:column --><div></div><!-- /wp:column -->',
        '<!-- wp:paragraph --><p>Body</p><!-- wp:image /--><!-- /wp:paragraph -->',
        '<!-- wp:heading --><p>Body</p><!-- /wp:heading -->',
    ]
    for source in sources:
        for message in lint_html_typos(source):
            text = translator.text(message.message_key, **(message.values or {}))
            assert text != message.message_key
            assert "{tag}" not in text
            assert "{block}" not in text
            assert "{parent}" not in text


def test_lint_reports_html_tag_and_attribute_typos() -> None:
    """文法チェックがHTMLのタグと属性の表記ミスを報告することを確認する。"""
    messages = lint_html_typos('<p clas="lead"><spna herf="https://example.com">本文</spna></p>')

    assert any(message.message_key == "html_typo_lint.unknown_html_tag" for message in messages)
    assert any(
        message.message_key == "html_typo_lint.unknown_html_attribute"
        and message.values
        and message.values.get("suggestion") == "class"
        for message in messages
    )
    assert any(
        message.message_key == "html_typo_lint.unknown_html_attribute"
        and message.values
        and message.values.get("suggestion") == "href"
        for message in messages
    )


def test_lint_reports_unknown_html_tag_once_per_line() -> None:
    """文法チェックが未登録のHTMLのタグの1回だけごとの行を報告することを確認する。"""
    messages = lint_html_typos("<p><pr>Body</pr></p>")

    unknown_messages = [
        message
        for message in messages
        if message.message_key == "html_typo_lint.unknown_html_tag"
        and message.values
        and message.values.get("tag") == "pr"
    ]
    assert len(unknown_messages) == 1


def test_lint_reports_wordpress_block_typo() -> None:
    """文法チェックがWordPressのブロックの表記ミスを報告することを確認する。"""
    messages = lint_html_typos("<!-- wp:paragaph -->\n<p>本文</p>\n<!-- /wp:paragaph -->")

    assert any(
        message.message_key == "html_typo_lint.unknown_wordpress_block"
        and message.values
        and message.values.get("suggestion") == "paragraph"
        for message in messages
    )


def test_lint_reports_wordpress_paragraph_missing_p_open() -> None:
    """文法チェックがWordPressの段落の不足したpの開く操作を報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "段落分割後にp開始タグが抜けています。</p>\n"
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key == "html_typo_lint.wordpress_paragraph_missing_p_open"
        and message.line_number == 2
        for message in messages
    )


def test_lint_reports_wordpress_paragraph_missing_p_close() -> None:
    """文法チェックがWordPressの段落の不足したpの閉じる操作を報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p>最後のp終了タグが抜けています。\n"
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key == "html_typo_lint.wordpress_paragraph_missing_p_close"
        and message.line_number == 2
        for message in messages
    )


def test_lint_reports_unexpected_wordpress_paragraph_closing_block() -> None:
    """文法チェックが想定外のWordPressの段落の終了コメントを報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- /wp:paragraph -->\n"
        "<p>終了コメントから始まっています。</p>\n"
    )

    assert any(
        message.message_key
        == "html_typo_lint.unexpected_wordpress_closing_block"
        and message.line_number == 1
        and message.values
        and message.values.get("block") == "paragraph"
        for message in messages
    )


def test_lint_reports_missing_wordpress_html_closing_block() -> None:
    """文法チェックが不足したWordPressのHTMLの終了コメントを報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:html -->\n"
        "<div class=\"notice\">閉じ忘れたHTMLブロックです。\n"
        "<!-- wp:paragraph -->\n"
        "<p>この段落が巻き込まれる可能性があります。</p>\n"
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key
        == "html_typo_lint.missing_wordpress_html_closing_block"
        and message.line_number == 1
        and message.values
        and message.values.get("block") == "html"
        for message in messages
    )


def test_lint_reports_wordpress_block_comment_inside_html_block() -> None:
    """文法チェックがWordPressのブロックのコメント内のHTMLのブロックを報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:html -->\n"
        "<div>本文</div>\n"
        "<!-- wp:paragraph -->\n"
        "<p>混入した段落です。</p>\n"
        "<!-- /wp:paragraph -->\n"
        "<!-- /wp:html -->"
    )

    assert any(
        message.message_key
        == "html_typo_lint.wordpress_html_contains_block_comment"
        and message.line_number == 3
        for message in messages
    )


def test_lint_reports_div_inside_wordpress_paragraph_block() -> None:
    """文法チェックがdiv内のWordPressの段落ブロックを報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<div>段落ブロック内のdivです。</div>\n"
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key
        == "html_typo_lint.wordpress_paragraph_contains_div"
        and message.line_number == 2
        for message in messages
    )


def test_lint_reports_simple_count_mismatches() -> None:
    """文法チェックが単純な件数の不一致を報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p><pre><code>本文</code></pre>\n"
        "<!-- wp:html -->\n"
        "<div>HTML</div>\n"
    )

    message_keys = {message.message_key for message in messages}
    assert "html_typo_lint.count_mismatch_wordpress_paragraph" in message_keys
    assert "html_typo_lint.count_mismatch_wordpress_html" in message_keys
    assert "html_typo_lint.count_mismatch_p" in message_keys


def test_lint_reports_pre_and_code_count_mismatches() -> None:
    """文法チェックがpreタグとコードの件数の不一致を報告することを確認する。"""
    messages = lint_html_typos("<pre><code>本文</pre>")

    message_keys = {message.message_key for message in messages}
    assert "html_typo_lint.count_mismatch_code" in message_keys
    assert "html_typo_lint.count_mismatch_pre" not in message_keys


def test_lint_reports_html_tag_closing_order_for_tracked_tags() -> None:
    """文法チェックがHTMLのタグの終了の順序の用の追跡中のタグを報告することを確認する。"""
    messages = lint_html_typos("<pre><code>sample</pre></code>")

    assert any(
        message.message_key == "html_typo_lint.mismatched_html_tag"
        and message.line_number == 1
        and message.values == {"open_tag": "code", "close_tag": "pre"}
        for message in messages
    )


def test_lint_reports_unexpected_html_closing_tag_for_tracked_tags() -> None:
    """文法チェックが想定外のHTMLの終了タグの用の追跡中のタグを報告することを確認する。"""
    messages = lint_html_typos("<p>text</p>\n</pre>")

    assert any(
        message.message_key == "html_typo_lint.unexpected_html_closing_tag"
        and message.line_number == 2
        and message.values == {"tag": "pre"}
        for message in messages
    )


def test_lint_reports_missing_html_closing_tag_for_tracked_tags() -> None:
    """文法チェックが不足したHTMLの終了タグの用の追跡中のタグを報告することを確認する。"""
    messages = lint_html_typos("<pre><code>sample</code>")

    assert any(
        message.message_key == "html_typo_lint.missing_html_closing_tag"
        and message.line_number == 1
        and message.values == {"tag": "pre"}
        for message in messages
    )


def test_lint_reports_nested_code_and_strong_count_mismatch() -> None:
    """文法チェックが入れ子のコードとstrongタグの件数の不一致を報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p><code>one <code>two</code></p>\n"
        "<p><strong>strong text</p>\n"
        "<!-- /wp:paragraph -->"
    )

    message_keys = {message.message_key for message in messages}
    assert "html_typo_lint.nested_html_tag" in message_keys
    assert "html_typo_lint.count_mismatch_code" in message_keys
    assert "html_typo_lint.inline_tag_unclosed_before_parent" in message_keys


def test_lint_reports_inline_tag_unclosed_before_paragraph_close() -> None:
    """段落の閉じる操作前、文法チェックがインラインのタグの閉じられていないを報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p>本文です。<br><br>\n"
        "<strong>重要です。</p>\n"
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key == "html_typo_lint.inline_tag_unclosed_before_parent"
        and message.line_number == 3
        and message.values == {"tag": "strong", "parent": "p"}
        for message in messages
    )


def test_lint_reports_inline_tag_closing_order() -> None:
    """文法チェックがインラインのタグの終了の順序を報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        '<p><strong><span style="color: red;">重要です。</strong></span></p>\n'
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key == "html_typo_lint.inline_tag_closing_order"
        and message.line_number == 2
        and message.values == {"tag": "span", "closing_tag": "strong"}
        for message in messages
    )


def test_lint_reports_inline_tag_unclosed_at_document_end() -> None:
    """文法チェックがインラインのタグの閉じられていないでの文書末尾を報告することを確認する。"""
    messages = lint_html_typos("<p><strong>重要です。")

    assert any(
        message.message_key == "html_typo_lint.inline_tag_unclosed_at_document_end"
        and message.line_number == 1
        and message.values == {"tag": "strong"}
        for message in messages
    )


def test_lint_accepts_escaped_html_inside_wordpress_code_block() -> None:
    """文法チェックがエスケープ済みのHTML内のWordPressのコードブロックを受け入れることを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:code -->\n"
        "<pre class=\"wp-block-code\"><code>&lt;!-- wp:paragraph --&gt;\n"
        "&lt;p&gt;段落は &lt;code&gt;&amp;lt;p&amp;gt;&lt;/code&gt; タグで作ります。&lt;/p&gt;\n"
        "&lt;!-- /wp:paragraph --&gt;</code></pre>\n"
        "<!-- /wp:code -->"
    )

    assert not any(
        message.message_key == "html_typo_lint.escaped_code_close_fragment"
        for message in messages
    )


def test_lint_reports_orphan_empty_paragraph_and_break() -> None:
    """文法チェックが孤立した空の段落と区切りを報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p>本文</p>\n"
        "<!-- /wp:paragraph -->\n"
        "<p></p>\n"
        "<br>\n"
    )

    message_keys = {message.message_key for message in messages}
    assert "html_typo_lint.empty_paragraph_outside_wordpress_block" in message_keys
    assert "html_typo_lint.break_outside_wordpress_block" in message_keys


def test_lint_reports_separator_code_contamination_and_escaped_code_fragment() -> None:
    """文法チェックが区切りのコードの混入とエスケープ済みのコードの断片を報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p><code>&lt;!-- wp:paragraph --&gt;/code&gt;</code></p>\n"
        "<!-- /wp:paragraph -->\n"
        "<!-- wp:separator -->\n"
        '<hr class="wp-block-separator has-alpha-channel-opacity"><code><code>\n'
        "<!-- /wp:separator -->"
    )

    message_keys = {message.message_key for message in messages}
    assert "html_typo_lint.wordpress_separator_contains_code" in message_keys
    assert "html_typo_lint.escaped_code_close_fragment" in message_keys


def test_lint_suppresses_separator_code_cascade_errors() -> None:
    """文法チェックが区切りのコードの連鎖のエラーを抑えることを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:separator -->\n"
        '<hr class="wp-block-separator has-alpha-channel-opacity"><code><code>\n'
        "<!-- /wp:separator -->\n"
        '<!-- wp:heading {"level":3} -->\n'
        '<h3 class="wp-block-heading">Sub block</h3>\n'
        "<!-- /wp:heading -->"
    )

    message_keys = [message.message_key for message in messages]
    assert message_keys == ["html_typo_lint.wordpress_separator_contains_code"]


def test_separator_cascade_keeps_independent_errors_on_same_line() -> None:
    """区切り文字の誤りから派生した指摘をまとめても、同じ行にある独立したエラーは残ることを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:separator -->\n"
        '<hr clas="separator"><code badattr="x"><code>\n'
        "<!-- /wp:separator -->\n"
        "<!-- wp:paragraph -->\n"
        "<p><strong>Later error</p>\n"
        "<!-- /wp:paragraph -->"
    )

    assert [(message.line_number, message.message_key) for message in messages] == [
        (2, "html_typo_lint.wordpress_separator_contains_code"),
        (2, "html_typo_lint.unknown_html_attribute"),
        (2, "html_typo_lint.unknown_html_attribute"),
        (5, "html_typo_lint.inline_tag_unclosed_before_parent"),
    ]
    for message, attribute in zip(messages[1:3], ["clas", "badattr"], strict=True):
        assert message.values is not None
        assert message.values["attribute"] == attribute


def test_separator_cascade_keeps_independent_fragile_typo() -> None:
    """区切りの連鎖が独立した壊れやすいの表記ミスを保持することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:separator -->\n"
        '<hr style="margin:2en"><code><code>\n'
        "<!-- /wp:separator -->"
    )

    assert {message.message_key for message in messages} == {
        "html_typo_lint.wordpress_separator_contains_code",
        "css_lint.known_unit_typo",
    }
    assert all(message.line_number == 2 for message in messages)


def test_list_item_missing_close_points_to_next_item() -> None:
    """リスト項目の不足した閉じる操作の位置のへの次の項目を確認する。"""
    messages = lint_html_typos(
        "<!-- wp:list -->\n<ul>\n"
        "<!-- wp:list-item --><li>First</li>\n"
        "<!-- wp:list-item --><li>Second</li><!-- /wp:list-item -->\n"
        "</ul><!-- /wp:list -->"
    )

    assert [
        (message.line_number, message.message_key, message.values)
        for message in messages
    ] == [
        (4, "html_typo_lint.missing_wordpress_closing_block",
         {"block": "list-item", "affected_start": "4", "affected_end": "5"}),
    ]


def test_list_mismatched_close_identifies_repair_comments() -> None:
    """リストの終了部分に不一致があるとき、修正対象のコメントを特定できることを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:list -->\n<ul>\n"
        "<!-- wp:list-item --><li>First</li>\n"
        "</ul><!-- /wp:list -->"
    )

    mismatch = next(
        message for message in messages
        if message.message_key == "html_typo_lint.mismatched_wordpress_block"
    )
    assert mismatch.line_number == 4
    assert mismatch.values == {"open_block": "list-item", "close_block": "list"}


def test_lint_reports_duplicate_wordpress_paragraph_opening() -> None:
    """文法チェックが重複したWordPressの段落の開始を報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p>ただし、制限が強いWordPressでは、埋め込みがうまく残らない場合があります。</p>\n"
        "<!-- /wp:paragraph -->\n"
        "<!-- wp:paragraph -->\n"
        "<p>ただし、制限が強いWordPressでは、埋め込みがうまく残らない時があります。</p>\n"
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key == "html_typo_lint.duplicate_wordpress_paragraph"
        and message.values
        and message.values["previous_line"] == "1"
        for message in messages
    )


def test_lint_counts_only_html_tag_tokens_for_code() -> None:
    """文法チェックがだけのHTMLのタグのトークンの用のコードを数えることを確認する。"""
    messages = lint_html_typos(
        "<!--wp:paragraph-->\n"
        "<p>コード表示は <code>code</code> と書きます。</p>\n"
        "<!--/wp:paragraph-->"
    )

    message_keys = {message.message_key for message in messages}
    assert "html_typo_lint.count_mismatch_code" not in message_keys
    assert "html_typo_lint.count_mismatch_wordpress_paragraph" not in message_keys


def test_lint_counts_ignore_escaped_html_code_examples() -> None:
    """エスケープ済みのHTMLサンプルは診断件数に含めないことを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p>表示例は <code>&lt;code&gt;本文&lt;/code&gt;</code> です。</p>\n"
        "<!-- /wp:paragraph -->"
    )

    assert not any(
        message.message_key == "html_typo_lint.count_mismatch_code"
        for message in messages
    )


def test_lint_wordpress_mismatch_does_not_consume_valid_open_block() -> None:
    """文法チェックのWordPressの不一致の行わないの取り込むの正しいの開く操作のブロックを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p>本文</p>\n"
        "<!-- /wp:html -->\n"
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key == "html_typo_lint.mismatched_wordpress_block"
        and message.line_number == 3
        and message.values == {"open_block": "paragraph", "close_block": "html"}
        for message in messages
    )
    assert not any(
        message.message_key == "html_typo_lint.missing_wordpress_closing_block"
        and message.values
        and message.values.get("block") == "paragraph"
        for message in messages
    )


def test_lint_reports_real_sample_problem_categories() -> None:
    """文法チェックが実際のサンプルの問題の分類を報告することを確認する。"""
    sample_path = Path("sample/test.wp_html")
    if not sample_path.exists():
        return
    sample_text = sample_path.read_text(encoding="utf-8")

    messages = lint_html_typos(sample_text)

    assert not any(
        message.message_key == "html_typo_lint.escaped_code_close_fragment"
        and message.line_number in {299, 319}
        for message in messages
    )
    if "<strong>ブロックの設定情報です。</p>" in sample_text:
        assert any(
            message.message_key == "html_typo_lint.inline_tag_unclosed_before_parent"
            and message.line_number == 501
            and message.values == {"tag": "strong", "parent": "p"}
            for message in messages
        )


def test_lint_reports_test_sample_without_separator_cascade() -> None:
    """区切りの連鎖を省いた場合、文法チェックがテストのサンプルを報告することを確認する。"""
    sample_path = Path("sample/test_sample.wp_html")
    if not sample_path.exists():
        return
    sample_text = sample_path.read_text(encoding="utf-8")

    messages = lint_html_typos(sample_text)

    assert [
        (message.line_number, message.message_key, message.values)
        for message in messages
    ] == [
        (
            31,
            "html_typo_lint.inline_tag_unclosed_before_parent",
            {"tag": "strong", "parent": "p"},
        ),
        (
            35,
            "html_typo_lint.inline_tag_closing_order",
            {"tag": "span", "closing_tag": "strong"},
        ),
        (
            49,
            "html_typo_lint.inline_tag_unclosed_before_parent",
            {"tag": "a", "parent": "p"},
        ),
        (
            81,
            "html_typo_lint.missing_wordpress_closing_block",
            {"block": "list-item", "affected_start": "81", "affected_end": str(sample_text.count("\n") + 1)},
        ),
        (98, "html_typo_lint.escaped_code_close_fragment", None),
        (120, "html_typo_lint.html_crosses_wordpress_boundary",
         {"tag": "div", "block": "html", "boundary_line": "123"}),
        (131, "html_typo_lint.wordpress_separator_contains_code", None),
        (
            148,
            "html_typo_lint.inline_tag_unclosed_before_parent",
            {"tag": "span", "parent": "p"},
        ),
    ]


def test_lint_reports_known_fragile_typos() -> None:
    """文法チェックが既知の壊れやすいの表記ミスを報告することを確認する。"""
    messages = lint_html_typos('<p style="margin:2en 0 1.5em;">本文<\\p>')

    message_keys = {message.message_key for message in messages}
    assert "html_typo_lint.invalid_p_closing_tag" in message_keys
    assert "css_lint.known_unit_typo" in message_keys


def test_inline_style_uses_css_dictionary_lint() -> None:
    """インラインのCSSがCSSの辞書の文法チェックを使うことを確認する。"""
    messages = lint_html_typos(
        '<p style="text-aling:center; display:blick; color:#zzzzzz">本文</p>'
    )
    message_keys = {message.message_key for message in messages}

    assert "css_lint.known_property_typo" in message_keys
    assert "css_lint.invalid_keyword" in message_keys
    assert "css_lint.invalid_color" in message_keys
    assert all(message.line_number == 1 for message in messages)


@pytest.mark.parametrize(
    "source",
    [
        '<div style="{cursor}">本文</div>',
        '<div class="{cursor}">本文</div>',
        '<div style="color:{cursor}" class="{cursor}">本文</div>',
        '<!-- wp:paragraph --><p style="{cursor}" class="{cursor}">本文</p><!-- /wp:paragraph -->',
    ],
)
def test_lint_accepts_cursor_placeholder_in_html_attributes(source: str) -> None:
    """HTML属性内のカーソル位置用プレースホルダーを文法チェックで許容することを確認する。"""
    assert lint_html_typos(source) == []


def test_multiline_inline_style_reports_original_html_line() -> None:
    """複数行のインラインのCSSが元のHTMLの行を報告することを確認する。"""
    messages = lint_html_typos(
        '<p style="color:#333;\n'
        "display:blick;\n"
        'padding:10px">本文</p>'
    )

    invalid_keyword = next(
        message
        for message in messages
        if message.message_key == "css_lint.invalid_keyword"
    )
    assert invalid_keyword.line_number == 2


def test_embedded_stylesheet_uses_css_lint_with_original_line() -> None:
    """組み込みのスタイルシートがCSSの文法チェック（元の行あり）を使うことを確認する。"""
    messages = lint_html_typos(
        "<style>\n"
        ".note {\n"
        "  display:blick;\n"
        "}\n"
        "</style>"
    )

    invalid_keyword = next(
        message
        for message in messages
        if message.message_key == "css_lint.invalid_keyword"
    )
    assert invalid_keyword.line_number == 3


def test_valid_inline_style_does_not_add_css_messages() -> None:
    """正しいのインラインのCSSがCSSのメッセージを追加しないことを確認する。"""
    messages = lint_html_typos(
        '<p style="color:#333; padding:10px; margin:1em auto">本文</p>'
    )

    assert not any(message.message_key.startswith("css_lint.") for message in messages)


def test_lint_reports_html_block_inside_wordpress_paragraph_block() -> None:
    """文法チェックがHTMLのブロック内のWordPressの段落ブロックを報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p>前半\n"
        "<!-- wp:html -->\n"
        "<div>入れ子HTML</div>\n"
        "<!-- /wp:html -->\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key
        == "html_typo_lint.wordpress_paragraph_contains_html_block"
        and message.line_number == 3
        for message in messages
    )


def test_lint_guides_decorated_preformatted_block_to_custom_html() -> None:
    """文法チェックが装飾付きの整形済みのブロックのへのカスタムHTMLへ案内することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:preformatted -->\n"
        '<pre class="wp-block-preformatted" '
        'style="background:#f9f9f9; padding:16px;">Prompt</pre>\n'
        "<!-- /wp:preformatted -->"
    )

    assert any(
        message.message_key
        == "html_typo_lint.wordpress_decorated_block_should_use_html"
        and message.line_number == 2
        and message.values == {"block": "preformatted"}
        for message in messages
    )


def test_lint_does_not_reject_group_style_json_as_custom_html() -> None:
    """グループブロックのstyle用JSONをカスタムHTMLの誤りとして扱わないことを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:group {"style":{"color":{"background":"#f6f6f6"}}} -->\n'
        '<div class="wp-block-group"><p>Note</p></div>\n'
        "<!-- /wp:group -->"
    )

    assert not any(
        message.message_key == "html_typo_lint.wordpress_decorated_block_should_use_html"
        for message in messages
    )


def test_lint_accepts_plain_preformatted_and_group_blocks() -> None:
    """文法チェックがプレーンテキストの整形済みのとグループのブロックを受け入れることを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:preformatted -->\n"
        '<pre class="wp-block-preformatted">Prompt</pre>\n'
        "<!-- /wp:preformatted -->\n"
        "<!-- wp:group -->\n"
        '<div class="wp-block-group"><p>Note</p></div>\n'
        "<!-- /wp:group -->"
    )

    assert not any(
        message.message_key
        == "html_typo_lint.wordpress_decorated_block_should_use_html"
        for message in messages
    )


def test_lint_reports_invalid_wordpress_block_attributes() -> None:
    """文法チェックが不正なWordPressのブロックの属性を報告することを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:spacer {"height":"32px",} -->\n'
        '<div style="height:32px" aria-hidden="true" class="wp-block-spacer"></div>\n'
        "<!-- /wp:spacer -->"
    )

    assert any(
        message.message_key == "html_typo_lint.invalid_wordpress_block_attributes"
        for message in messages
    )


def test_lint_rejects_non_object_wordpress_block_attributes() -> None:
    """文法チェックが非のオブジェクトのWordPressのブロックの属性を拒否することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph [1, 2] -->\n"
        "<p>Body</p>\n"
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key == "html_typo_lint.invalid_wordpress_block_attributes"
        and message.line_number == 1
        for message in messages
    )


def test_lint_suppresses_attribute_html_mismatch_when_block_json_is_invalid() -> None:
    """ブロックのJSONが不正なになるの場合、文法チェックが属性のHTMLの不一致を抑えることを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:heading {level:3} -->\n"
        '<h3 class="wp-block-heading">Heading</h3>\n'
        "<!-- /wp:heading -->"
    )
    message_keys = [message.message_key for message in messages]

    assert "html_typo_lint.invalid_wordpress_block_attributes" in message_keys
    assert "html_typo_lint.wordpress_block_attribute_html_mismatch" not in message_keys


def test_lint_reports_unknown_wordpress_block_attribute() -> None:
    """文法チェックが未登録のWordPressのブロックの属性を報告することを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:heading {"level":3,"badParam":true} -->\n'
        '<h3 class="wp-block-heading">見出し</h3>\n'
        "<!-- /wp:heading -->"
    )

    assert any(
        message.message_key == "html_typo_lint.unknown_wordpress_block_attribute"
        and message.line_number == 1
        and message.values == {"block": "heading", "attribute": "badParam"}
        for message in messages
    )


def test_lint_suggests_unknown_wordpress_block_attribute_typo() -> None:
    """未知のWordPressブロック属性に対して、入力ミスの修正候補を示すことを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:heading {"lebel":3} -->\n'
        '<h3 class="wp-block-heading">Heading</h3>\n'
        "<!-- /wp:heading -->"
    )

    assert any(
        message.message_key == "html_typo_lint.unknown_wordpress_block_attribute"
        and message.values
        and message.values.get("attribute") == "lebel"
        and message.values.get("suggestion") == "level"
        for message in messages
    )


def test_lint_accepts_known_wordpress_block_attributes() -> None:
    """文法チェックが既知のWordPressのブロックの属性を受け入れることを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:spacer {"height":"32px","className":"wide"} -->\n'
        '<div style="height:32px" aria-hidden="true" class="wp-block-spacer wide"></div>\n'
        "<!-- /wp:spacer -->"
    )

    assert not any(
        message.message_key == "html_typo_lint.unknown_wordpress_block_attribute"
        for message in messages
    )


def test_lint_accepts_reference_wordpress_block_attributes() -> None:
    """文法チェックが参照資料のWordPressのブロックの属性を受け入れることを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:post-title {"level":3,"isLink":true,"linkTarget":"_blank"} -->\n'
        '<h3 class="wp-block-post-title"><a href="/sample" target="_blank">Title</a></h3>\n'
        "<!-- /wp:post-title -->"
    )

    rejected_keys = {
        "html_typo_lint.unknown_wordpress_block",
        "html_typo_lint.unknown_wordpress_block_attribute",
    }
    assert not any(message.message_key in rejected_keys for message in messages)


def test_lint_accepts_wordpress_image_generated_html_attributes() -> None:
    """文法チェックがWordPressの画像の生成されたHTMLの属性を受け入れることを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:image {"sizeSlug":"large","linkDestination":"none"} -->\n'
        '<figure class="wp-block-image size-large">'
        '<img src="sample.jpg" alt="Sample" decoding="async" fetchpriority="high" '
        'srcset="sample.jpg 800w" sizes="(max-width: 800px) 100vw, 800px"/>'
        "</figure>\n"
        "<!-- /wp:image -->"
    )

    assert not any(
        message.message_key == "html_typo_lint.unknown_html_attribute"
        for message in messages
    )


def test_lint_reports_unknown_reference_wordpress_block_attribute() -> None:
    """文法チェックが未登録の参照資料のWordPressのブロックの属性を報告することを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:post-title {"level":3,"badParam":true} -->\n'
        '<h3 class="wp-block-post-title">Title</h3>\n'
        "<!-- /wp:post-title -->"
    )

    assert any(
        message.message_key == "html_typo_lint.unknown_wordpress_block_attribute"
        and message.values == {"block": "post-title", "attribute": "badParam"}
        for message in messages
    )


def test_lint_reports_wordpress_block_attribute_type_mismatch() -> None:
    """文法チェックがWordPressのブロックの属性の型の不一致を報告することを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:heading {"level":"3"} -->\n'
        '<h3 class="wp-block-heading">Heading</h3>\n'
        "<!-- /wp:heading -->\n"
        '<!-- wp:paragraph {"dropCap":"true"} -->\n'
        "<p>Drop cap text.</p>\n"
        "<!-- /wp:paragraph -->"
    )

    type_messages = [
        message
        for message in messages
        if message.message_key
        == "html_typo_lint.invalid_wordpress_block_attribute_type"
    ]
    assert {
        (
            message.values.get("block") if message.values else "",
            message.values.get("attribute") if message.values else "",
            message.values.get("expected_type") if message.values else "",
            message.values.get("actual_value") if message.values else "",
        )
        for message in type_messages
    } == {
        ("heading", "level", "integer", '"3"'),
        ("paragraph", "dropCap", "boolean", '"true"'),
    }


def test_lint_reports_wordpress_block_attribute_invalid_value() -> None:
    """文法チェックがWordPressのブロックの属性の不正な値を報告することを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:paragraph {"align":"centre"} -->\n'
        "<p>Aligned text.</p>\n"
        "<!-- /wp:paragraph -->"
    )

    assert any(
        message.message_key
        == "html_typo_lint.invalid_wordpress_block_attribute_value"
        and message.values
        and message.values.get("block") == "paragraph"
        and message.values.get("attribute") == "align"
        and message.values.get("actual_value") == '"centre"'
        and message.values.get("suggestion") == "center"
        for message in messages
    )


def test_lint_recovers_wordpress_block_structure_after_invalid_json() -> None:
    """文法チェックの復旧するのWordPressのブロックの構造後の不正なJSONを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:heading {"level":3}XYZ -->\n'
        '<h3 class="wp-block-heading">Heading</h3>\n'
        "<!-- /wp:heading -->"
    )
    message_keys = [message.message_key for message in messages]

    assert "html_typo_lint.invalid_wordpress_block_attributes" in message_keys
    assert "html_typo_lint.unexpected_wordpress_closing_block" not in message_keys
    assert "html_typo_lint.missing_wordpress_closing_block" not in message_keys


def test_lint_reports_unclosed_div_inside_wordpress_html_block() -> None:
    """文法チェックが閉じられていないのdiv内のWordPressのHTMLのブロックを報告することを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:html -->\n"
        '<div class="notice">\n'
        "本文<br>\n"
        "<!-- /wp:html -->"
    )

    assert any(
        message.message_key == "html_typo_lint.html_crosses_wordpress_boundary"
        and message.line_number == 2
        and message.values == {"tag": "div", "block": "html", "boundary_line": "4"}
        for message in messages
    )


def test_lint_checks_entire_plain_html_file_structure() -> None:
    """文法チェックが全体のプレーンテキストのHTMLのファイルの構造を検査することを確認する。"""
    messages = lint_html_typos(
        '<main><div class="notice">\n'
        "<p>本文</p>\n"
        "</main>"
    )

    assert any(
        message.message_key == "html_typo_lint.mismatched_html_tag"
        and message.line_number == 3
        and message.values == {"open_tag": "div", "close_tag": "main"}
        for message in messages
    )


def test_lint_reports_wordpress_heading_level_html_mismatch() -> None:
    """文法チェックがWordPressの見出しレベルのHTMLの不一致を報告することを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:heading {"level":3} -->\n'
        '<h2 class="wp-block-heading">見出し</h2>\n'
        "<!-- /wp:heading -->"
    )

    mismatch = next(
        message
        for message in messages
        if message.message_key
        == "html_typo_lint.wordpress_block_attribute_html_mismatch"
    )
    assert mismatch.values == {
        "block": "heading",
        "attribute": "level",
        "attribute_value": "3",
        "html_value": "h2",
    }


def test_lint_reports_wordpress_spacer_height_html_mismatch() -> None:
    """文法チェックがWordPressのスペーサーの高さのHTMLの不一致を報告することを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:spacer {"height":"64px"} -->\n'
        '<div style="height:32px" aria-hidden="true" class="wp-block-spacer"></div>\n'
        "<!-- /wp:spacer -->"
    )

    assert any(
        message.message_key
        == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        and message.values
        and message.values["block"] == "spacer"
        for message in messages
    )


def test_lint_reports_wordpress_image_size_html_mismatch() -> None:
    """文法チェックがWordPressの画像のサイズのHTMLの不一致を報告することを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:image {"sizeSlug":"large","linkDestination":"none"} -->\n'
        '<figure class="wp-block-image size-full"><img src="sample.jpg" alt="説明"/></figure>\n'
        "<!-- /wp:image -->"
    )

    assert any(
        message.message_key
        == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        and message.values
        and message.values["block"] == "image"
        for message in messages
    )


def test_lint_accepts_matching_wordpress_comment_attributes_and_html() -> None:
    """文法チェックが一致するのWordPressのコメントの属性とHTMLを受け入れることを確認する。"""
    messages = lint_html_typos(
        '<!-- wp:heading {"level":3} -->\n'
        '<h3 class="wp-block-heading">見出し</h3>\n'
        "<!-- /wp:heading -->\n"
        '<!-- wp:spacer {"height":"32px"} -->\n'
        '<div style="height:32px" aria-hidden="true" class="wp-block-spacer"></div>\n'
        "<!-- /wp:spacer -->\n"
        '<!-- wp:image {"sizeSlug":"full","linkDestination":"none"} -->\n'
        '<figure class="wp-block-image size-full"><img src="sample.jpg" alt="説明"/></figure>\n'
        "<!-- /wp:image -->"
    )

    assert not any(
        message.message_key
        == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        for message in messages
    )


def test_lint_accepts_wordpress_accordion_blocks() -> None:
    """文法チェックがWordPressのアコーディオンのブロックを受け入れることを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:accordion -->\n"
        '<div role="group" class="wp-block-accordion"><!-- wp:accordion-item -->\n'
        '<div class="wp-block-accordion-item"><!-- wp:accordion-heading -->\n'
        '<h3 class="wp-block-accordion-heading has-icon has-icon-right">'
        '<button type="button" class="wp-block-accordion-heading__toggle">'
        '<span class="wp-block-accordion-heading__toggle-title">'
        "Google検索の便利な使い方"
        "</span>"
        '<span class="wp-block-accordion-heading__toggle-icon" aria-hidden="true">'
        "+"
        "</span>"
        "</button></h3>\n"
        "<!-- /wp:accordion-heading -->\n"
        "\n"
        "<!-- wp:accordion-panel -->\n"
        '<div role="region" class="wp-block-accordion-panel"><!-- wp:paragraph -->\n'
        "<p></p>\n"
        "<!-- /wp:paragraph --></div>\n"
        "<!-- /wp:accordion-panel --></div>\n"
        "<!-- /wp:accordion-item --></div>\n"
        "<!-- /wp:accordion -->"
    )

    rejected_keys = {
        "html_typo_lint.unknown_wordpress_block",
        "html_typo_lint.unknown_html_attribute",
        "html_typo_lint.restricted_html_tag",
    }
    assert not any(message.message_key in rejected_keys for message in messages)


def test_lint_accepts_valid_wordpress_paragraph_blocks() -> None:
    """文法チェックが正しいのWordPressの段落のブロックを受け入れることを確認する。"""
    messages = lint_html_typos(
        "<!-- wp:paragraph -->\n"
        "<p>1つ目の段落です。</p>\n"
        "<!-- /wp:paragraph -->\n"
        "<!-- wp:paragraph -->\n"
        "<p>2つ目の段落です。</p>\n"
        "<!-- /wp:paragraph -->"
    )

    structural_keys = {
        "html_typo_lint.wordpress_paragraph_missing_p_open",
        "html_typo_lint.wordpress_paragraph_missing_p_close",
        "html_typo_lint.unexpected_wordpress_closing_block",
        "html_typo_lint.mismatched_wordpress_block",
        "html_typo_lint.missing_wordpress_closing_block",
        "html_typo_lint.missing_wordpress_html_closing_block",
        "html_typo_lint.wordpress_html_contains_block_comment",
        "html_typo_lint.wordpress_paragraph_contains_div",
    }
    assert not any(message.message_key in structural_keys for message in messages)


def test_lint_accepts_reference_json_attribute_prefixes() -> None:
    """文法チェックが参照資料のJSONの属性の接頭辞を受け入れることを確認する。"""
    messages = lint_html_typos('<p data-note-id="1" aria-label="説明">本文</p>')

    assert not any(message.message_key == "html_typo_lint.unknown_html_attribute" for message in messages)


def test_lint_reports_unexpected_html_attribute_for_tag() -> None:
    """文法チェックが想定外のHTMLの属性の用のタグを報告することを確認する。"""
    messages = lint_html_typos('<p href="https://example.com">Body</p>')

    assert any(
        message.message_key == "html_typo_lint.unexpected_html_attribute_for_tag"
        and message.values == {"tag": "p", "attribute": "href"}
        for message in messages
    )


def test_lint_accepts_global_and_prefixed_attributes_on_tag_specific_checks() -> None:
    """タグごとの検査でもグローバル属性と接頭辞付き属性を許容することを確認する。"""
    messages = lint_html_typos(
        '<p id="intro" class="lead" data-note-id="1" aria-label="Intro">Body</p>'
    )

    assert not any(
        message.message_key == "html_typo_lint.unexpected_html_attribute_for_tag"
        for message in messages
    )


def test_lint_reports_tag_specific_html_attribute_typo_suggestion() -> None:
    """タグ固有のHTML属性の綴り間違いに対して候補を提示することを確認する。"""
    messages = lint_html_typos('<img scrset="sample.jpg 800w" alt="Sample">')

    assert any(
        message.message_key == "html_typo_lint.unknown_html_attribute"
        and message.values
        and message.values.get("attribute") == "scrset"
        and message.values.get("suggestion") == "srcset"
        for message in messages
    )


def test_lint_uses_startup_reference_cache_without_rereading_json() -> None:
    """読み直しのJSONを省いた場合、文法チェックが起動時の参照資料のキャッシュを使うことを確認する。"""
    with patch("pathlib.Path.read_text") as read_text:
        messages = lint_html_typos('<p clas="lead">本文</p>')

    read_text.assert_not_called()
    assert any(
        message.message_key == "html_typo_lint.unknown_html_attribute"
        and message.values
        and message.values.get("suggestion") == "class"
        for message in messages
    )


def test_lint_warns_about_restricted_html_tags_and_event_attributes() -> None:
    """文法チェックが制限されたHTMLのタグとイベントの属性を警告することを確認する。"""
    messages = lint_html_typos(
        '<script>alert("x")</script>\n'
        '<iframe src="https://example.com"></iframe>\n'
        '<button type="button" onclick="alert(1)">押す</button>'
    )
    message_keys = [message.message_key for message in messages]

    assert message_keys.count("html_typo_lint.restricted_html_tag") >= 3
    assert "html_typo_lint.restricted_html_attribute" in message_keys


def test_lint_accepts_verified_wordpress_table_classes_with_character_references() -> None:
    """文法チェックが確認済みののWordPressの表のクラス（文字の参照資料あり）を受け入れることを確認する。"""
    source = (
        '<figure class="wp-block-table"><table class="&#x9;has-base-color&#x20;'
        'has-text-color&#x20;has-background&#x20;has-link-color&#x20;'
        'has-fixed-layout"><tbody><tr><td>内容</td></tr></tbody></table></figure>'
    )

    messages = lint_html_typos(source)

    assert not any(
        message.message_key == "html_typo_lint.wordpress_class_tag_mismatch"
        for message in messages
    )


def test_lint_reports_only_strict_wordpress_class_tag_mismatch() -> None:
    """文法チェックがだけの厳格なWordPressのクラスのタグの不一致を報告することを確認する。"""
    messages = lint_html_typos(
        '<div class="has-fixed-layout has-background custom-class">内容</div>'
    )

    mismatch_messages = [
        message
        for message in messages
        if message.message_key == "html_typo_lint.wordpress_class_tag_mismatch"
    ]
    assert len(mismatch_messages) == 1
    assert mismatch_messages[0].values == {
        "class_name": "has-fixed-layout",
        "tag": "div",
        "allowed_tags": "<table>",
    }


def test_lint_accepts_verified_flex_nowrap_group_block() -> None:
    """文法チェックが確認済みのFlexboxの折り返さない指定のグループのブロックを受け入れることを確認する。"""
    source = (Path(__file__).parent / "group_block_flex_nowrap_correct.wp_html").read_text(
        encoding="utf-8"
    )

    assert lint_html_typos(source) == []


def test_lint_accepts_verified_decorated_group_block() -> None:
    """文法チェックが確認済みの装飾付きのグループのブロックを受け入れることを確認する。"""
    source = (Path(__file__).parent / "group_block_decorated_correct.wp_html").read_text(
        encoding="utf-8"
    )

    assert lint_html_typos(source) == []


def test_lint_accepts_verified_decorated_paragraph_block() -> None:
    """文法チェックが確認済みの装飾付きの段落ブロックを受け入れることを確認する。"""
    source = (
        Path(__file__).parent / "paragraph_block_decorated_correct.wp_html"
    ).read_text(encoding="utf-8")

    assert lint_html_typos(source) == []


def test_lint_reports_verified_paragraph_fit_text_and_weight_mismatches() -> None:
    """文法チェックが確認済みの段落の文字幅に合わせる設定と太さの不一致を報告することを確認する。"""
    source = (
        Path(__file__).parent / "paragraph_block_decorated_correct.wp_html"
    ).read_text(encoding="utf-8")
    broken_source = source.replace("has-fit-text ", "", 1).replace(
        "font-weight:700",
        "font-weight:400",
        1,
    )

    mismatch_attributes = {
        message.values.get("attribute")
        for message in lint_html_typos(broken_source)
        if message.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        and message.values
    }

    assert "fitText" in mismatch_attributes
    assert "style.typography.fontWeight" in mismatch_attributes


def test_lint_accepts_verified_decorated_button_block() -> None:
    """文法チェックが確認済みの装飾付きのボタンのブロックを受け入れることを確認する。"""
    source = (Path(__file__).parent / "button_block_decorated_correct.wp_html").read_text(
        encoding="utf-8"
    )

    assert lint_html_typos(source) == []


@pytest.mark.parametrize(
    "fixture_name",
    [
        "quote_block_decorated_correct.wp_html",
        "pullquote_block_decorated_correct.wp_html",
    ],
)
def test_lint_accepts_verified_decorated_quote_blocks(fixture_name: str) -> None:
    """文法チェックが確認済みの装飾付きの引用符のブロックを受け入れることを確認する。"""
    source = (Path(__file__).parent / fixture_name).read_text(encoding="utf-8")

    assert lint_html_typos(source) == []


@pytest.mark.parametrize(
    "fixture_name",
    [
        "accordion_block_background_font_correct.wp_html",
        "accordion_block_border_correct.wp_html",
    ],
)
def test_lint_accepts_verified_decorated_accordion_blocks(fixture_name: str) -> None:
    """文法チェックが確認済みの装飾付きのアコーディオンのブロックを受け入れることを確認する。"""
    source = (Path(__file__).parent / fixture_name).read_text(encoding="utf-8")

    assert lint_html_typos(source) == []


def test_lint_accepts_verified_columns_block_with_mixed_content() -> None:
    """文法チェックが確認済みのの列のブロック（混在するの内容あり）を受け入れることを確認する。"""
    source = (
        Path(__file__).parent / "columns_block_mixed_content_correct.wp_html"
    ).read_text(encoding="utf-8")

    assert lint_html_typos(source) == []


def test_lint_reports_verified_columns_root_class_mismatch() -> None:
    """文法チェックが確認済みの列のルート要素のクラスの不一致を報告することを確認する。"""
    source = (
        Path(__file__).parent / "columns_block_mixed_content_correct.wp_html"
    ).read_text(encoding="utf-8")
    broken_source = source.replace('class="wp-block-columns"', 'class="columns"', 1)

    assert any(
        message.message_key
        == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        and message.values
        and message.values.get("attribute") == "class"
        for message in lint_html_typos(broken_source)
    )


def test_lint_reports_columns_class_on_wrong_html_tag() -> None:
    """文法チェックが列のクラスでの誤ったのHTMLのタグを報告することを確認する。"""
    messages = lint_html_typos('<section class="wp-block-columns"></section>')

    assert any(
        message.message_key == "html_typo_lint.wordpress_class_tag_mismatch"
        and message.values
        and message.values.get("class_name") == "wp-block-columns"
        for message in messages
    )


def test_lint_reports_verified_accordion_heading_class_mismatch() -> None:
    """文法チェックが確認済みのアコーディオンの見出しのクラスの不一致を報告することを確認する。"""
    source = (
        Path(__file__).parent / "accordion_block_background_font_correct.wp_html"
    ).read_text(encoding="utf-8")
    broken_source = source.replace(" has-large-font-size", "", 1)

    mismatch_attributes = {
        message.values.get("attribute")
        for message in lint_html_typos(broken_source)
        if message.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        and message.values
    }

    assert "fontSize" in mismatch_attributes


def test_lint_reports_verified_accordion_heading_border_mismatch() -> None:
    """文法チェックが確認済みのアコーディオンの見出しの境界線の不一致を報告することを確認する。"""
    source = (Path(__file__).parent / "accordion_block_border_correct.wp_html").read_text(
        encoding="utf-8"
    )
    broken_source = source.replace("border-width:1px", "border-width:2px", 1)

    assert any(
        message.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        and message.values
        and message.values.get("attribute") == "style.border.width"
        for message in lint_html_typos(broken_source)
    )


def test_lint_reports_verified_quote_class_and_style_mismatches() -> None:
    """文法チェックが確認済みの引用符のクラスとスタイルの不一致を報告することを確認する。"""
    source = (Path(__file__).parent / "quote_block_decorated_correct.wp_html").read_text(
        encoding="utf-8"
    )
    broken_source = source.replace(" has-background", "", 1).replace(
        "border-left-width:4px",
        "border-left-width:2px",
        1,
    )

    mismatch_attributes = {
        message.values.get("attribute")
        for message in lint_html_typos(broken_source)
        if message.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        and message.values
    }

    assert "backgroundColor" not in mismatch_attributes
    assert "style.border.left.width" in mismatch_attributes


def test_lint_reports_verified_pullquote_class_and_style_mismatches() -> None:
    """文法チェックが確認済みの抜粋引用のクラスとスタイルの不一致を報告することを確認する。"""
    source = (
        Path(__file__).parent / "pullquote_block_decorated_correct.wp_html"
    ).read_text(encoding="utf-8")
    broken_source = source.replace(" has-background", "", 1).replace(
        "border-width:2px",
        "border-width:1px",
        1,
    )

    mismatch_attributes = {
        message.values.get("attribute")
        for message in lint_html_typos(broken_source)
        if message.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        and message.values
    }

    assert "backgroundColor" not in mismatch_attributes
    assert "style.border.width" in mismatch_attributes


def test_lint_reports_verified_button_link_class_and_style_mismatches() -> None:
    """文法チェックが確認済みのボタンのリンクのクラスとスタイルの不一致を報告することを確認する。"""
    source = (Path(__file__).parent / "button_block_decorated_correct.wp_html").read_text(
        encoding="utf-8"
    )
    broken_source = source.replace(" has-background", "", 1).replace(
        "border-width:4px",
        "border-width:2px",
        1,
    )

    mismatch_attributes = {
        message.values.get("attribute")
        for message in lint_html_typos(broken_source)
        if message.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        and message.values
    }

    assert "backgroundColor" not in mismatch_attributes
    assert "style.border.width" in mismatch_attributes


def test_lint_reports_verified_group_class_and_style_mismatches() -> None:
    """文法チェックが確認済みのグループのクラスとスタイルの不一致を報告することを確認する。"""
    source = (Path(__file__).parent / "group_block_decorated_correct.wp_html").read_text(
        encoding="utf-8"
    )
    broken_source = source.replace(" has-background", "", 1).replace(
        "margin-top:var(--wp--preset--spacing--20)",
        "margin-top:10px",
        1,
    )

    mismatch_attributes = {
        message.values.get("attribute")
        for message in lint_html_typos(broken_source)
        if message.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch"
        and message.values
    }

    assert "backgroundColor" not in mismatch_attributes
    assert "style.spacing.margin.top" in mismatch_attributes


def test_lint_reports_empty_root_style_in_verified_flex_nowrap_group_block() -> None:
    """文法チェックが空のルート要素のスタイル内の確認済みのFlexboxの折り返さない指定のグループのブロックを報告することを確認する。"""
    correct_source = (
        Path(__file__).parent / "group_block_flex_nowrap_correct.wp_html"
    ).read_text(encoding="utf-8")
    broken_source = (
        Path(__file__).parent / "group_block_flex_nowrap_empty_style_broken.wp_html"
    ).read_text(encoding="utf-8")

    correct_keys = {message.message_key for message in lint_html_typos(correct_source)}
    broken_messages = lint_html_typos(broken_source)

    assert "html_typo_lint.wordpress_group_empty_root_style" not in correct_keys
    assert any(
        message.severity == "error"
        and message.message_key == "html_typo_lint.wordpress_group_empty_root_style"
        and message.line_number == 1
        for message in broken_messages
    )


def test_lint_registers_group_layout_as_an_object_attribute() -> None:
    """グループブロックのlayout属性がオブジェクト型として登録されていることを確認する。"""
    source = (
        '<!-- wp:group {"layout":"flex"} -->\n'
        '<div class="wp-block-group"></div>\n'
        '<!-- /wp:group -->'
    )

    messages = lint_html_typos(source)

    assert any(
        message.message_key == "html_typo_lint.invalid_wordpress_block_attribute_type"
        and message.values
        and message.values.get("block") == "group"
        and message.values.get("attribute") == "layout"
        and message.values.get("expected_type") == "object"
        for message in messages
    )
