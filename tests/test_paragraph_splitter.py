"""段落分割処理を検証する。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from editor.paragraph_insert_rules import load_paragraph_insert_rule_book
from editor.paragraph_splitter import (
    INSERT_SPACER_KEY,
    ParagraphSplitError,
    build_paragraph_block,
    find_current_paragraph_block,
    lint_paragraph_insertion,
    split_paragraph_insert_html,
    split_paragraph_insert_spacer,
    wrap_selection_as_code_block,
    wrap_selection_as_decorated_block,
)


def _code_block_style() -> str:
    """テストで色を固定せず、編集可能なコードブロック用のstyleを読み込む。"""
    template = load_paragraph_insert_rule_book().operation("insert_html").replacement
    return template.split('style="', 1)[1].split('"', 1)[0]


def test_find_current_paragraph_block_detects_content_range() -> None:
    """検索の現在の段落ブロックが内容の範囲を検出することを確認する。"""
    text = "<!-- wp:paragraph -->\n<p>行A</p>\n<!-- /wp:paragraph -->"

    block = find_current_paragraph_block(text, text.index("行A"))

    assert block is not None
    assert text[block.content_start:block.content_end] == "行A"


def test_build_paragraph_block_trims_edge_breaks() -> None:
    """段落ブロックを生成するとき、両端にある余分な改行を除くことを確認する。"""
    assert build_paragraph_block("行A<br><br>\n") == (
        "<!-- wp:paragraph -->\n"
        "<p>行A</p>\n"
        "<!-- /wp:paragraph -->"
    )


def test_split_paragraph_insert_spacer() -> None:
    """分割の段落挿入のスペーサーを確認する。"""
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
    """分割の段落挿入のスペーサーが空白以外の行を拒否することを確認する。"""
    text = (
        "<!-- wp:paragraph -->\n"
        "<p>行A<br><br>\n"
        "行B<br><br>\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )

    with pytest.raises(ParagraphSplitError) as error:
        split_paragraph_insert_spacer(text, text.index("行B"))
    assert error.value.message_key == "paragraph_split.insert_spacer_not_available"


def test_split_paragraph_insert_html_code_block_rejects_nonblank_line() -> None:
    """分割の段落挿入のHTMLのコードブロックが空白以外の行を拒否することを確認する。"""
    text = (
        "<!-- wp:paragraph -->\n"
        "<p>行A<br><br>\n"
        "行B<br><br>\n"
        "</p>\n"
        "<!-- /wp:paragraph -->"
    )

    with pytest.raises(ParagraphSplitError) as error:
        split_paragraph_insert_html(text, text.index("行B"))
    assert error.value.message_key == "paragraph_split.insert_html_not_available"


def test_split_paragraph_insert_html_code_block_at_blank_line() -> None:
    """分割の段落挿入のHTMLのコードブロックでの空の行を確認する。"""
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
        f'    style="{_code_block_style()}"\n'
        "><code>\n"
        "</code></pre>\n"
        "<!-- /wp:html -->\n\n"
        "<!-- wp:paragraph -->\n"
        "<p>行B</p>\n"
        "<!-- /wp:paragraph -->"
    )
    assert replacement.cursor_position == replacement.text.index("</code>")


def test_wrap_selection_as_code_block_expands_partial_selection_to_lines() -> None:
    """折り返しの選択範囲のとしてのコードブロックが一部の選択範囲のへの行を広げることを確認する。"""
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
    """折り返しの選択範囲のとしてのコードブロックがbrのへの改行に変換することを確認する。"""
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
        f'    style="{_code_block_style()}"\n'
        "><code>・行1\n"
        "・行2\n"
        "・行3</code></pre>\n"
        "<!-- /wp:html -->\n\n"
        "<!-- wp:paragraph -->\n"
        "<p>行B</p>\n"
        "<!-- /wp:paragraph -->"
    )


def test_wrap_selection_as_decorated_block_uses_div_frame() -> None:
    """選択範囲を装飾ブロックで包むとき、divの枠を使うことを確認する。"""
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

    template = load_paragraph_insert_rule_book().operation("decorated_block").replacement
    display = template.split('<div style="', 1)[1].split(";", 1)[0]
    assert f'<div style="{display};' in replacement.text
    assert "border: 2px solid #4d29ff;" in replacement.text
    assert "background-color: #d0e7fb;" in replacement.text
    assert "border-left: 4px solid #2401d0;" in replacement.text
    assert "・行1<br>\n・行2" in replacement.text
    assert "<\\p>" not in replacement.text
    assert "2en" not in replacement.text
    assert "wp:preformatted" not in replacement.text
    assert "<!-- wp:html -->" in replacement.text


def test_wrap_selection_as_decorated_block_reads_paragraph_insert_dictionary(
    tmp_path: Path,
) -> None:
    """折り返しの選択範囲のとしての装飾付きのブロックが段落挿入の辞書を読み取ることを確認する。"""
    load_data = json.loads(
        Path("dictionaries/paragraph_insert_dict.json").read_text(encoding="utf-8")
    )
    load_data["operations"]["decorated_block"]["replacement"] = (
        '<!-- wp:html -->\n<div data-source="dictionary">\n'
        "{selection}{cursor}\n</div>\n<!-- /wp:html -->"
    )
    load_data["operations"]["decorated_block"]["empty_selection"] = "辞書の初期本文"
    (tmp_path / "paragraph_insert_dict.json").write_text(
        json.dumps(load_data, ensure_ascii=False, indent=2),
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
    """折り返しの選択範囲のとしての装飾付きのブロックが一部の選択範囲のへの行を広げることを確認する。"""
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
    """分割が位置の外の段落ブロックを拒否することを確認する。"""
    with pytest.raises(ParagraphSplitError) as error:
        split_paragraph_insert_spacer("plain text", 0)
    assert error.value.message_key == "paragraph_split.not_available"


@pytest.mark.parametrize(
    ("fixture_name", "allowed", "message_key"),
    [
        ("correct.wp_html", True, ""),
        (
            "incorrect.wp_html",
            False,
            "paragraph_split.insert_spacer_not_available",
        ),
    ],
)
def test_paragraph_insert_fixtures_drive_read_only_insertion_linter(
    fixture_name: str,
    allowed: bool,
    message_key: str,
) -> None:
    """段落挿入の検証用の例のドライブの読み取り専用の挿入の文法チェッカーを確認する。"""
    load_file_path = Path("tests") / f"paragraph_insert_{fixture_name}"
    source = load_file_path.read_text(encoding="utf-8")
    cursor_marker = "{cursor}"
    cursor_pos = source.index(cursor_marker)
    text = source.replace(cursor_marker, "")

    result = lint_paragraph_insertion(
        text,
        cursor_pos,
        cursor_pos,
        INSERT_SPACER_KEY,
    )

    assert result.allowed is allowed
    assert result.message_key == message_key
    assert text == source.replace(cursor_marker, "")


@pytest.mark.parametrize(
    ("text", "message_key"),
    [
        (
            (
                '<!-- wp:paragraph -->\n<p class="has-text-align-center">本文</p>\n'
                '<!-- /wp:paragraph -->'
            ),
            "paragraph_split.paragraph_attributes",
        ),
        (
            "<!-- wp:paragraph -->\n<div><p>本文</p></div>\n<!-- /wp:paragraph -->",
            "paragraph_split.paragraph_structure",
        ),
    ],
)
def test_paragraph_insert_linter_rejects_unsafe_paragraph_grammar(
    text: str,
    message_key: str,
) -> None:
    """段落挿入の文法チェッカーが安全でないの段落の文法を拒否することを確認する。"""
    cursor_pos = text.index("本文")

    result = lint_paragraph_insertion(
        text,
        cursor_pos,
        cursor_pos,
        INSERT_SPACER_KEY,
    )

    assert not result.allowed
    assert result.message_key == message_key


def test_paragraph_insert_replacement_is_loaded_from_dedicated_dictionary(
    tmp_path: Path,
) -> None:
    """段落挿入の置換が専用の辞書の状態でから読み込まれることを確認する。"""
    load_data = json.loads(
        Path("dictionaries/paragraph_insert_dict.json").read_text(encoding="utf-8")
    )
    load_data["operations"]["insert_spacer"]["replacement"] = (
        '<!-- custom-spacer data-height="{height}">{cursor}'
    )
    (tmp_path / "paragraph_insert_dict.json").write_text(
        json.dumps(load_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    text = "<!-- wp:paragraph -->\n<p>前\n\n後</p>\n<!-- /wp:paragraph -->"

    replacement = split_paragraph_insert_spacer(
        text,
        text.index("\n\n") + 1,
        tmp_path,
    )

    assert '<!-- custom-spacer data-height="32">' in replacement.text
    assert "<!-- wp:spacer" not in replacement.text


def test_paragraph_insert_exclusion_is_applied_by_search_engine(
    tmp_path: Path,
) -> None:
    """段落挿入の除外がによるの検索のエンジンが適用されることを確認する。"""
    load_data = json.loads(
        Path("dictionaries/paragraph_insert_dict.json").read_text(encoding="utf-8")
    )
    load_data["operations"]["insert_html"]["exclude"] = "禁止"
    (tmp_path / "paragraph_insert_dict.json").write_text(
        json.dumps(load_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    text = "<!-- wp:paragraph -->\n<p>前\n禁止\n後</p>\n<!-- /wp:paragraph -->"
    start = text.index("禁止")

    with pytest.raises(ParagraphSplitError) as error:
        wrap_selection_as_code_block(text, start, start + len("禁止"), tmp_path)

    assert error.value.message_key == "paragraph_split.insert_html_not_available"


def test_paragraph_splitter_contains_no_block_output_literals() -> None:
    """段落分割処理がなしのブロックの出力のリテラルを含むことを確認する。"""
    source = Path("editor/paragraph_splitter.py").read_text(encoding="utf-8")
    assert "<!-- wp:" not in source
    assert "<pre" not in source
    assert "ここでは" not in source
