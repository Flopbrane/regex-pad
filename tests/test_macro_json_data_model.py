from __future__ import annotations

from dataclasses import is_dataclass

import pytest

from macro.json_data_model import MacroJsonData, MacroJsonStepData
from unicode_normalize import NORMALIZATION_FORMS, NormalizationForm


def _step() -> MacroJsonStepData:
    return MacroJsonStepData(
        step_name="insert_@@@",
        enabled=True,
        regular_expression=True,
        unicode_normalize=False,
        unicode_normalize_form=None,
        append_dot_to_circled_number=False,
        search_text=r"(?m)^@@@$",
        exclusion_text=None,
        replacement_text="<div></div>",
    )


def test_macro_json_models_are_dataclasses_with_public_properties() -> None:
    step = _step()
    macro = MacroJsonData(1, "WordPress本文整形", "説明", [step])

    assert is_dataclass(step)
    assert is_dataclass(macro)
    assert step.step_name == "insert_@@@"
    assert step.enabled is True
    assert step.regular_expression is True
    assert step.unicode_normalize is False
    assert step.unicode_normalize_form is None
    assert step.append_dot_to_circled_number is False
    assert step.search_text == r"(?m)^@@@$"
    assert step.exclusion_text is None
    assert step.replacement_text == "<div></div>"
    assert macro.format_version == 1
    assert macro.macro_name == "WordPress本文整形"
    assert macro.description == "説明"
    assert macro.steps == (step,)


def test_macro_json_model_setters_update_every_field() -> None:
    first_step = _step()
    second_step = _step()
    first_step.step_name = "normalize"
    first_step.enabled = False
    first_step.regular_expression = False
    first_step.unicode_normalize = True
    first_step.unicode_normalize_form = "NFKC"
    first_step.append_dot_to_circled_number = True
    first_step.search_text = "Ａ"
    first_step.exclusion_text = "除外"
    first_step.replacement_text = None
    macro = MacroJsonData(1, "旧名", "旧説明", [second_step])
    macro.format_version = 2
    macro.macro_name = "新名"
    macro.description = "新説明"
    macro.steps = (first_step, second_step)

    assert first_step.step_name == "normalize"
    assert first_step.enabled is False
    assert first_step.regular_expression is False
    assert first_step.unicode_normalize is True
    assert first_step.unicode_normalize_form == "NFKC"
    assert first_step.append_dot_to_circled_number is True
    assert first_step.search_text == "Ａ"
    assert first_step.exclusion_text == "除外"
    assert first_step.replacement_text is None
    assert macro.format_version == 2
    assert macro.macro_name == "新名"
    assert macro.description == "新説明"
    assert macro.steps == (first_step, second_step)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("step_name", 1),
        ("enabled", 1),
        ("regular_expression", "true"),
        ("unicode_normalize", None),
        ("unicode_normalize_form", 1),
        ("append_dot_to_circled_number", 1),
        ("search_text", []),
        ("exclusion_text", False),
        ("replacement_text", 1),
    ],
)
def test_macro_json_step_setters_reject_wrong_types(
    field_name: str,
    value: object,
) -> None:
    step = _step()

    with pytest.raises(TypeError):
        setattr(step, field_name, value)


@pytest.mark.parametrize("normalization_form", NORMALIZATION_FORMS)
def test_unicode_normalize_form_accepts_only_registered_literal_values(
    normalization_form: NormalizationForm,
) -> None:
    step = _step()

    step.unicode_normalize_form = normalization_form

    assert step.unicode_normalize_form == normalization_form


def test_unicode_normalize_form_rejects_unknown_string() -> None:
    step = _step()

    with pytest.raises(ValueError, match="NFC, NFD, NFKC, NFKD"):
        step.unicode_normalize_form = "NFCK"  # type: ignore[assignment]


def test_macro_json_data_rejects_wrong_types_and_step_contents() -> None:
    macro = MacroJsonData(1, "名前", "説明", [])

    with pytest.raises(TypeError):
        macro.format_version = True
    with pytest.raises(TypeError):
        macro.macro_name = 1  # type: ignore[assignment]
    with pytest.raises(TypeError):
        macro.description = None  # type: ignore[assignment]
    with pytest.raises(TypeError):
        macro.steps = [_step()]  # type: ignore[assignment]
    with pytest.raises(TypeError):
        macro.steps = (object(),)  # type: ignore[assignment]


def test_macro_json_data_copies_input_steps_to_an_immutable_tuple() -> None:
    step = _step()
    source_steps = [step]
    macro = MacroJsonData(1, "名前", "説明", source_steps)

    source_steps.clear()

    assert macro.steps == (step,)
