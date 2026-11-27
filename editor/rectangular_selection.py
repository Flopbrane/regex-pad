"""通常選択から矩形範囲を求めてテキストを取り出す。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RectangularSelection:
    """矩形の行と列の両端を保持する。"""
    start_line: int
    start_column: int
    end_line: int
    end_column: int


def rectangular_selection_from_text_positions(
    source_text: str,
    selection_start: int,
    selection_end: int,
) -> RectangularSelection:
    """2つの文字位置を行と列へ変換して矩形を求める。"""
    start_line, start_column = _line_column_at_position(source_text, selection_start)
    end_line, end_column = _line_column_at_position(source_text, selection_end)
    return RectangularSelection(
        start_line=start_line,
        start_column=start_column,
        end_line=end_line,
        end_column=end_column,
    )


def rectangular_text(source_text: str, selection: RectangularSelection) -> str:
    """矩形と交わる部分を各行から取り出し、改行でつなぐ。"""
    top_line = min(selection.start_line, selection.end_line)
    bottom_line = max(selection.start_line, selection.end_line)
    left_column = min(selection.start_column, selection.end_column)
    right_column = max(selection.start_column, selection.end_column)
    if left_column == right_column:
        return ""

    lines = source_text.split("\n")
    copied_lines: list[str] = []
    for line_index in range(top_line, bottom_line + 1):
        line = lines[line_index] if line_index < len(lines) else ""
        copied_lines.append(line[left_column:right_column])
    return "\n".join(copied_lines)


def _line_column_at_position(source_text: str, text_position: int) -> tuple[int, int]:
    """本文内の文字位置を行番号と列位置に変換する。"""
    bounded_position = min(max(text_position, 0), len(source_text))
    preceding_text = source_text[:bounded_position]
    line_number = preceding_text.count("\n")
    if not preceding_text:
        return 0, 0
    column_number = len(preceding_text.rsplit("\n", maxsplit=1)[-1])
    return line_number, column_number
