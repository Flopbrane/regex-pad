"""選択されたMarkdownを同梱のWordPress変換処理に渡す。"""

from __future__ import annotations

from collections.abc import Callable
from html.parser import HTMLParser

from wp_conv_core.wp_converters.wp_markdown_converter import (
    WPComplexMarkdownConversionError,
    wp_convert_complex_markdown_blocks_to_wordpress,
    wp_convert_markdown_lists_to_wordpress,
    wp_convert_markdown_tables_to_wordpress,
)


class WordPressMarkdownConversionError(RuntimeError):
    """同梱のWordPress変換処理が出力を生成できなかった場合に発生する。"""


def convert_complex_markdown_blocks_to_wordpress_html(markdown_text: str) -> str:
    """選択したMarkdownの表とリストをWordPressのブロックHTMLに変換する。"""
    return _convert_with_embedded_core(
        wp_convert_complex_markdown_blocks_to_wordpress,
        markdown_text,
    )


def convert_markdown_tables_to_wordpress_html(markdown_text: str) -> str:
    """選択したMarkdownの表をWordPressの表ブロックに変換する。"""
    return _convert_with_embedded_core(
        wp_convert_markdown_tables_to_wordpress,
        markdown_text,
    )


def convert_markdown_lists_to_wordpress_html(markdown_text: str) -> str:
    """選択したMarkdownのリストをWordPressのリストブロックに変換する。"""
    return _convert_with_embedded_core(
        wp_convert_markdown_lists_to_wordpress,
        markdown_text,
    )


def convert_list_to_wordpress_frame_html(
    source_text: str,
    *,
    alignment: str = "left",
    outer_spacing: str = "1.5em 0 2em 0",
    inner_style: str = (
        "display: inline-block; max-width: 100%; border: 2px solid #f0b84a; "
        "background-color: #fffaf0; color: #333333; padding: 14px 16px; "
        "border-radius: 8px; text-align: left;"
    ),
) -> str:
    """MarkdownまたはWordPressのリストを、区切りコメントが壊れない単一の枠ブロックに変換する。"""
    list_html = source_text.strip()
    parser = _ListItemParser()
    parser.feed(list_html)
    parser.close()
    if not parser.items:
        list_html = convert_markdown_lists_to_wordpress_html(source_text)
        parser = _ListItemParser()
        parser.feed(list_html)
        parser.close()
    if not parser.items:
        raise WordPressMarkdownConversionError(
            "Markdown or WordPress list items were not found in the selection."
        )

    rows = []
    for index, item_html in enumerate(parser.items, start=1):
        marker = f"{index}." if parser.ordered else "・"
        bottom_margin = "0" if index == len(parser.items) else "0.45em"
        rows.append(
            f'<div style="margin: 0 0 {bottom_margin} 0;">'
            f'<span style="font-weight: bold;">{marker}</span> {item_html}'
            "</div>"
        )
    return (
        "<!-- wp:html -->\n"
        f'<div style="text-align: {alignment}; margin: {outer_spacing};">\n'
        f'<div style="{inner_style}">\n'
        + "\n".join(rows)
        + "\n</div>\n</div>\n<!-- /wp:html -->"
    )


class _ListItemParser(HTMLParser):
    """Gutenbergコメントを除き、リスト項目の内側のHTMLを集める。"""

    def __init__(self) -> None:
        """リスト項目を切り出すための解析状態を初期化する。"""
        super().__init__(convert_charrefs=False)
        self.items: list[str] = []
        self.ordered = False
        self._current_item: list[str] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """開始タグを読み、リスト項目の内側のHTMLを記録する。"""
        del attrs
        if tag == "ol" and self._current_item is None:
            self.ordered = True
        if tag == "li" and self._current_item is None:
            self._current_item = []
        elif self._current_item is not None:
            start_tag_text = self.get_starttag_text()
            if start_tag_text is not None:
                self._current_item.append(start_tag_text)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """リスト項目内の自己終了タグを記録する。"""
        del tag, attrs
        if self._current_item is not None:
            start_tag_text = self.get_starttag_text()
            if start_tag_text is not None:
                self._current_item.append(start_tag_text)

    def handle_endtag(self, tag: str) -> None:
        """終了タグを読み、項目の境界と内容を管理する。"""
        if tag == "li" and self._current_item is not None:
            item_html = "".join(self._current_item).strip()
            if item_html:
                self.items.append(item_html)
            self._current_item = None
        elif self._current_item is not None:
            self._current_item.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        """リスト項目内の本文を記録する。"""
        if self._current_item is not None:
            self._current_item.append(data)

    def handle_entityref(self, name: str) -> None:
        """リスト項目内の名前付き文字参照を記録する。"""
        if self._current_item is not None:
            self._current_item.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        """リスト項目内の数値文字参照を記録する。"""
        if self._current_item is not None:
            self._current_item.append(f"&#{name};")


def _convert_with_embedded_core(
    converter: Callable[[str], str],
    markdown_text: str,
) -> str:
    """選択内容を同梱の変換処理へ渡し、変換結果を取得する。"""
    try:
        return converter(markdown_text)
    except WPComplexMarkdownConversionError as error:
        raise WordPressMarkdownConversionError(str(error)) from error
