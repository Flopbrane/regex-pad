"""エディター右端に検索結果の分布を表示する欄を提供する。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize
from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from editor.text_editor import TextEditor


class SearchMarkerArea(QWidget):
    """エディターの検索マーカーを描画する欄。"""
    def __init__(self, editor: TextEditor) -> None:
        """マーカー欄を対象のエディターに関連付ける。"""
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        """マーカー欄に必要な幅を返す。"""
        return QSize(self.editor.search_marker_area_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        """検索マーカーの描画をエディターに委ねる。"""
        self.editor.paint_search_marker_area(event)
