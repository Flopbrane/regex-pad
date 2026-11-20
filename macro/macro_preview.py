"""Immutable reviewed result; applying a preview must not rerun the macro."""

from dataclasses import dataclass

from macro.macro_runner import MacroRunResult


@dataclass(frozen=True, slots=True)
class MacroPreview:
    macro_name: str
    result: MacroRunResult

    @property
    def can_apply(self) -> bool:
        return self.result.succeeded and self.result.text != self.result.original_text
