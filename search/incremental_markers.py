"""文書を読み直さず、Qtの編集位置とPythonの文字位置を対応させる。"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field


def _utf16_length(text: str) -> int:
    """文字列のQt UTF-16単位での長さを返す。"""
    return len(text.encode("utf-16-le")) // 2


@dataclass
class IndexedSource:
    """編集されたQtの範囲をPythonの文字位置へ変換するため、行の開始位置を保持する。"""

    text: str
    python_line_starts: list[int] = field(init=False)
    qt_line_starts: list[int] = field(init=False)

    def __post_init__(self) -> None:
        """検索位置の変換に使う行境界の索引を初期化する。"""
        self.python_line_starts = [0]
        self.qt_line_starts = [0]
        qt_position = 0
        for position, character in enumerate(self.text):
            qt_position += 2 if ord(character) > 0xFFFF else 1
            if character == "\n":
                self.python_line_starts.append(position + 1)
                self.qt_line_starts.append(qt_position)

    def python_position(self, qt_position: int) -> int:
        """QtのUTF-16位置がある行だけを調べてPythonの位置を求める。"""
        line_index = bisect_right(self.qt_line_starts, qt_position) - 1
        line_index = max(line_index, 0)
        python_start = self.python_line_starts[line_index]
        remaining_units = qt_position - self.qt_line_starts[line_index]
        position = python_start
        while position < len(self.text) and remaining_units > 0:
            width = 2 if ord(self.text[position]) > 0xFFFF else 1
            if width > remaining_units:
                break
            remaining_units -= width
            position += 1
        return position

    def qt_position(self, python_position: int) -> int:
        """指定されたPythonの位置を、その行だけを調べてQtの位置に変換する。"""
        bounded_position = min(max(python_position, 0), len(self.text))
        line_index = bisect_right(self.python_line_starts, bounded_position) - 1
        line_start = self.python_line_starts[line_index]
        return self.qt_line_starts[line_index] + _utf16_length(
            self.text[line_start:bounded_position]
        )

    def replace(self, qt_position: int, removed_units: int, added_text: str) -> tuple[int, int, int]:
        """Qtから通知された編集1件を反映し、編集前の両端とPython文字数の増減を返す。"""
        start = self.python_position(qt_position)
        old_end = self.python_position(qt_position + removed_units)
        old_start_line = bisect_right(self.python_line_starts, start) - 1
        old_end_line = bisect_right(self.python_line_starts, old_end) - 1
        delta_python = len(added_text) - (old_end - start)
        delta_qt = _utf16_length(added_text) - removed_units

        added_python_starts: list[int] = []
        added_qt_starts: list[int] = []
        qt_offset = 0
        for offset, character in enumerate(added_text):
            qt_offset += 2 if ord(character) > 0xFFFF else 1
            if character == "\n":
                added_python_starts.append(start + offset + 1)
                added_qt_starts.append(qt_position + qt_offset)

        self.python_line_starts = (
            self.python_line_starts[: old_start_line + 1]
            + added_python_starts
            + [position + delta_python for position in self.python_line_starts[old_end_line + 1 :]]
        )
        self.qt_line_starts = (
            self.qt_line_starts[: old_start_line + 1]
            + added_qt_starts
            + [position + delta_qt for position in self.qt_line_starts[old_end_line + 1 :]]
        )
        self.text = self.text[:start] + added_text + self.text[old_end:]
        return start, old_end, delta_python
