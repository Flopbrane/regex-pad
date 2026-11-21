"""ファイル、GUI、および非GUIの各マクロ呼び出し元に対する共通の司令塔。"""

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
    """マクロの検証に失敗した場合に送出される例外。"""
    def __init__(self, validation: MacroValidationResult) -> None:
        super().__init__("macro validation failed")
        self.validation: MacroValidationResult = validation


class MacroManager:
    """ファイル、GUI、および非GUIの各マクロ呼び出し元に対する共通の司令塔。"""
    def __init__(
        self, macro_folder: Path | None = None, runner: MacroRunner | None = None
    ) -> None:
        self.loader: MacroJsonLoader = MacroJsonLoader(macro_folder)
        self.saver: MacroJsonSaver = MacroJsonSaver(macro_folder)
        self.runner: MacroRunner = runner or MacroRunner()

    def prepare_macro(self, model: MacroJsonData) -> MacroPreparation:
        """マクロの準備状態を作成する。"""
        return MacroCompiler.prepare(model)

    def validate_macro(self, model: MacroJsonData) -> MacroValidationResult:
        """マクロの検証結果を取得する。"""
        return self.prepare_macro(model).validation

    def load_macro(self, load_file_path: str | Path) -> MacroPreparation:
        """絶対パス、または ``macro_folder`` からの相対パスを1つ読み込みます。"""
        return self.prepare_macro(self.loader.load(load_file_path))

    def save_macro(self, model: MacroJsonData, save_file_path: str | Path) -> Path:
        """モデルを保存し、確定した保存先パスを返す。"""
        prepared: MacroPreparation = self.prepare_macro(model)
        if not prepared.validation.is_valid:
            raise MacroValidationError(prepared.validation)
        return self.saver.save(prepared.model, save_file_path)

    def execute_macro(
        self, model: MacroJsonData, source_text: str,
        selected_scope: tuple[int, int] | None = None,
        visible_scope: tuple[int, int] | None = None,
    ) -> MacroRunResult:
        """マクロを実行し、結果を返す。"""
        prepared: MacroPreparation = self.prepare_macro(model)
        if prepared.definition is None:
            return MacroRunResult(
                source_text, source_text, (), prepared.validation, False
            )
        result: MacroRunResult = self.runner.run(
            prepared.definition, source_text, selected_scope, visible_scope
        )
        return replace(
            result,
            validation=MacroLinter.combine(prepared.validation, result.validation),
        )

    def preview_macro(
        self, model: MacroJsonData, source_text: str,
        selected_scope: tuple[int, int] | None = None,
        visible_scope: tuple[int, int] | None = None,
    ) -> MacroPreview:
        """マクロを実行し、結果を返す。"""
        return MacroPreview(
            model.macro_name,
            self.execute_macro(model, source_text, selected_scope, visible_scope),
        )
