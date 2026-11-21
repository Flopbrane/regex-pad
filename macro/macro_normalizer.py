"""ユーザーの式を書き換えることなく、安全な擬似マクロのデフォルトを標準化する。"""

from __future__ import annotations

from macro.json_data_model import MacroJsonData, MacroJsonStepData


class MacroNormalizer:
    """ユーザーのテキストをすべて保持したまま、独立したカノニカルモデルを作成する。"""

    @staticmethod
    def normalize(load_data: MacroJsonData) -> MacroJsonData:
        """意味的な修正を行わず、モデルの独立したコピーを返す。

        バージョン1では現在、すべてのJSONフィールドが必須となっているため、デフォルト値を挿入する必要はない。
        この境界は将来的なフォーマット移行を見据えたものであり、
        空文字列、``None``、空白、改行、バックスラッシュ、全角文字を、
        入力されたそのままの状態で保持するよう意図されている。
        """
        if not isinstance(load_data, MacroJsonData):
            raise TypeError("load_data must be MacroJsonData")

        normalized_steps: tuple[MacroJsonStepData, ...] = tuple(
            MacroJsonStepData(
                step_name=step.step_name,
                enabled=step.enabled,
                regular_expression=step.regular_expression,
                unicode_normalize=step.unicode_normalize,
                unicode_normalize_form=step.unicode_normalize_form,
                append_dot_to_circled_number=step.append_dot_to_circled_number,
                search_text=step.search_text,
                exclusion_text=step.exclusion_text,
                replacement_text=step.replacement_text,
                case_sensitive=step.case_sensitive,
                whole_word=step.whole_word,
                selected_only=step.selected_only,
                visible_only=step.visible_only,
                replacement_input_text=step.replacement_input_text,
            )
            for step in load_data.steps
        )
        return MacroJsonData(
            format_version=load_data.format_version,
            macro_name=load_data.macro_name,
            description=load_data.description,
            steps=normalized_steps,
        )
