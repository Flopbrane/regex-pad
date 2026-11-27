"""エディター左側に行番号を表示する欄を提供する。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QMouseEvent, QPaintEvent
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from editor.text_editor import TextEditor


class LineNumberArea(QWidget):
    """行番号の描画と行選択をエディターへ渡す欄。"""
    def __init__(self, editor: TextEditor) -> None:
        """行番号欄をエディターに関連付ける。"""
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        """行番号欄に必要な幅を返す。"""
        return self.editor.line_number_area_size_hint()

    def paintEvent(self, event: QPaintEvent) -> None:
        """行番号の描画をエディターに委ねる。"""
        self.editor.paint_line_number_area(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """クリック位置から該当する行を選ぶ。"""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self.editor.select_line_at_view_y(round(event.position().y()))
        event.accept()
