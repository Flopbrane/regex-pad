"""SearchEngineを使用して、切り離されたテキストスナップショット上で、不変のマクロステップを実行。"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from macro.macro_linter import MacroLinter
from macro.macro_model import MacroDefinition
from macro.validation_types import (
    MacroDiagnostic,
    MacroDiagnosticSeverity,
    MacroValidationResult,
)
from search.search_engine import ReplaceResult, SearchAnalysis, SearchEngine


@dataclass(frozen=True, slots=True)
class MacroStepResult:
    """マクロステップの実行結果を表す。"""
    step_index: int
    step_name: str
    enabled: bool
    matches: int = 0
    excluded: int = 0
    replacements: int = 0


@dataclass(frozen=True, slots=True)
class MacroRunResult:
    """マクロの実行結果を表す。"""
    original_text: str
    text: str
    steps: tuple[MacroStepResult, ...]
    validation: MacroValidationResult
    completed: bool

    @property
    def succeeded(self) -> bool:
        """マクロの実行が完了し、かつすべてのステップが成功したかどうかを返す。"""
        return self.completed and self.validation.is_valid


class MacroRunner:
    """SearchEngineを使用して、切り離されたテキストスナップショット上で、不変のマクロステップを実行。"""
    def __init__(self, search_engine: SearchEngine | None = None) -> None:
        self.search_engine: SearchEngine = search_engine or SearchEngine()

    def run(
        self,
        definition: MacroDefinition,
        source_text: str,
        selected_scope: tuple[int, int] | None = None,
        visible_scope: tuple[int, int] | None = None,
    ) -> MacroRunResult:
        """マクロを実行し、結果を返す。"""
        current_text: str = source_text
        current_selected_scope = selected_scope
        current_visible_scope = visible_scope
        reports: list[MacroStepResult] = []
        diagnostics: list[MacroDiagnostic] = []
        for step in definition.steps:
            if not step.enabled:
                reports.append(MacroStepResult(step.step_index, step.step_name, False))
                continue
            try:
                scope: tuple[int, int] | None = self._scope_for_step(
                    step.options.selected_only,
                    step.options.visible_only,
                    current_selected_scope,
                    current_visible_scope,
                    len(current_text),
                )
                if scope is None:
                    reports.append(MacroStepResult(step.step_index, step.step_name, True))
                    continue
                scope_start, scope_end = scope
                source_part: str = current_text[scope_start:scope_end]
                analysis: SearchAnalysis = self.search_engine.analyze_matches(
                    source_part, step.search_text, step.options
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
                result: ReplaceResult = self.search_engine.replace_all(
                    source_part,
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
            previous_text: str = current_text
            current_text: str = (
                previous_text[:scope_start] + result.text + previous_text[scope_end:]
            )
            if current_text != previous_text:
                current_selected_scope: tuple[int, int] | None = self._map_scope(
                    previous_text, current_text, current_selected_scope
                )
                current_visible_scope: tuple[int, int] | None = self._map_scope(
                    previous_text, current_text, current_visible_scope
                )
        return MacroRunResult(
            source_text,
            current_text,
            tuple(reports),
            MacroValidationResult(tuple(diagnostics)),
            True,
        )

    @staticmethod
    def _scope_for_step(
        selected_only: bool,
        visible_only: bool,
        selected_scope: tuple[int, int] | None,
        visible_scope: tuple[int, int] | None,
        text_length: int,
    ) -> tuple[int, int] | None:
        """マクロステップの実行に使用する、ソーステキストのスコープを決定する。"""
        if selected_only and selected_scope is None:
            return None
        if visible_only and visible_scope is None:
            return None
        start, end = 0, text_length
        for bounds in (
            selected_scope if selected_only else None,
            visible_scope if visible_only else None,
        ):
            if bounds is not None:
                start, end = max(start, bounds[0]), min(end, bounds[1])
        start, end = max(0, start), min(text_length, end)
        return (start, end) if start < end else None

    @staticmethod
    def _map_scope(
        before: str, after: str, bounds: tuple[int, int] | None
    ) -> tuple[int, int] | None:
        """マクロステップの実行後に、ソーステキストのスコープをマッピングする。"""
        if bounds is None:
            return None
        opcodes = SequenceMatcher(None, before, after).get_opcodes()

        def map_offset(offset: int, *, end: bool) -> int:
            for tag, old_start, old_end, new_start, new_end in opcodes:
                if offset < old_start:
                    return new_start - (old_start - offset)
                if old_start <= offset <= old_end:
                    if tag == "equal":
                        return new_start + offset - old_start
                    if offset == old_start:
                        return new_start
                    if offset == old_end or end:
                        return new_end
                    return new_start
            return len(after)

        return map_offset(bounds[0], end=False), map_offset(bounds[1], end=True)
