"""マクロの1手順を編集する入力欄を提供する。ファイル操作や検証は呼び出し側で行う。"""

from dataclasses import replace
from typing import cast

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QWidget,
)

from dialogs.regex_input_edit import RegexInputEdit
from localization.translator import Translator
from macro.editor_data_model import MacroEditorStepData
from unicode_normalize import NORMALIZATION_FORMS


class MacroStepEditorWidget(QWidget):
    """プリセット内の1手順を編集するフォーム。"""
    step_changed = Signal(object)

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        """手順名、検索・置換条件、チェック項目を作る。"""
        super().__init__(parent)
        self.translator = translator
        self._loading = False
        self._step = MacroEditorStepData()
        self.fields: dict[str, QLineEdit | QCheckBox | QComboBox | RegexInputEdit] = {}
        self.form = QFormLayout(self)
        field_order = (
            "step_name",
            "enabled",
            "operation",
            "search_text",
            "exclusion_enabled",
            "exclusion_text",
            "replacement_enabled",
            "replacement_text",
            "regular_expression",
            "case_sensitive",
            "whole_word",
            "selected_only",
            "visible_only",
            "unicode_normalize",
            "unicode_normalize_form",
            "append_dot_to_circled_number",
        )
        for name in field_order:
            if name in {"step_name"}:
                widget = QLineEdit()
                widget.textChanged.connect(self._changed)
            elif name.endswith("text"):
                widget = RegexInputEdit()
                widget.textChanged.connect(self._changed)
            elif name == "unicode_normalize_form":
                widget = QComboBox()
                widget.setEditable(False)
                widget.addItem(translator.text("macro.editor.unspecified"), None)
                for value in NORMALIZATION_FORMS:
                    widget.addItem(value, value)
                widget.currentIndexChanged.connect(self._changed)
            else:
                widget = QCheckBox()
                widget.setAccessibleName(translator.text("macro.editor." + name))
                widget.toggled.connect(self._changed)
            widget.setObjectName(name)
            self.fields[name] = widget
            self.form.addRow(translator.text("macro.editor." + name), widget)
            if name == "visible_only":
                self.normalize_separator = QFrame(self)
                self.normalize_separator.setObjectName("normalize_separator")
                self.normalize_separator.setFrameShape(QFrame.Shape.HLine)
                self.normalize_separator.setFrameShadow(QFrame.Shadow.Sunken)
                self.form.addRow(self.normalize_separator)
        self.set_step(self._step)

    def set_step(self, step: MacroEditorStepData) -> None:
        """指定手順の値をフォームに表示する。"""
        self._loading = True
        self._step = replace(step)
        for name, widget in self.fields.items():
            value = getattr(step, name)
            widget.setStyleSheet("")
            widget.setToolTip("")
            if isinstance(widget, QCheckBox):
                widget.setChecked(value == "numbered_heading" if name == "operation" else value)
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(widget.findData(value))
            elif isinstance(widget, RegexInputEdit):
                widget.setPlainText(value)
            else:
                widget.setText(value)
        self._sync_enabled()
        self._loading = False

    def _check(self, name: str) -> QCheckBox:
        """項目用のチェックボックスを作る。"""
        return cast(QCheckBox, self.fields[name])

    def _normalization_form(self) -> QComboBox:
        """入力欄からUnicode正規化方式を取得する。"""
        return cast(QComboBox, self.fields["unicode_normalize_form"])

    def retranslate_ui(self) -> None:
        """現在の言語をラベルと選択肢に反映する。"""
        for name, widget in self.fields.items():
            label = self.form.labelForField(widget)
            if isinstance(label, QLabel):
                label.setText(self.translator.text("macro.editor." + name))
            if isinstance(widget, QCheckBox):
                widget.setAccessibleName(self.translator.text("macro.editor." + name))
            elif isinstance(widget, QComboBox):
                widget.setItemText(0, self.translator.text("macro.editor.unspecified"))

    def _sync_enabled(self) -> None:
        """設定に応じて入力欄の有効状態を更新する。"""
        special = self._check("operation").isChecked()
        normalize = self._check("unicode_normalize").isChecked()
        self.fields["unicode_normalize_form"].setEnabled(normalize and not special)
        self.fields["replacement_enabled"].setEnabled(not normalize and not special)
        self.fields["replacement_text"].setEnabled(
            not special and not normalize and self._check("replacement_enabled").isChecked()
        )
        self.fields["exclusion_text"].setEnabled(
            not special and self._check("exclusion_enabled").isChecked()
        )
        for name in ("search_text", "exclusion_enabled", "regular_expression", "case_sensitive", "whole_word", "selected_only", "visible_only", "unicode_normalize", "append_dot_to_circled_number"):
            self.fields[name].setEnabled(not special)
        regex = self._check("regular_expression").isChecked()
        for name in ("search_text", "exclusion_text", "replacement_text"):
            cast(RegexInputEdit, self.fields[name]).highlighter.set_enabled(regex)

    def step_data(self) -> MacroEditorStepData:
        """フォームの値から手順データを作る。"""
        values = {}
        for name, widget in self.fields.items():
            if isinstance(widget, QCheckBox):
                values[name] = (
                    "numbered_heading" if widget.isChecked() else "search_replace"
                ) if name == "operation" else widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[name] = widget.currentData()
            elif isinstance(widget, RegexInputEdit):
                values[name] = widget.toPlainText()
            else:
                values[name] = widget.text()
        return MacroEditorStepData(**values)

    def _changed(self, *_args: object) -> None:
        """手順の値が変わったことを通知する。"""
        if self._loading:
            return
        # Keep dormant text in widgets, but explicitly select the valid route.
        self._loading = True
        try:
            if self._check("operation").isChecked():
                self._check("selected_only").setChecked(False)
                self._check("visible_only").setChecked(False)
            if self._check("unicode_normalize").isChecked():
                self._check("replacement_enabled").setChecked(False)
            else:
                self._normalization_form().setCurrentIndex(0)
            self._sync_enabled()
            self._step = self.step_data()
        finally:
            self._loading = False
        self.step_changed.emit(self._step)

    def focus_field(self, name: str, message: str = "") -> None:
        """診断に対応する入力欄へフォーカスを移す。"""
        widget = self.fields.get(name)
        if widget is None:
            return
        widget.setStyleSheet("border: 1px solid #c62828;" if message else "")
        widget.setToolTip(message)
        widget.setFocus()
        if isinstance(widget, QLineEdit):
            widget.selectAll()
