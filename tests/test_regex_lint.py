"""正規表現の検査を検証する。"""

from __future__ import annotations

from search.regex_lint import RegexLint


def test_lint_reports_invalid_regex() -> None:
    """文法チェックが不正な正規表現を報告することを確認する。"""
    messages = RegexLint().lint("[")

    assert messages
    assert messages[0].severity == "error"
    assert messages[0].message_key == "regex_lint.invalid_regex"


def test_lint_warns_about_empty_matches() -> None:
    """文法チェックが空の一致箇所を警告することを確認する。"""
    messages = RegexLint().lint(r"\d*")

    assert any(message.message_key == "regex_lint.empty_match" for message in messages)


def test_lint_reports_invalid_replacement_reference() -> None:
    """文法チェックが不正な置換の参照資料を報告することを確認する。"""
    messages = RegexLint().lint(
        r"item-(\d+)",
        r"\2",
        check_replacement=True,
    )

    assert any(message.severity == "error" for message in messages)


def test_lint_reports_invalid_dollar_replacement_reference() -> None:
    """文法チェックが不正なドル記号の置換の参照資料を報告することを確認する。"""
    messages = RegexLint().lint(
        r"item-(\d+)",
        "$2",
        check_replacement=True,
    )

    assert any(message.severity == "error" for message in messages)


def test_lint_warns_about_unescaped_dot() -> None:
    """エスケープされていないピリオドを文法チェックが警告することを確認する。"""
    messages = RegexLint().lint("example.com")

    assert any(message.message_key == "regex_lint.unescaped_dot" for message in messages)


def test_lint_warns_about_backslash_n() -> None:
    """文法チェックがバックスラッシュのnを警告することを確認する。"""
    messages = RegexLint().lint(r"\n{3,}")

    assert any(message.message_key == "regex_lint.backslash_n" for message in messages)


def test_lint_warns_about_yen_sign_used_as_escape() -> None:
    """円記号をエスケープに使った場合に警告が出ることを確認する。"""
    messages = RegexLint().lint("first¥nsecond")

    assert any(
        message.message_key == "regex_lint.yen_sign_escape"
        for message in messages
    )
