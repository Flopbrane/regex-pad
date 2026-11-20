"""Form for one macro step; no file I/O or validation side effects."""

from dataclasses import replace
from typing import cast

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QWidget

from dialogs.regex_input_edit import RegexInputEdit
from localization.translator import Translator
from macro.editor_data_model import MacroEditorStepData
from unicode_normalize import NORMALIZATION_FORMS


class MacroStepEditorWidget(QWidget):
    step_changed = Signal(object)

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.translator = translator
        self._loading = False
        self._step = MacroEditorStepData()
        self.fields: dict[str, QLineEdit | QComboBox | RegexInputEdit] = {}
        self.form = QFormLayout(self)
        field_order = (
            "step_name",
            "enabled",
            "search_text",
            "exclusion_enabled",
            "exclusion_text",
            "replacement_enabled",
            "replacement_text",
            "regular_expression",
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
            else:
                widget = QComboBox()
                widget.setEditable(False)
                if name == "unicode_normalize_form":
                    widget.addItem(translator.text("macro.editor.unspecified"), None)
                    for value in NORMALIZATION_FORMS:
                        widget.addItem(value, value)
                else:
                    widget.addItem(translator.text("macro.editor.off"), False)
                    widget.addItem(translator.text("macro.editor.on"), True)
                widget.currentIndexChanged.connect(self._changed)
            widget.setObjectName(name)
            self.fields[name] = widget
            self.form.addRow(translator.text("macro.editor." + name), widget)
        self.set_step(self._step)

    def set_step(self, step: MacroEditorStepData) -> None:
        self._loading = True
        self._step = replace(step)
        for name, widget in self.fields.items():
            value = getattr(step, name)
            widget.setStyleSheet("")
            widget.setToolTip("")
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(widget.findData(value))
            elif isinstance(widget, RegexInputEdit):
                widget.setPlainText(value)
            else:
                widget.setText(value)
        self._sync_enabled()
        self._loading = False

    def _combo(self, name: str) -> QComboBox:
        return cast(QComboBox, self.fields[name])

    def retranslate_ui(self) -> None:
        for name, widget in self.fields.items():
            label = self.form.labelForField(widget)
            if isinstance(label, QLabel):
                label.setText(self.translator.text("macro.editor." + name))
            if isinstance(widget, QComboBox):
                if name == "unicode_normalize_form":
                    widget.setItemText(
                        0, self.translator.text("macro.editor.unspecified")
                    )
                else:
                    widget.setItemText(0, self.translator.text("macro.editor.off"))
                    widget.setItemText(1, self.translator.text("macro.editor.on"))

    def _sync_enabled(self) -> None:
        normalize = bool(self._combo("unicode_normalize").currentData())
        self.fields["unicode_normalize_form"].setEnabled(normalize)
        self.fields["replacement_enabled"].setEnabled(not normalize)
        self.fields["replacement_text"].setEnabled(
            not normalize and bool(self._combo("replacement_enabled").currentData())
        )
        self.fields["exclusion_text"].setEnabled(
            bool(self._combo("exclusion_enabled").currentData())
        )
        regex = bool(self._combo("regular_expression").currentData())
        for name in ("search_text", "exclusion_text", "replacement_text"):
            cast(RegexInputEdit, self.fields[name]).highlighter.set_enabled(regex)

    def step_data(self) -> MacroEditorStepData:
        values = {}
        for name, widget in self.fields.items():
            if isinstance(widget, QComboBox):
                values[name] = widget.currentData()
            elif isinstance(widget, RegexInputEdit):
                values[name] = widget.toPlainText()
            else:
                values[name] = widget.text()
        return MacroEditorStepData(**values)

    def _changed(self, *_args: object) -> None:
        if self._loading:
            return
        # Keep dormant text in widgets, but explicitly select the valid route.
        self._loading = True
        try:
            if self._combo("unicode_normalize").currentData():
                self._combo("replacement_enabled").setCurrentIndex(0)
            else:
                self._combo("unicode_normalize_form").setCurrentIndex(0)
            self._sync_enabled()
            self._step = self.step_data()
        finally:
            self._loading = False
        self.step_changed.emit(self._step)

    def focus_field(self, name: str, message: str = "") -> None:
        widget = self.fields.get(name)
        if widget is None:
            return
        widget.setStyleSheet("border: 1px solid #c62828;" if message else "")
        widget.setToolTip(message)
        widget.setFocus()
        if isinstance(widget, QLineEdit):
            widget.selectAll()
