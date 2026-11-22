"""永続化されたマクロモデルとは分離された、編集可能なGUIデータ。"""

from dataclasses import dataclass, field

from unicode_normalize import NormalizationForm


@dataclass(slots=True)
class MacroEditorStepData:
    """エディターで編集可能な、単一のマクロステップのデータ。"""
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
    case_sensitive: bool = False
    whole_word: bool = False
    selected_only: bool = False
    visible_only: bool = False
    operation: str = "search_replace"


@dataclass(slots=True)
class MacroEditorDocumentData:
    """エディターで編集可能な、マクロ全体のデータ。"""
    format_version: int = 2
    macro_name: str = ""
    description: str = ""
    steps: list[MacroEditorStepData] = field(
        default_factory=lambda: [MacroEditorStepData()]
    )
