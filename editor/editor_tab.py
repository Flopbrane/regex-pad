"""エディターとルーラーを組み合わせたタブを提供する。"""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from editor.ruler import Ruler
from editor.text_editor import TextEditor


class EditorTab(QWidget):
    """文書編集欄とルーラーを持つタブのコンテナ。"""
    def __init__(self, editor: TextEditor, parent: QWidget | None = None) -> None:
        """編集欄とルーラーをタブ内に配置する。"""
        super().__init__(parent)
        self.editor = editor
        self.ruler = Ruler(self)
        self.ruler.set_editor(editor)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.ruler)
        layout.addWidget(editor)
        self.setLayout(layout)

    def set_ruler_visible(self, visible: bool) -> None:
        """ルーラーの表示を切り替える。"""
        self.ruler.setVisible(visible)
