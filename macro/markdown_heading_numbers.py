"""直前の番号付き見出しを使い、Markdownの番号付き項目を振り直す。"""

import re

_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(\d+)\.(?:[ \t]+.*|[ \t]*)$")
_CHILD_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(\d+)-(\d+)\.(?:[ \t]+.*|[ \t]*)$")
_ANY_HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
_ITEM = re.compile(r"^(\d+)\.[ \t]+")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(?:.*)$")


def number_items_under_headings(source_text: str) -> tuple[str, int]:
    """文書を上から走査し、インデントのない項目番号の前に見出し番号を付ける。

    番号のない見出しで現在の区間を終える。フェンス付きコードはそのままコピーし、既存の本文、項目記号の後ろの空白、改行コードを保持する。
    """
    parent: tuple[str, str] | None = None
    fence: tuple[str, int] | None = None
    output: list[str] = []
    count = 0
    for line in source_text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        ending = line[len(body):]
        fence_match = _FENCE.match(body)
        if fence is not None:
            if fence_match and fence_match[1][0] == fence[0] and len(fence_match[1]) >= fence[1]:
                fence = None
            output.append(line)
            continue
        if fence_match:
            fence = fence_match[1][0], len(fence_match[1])
            output.append(line)
            continue
        heading = _HEADING.match(body)
        if heading:
            parent = heading[1], heading[2]
        elif _ANY_HEADING.match(body):
            child = _CHILD_HEADING.match(body)
            if not (parent and child and (child[1], child[2]) == parent):
                parent = None
        elif parent and (item := _ITEM.match(body)):
            line = f"{parent[0]} {parent[1]}-{item[1]}. " + body[item.end():] + ending
            count += 1
        output.append(line)
    return "".join(output), count
