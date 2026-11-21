"""結果は不変のものとして確認済みです。プレビューを適用する際、マクロが再実行されてはなりません。"""

from dataclasses import dataclass

from macro.macro_runner import MacroRunResult


@dataclass(frozen=True, slots=True)
class MacroPreview:
    """マクロの実行結果を表す。"""
    macro_name: str
    result: MacroRunResult

    @property
    def can_apply(self) -> bool:
        """マクロの実行結果が、プレビューを適用するのに十分であるかどうかを返す。"""
        return self.result.succeeded and self.result.text != self.result.original_text
