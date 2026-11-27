"""regex_pad用検索・置換エンジン。"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, replace
from re import Match, Pattern

from unicode_normalize import NormalizationForm, normalize_matched_text


@dataclass(frozen=True)
class SearchOptions:
    """検索・置換のオプションを表す。"""
    case_sensitive: bool = False
    regular_expression: bool = False
    whole_word: bool = False
    selected_only: bool = False
    visible_only: bool = False
    exclusion_text: str = ""
    unicode_normalize: bool = False
    unicode_normalize_form: NormalizationForm = "NFKC"
    append_dot_to_circled_number: bool = False


@dataclass(frozen=True)
class SearchMatch:
    """検索結果のマッチを表す。"""
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class ReplaceResult:
    """置換結果を表す。"""
    text: str
    count: int


@dataclass(frozen=True)
class SearchAnalysis:
    """置換前のカウント（保護された一致やゼロ幅の一致を含む）。"""

    matches: int
    excluded: int
    zero_width: int


class SearchEngine:
    """検索・置換のためのエンジン。"""
    def analyze_matches(
        self, source_text: str, search_text: str, options: SearchOptions,
    ) -> SearchAnalysis:
        """ソーステキストを分析し、一致箇所、除外された一致箇所、およびゼロ幅の一致箇所を特定します。"""

        pattern: Pattern[str] = self._compile_pattern(search_text, options)
        excluded_ranges: list[tuple[int, int]] = self._excluded_ranges(source_text, options)
        matches: int = 0
        excluded: int = 0
        zero_width: int = 0
        for match in pattern.finditer(source_text):
            if match.start() == match.end():
                zero_width += 1
            else:
                matches += 1
                if self._is_excluded(match, excluded_ranges):
                    excluded += 1
        return SearchAnalysis(matches, excluded, zero_width)

    def validate_replacement(
        self, search_text: str, replace_text: str, options: SearchOptions,
    ) -> None:
        """ドキュメント内に一致するテキストがない場合でも、テンプレートを検証する."""

        if not options.unicode_normalize:
            pattern: Pattern[str] = self._compile_pattern(search_text, options)
            pattern.sub(self._replacement_text_for_options(replace_text, options), "")

    def find_all(
        self,
        source_text: str,
        search_text: str,
        options: SearchOptions | None = None,
        *,
        max_matches: int | None = None,
    ) -> list[SearchMatch]:
        """指定されたソーステキストから、一致するすべてのマッチを検索します。"""
        if not search_text:
            return []

        search_options: SearchOptions = options or SearchOptions()
        pattern: Pattern[str] = self._compile_pattern(search_text, search_options)
        excluded_ranges: list[tuple[int, int]] = self._excluded_ranges(source_text, search_options)
        matches: list[SearchMatch] = []
        for match in pattern.finditer(source_text):
            if match.start() == match.end() or self._is_excluded(match, excluded_ranges):
                continue
            matches.append(SearchMatch(match.start(), match.end(), match.group(0)))
            if max_matches is not None and len(matches) >= max_matches:
                break
        return matches

    def find_exclusion_matches(
        self,
        source_text: str,
        options: SearchOptions | None = None,
        *,
        max_matches: int | None = None,
    ) -> list[SearchMatch]:
        """マーカー表示用に、空ではない除外一致を返す。"""

        search_options: SearchOptions = options or SearchOptions()
        if not search_options.exclusion_text:
            return []

        excluded_ranges: list[tuple[int, int]] = self._excluded_ranges(source_text, search_options)
        matches: list[SearchMatch] = [
            SearchMatch(start, end, source_text[start:end])
            for start, end in excluded_ranges
        ]
        if max_matches is not None:
            return matches[:max_matches]
        return matches

    def find_next(
        self,
        source_text: str,
        search_text: str,
        start_position: int,
        options: SearchOptions | None = None,
    ) -> SearchMatch | None:
        """指定されたソーステキストから、次の一致を検索します。"""
        if not search_text:
            return None

        search_options: SearchOptions = options or SearchOptions()
        pattern: Pattern[str] = self._compile_pattern(search_text, search_options)
        excluded_ranges: list[tuple[int, int]] = self._excluded_ranges(source_text, search_options)
        bounded_start_position: int = min(max(start_position, 0), len(source_text))
        match: Match[str] | None = self._first_non_empty_match(
            pattern,
            source_text,
            bounded_start_position,
            excluded_ranges,
        )
        if match is None and bounded_start_position > 0:
            match = self._first_non_empty_match(pattern, source_text, 0, excluded_ranges)

        if match is None:
            return None
        return SearchMatch(match.start(), match.end(), match.group(0))

    def find_previous(
        self,
        source_text: str,
        search_text: str,
        start_position: int,
        options: SearchOptions | None = None,
    ) -> SearchMatch | None:
        """指定されたソーステキストから、前の一致を検索します。"""
        if not search_text:
            return None

        search_options: SearchOptions = options or SearchOptions()
        pattern: Pattern[str] = self._compile_pattern(search_text, search_options)
        excluded_ranges: list[tuple[int, int]] = self._excluded_ranges(source_text, search_options)
        bounded_start_position: int = min(max(start_position, 0), len(source_text))
        match: Match[str] | None = self._last_non_empty_match(
            pattern,
            source_text,
            0,
            bounded_start_position,
            excluded_ranges,
        )
        if match is None and bounded_start_position < len(source_text):
            match = self._last_non_empty_match(
                pattern,
                source_text,
                bounded_start_position,
                len(source_text),
                excluded_ranges,
            )

        if match is None:
            return None
        return SearchMatch(match.start(), match.end(), match.group(0))

    def replace_all(
        self,
        source_text: str,
        search_text: str,
        replace_text: str,
        options: SearchOptions | None = None,
    ) -> ReplaceResult:
        """指定されたソーステキスト内のすべての一致を置換します。"""
        if not search_text:
            return ReplaceResult(source_text, 0)

        search_options: SearchOptions = options or SearchOptions()
        pattern: Pattern[str] = self._compile_pattern(search_text, search_options)
        replacement_text: str = self._replacement_text_for_options(replace_text, search_options)
        excluded_ranges: list[tuple[int, int]] = self._excluded_ranges(source_text, search_options)
        if search_options.exclusion_text:
            # Validate the replacement even if every occurrence is excluded.
            if not search_options.unicode_normalize:
                pattern.sub(replacement_text, "")
            replacement_count = 0

            def replace_allowed_match(match: Match[str]) -> str:
                """除外されていない一致にだけ置換文字列を展開する。"""
                nonlocal replacement_count
                if self._is_excluded(match, excluded_ranges):
                    return match.group(0)
                replacement_count += 1
                return self._replacement_for_match(
                    match,
                    replacement_text,
                    search_options,
                )

            return ReplaceResult(pattern.sub(replace_allowed_match, source_text), replacement_count)
        if search_options.unicode_normalize:
            replaced_text, count = pattern.subn(
                lambda match: self._replacement_for_match(
                    match,
                    replacement_text,
                    search_options,
                ),
                source_text,
            )
            return ReplaceResult(replaced_text, count)
        replaced_text, count = pattern.subn(replacement_text, source_text)
        return ReplaceResult(replaced_text, count)

    def replace_match(
        self,
        source_text: str,
        match: SearchMatch,
        replace_text: str,
        search_text: str,
        options: SearchOptions | None = None,
    ) -> ReplaceResult:
        """指定されたソーステキスト内の、特定の一致を置換します。"""
        search_options: SearchOptions = options or SearchOptions()
        pattern: Pattern[str] = self._compile_pattern(search_text, search_options)
        replacement_text: str = self._replacement_text_for_options(replace_text, search_options)
        excluded_ranges: list[tuple[int, int]] = self._excluded_ranges(source_text, search_options)
        if self._range_is_excluded(match.start, match.end, excluded_ranges):
            return ReplaceResult(source_text, 0)
        target_text: str = source_text[match.start : match.end]
        if search_options.unicode_normalize:
            replaced_text, count = pattern.subn(
                lambda regex_match: self._replacement_for_match(
                    regex_match,
                    replacement_text,
                    search_options,
                ),
                target_text,
                count=1,
            )
        else:
            replaced_text, count = pattern.subn(replacement_text, target_text, count=1)
        if count == 0:
            return ReplaceResult(source_text, 0)

        return ReplaceResult(
            source_text[: match.start] + replaced_text + source_text[match.end :],
            count,
        )

    def preview_replacement(
        self,
        match_text: str,
        search_text: str,
        replace_text: str,
        options: SearchOptions | None = None,
    ) -> ReplaceResult:
        """指定された一致テキストを置換し、置換後のテキストと置換回数を返します。"""
        if not search_text:
            return ReplaceResult(match_text, 0)

        search_options: SearchOptions = options or SearchOptions()
        pattern: Pattern[str] = self._compile_pattern(search_text, search_options)
        replacement_text: str = self._replacement_text_for_options(replace_text, search_options)
        excluded_ranges: list[tuple[int, int]] = self._excluded_ranges(match_text, search_options)
        if self._range_is_excluded(0, len(match_text), excluded_ranges):
            return ReplaceResult(match_text, 0)
        if search_options.unicode_normalize:
            replaced_text, count = pattern.subn(
                lambda regex_match: self._replacement_for_match(
                    regex_match,
                    replacement_text,
                    search_options,
                ),
                match_text,
                count=1,
            )
        else:
            replaced_text, count = pattern.subn(replacement_text, match_text, count=1)
        return ReplaceResult(replaced_text, count)

    def _compile_pattern(
        self,
        search_text: str,
        options: SearchOptions,
    ) -> Pattern[str]:
        """検索テキストとオプションに基づいて、正規表現パターンをコンパイルします。"""
        pattern_text: str = search_text if options.regular_expression else re.escape(search_text)
        if options.whole_word:
            pattern_text = rf"\b(?:{pattern_text})\b"

        flags = re.RegexFlag(0)
        if options.regular_expression:
            flags |= re.MULTILINE
        if not options.case_sensitive:
            flags |= re.IGNORECASE
        return re.compile(pattern_text, flags)

    def _replacement_text_for_options(
        self,
        replace_text: str,
        options: SearchOptions,
    ) -> str:
        """置換テキストを、オプションに基づいて適切な形式に変換します。"""
        if options.unicode_normalize:
            return replace_text
        if not options.regular_expression:
            # リテラルな置換が `re.sub` の後方参照になってはならない。
            return replace_text.replace("\\", "\\\\")
        return convert_dollar_replacement_references(replace_text)

    @staticmethod
    def _replacement_for_match(
        match: Match[str],
        replacement_text: str,
        options: SearchOptions,
    ) -> str:
        """指定された一致に対して、置換テキストを適用します。"""
        if options.unicode_normalize:
            return normalize_matched_text(
                match.group(0),
                options.unicode_normalize_form,
                options.append_dot_to_circled_number,
            )
        return match.expand(replacement_text)

    def _first_non_empty_match(
        self,
        pattern: Pattern[str],
        source_text: str,
        start_position: int,
        excluded_ranges: list[tuple[int, int]],
    ) -> Match[str] | None:
        """指定されたソーステキストから、最初の空ではない一致を検索します。"""
        for match in pattern.finditer(source_text, start_position):
            if match.start() != match.end() and not self._is_excluded(match, excluded_ranges):
                return match
        return None

    def _last_non_empty_match(
        self,
        pattern: Pattern[str],
        source_text: str,
        start_position: int,
        end_position: int,
        excluded_ranges: list[tuple[int, int]],
    ) -> Match[str] | None:
        """指定されたソーステキストから、最後の空ではない一致を検索します。"""
        last_match: Match[str] | None = None
        for match in pattern.finditer(source_text, start_position, end_position):
            if match.start() != match.end() and not self._is_excluded(match, excluded_ranges):
                last_match = match
        return last_match

    def _excluded_ranges(
        self, source_text: str, options: SearchOptions,
    ) -> list[tuple[int, int]]:
        """元の検索範囲において、空ではない除外一致を保護する。"""

        if not options.exclusion_text:
            return []
        try:
            pattern: Pattern[str] = self._compile_pattern(
                options.exclusion_text, replace(options, whole_word=False),
            )
        except re.error as error:
            raise re.error(f"exclude: {error}") from error
        return [
            match.span() for match in pattern.finditer(source_text)
            if match.start() != match.end()
        ]

    def _is_excluded(
        self, match: Match[str], excluded_ranges: list[tuple[int, int]],
    ) -> bool:
        """指定された一致が、除外範囲に含まれるかどうかを判定します。"""
        return self._range_is_excluded(match.start(), match.end(), excluded_ranges)

    @staticmethod
    def _range_is_excluded(
        start: int, end: int, excluded_ranges: list[tuple[int, int]],
    ) -> bool:
        """指定された範囲が、除外範囲に含まれるかどうかを判定します。"""
        index: int = bisect_right(excluded_ranges, start, key=lambda span: span[1])
        return index < len(excluded_ranges) and excluded_ranges[index][0] < end


def convert_dollar_replacement_references(replace_text: str) -> str:
    """置換テキスト内の `$1`、`${name}` などの後方参照を、Python の `re` モジュールで使用できる形式に変換します。"""
    converted: list[str] = []
    index: int = 0
    while index < len(replace_text):
        character: str = replace_text[index]
        if character != "$":
            converted.append(character)
            index += 1
            continue

        next_index: int = index + 1
        if next_index >= len(replace_text):
            converted.append(character)
            index += 1
            continue

        next_character: str = replace_text[next_index]
        if next_character == "$":
            converted.append("$")
            index += 2
            continue

        if next_character.isdigit():
            group_end: int = next_index + 1
            while group_end < len(replace_text) and replace_text[group_end].isdigit():
                group_end += 1
            converted.append(rf"\g<{replace_text[next_index:group_end]}>")
            index = group_end
            continue

        if next_character == "{":
            closing_index: int = replace_text.find("}", next_index + 1)
            if closing_index != -1:
                group_name: str = replace_text[next_index + 1 : closing_index]
                if group_name.isidentifier() or group_name.isdigit():
                    converted.append(rf"\g<{group_name}>")
                    index = closing_index + 1
                    continue

        converted.append(character)
        index += 1
    return "".join(converted)
