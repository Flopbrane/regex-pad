from __future__ import annotations

from pathlib import Path

from macro.json_data_model import MacroJsonData, MacroJsonStepData
from macro.json_loader import MacroJsonLoader
from macro.macro_normalizer import MacroNormalizer
from macro.macro_validator import MacroValidator
from macro.validation_types import MacroDiagnosticSeverity, MacroValidationResult
from unicode_normalize import NormalizationForm


def _step(
    *,
    step_name: str = "replace",
    enabled: bool = True,
    regular_expression: bool = False,
    unicode_normalize: bool = False,
    unicode_normalize_form: NormalizationForm | None = None,
    append_dot_to_circled_number: bool = False,
    search_text: str = "before",
    exclusion_text: str | None = None,
    replacement_text: str | None = "after",
) -> MacroJsonStepData:
    return MacroJsonStepData(
        step_name=step_name,
        enabled=enabled,
        regular_expression=regular_expression,
        unicode_normalize=unicode_normalize,
        unicode_normalize_form=unicode_normalize_form,
        append_dot_to_circled_number=append_dot_to_circled_number,
        search_text=search_text,
        exclusion_text=exclusion_text,
        replacement_text=replacement_text,
    )


def _model(*steps: MacroJsonStepData) -> MacroJsonData:
    return MacroJsonData(1, "Macro", "Description", steps or (_step(),))


def _codes(result: MacroValidationResult) -> list[str]:
    return [diagnostic.code for diagnostic in result.diagnostics]


def test_normalizer_returns_detached_copy_without_rewriting_user_text() -> None:
    source_step = _step(
        search_text="  \\d+\nＡＢＣ  ",
        exclusion_text="",
        replacement_text="",
    )
    source = _model(source_step)

    normalized = MacroNormalizer.normalize(source)
    source_step.search_text = "changed"

    assert normalized is not source
    assert normalized.steps[0] is not source_step
    assert normalized.steps[0].search_text == "  \\d+\nＡＢＣ  "
    assert normalized.steps[0].exclusion_text == ""
    assert normalized.steps[0].replacement_text == ""


def test_version_one_reference_macro_has_no_diagnostics() -> None:
    load_data = MacroJsonLoader(Path("macro")).load("macro_format_v1.json")

    result = MacroValidator.validate(MacroNormalizer.normalize(load_data))

    assert result.is_valid
    assert result.diagnostics == ()


def test_validator_reports_root_errors_together() -> None:
    load_data = MacroJsonData(3, "   ", "", ())

    result = MacroValidator.validate(load_data)

    assert not result.is_valid
    assert _codes(result) == [
        "unsupported_format_version",
        "empty_macro_name",
        "no_steps",
    ]
    assert all(
        diagnostic.severity is MacroDiagnosticSeverity.ERROR
        for diagnostic in result.errors
    )


def test_disabled_steps_do_not_block_execution_but_report_no_enabled_steps() -> None:
    load_data = _model(
        _step(
            enabled=False,
            regular_expression=True,
            search_text="[",
            replacement_text=None,
        )
    )

    result = MacroValidator.validate(load_data)

    assert result.is_valid
    assert _codes(result) == ["no_enabled_steps"]
    assert result.warnings[0].severity is MacroDiagnosticSeverity.WARNING


def test_validator_reports_duplicate_step_names_for_each_step() -> None:
    result = MacroValidator.validate(_model(_step(), _step()))

    assert not result.is_valid
    assert _codes(result) == ["duplicate_step_name", "duplicate_step_name"]
    assert [diagnostic.step_index for diagnostic in result.errors] == [0, 1]


def test_validator_reports_invalid_search_and_exclusion_regex() -> None:
    result = MacroValidator.validate(
        _model(
            _step(
                regular_expression=True,
                search_text="[",
                exclusion_text="(",
            )
        )
    )

    assert not result.is_valid
    assert _codes(result) == ["invalid_search_regex", "invalid_exclusion_regex"]
    assert [diagnostic.field_name for diagnostic in result.errors] == [
        "search_text",
        "exclusion_text",
    ]


def test_validator_enforces_replacement_route_relationships() -> None:
    unicode_result = MacroValidator.validate(
        _model(
            _step(
                unicode_normalize=True,
                unicode_normalize_form=None,
                replacement_text="must be null",
            )
        )
    )
    replacement_result = MacroValidator.validate(
        _model(
            _step(
                unicode_normalize=False,
                unicode_normalize_form="NFC",
                append_dot_to_circled_number=True,
                replacement_text=None,
            )
        )
    )

    assert _codes(unicode_result) == [
        "missing_unicode_normalize_form",
        "replacement_with_unicode_normalize",
    ]
    assert _codes(replacement_result) == [
        "unused_unicode_normalize_form",
        "missing_replacement_text",
        "invalid_append_dot_configuration",
    ]
    assert len(replacement_result.warnings) == 1
    assert len(replacement_result.errors) == 2
