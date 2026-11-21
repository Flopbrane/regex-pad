"""テキストを一切変更することなく、静的および実行時の診断情報を収集します。"""

from macro.validation_types import (
    MacroDiagnostic,
    MacroDiagnosticSeverity,
    MacroValidationResult,
)


class MacroLinter:
    """テキストを一切変更することなく、静的および実行時の診断情報を収集します。"""
    @staticmethod
    def combine(*results: MacroValidationResult) -> MacroValidationResult:
        """複数の診断結果を1つにまとめる。"""
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
        """単一のマクロステップに関連する診断を作成する。"""
        return MacroDiagnostic(
            severity,
            code,
            "macro.runtime." + code,
            step_index,
            field_name,
            {"error": error} if error is not None else {},
        )
