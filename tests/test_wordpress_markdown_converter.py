"""WordPressのMarkdown変換器を検証する。"""

from __future__ import annotations

import pytest

from editor.wordpress_markdown_converter import (
    WordPressMarkdownConversionError,
    convert_complex_markdown_blocks_to_wordpress_html,
    convert_list_to_wordpress_frame_html,
    convert_markdown_lists_to_wordpress_html,
    convert_markdown_tables_to_wordpress_html,
)


def test_convert_complex_markdown_blocks_converts_table() -> None:
    """変換の複雑なMarkdownがに変換するの表を拒否することを確認する。"""
    result = convert_complex_markdown_blocks_to_wordpress_html(
        "| Purpose | AI |\n"
        "|---|---|\n"
        "| B-roll | **Runway / Veo / Luma** |"
    )

    assert result.startswith("<!-- wp:table -->")
    assert "<th>Purpose</th><th>AI</th>" in result
    assert "<td>B-roll</td><td><strong>Runway / Veo / Luma</strong></td>" in result
    assert result.endswith("<!-- /wp:table -->")


def test_convert_complex_markdown_blocks_accepts_escaped_pipe_text() -> None:
    """変換の複雑なMarkdownがを受け入れるのエスケープされた縦棒の文字列を拒否することを確認する。"""
    result = convert_complex_markdown_blocks_to_wordpress_html(
        r"\| Purpose \| AI \|"
        "\n"
        r"\|---\|---\|"
        "\n"
        r"\| B-roll \| Runway \|"
    )

    assert "<!-- wp:table -->" in result
    assert "<th>Purpose</th><th>AI</th>" in result


def test_convert_markdown_table_keeps_literal_escaped_pipe_in_cell() -> None:
    """変換のMarkdownの表がリテラルのエスケープされた縦棒内のセルを保持することを確認する。"""
    result = convert_markdown_tables_to_wordpress_html(
        "| Tool | Note |\n"
        "|---|---|\n"
        r"| Runway | speed \| quality |"
    )

    assert "<td>Runway</td><td>speed | quality</td>" in result


def test_convert_markdown_table_pads_short_rows_for_stable_columns() -> None:
    """変換のMarkdownの表のを補うの短いの行の用の安定した列を確認する。"""
    result = convert_markdown_tables_to_wordpress_html(
        "| Purpose | AI | Cost |\n"
        "|---|---|---|\n"
        "| B-roll | Runway |"
    )

    assert "<th>Purpose</th><th>AI</th><th>Cost</th>" in result
    assert "<td>B-roll</td><td>Runway</td><td></td>" in result


def test_convert_markdown_tables_converts_only_table_blocks() -> None:
    """変換のMarkdownの表がだけの表のブロックに変換することを確認する。"""
    result = convert_markdown_tables_to_wordpress_html(
        "| Purpose | AI |\n"
        "|---|---|\n"
        "| B-roll | Runway |\n"
        "\n"
        "- Not converted here"
    )

    assert "<!-- wp:table -->" in result
    assert "<!-- wp:list -->" not in result


def test_convert_complex_markdown_blocks_converts_unordered_list() -> None:
    """変換の複雑なMarkdownがに変換するの番号なしのリストを拒否することを確認する。"""
    result = convert_complex_markdown_blocks_to_wordpress_html(
        "- **Runway** for realistic B-roll\n"
        "- `Kling` for short motion clips"
    )

    assert "<!-- wp:list -->" in result
    assert '<ul class="wp-block-list">' in result
    assert "<!-- wp:list-item -->" in result
    assert "<li><strong>Runway</strong> for realistic B-roll</li>" in result
    assert "<li><code>Kling</code> for short motion clips</li>" in result
    assert "<!-- /wp:list -->" in result


def test_convert_markdown_lists_converts_only_list_blocks() -> None:
    """変換のMarkdownのリストがだけのリストのブロックに変換することを確認する。"""
    result = convert_markdown_lists_to_wordpress_html(
        "| Purpose | AI |\n"
        "|---|---|\n"
        "| B-roll | Runway |\n"
        "\n"
        "- Converted here"
    )

    assert "<!-- wp:table -->" not in result
    assert "<!-- wp:list -->" in result
    assert "<li>Converted here</li>" in result


def test_convert_complex_markdown_blocks_converts_ordered_list() -> None:
    """変換の複雑なMarkdownがに変換するの番号付きのリストを拒否することを確認する。"""
    result = convert_complex_markdown_blocks_to_wordpress_html(
        "1. Prepare source\n2. Convert block"
    )

    assert '<!-- wp:list {"ordered":true} -->' in result
    assert '<ol class="wp-block-list">' in result
    assert "<li>Prepare source</li>" in result
    assert "<li>Convert block</li>" in result


def test_convert_complex_markdown_blocks_keeps_table_and_list_blocks() -> None:
    """変換の複雑なMarkdownが保持するの表とリストのブロックを拒否することを確認する。"""
    result = convert_complex_markdown_blocks_to_wordpress_html(
        "| Purpose | AI |\n"
        "|---|---|\n"
        "| B-roll | Runway |\n"
        "\n"
        "- First point\n"
        "- Second point"
    )

    assert "<!-- wp:table -->" in result
    assert "<!-- wp:list -->" in result
    assert result.index("<!-- wp:table -->") < result.index("<!-- wp:list -->")


def test_convert_complex_markdown_blocks_rejects_plain_text() -> None:
    """変換の複雑なMarkdownがを拒否するのプレーンテキストの文字列を拒否することを確認する。"""
    with pytest.raises(WordPressMarkdownConversionError, match="Markdown table or list"):
        convert_complex_markdown_blocks_to_wordpress_html("plain text")


def test_convert_markdown_tables_rejects_list_only_selection() -> None:
    """変換のMarkdownの表がリストだけの選択範囲を拒否することを確認する。"""
    with pytest.raises(WordPressMarkdownConversionError, match="Markdown table"):
        convert_markdown_tables_to_wordpress_html("- list only")


def test_convert_markdown_lists_rejects_table_only_selection() -> None:
    """変換のMarkdownのリストが表だけの選択範囲を拒否することを確認する。"""
    with pytest.raises(WordPressMarkdownConversionError, match="Markdown list"):
        convert_markdown_lists_to_wordpress_html("| A | B |\n|---|---|\n| 1 | 2 |")


def test_convert_markdown_list_to_marker_safe_frame() -> None:
    """Markdownのリストをマーカーに干渉しない枠に変換することを確認する。"""
    result = convert_list_to_wordpress_frame_html(
        "- **重要**な項目\n- `code` の項目",
        alignment="center",
        outer_spacing="2em 0",
        inner_style="border: 1px solid #999; padding: 12px;",
    )

    assert result.count("<!-- wp:html -->") == 1
    assert result.count("<!-- /wp:html -->") == 1
    assert "wp:list" not in result
    assert "<ul" not in result
    assert "<li" not in result
    assert 'text-align: center; margin: 2em 0;' in result
    assert 'style="border: 1px solid #999; padding: 12px;"' in result
    assert "・</span> <strong>重要</strong>な項目" in result
    assert "・</span> <code>code</code> の項目" in result


def test_convert_ordered_wordpress_list_block_to_numbered_frame_rows() -> None:
    """変換の番号付きのWordPressのリストブロックのへの番号付きの枠の行を確認する。"""
    result = convert_list_to_wordpress_frame_html(
        '<!-- wp:list {"ordered":true} -->\n'
        '<ol class="wp-block-list">\n'
        '<!-- wp:list-item --><li>準備</li><!-- /wp:list-item -->\n'
        '<!-- wp:list-item --><li><strong>実行</strong></li><!-- /wp:list-item -->\n'
        "</ol>\n<!-- /wp:list -->"
    )

    assert "wp:list" not in result
    assert "1.</span> 準備" in result
    assert "2.</span> <strong>実行</strong>" in result


def test_convert_list_to_frame_rejects_non_list_selection() -> None:
    """変換のリストのへの枠が非のリストの選択範囲を拒否することを確認する。"""
    with pytest.raises(WordPressMarkdownConversionError, match="Markdown list"):
        convert_list_to_wordpress_frame_html("普通の文章です")
