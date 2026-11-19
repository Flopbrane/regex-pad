"""Pseudo-macro package for validated, previewable sequential text transformations."""

from macro.json_bridge import MacroJsonBridge, MacroJsonBridgeError
from macro.json_data_model import MacroJsonData, MacroJsonStepData
from macro.json_loader import MacroJsonLoader, MacroJsonLoadError
from macro.json_saver import MacroJsonSaveError, MacroJsonSaver
from macro.macro_normalizer import MacroNormalizer
from macro.macro_validator import MacroValidator
from macro.validation_types import (
    MacroDiagnostic,
    MacroDiagnosticSeverity,
    MacroValidationResult,
)

__all__ = [
    "MacroDiagnostic",
    "MacroDiagnosticSeverity",
    "MacroJsonBridge",
    "MacroJsonBridgeError",
    "MacroJsonData",
    "MacroJsonLoadError",
    "MacroJsonLoader",
    "MacroJsonSaveError",
    "MacroJsonSaver",
    "MacroJsonStepData",
    "MacroNormalizer",
    "MacroValidationResult",
    "MacroValidator",
]
