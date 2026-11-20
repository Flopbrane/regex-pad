"""Shared orchestration for file, GUI and non-GUI macro callers."""

from dataclasses import replace
from pathlib import Path

from macro.json_data_model import MacroJsonData
from macro.json_loader import MacroJsonLoader
from macro.json_saver import MacroJsonSaver
from macro.macro_linter import MacroLinter
from macro.macro_model import MacroCompiler, MacroPreparation
from macro.macro_preview import MacroPreview
from macro.macro_runner import MacroRunner, MacroRunResult
from macro.validation_types import MacroValidationResult


class MacroValidationError(ValueError):
    def __init__(self, validation: MacroValidationResult) -> None:
        super().__init__("macro validation failed")
        self.validation = validation


class MacroManager:
    def __init__(
        self, macro_folder: Path | None = None, runner: MacroRunner | None = None
    ) -> None:
        self.loader = MacroJsonLoader(macro_folder)
        self.saver = MacroJsonSaver(macro_folder)
        self.runner = runner or MacroRunner()

    def prepare_macro(self, model: MacroJsonData) -> MacroPreparation:
        return MacroCompiler.prepare(model)

    def validate_macro(self, model: MacroJsonData) -> MacroValidationResult:
        return self.prepare_macro(model).validation

    def load_macro(self, load_file_path: str | Path) -> MacroPreparation:
        return self.prepare_macro(self.loader.load(load_file_path))

    def save_macro(self, model: MacroJsonData, save_file_path: str | Path) -> Path:
        prepared = self.prepare_macro(model)
        if not prepared.validation.is_valid:
            raise MacroValidationError(prepared.validation)
        return self.saver.save(prepared.model, save_file_path)

    def execute_macro(self, model: MacroJsonData, source_text: str) -> MacroRunResult:
        prepared = self.prepare_macro(model)
        if prepared.definition is None:
            return MacroRunResult(
                source_text, source_text, (), prepared.validation, False
            )
        result = self.runner.run(prepared.definition, source_text)
        return replace(
            result,
            validation=MacroLinter.combine(prepared.validation, result.validation),
        )

    def preview_macro(self, model: MacroJsonData, source_text: str) -> MacroPreview:
        return MacroPreview(model.macro_name, self.execute_macro(model, source_text))
