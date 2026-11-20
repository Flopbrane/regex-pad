"""Editable GUI data, separate from the persisted macro model."""

from dataclasses import dataclass, field

from unicode_normalize import NormalizationForm


@dataclass(slots=True)
class MacroEditorStepData:
    step_name: str = "step_1"
    enabled: bool = True
    regular_expression: bool = False
    unicode_normalize: bool = False
    unicode_normalize_form: NormalizationForm | None = None
    append_dot_to_circled_number: bool = False
    search_text: str = ""
    exclusion_enabled: bool = False
    exclusion_text: str = ""
    replacement_enabled: bool = True
    replacement_text: str = ""


@dataclass(slots=True)
class MacroEditorDocumentData:
    format_version: int = 1
    macro_name: str = ""
    description: str = ""
    steps: list[MacroEditorStepData] = field(
        default_factory=lambda: [MacroEditorStepData()]
    )
