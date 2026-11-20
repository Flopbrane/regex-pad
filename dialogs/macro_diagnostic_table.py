"""Macro diagnostics with navigation back to the corresponding form."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem

from localization.translator import Translator
from macro.validation_types import MacroDiagnostic, MacroValidationResult


class MacroDiagnosticTable(QTableWidget):
    diagnostic_activated = Signal(int, str)

    def __init__(self, translator: Translator) -> None:
        super().__init__(0, 4)
        self.translator = translator
        self.diagnostics: tuple[MacroDiagnostic, ...] = ()
        self.setHorizontalHeaderLabels(
            [
                translator.text("macro.editor." + name)
                for name in ("severity", "step", "field", "message")
            ]
        )
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)
        self.cellClicked.connect(self._activate)
        self.cellActivated.connect(self._activate)

    def set_result(self, result: MacroValidationResult) -> None:
        self.diagnostics = result.diagnostics
        self.setRowCount(len(self.diagnostics))
        for row, diagnostic in enumerate(self.diagnostics):
            values = (
                diagnostic.severity.value,
                str(diagnostic.step_index + 1)
                if diagnostic.step_index is not None
                else "—",
                self.translator.text(
                    "macro.editor." + (diagnostic.field_name or "steps")
                ),
                self.translator.text(diagnostic.message_key, **diagnostic.values),
            )
            for column, value in enumerate(values):
                self.setItem(row, column, QTableWidgetItem(value))
        self.resizeColumnsToContents()

    def _activate(self, row: int, _column: int) -> None:
        diagnostic = self.diagnostics[row]
        self.diagnostic_activated.emit(
            diagnostic.step_index if diagnostic.step_index is not None else -1,
            diagnostic.field_name or "",
        )
