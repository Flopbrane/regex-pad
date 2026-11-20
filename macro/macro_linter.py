"""Collect static and runtime diagnostics without changing any text."""

from macro.validation_types import (
    MacroDiagnostic,
    MacroDiagnosticSeverity,
    MacroValidationResult,
)


class MacroLinter:
    @staticmethod
    def combine(*results: MacroValidationResult) -> MacroValidationResult:
        return MacroValidationResult(
            tuple(diagnostic for result in results for diagnostic in result.diagnostics)
        )

    @staticmethod
    def step_diagnostic(
        code: str,
        step_index: int,
        *,
        error: str | None = None,
        field_name: str = "search_text",
        severity: MacroDiagnosticSeverity = MacroDiagnosticSeverity.ERROR,
    ) -> MacroDiagnostic:
        return MacroDiagnostic(
            severity,
            code,
            "macro.runtime." + code,
            step_index,
            field_name,
            {"error": error} if error is not None else {},
        )
