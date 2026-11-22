# pylint: disable=C0301
"""擬似マクロ形式のJSON辞書を、ファイルデータモデルとの間で相互変換する。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from macro.json_data_model import MacroJsonData, MacroJsonStepData
from unicode_normalize import NormalizationForm

FORMAT_VERSION_KEY: Final = "形式バージョン"
MACRO_NAME_KEY: Final = "マクロ名"
DESCRIPTION_KEY: Final = "説明"
STEPS_KEY: Final = "手順"

STEP_NAME_KEY: Final = "手順名"
ENABLED_KEY: Final = "有効"
REGULAR_EXPRESSION_KEY: Final = "正規表現"
UNICODE_NORMALIZE_KEY: Final = "Unicode正規化"
UNICODE_NORMALIZE_FORM_KEY: Final = "Unicode正規化形式"
APPEND_DOT_KEY: Final = "丸数字変換後ピリオド追加"
SEARCH_TEXT_KEY: Final = "検索文字列"
EXCLUSION_TEXT_KEY: Final = "除外文字列"
REPLACEMENT_TEXT_KEY: Final = "置換文字列"
CASE_SENSITIVE_KEY: Final = "大文字小文字を区別"
WHOLE_WORD_KEY: Final = "単語単位"
SELECTED_ONLY_KEY: Final = "選択範囲のみ"
VISIBLE_ONLY_KEY: Final = "表示範囲のみ"
REPLACEMENT_INPUT_KEY: Final = "置換欄の入力"
OPERATION_KEY: Final = "処理種別"

ROOT_KEYS: Final = frozenset(
    {FORMAT_VERSION_KEY, MACRO_NAME_KEY, DESCRIPTION_KEY, STEPS_KEY}
)
STEP_KEYS: Final = frozenset(
    {
        STEP_NAME_KEY,
        ENABLED_KEY,
        REGULAR_EXPRESSION_KEY,
        UNICODE_NORMALIZE_KEY,
        UNICODE_NORMALIZE_FORM_KEY,
        APPEND_DOT_KEY,
        SEARCH_TEXT_KEY,
        EXCLUSION_TEXT_KEY,
        REPLACEMENT_TEXT_KEY,
    }
)
STEP_KEYS_V2: Final = STEP_KEYS | frozenset(
    {CASE_SENSITIVE_KEY, WHOLE_WORD_KEY, SELECTED_ONLY_KEY, VISIBLE_ONLY_KEY, REPLACEMENT_INPUT_KEY}
)
STEP_KEYS_V3: Final = STEP_KEYS_V2 | frozenset({OPERATION_KEY})


class MacroJsonBridgeError(ValueError):
    """JSONデータがファイルデータモデルで表現できない場合に発生します。"""

class MacroJsonBridge:
    """構造的な `dict` および dataclass への変換のみを行う。"""

    @classmethod
    def from_dict(cls, load_data: object) -> MacroJsonData:
        """デコード済みのJSONオブジェクトを ``MacroJsonData`` に変換する。"""

        root: Mapping[str, object] = cls._require_mapping(load_data, "root")
        cls._require_exact_keys(root, ROOT_KEYS, "root")
        raw_steps: object = root[STEPS_KEY]
        if not isinstance(raw_steps, list):
            raise MacroJsonBridgeError(f"{STEPS_KEY} must be list")

        steps: tuple[MacroJsonStepData, ...] = tuple(
            cls._step_from_dict(step_data, step_index, cast(int, root[FORMAT_VERSION_KEY]))
            for step_index, step_data in enumerate(raw_steps)
        )
        try:
            return MacroJsonData(
                format_version=cast(int, root[FORMAT_VERSION_KEY]),
                macro_name=cast(str, root[MACRO_NAME_KEY]),
                description=cast(str, root[DESCRIPTION_KEY]),
                steps=steps,
            )
        except (TypeError, ValueError) as error:
            raise MacroJsonBridgeError(f"invalid root value: {error}") from error

    @classmethod
    def to_dict(cls, save_data: MacroJsonData) -> dict[str, object]:
        """``MacroJsonData`` を、順序が保持されたJSON互換の辞書に変換します。"""

        if not isinstance(save_data, MacroJsonData):
            raise TypeError("save_data must be MacroJsonData")
        return {
            FORMAT_VERSION_KEY: save_data.format_version,
            MACRO_NAME_KEY: save_data.macro_name,
            DESCRIPTION_KEY: save_data.description,
            STEPS_KEY: [
                cls._step_to_dict(step, save_data.format_version)
                for step in save_data.steps
            ],
        }

    @classmethod
    def _step_from_dict(
        cls,
        step_data: object,
        step_index: int,
        format_version: int,
    ) -> MacroJsonStepData:
        """単一ステップの辞書を ``MacroJsonStepData`` に変換する。"""
        step: Mapping[str, object] = cls._require_mapping(step_data, f"{STEPS_KEY}[{step_index}]")
        cls._require_exact_keys(
            step,
            STEP_KEYS_V3 if format_version >= 3 else STEP_KEYS_V2 if format_version == 2 else STEP_KEYS,
            f"{STEPS_KEY}[{step_index}]",
        )
        try:
            return MacroJsonStepData(
                step_name=cast(str, step[STEP_NAME_KEY]),
                enabled=cast(bool, step[ENABLED_KEY]),
                regular_expression=cast(bool, step[REGULAR_EXPRESSION_KEY]),
                unicode_normalize=cast(bool, step[UNICODE_NORMALIZE_KEY]),
                unicode_normalize_form=cast(
                    NormalizationForm | None,
                    step[UNICODE_NORMALIZE_FORM_KEY],
                ),
                append_dot_to_circled_number=cast(bool, step[APPEND_DOT_KEY]),
                search_text=cast(str, step[SEARCH_TEXT_KEY]),
                exclusion_text=cast(str | None, step[EXCLUSION_TEXT_KEY]),
                replacement_text=cast(str | None, step[REPLACEMENT_TEXT_KEY]),
                case_sensitive=cast(bool, step[CASE_SENSITIVE_KEY]) if format_version >= 2 else False,
                whole_word=cast(bool, step[WHOLE_WORD_KEY]) if format_version >= 2 else False,
                selected_only=cast(bool, step[SELECTED_ONLY_KEY]) if format_version >= 2 else False,
                visible_only=cast(bool, step[VISIBLE_ONLY_KEY]) if format_version >= 2 else False,
                replacement_input_text=cast(str, step[REPLACEMENT_INPUT_KEY]) if format_version >= 2 else None,
                operation=cast(str, step[OPERATION_KEY]) if format_version >= 3 else "search_replace",
            )
        except (TypeError, ValueError) as error:
            raise MacroJsonBridgeError(
                f"invalid value in {STEPS_KEY}[{step_index}]: {error}"
            ) from error

    @staticmethod
    def _step_to_dict(step: MacroJsonStepData, format_version: int) -> dict[str, object]:
        """単一ステップの ``MacroJsonStepData`` を辞書に変換する。"""
        if not isinstance(step, MacroJsonStepData):
            raise TypeError("steps must contain only MacroJsonStepData")
        result: dict[str, object] = {
            STEP_NAME_KEY: step.step_name,
            ENABLED_KEY: step.enabled,
            REGULAR_EXPRESSION_KEY: step.regular_expression,
            UNICODE_NORMALIZE_KEY: step.unicode_normalize,
            UNICODE_NORMALIZE_FORM_KEY: step.unicode_normalize_form,
            APPEND_DOT_KEY: step.append_dot_to_circled_number,
            SEARCH_TEXT_KEY: step.search_text,
            EXCLUSION_TEXT_KEY: step.exclusion_text,
            REPLACEMENT_TEXT_KEY: step.replacement_text,
        }
        if format_version >= 2:
            result.update({
                CASE_SENSITIVE_KEY: step.case_sensitive,
                WHOLE_WORD_KEY: step.whole_word,
                SELECTED_ONLY_KEY: step.selected_only,
                VISIBLE_ONLY_KEY: step.visible_only,
                REPLACEMENT_INPUT_KEY: step.replacement_input_text
                if step.replacement_input_text is not None else (step.replacement_text or ""),
            })
        if format_version >= 3:
            result[OPERATION_KEY] = step.operation
        return result

    @staticmethod
    def _require_mapping(value: object, location: str) -> Mapping[str, object]:
        """値が辞書であることを確認し、キーがすべて文字列であることを検証する。"""
        if not isinstance(value, dict):
            raise MacroJsonBridgeError(f"{location} must be object")
        if not all(isinstance(key, str) for key in value):
            raise MacroJsonBridgeError(f"{location} keys must be str")
        return cast(Mapping[str, object], value)

    @staticmethod
    def _require_exact_keys(
        value: Mapping[str, object],
        expected_keys: frozenset[str],
        location: str,
    ) -> None:
        """値が指定されたキーの正確な集合を持つことを確認する。"""
        actual_keys: frozenset[str] = frozenset(value)
        missing_keys: frozenset[str] = expected_keys - actual_keys
        unknown_keys: frozenset[str] = actual_keys - expected_keys
        if missing_keys:
            raise MacroJsonBridgeError(
                f"{location} is missing keys: {', '.join(sorted(missing_keys))}"
            )
        if unknown_keys:
            raise MacroJsonBridgeError(
                f"{location} has unknown keys: {', '.join(sorted(unknown_keys))}"
            )
