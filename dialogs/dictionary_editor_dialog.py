"""プリセットエディターから挿入辞書のJSONを編集する画面を提供する。"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from editor.dictionary_edit_service import (
    EDITABLE_DICTIONARIES,
    DictionaryEditError,
    DictionaryEditService,
)
from localization.translator import Translator


class DictionaryEditorDialog(QDialog):
    """アウトラインで文字列の項目を編集するか、JSON全体を編集して検証する。"""

    def __init__(
        self, translator: Translator, service: DictionaryEditService,
        on_saved: Callable[[Path], None], parent: QWidget | None = None,
    ) -> None:
        """辞書編集画面の一覧とJSON編集欄を用意する。"""
        super().__init__(parent)
        self.translator = translator
        self.service = service
        self.on_saved = on_saved
        self.current_data: object = None
        self.current_name = ""
        self.current_path: tuple[str | int, ...] | None = None
        self._saved_text = ""
        self._loading = False
        self._dirty = False
        self._tab_index = 0
        self.setWindowTitle(translator.text("dictionary.editor.title"))
        self.resize(980, 700)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel(translator.text("dictionary.editor.file")))
        self.files = QComboBox()
        for name in EDITABLE_DICTIONARIES:
            self.files.addItem(name, name)
        self.files.currentIndexChanged.connect(self._file_changed)
        top.addWidget(self.files, 1)
        layout.addLayout(top)
        self.path_label = QLabel()
        self.path_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.path_label)
        self.tabs = QTabWidget()
        structured = QWidget()
        structured_layout = QVBoxLayout(structured)
        splitter = QSplitter()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel(translator.text("dictionary.editor.outline"))
        self.tree.currentItemChanged.connect(self._selection_changed)
        splitter.addWidget(self.tree)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.field_label = QLabel(translator.text("dictionary.editor.select_field"))
        right_layout.addWidget(self.field_label)
        self.value_edit = QPlainTextEdit()
        self.value_edit.setEnabled(False)
        self.value_edit.textChanged.connect(self._value_changed)
        right_layout.addWidget(self.value_edit)
        splitter.addWidget(right)
        splitter.setSizes([380, 590])
        structured_layout.addWidget(splitter)
        self.tabs.addTab(structured, translator.text("dictionary.editor.fields"))
        self.raw_edit = QPlainTextEdit()
        self.raw_edit.textChanged.connect(self._raw_changed)
        self.tabs.addTab(self.raw_edit, translator.text("dictionary.editor.raw"))
        self.tabs.currentChanged.connect(self._tab_changed)
        layout.addWidget(self.tabs, 1)
        row = QHBoxLayout()
        self.validate_button = QPushButton(translator.text("dictionary.editor.validate"))
        self.save_button = QPushButton(translator.text("dictionary.editor.save"))
        self.close_button = QPushButton(translator.text("dictionary.editor.close"))
        self.save_button.setShortcut("Ctrl+S")
        self.validate_button.clicked.connect(self.validate_current)
        self.save_button.clicked.connect(self.save_current)
        self.close_button.clicked.connect(self.close)
        row.addStretch()
        for button in (self.validate_button, self.save_button, self.close_button):
            row.addWidget(button)
        layout.addLayout(row)
        self._load_name(EDITABLE_DICTIONARIES[0])

    def _load_name(self, name: str) -> bool:
        """指定辞書を読み込んで編集状態を更新する。"""
        try:
            data = self.service.load(name)
        except DictionaryEditError as error:
            self._warning(str(error))
            return False
        self.current_name = name
        self.current_data = data
        self._saved_text = json.dumps(data, ensure_ascii=False, indent=2)
        self._dirty = False
        load_file_path = self.service.user_folder / name
        if not load_file_path.is_file():
            load_file_path = self.service.bundled_folder / name
        self.path_label.setText(str(load_file_path))
        self._render_tree()
        self._loading = True
        self.raw_edit.setPlainText(self._saved_text)
        self._loading = False
        self._update_title()
        return True

    def _file_changed(self, _index: int) -> None:
        """ファイル選択が変わったときに対象辞書を切り替える。"""
        name = self.files.currentData()
        if not isinstance(name, str) or not self.current_name or name == self.current_name:
            return
        if not self._confirm_discard():
            self.files.blockSignals(True)
            self.files.setCurrentIndex(self.files.findData(self.current_name))
            self.files.blockSignals(False)
            return
        if not self._load_name(name):
            self.files.blockSignals(True)
            self.files.setCurrentIndex(self.files.findData(self.current_name))
            self.files.blockSignals(False)

    def _render_tree(self) -> None:
        """辞書の構造をツリーに表示する。"""
        self._loading = True
        self.current_path = None
        self.tree.clear()
        self.value_edit.clear()
        self.value_edit.setEnabled(False)
        self.field_label.setText(self.translator.text("dictionary.editor.select_field"))

        def add(parent: QTreeWidgetItem | None, value: object, path: tuple[str | int, ...], label: str) -> None:
            """値と参照位置を対応するツリー項目に追加する。"""
            item = QTreeWidgetItem([label])
            if parent is None:
                self.tree.addTopLevelItem(item)
            else:
                parent.addChild(item)
            if isinstance(value, dict):
                for key, child in value.items():
                    add(item, child, (*path, key), key)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    name = child.get("label_key", str(index)) if isinstance(child, dict) else str(index)
                    add(item, child, (*path, index), name)
            elif isinstance(value, str):
                item.setData(0, Qt.ItemDataRole.UserRole, path)
        add(None, self.current_data, (), self.current_name)
        self.tree.expandToDepth(1)
        self._loading = False

    def _selection_changed(self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None) -> None:
        """選択された項目の値を編集欄に表示する。"""
        if self._loading:
            return
        path = current.data(0, Qt.ItemDataRole.UserRole) if current is not None else None
        self.current_path = path if isinstance(path, tuple) else None
        self._loading = True
        self.value_edit.setEnabled(self.current_path is not None)
        self.value_edit.setPlainText(
            self._get_path(self.current_path) if self.current_path is not None else ""
        )
        self.field_label.setText(
            " / ".join(map(str, self.current_path))
            if self.current_path is not None
            else self.translator.text("dictionary.editor.select_field")
        )
        self._loading = False

    def _get_path(self, path: tuple[str | int, ...]) -> str:
        """辞書内で指定された階層の値を取得する。"""
        value = self.current_data
        for part in path:
            value = value[part]  # type: ignore[index]
        return str(value)

    def _value_changed(self) -> None:
        """入力欄の変更を選択中の辞書項目に反映する。"""
        if self._loading or self.current_path is None:
            return
        target = self.current_data
        for part in self.current_path[:-1]:
            target = target[part]  # type: ignore[index]
        target[self.current_path[-1]] = self.value_edit.toPlainText()  # type: ignore[index]
        self._dirty = True
        self._update_title()

    def _raw_changed(self) -> None:
        """JSON編集欄の変更を未保存として記録する。"""
        if not self._loading:
            self._dirty = True
            self._update_title()

    def _tab_changed(self, index: int) -> None:
        """編集タブの切り替えに応じて表示を同期する。"""
        if self._tab_index == 0 and index == 1:
            self._loading = True
            self.raw_edit.setPlainText(json.dumps(self.current_data, ensure_ascii=False, indent=2))
            self._loading = False
        elif self._tab_index == 1 and index == 0:
            try:
                self.current_data = json.loads(self.raw_edit.toPlainText())
            except json.JSONDecodeError as error:
                self._warning(str(error))
                self.tabs.blockSignals(True)
                self.tabs.setCurrentIndex(1)
                self.tabs.blockSignals(False)
                return
            self._render_tree()
        self._tab_index = index

    def _current_model(self) -> object:
        """現在の編集内容から検証対象の辞書データを取得する。"""
        if self.tabs.currentIndex() == 1:
            try:
                return json.loads(self.raw_edit.toPlainText())
            except json.JSONDecodeError as error:
                raise DictionaryEditError(str(error)) from error
        return self.current_data

    def validate_current(self) -> bool:
        """編集中の辞書を検証して結果を表示する。"""
        try:
            self.service.validate(self.current_name, self._current_model())
        except DictionaryEditError as error:
            self._warning(str(error))
            return False
        QMessageBox.information(
            self, self.translator.text("dictionary.editor.title"),
            self.translator.text("dictionary.editor.valid"),
        )
        return True

    def save_current(self) -> bool:
        """現在の辞書を検証してユーザー用の保存先へ書き込む。"""
        try:
            data = self._current_model()
            save_file_path = self.service.save(self.current_name, data)
        except DictionaryEditError as error:
            self._warning(str(error))
            return False
        self.current_data = data
        self._saved_text = json.dumps(data, ensure_ascii=False, indent=2)
        self._dirty = False
        self.path_label.setText(str(save_file_path))
        self._update_title()
        self.on_saved(save_file_path)
        return True

    def _confirm_discard(self) -> bool:
        """未保存変更を破棄してよいか確認する。"""
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self, self.translator.text("dictionary.editor.title"),
            self.translator.text("dictionary.editor.unsaved"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_current()
        return answer == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        """未保存編集の確認結果に従って画面を閉じる。"""
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def _update_title(self) -> None:
        """辞書名と未保存状態をタイトルに反映する。"""
        title = self.translator.text("dictionary.editor.title")
        self.setWindowTitle(f"{title} — {self.current_name}{' *' if self._dirty else ''}")

    def _warning(self, message: str) -> None:
        """辞書操作の警告を表示する。"""
        QMessageBox.warning(self, self.translator.text("dictionary.editor.title"), message)
