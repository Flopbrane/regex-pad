# pylint: disable=C0301,I1101,C0103
"""Regex input widget with lightweight regex highlighting."""

from __future__ import annotations

import math
import re

from PySide6 import QtCore, QtGui, QtWidgets

REGEX_TOKEN_COLOR = QtGui.QColor("#7a4a12")


class RegexInputHighlighter(QtGui.QSyntaxHighlighter):
    """Syntax highlighter for regex input."""
    def __init__(self, document: QtGui.QTextDocument) -> None:
        super().__init__(document)
        self.enabled = False
        self.normal_format = QtGui.QTextCharFormat()
        self._normal_foreground_color = QtGui.QColor()
        self.regex_format = QtGui.QTextCharFormat()
        self.regex_format.setForeground(REGEX_TOKEN_COLOR)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable regex highlighting."""
        self.enabled = enabled
        self.rehighlight()

    def set_normal_foreground(self, color: QtGui.QColor) -> None:
        """Set the foreground color used for non-highlighted regex text."""
        if color == self._normal_foreground_color:
            return
        self._normal_foreground_color = QtGui.QColor(color)
        self.normal_format.setForeground(color)
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        """Highlight regex tokens in the given text block."""
        if not self.enabled:
            return

        if text:
            self.setFormat(0, len(text), self.normal_format)
        for start, length in self._regex_token_ranges(text):
            self.setFormat(start, length, self.regex_format)

    def _regex_token_ranges(self, text: str) -> list[tuple[int, int]]:
        """Return a list of (start, length) tuples for regex tokens in the given text."""
        ranges: list[tuple[int, int]] = []
        ranges.extend(self._match_ranges(r"\\[AbBdDsSwWZzGnrtfv](?:[*+?]|\{\d+(?:,\d*)?\})?\??", text))
        ranges.extend(self._group_ranges(text))
        ranges.extend(self._match_ranges(r"(?<!\\)\.(?:[*+?]|\{\d+(?:,\d*)?\})?\??", text))
        ranges.extend(self._match_ranges(r"(?<!\\)(?:\^|\$|\|)", text))
        ranges.extend(self._match_ranges(r"(?<!\\)(?:[*+?]|\{\d+(?:,\d*)?\})\??", text))
        ranges.extend(self._match_ranges(r"(?:\\g<[^>]+>|\\[1-9]\d*|\$\d+|\$\{[A-Za-z_]\w*\})", text))
        return self._merge_ranges(ranges)

    def _match_ranges(self, pattern: str, text: str) -> list[tuple[int, int]]:
        """Return a list of (start, length) tuples for matches of the given regex pattern in the text."""
        return [(match.start(), match.end() - match.start()) for match in re.finditer(pattern, text)]

    def _group_ranges(self, text: str) -> list[tuple[int, int]]:
        """Return a list of (start, length) tuples for regex groups in the text."""
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
        """Merge overlapping or adjacent ranges."""
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
    """Plain text edit widget for regex input with lightweight regex highlighting."""
    returnPressed = QtCore.Signal()
    MINIMUM_VISIBLE_LINES = 1
    MAXIMUM_VISIBLE_LINES = 5

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTabChangesFocus(True)
        self._visible_line_count = self.MINIMUM_VISIBLE_LINES
        self._height_refresh_queued = False
        self.setFixedHeight(self._visible_text_height())
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.highlighter = RegexInputHighlighter(self.document())
        self._visible_text_refresh_queued = False
        self._preserve_full_selection_on_focus_out = False
        self.textChanged.connect(self._queue_height_refresh)
        self._update_highlighter_text_color()

    def sizeHint(self) -> QtCore.QSize:
        """Return the preferred size with enough height to keep blank lines visible."""
        size = super().sizeHint()
        return QtCore.QSize(size.width(), self._visible_text_height())

    def minimumSizeHint(self) -> QtCore.QSize:
        """Return the minimum size with surrounding lines visible."""
        size = super().minimumSizeHint()
        return QtCore.QSize(size.width(), self._visible_text_height())

    def _visible_text_height(self) -> int:
        """Return the height needed for the configured visible line count."""
        metrics = self.fontMetrics()
        line_height = max(metrics.height(), metrics.lineSpacing())
        margins = math.ceil(self.document().documentMargin() * 2)
        # Include the actual frame and a rounding allowance. An exact-fit
        # viewport can acquire an extra scroll step on the Windows 11 style.
        return line_height * self._visible_line_count + margins + self.frameWidth() * 2 + 2

    def text(self) -> str:
        """Return the current text in the widget."""
        return self.toPlainText()

    def setText(self, text: str) -> None:
        """Set the text in the widget."""
        self.setPlainText(text)
        self._queue_visible_text_refresh()

    def insert(self, text: str) -> None:
        """Insert text at the current cursor position."""
        self.textCursor().insertText(text)
        self._queue_visible_text_refresh()

    def selectionStart(self) -> int:
        """Return the start position of the current selection."""
        return self.textCursor().selectionStart()

    def hasSelectedText(self) -> bool:
        """Return whether the widget has selected text."""
        return self.textCursor().hasSelection()

    def cursorPosition(self) -> int:
        """Return the current cursor position."""
        return self.textCursor().position()

    def setCursorPosition(self, position: int) -> None:
        """Set the current cursor position."""
        cursor = self.textCursor()
        cursor.setPosition(position)
        self.setTextCursor(cursor)
        self._queue_visible_text_refresh()

    def setSelection(self, start: int, length: int) -> None:
        """Set the selection range in the widget."""
        cursor: QtGui.QTextCursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(start + length, cursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
        self._queue_visible_text_refresh()

    def set_regex_highlighting_enabled(self, enabled: bool) -> None:
        """Enable or disable regex highlighting."""
        self._update_highlighter_text_color()
        self.highlighter.set_enabled(enabled)
        self._queue_visible_text_refresh()

    def stabilize_visible_text(self) -> None:
        """Refresh layout and keep the current text visible."""
        self._refresh_visible_text()
        self._queue_visible_text_refresh()

    def select_all_and_stabilize_visible_text(self) -> None:
        """Select all text and refresh layout after Qt updates the selection."""
        self._preserve_full_selection_on_focus_out = True
        self.selectAll()
        self.highlighter.rehighlight()
        self._refresh_visible_text()
        self._queue_visible_text_refresh()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle key press events, emitting returnPressed signal on Enter key."""
        if event.key() in {QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter} and not (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier
        ):
            self.returnPressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)
        self._queue_visible_text_refresh()

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        """Refresh the visible text when the editor regains focus."""
        super().focusInEvent(event)
        self._update_highlighter_text_color()
        self._queue_visible_text_refresh()

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        """Handle focus out events, moving cursor to end if all text is selected."""
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
        """Refresh after mouse selection, where hidden horizontal scrolling can linger."""
        super().mouseReleaseEvent(event)
        self._queue_visible_text_refresh()

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        """Keep selection autoscrolling from leaving the document entirely."""
        super().scrollContentsBy(dx, dy)
        self._restore_valid_scroll_position()

    def _restore_valid_scroll_position(self) -> None:
        """Recover only when the viewport has scrolled beyond every text block."""
        if not self.firstVisibleBlock().isValid():
            scroll_bar = self.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.minimum())
            self.viewport().update()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Recalculate wrapped line height when the input width changes."""
        super().resizeEvent(event)
        self._queue_height_refresh()

    def _queue_height_refresh(self) -> None:
        """Queue a height update after Qt finishes the document layout."""
        if self._height_refresh_queued:
            return
        self._height_refresh_queued = True
        QtCore.QTimer.singleShot(0, self._refresh_height_for_content)

    def _refresh_height_for_content(self) -> None:
        """Fit the input to its visual lines, capped to keep the dialog compact."""
        self._height_refresh_queued = False
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
        """Queue a viewport refresh after Qt finishes cursor, selection, and layout updates."""
        if self._visible_text_refresh_queued:
            return
        self._visible_text_refresh_queued = True
        QtCore.QTimer.singleShot(0, self._refresh_visible_text)

    def _refresh_visible_text(self) -> None:
        """Keep the input text visible after selection, focus, and highlighter updates."""
        self._visible_text_refresh_queued = False
        self._restore_valid_scroll_position()
        self.ensureCursorVisible()
        self.horizontalScrollBar().setValue(0)
        self.viewport().update()
        self.updateGeometry()

    def _update_highlighter_text_color(self) -> None:
        """Keep non-regex text readable when syntax highlighting is enabled."""
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
