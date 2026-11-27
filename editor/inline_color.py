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
    INLINE_STYLE_SINGLE = 10
    INLINE_STYLE_DOUBLE = 11


COLOR = re.compile(r"(?<![\w#\\-])#[0-9a-fA-F]{6}(?![\w\\-])")
DECLARATION = re.compile(r"(?:^|(?<=[;{}]))\s*(?:--)?[a-zA-Z_][\w-]*\s*:\s*([^;{}]*)(?=[;}]|$)")
CSS_TOKEN = re.compile(r"""/\*|"(?:\\.|[^"\\])*"?|'(?:\\.|[^'\\])*'?|(?:[a-zA-Z_-][\w-]*)?\(|\)""")
GRADIENTS = {
    "linear-gradient", "radial-gradient", "conic-gradient",
    "repeating-linear-gradient", "repeating-radial-gradient", "repeating-conic-gradient",
}
TAG = re.compile(r"</?([a-zA-Z][\w:-]*)(?=[\s/>]|$)")
ATTRIBUTE = re.compile(r"\s*([^\s=/<>\x22']+)(\s*=\s*)?")
UNQUOTED_VALUE = re.compile(r"[^\s>]+")
TAG_QUOTES = {
    ColorContext.HTML_SINGLE_QUOTE: "'",
    ColorContext.HTML_DOUBLE_QUOTE: '"',
    ColorContext.INLINE_STYLE_SINGLE: "'",
    ColorContext.INLINE_STYLE_DOUBLE: '"',
}
INLINE_STYLES = {ColorContext.INLINE_STYLE_SINGLE, ColorContext.INLINE_STYLE_DOUBLE}
STYLE_END = re.compile(r"</style\s*>", re.IGNORECASE)
RAW_END = {
    context: re.compile(rf"</{context.name.lower()}\s*>", re.IGNORECASE)
    for context in (ColorContext.SCRIPT, ColorContext.TEXTAREA, ColorContext.TITLE)
}


def css_colors(
    text: str, in_comment: bool = False, depth: int = 0,
) -> tuple[list[tuple[int, str]], bool, int]:
    """CSS宣言値とグラデーションの色を調べ、文字列やURLを除外する。"""
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
        if value.endswith("("):
            if depth or value[:-1].lower() not in GRADIENTS:
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


def _tag_colors(
    text: str, position: int, state: ColorContext, css_state: int,
    colors: list[tuple[int, str]],
) -> tuple[int, ColorContext, int]:
    """開始タグの続きを読み、属性値の引用符を次の行へ引き継ぐ。"""
    while position < len(text):
        quote = TAG_QUOTES.get(state)
        if quote:
            closing = text.find(quote, position)
            end = len(text) if closing < 0 else closing
            if state in INLINE_STYLES:
                found, comment, depth = css_colors(
                    text[position:end], bool(css_state & 1), css_state >> 1,
                )
                colors.extend((position + start, code) for start, code in found)
                css_state = (depth << 1) | int(comment)
            if closing < 0:
                return len(text), state, css_state
            position, state, css_state = end + 1, ColorContext.HTML_TAG, 0
            continue
        if text[position] == ">":
            return position + 1, ColorContext.HTML, 0
        attribute = ATTRIBUTE.match(text, position)
        if attribute is None:
            position += 1
            continue
        position = attribute.end()
        if attribute.group(2) is None or position == len(text):
            continue
        is_style = attribute.group(1).lower() == "style"
        if text[position] == "'":
            state = ColorContext.INLINE_STYLE_SINGLE if is_style else ColorContext.HTML_SINGLE_QUOTE
            position += 1
        elif text[position] == '"':
            state = ColorContext.INLINE_STYLE_DOUBLE if is_style else ColorContext.HTML_DOUBLE_QUOTE
            position += 1
        elif value := UNQUOTED_VALUE.match(text, position):
            if is_style:
                found, _, _ = css_colors(value.group())
                colors.extend((position + start, code) for start, code in found)
            position = value.end()
    return position, state, css_state


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
            position, context, depth = _tag_colors(text, position, context, depth, colors)
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
            position, context, depth = _tag_colors(text, tag.end(), ColorContext.HTML_TAG, 0, colors)
            if context == ColorContext.HTML and not text.startswith("</", tag.start()):
                name = tag.group(1).lower()
                context = {
                    "style": ColorContext.STYLE, "script": ColorContext.SCRIPT,
                    "textarea": ColorContext.TEXTAREA, "title": ColorContext.TITLE,
                }.get(name, ColorContext.HTML)
    return colors, context, depth
