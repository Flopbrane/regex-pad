"""File-I/O dataclasses that mirror the pseudo-macro JSON version 1 format."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import LiteralString, cast

from unicode_normalize import NORMALIZATION_FORMS, NormalizationForm


def _string_value(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be str")
    return value


def _boolean_value(field_name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be bool")
    return value


def _integer_value(field_name: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be int")
    return value


def _optional_string_value(field_name: str, value: object) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{field_name} must be str or None")
    return value


def _optional_normalization_form_value(value: object) -> NormalizationForm | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("unicode_normalize_form must be str or None")
    if value not in NORMALIZATION_FORMS:
        allowed_values: LiteralString = ", ".join(NORMALIZATION_FORMS)
        raise ValueError(
            f"unicode_normalize_form must be one of {allowed_values} or None"
        )
    return cast(NormalizationForm, value)


@dataclass(slots=True, init=False)
class MacroJsonStepData:
    """Represent one step in a pseudo-macro JSON file."""

    _step_name: str
    _enabled: bool
    _regular_expression: bool
    _unicode_normalize: bool
    _unicode_normalize_form: NormalizationForm | None
    _append_dot_to_circled_number: bool
    _search_text: str
    _exclusion_text: str | None
    _replacement_text: str | None

    def __init__(
        self,
        step_name: str,
        enabled: bool,
        regular_expression: bool,
        unicode_normalize: bool,
        unicode_normalize_form: NormalizationForm | None,
        append_dot_to_circled_number: bool,
        search_text: str,
        exclusion_text: str | None,
        replacement_text: str | None,
    ) -> None:
        self.step_name = step_name
        self.enabled = enabled
        self.regular_expression = regular_expression
        self.unicode_normalize = unicode_normalize
        self.unicode_normalize_form = unicode_normalize_form
        self.append_dot_to_circled_number = append_dot_to_circled_number
        self.search_text = search_text
        self.exclusion_text = exclusion_text
        self.replacement_text = replacement_text

    @property
    def step_name(self) -> str:
        """Return the step name."""
        return self._step_name

    @step_name.setter
    def step_name(self, value: str) -> None:
        self._step_name = _string_value("step_name", value)

    @property
    def enabled(self) -> bool:
        """Return whether the step is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = _boolean_value("enabled", value)

    @property
    def regular_expression(self) -> bool:
        """Return whether search and exclusion text use regular expressions."""
        return self._regular_expression

    @regular_expression.setter
    def regular_expression(self, value: bool) -> None:
        self._regular_expression = _boolean_value("regular_expression", value)

    @property
    def unicode_normalize(self) -> bool:
        """Return whether matched text is Unicode-normalized."""
        return self._unicode_normalize

    @unicode_normalize.setter
    def unicode_normalize(self, value: bool) -> None:
        self._unicode_normalize = _boolean_value("unicode_normalize", value)

    @property
    def unicode_normalize_form(self) -> NormalizationForm | None:
        """Return the requested Unicode normalization form."""
        return self._unicode_normalize_form

    @unicode_normalize_form.setter
    def unicode_normalize_form(self, value: NormalizationForm | None) -> None:
        self._unicode_normalize_form = _optional_normalization_form_value(value)

    @property
    def append_dot_to_circled_number(self) -> bool:
        """Return whether converted circled numbers receive a trailing dot."""
        return self._append_dot_to_circled_number

    @append_dot_to_circled_number.setter
    def append_dot_to_circled_number(self, value: bool) -> None:
        self._append_dot_to_circled_number = _boolean_value(
            "append_dot_to_circled_number",
            value,
        )

    @property
    def search_text(self) -> str:
        """Return the search text exactly as supplied by the JSON data."""
        return self._search_text

    @search_text.setter
    def search_text(self, value: str) -> None:
        self._search_text = _string_value("search_text", value)

    @property
    def exclusion_text(self) -> str | None:
        """Return the exclusion text, or None when exclusion is unused."""
        return self._exclusion_text

    @exclusion_text.setter
    def exclusion_text(self, value: str | None) -> None:
        self._exclusion_text = _optional_string_value("exclusion_text", value)

    @property
    def replacement_text(self) -> str | None:
        """Return replacement text, or None when Unicode normalization is used."""
        return self._replacement_text

    @replacement_text.setter
    def replacement_text(self, value: str | None) -> None:
        self._replacement_text = _optional_string_value("replacement_text", value)


@dataclass(slots=True, init=False)
class MacroJsonData:
    """Represent a complete pseudo-macro JSON file."""

    _format_version: int
    _macro_name: str
    _description: str
    _steps: tuple[MacroJsonStepData, ...]

    def __init__(
        self,
        format_version: int,
        macro_name: str,
        description: str,
        steps: Sequence[MacroJsonStepData],
    ) -> None:
        self.format_version = format_version
        self.macro_name = macro_name
        self.description = description
        self.steps = tuple(steps)

    @property
    def format_version(self) -> int:
        """Return the pseudo-macro JSON format version."""
        return self._format_version

    @format_version.setter
    def format_version(self, value: int) -> None:
        self._format_version = _integer_value("format_version", value)

    @property
    def macro_name(self) -> str:
        """Return the macro name."""
        return self._macro_name

    @macro_name.setter
    def macro_name(self, value: str) -> None:
        self._macro_name = _string_value("macro_name", value)

    @property
    def description(self) -> str:
        """Return the macro description."""
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = _string_value("description", value)

    @property
    def steps(self) -> tuple[MacroJsonStepData, ...]:
        """Return the ordered macro steps as an immutable tuple."""
        return self._steps

    @steps.setter
    def steps(self, value: tuple[MacroJsonStepData, ...]) -> None:
        if not isinstance(value, tuple):
            raise TypeError("steps must be tuple[MacroJsonStepData, ...]")
        if not all(isinstance(step, MacroJsonStepData) for step in value):
            raise TypeError("steps must contain only MacroJsonStepData")
        self._steps = value
