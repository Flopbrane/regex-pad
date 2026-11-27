# pylint: disable=C0301,I1101,C0103
"""正規表現を軽量に色分けする入力ウィジェットを提供する。"""

from __future__ import annotations

import math
import re

from PySide6 import QtCore, QtGui, QtWidgets

REGEX_TOKEN_COLOR = QtGui.QColor("#7a4a12")


class RegexInputHighlighter(QtGui.QSyntaxHighlighter):
    """正規表現の入力に構文の色付けを行う。"""
    def __init__(self, document: QtGui.QTextDocument) -> None:
        """正規表現の色付けに使う書式を初期化する。"""
        super().__init__(document)
        self.enabled = False
        self.normal_format = QtGui.QTextCharFormat()
        self._normal_foreground_color = QtGui.QColor()
        self.regex_format = QtGui.QTextCharFormat()
        self.regex_format.setForeground(REGEX_TOKEN_COLOR)

    def set_enabled(self, enabled: bool) -> None:
        """正規表現の色付けを有効または無効にする。"""
        self.enabled = enabled
        self.rehighlight()

    def set_normal_foreground(self, color: QtGui.QColor) -> None:
        """色付けの対象外となる文字の色を設定する。"""
        if color == self._normal_foreground_color:
            return
        self._normal_foreground_color = QtGui.QColor(color)
        self.normal_format.setForeground(color)
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        """指定されたテキストブロック内の正規表現要素を色付けする。"""
        if not self.enabled:
            return

        if text:
            self.setFormat(0, len(text), self.normal_format)
        for start, length in self._regex_token_ranges(text):
            self.setFormat(start, length, self.regex_format)

    def _regex_token_ranges(self, text: str) -> list[tuple[int, int]]:
        """正規表現要素の範囲を開始位置と長さの組で返す。"""
        ranges: list[tuple[int, int]] = []
        ranges.extend(self._match_ranges(r"\\[AbBdDsSwWZzGnrtfv](?:[*+?]|\{\d+(?:,\d*)?\})?\??", text))
        ranges.extend(self._group_ranges(text))
        ranges.extend(self._match_ranges(r"(?<!\\)\.(?:[*+?]|\{\d+(?:,\d*)?\})?\??", text))
        ranges.extend(self._match_ranges(r"(?<!\\)(?:\^|\$|\|)", text))
        ranges.extend(self._match_ranges(r"(?<!\\)(?:[*+?]|\{\d+(?:,\d*)?\})\??", text))
        ranges.extend(self._match_ranges(r"(?:\\g<[^>]+>|\\[1-9]\d*|\$\d+|\$\{[A-Za-z_]\w*\})", text))
        return self._merge_ranges(ranges)

    def _match_ranges(self, pattern: str, text: str) -> list[tuple[int, int]]:
        """指定パターンに一致した範囲を開始位置と長さの組で返す。"""
        return [(match.start(), match.end() - match.start()) for match in re.finditer(pattern, text)]

    def _group_ranges(self, text: str) -> list[tuple[int, int]]:
        """正規表現のグループの範囲を開始位置と長さの組で返す。"""
        ranges: list[tuple[int, int]] = []
        stack: list[int] = []
        escaped = False
        in_character_class = False
        for index, character in enumerate(text):
            if escaped:
                escaped = False
                continue
            if character == "\\":
                escaped = True
                continue
            if character == "[" and not in_character_class:
                in_character_class = True
                continue
            if character == "]" and in_character_class:
                in_character_class = False
                continue
            if in_character_class:
                continue
            if character == "(":
                stack.append(index)
            elif character == ")" and stack:
                start = stack.pop()
                ranges.append((start, index - start + 1))
        return ranges

    def _merge_ranges(self, ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """重なる範囲と隣接する範囲をまとめる。"""
        if not ranges:
            return []
        sorted_ranges: list[tuple[int, int]] = sorted((start, start + length) for start, length in ranges)
        merged: list[tuple[int, int]] = []
        current_start, current_end = sorted_ranges[0]
        for start, end in sorted_ranges[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
                continue
            merged.append((current_start, current_end - current_start))
            current_start, current_end = start, end
        merged.append((current_start, current_end - current_start))
        return merged


class RegexInputEdit(QtWidgets.QPlainTextEdit):
    """正規表現を軽量に色付けするプレーンテキスト入力欄。"""
    returnPressed = QtCore.Signal()
    MINIMUM_VISIBLE_LINES = 1
    MAXIMUM_VISIBLE_LINES = 5

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """正規表現入力欄と表示更新を初期化する。"""
        super().__init__(parent)
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTabChangesFocus(True)
        self._visible_line_count = self.MINIMUM_VISIBLE_LINES
        self._refreshing_height = False
        self.setFixedHeight(self._visible_text_height())
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.highlighter = RegexInputHighlighter(self.document())
        self._refreshing_visible_text = False
        self._preserve_full_selection_on_focus_out = False
        self.document().documentLayout().documentSizeChanged.connect(
            self._refresh_height_for_content
        )
        self._update_highlighter_text_color()

    def sizeHint(self) -> QtCore.QSize:
        """空行が見える高さを含めた推奨サイズを返す。"""
        size = super().sizeHint()
        return QtCore.QSize(size.width(), self._visible_text_height())

    def minimumSizeHint(self) -> QtCore.QSize:
        """前後の行が表示できる最小サイズを返す。"""
        size = super().minimumSizeHint()
        return QtCore.QSize(size.width(), self._visible_text_height())

    def _visible_text_height(self) -> int:
        """設定された表示行数に必要な高さを返す。"""
        metrics = self.fontMetrics()
        line_height = max(metrics.height(), metrics.lineSpacing())
        margins = math.ceil(self.document().documentMargin() * 2)
        # Include the actual frame and a rounding allowance. An exact-fit
        # viewport can acquire an extra scroll step on the Windows 11 style.
        return line_height * self._visible_line_count + margins + self.frameWidth() * 2 + 2

    def text(self) -> str:
        """ウィジェットの現在の文字列を返す。"""
        return self.toPlainText()

    def setText(self, text: str) -> None:
        """ウィジェットに文字列を設定する。"""
        self.setPlainText(text)
        self._queue_visible_text_refresh()

    def insert(self, text: str) -> None:
        """現在のカーソル位置へ文字列を挿入する。"""
        self.textCursor().insertText(text)
        self._queue_visible_text_refresh()

    def selectionStart(self) -> int:
        """現在の選択範囲の開始位置を返す。"""
        return self.textCursor().selectionStart()

    def hasSelectedText(self) -> bool:
        """文字列が選択されているかを返す。"""
        return self.textCursor().hasSelection()

    def cursorPosition(self) -> int:
        """現在のカーソル位置を返す。"""
        return self.textCursor().position()

    def setCursorPosition(self, position: int) -> None:
        """カーソル位置を設定する。"""
        cursor = self.textCursor()
        cursor.setPosition(position)
        self.setTextCursor(cursor)
        self._queue_visible_text_refresh()

    def setSelection(self, start: int, length: int) -> None:
        """指定した範囲を入力欄で選択する。"""
        cursor: QtGui.QTextCursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(start + length, cursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
        self._queue_visible_text_refresh()

    def set_regex_highlighting_enabled(self, enabled: bool) -> None:
        """正規表現の色付けを有効または無効にする。"""
        self._update_highlighter_text_color()
        self.highlighter.set_enabled(enabled)
        self._queue_visible_text_refresh()

    def stabilize_visible_text(self) -> None:
        """レイアウトを更新し、現在の入力文字列が見えるようにする。"""
        self._refresh_visible_text()
        self._queue_visible_text_refresh()

    def select_all_and_stabilize_visible_text(self) -> None:
        """全文を選択し、Qtの選択状態が更新された後にレイアウトを整える。"""
        self._preserve_full_selection_on_focus_out = True
        self.selectAll()
        self.highlighter.rehighlight()
        self._refresh_visible_text()
        self._queue_visible_text_refresh()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """キー入力を処理し、Enterキーで `returnPressed` を通知する。"""
        if event.key() in {QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter} and not (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier
        ):
            self.returnPressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)
        self._queue_visible_text_refresh()

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        """入力欄にフォーカスが戻ったときに表示を整える。"""
        super().focusInEvent(event)
        self._update_highlighter_text_color()
        self._queue_visible_text_refresh()

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        """フォーカスが外れるとき、全文選択中ならカーソルを末尾に移す。"""
        super().focusOutEvent(event)
        cursor = self.textCursor()
        if (
            not self._preserve_full_selection_on_focus_out
            and cursor.hasSelection()
            and cursor.selectionStart() == 0
            and cursor.selectionEnd() == len(self.toPlainText())
        ):
            cursor.setPosition(cursor.selectionEnd())
            self.setTextCursor(cursor)
        self._preserve_full_selection_on_focus_out = False
        self._queue_visible_text_refresh()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """マウス選択の後に残る横スクロール位置を調整する。"""
        super().mouseReleaseEvent(event)
        self._queue_visible_text_refresh()

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        """選択中の自動スクロールが文書の外まで進まないようにする。"""
        super().scrollContentsBy(dx, dy)
        self._restore_valid_scroll_position()

    def _restore_valid_scroll_position(self) -> None:
        """表示領域が全テキストブロックの外まで移動した場合にスクロール位置を戻す。"""
        if not self.firstVisibleBlock().isValid():
            scroll_bar = self.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.minimum())
            self.viewport().update()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """入力欄の幅が変わったときに、折り返しを含む行の高さを測り直す。"""
        super().resizeEvent(event)
        self._refresh_height_for_content()

    def _refresh_height_for_content(self, *_args: object) -> None:
        """見えている行に合わせて、上限内で入力欄の高さを調整する。"""
        if self._refreshing_height:
            return
        self._refreshing_height = True
        try:
            self._fit_visible_height()
        finally:
            self._refreshing_height = False

    def _fit_visible_height(self) -> None:
        """見える行数に応じて入力欄の高さを調整する。"""
        visual_line_count = max(1, math.ceil(self.document().size().height()))
        visible_line_count = min(
            max(visual_line_count, self.MINIMUM_VISIBLE_LINES),
            self.MAXIMUM_VISIBLE_LINES,
        )
        if visible_line_count == self._visible_line_count:
            return
        self._visible_line_count = visible_line_count
        self.setFixedHeight(self._visible_text_height())
        self.updateGeometry()

    def _queue_visible_text_refresh(self) -> None:
        """現在の入力イベントやフォーカスイベントが終わった後に表示を更新する。"""
        if self._refreshing_visible_text:
            return
        self._refreshing_visible_text = True
        try:
            self._refresh_visible_text()
        finally:
            self._refreshing_visible_text = False

    def _refresh_visible_text(self) -> None:
        """選択、フォーカス、色付けの変更後も入力文字列が見えるようにする。"""
        self._restore_valid_scroll_position()
        self.ensureCursorVisible()
        self.horizontalScrollBar().setValue(0)
        self.viewport().update()
        self.updateGeometry()

    def _update_highlighter_text_color(self) -> None:
        """構文の色付けを有効にしても、正規表現要素以外の文字が読みやすい色にする。"""
        palette = self.palette()
        text_color = palette.color(QtGui.QPalette.ColorRole.Text)
        base_color = palette.color(QtGui.QPalette.ColorRole.Base)
        if text_color == base_color:
            text_color = (
                QtGui.QColor("#202124")
                if base_color.lightness() > 127
                else QtGui.QColor("#f8f9fa")
            )
        self.highlighter.set_normal_foreground(text_color)
