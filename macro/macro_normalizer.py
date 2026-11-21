"""Normalize safe pseudo-macro defaults without rewriting user expressions."""

from __future__ import annotations

from macro.json_data_model import MacroJsonData, MacroJsonStepData


class MacroNormalizer:
    """Create a detached canonical model while preserving all user text."""

    @staticmethod
    def normalize(load_data: MacroJsonData) -> MacroJsonData:
        """Return a detached model copy without semantic correction.

        Version 1 currently requires every JSON field, so no default needs to
        be inserted.  This boundary exists for future format migrations and
        deliberately preserves empty strings, ``None``, whitespace, newlines,
        backslashes and full-width characters exactly as supplied.
        """
        if not isinstance(load_data, MacroJsonData):
            raise TypeError("load_data must be MacroJsonData")

        normalized_steps: tuple[MacroJsonStepData, ...] = tuple(
            MacroJsonStepData(
                step_name=step.step_name,
                enabled=step.enabled,
                regular_expression=step.regular_expression,
                unicode_normalize=step.unicode_normalize,
                unicode_normalize_form=step.unicode_normalize_form,
                append_dot_to_circled_number=step.append_dot_to_circled_number,
                search_text=step.search_text,
                exclusion_text=step.exclusion_text,
                replacement_text=step.replacement_text,
                case_sensitive=step.case_sensitive,
                whole_word=step.whole_word,
                selected_only=step.selected_only,
                visible_only=step.visible_only,
                replacement_input_text=step.replacement_input_text,
            )
            for step in load_data.steps
        )
        return MacroJsonData(
            format_version=load_data.format_version,
            macro_name=load_data.macro_name,
            description=load_data.description,
            steps=normalized_steps,
        )
