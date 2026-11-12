from __future__ import annotations

import pytest

from editor.paragraph_splitter import (
    ParagraphSplitError,
    build_paragraph_block,
    find_current_paragraph_block,
    split_paragraph_insert_html,
    split_paragraph_insert_spacer,
    wrap_selection_as_code_block,
    wrap_selection_as_decorated_block,
)


def test_find_current_paragraph_block_detects_content_range() -> None:
    text = "<!-- wp:paragraph -->\n<p>行A</p>\n<!-- /wp:paragraph -->"

    block = find_current_paragraph_block(text, text.index("行A"))

    assert block is not None
    assert text[block.content_start:block.content_end] == "行A"


def test_build_paragraph_block_trims_edge_breaks() -> None:
    assert build_paragraph_block("行A<br><br>\n") == (
        "<!-- wp:paragraph -->\n"
        "<p>行A</p>\n"
        "<!-- /wp:paragraph -->"
    )


def test_split_paragraph_insert_spacer() -> None:
    text = (
        "<!-- wp:paragraph -->\n"
        "<p>行A<br><br>\n"
        "\n"
        "行B<br><br>\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )

    replacement = split_paragraph_insert_spacer(text, text.index("\n\n") + 1)

    assert replacement.text == (
        "<!-- wp:paragraph -->\n"
        "<p>行A</p>\n"
        "<!-- /wp:paragraph -->\n\n"
        '<!-- wp:spacer {"height":"32px"} -->\n'
        '<div style="height:32px" aria-hidden="true" '
        'class="wp-block-spacer"></div>\n'
        "<!-- /wp:spacer -->\n\n"
        "<!-- wp:paragraph -->\n"
        "<p>行B</p>\n"
        "<!-- /wp:paragraph -->"
    )


def test_split_paragraph_insert_spacer_rejects_nonblank_line() -> None:
    text = (
        "<!-- wp:paragraph -->\n"
        "<p>行A<br><br>\n"
        "行B<br><br>\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )

    with pytest.raises(ParagraphSplitError, match="空行で右クリック"):
        split_paragraph_insert_spacer(text, text.index("行B"))


def test_split_paragraph_insert_html_code_block_rejects_nonblank_line() -> None:
    text = (
        "<!-- wp:paragraph -->\n"
        "<p>行A<br><br>\n"
        "行B<br><br>\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )

    with pytest.raises(ParagraphSplitError, match="空行で右クリック"):
        split_paragraph_insert_html(text, text.index("行B"))


def test_split_paragraph_insert_html_code_block_at_blank_line() -> None:
    text = (
        "<!-- wp:paragraph -->\n"
        "<p>行A<br><br>\n"
        "\n"
        "行B<br><br>\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )

    replacement = split_paragraph_insert_html(text, text.index("\n\n") + 1)

    assert replacement.text == (
        "<!-- wp:paragraph -->\n"
        "<p>行A</p>\n"
        "<!-- /wp:paragraph -->\n\n"
        "<!-- wp:html -->\n"
        "<pre\n"
        '    class="wp-block-code"\n'
        '    style="display:inline-block; border:1px solid #999; padding:16px; '
        'border-radius:8px; background-color:#f9f9f9;"\n'
        "><code>\n"
        "</code></pre>\n"
        "<!-- /wp:html -->\n\n"
        "<!-- wp:paragraph -->\n"
        "<p>行B</p>\n"
        "<!-- /wp:paragraph -->"
    )
    assert replacement.cursor_position == replacement.text.index("</code>")


def test_wrap_selection_as_code_block_expands_partial_selection_to_lines() -> None:
    text = (
        "<!-- wp:paragraph -->\n"
        "<p>行A<br><br>\n"
        "・行1<br>\n"
        "・行2<br>\n"
        "行B<br><br>\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )
    start = text.index("行1")
    end = text.index("行2") + len("行2")

    replacement = wrap_selection_as_code_block(text, start, end)

    assert "><code>・行1\n・行2</code></pre>" in replacement.text
    assert "<p>行A</p>" in replacement.text
    assert "<p>行B</p>" in replacement.text


def test_wrap_selection_as_code_block_converts_br_to_newlines() -> None:
    text = (
        "<!-- wp:paragraph -->\n"
        "<p>行A<br><br>\n"
        "・行1<br>\n"
        "・行2<br>\n"
        "・行3<br><br>\n"
        "行B<br><br>\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )
    start = text.index("・行1")
    end = text.index("<br><br>\n行B")

    replacement = wrap_selection_as_code_block(text, start, end)

    assert replacement.text == (
        "<!-- wp:paragraph -->\n"
        "<p>行A</p>\n"
        "<!-- /wp:paragraph -->\n\n"
        "<!-- wp:html -->\n"
        "<pre\n"
        '    class="wp-block-code"\n'
        '    style="display:inline-block; border:1px solid #999; padding:16px; '
        'border-radius:8px; background-color:#f9f9f9;"\n'
        "><code>・行1\n"
        "・行2\n"
        "・行3</code></pre>\n"
        "<!-- /wp:html -->\n\n"
        "<!-- wp:paragraph -->\n"
        "<p>行B</p>\n"
        "<!-- /wp:paragraph -->"
    )


def test_wrap_selection_as_decorated_block_uses_div_frame() -> None:
    text = (
        "<!-- wp:paragraph -->\n"
        "<p>行A<br><br>\n"
        "・行1<br>\n"
        "・行2<br><br>\n"
        "行B<br><br>\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )
    start = text.index("・行1")
    end = text.index("<br><br>\n行B")

    replacement = wrap_selection_as_decorated_block(text, start, end)

    assert '<div style="display: grid;' in replacement.text
    assert "border: 2px solid #4d29ff;" in replacement.text
    assert "background-color: #d0e7fb;" in replacement.text
    assert "border-left: 4px solid #2401d0;" in replacement.text
    assert "・行1<br>\n・行2" in replacement.text
    assert "<\\p>" not in replacement.text
    assert "2en" not in replacement.text
    assert "wp:preformatted" not in replacement.text
    assert "<!-- wp:html -->" in replacement.text


def test_wrap_selection_as_decorated_block_reads_info_frame_dictionary(
    tmp_path,
) -> None:
    (tmp_path / "wordpress_html_dict.json").write_text(
        """[
  {
    \"label_key\": \"tag.wordpress.info_frame_block\",
    \"hint_key\": \"tag.hint.wordpress.info_frame_block\",
    \"template\": \"<!-- wp:html -->\\n<div data-source=\\\"dictionary\\\">\\n{selection}{cursor}\\n</div>\\n<!-- /wp:html -->\",
    \"default_selection\": \"辞書の初期本文\"
  }
]""",
        encoding="utf-8",
    )
    text = "<!-- wp:paragraph -->\n<p><br><br>\n</p>\n<!-- /wp:paragraph -->"
    start = text.index("<br><br>")
    end = start + len("<br><br>")

    replacement = wrap_selection_as_decorated_block(text, start, end, tmp_path)

    assert '<div data-source="dictionary">' in replacement.text
    assert "辞書の初期本文" in replacement.text
    assert replacement.cursor_position == replacement.text.index("辞書の初期本文") + len(
        "辞書の初期本文"
    )


def test_wrap_selection_as_decorated_block_expands_partial_selection_to_lines() -> None:
    text = (
        "<!-- wp:paragraph -->\n"
        "<p>行A<br><br>\n"
        "・行1<br>\n"
        "・行2<br>\n"
        "行B<br><br>\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )
    start = text.index("行1")
    end = text.index("行2") + len("行2")

    replacement = wrap_selection_as_decorated_block(text, start, end)

    assert "・行1<br>\n・行2" in replacement.text
    assert "<p>行A</p>" in replacement.text
    assert "<p>行B</p>" in replacement.text


def test_split_rejects_position_outside_paragraph_block() -> None:
    with pytest.raises(ParagraphSplitError):
        split_paragraph_insert_spacer("plain text", 0)
