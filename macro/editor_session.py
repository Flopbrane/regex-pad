"""単一の独立したマクロエディタの状態。"""

from dataclasses import dataclass, field
from pathlib import Path

from macro.editor_data_model import MacroEditorDocumentData
from macro.json_paths import default_macro_folder
from macro.validation_types import MacroValidationResult


@dataclass(slots=True)
class MacroEditorSession:
    """単一の独立したマクロエディタの状態。"""
    document: MacroEditorDocumentData = field(default_factory=MacroEditorDocumentData)
    load_file_path: Path | None = None
    save_file_path: Path | None = None
    macro_folder: Path = field(default_factory=default_macro_folder)
    modified: bool = False
    validation_result: MacroValidationResult = field(
        default_factory=MacroValidationResult
    )
