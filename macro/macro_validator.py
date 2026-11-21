# pylint: disable=C0301

"""擬似マクロの値の関係および正規表現を検証する。"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Final

from macro.json_data_model import MacroJsonData, MacroJsonStepData
from macro.validation_types import (
    MacroDiagnostic,
    MacroDiagnosticSeverity,
    MacroValidationResult,
)
from search.search_engine import SearchEngine, SearchOptions

SUPPORTED_FORMAT_VERSIONS: Final = frozenset({1, 2})
APPEND_DOT_NORMALIZATION_FORMS: Final = frozenset({"NFKC", "NFKD"})


class MacroValidator:
    """提供されたモデルを変更することなく、バージョン1のセマンティクスを検証する。"""

    @classmethod
    def validate(cls, load_data: MacroJsonData) -> MacroValidationResult:
        """正規化されたモデル1つについて、確定した診断結果をすべて返す。"""
        if not isinstance(load_data, MacroJsonData):
            raise TypeError("load_data must be MacroJsonData")

        diagnostics: list[MacroDiagnostic] = []
        if load_data.format_version not in SUPPORTED_FORMAT_VERSIONS:
            diagnostics.append(
                cls._error(
                    "unsupported_format_version",
                    "macro.validation.unsupported_format_version",
                    field_name="format_version",
                    values={"format_version": load_data.format_version},
                )
            )
        if not load_data.macro_name.strip():
            diagnostics.append(
                cls._error(
                    "empty_macro_name",
                    "macro.validation.empty_macro_name",
                    field_name="macro_name",
                )
            )
        if not load_data.steps:
            diagnostics.append(
                cls._error(
                    "no_steps",
                    "macro.validation.no_steps",
                    field_name="steps",
                )
            )
            return MacroValidationResult(tuple(diagnostics))

        if not any(step.enabled for step in load_data.steps):
            diagnostics.append(
                cls._warning(
                    "no_enabled_steps",
                    "macro.validation.no_enabled_steps",
                    field_name="steps",
                )
            )

        step_name_counts: Counter[str] = Counter(step.step_name for step in load_data.steps)
        for step_index, step in enumerate(load_data.steps):
            diagnostics.extend(
                cls._validate_step(
                    step,
                    step_index,
                    step_name_counts,
                    load_data.format_version,
                )
            )
        return MacroValidationResult(tuple(diagnostics))

    @classmethod
    def _validate_step(
        cls,
        step: MacroJsonStepData,
        step_index: int,
        step_name_counts: Counter[str],
        format_version: int,
    ) -> list[MacroDiagnostic]:
        """単一のステップを検証し、診断結果を返す。"""
        diagnostics: list[MacroDiagnostic] = []
        if not step.step_name.strip():
            diagnostics.append(
                cls._error(
                    "empty_step_name",
                    "macro.validation.empty_step_name",
                    step_index=step_index,
                    field_name="step_name",
                )
            )
        elif step_name_counts[step.step_name] > 1:
            diagnostics.append(
                cls._error(
                    "duplicate_step_name",
                    "macro.validation.duplicate_step_name",
                    step_index=step_index,
                    field_name="step_name",
                    values={"step_name": step.step_name},
                )
            )

        if not step.enabled:
            return diagnostics

        if step.search_text == "":
            diagnostics.append(
                cls._error(
                    "empty_search_text",
                    "macro.validation.empty_search_text",
                    step_index=step_index,
                    field_name="search_text",
                )
            )
        elif step.regular_expression:
            diagnostics.extend(cls._validate_regular_expressions(step, step_index))

        diagnostics.extend(
            cls._validate_replacement_route(step, step_index, format_version)
        )
        if not any(d.severity is MacroDiagnosticSeverity.ERROR for d in diagnostics):
            options = SearchOptions(
                regular_expression=step.regular_expression,
                case_sensitive=step.case_sensitive,
                whole_word=step.whole_word,
            )
            engine = SearchEngine()
            if engine.analyze_matches("", step.search_text, options).zero_width:
                diagnostics.append(cls._error(
                    "zero_width_search", "macro.validation.zero_width_search",
                    step_index=step_index, field_name="search_text",
                ))
            if not step.unicode_normalize and step.replacement_text is not None:
                try:
                    engine.validate_replacement(step.search_text, step.replacement_text, options)
                except (re.error, IndexError) as error:
                    diagnostics.append(cls._error(
                        "invalid_replacement", "macro.validation.invalid_replacement",
                        step_index=step_index, field_name="replacement_text",
                        values={"error": str(error)},
                    ))
        return diagnostics

    @classmethod
    def _validate_regular_expressions(
        cls,
        step: MacroJsonStepData,
        step_index: int,
    ) -> list[MacroDiagnostic]:
        """正規表現の検索および除外パターンを検証し、診断結果を返す。"""
        diagnostics: list[MacroDiagnostic] = []
        try:
            re.compile(step.search_text)
        except re.error as error:
            diagnostics.append(
                cls._error(
                    "invalid_search_regex",
                    "macro.validation.invalid_search_regex",
                    step_index=step_index,
                    field_name="search_text",
                    values={"error": str(error)},
                )
            )
        if step.exclusion_text:
            try:
                re.compile(step.exclusion_text)
            except re.error as error:
                diagnostics.append(
                    cls._error(
                        "invalid_exclusion_regex",
                        "macro.validation.invalid_exclusion_regex",
                        step_index=step_index,
                        field_name="exclusion_text",
                        values={"error": str(error)},
                    )
                )
        return diagnostics

    @classmethod
    def _validate_replacement_route(
        cls,
        step: MacroJsonStepData,
        step_index: int,
        format_version: int,
    ) -> list[MacroDiagnostic]:
        """置換ルートの構成を検証し、診断結果を返す。"""
        diagnostics: list[MacroDiagnostic] = []
        if step.unicode_normalize:
            if step.unicode_normalize_form is None:
                diagnostics.append(
                    cls._error(
                        "missing_unicode_normalize_form",
                        "macro.validation.missing_unicode_normalize_form",
                        step_index=step_index,
                        field_name="unicode_normalize_form",
                    )
                )
            if step.replacement_text is not None:
                diagnostics.append(
                    cls._error(
                        "replacement_with_unicode_normalize",
                        "macro.validation.replacement_with_unicode_normalize",
                        step_index=step_index,
                        field_name="replacement_text",
                    )
                )
        else:
            if step.unicode_normalize_form is not None:
                diagnostics.append(
                    cls._warning(
                        "unused_unicode_normalize_form",
                        "macro.validation.unused_unicode_normalize_form",
                        step_index=step_index,
                        field_name="unicode_normalize_form",
                    )
                )
            if step.replacement_text is None:
                diagnostics.append(
                    cls._error(
                        "missing_replacement_text",
                        "macro.validation.missing_replacement_text",
                        step_index=step_index,
                        field_name="replacement_text",
                    )
                )

        if step.append_dot_to_circled_number and (
            (format_version == 1 and not step.unicode_normalize)
            or (step.unicode_normalize and step.unicode_normalize_form not in APPEND_DOT_NORMALIZATION_FORMS)
        ):
            diagnostics.append(
                cls._error(
                    "invalid_append_dot_configuration",
                    "macro.validation.invalid_append_dot_configuration",
                    step_index=step_index,
                    field_name="append_dot_to_circled_number",
                )
            )
        return diagnostics

    @staticmethod
    def _error(
        code: str,
        message_key: str,
        *,
        step_index: int | None = None,
        field_name: str | None = None,
        values: dict[str, Any] | None = None,
    ) -> MacroDiagnostic:
        """診断結果をエラーとして返す。"""
        return MacroDiagnostic(
            severity=MacroDiagnosticSeverity.ERROR,
            code=code,
            message_key=message_key,
            step_index=step_index,
            field_name=field_name,
            values=values or {},
        )

    @staticmethod
    def _warning(
        code: str,
        message_key: str,
        *,
        step_index: int | None = None,
        field_name: str | None = None,
        values: dict[str, Any] | None = None,
    ) -> MacroDiagnostic:
        """診断結果を警告として返す。"""
        return MacroDiagnostic(
            severity=MacroDiagnosticSeverity.WARNING,
            code=code,
            message_key=message_key,
            step_index=step_index,
            field_name=field_name,
            values=values or {},
        )
