from __future__ import annotations

import re

import pytest

from search.search_engine import SearchEngine, SearchMatch, SearchOptions


def test_find_all_returns_literal_matches() -> None:
    engine = SearchEngine()

    matches = engine.find_all("Alpha alpha beta", "alpha")

    assert [(match.start, match.end, match.text) for match in matches] == [
        (0, 5, "Alpha"),
        (6, 11, "alpha"),
    ]


def test_find_all_supports_regular_expressions() -> None:
    engine = SearchEngine()

    matches = engine.find_all(
        "item-01 item-20",
        r"item-\d+",
        SearchOptions(regular_expression=True),
    )

    assert [match.text for match in matches] == ["item-01", "item-20"]


def test_find_all_can_limit_match_count() -> None:
    engine = SearchEngine()

    matches = engine.find_all("one one one", "one", max_matches=2)

    assert [(match.start, match.end) for match in matches] == [(0, 3), (4, 7)]


def test_find_all_can_be_case_sensitive() -> None:
    engine = SearchEngine()

    matches = engine.find_all(
        "Alpha alpha",
        "alpha",
        SearchOptions(case_sensitive=True),
    )

    assert [match.text for match in matches] == ["alpha"]


def test_find_all_can_match_whole_words() -> None:
    engine = SearchEngine()

    matches = engine.find_all(
        "cat catalog cat",
        "cat",
        SearchOptions(whole_word=True),
    )

    assert [(match.start, match.end) for match in matches] == [(0, 3), (12, 15)]


def test_find_next_wraps_to_the_beginning() -> None:
    engine = SearchEngine()

    match = engine.find_next("abc abc", "abc", 5)

    assert match is not None
    assert (match.start, match.end, match.text) == (0, 3, "abc")


def test_find_previous_wraps_to_the_end() -> None:
    engine = SearchEngine()

    match = engine.find_previous("abc abc", "abc", 0)

    assert match is not None
    assert (match.start, match.end, match.text) == (4, 7, "abc")


def test_replace_all_supports_regex_groups() -> None:
    engine = SearchEngine()

    result = engine.replace_all(
        "item-01 item-20",
        r"(\w+)-(\d+)",
        r"\2:\1",
        SearchOptions(regular_expression=True),
    )

    assert result.text == "01:item 20:item"
    assert result.count == 2


def test_replace_all_supports_dollar_regex_groups() -> None:
    engine = SearchEngine()

    result = engine.replace_all(
        "item-01 item-20",
        r"(\w+)-(\d+)",
        "$2:$1",
        SearchOptions(regular_expression=True),
    )

    assert result.text == "01:item 20:item"
    assert result.count == 2


def test_replace_all_supports_dollar_named_regex_groups() -> None:
    engine = SearchEngine()

    result = engine.replace_all(
        "item-01",
        r"(?P<name>\w+)-(?P<number>\d+)",
        "${number}:${name}",
        SearchOptions(regular_expression=True),
    )

    assert result.text == "01:item"
    assert result.count == 1


def test_replace_all_uses_double_dollar_as_literal_dollar() -> None:
    engine = SearchEngine()

    result = engine.replace_all(
        "item-01",
        r"item-(\d+)",
        "$$1",
        SearchOptions(regular_expression=True),
    )

    assert result.text == "$1"
    assert result.count == 1


def test_replace_all_supports_literal_search_text() -> None:
    engine = SearchEngine()

    result = engine.replace_all(
        "a.b a-b",
        "a.b",
        "dot",
    )

    assert result.text == "dot a-b"
    assert result.count == 1


def test_replace_all_can_normalize_only_regex_matches() -> None:
    result = SearchEngine().replace_all(
        "① ＡＢＣ １２３ ② ⑩ ⑳",
        "[①-⑳]",
        r"ignored\2",
        SearchOptions(
            regular_expression=True,
            unicode_normalize=True,
            unicode_normalize_form="NFKC",
            append_dot_to_circled_number=True,
        ),
    )

    assert result.text == "1. ＡＢＣ １２３ 2. 10. 20."
    assert result.count == 4


def test_unicode_normalize_does_not_append_dot_to_fullwidth_digits() -> None:
    result = SearchEngine().replace_all(
        "１２３",
        r"\d+",
        "ignored",
        SearchOptions(
            regular_expression=True,
            unicode_normalize=True,
            append_dot_to_circled_number=True,
        ),
    )

    assert result.text == "123"
    assert result.count == 1


def test_normal_replacement_route_is_unchanged_when_unicode_mode_is_off() -> None:
    result = SearchEngine().replace_all(
        "① ②",
        "[①-⑳]",
        "item",
        SearchOptions(regular_expression=True),
    )

    assert result.text == "item item"
    assert result.count == 2


def test_replace_match_uses_unicode_normalization_route() -> None:
    result = SearchEngine().replace_match(
        "before ⑩ after",
        SearchMatch(7, 8, "⑩"),
        "ignored",
        "[①-⑳]",
        SearchOptions(
            regular_expression=True,
            unicode_normalize=True,
            append_dot_to_circled_number=True,
        ),
    )

    assert result.text == "before 10. after"
    assert result.count == 1


def test_regex_line_end_matches_each_line() -> None:
    engine = SearchEngine()

    result = engine.replace_all(
        "first  \nsecond\t\nthird",
        r"[ \t]+$",
        "",
        SearchOptions(regular_expression=True),
    )

    assert result.text == "first\nsecond\nthird"
    assert result.count == 2


def test_preview_replacement_returns_single_match_result() -> None:
    engine = SearchEngine()

    result = engine.preview_replacement(
        "2026-09-11",
        r"(\d{4})-(\d{2})-(\d{2})",
        r"\1/\2/\3",
        SearchOptions(regular_expression=True),
    )

    assert result.text == "2026/09/11"
    assert result.count == 1


def test_preview_replacement_supports_dollar_regex_groups() -> None:
    engine = SearchEngine()

    result = engine.preview_replacement(
        "2026-09-11",
        r"(\d{4})-(\d{2})-(\d{2})",
        "$1/$2/$3",
        SearchOptions(regular_expression=True),
    )

    assert result.text == "2026/09/11"
    assert result.count == 1


def test_invalid_replacement_reference_is_reported() -> None:
    engine = SearchEngine()

    with pytest.raises(re.error):
        engine.replace_all(
            "item-01",
            r"item-(\d+)",
            r"\2",
            SearchOptions(regular_expression=True),
        )


def test_invalid_dollar_replacement_reference_is_reported() -> None:
    engine = SearchEngine()

    with pytest.raises(re.error):
        engine.replace_all(
            "item-01",
            r"item-(\d+)",
            "$2",
            SearchOptions(regular_expression=True),
        )


def test_invalid_regular_expression_is_reported() -> None:
    engine = SearchEngine()

    with pytest.raises(re.error):
        engine.find_all(
            "source text",
            r"[",
            SearchOptions(regular_expression=True),
        )


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_exclusion_protects_tag_newlines(newline: str) -> None:
    engine = SearchEngine()
    source = f"plain{newline}<br><br>{newline}<p>{newline}comma、{newline}last"
    options = SearchOptions(regular_expression=True, exclusion_text=r"<br><br>\r?\n|>\r?\n")

    matches = engine.find_all(source, r"\r?\n", options)
    result = engine.replace_all(source, r"\r?\n", " / ", options)

    assert [match.start for match in matches] == [source.index(newline), source.rindex(newline)]
    assert result.text == f"plain / <br><br>{newline}<p>{newline}comma、 / last"
    assert result.count == 2


@pytest.mark.parametrize("start", [0, 4, 7, 11])
def test_navigation_skips_exclusions_and_wraps(start: int) -> None:
    engine = SearchEngine()
    source = "x [x] x [x]"
    options = SearchOptions(exclusion_text="[x]")
    next_match = engine.find_next(source, "x", start, options)
    previous_match = engine.find_previous(source, "x", start, options)

    assert next_match is not None and previous_match is not None
    assert next_match.start == (6 if 0 < start <= 6 else 0)
    assert previous_match.start == (0 if 0 < start <= 6 else 6)


def test_exclusion_filters_before_match_limit() -> None:
    matches = SearchEngine().find_all(
        "[x] [x] x x", "x", SearchOptions(exclusion_text="[x]"), max_matches=1,
    )
    assert [match.start for match in matches] == [8]


@pytest.mark.parametrize("exclusion", ["b", "ab", "bc", "abc"])
def test_any_overlap_excludes_the_entire_match(exclusion: str) -> None:
    engine = SearchEngine()
    options = SearchOptions(exclusion_text=exclusion)
    assert engine.find_all("abc", "abc", options) == []
    result = engine.replace_all("abc", "abc", "changed", options)
    assert result.text == "abc" and result.count == 0


def test_exclusion_does_not_protect_adjacent_matches() -> None:
    result = SearchEngine().replace_all("abc", ".", "x", SearchOptions(
        regular_expression=True, exclusion_text="b",
    ))
    assert result.text == "xbx" and result.count == 2


@pytest.mark.parametrize("case_sensitive, count", [(False, 0), (True, 1)])
def test_exclusion_uses_case_option_and_literal_metacharacters(
    case_sensitive: bool, count: int,
) -> None:
    matches = SearchEngine().find_all("[Alpha]", "Alpha", SearchOptions(
        case_sensitive=case_sensitive, exclusion_text="[alpha]",
    ))
    assert len(matches) == count


def test_whole_word_search_does_not_add_boundaries_to_exclusion() -> None:
    assert SearchEngine().find_all("[cat] cat", "cat", SearchOptions(
        whole_word=True, exclusion_text="[cat]",
    )) == [SearchMatch(6, 9, "cat")]


def test_replace_current_checks_exclusion_in_original_source() -> None:
    engine = SearchEngine()
    source = "<p>\nplain\n"
    options = SearchOptions(regular_expression=True, exclusion_text=r">\n")
    result = engine.replace_match(source, SearchMatch(3, 4, "\n"), "X", r"\n", options)
    assert result.text == source and result.count == 0
    result = engine.replace_match(source, SearchMatch(9, 10, "\n"), "X", r"\n", options)
    assert result.text == "<p>\nplainX" and result.count == 1


def test_exclusions_do_not_change_capture_numbers_or_replacement_escapes() -> None:
    result = SearchEngine().replace_all("item-01 item-20", r"item-(\d+)", r"$1\n", SearchOptions(
        regular_expression=True, exclusion_text=r"item-01",
    ))
    assert result.text == "item-01 20\n" and result.count == 1


def test_exclusions_are_evaluated_before_any_replacement() -> None:
    result = SearchEngine().replace_all("a a", "a", "[a]", SearchOptions(exclusion_text="[a]"))
    assert result.text == "[a] [a]" and result.count == 2


def test_zero_width_exclusions_protect_no_characters() -> None:
    assert len(SearchEngine().find_all("abc", "abc", SearchOptions(
        regular_expression=True, exclusion_text=r"^|$",
    ))) == 1


@pytest.mark.parametrize("method", ["find_all", "find_next", "find_previous", "replace_all", "preview_replacement"])
def test_invalid_exclusion_is_reported(method: str) -> None:
    engine = SearchEngine()
    options = SearchOptions(regular_expression=True, exclusion_text="[")
    with pytest.raises(re.error, match="exclude"):
        if method in {"find_next", "find_previous"}:
            getattr(engine, method)("abc", "a", 0, options)
        elif method in {"replace_all", "preview_replacement"}:
            getattr(engine, method)("abc", "a", "x", options)
        else:
            engine.find_all("abc", "a", options)


def test_preview_does_not_replace_excluded_match() -> None:
    result = SearchEngine().preview_replacement("cat", "cat", "dog", SearchOptions(exclusion_text="cat"))
    assert result.text == "cat" and result.count == 0


def test_invalid_replacement_is_reported_even_when_all_matches_are_excluded() -> None:
    with pytest.raises(re.error):
        SearchEngine().replace_all("cat", "cat", r"\2", SearchOptions(
            regular_expression=True, exclusion_text="cat",
        ))
