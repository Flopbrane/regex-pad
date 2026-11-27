"""カーソル位置または選択先頭文字の Unicode 情報を表示する。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from editor.unicode_character_info import UnicodeCharacterInfo
from localization.translator import Translator


class UnicodeCharacterInfoDialog(QDialog):
    """本文を書き換えずに1文字の属性を表示するダイアログ。"""

    def __init__(
        self,
        info: UnicodeCharacterInfo | None,
        from_selection: bool,
        translator: Translator,
        parent: QWidget | None = None,
    ) -> None:
        """調査対象と翻訳を受け取り、文字情報の表示を組み立てる。"""
        super().__init__(parent)
        self.info = info
        self.from_selection = from_selection
        self.translator = translator
        self.resize(460, 250)
        self.description_label = QLabel(self)
        self.description_label.setWordWrap(True)
        self.form = QFormLayout()
        self.field_labels = [QLabel(self) for _ in range(5)]
        self.value_labels = [QLabel(self) for _ in range(5)]
        for field_label, value_label in zip(self.field_labels, self.value_labels, strict=True):
            value_label.setTextFormat(Qt.TextFormat.PlainText)
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            self.form.addRow(field_label, value_label)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        self.buttons.rejected.connect(self.close)
        layout = QVBoxLayout(self)
        layout.addWidget(self.description_label)
        layout.addLayout(self.form)
        layout.addWidget(self.buttons)
        self.apply_language()

    def set_character(
        self, info: UnicodeCharacterInfo | None, from_selection: bool
    ) -> None:
        """開いたまま次の文字を調べたときに表示対象を更新する。"""
        self.info = info
        self.from_selection = from_selection
        self.apply_language()

    def apply_language(self) -> None:
        """現在の表示言語で見出しと値を描き直す。"""
        self.setWindowTitle(self.translator.text("unicode_info.title"))
        source_key = "unicode_info.selection" if self.from_selection else "unicode_info.cursor"
        self.description_label.setText(
            self.translator.text("unicode_info.empty")
            if self.info is None else self.translator.text(source_key)
        )
        keys = (
            "unicode_info.character",
            "unicode_info.code_point",
            "unicode_info.name",
            "unicode_info.category",
            "unicode_info.nfkc",
        )
        values = (
            repr(self.info.character),
            self.info.code_point,
            self.info.name or self.translator.text("unicode_info.unnamed"),
            self.info.category,
            repr(self.info.nfkc),
        ) if self.info is not None else ("", "", "", "", "")
        for index, (key, value) in enumerate(zip(keys, values, strict=True)):
            self.field_labels[index].setText(self.translator.text(key))
            self.value_labels[index].setText(value)
        self.buttons.button(QDialogButtonBox.StandardButton.Close).setText(
            self.translator.text("unicode_info.close")
        )
