"""Convert pseudo-macro JSON dictionaries to and from file data models."""

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


class MacroJsonBridgeError(ValueError):
    """Raised when JSON data cannot be represented by the file data model."""


class MacroJsonBridge:
    """Perform structural ``dict`` and dataclass conversion only."""

    @classmethod
    def from_dict(cls, load_data: object) -> MacroJsonData:
        """Convert a decoded JSON object into ``MacroJsonData``."""
        root = cls._require_mapping(load_data, "root")
        cls._require_exact_keys(root, ROOT_KEYS, "root")
        raw_steps = root[STEPS_KEY]
        if not isinstance(raw_steps, list):
            raise MacroJsonBridgeError(f"{STEPS_KEY} must be list")

        steps = tuple(
            cls._step_from_dict(step_data, step_index)
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
        """Convert ``MacroJsonData`` into an ordered JSON-compatible dictionary."""
        if not isinstance(save_data, MacroJsonData):
            raise TypeError("save_data must be MacroJsonData")
        return {
            FORMAT_VERSION_KEY: save_data.format_version,
            MACRO_NAME_KEY: save_data.macro_name,
            DESCRIPTION_KEY: save_data.description,
            STEPS_KEY: [cls._step_to_dict(step) for step in save_data.steps],
        }

    @classmethod
    def _step_from_dict(
        cls,
        step_data: object,
        step_index: int,
    ) -> MacroJsonStepData:
        step = cls._require_mapping(step_data, f"{STEPS_KEY}[{step_index}]")
        cls._require_exact_keys(step, STEP_KEYS, f"{STEPS_KEY}[{step_index}]")
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
            )
        except (TypeError, ValueError) as error:
            raise MacroJsonBridgeError(
                f"invalid value in {STEPS_KEY}[{step_index}]: {error}"
            ) from error

    @staticmethod
    def _step_to_dict(step: MacroJsonStepData) -> dict[str, object]:
        if not isinstance(step, MacroJsonStepData):
            raise TypeError("steps must contain only MacroJsonStepData")
        return {
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

    @staticmethod
    def _require_mapping(value: object, location: str) -> Mapping[str, object]:
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
        actual_keys = frozenset(value)
        missing_keys = expected_keys - actual_keys
        unknown_keys = actual_keys - expected_keys
        if missing_keys:
            raise MacroJsonBridgeError(
                f"{location} is missing keys: {', '.join(sorted(missing_keys))}"
            )
        if unknown_keys:
            raise MacroJsonBridgeError(
                f"{location} has unknown keys: {', '.join(sorted(unknown_keys))}"
            )
