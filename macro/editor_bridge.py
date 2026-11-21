"""Lossless conversion between editor state and macro JSON models."""

from macro.editor_data_model import MacroEditorDocumentData, MacroEditorStepData
from macro.json_data_model import MacroJsonData, MacroJsonStepData
from unicode_normalize import NORMALIZATION_FORMS


class MacroEditorInputError(ValueError):
    """An editor value that can be mapped back to a particular field."""

    def __init__(self, step_index: int, field_name: str, message: str) -> None:
        super().__init__(message)
        self.step_index = step_index
        self.field_name = field_name


class MacroEditorBridge:
    @staticmethod
    def from_json_model(model: MacroJsonData) -> MacroEditorDocumentData:
        return MacroEditorDocumentData(
            model.format_version,
            model.macro_name,
            model.description,
            [
                MacroEditorStepData(
                    step.step_name,
                    step.enabled,
                    step.regular_expression,
                    step.unicode_normalize,
                    step.unicode_normalize_form,
                    step.append_dot_to_circled_number,
                    step.search_text,
                    step.exclusion_text is not None,
                    step.exclusion_text or "",
                    step.replacement_text is not None,
                    step.replacement_input_text
                    if step.replacement_input_text is not None else (step.replacement_text or ""),
                    step.case_sensitive,
                    step.whole_word,
                    step.selected_only,
                    step.visible_only,
                    step.replacement_text,
                )
                for step in model.steps
            ],
        )

    @staticmethod
    def to_json_model(document: MacroEditorDocumentData) -> MacroJsonData:
        if document.format_version == 1 and any(
            step.case_sensitive or step.whole_word or step.selected_only or step.visible_only
            for step in document.steps
        ):
            raise MacroEditorInputError(-1, "format_version", "Search scope options require format version 2")
        for index, step in enumerate(document.steps):
            if (
                step.unicode_normalize_form is not None
                and step.unicode_normalize_form not in NORMALIZATION_FORMS
            ):
                raise MacroEditorInputError(
                    index, "unicode_normalize_form", str(step.unicode_normalize_form)
                )
        return MacroJsonData(
            document.format_version,
            document.macro_name,
            document.description,
            [
                MacroJsonStepData(
                    step.step_name,
                    step.enabled,
                    step.regular_expression,
                    step.unicode_normalize,
                    step.unicode_normalize_form,
                    step.append_dot_to_circled_number,
                    step.search_text,
                    step.exclusion_text if step.exclusion_enabled else None,
                    step.replacement_text if step.replacement_enabled else None,
                    step.case_sensitive,
                    step.whole_word,
                    step.selected_only,
                    step.visible_only,
                )
                for step in document.steps
            ],
        )
