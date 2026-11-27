"""WordPressの表ブロックを組み立てる。"""

from __future__ import annotations

from wp_conv_core.wp_blocks.wp_inline import wp_format_inline_text


def wp_create_table_block_from_rows(
    headers: list[str],
    rows: list[list[str]],
    convert_inline_code: bool = False,
) -> str:
    """Markdownの表の行をWordPressのGutenberg表ブロックに変換する。"""
    table_rows: list[list[dict[str, str]]] = []

    if headers:
        table_rows.append([{"tag": "th", "text": header.strip()} for header in headers])

    for row in rows:
        table_rows.append([{"tag": "td", "text": cell.strip()} for cell in row])

    if not table_rows:
        return ""

    return _wp_create_table_block_from_row_data(
        table_rows,
        convert_inline_code=convert_inline_code,
    )


def _wp_create_table_block_from_row_data(
    rows: list[list[dict[str, str]]],
    convert_inline_code: bool = False,
) -> str:
    """見出し行と本文行からWordPress表のHTMLを組み立てる。"""
    header_rows: list[list[dict[str, str]]] = []
    body_rows = rows

    if rows and all(cell["tag"] == "th" for cell in rows[0]):
        header_rows = [rows[0]]
        body_rows = rows[1:]

    header_html = ""
    if header_rows:
        header_html = (
            "<thead>\n"
            + "\n".join(
                _wp_create_row_html(row, convert_inline_code=convert_inline_code)
                for row in header_rows
            )
            + "\n</thead>\n"
        )

    body_html = "\n".join(
        _wp_create_row_html(row, convert_inline_code=convert_inline_code)
        for row in body_rows
    )
    return (
        "<!-- wp:table -->\n"
        '<figure class="wp-block-table"><table>\n'
        f"{header_html}<tbody>\n"
        f"{body_html}\n"
        "</tbody></table></figure>\n"
        "<!-- /wp:table -->"
    )


def _wp_create_row_html(
    row: list[dict[str, str]],
    convert_inline_code: bool = False,
) -> str:
    """指定のセルを表の1行分のHTMLにする。"""
    cells = "".join(
        f"<{cell['tag']}>"
        f"{wp_format_inline_text(cell['text'], convert_inline_code=convert_inline_code)}"
        f"</{cell['tag']}>"
        for cell in row
    )
    return f"<tr>{cells}</tr>"

