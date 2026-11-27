"""文法チェックの結果表示を提供する。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QHideEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from localization.translator import Translator


class GrammarCheckDialog(QDialog):
    """診断一覧と原稿の該当行への移動を提供する画面。"""
    line_selected = Signal(int)
    refresh_requested = Signal()
    dismissed = Signal()

    def __init__(
        self,
        translator: Translator,
        parent: QWidget | None = None,
    ) -> None:
        """診断の要約、一覧、ボタンを組み立てる。"""
        super().__init__(parent)
        self.translator = translator
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self.summary_label = QLabel(self)
        self.summary_label.setWordWrap(True)
        self.runtime_feedback_label = QLabel(self)
        self.runtime_feedback_label.setWordWrap(True)
        self.runtime_feedback_label.hide()
        self.message_list = QListWidget(self)
        self.copy_button = QPushButton(self)
        self.refresh_button = QPushButton(self)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        self.button_box.addButton(
            self.copy_button,
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.button_box.addButton(
            self.refresh_button,
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self._copy_text = ""
        self._document_label = ""

        layout = QVBoxLayout()
        layout.addWidget(self.summary_label)
        layout.addWidget(self.runtime_feedback_label)
        layout.addWidget(self.message_list, 1)
        layout.addWidget(self.button_box)
        self.setLayout(layout)
        self.resize(930, 360)

        self.message_list.itemActivated.connect(self._emit_line_selected)
        self.message_list.itemClicked.connect(self._emit_line_selected)
        self.copy_button.clicked.connect(self.copy_results_to_clipboard)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.button_box.rejected.connect(self.hide)
        self.apply_language()

    def apply_language(self) -> None:
        """現在の言語を見出しとボタンに反映する。"""
        self._update_window_title()
        self.copy_button.setText(self.translator.text("grammar_check.copy_results"))
        self.refresh_button.setText(self.translator.text("grammar_check.refresh"))

    def set_document_label(self, document_label: str) -> None:
        """診断対象の文書名を設定する。"""
        self._document_label = document_label
        self._update_window_title()

    def _update_window_title(self) -> None:
        """現在の文書名をタイトルに反映する。"""
        title = self.translator.text("grammar_check.title")
        if self._document_label:
            title = f"{title} - {self._document_label}"
        self.setWindowTitle(title)

    def set_result(
        self,
        summary: str,
        rows: list[tuple[int, str]],
    ) -> None:
        """診断の要約と行番号付きの結果を表示する。"""
        self.set_runtime_feedback("")
        self.summary_label.setText(summary)
        self.message_list.clear()
        row_texts: list[str] = []
        for line_number, message_text in rows:
            row_text = self.translator.text(
                "grammar_check.issue_row",
                line=line_number,
                message=message_text,
            )
            row_texts.append(row_text)
            item = QListWidgetItem(row_text)
            item.setData(Qt.ItemDataRole.UserRole, line_number)
            self.message_list.addItem(item)
        self._copy_text = "\n".join(row_texts)
        self.copy_button.setEnabled(bool(row_texts))

    def set_runtime_feedback(self, text: str) -> None:
        """原稿の行と対応しない実行エンジンの結果を別欄に表示する。"""
        self.runtime_feedback_label.setText(text)
        self.runtime_feedback_label.setVisible(bool(text))
        self.copy_button.setEnabled(bool(text or self._copy_text))

    def copy_results_to_clipboard(self) -> None:
        """現在の診断結果をクリップボードへコピーする。"""
        if not self._copy_text and not self.runtime_feedback_label.text():
            return
        text = "\n\n".join(part for part in (self._copy_text, self.runtime_feedback_label.text()) if part)
        QApplication.clipboard().setText(text)

    def _emit_line_selected(self, item: QListWidgetItem) -> None:
        """選択した診断の行番号を通知する。"""
        line_number = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(line_number, int):
            self.line_selected.emit(line_number)

    def hideEvent(self, event: QHideEvent) -> None:
        """画面が非表示になったときの処理を行う。"""
        super().hideEvent(event)
        self.dismissed.emit()
