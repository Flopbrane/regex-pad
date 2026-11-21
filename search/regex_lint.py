
"""正規化表現の構文を検証するためのモジュールです。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern

from search.search_engine import convert_dollar_replacement_references


@dataclass(frozen=True)
class RegexLintMessage:
    """正規化表現の構文検証メッセージを表す。"""
    severity: str
    message_key: str
    values: dict[str, str] | None = None

    @property
    def message(self) -> str:
        """メッセージの文字列を返す。"""
        if self.values:
            values = ", ".join(self.values.values())
            return f"{self.message_key}: {values}"
        return self.message_key


class RegexLint:
    """正規化表現の構文を検証するためのクラス。"""
    def lint(
        self,
        pattern_text: str,
        replacement_text: str = "",
        *,
        check_replacement: bool = False,
    ) -> list[RegexLintMessage]:
        """正規化表現の構文を検証し、メッセージのリストを返す。"""
        messages: list[RegexLintMessage] = []
        if not pattern_text:
            return [RegexLintMessage("warning", "regex_lint.empty")]

        pattern: Pattern[str] | None = self._compile_pattern(pattern_text, messages)
        if pattern is None:
            return messages

        self._warn_about_empty_matches(pattern, messages)
        self._warn_about_broad_patterns(pattern_text, messages)
        self._warn_about_common_confusions(pattern_text, messages)

        if check_replacement:
            self._check_replacement(pattern, replacement_text, messages)

        return messages

    def _compile_pattern(
        self,
        pattern_text: str,
        messages: list[RegexLintMessage],
    ) -> Pattern[str] | None:
        """正規化表現のパターンをコンパイルし、エラーがあればメッセージを追加する。"""
        try:
            return re.compile(pattern_text)
        except re.error as error:
            messages.append(
                RegexLintMessage(
                    "error",
                    "regex_lint.invalid_regex",
                    {"error": str(error)},
                )
            )
            return None

    def _warn_about_empty_matches(
        self,
        pattern: Pattern[str],
        messages: list[RegexLintMessage],
    ) -> None:
        """空マッチについて警告する。"""
        if pattern.match("") is not None:
            messages.append(
                RegexLintMessage(
                    "warning",
                    "regex_lint.empty_match",
                )
            )

    def _warn_about_broad_patterns(
        self,
        pattern_text: str,
        messages: list[RegexLintMessage],
    ) -> None:
        """広すぎるパターンについて警告する。"""
        if pattern_text in {".*", ".*?", "^.*$", "^.*?$"}:
            messages.append(
                RegexLintMessage(
                    "warning",
                    "regex_lint.broad",
                )
            )
        if pattern_text.startswith(".*") and len(pattern_text) > 2:
            messages.append(
                RegexLintMessage(
                    "warning",
                    "regex_lint.leading_dot_star",
                )
            )

    def _warn_about_common_confusions(
        self,
        pattern_text: str,
        messages: list[RegexLintMessage],
    ) -> None:
        """一般的な混同について警告する。"""
        if self._has_unescaped_dot(pattern_text):
            messages.append(
                RegexLintMessage(
                    "warning",
                    "regex_lint.unescaped_dot",
                )
            )
        if "\\n" in pattern_text:
            messages.append(
                RegexLintMessage(
                    "warning",
                    "regex_lint.backslash_n",
                )
            )
        if "¥" in pattern_text:
            messages.append(
                RegexLintMessage(
                    "warning",
                    "regex_lint.yen_sign_escape",
                )
            )
        if pattern_text.endswith("\\"):
            messages.append(
                RegexLintMessage(
                    "warning",
                    "regex_lint.trailing_escape",
                )
            )

    def _check_replacement(
        self,
        pattern: Pattern[str],
        replacement_text: str,
        messages: list[RegexLintMessage],
    ) -> None:
        """置換テキストの構文を検証し、エラーがあればメッセージを追加する。"""
        replacement_text = convert_dollar_replacement_references(replacement_text)
        try:
            pattern.sub(replacement_text, "", count=1)
        except re.error as error:
            messages.append(
                RegexLintMessage(
                    "error",
                    "regex_lint.invalid_replacement",
                    {"error": str(error)},
                )
            )
        if pattern.groups == 0 and re.search(r"\\[1-9]", replacement_text):
            messages.append(
                RegexLintMessage(
                    "warning",
                    "regex_lint.backref_without_group",
                )
            )

    def _has_unescaped_dot(self, pattern_text: str) -> bool:
        """パターンにエスケープされていないドットが含まれているかどうかを判定する。"""
        escaped = False
        in_character_class = False
        for character in pattern_text:
            if escaped:
                escaped = False
                continue
            if character == "\\":
                escaped = True
                continue
            if character == "[":
                in_character_class = True
                continue
            if character == "]":
                in_character_class = False
                continue
            if character == "." and not in_character_class:
                return True
        return False
