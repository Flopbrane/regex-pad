"""Diagnostic data types returned by pseudo-macro validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MacroDiagnosticSeverity(str, Enum):
    """Severity used by future pseudo-macro Linter presentation."""

    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"


@dataclass(frozen=True, slots=True)
class MacroDiagnostic:
    """Describe one model-level validation finding."""

    severity: MacroDiagnosticSeverity
    code: str
    message_key: str
    step_index: int | None = None
    field_name: str | None = None
    values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MacroValidationResult:
    """Collect diagnostics and expose execution gating properties."""

    diagnostics: tuple[MacroDiagnostic, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether no Error diagnostic prevents execution."""
        return not self.errors

    @property
    def errors(self) -> tuple[MacroDiagnostic, ...]:
        """Return Error diagnostics only."""
        return self._with_severity(MacroDiagnosticSeverity.ERROR)

    @property
    def warnings(self) -> tuple[MacroDiagnostic, ...]:
        """Return Warning diagnostics only."""
        return self._with_severity(MacroDiagnosticSeverity.WARNING)

    @property
    def information(self) -> tuple[MacroDiagnostic, ...]:
        """Return Information diagnostics only."""
        return self._with_severity(MacroDiagnosticSeverity.INFORMATION)

    def _with_severity(
        self,
        severity: MacroDiagnosticSeverity,
    ) -> tuple[MacroDiagnostic, ...]:
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.severity is severity
        )
