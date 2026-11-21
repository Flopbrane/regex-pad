from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from localization.translator import Translator

SEARCH_COLUMN = 2
MIN_COLUMN_WIDTHS = (140, 180, 220, 170, 190, 150, 190, 380)
HEADERS = {
    "EN_Ver.": ["Section", "Topic", "Search pattern", "Replacement text", "Input example", "Matched text", "Result", "Explanation"],
    "JP_Ver.": ["区分", "項目", "検索文字列", "置換文字列", "入力例", "一致部分", "置換結果", "説明"],
}
NOTES = {
    "EN_Ver.": (
        "Turn on Regular Expression in Find/Replace to use these patterns and "
        "replacement references. \\d searches for a digit; \\1 or \\g<1> reuses "
        "a captured group in the replacement field. Double-click a row to "
        "insert its search pattern."
    ),
    "JP_Ver.": (
        "検索/置換画面で「正規表現として検索する」を有効にしてください。"
        "\\d は数字を探す検索記法、\\1・\\g<1> は括弧で保存した文字列を"
        "置換欄で再利用する記法です。行をダブルクリックすると検索文字列を挿入します。"
    ),
}
COLUMNS = ("section", "topic", "search", "replacement", "input", "match", "result", "explanation")


class RegexHelpDialog(QDialog):
    pattern_insert_requested = Signal(str)

    def __init__(
        self,
        regex_help_path: Path | dict[str, Path],
        translator: Translator,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.translator = translator
        self.resize(1100, 620)
        self.regex_help_paths = (
            {"EN_Ver.": regex_help_path}
            if isinstance(regex_help_path, Path)
            else regex_help_path
        )
        self.language_combo_box = QComboBox(self)
        for language_name in self.regex_help_paths:
            self.language_combo_box.addItem(language_name)

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(COLUMNS))
        header = self.table.horizontalHeader()
        header.setSectionsMovable(True)
        for column, width in enumerate(MIN_COLUMN_WIDTHS):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(column, width)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        self.insert_button = button_box.addButton(
            self.translator.text("regex_help.insert"),
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.language_label = QLabel(self)
        self.instructions_label = QLabel(self)
        self.instructions_label.setWordWrap(True)
        language_layout = QHBoxLayout()
        language_layout.addWidget(self.language_label)
        language_layout.addWidget(self.language_combo_box)
        language_layout.addStretch()
        layout = QVBoxLayout()
        layout.addLayout(language_layout)
        layout.addWidget(self.instructions_label)
        layout.addWidget(self.table)
        layout.addWidget(button_box)
        self.setLayout(layout)

        self._load_current_language()
        self.insert_button.clicked.connect(self._emit_selected_pattern)
        button_box.rejected.connect(self.close)
        self.table.itemDoubleClicked.connect(self._emit_item_pattern)
        self.language_combo_box.currentTextChanged.connect(self._load_current_language)
        self.apply_language()

    def apply_language(self) -> None:
        self.setWindowTitle(self.translator.text("regex_help.title"))
        self.language_label.setText(self.translator.text("regex_help.language"))
        self.insert_button.setText(self.translator.text("regex_help.insert"))
        self._set_headers()

    def _set_headers(self) -> None:
        language = self.language_combo_box.currentText()
        self.table.setHorizontalHeaderLabels(HEADERS.get(language, HEADERS["EN_Ver."]))
        self.instructions_label.setText(NOTES.get(language, NOTES["EN_Ver."]))

    def _load_current_language(self) -> None:
        self._set_headers()
        load_file_path = self.regex_help_paths[self.language_combo_box.currentText()]
        load_data = json.loads(load_file_path.read_text(encoding="utf-8"))
        self.table.setRowCount(len(load_data))
        for row, item in enumerate(load_data):
            for column, key in enumerate(COLUMNS):
                self.table.setItem(row, column, QTableWidgetItem(str(item[key])))
        self.table.resizeColumnsToContents()
        for column, minimum_width in enumerate(MIN_COLUMN_WIDTHS):
            self.table.setColumnWidth(
                column, max(self.table.columnWidth(column), minimum_width)
            )
        self.table.resizeRowsToContents()

    def _emit_selected_pattern(self) -> None:
        selected_items = self.table.selectedItems()
        if selected_items:
            self._emit_item_pattern(selected_items[0])

    def _emit_item_pattern(self, item: QTableWidgetItem) -> None:
        pattern_item = self.table.item(item.row(), SEARCH_COLUMN)
        if pattern_item is not None:
            self.pattern_insert_requested.emit(pattern_item.text())
