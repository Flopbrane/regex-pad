"""WordPressのリストブロックを組み立てる。"""

from __future__ import annotations

from typing import Literal

from wp_conv_core.wp_blocks.wp_inline import wp_format_inline_text

WP_ADJACENT_UNORDERED_LIST_BLOCK_PATTERN = (
    "</ul>\n"
    "<!-- /wp:list -->\n\n"
    "<!-- wp:list -->\n"
    '<ul class="wp-block-list">'
)
WP_ADJACENT_ORDERED_LIST_BLOCK_PATTERN = (
    "</ol>\n"
    "<!-- /wp:list -->\n\n"
    '<!-- wp:list {"ordered":true} -->\n'
    '<ol class="wp-block-list">'
)


def wp_create_list_block(
    items: list[str],
    ordered: bool = False,
    convert_inline_code: bool = False,
) -> str:
    """リスト項目をWordPressのGutenbergリストブロックに変換する。"""
    tag_name: Literal["ol", "ul"] = "ol" if ordered else "ul"
    safe_items = [
        wp_format_inline_text(item.strip(), convert_inline_code=convert_inline_code)
        for item in items
        if item.strip()
    ]
    list_items = "\n".join(
        "<!-- wp:list-item -->\n"
        f"<li>{item}</li>\n"
        "<!-- /wp:list-item -->"
        for item in safe_items
    )
    start_comment = '<!-- wp:list {"ordered":true} -->' if ordered else "<!-- wp:list -->"
    return (
        f"{start_comment}\n"
        f'<{tag_name} class="wp-block-list">\n'
        f"{list_items}\n"
        f"</{tag_name}>\n"
        "<!-- /wp:list -->"
    )


def wp_normalize_adjacent_list_blocks(save_data: str) -> str:
    """隣り合う同じ種類のリストブロックを1つにまとめる。"""
    save_data = save_data.replace(WP_ADJACENT_UNORDERED_LIST_BLOCK_PATTERN, "\n\n")
    return save_data.replace(WP_ADJACENT_ORDERED_LIST_BLOCK_PATTERN, "\n\n")

