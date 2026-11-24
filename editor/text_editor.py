# pylint: disable=E0611,W0611,C0301,C0103
"""メインのテキストエディタウィジェットを提供するモジュール"""
from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtCore import (
    QEvent,
    QObject,
    QRect,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QSyntaxHighlighter,
    QTextBlock,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextOption,
    QWheelEvent,
)
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QTextEdit

from editor.line_number_area import LineNumberArea
from editor.search_marker_area import SearchMarkerArea
from search.search_engine import SearchMatch


@dataclass(frozen=True)
class VisibleWhitespaceMark:
    """スペースの可視化マークの位置とマーク文字を表すデータクラス"""
    text_position: int
    marker: str


class HtmlSyntaxHighlighter(QSyntaxHighlighter):
    """HTMLの構文を強調表示するためのQSyntaxHighlighterのサブクラス"""
    NORMAL = 0
    TAG = 1
    SINGLE_QUOTED_ATTRIBUTE = 2
    DOUBLE_QUOTED_ATTRIBUTE = 3
    COMMENT = 4
    WORDPRESS_COMMENT = 5
    TAG_START: re.Pattern[str] = re.compile(r"</?[A-Za-z][A-Za-z0-9:-]*(?=[\s/>]|$)")
    WORDPRESS_COMMENT_START: re.Pattern[str] = re.compile(r"<!--\s*/?wp:")

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self.enabled = True
        self.tag_format = QTextCharFormat()
        self.tag_format.setForeground(QColor("#0b5cad"))
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#667085"))

    def set_tag_color(self, color_code: str) -> None:
        """HTMLタグの色を設定するメソッド"""
        color = QColor(color_code)
        self.tag_format.setForeground(color if color.isValid() else QColor("#0b5cad"))
        self.rehighlight()

    def set_core_block_color(self, color_code: str) -> None:
        """WordPressのコアブロックコメントの色を設定するメソッド"""
        color = QColor(color_code)
        self.comment_format.setForeground(
            color if color.isValid() else QColor("#667085")
        )
        self.rehighlight()

    def set_enabled(self, enabled: bool) -> None:
        """構文強調表示の有効/無効を設定するメソッド"""
        self.enabled: bool = enabled
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:  # pylint: disable=invalid-name
        """テキストブロックを強調表示するメソッド"""
        self.setCurrentBlockState(self.NORMAL)
        if not self.enabled:
            return
        state: int = max(self.previousBlockState(), self.NORMAL)
        # QTextLayout indexes UTF-16 code units, unlike Python string indexes.
        offsets: list[int] = [0]
        for character in text:
            offsets.append(offsets[-1] + (2 if ord(character) > 0xFFFF else 1))
        position: int = 0
        while position < len(text):
            if state in {self.TAG, self.SINGLE_QUOTED_ATTRIBUTE, self.DOUBLE_QUOTED_ATTRIBUTE}:
                end, state = self._tag_end(text, position, state)
                self.setFormat(offsets[position], offsets[end] - offsets[position], self.tag_format)
                position = end
                continue
            if state in {self.COMMENT, self.WORDPRESS_COMMENT}:
                closing: int = text.find("-->", position)
                end: int = closing + 3 if closing >= 0 else len(text)
                if state == self.WORDPRESS_COMMENT:
                    self.setFormat(offsets[position], offsets[end] - offsets[position], self.comment_format)
                position = end
                if closing >= 0:
                    state = self.NORMAL
                continue
            position: int = text.find("<", position)
            if position < 0:
                break
            if text.startswith("<!--", position):
                state = (
                    self.WORDPRESS_COMMENT if self.WORDPRESS_COMMENT_START.match(text, position)
                    else self.COMMENT
                )
            elif self.TAG_START.match(text, position):
                state = self.TAG
            else:
                position += 1
        self.setCurrentBlockState(state)

    def _tag_end(self, text: str, start: int, state: int) -> tuple[int, int]:
        """固有タグの終了位置を見つけるためのヘルパーメソッド"""
        for position in range(start, len(text)):
            character: str = text[position]
            if state == self.SINGLE_QUOTED_ATTRIBUTE:
                if character == "'":
                    state = self.TAG
            elif state == self.DOUBLE_QUOTED_ATTRIBUTE:
                if character == '"':
                    state = self.TAG
            elif character == "'":
                state = self.SINGLE_QUOTED_ATTRIBUTE
            elif character == '"':
                state = self.DOUBLE_QUOTED_ATTRIBUTE
            elif character == ">":
                return position + 1, self.NORMAL
        return len(text), state


class TextEditor(QPlainTextEdit):
    """テキストエディタウィジェットを提供するクラス"""
    line_head_selection_width = 8

    def __init__(self) -> None:
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.search_marker_area = SearchMarkerArea(self)
        self.line_number_area.installEventFilter(self)
        self.search_marker_area.installEventFilter(self)
        self.line_numbers_enabled = True
        self.search_matches: list[SearchMatch] = []
        self.search_exclusion_matches: list[SearchMatch] = []
        self.search_scope_bounds: tuple[int, int] | None = None
        self._highlight_selection_bounds: tuple[int, int] | None = None
        self.search_marker_color = "#ffff00"
        self.current_match_marker_color = "#ff9900"
        self.search_scope_marker_color = "#dcecff"
        self.grammar_issue_lines: list[int] = []
        self.grammar_issue_background_color = "#ffe3e3"
        self.visible_spaces_enabled = False
        self.visible_tabs_enabled = False
        self.visible_newlines_enabled = False
        self.visible_space_marker_color = "#9a9a9a"
        self.visible_tab_marker_color = "#9ed8ff"
        self.visible_newline_marker_color = "#ff9900"
        self.word_wrap_enabled = False
        self.fixed_column_wrap_enabled = False
        self.fixed_column_wrap_column = 80
        self.editor_background_color = "#ffffff"
        self.editor_text_color = "#202124"
        self.html_tag_color = "#0b5cad"
        self.wordpress_core_block_color = "#667085"
        self.html_highlighter = HtmlSyntaxHighlighter(self.document())

        self.setFont(QFont("Consolas", 11))
        self._apply_editor_colors()
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self._apply_search_highlights)
        self.update_editor_margins()

    def set_word_wrap_enabled(self, enabled: bool) -> None:
        """ワードラップの有効/無効を設定するメソッド"""
        self.word_wrap_enabled: bool = enabled
        self._apply_line_wrap_mode()

    def set_fixed_column_wrap_options(self, *, enabled: bool, column: int) -> None:
        """固定カラムラップの有効/無効とカラム数を設定するメソッド"""
        self.fixed_column_wrap_enabled: bool = enabled
        self.fixed_column_wrap_column: int = max(1, column)
        self._apply_line_wrap_mode()
        self.update_editor_margins()
        self.viewport().update()

    def set_editor_colors(
        self,
        *,
        background_color: str,
        text_color: str,
        html_tag_color: str,
        wordpress_core_block_color: str = "#667085",
    ) -> None:
        """エディタの色を設定するメソッド"""
        self.editor_background_color: str = _valid_color_or_default(
            background_color,
            "#ffffff",
        )
        self.editor_text_color: str = _valid_color_or_default(text_color, "#202124")
        self.html_tag_color: str = _valid_color_or_default(html_tag_color, "#0b5cad")
        self.wordpress_core_block_color: str = _valid_color_or_default(
            wordpress_core_block_color,
            "#667085",
        )
        self._apply_editor_colors()
        self.html_highlighter.set_tag_color(self.html_tag_color)
        self.html_highlighter.set_core_block_color(self.wordpress_core_block_color)

    def _apply_editor_colors(self) -> None:
        """エディタの背景色とテキスト色を適用するヘルパーメソッド"""
        self.setStyleSheet(
            "QPlainTextEdit {"
            f" background-color: {self.editor_background_color};"
            f" color: {self.editor_text_color};"
            "}"
        )

    def _apply_line_wrap_mode(self) -> None:
        """行ラップモードを適用するヘルパーメソッド"""
        enabled: bool = self.word_wrap_enabled or self.fixed_column_wrap_enabled
        wrap_mode: QPlainTextEdit.LineWrapMode = (
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if enabled
            else QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.setLineWrapMode(wrap_mode)
        self.setWordWrapMode(
            QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
            if enabled
            else QTextOption.WrapMode.NoWrap
        )

    def set_line_numbers_enabled(self, enabled: bool) -> None:
        """行番号の有効/無効を設定するメソッド"""
        self.line_numbers_enabled: bool = enabled
        self.line_number_area.setVisible(enabled)
        self.update_line_number_area_width()

    def line_number_area_size_hint(self) -> QSize:
        """行番号エリアのサイズヒントを返すメソッド"""
        return QSize(self.line_number_area_width(), 0)

    def line_number_area_width(self) -> int:
        """行番号エリアの幅を返すメソッド"""
        if not self.line_numbers_enabled:
            return 0

        digits: int = len(str(max(1, self.blockCount())))
        space_width: int = self.fontMetrics().horizontalAdvance("9") * digits
        return 12 + space_width

    def search_marker_area_width(self) -> int:
        """検索マーカーエリアの幅を返すメソッド"""
        return 10

    def update_line_number_area_width(self) -> None:
        """行番号エリアの幅を更新するメソッド"""
        self.update_editor_margins()

    def update_editor_margins(self) -> None:
        """エディタのマージンを更新するメソッド"""
        left_margin: int = self.line_number_area_width()
        right_margin: int = self.search_marker_area_width() + self._fixed_wrap_extra_margin()
        self.setViewportMargins(
            left_margin,
            0,
            right_margin,
            0,
        )

    def _fixed_wrap_extra_margin(self) -> int:
        """固定カラムラップのための追加マージンを計算するヘルパーメソッド"""
        if not self.fixed_column_wrap_enabled:
            return 0

        content_width: int = self.contentsRect().width()
        available_text_width: int = max(
            0,
            content_width - self.line_number_area_width() - self.search_marker_area_width(),
        )
        target_text_width: int = self.fixed_column_wrap_pixel_width()
        return max(0, available_text_width - target_text_width)

    def fixed_column_wrap_pixel_width(self) -> int:
        """固定カラムラップのピクセル幅を計算するヘルパーメソッド"""
        return max(
            1,
            self.fontMetrics().horizontalAdvance("0") * self.fixed_column_wrap_column,
        )

    def fixed_column_wrap_line_x(self) -> int | None:
        """固定カラムラップのガイドラインのX座標を計算するヘルパーメソッド"""
        if not self.fixed_column_wrap_enabled:
            return None

        horizontal_offset: int = self.horizontalScrollBar().value()
        x_position: int = self.fixed_column_wrap_pixel_width() - horizontal_offset
        if x_position < 0 or x_position > self.viewport().width():
            return None
        return min(x_position, max(0, self.viewport().width() - 1))

    def update_line_number_area(self, rect: QRect, vertical_delta: int) -> None:
        """行番号エリアを更新するメソッド"""
        if vertical_delta:
            self.line_number_area.scroll(0, vertical_delta)
        else:
            self.line_number_area.update(
                0,
                rect.y(),
                self.line_number_area.width(),
                rect.height(),
            )

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()
        self.search_marker_area.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """リサイズイベントを処理するメソッド"""
        super().resizeEvent(event)
        content_rect: QRect = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(
                content_rect.left(),
                content_rect.top(),
                self.line_number_area_width(),
                content_rect.height(),
            )
        )
        marker_width: int = self.search_marker_area_width()
        self.search_marker_area.setGeometry(
            QRect(
                content_rect.right() - marker_width + 1,
                content_rect.top(),
                marker_width,
                content_rect.height(),
            )
        )

    def event(self, event: QEvent) -> bool:
        """Scroll over the blank margin created by fixed-column wrapping."""
        if (
            event.type() == QEvent.Type.Wheel
            and getattr(self, "fixed_column_wrap_enabled", False)
            and isinstance(event, QWheelEvent)
            and (event.angleDelta().y() or event.pixelDelta().y())
            and not self.viewport().geometry().contains(event.position().toPoint())
        ):
            QApplication.sendEvent(self.verticalScrollBar(), event)
            return event.isAccepted()
        return super().event(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Allow wheel scrolling while the pointer is on either side area."""
        if (
            watched in (self.line_number_area, self.search_marker_area)
            and event.type() == QEvent.Type.Wheel
            and isinstance(event, QWheelEvent)
            and (event.angleDelta().y() or event.pixelDelta().y())
        ):
            QApplication.sendEvent(self.verticalScrollBar(), event)
            return event.isAccepted()
        return super().eventFilter(watched, event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """ペイントイベントを処理するメソッド"""
        super().paintEvent(event)
        self._paint_fixed_column_wrap_guide(event)
        self._paint_visible_whitespace(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """マウスプレスイベントを処理するメソッド"""
        if (
            not self.line_numbers_enabled
            and event.button() == Qt.MouseButton.LeftButton
            and event.position().x() <= self.line_head_selection_width
        ):
            self.select_line_at_view_y(round(event.position().y()))
            event.accept()
            return
        super().mousePressEvent(event)

    def select_line_at_view_y(self, y_position: int) -> None:
        """指定されたY座標にある行を選択するメソッド"""
        block: QTextBlock = self._visible_block_at_y(y_position)
        if not block.isValid():
            return

        cursor = QTextCursor(block)
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        self.setTextCursor(cursor)
        self.setFocus()

    def _visible_block_at_y(self, y_position: int) -> QTextBlock:
        """指定されたY座標にある可視ブロックを取得するヘルパーメソッド"""
        block: QTextBlock = self.firstVisibleBlock()
        top: int = round(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset())
            .top()
        )
        bottom: int = top + round(self.blockBoundingRect(block).height())

        while block.isValid():
            if block.isVisible() and top <= y_position < bottom:
                return block
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
        return block

    def _paint_fixed_column_wrap_guide(self, event: QPaintEvent) -> None:
        """固定カラムラップのガイドラインを描画するヘルパーメソッド"""
        line_x = self.fixed_column_wrap_line_x()
        if line_x is None:
            return

        painter = QPainter(self.viewport())
        painter.setPen(QColor("#1f9d55"))
        painter.drawLine(line_x, event.rect().top(), line_x, event.rect().bottom())

    def set_search_matches(
        self,
        matches: list[SearchMatch],
        exclusion_matches: list[SearchMatch] | None = None,
        scope_bounds: tuple[int, int] | None = None,
    ) -> None:
        """検索マッチのリストを設定するメソッド"""
        self.search_matches = matches
        self.search_exclusion_matches = exclusion_matches or []
        self.search_scope_bounds = scope_bounds
        self._apply_extra_selections()
        self.search_marker_area.update()

    def clear_search_matches(self) -> None:
        """検索マッチをクリアするメソッド"""
        self.set_search_matches([], [], None)

    def set_search_marker_colors(
        self,
        search_marker_color: str,
        current_match_marker_color: str,
    ) -> None:
        """検索マーカーの色を設定するメソッド"""
        self.search_marker_color: str = search_marker_color
        self.current_match_marker_color: str = current_match_marker_color
        self._apply_extra_selections()
        self.search_marker_area.update()

    def set_grammar_issue_lines(self, line_numbers: list[int]) -> None:
        """文法エラーの行番号リストを設定するメソッド"""
        self.grammar_issue_lines = sorted(
            {line_number for line_number in line_numbers if line_number > 0}
        )
        self._apply_extra_selections()

    def clear_grammar_issue_lines(self) -> None:
        """文法エラーの行番号リストをクリアするメソッド"""
        if not self.grammar_issue_lines:
            return
        self.grammar_issue_lines = []
        self._apply_extra_selections()

    def set_visible_whitespace_options(
        self,
        *,
        spaces_enabled: bool,
        tabs_enabled: bool,
        newlines_enabled: bool,
    ) -> None:
        """可視化する空白文字のオプションを設定するメソッド"""
        self.visible_spaces_enabled: bool = spaces_enabled
        self.visible_tabs_enabled: bool = tabs_enabled
        self.visible_newlines_enabled: bool = newlines_enabled
        self.viewport().update()

    def set_visible_whitespace_marker_colors(
        self,
        *,
        space_color: str,
        tab_color: str,
        newline_color: str,
    ) -> None:
        """可視化する空白文字のマーカー色を設定するメソッド"""
        self.visible_space_marker_color: str = space_color
        self.visible_tab_marker_color: str = tab_color
        self.visible_newline_marker_color: str = newline_color
        self.viewport().update()

    def visible_whitespace_marks(self) -> list[VisibleWhitespaceMark]:
        """可視化する空白文字の位置とマーカーを取得するメソッド"""
        source_text: str = self.toPlainText()
        marks: list[VisibleWhitespaceMark] = []
        for text_position, character in enumerate(source_text):
            marker = self._visible_whitespace_marker(character)
            if marker is not None:
                marks.append(VisibleWhitespaceMark(text_position, marker))
        return marks

    def _visible_whitespace_marker(self, character: str) -> str | None:
        """指定された文字に対応する可視化マーカーを取得するヘルパーメソッド"""
        if self.visible_spaces_enabled:
            if character == " ":
                return "·"
            if character == "\u3000":
                return "□"
        if self.visible_tabs_enabled and character == "\t":
            return "→"
        if self.visible_newlines_enabled and character == "\n":
            return "↵"
        return None

    def _paint_visible_whitespace(self, event: QPaintEvent) -> None:
        """可視化する空白文字を描画するヘルパーメソッド"""
        if not (
            self.visible_spaces_enabled
            or self.visible_tabs_enabled
            or self.visible_newlines_enabled
        ):
            return

        painter = QPainter(self.viewport())
        painter.setFont(self.font())

        block: QTextBlock = self.firstVisibleBlock()
        top: int = round(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset())
            .top()
        )
        bottom: int = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                self._paint_block_visible_whitespace(
                    painter,
                    event.rect(),
                    block,
                )

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())

    def _paint_block_visible_whitespace(
        self,
        painter: QPainter,
        event_rect: QRect,
        block: QTextBlock,
    ) -> None:
        """指定されたブロック内の可視化する空白文字を描画するヘルパーメソッド"""
        cursor_position = block.position()
        for character in block.text():
            marker = self._visible_whitespace_marker(character)
            if marker is not None:
                self._paint_visible_whitespace_marker(
                    painter,
                    event_rect,
                    cursor_position,
                    marker,
                    character,
                )
            cursor_position += 2 if ord(character) > 0xFFFF else 1

        if block.next().isValid():
            marker = self._visible_whitespace_marker("\n")
            if marker is not None:
                self._paint_visible_whitespace_marker(
                    painter,
                    event_rect,
                    cursor_position,
                    marker,
                    "\n",
                )

    def _paint_visible_whitespace_marker(
        self,
        painter: QPainter,
        event_rect: QRect,
        cursor_position: int,
        marker: str,
        character: str,
    ) -> None:
        """指定された位置に可視化する空白文字のマーカーを描画するヘルパーメソッド"""
        cursor = QTextCursor(self.document())
        cursor.setPosition(cursor_position)
        marker_rect: QRect = self.cursorRect(cursor)

        if not marker_rect.intersects(
            event_rect.adjusted(-20, -20, 20, 20)
            ):
            return

        painter.setFont(self.font())
        painter.setPen(
            QColor(
                self._visible_whitespace_marker_color(character)
                )
            )

        if character != "\n":
            next_cursor = QTextCursor(self.document())
            next_cursor.setPosition(cursor_position + 1)
            next_rect: QRect = self.cursorRect(next_cursor)

            # 同じ表示行なら、現在位置～次文字位置を
            # 実際の1文字分の描画領域として使用する。
            if next_rect.top() == marker_rect.top():
                width: int = next_rect.left() - marker_rect.left()

                if width > 0:
                    marker_rect.setWidth(width)

        if character == "\n":
            marker_rect.translate(2, 0)
            marker_rect.setWidth(
                max(
                    marker_rect.width(),
                    self.fontMetrics().height(),
                )
            )
            alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        elif character == "\t":
            # 上で取得できなかった場合だけfallback
            if marker_rect.width() <= 1:
                marker_rect.setWidth(round(self.tabStopDistance()))

            alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        else:
            # 半角・全角スペース
            if marker_rect.width() <= 1:
                marker_rect.setWidth(
                    max(
                        1,
                        self.fontMetrics().horizontalAdvance(character),
                    )
                )

            alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter

        painter.drawText(marker_rect, alignment, marker)

    def _visible_whitespace_marker_color(self, character: str) -> str:
        """指定された文字に対応する可視化マーカーの色を取得するヘルパーメソッド"""
        if character == "\t":
            return self.visible_tab_marker_color
        if character == "\n":
            return self.visible_newline_marker_color
        return self.visible_space_marker_color

    def _apply_search_highlights(self) -> None:
        """検索マッチのハイライトを適用するヘルパーメソッド"""
        if not self.search_matches:
            return
        cursor = self.textCursor()
        bounds = (
            (cursor.selectionStart(), cursor.selectionEnd())
            if cursor.hasSelection()
            else None
        )
        if bounds != self._highlight_selection_bounds:
            self._apply_extra_selections()

    def _apply_extra_selections(self) -> None:
        """文法エラーと検索マッチのハイライトを適用するヘルパーメソッド"""
        cursor = self.textCursor()
        self._highlight_selection_bounds = (
            (cursor.selectionStart(), cursor.selectionEnd())
            if cursor.hasSelection()
            else None
        )
        selections: list[QTextEdit.ExtraSelection] = self._grammar_issue_selections()
        position_map = self._search_cursor_positions()
        scope_selection = self._search_scope_selection(position_map)
        if scope_selection is not None:
            selections.append(scope_selection)
        selections.extend(self._search_match_selections(position_map))
        self.setExtraSelections(selections)

    def _search_cursor_positions(self) -> dict[int, int]:
        """Convert marker offsets to Qt UTF-16 positions in one document pass."""
        positions: set[int] = set()
        if self.search_scope_bounds is not None:
            positions.update(self.search_scope_bounds)
        for match in (*self.search_matches[:1000], *self.search_exclusion_matches[:1000]):
            positions.update((match.start, match.end))
        if not positions:
            return {}
        source_text = self.toPlainText()
        position_map: dict[int, int] = {}
        previous_text_position = 0
        cursor_position = 0
        for text_position in sorted(positions):
            bounded_position = min(max(text_position, 0), len(source_text))
            cursor_position += len(
                source_text[previous_text_position:bounded_position].encode("utf-16-le")
            ) // 2
            position_map[text_position] = cursor_position
            previous_text_position = bounded_position
        return position_map

    def _search_scope_selection(
        self, position_map: dict[int, int]
    ) -> QTextEdit.ExtraSelection | None:
        """Create the retained selected-range highlight used during scoped search."""
        if self.search_scope_bounds is None:
            return None
        scope_start, scope_end = self.search_scope_bounds
        if scope_start >= scope_end:
            return None

        scope_format = QTextCharFormat()
        scope_format.setBackground(QColor(self.search_scope_marker_color))
        scope_cursor = QTextCursor(self.document())
        scope_cursor.setPosition(position_map[scope_start])
        scope_cursor.setPosition(
            position_map[scope_end],
            QTextCursor.MoveMode.KeepAnchor,
        )
        selection = QTextEdit.ExtraSelection()
        selection.format = scope_format
        selection.cursor = scope_cursor
        return selection

    def _grammar_issue_selections(self) -> list[QTextEdit.ExtraSelection]:
        """文法エラーの行に対するハイライトを適用するヘルパーメソッド"""
        issue_format = QTextCharFormat()
        issue_format.setBackground(QColor(self.grammar_issue_background_color))
        issue_format.setProperty(QTextFormat.Property.FullWidthSelection, True)

        selections: list[QTextEdit.ExtraSelection] = []
        for line_number in self.grammar_issue_lines:
            block: QTextBlock = self.document().findBlockByNumber(line_number - 1)
            if not block.isValid():
                continue
            cursor: QTextCursor = QTextCursor(block)
            selection: QTextEdit.ExtraSelection = QTextEdit.ExtraSelection()
            selection.format = issue_format
            selection.cursor = cursor
            selections.append(selection)
        return selections

    def _search_match_selections(
        self, position_map: dict[int, int]
    ) -> list[QTextEdit.ExtraSelection]:
        """検索マッチに対するハイライトを適用するヘルパーメソッド"""
        highlight_format: QTextCharFormat = QTextCharFormat()
        highlight_format.setBackground(QColor(self.search_marker_color))
        current_highlight_format: QTextCharFormat = QTextCharFormat()
        current_highlight_format.setBackground(QColor(self.current_match_marker_color))
        exclusion_highlight_format: QTextCharFormat = QTextCharFormat()
        exclusion_highlight_format.setBackground(QColor(self.current_match_marker_color))

        selections: list[QTextEdit.ExtraSelection] = []
        cursor: QTextCursor = self.textCursor()
        selection_start: int = self.cursor_position_to_text_position(cursor.selectionStart())
        selection_end: int = self.cursor_position_to_text_position(cursor.selectionEnd())
        for match in self.search_matches[:1000]:
            if match.start == match.end:
                continue
            selection: QTextEdit.ExtraSelection = QTextEdit.ExtraSelection()
            selection.format = (
                current_highlight_format
                if match.start == selection_start and match.end == selection_end
                else highlight_format
            )
            match_cursor: QTextCursor = QTextCursor(self.document())
            match_cursor.setPosition(position_map[match.start])
            match_cursor.setPosition(
                position_map[match.end],
                QTextCursor.MoveMode.KeepAnchor,
            )
            selection.cursor = match_cursor
            selections.append(selection)
        for match in self.search_exclusion_matches[:1000]:
            if match.start == match.end:
                continue
            selection: QTextEdit.ExtraSelection = QTextEdit.ExtraSelection()
            selection.format = exclusion_highlight_format
            match_cursor: QTextCursor = QTextCursor(self.document())
            match_cursor.setPosition(position_map[match.start])
            match_cursor.setPosition(
                position_map[match.end],
                QTextCursor.MoveMode.KeepAnchor,
            )
            selection.cursor = match_cursor
            selections.append(selection)
        return selections

    def text_position_to_cursor_position(self, text_position: int) -> int:
        """テキスト位置をカーソル位置に変換するメソッド"""
        source_text: str = self.toPlainText()
        bounded_position: int = min(max(text_position, 0), len(source_text))
        return len(source_text[:bounded_position].encode("utf-16-le")) // 2

    def cursor_position_to_text_position(self, cursor_position: int) -> int:
        """カーソル位置をテキスト位置に変換するメソッド"""
        source_text: str = self.toPlainText()
        bounded_position: int = max(cursor_position, 0)
        utf16_position: int = 0
        for text_position, character in enumerate(source_text):
            character_width = 2 if ord(character) > 0xFFFF else 1
            if utf16_position + character_width > bounded_position:
                return text_position
            utf16_position += character_width
        return len(source_text)

    def paint_line_number_area(self, event: QPaintEvent) -> None:
        """行番号エリアを描画するメソッド"""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#f3f3f3"))

        block: QTextBlock = self.firstVisibleBlock()
        block_number: int = block.blockNumber()
        top: int = round(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset())
            .top()
        )
        bottom: int = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number: str = str(block_number + 1)
                painter.setPen(QColor("#606060"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def paint_search_marker_area(self, event: QPaintEvent) -> None:
        """検索マーカーエリアを描画するメソッド"""
        painter = QPainter(self.search_marker_area)
        painter.fillRect(event.rect(), QColor("#f7f7f7"))
        if not self.search_matches:
            return

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.search_marker_color))
        area_width: int = self.search_marker_area.width()
        area_height: int = max(1, self.search_marker_area.height())
        block_count: int = max(1, self.blockCount())
        marked_lines: set[int] = {
            self.document().findBlock(match.start).blockNumber()
            for match in self.search_matches
            if match.start != match.end
        }
        for line_number in marked_lines:
            marker_y: int = round((line_number / block_count) * area_height)
            painter.drawRect(2, marker_y, area_width - 4, 3)


def _valid_color_or_default(color_code: str, default: str) -> str:
    """指定された色コードが有効かどうかを確認し、有効であればその色コードを返し、無効であればデフォルトの色コードを返すヘルパーメソッド"""
    color = QColor(color_code)
    if color.isValid():
        return color.name()
    return default
