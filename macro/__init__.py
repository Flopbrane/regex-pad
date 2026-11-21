"""検証可能かつプレビュー可能な、一連のテキスト変換を行うための疑似マクロパッケージ。"""

from macro.json_bridge import MacroJsonBridge, MacroJsonBridgeError
from macro.json_data_model import MacroJsonData, MacroJsonStepData
from macro.json_loader import MacroJsonLoader, MacroJsonLoadError
from macro.json_saver import MacroJsonSaveError, MacroJsonSaver
from macro.macro_linter import MacroLinter
from macro.macro_manager import MacroManager, MacroValidationError
from macro.macro_model import (
    MacroCompiler,
    MacroDefinition,
    MacroPreparation,
    MacroStep,
)
from macro.macro_normalizer import MacroNormalizer
from macro.macro_parser import MacroJsonParseError, MacroParser
from macro.macro_preview import MacroPreview
from macro.macro_runner import MacroRunner, MacroRunResult, MacroStepResult
from macro.macro_validator import MacroValidator
from macro.validation_types import (
    MacroDiagnostic,
    MacroDiagnosticSeverity,
    MacroValidationResult,
)

__all__: list[str] = [
    "MacroCompiler",
    "MacroDefinition",
    "MacroDiagnostic",
    "MacroDiagnosticSeverity",
    "MacroJsonBridge",
    "MacroJsonBridgeError",
    "MacroJsonData",
    "MacroJsonLoadError",
    "MacroJsonLoader",
    "MacroJsonParseError",
    "MacroJsonSaveError",
    "MacroJsonSaver",
    "MacroJsonStepData",
    "MacroLinter",
    "MacroManager",
    "MacroNormalizer",
    "MacroParser",
    "MacroPreparation",
    "MacroPreview",
    "MacroRunResult",
    "MacroRunner",
    "MacroStep",
    "MacroStepResult",
    "MacroValidationError",
    "MacroValidationResult",
    "MacroValidator",
]
