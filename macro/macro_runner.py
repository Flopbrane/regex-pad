"""Run immutable macro steps on a detached text snapshot using SearchEngine."""

import re
from dataclasses import dataclass

from macro.macro_linter import MacroLinter
from macro.macro_model import MacroDefinition
from macro.validation_types import (
    MacroDiagnostic,
    MacroDiagnosticSeverity,
    MacroValidationResult,
)
from search.search_engine import SearchEngine


@dataclass(frozen=True, slots=True)
class MacroStepResult:
    step_index: int
    step_name: str
    enabled: bool
    matches: int = 0
    excluded: int = 0
    replacements: int = 0


@dataclass(frozen=True, slots=True)
class MacroRunResult:
    original_text: str
    text: str
    steps: tuple[MacroStepResult, ...]
    validation: MacroValidationResult
    completed: bool

    @property
    def succeeded(self) -> bool:
        return self.completed and self.validation.is_valid


class MacroRunner:
    def __init__(self, search_engine: SearchEngine | None = None) -> None:
        self.search_engine = search_engine or SearchEngine()

    def run(self, definition: MacroDefinition, source_text: str) -> MacroRunResult:
        current_text = source_text
        reports: list[MacroStepResult] = []
        diagnostics: list[MacroDiagnostic] = []
        for step in definition.steps:
            if not step.enabled:
                reports.append(MacroStepResult(step.step_index, step.step_name, False))
                continue
            try:
                analysis = self.search_engine.analyze_matches(
                    current_text, step.search_text, step.options
                )
                if analysis.zero_width:
                    diagnostics.append(
                        MacroLinter.step_diagnostic(
                            "zero_width_search", step.step_index
                        )
                    )
                    return MacroRunResult(
                        source_text,
                        source_text,
                        tuple(reports),
                        MacroValidationResult(tuple(diagnostics)),
                        False,
                    )
                result = self.search_engine.replace_all(
                    current_text,
                    step.search_text,
                    step.replacement_text,
                    step.options,
                )
            except (re.error, IndexError, ValueError) as error:
                diagnostics.append(
                    MacroLinter.step_diagnostic(
                        "step_failed",
                        step.step_index,
                        error=str(error),
                        field_name="replacement_text",
                    )
                )
                return MacroRunResult(
                    source_text,
                    source_text,
                    tuple(reports),
                    MacroValidationResult(tuple(diagnostics)),
                    False,
                )
            reports.append(
                MacroStepResult(
                    step.step_index,
                    step.step_name,
                    True,
                    analysis.matches,
                    analysis.excluded,
                    result.count,
                )
            )
            if not result.count:
                diagnostics.append(
                    MacroLinter.step_diagnostic(
                        "no_matches",
                        step.step_index,
                        severity=MacroDiagnosticSeverity.INFORMATION,
                    )
                )
            current_text = result.text
        return MacroRunResult(
            source_text,
            current_text,
            tuple(reports),
            MacroValidationResult(tuple(diagnostics)),
            True,
        )
