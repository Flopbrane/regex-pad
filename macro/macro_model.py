"""Immutable execution definitions compiled only after model validation."""

from dataclasses import dataclass

from macro.json_data_model import MacroJsonData
from macro.macro_normalizer import MacroNormalizer
from macro.macro_validator import MacroValidator
from macro.validation_types import MacroValidationResult
from search.search_engine import SearchOptions


@dataclass(frozen=True, slots=True)
class MacroStep:
    step_index: int
    step_name: str
    enabled: bool
    search_text: str
    replacement_text: str
    options: SearchOptions


@dataclass(frozen=True, slots=True)
class MacroDefinition:
    macro_name: str
    description: str
    steps: tuple[MacroStep, ...]


@dataclass(frozen=True, slots=True)
class MacroPreparation:
    model: MacroJsonData
    validation: MacroValidationResult
    definition: MacroDefinition | None


class MacroCompiler:
    @staticmethod
    def prepare(model: MacroJsonData) -> MacroPreparation:
        normalized = MacroNormalizer.normalize(model)
        validation = MacroValidator.validate(normalized)
        if not validation.is_valid:
            return MacroPreparation(normalized, validation, None)
        steps = tuple(
            MacroStep(
                index,
                step.step_name,
                step.enabled,
                step.search_text,
                step.replacement_text or "",
                SearchOptions(
                    case_sensitive=step.case_sensitive,
                    regular_expression=step.regular_expression,
                    whole_word=step.whole_word,
                    selected_only=step.selected_only,
                    visible_only=step.visible_only,
                    exclusion_text=step.exclusion_text or "",
                    unicode_normalize=step.unicode_normalize,
                    unicode_normalize_form=step.unicode_normalize_form or "NFKC",
                    append_dot_to_circled_number=step.append_dot_to_circled_number,
                ),
            )
            for index, step in enumerate(normalized.steps)
        )
        return MacroPreparation(
            normalized,
            validation,
            MacroDefinition(
                normalized.macro_name,
                normalized.description,
                steps,
            ),
        )
