"""疑似マクロの検証結果を表す診断データ型を定義する。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MacroDiagnosticSeverity(str, Enum):
    """疑似マクロの診断画面で使う重大度を定義する。"""

    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"


@dataclass(frozen=True, slots=True)
class MacroDiagnostic:
    """マクロ定義の検証で得た診断1件を表す。"""

    severity: MacroDiagnosticSeverity
    code: str
    message_key: str
    step_index: int | None = None
    field_name: str | None = None
    values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MacroValidationResult:
    """診断結果をまとめて保持し、実行できるかを示す。"""

    diagnostics: tuple[MacroDiagnostic, ...] = ()

    @property
    def is_valid(self) -> bool:
        """実行を止めるエラーがないかを返す。"""
        return not self.errors

    @property
    def errors(self) -> tuple[MacroDiagnostic, ...]:
        """重大度がエラーの診断だけを返す。"""
        return self._with_severity(MacroDiagnosticSeverity.ERROR)

    @property
    def warnings(self) -> tuple[MacroDiagnostic, ...]:
        """重大度が警告の診断だけを返す。"""
        return self._with_severity(MacroDiagnosticSeverity.WARNING)

    @property
    def information(self) -> tuple[MacroDiagnostic, ...]:
        """重大度が情報の診断だけを返す。"""
        return self._with_severity(MacroDiagnosticSeverity.INFORMATION)

    def _with_severity(
        self,
        severity: MacroDiagnosticSeverity,
    ) -> tuple[MacroDiagnostic, ...]:
        """指定された重大度に該当する診断だけを返す。"""
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.severity is severity
        )
