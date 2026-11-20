"""Review the exact macro output and per-step counts before applying it."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dialogs.macro_diagnostic_table import MacroDiagnosticTable
from localization.translator import Translator
from macro.macro_preview import MacroPreview


class MacroRunPreviewDialog(QDialog):
    def __init__(
        self,
        preview: MacroPreview,
        translator: Translator,
        target_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(translator.text("macro.run.title"))
        self.resize(1100, 800)
        layout = QVBoxLayout(self)
        label = QLabel(
            translator.text(
                "macro.run.target", target=target_label, name=preview.macro_name
            )
        )
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(label)
        self.counts = QTableWidget(len(preview.result.steps), 5)
        self.counts.setHorizontalHeaderLabels(
            [
                translator.text("macro.run." + name)
                for name in ("step", "enabled", "matches", "excluded", "replacements")
            ]
        )
        self.counts.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.counts.horizontalHeader().setStretchLastSection(True)
        for row, report in enumerate(preview.result.steps):
            for column, value in enumerate(
                (
                    report.step_name,
                    translator.text(
                        "macro.editor.on" if report.enabled else "macro.editor.off"
                    ),
                    str(report.matches),
                    str(report.excluded),
                    str(report.replacements),
                )
            ):
                self.counts.setItem(row, column, QTableWidgetItem(value))
        self.counts.resizeColumnsToContents()
        layout.addWidget(self.counts)
        self.before = QPlainTextEdit()
        self.after = QPlainTextEdit()
        splitter = QSplitter()
        for name, editor, text in (
            ("before", self.before, preview.result.original_text),
            ("after", self.after, preview.result.text),
        ):
            editor.setReadOnly(True)
            editor.setPlainText(text)
            pane = QWidget()
            pane_layout = QVBoxLayout(pane)
            pane_layout.addWidget(QLabel(translator.text("macro.run." + name)))
            pane_layout.addWidget(editor)
            splitter.addWidget(pane)
        layout.addWidget(splitter, 1)
        diagnostics = MacroDiagnosticTable(translator)
        diagnostics.set_result(preview.result.validation)
        layout.addWidget(diagnostics)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.apply_button = self.buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.apply_button.setText(translator.text("macro.run.apply"))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            translator.text("macro.run.cancel")
        )
        self.apply_button.setEnabled(preview.can_apply)
        self.apply_button.clicked.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
