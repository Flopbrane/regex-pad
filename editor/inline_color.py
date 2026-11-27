"""エディターに表示する6桁のCSS色コードを行単位で検出する。"""

from __future__ import annotations

import re
from enum import IntEnum


class ColorContext(IntEnum):
    HTML = 0
    HTML_COMMENT = 1
    HTML_TAG = 2
    HTML_SINGLE_QUOTE = 3
    HTML_DOUBLE_QUOTE = 4
    STYLE = 5
    STYLE_COMMENT = 6
    SCRIPT = 7
    TEXTAREA = 8
    TITLE = 9


COLOR = re.compile(r"(?<![\w#\\-])#[0-9a-fA-F]{6}(?![\w\\-])")
DECLARATION = re.compile(r"(?:^|(?<=[;{}]))\s*(?:--)?[a-zA-Z_][\w-]*\s*:\s*([^;{}]*)(?=[;}]|$)")
CSS_TOKEN = re.compile(r"""/\*|"(?:\\.|[^"\\])*"?|'(?:\\.|[^'\\])*'?|[()]""")
TAG = re.compile(r"</?([a-zA-Z][\w:-]*)(?=[\s/>]|$)")
ATTRIBUTE = re.compile(r"""([^\s=/<>]+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s>]+))?""")
STYLE_END = re.compile(r"</style\s*>", re.IGNORECASE)
RAW_END = {
    context: re.compile(rf"</{context.name.lower()}\s*>", re.IGNORECASE)
    for context in (ColorContext.SCRIPT, ColorContext.TEXTAREA, ColorContext.TITLE)
}


def css_colors(
    text: str, in_comment: bool = False, depth: int = 0,
) -> tuple[list[tuple[int, str]], bool, int]:
    """コメント、文字列、関数の引数を除いたCSS宣言値を調べる。"""
    masked = list(text)
    position = 0
    while position < len(text):
        if in_comment:
            closing = text.find("*/", position)
            end = len(text) if closing < 0 else closing + 2
            masked[position:end] = " " * (end - position)
            position, in_comment = end, closing < 0
            continue
        token = CSS_TOKEN.search(text, position)
        if depth:
            end = len(text) if token is None else token.start()
            masked[position:end] = " " * (end - position)
        if token is None:
            break
        value = token.group()
        if value == "/*":
            masked[token.start():token.end()] = "  "
            position = token.end()
            in_comment = True
            continue
        if value == "(":
            depth += 1
        elif value == ")":
            depth = max(0, depth - 1)
        masked[token.start():token.end()] = " " * len(value)
        position = token.end()
    source = "".join(masked)
    colors = [
        (match.start(), match.group())
        for declaration in DECLARATION.finditer(source)
        for match in COLOR.finditer(source, *declaration.span(1))
    ]
    return colors, in_comment, depth


def _tag_end(text: str, start: int, state: ColorContext) -> tuple[int, ColorContext]:
    quote = {ColorContext.HTML_SINGLE_QUOTE: "'", ColorContext.HTML_DOUBLE_QUOTE: '"'}.get(state)
    for position in range(start, len(text)):
        character = text[position]
        if quote:
            if character == quote:
                quote = None
        elif character in "\"'":
            quote = character
        elif character == ">":
            return position, ColorContext.HTML
    state = {"'": ColorContext.HTML_SINGLE_QUOTE, '"': ColorContext.HTML_DOUBLE_QUOTE}.get(
        quote or "", ColorContext.HTML_TAG,
    )
    return len(text), state


def find_colors(
    text: str, context: ColorContext, depth: int, *, stylesheet: bool,
) -> tuple[list[tuple[int, str]], ColorContext, int]:
    """行の色と次の行に引き継ぐ構文状態を返す。"""
    colors: list[tuple[int, str]] = []
    if stylesheet:
        context = ColorContext.STYLE_COMMENT if context == ColorContext.STYLE_COMMENT else ColorContext.STYLE
    position = 0
    while position < len(text):
        if context in (ColorContext.STYLE, ColorContext.STYLE_COMMENT):
            closing = None if stylesheet else STYLE_END.search(text, position)
            end = closing.start() if closing else len(text)
            found, in_comment, depth = css_colors(
                text[position:end], context == ColorContext.STYLE_COMMENT, depth,
            )
            colors.extend((position + start, code) for start, code in found)
            if not closing:
                context = ColorContext.STYLE_COMMENT if in_comment else ColorContext.STYLE
                break
            position, context, depth = closing.end(), ColorContext.HTML, 0
        elif context == ColorContext.HTML_COMMENT:
            end = text.find("-->", position)
            if end < 0:
                break
            position, context = end + 3, ColorContext.HTML
        elif context in RAW_END:
            closing = RAW_END[context].search(text, position)
            if not closing:
                break
            position, context = closing.end(), ColorContext.HTML
        elif context != ColorContext.HTML:
            end, context = _tag_end(text, position, context)
            position = end + 1
        else:
            position = text.find("<", position)
            if position < 0:
                break
            if text.startswith("<!--", position):
                position, context = position + 4, ColorContext.HTML_COMMENT
                continue
            tag = TAG.match(text, position)
            if not tag:
                position += 1
                continue
            end, context = _tag_end(text, tag.end(), ColorContext.HTML_TAG)
            if context == ColorContext.HTML and not text.startswith("</", position):
                for attribute in ATTRIBUTE.finditer(text, tag.end(), end):
                    value = attribute.group(2)
                    if attribute.group(1).lower() != "style" or not value:
                        continue
                    quoted = value[0] in "\"'"
                    found, _, _ = css_colors(value[1:-1] if quoted else value)
                    colors.extend((attribute.start(2) + int(quoted) + start, code) for start, code in found)
                name = tag.group(1).lower()
                context = {
                    "style": ColorContext.STYLE, "script": ColorContext.SCRIPT,
                    "textarea": ColorContext.TEXTAREA, "title": ColorContext.TITLE,
                }.get(name, ColorContext.HTML)
            position = end + 1
    return colors, context, depth
