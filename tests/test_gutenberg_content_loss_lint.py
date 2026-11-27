"""Gutenbergの内容の消失の文法チェックを検証する。"""

from __future__ import annotations

from pathlib import Path

import pytest

from localization.translator import Translator
from search.html_typo_lint import lint_html_typos

CASES = Path(__file__).parent / "fixtures/linter_cases"


@pytest.mark.parametrize(("name", "key", "line"), [
    ("wrong_heading", "wordpress_block_html_shape", 2),
    ("missing_close", "missing_wordpress_closing_block", 3),
    ("orphan_close", "unexpected_wordpress_closing_block", 1),
    ("non_container_child", "invalid_wordpress_child", 3),
])
def test_content_loss_fixtures(name: str, key: str, line: int) -> None:
    """内容の消失の検証用の例を確認する。"""
    directory = CASES / f"gutenberg_{name}"
    source = (directory / "broken.wp_html").read_text(encoding="utf-8")
    original = source
    findings = lint_html_typos(source)
    assert source == original
    finding = next(item for item in findings if item.message_key == f"html_typo_lint.{key}")
    assert (finding.severity, finding.line_number) == ("error", line)
    for variant in ("fixed", "control"):
        assert not lint_html_typos((directory / f"{variant}.wp_html").read_text(encoding="utf-8"))


@pytest.mark.parametrize("variant", ["broken", "fixed", "control"])
def test_normalization_is_not_a_source_error(variant: str) -> None:
    """正規化がしないの原文のエラーになることを確認する。"""
    source = (CASES / "gutenberg_richtext_whitespace" / f"{variant}.wp_html").read_text(encoding="utf-8")
    assert not lint_html_typos(source)


def test_nested_html_is_only_a_portability_warning() -> None:
    """入れ子のHTMLがだけの移植性の警告になることを確認する。"""
    directory = CASES / "gutenberg_nested_html"
    messages = lint_html_typos((directory / "broken.wp_html").read_text(encoding="utf-8"))
    assert [(m.severity, m.message_key) for m in messages] == [
        ("warning", "html_typo_lint.wordpress_html_contains_block_comment"),
    ]
    for variant in ("fixed", "control"):
        assert not lint_html_typos((directory / f"{variant}.wp_html").read_text(encoding="utf-8"))


@pytest.mark.parametrize("parent,body", [
    ("paragraph", "<p>PARENT</p>"),
    ("heading", '<h2 class="wp-block-heading">PARENT</h2>'),
    ("separator", '<hr class="wp-block-separator">'),
    ("spacer", '<div class="wp-block-spacer" style="height:32px" aria-hidden="true"></div>'),
    ("image", '<figure class="wp-block-image"><img src="x.jpg" alt=""></figure>'),
])
@pytest.mark.parametrize("child", ["<!-- wp:paragraph --><p>KEEP</p><!-- /wp:paragraph -->", "<!-- wp:separator /-->"])
def test_non_container_core_children(parent: str, body: str, child: str) -> None:
    """非のコンテナのコアの子要素を確認する。"""
    messages = lint_html_typos(f"<!-- wp:{parent} -->{body}{child}<!-- /wp:{parent} -->")
    assert any(m.severity == "error" and m.message_key == "html_typo_lint.invalid_wordpress_child" for m in messages)


def test_missing_close_has_repair_line_and_conservative_affected_range() -> None:
    """不足した閉じる操作が修復の行と慎重な影響を受けたの範囲を持つことを確認する。"""
    source = "<!-- wp:paragraph -->\n<p>FIRST</p>\n<!-- wp:heading -->\n<h2>KEEP</h2>\n<!-- /wp:heading -->"
    message = next(m for m in lint_html_typos(source) if m.message_key == "html_typo_lint.missing_wordpress_closing_block")
    assert message.line_number == 1
    assert message.values and message.values["affected_start"] == "3" and message.values["affected_end"] == "5"
    assert any(m.message_key == "html_typo_lint.invalid_wordpress_child" for m in lint_html_typos(source))


@pytest.mark.parametrize("separator", ["", "\n", "\r\n  "])
def test_crossed_wordpress_closers_with_balanced_counts(separator: str) -> None:
    """開始と終了の件数がそろっていても、WordPressの終了コメントの順序が交差すると検出できることを確認する。"""
    source = separator.join(["<!-- wp:group -->", '<div class="wp-block-group">', "<!-- wp:paragraph -->", "<p>KEEP</p>", "<!-- /wp:group -->", "<!-- /wp:paragraph -->"])
    mismatch = next(m for m in lint_html_typos(source) if m.message_key == "html_typo_lint.mismatched_wordpress_block")
    assert mismatch.severity == "error"
    assert mismatch.values == {"open_block": "paragraph", "close_block": "group"}


def test_html_crossing_sibling_block_boundary_is_an_error() -> None:
    """HTML要素が同階層のブロックの境界をまたぐ場合にエラーを報告することを確認する。"""
    directory = CASES / "gutenberg_cross_boundary"
    source = (directory / "broken.wp_html").read_text(encoding="utf-8")
    crossings = [m for m in lint_html_typos(source) if m.message_key == "html_typo_lint.html_crosses_wordpress_boundary"]
    assert len(crossings) == 1
    assert (crossings[0].severity, crossings[0].line_number) == ("error", 2)
    assert crossings[0].values and crossings[0].values["boundary_line"] == "3"
    for variant in ("fixed", "control"):
        assert not lint_html_typos((directory / f"{variant}.wp_html").read_text(encoding="utf-8"))


def test_container_html_surrounding_children_is_valid() -> None:
    """コンテナのHTMLの周囲の子要素が正しいになることを確認する。"""
    source = '<!-- wp:group --><div class="wp-block-group">\n<!-- wp:paragraph --><p>KEEP <strong>TEXT</strong></p><!-- /wp:paragraph -->\n</div><!-- /wp:group -->'
    assert not lint_html_typos(source)


@pytest.mark.parametrize("block,html", [("heading", "<div>KEEP</div>"), ("paragraph", "<div>KEEP</div>"), ("list", "<div>KEEP</div>")])
def test_wrong_shapes_point_to_actual_html(block: str, html: str) -> None:
    """誤ったの形の点のへの実際のHTMLを確認する。"""
    messages = lint_html_typos(f"<!-- wp:{block} -->\n\n{html}\n<!-- /wp:{block} -->")
    shape = next(m for m in messages if m.message_key == "html_typo_lint.wordpress_block_html_shape")
    assert (shape.severity, shape.line_number) == ("error", 3)
    assert all(m.line_number == 3 for m in messages if m.severity == "error")


def test_root_cause_suppression_retains_independent_css_problem() -> None:
    """同じ原因から派生した診断を抑制しても、独立したCSSの問題は報告されることを確認する。"""
    source = '<!-- wp:paragraph -->\n<p style="color:;">FIRST</p>\n<!-- wp:heading --><h2>KEEP</h2><!-- /wp:heading -->\n<!-- /wp:paragraph -->'
    messages = lint_html_typos(source)
    assert any(m.message_key == "html_typo_lint.invalid_wordpress_child" for m in messages)
    assert not any(m.message_key == "html_typo_lint.wordpress_block_html_shape" for m in messages)
    assert any(m.message_key.startswith("css_lint.") for m in messages)


def test_invalid_json_does_not_produce_attribute_comparison_cascade() -> None:
    """不正なJSONの行わないの出力の属性の比較の連鎖を確認する。"""
    source = '<!-- wp:heading {"level":3,} -->\n<h2 class="wp-block-heading">KEEP</h2>\n<!-- /wp:heading -->'
    messages = lint_html_typos(source)
    assert any(m.message_key == "html_typo_lint.invalid_wordpress_block_attributes" for m in messages)
    assert not any(m.message_key == "html_typo_lint.wordpress_block_attribute_html_mismatch" for m in messages)


def test_unknown_plugin_block_does_not_get_core_shape_or_child_errors() -> None:
    """未登録のプラグインのブロックの行わないの取得のコアの形または子要素のエラーを確認する。"""
    assert not lint_html_typos('<!-- wp:plugin/widget --><div><!-- wp:paragraph --><p>KEEP</p><!-- /wp:paragraph --></div><!-- /wp:plugin/widget -->')


def test_parent_shape_problem_is_independent_of_invalid_child() -> None:
    """親要素の形の問題が独立した不正な子要素になることを確認する。"""
    messages = lint_html_typos('<!-- wp:heading -->\n<div>KEEP_PARENT</div>\n<!-- wp:paragraph --><p>KEEP_CHILD</p><!-- /wp:paragraph -->\n<!-- /wp:heading -->')
    keys = {message.message_key for message in messages}
    assert "html_typo_lint.wordpress_block_html_shape" in keys
    assert "html_typo_lint.invalid_wordpress_child" in keys


@pytest.mark.parametrize("self_closing", [False, True])
def test_multiline_json_comments_keep_block_boundaries(self_closing: bool) -> None:
    """複数行のJSONのコメントの保持するのブロックの境界を確認する。"""
    source = '<!-- wp:heading {\n"level":3\n}' + (' /-->' if self_closing else ' -->\n<h3 class="wp-block-heading">KEEP</h3>\n<!-- /wp:heading -->')
    assert not lint_html_typos(source)


def test_multiline_invalid_json_keeps_structure_and_css_checks() -> None:
    """複数行のJSONが不正でも、ブロック構造とCSSの検査が続くことを確認する。"""
    messages = lint_html_typos('<!-- wp:heading {\n"level":3,\n} -->\n<h2 style="color:;">KEEP</h2>\n<!-- /wp:heading -->')
    assert any(m.message_key == "html_typo_lint.invalid_wordpress_block_attributes" for m in messages)
    assert any(m.message_key.startswith("css_lint.") for m in messages)
    assert not any(m.message_key in {"html_typo_lint.wordpress_block_attribute_html_mismatch", "html_typo_lint.unexpected_wordpress_closing_block"} for m in messages)


@pytest.mark.parametrize("block,body", [("list", "<ul><li>KEEP</li></ul>"), ("list-item", "<li>KEEP</li>")])
def test_list_shapes_accept_valid_wrapper_and_parent(block: str, body: str) -> None:
    """リストの形の受理の正しいの外枠と親要素を確認する。"""
    source = f'<!-- wp:{block} -->{body}<!-- /wp:{block} -->'
    if block == "list-item":
        source = f'<!-- wp:list --><ul>{source}</ul><!-- /wp:list -->'
    assert not lint_html_typos(source)


def test_columns_container_remains_valid() -> None:
    """列のコンテナの残るの正しいことを確認する。"""
    assert not lint_html_typos('<!-- wp:columns --><div class="wp-block-columns"><!-- wp:column --><div class="wp-block-column"><!-- wp:paragraph --><p>KEEP</p><!-- /wp:paragraph --></div><!-- /wp:column --></div><!-- /wp:columns -->')


@pytest.mark.parametrize("language", ["ja", "en"])
def test_risk_messages_can_be_formatted(language: str) -> None:
    """危険性のメッセージが整形したが可能であることを確認する。"""
    translator = Translator(Path("resources"), language)
    sources = [(CASES / f"gutenberg_{name}" / "broken.wp_html").read_text(encoding="utf-8") for name in ("wrong_heading", "missing_close", "orphan_close", "non_container_child", "nested_html")]
    for source in sources:
        for message in lint_html_typos(source):
            text = translator.text(message.message_key, **(message.values or {}))
            assert text != message.message_key and "{affected_" not in text
    cross = next(m for m in lint_html_typos('<!-- wp:html --><div>KEEP<!-- /wp:html -->') if m.message_key == 'html_typo_lint.html_crosses_wordpress_boundary')
    assert "boundary_line" not in translator.text(cross.message_key, **(cross.values or {}))
