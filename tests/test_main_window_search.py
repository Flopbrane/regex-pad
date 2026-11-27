"""メインウインドウの検索を検証する。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from main import MainWindow
from search.html_typo_lint import HtmlTypoLintMessage
from search.search_engine import SearchMatch, SearchOptions


def _process_delayed_ui_events(delay_ms: int = 75) -> None:
    """テスト対象の遅延処理が実行されるまでQtイベントを処理する。"""
    loop = QEventLoop()
    QTimer.singleShot(delay_ms, loop.quit)
    loop.exec()
    QApplication.processEvents()


@pytest.mark.parametrize("severity,confirmations", [("info", 0), ("warning", 1), ("error", 1)])
def test_save_lint_confirmation_respects_severity(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    severity: str, confirmations: int,
) -> None:
    """保存時の確認が文法チェックの重大度に応じて出ることを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json", unsaved_backup_path=tmp_path / "backup.json")
    window.html_typo_lint_enabled = True
    original = "KEEP THIS TEXT"
    window.editor.setPlainText(original)
    message = HtmlTypoLintMessage(severity, "html_typo_lint.missing_html_closing_tag", 1, {"tag": "p"})
    monkeypatch.setattr(window, "_lint_document", lambda text: [message])
    requests = []

    def confirm(*args, **kwargs):
        """確認ダイアログへの利用者の応答をテスト用に代用する。"""
        requests.append(args)
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", confirm)
    assert window._confirm_save_after_grammar_check(original) is (severity == "info")
    assert len(requests) == confirmations
    assert window.editor.toPlainText() == original
    window.editor.document().setModified(False)
    window.close()


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_find_next_selects_regex_match(app: QApplication) -> None:
    """次の検索が正規表現の一致を選択することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("abc item-123 xyz")

    window.find_next(
        r"item-\d+",
        SearchOptions(regular_expression=True),
    )

    assert window.editor.textCursor().selectedText() == "item-123"


def test_replace_all_uses_regex_groups(app: QApplication) -> None:
    """全置換が正規表現のグループを使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("item-01 item-20")

    window.replace_all(
        r"(\w+)-(\d+)",
        r"\2:\1",
        SearchOptions(regular_expression=True),
    )

    assert window.editor.toPlainText() == "01:item 20:item"


def test_replace_all_button_uses_unicode_normalization_route(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """全置換のボタンがUnicodeの正規化の経路を使うことを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("① ＡＢＣ １２３ ② ⑩ ⑳")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.regular_expression_check_box.setChecked(True)
    dialog.find_text_edit.setText("[①-⑳]")
    dialog.replace_text_edit.setText("must not be used")
    dialog.unicode_normalize_check_box.setChecked(True)
    dialog.append_dot_to_circled_number_check_box.setChecked(True)

    dialog.replace_all_button.click()
    QApplication.processEvents()

    assert window.editor.toPlainText() == "1. ＡＢＣ １２３ 2. 10. 20."
    assert dialog.preview_table.rowCount() == 0
    window.editor.undo()
    assert window.editor.toPlainText() == "① ＡＢＣ １２３ ② ⑩ ⑳"


def test_replace_current_uses_unicode_normalization_route(app: QApplication) -> None:
    """1件置換がUnicodeの正規化の経路を使うことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("⑩ follows ①")
    options = SearchOptions(
        regular_expression=True,
        unicode_normalize=True,
        append_dot_to_circled_number=True,
    )

    window.find_next("[①-⑳]", options)
    window.replace_current("[①-⑳]", "ignored", options)

    assert window.editor.toPlainText() == "10. follows ①"
    assert window.editor.textCursor().position() == len("10.")


def test_replace_all_returns_focus_to_find_text(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """全置換が検索欄へのフォーカスを返すことを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("target target")
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None
    window.find_replace_dialog.find_text_edit.setText("target")
    window.find_replace_dialog.replace_text_edit.setText("done")
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )

    window.find_replace_dialog.replace_all_button.click()
    _process_delayed_ui_events()

    assert window.editor.toPlainText() == "done done"
    assert window.find_replace_dialog.find_text_edit.hasFocus()
    assert window.find_replace_dialog.find_text_edit.text() == "target"
    assert window.find_replace_dialog.replace_text_edit.text() == "done"
    assert not window.find_replace_dialog.find_text_edit.hasSelectedText()
    assert not window.find_replace_dialog.replace_text_edit.hasSelectedText()


def test_replace_current_returns_focus_to_find_text(
    app: QApplication,
    tmp_path,
) -> None:
    """1件置換の後、検索文字列の入力欄にフォーカスが戻ることを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("target target")
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None
    window.find_replace_dialog.find_text_edit.setText("target")
    window.find_replace_dialog.replace_text_edit.setText("done")

    window.find_replace_dialog.find_next_button.click()
    window.find_replace_dialog.replace_button.click()
    _process_delayed_ui_events()

    assert window.editor.toPlainText() == "done target"
    assert window.find_replace_dialog.find_text_edit.hasFocus()
    assert window.find_replace_dialog.find_text_edit.text() == "target"
    assert window.find_replace_dialog.replace_text_edit.text() == "done"
    assert not window.find_replace_dialog.find_text_edit.hasSelectedText()
    assert not window.find_replace_dialog.replace_text_edit.hasSelectedText()


def test_replace_marked_returns_focus_to_find_text(
    app: QApplication,
    tmp_path,
) -> None:
    """マーカー付きの一致を置換した後、検索欄にフォーカスが戻ることを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("target keep target")
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None
    window.find_replace_dialog.find_text_edit.setText("target")
    window.find_replace_dialog.replace_text_edit.setText("done")
    window.update_search_highlights("target", SearchOptions())

    window.find_replace_dialog.replace_marked_button.click()
    _process_delayed_ui_events()

    assert window.editor.toPlainText() == "done keep done"
    assert window.find_replace_dialog.find_text_edit.hasFocus()
    assert window.find_replace_dialog.find_text_edit.text() == "target"
    assert window.find_replace_dialog.replace_text_edit.text() == "done"
    assert not window.find_replace_dialog.find_text_edit.hasSelectedText()
    assert not window.find_replace_dialog.replace_text_edit.hasSelectedText()


def test_replace_all_button_previews_and_replaces(
    app: QApplication,
    tmp_path,
) -> None:
    """全置換ボタンで変更のプレビューと適用ができることを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("target target")
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None
    window.find_replace_dialog.find_text_edit.setText("target")
    window.find_replace_dialog.replace_text_edit.setText("done")

    window.find_replace_dialog.replace_all_button.click()
    QApplication.processEvents()

    assert window.editor.toPlainText() == "done done"
    assert window.find_replace_dialog.preview_table.rowCount() == 0


def test_replace_all_button_replaces_wordpress_paragraph_gap_regex(
    app: QApplication,
    tmp_path,
) -> None:
    """全置換のボタンがWordPressの段落の隙間の正規表現を置き換えることを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText(
        "first"
        "\n<!-- /wp:paragraph ->"
        "\n\n<!-- wp:paragraph -->"
        "second"
        "\n<!-- /wp:paragraph ->"
        "\n\n<!-- wp:paragraph -->"
        "third"
    )
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None
    window.find_replace_dialog.regular_expression_check_box.setChecked(True)
    window.find_replace_dialog.find_text_edit.setText(
        r"\n<!-- /wp:paragraph ->\n\n<!-- wp:paragraph -->"
    )
    window.find_replace_dialog.replace_text_edit.setText(r"\n")

    window.find_replace_dialog.replace_all_button.click()
    QApplication.processEvents()

    assert window.editor.toPlainText() == "first\nsecond\nthird"
    assert window.find_replace_dialog.preview_table.rowCount() == 0


def test_low_load_mode_skips_auto_search_highlights(
    app: QApplication,
    tmp_path,
) -> None:
    """低負荷モードが自動の検索の強調表示を省くことを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.reduced_error_check_enabled = True
    window.editor.setPlainText("target target")
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None

    window.find_replace_dialog.find_text_edit.setText("target")

    assert window.editor.search_matches == []


def test_replace_current_keeps_cursor_after_replaced_text(app: QApplication) -> None:
    """置換された文字列後、1件置換がカーソルを保持することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("target 1\nkeep\ntarget 2\nkeep\ntarget 3")
    options = SearchOptions()

    window.find_next("target", options)
    window.find_next("target", options)
    window.replace_current("target", "done", options)

    assert window.editor.toPlainText() == "target 1\nkeep\ndone 2\nkeep\ntarget 3"
    assert window.editor.textCursor().position() == len("target 1\nkeep\ndone")


def test_find_next_after_replace_current_continues_to_following_match(
    app: QApplication,
) -> None:
    """1件置換した後の次検索が、後続の一致箇所へ進むことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("target 1\nkeep\ntarget 2\nkeep\ntarget 3")
    options = SearchOptions()

    window.find_next("target", options)
    window.find_next("target", options)
    window.replace_current("target", "done", options)
    window.find_next("target", options)

    assert window.editor.textCursor().selectedText() == "target"
    assert window.editor.textCursor().selectionStart() == len(
        "target 1\nkeep\ndone 2\nkeep\n"
    )


def test_replace_current_with_newline_keeps_cursor_at_new_line_start(
    app: QApplication,
) -> None:
    """1件置換（改行あり）がカーソルでの新規の行の先頭を保持することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("alpha, beta, gamma")

    window.find_next(",", SearchOptions())
    window.replace_current(",", "\n", SearchOptions())

    assert window.editor.toPlainText() == "alpha\n beta, gamma"
    assert window.editor.textCursor().blockNumber() == 1
    assert window.editor.textCursor().positionInBlock() == 0


def test_invalid_regex_does_not_modify_document(app: QApplication) -> None:
    """不正な正規表現が文書を変更しないことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("keep this text")

    window.replace_all(
        r"[",
        "changed",
        SearchOptions(regular_expression=True),
    )

    assert window.editor.toPlainText() == "keep this text"


def test_replace_all_can_target_selected_text_only(app: QApplication) -> None:
    """全置換が選択文字列のだけを対象にできることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("first 123\nsecond 456\nthird 789")
    cursor = window.editor.textCursor()
    cursor.setPosition(10)
    cursor.setPosition(20, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.search_scope = (cursor.selectionStart(), cursor.selectionEnd())

    window.replace_all(
        r"\d+",
        "NUM",
        SearchOptions(regular_expression=True, selected_only=True),
    )

    assert window.editor.toPlainText() == "first 123\nsecond NUM\nthird 789"


def test_dialog_replace_all_honours_selection_and_exclusion(app: QApplication) -> None:
    """ダイアログの全置換で選択範囲と除外条件を適用することを確認する。"""
    _ = app
    window = MainWindow()
    source_text = "outside target\n[target] target\noutside target"
    window.editor.setPlainText(source_text)
    scope_start = len("outside target\n")
    scope_end = len("outside target\n[target] target")
    cursor = window.editor.textCursor()
    cursor.setPosition(scope_start)
    cursor.setPosition(scope_end, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("target")
    dialog.replace_text_edit.setText("done")
    dialog.exclusion_text_edit.setText("[target]")
    dialog.selected_only_check_box.setChecked(True)

    dialog.replace_all_button.click()

    assert window.editor.toPlainText() == (
        "outside target\n[target] done\noutside target"
    )


def test_dialog_can_reset_scope_to_current_editor_selection(
    app: QApplication,
) -> None:
    """ダイアログがリセットの対象範囲のへの現在のエディターの選択範囲が可能であることを確認する。"""
    _ = app
    window = MainWindow()
    source_text = "first target\nsecond target\nthird target"
    window.editor.setPlainText(source_text)

    first_start = 0
    first_end = len("first target")
    cursor = window.editor.textCursor()
    cursor.setPosition(first_start)
    cursor.setPosition(first_end, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.selected_only_check_box.setChecked(True)
    assert window.search_scope == (first_start, first_end)

    second_start = len("first target\n")
    second_end = second_start + len("second target")
    cursor = window.editor.textCursor()
    cursor.setPosition(second_start)
    cursor.setPosition(second_end, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)

    dialog.reset_selection_scope_button.click()

    assert window.search_scope == (second_start, second_end)


def test_regex_normalise_rewrites_document_text(app: QApplication) -> None:
    """正規表現を使ったUnicode正規化置換で本文を書き換えられることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("ＷｏｒｄＰｒｅｓｓとＨＴＭＬ")
    window.show_find_replace_dialog()

    window.apply_regex_normalise_operation("fullwidth_alphabet_to_halfwidth")

    assert window.editor.toPlainText() == "WordPressとHTML"


def test_regex_normalise_can_target_selected_text_only(app: QApplication) -> None:
    """正規表現の正規化が選択文字列のだけを対象にできることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("外側：１\n内側：２")
    cursor = window.editor.textCursor()
    cursor.setPosition(len("外側：１\n"))
    cursor.setPosition(len("外側：１\n内側：２"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.search_scope = (cursor.selectionStart(), cursor.selectionEnd())
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None
    window.find_replace_dialog.selected_only_check_box.setChecked(True)

    window.apply_regex_normalise_operation("fullwidth_digits_symbols_to_halfwidth")

    assert window.editor.toPlainText() == "外側：１\n内側:2"


def test_find_next_can_target_selected_text_only(app: QApplication) -> None:
    """次の検索が選択文字列のだけを対象にできることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("target\ninside target\noutside")
    cursor = window.editor.textCursor()
    cursor.setPosition(7)
    cursor.setPosition(20, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.search_scope = (cursor.selectionStart(), cursor.selectionEnd())

    window.find_next(
        "target",
        SearchOptions(selected_only=True),
    )

    assert window.editor.textCursor().selectedText() == "target"
    assert window.editor.textCursor().selectionStart() == 14


def test_find_previous_selects_previous_match(app: QApplication) -> None:
    """前の検索が前の一致を選択することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("alpha beta alpha")
    cursor = window.editor.textCursor()
    cursor.setPosition(len(window.editor.toPlainText()))
    window.editor.setTextCursor(cursor)

    window.find_previous("alpha", SearchOptions())

    assert window.editor.textCursor().selectedText() == "alpha"
    assert window.editor.textCursor().selectionStart() == 11


def test_paragraph_insert_linter_shows_dictionary_backed_message(
    app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """段落挿入の文法チェッカーが辞書の裏付けられたのメッセージを表示することを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("plain text")
    captured: dict[str, str] = {}

    def capture_warning(
        _parent: object,
        title: str,
        message: str,
    ) -> QMessageBox.StandardButton:
        """画面へ表示される警告の内容を記録する。"""
        captured["title"] = title
        captured["message"] = message
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", capture_warning)

    window.insert_paragraph_split_spacer()

    assert captured["title"] == window.translator.text("paragraph_split.error_title")
    assert captured["message"] == window.translator.text("paragraph_split.not_available")
    assert window.editor.toPlainText() == "plain text"


def test_grammar_check_action_is_available_from_search_menu(
    app: QApplication,
) -> None:
    """文法チェックの操作が検索のメニューを利用できることを確認する。"""
    _ = app
    window = MainWindow()

    assert window.grammar_check_action.text() == "文法チェック(&G)"
    assert window.grammar_check_action.shortcut().toString() == "F7"
    assert window.grammar_check_action in [
        action for action in window.search_menu.actions()
    ]


def test_grammar_check_reports_html_and_wordpress_typos(
    app: QApplication,
) -> None:
    """文法チェックがHTMLとWordPressの表記ミスを報告することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText(
        "<p>本文</p>\n"
        '<p clas="lead"><spna>誤字</spna></p>\n'
        "<!-- wp:paragaph -->\n"
    )

    window.run_grammar_check()

    assert window.grammar_check_dialog is not None
    assert window.grammar_check_dialog.isModal() is False
    assert window.grammar_check_dialog.size().width() == 930
    assert window.grammar_check_dialog.windowTitle().startswith("文法チェック - ")
    assert "文法チェックで" in window.grammar_check_dialog.summary_label.text()
    result_text = "\n".join(
        window.grammar_check_dialog.message_list.item(row).text()
        for row in range(window.grammar_check_dialog.message_list.count())
    )
    assert "2行目" in result_text
    assert "spna" in result_text
    assert "span" in result_text
    assert "clas" in result_text
    assert "class" in result_text
    assert "3行目" in result_text
    assert "paragaph" in result_text
    assert "paragraph" in result_text
    assert "Typoです" in result_text
    assert "wp:paragraph" in result_text
    assert window.translator.text("grammar_check.severity.warning") in result_text
    assert "警告" in window.grammar_check_dialog.summary_label.text()
    assert window.grammar_check_dialog.copy_button.isEnabled() is True
    window.grammar_check_dialog.copy_results_to_clipboard()
    assert QApplication.clipboard().text() == result_text
    assert "修正してください" in result_text
    # Missing block boundaries are now Error and take priority over the earlier typos.
    assert window.translator.text("grammar_check.severity.error") in result_text
    assert window.editor.textCursor().blockNumber() == 2
    line_three_item = next(
        window.grammar_check_dialog.message_list.item(row)
        for row in range(window.grammar_check_dialog.message_list.count())
        if "3行目" in window.grammar_check_dialog.message_list.item(row).text()
    )
    window.grammar_check_dialog.message_list.itemClicked.emit(line_three_item)
    assert window.editor.textCursor().blockNumber() == 2


def test_grammar_check_highlights_issue_lines(
    app: QApplication,
) -> None:
    """文法チェックが指摘の行を強調表示することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText(
        "<p>本文</p>\n"
        '<p clas="lead"><spna>誤字</spna></p>\n'
        "<!-- wp:paragaph -->\n"
    )

    window.run_grammar_check()

    issue_selections = [
        selection
        for selection in window.editor.extraSelections()
        if selection.format.background().color().name() == "#ffe3e3"
    ]
    assert len(issue_selections) == 2
    assert window.editor.grammar_issue_lines == [2, 3]


@pytest.mark.parametrize("sample_name, expected_count", [("broken.wp_html", 11), ("fixed.wp_html", 0)])
def test_grammar_check_detects_qualification_article_malformed_openers(
    app: QApplication, tmp_path: Path, sample_name: str, expected_count: int,
) -> None:
    """文法チェックが修飾の原稿の壊れたの開始記号を検出することを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    case_folder = Path(__file__).parent / "fixtures" / "linter_cases" / "qualification_article_20261023"
    source = (case_folder / sample_name).read_text(encoding="utf-8-sig")
    window.editor.setPlainText(source)
    window.run_grammar_check()

    assert window.grammar_check_dialog is not None
    family_texts = [
        window.translator.text(f"html_typo_lint.{key}", tag="div", attribute="style")
        for key in (
            "html_attribute_outside_opening_tag", "malformed_html_attribute_continuation",
            "unexpected_html_tag_close_delimiter",
        )
    ]
    findings = [
        window.grammar_check_dialog.message_list.item(row).text()
        for row in range(window.grammar_check_dialog.message_list.count())
    ]
    assert sum(any(text in finding for text in family_texts) for finding in findings) == expected_count
    assert window.editor.toPlainText() == source
    if expected_count:
        assert {22, 82, 109, 127, 151, 211, 288, 361, 430, 496, 523}.issubset(
            window.editor.grammar_issue_lines,
        )


def test_grammar_check_clears_issue_highlights_when_no_issues(
    app: QApplication,
) -> None:
    """文法チェックで指摘がなくなったとき、既存の強調表示を消すことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText('<p clas="lead">誤字</p>')
    window.run_grammar_check()
    assert window.editor.grammar_issue_lines == [1]

    window.editor.setPlainText(
        "<!-- wp:paragraph -->\n"
        '<p class="lead">本文</p>\n'
        "<!-- /wp:paragraph -->\n"
    )
    window.run_grammar_check()

    assert window.editor.grammar_issue_lines == []
    assert not [
        selection
        for selection in window.editor.extraSelections()
        if selection.format.background().color().name() == "#ffe3e3"
    ]


def test_grammar_check_clears_issue_highlights_on_edit(
    app: QApplication,
) -> None:
    """文法チェックが指摘の強調表示での編集を消すことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText('<p clas="lead">誤字</p>')
    window.run_grammar_check()
    assert window.editor.grammar_issue_lines == [1]

    window.editor.insertPlainText("修正中")

    assert window.editor.grammar_issue_lines == []


def test_grammar_check_clears_issue_highlights_when_dialog_hides(
    app: QApplication,
) -> None:
    """ダイアログが非表示にするの場合、文法チェックが指摘の強調表示を消すことを確認する。"""
    window = MainWindow()
    window.editor.setPlainText('<p clas="lead">誤字</p>')
    window.run_grammar_check()
    assert window.grammar_check_dialog is not None
    assert window.editor.grammar_issue_lines == [1]

    window.grammar_check_dialog.hide()
    app.processEvents()

    assert window.editor.grammar_issue_lines == []


def test_grammar_check_reports_no_issues(
    app: QApplication,
) -> None:
    """文法チェックが指摘なしを報告することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText(
        "<!-- wp:paragraph -->\n"
        '<p class="lead">本文</p>\n'
        "<!-- /wp:paragraph -->\n"
    )

    window.run_grammar_check()

    assert window.grammar_check_dialog is not None
    assert window.grammar_check_dialog.summary_label.text() == (
        "簡易チェック完了：大きな構造エラーは見つかりませんでした。"
    )
    assert window.grammar_check_dialog.message_list.count() == 0
    assert window.grammar_check_dialog.copy_button.isEnabled() is False


def test_grammar_check_results_are_kept_per_tab(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """文法チェックの結果が保持されたごとのタブであることを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    first_editor = window.editor
    window.tab_file_paths[first_editor] = tmp_path / "first.wp_html"
    first_editor.setPlainText('<p clas="lead">本文</p>')
    first_editor.document().setModified(False)

    window.run_grammar_check()

    assert window.grammar_check_dialog is not None
    first_result_path = window.tab_grammar_result_paths[first_editor]
    assert first_result_path.exists()
    assert "first.wp_html" in window.grammar_check_dialog.windowTitle()
    assert window.grammar_check_dialog.message_list.count() == 1

    second_editor = window.create_editor_tab(
        text=(
            "<!-- wp:paragraph -->\n"
            '<p class="lead">本文</p>\n'
            "<!-- /wp:paragraph -->\n"
        ),
        save_file_path=tmp_path / "second.wp_html",
    )
    second_editor.document().setModified(False)

    window.run_grammar_check()

    second_result_path = window.tab_grammar_result_paths[second_editor]
    assert second_result_path.exists()
    assert second_result_path != first_result_path
    assert "second.wp_html" in window.grammar_check_dialog.windowTitle()
    assert window.grammar_check_dialog.message_list.count() == 0

    window.tab_widget.setCurrentIndex(0)
    app.processEvents()

    assert "first.wp_html" in window.grammar_check_dialog.windowTitle()
    assert window.grammar_check_dialog.message_list.count() == 1
    assert first_editor.grammar_issue_lines == [1]
    assert second_editor.grammar_issue_lines == []

    window.tab_widget.setCurrentIndex(1)
    app.processEvents()

    assert "second.wp_html" in window.grammar_check_dialog.windowTitle()
    assert window.grammar_check_dialog.message_list.count() == 0

    window.remove_tab(1)
    window.remove_tab(0)
    assert not first_result_path.exists()
    assert not second_result_path.exists()


def test_grammar_check_result_file_is_deleted_when_tab_closes(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """タブが閉じるの場合、文法チェックの結果のファイルが削除されたになることを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText('<p clas="lead">本文</p>')
    window.editor.document().setModified(False)
    editor = window.editor

    window.run_grammar_check()

    result_path = window.tab_grammar_result_paths[editor]
    assert result_path.exists()

    assert window.close_tab(0)

    assert not result_path.exists()


def test_grammar_check_temp_folder_is_deleted_when_window_closes(
    app: QApplication,
    tmp_path: Path,
) -> None:
    """ウインドウが閉じるの場合、文法チェックの一時的なフォルダーが削除されたになることを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText('<p clas="lead">本文</p>')
    window.editor.document().setModified(False)

    window.run_grammar_check()

    result_folder = window.grammar_lint_result_store.result_folder
    assert result_folder.exists()

    assert window.close()
    app.processEvents()

    assert not result_folder.exists()


def test_preview_matches_shows_line_context_and_replacement(app: QApplication) -> None:
    """プレビューがを表示するの行の周辺の文脈と置換に一致することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("first\nsecond  \nthird")
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None

    window.preview_matches(
        r"[ \t]+$",
        "",
        SearchOptions(regular_expression=True),
    )

    assert window.find_replace_dialog.preview_table.rowCount() == 1
    line_item = window.find_replace_dialog.preview_table.item(0, 0)
    before_item = window.find_replace_dialog.preview_table.item(0, 1)
    after_item = window.find_replace_dialog.preview_table.item(0, 2)
    assert line_item is not None
    assert before_item is not None
    assert after_item is not None
    assert line_item.text() == "2"
    assert before_item.text() == "second  "
    assert after_item.text() == "second"


def test_preview_row_click_jumps_to_original_tab_and_line(app: QApplication) -> None:
    """プレビューの行のクリックのへ移動するのへの元のタブと行を確認する。"""
    _ = app
    window = MainWindow()
    source_editor = window.editor
    source_editor.setPlainText("first\nsecond  \nthird\nfourth  ")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    window.preview_matches(r"[ \t]+$", "", SearchOptions(regular_expression=True))
    assert dialog.preview_table.rowCount() == 2

    window.create_editor_tab(text="another document")
    assert window.editor is not source_editor
    after_item = dialog.preview_table.item(1, 2)
    assert after_item is not None
    dialog.preview_table.scrollToItem(after_item)
    QApplication.processEvents()
    QTest.mouseClick(
        dialog.preview_table.viewport(),
        Qt.MouseButton.LeftButton,
        pos=dialog.preview_table.visualItemRect(after_item).center(),
    )

    assert window.editor is source_editor
    assert source_editor.textCursor().blockNumber() == 3
    assert source_editor.textCursor().positionInBlock() == 0
    assert source_editor.toPlainText() == "first\nsecond  \nthird\nfourth  "


def test_preview_rows_clear_after_source_edit(app: QApplication) -> None:
    """プレビューの行の消去後の原文の編集を確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("first\nsecond  ")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    window.preview_matches(r"[ \t]+$", "", SearchOptions(regular_expression=True))
    assert dialog.preview_table.rowCount() == 1

    window.editor.insertPlainText("changed")

    assert dialog.preview_table.rowCount() == 0


def test_clearing_search_text_clears_preview_even_in_reduced_mode(
    app: QApplication,
) -> None:
    """軽量モードでも検索文字列を消すとプレビューが消えることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("target")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("target")
    dialog.set_reduced_error_check_enabled(True)
    window.preview_matches("target", "done", SearchOptions())
    assert dialog.preview_table.rowCount() == 1
    assert window._preview_source is not None

    dialog.find_text_edit.clear()

    assert dialog.preview_table.rowCount() == 0
    assert dialog.preview_summary_label.text() == ""
    assert window._preview_source is None


def test_reopening_search_dialog_does_not_duplicate_find_handler(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """開き直しの検索のダイアログが検索の処理を重複させないことを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("target target")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("target")
    for _ in range(50):
        dialog.close()
        window.show_find_replace_dialog()
        assert window.find_replace_dialog is dialog

    find_calls = 0
    original_find_next = window.search_engine.find_next

    def count_find(*args, **kwargs):
        """検索の呼び出し回数を記録し、本来の検索処理を実行する。"""
        nonlocal find_calls
        find_calls += 1
        return original_find_next(*args, **kwargs)

    monkeypatch.setattr(window.search_engine, "find_next", count_find)
    dialog.find_button.click()
    assert find_calls == 1


def test_closing_preview_source_tab_clears_rows_and_target(
    app: QApplication,
) -> None:
    """終了のプレビューの元のタブが行と対象を消すことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("first\nsecond  ")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    window.preview_matches(r"[ \t]+$", "", SearchOptions(regular_expression=True))
    assert dialog.preview_table.rowCount() == 1

    other_editor = window.create_editor_tab(text="another document")
    window.remove_tab(0)

    assert window.editor is other_editor
    assert other_editor.textCursor().position() == 0
    assert dialog.preview_table.rowCount() == 0
    assert window._preview_source is None


def test_preview_matches_shows_line_after_all_same_line_replacements(
    app: QApplication,
) -> None:
    """すべての同じ行の置換後、プレビューがを表示するの行に一致することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText('<h2 class="wp-block-heading"></h2>')
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None

    window.preview_matches(
        "2",
        "3",
        SearchOptions(regular_expression=True),
    )

    assert window.find_replace_dialog.preview_table.rowCount() == 2
    first_after_item = window.find_replace_dialog.preview_table.item(0, 2)
    second_after_item = window.find_replace_dialog.preview_table.item(1, 2)
    assert first_after_item is not None
    assert second_after_item is not None
    assert first_after_item.text() == '<h3 class="wp-block-heading"></h3>'
    assert second_after_item.text() == '<h3 class="wp-block-heading"></h3>'


def test_preview_line_numbers_read_source_once_for_many_matches(
    app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """プレビューの行番号の読み込みの原文の1回だけの用の複数の一致箇所を確認する。"""
    _ = app
    window = MainWindow()
    source = "x\n" * 200
    window.editor.setPlainText(source)
    options = SearchOptions()
    matches = window.search_engine.find_all(source, "x", options)
    original = window.editor.toPlainText
    reads = 0

    def count_read() -> str:
        """テスト中に本文を読み出した回数を記録する。"""
        nonlocal reads
        reads += 1
        return original()

    monkeypatch.setattr(window.editor, "toPlainText", count_read)
    rows = window._preview_rows(source, matches, "x", "y", options, 0)

    assert len(rows) == 200
    assert rows[0][0] == 1
    assert rows[-1][0] == 200
    assert reads == 1


def test_preview_matches_uses_selected_text_only(app: QApplication) -> None:
    """プレビューがを使うの選択文字列のだけに一致することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("outside  \ninside  \noutside  ")
    cursor = window.editor.textCursor()
    cursor.setPosition(10)
    cursor.setPosition(19, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.search_scope = (cursor.selectionStart(), cursor.selectionEnd())
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None

    window.preview_matches(
        r"[ \t]+$",
        "",
        SearchOptions(regular_expression=True, selected_only=True),
    )

    assert window.find_replace_dialog.preview_table.rowCount() == 1
    line_item = window.find_replace_dialog.preview_table.item(0, 0)
    assert line_item is not None
    assert line_item.text() == "2"


def test_search_highlights_all_matches(app: QApplication) -> None:
    """検索がすべての一致箇所を強調表示することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("alpha\nbeta alpha\nalpha")

    window.update_search_highlights("alpha", SearchOptions())

    assert [match.start for match in window.editor.search_matches] == [0, 11, 17]
    assert len(window.editor.extraSelections()) == 3


def test_search_highlight_positions_stay_aligned_after_emoji(
    app: QApplication,
) -> None:
    """検索の強調表示の位置の維持するの位置が一致した後の絵文字を確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("emoji 💦 before\n<p><strong>target</strong></p>")

    window.update_search_highlights("<strong>", SearchOptions())

    selections = window.editor.extraSelections()
    assert len(selections) == 1
    assert selections[0].cursor.selectedText() == "<strong>"
    assert selections[0].format.background().color().name() == "#ffff00"


def test_find_next_positions_stay_aligned_after_emoji(app: QApplication) -> None:
    """次の検索の位置の維持するの位置が一致した後の絵文字を確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("emoji 💦 before\n<p><strong>target</strong></p>")

    window.find_next("<strong>", SearchOptions())

    assert window.editor.textCursor().selectedText() == "<strong>"


def test_search_highlights_can_target_selected_text_only(app: QApplication) -> None:
    """検索ができるの対象の選択文字列のだけを強調表示することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("target\ninside target\noutside target")
    cursor = window.editor.textCursor()
    cursor.setPosition(7)
    cursor.setPosition(20, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.search_scope = (cursor.selectionStart(), cursor.selectionEnd())

    window.update_search_highlights("target", SearchOptions(selected_only=True))

    assert len(window.editor.search_matches) == 1
    assert window.editor.search_matches[0].start == 14
    assert len(window.editor.extraSelections()) == 2


def test_selected_scope_shows_search_and_exclusion_marker_colors(
    app: QApplication,
) -> None:
    """選択中の対象範囲が検索と除外のマーカーの色を表示することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("outside target\n[target] target\noutside target")
    scope_start = len("outside target\n")
    scope_end = len("outside target\n[target] target")
    cursor = window.editor.textCursor()
    cursor.setPosition(scope_start)
    cursor.setPosition(scope_end, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.search_scope = (scope_start, scope_end)

    window.update_search_highlights(
        "target",
        SearchOptions(selected_only=True, exclusion_text="[target]"),
    )

    assert window.editor.textCursor().hasSelection()
    assert (
        window.editor.textCursor().selectionStart(),
        window.editor.textCursor().selectionEnd(),
    ) == (scope_start, scope_end)
    assert [match.text for match in window.editor.search_matches] == ["target"]
    assert [match.text for match in window.editor.search_exclusion_matches] == [
        "[target]"
    ]
    marked_text_and_color = {
        selection.cursor.selectedText(): selection.format.background().color().name()
        for selection in window.editor.extraSelections()
    }
    assert marked_text_and_color["target"] == "#ffff00"
    assert marked_text_and_color["[target]"] == "#ff9900"


def test_scope_toggle_close_and_reopen_keep_real_editor_selection(
    app: QApplication, tmp_path: Path,
) -> None:
    """対象範囲の切り替えの閉じる操作と開き直す操作の保持するの実際のエディターの選択範囲を確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("A target\nB target\n")
    cursor = window.editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len("A target"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    assert dialog.find_text_edit.text() == "A target"
    dialog.find_text_edit.setText("target")
    dialog.selected_only_check_box.setChecked(True)
    assert window.search_scope == (0, len("A target"))
    assert window.editor.search_scope_bounds == window.search_scope
    assert window.editor.textCursor().selectedText() == "A target"

    dialog.selected_only_check_box.setChecked(False)
    assert window.editor.textCursor().selectedText() == "A target"
    assert window.search_scope == (0, len("A target"))
    assert window.editor.search_scope_bounds is None
    assert len(window.editor.search_matches) == 2

    dialog.close()
    assert window.editor.textCursor().selectedText() == "A target"
    assert window.search_scope is None
    assert window.editor.search_matches == []
    cursor = window.editor.textCursor()
    cursor.setPosition(len("A target\n"))
    cursor.setPosition(len("A target\nB target"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    assert dialog.find_text_edit.text() == "target"
    dialog.selected_only_check_box.setChecked(True)
    assert window.search_scope == (len("A target\n"), len("A target\nB target"))
    dialog.selected_only_check_box.setChecked(False)
    assert window.editor.textCursor().selectedText() == "B target"
    window.preview_matches("target", "done", SearchOptions())
    assert dialog.preview_table.rowCount() == 2


def test_scope_reset_replaces_new_paragraph_without_revisiting_old_one(
    app: QApplication, tmp_path: Path,
) -> None:
    """対象範囲を設定し直すと、以前の段落に戻らず新しい段落だけを置換することを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    source = "A <strong > end\nB <strong > end\nC <strong > end"
    window.editor.setPlainText(source)
    cursor = window.editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len("A <strong > end"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("<strong >")
    replacement = '<strong style="color: #333333;background-color: #FFDDEE">'
    dialog.replace_text_edit.setText(replacement)
    dialog.selected_only_check_box.setChecked(True)
    dialog.replace_all_button.click()
    assert window.editor.toPlainText().count(replacement) == 1
    assert window.editor.toPlainText().count("<strong >") == 2
    assert window.search_scope is None
    assert window.editor.search_matches == []
    assert window.editor.search_scope_bounds is None

    current_text = window.editor.toPlainText()
    second_start = current_text.index("B <strong > end")
    second_end = second_start + len("B <strong > end")
    cursor = window.editor.textCursor()
    cursor.setPosition(second_start)
    cursor.setPosition(second_end, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    dialog.reset_selection_scope_button.click()
    assert window.search_scope == (second_start, second_end)
    dialog.replace_all_button.click()
    assert window.editor.toPlainText().count(replacement) == 2
    assert window.editor.toPlainText().count("<strong >") == 1
    assert window.editor.search_matches == []
    assert window.editor.search_scope_bounds is None
    assert "C <strong > end" in window.editor.toPlainText()


def test_find_clears_old_scope_markers_and_preview_but_keeps_conditions(
    app: QApplication, tmp_path: Path,
) -> None:
    """検索が古いの対象範囲のマーカーとプレビューの一方の保持するの条件を消すことを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("A target\nB target")
    cursor = window.editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len("A target"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("target")
    dialog.replace_text_edit.setText("done")
    dialog.selected_only_check_box.setChecked(True)
    dialog.preview_button.click()
    assert dialog.preview_table.rowCount() == 1

    dialog.find_button.click()

    assert window.editor.textCursor().selectedText() == "target"
    assert window.search_scope is None
    assert window.editor.search_matches == []
    assert window.editor.current_search_match_bounds == (2, 8)
    assert window.editor.search_scope_bounds is None
    assert dialog.preview_table.rowCount() == 0
    assert window._preview_source is None
    assert dialog.find_text_edit.text() == "target"
    assert dialog.replace_text_edit.text() == "done"
    assert dialog.selected_only_check_box.isChecked()
    dialog.find_button.click()
    assert window.search_scope is None
    assert window.editor.current_search_match_bounds is None

    cursor = window.editor.textCursor()
    cursor.setPosition(len("A target\n"))
    cursor.setPosition(len("A target\nB target"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    dialog.find_button.click()
    assert window.editor.textCursor().selectedText() == "target"
    assert window.search_scope is None


@pytest.mark.parametrize("backward", [False, True])
def test_search_centers_current_result_and_clears_marker_on_edit(
    app: QApplication, tmp_path: Path, backward: bool,
) -> None:
    """検索結果を画面中央に表示し、編集するとマーカーを消すことを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    editor = window.editor
    source = "\n".join("target" if row == 80 else f"line {row}" for row in range(160))
    editor.setPlainText(source)
    window.resize(700, 500)
    window.show()
    app.processEvents()
    editor.moveCursor(QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start)
    search = window.find_previous if backward else window.find_next
    search("target", SearchOptions())
    app.processEvents()

    position = source.index("target")
    cursor = editor.textCursor()
    assert cursor.selectedText() == "target"
    assert editor.current_search_match_bounds == (position, position + len("target"))
    assert editor.search_matches == []
    center = editor.viewport().rect().center().y()
    assert abs(editor.cursorRect(cursor).center().y() - center) <= 2 * editor.fontMetrics().height()
    assert any(
        selection.cursor.selectedText() == "target"
        and selection.format.background().color().name() == editor.current_match_marker_color.lower()
        for selection in editor.extraSelections()
    )
    editor.insertPlainText("edited")
    assert editor.current_search_match_bounds is None
    assert not editor.extraSelections()
    window.hide()


def test_reopening_search_keeps_text_until_user_clears_it(
    app: QApplication, tmp_path: Path,
) -> None:
    """開き直しの検索が文字列を保持する（利用者がその内容を消すまで）を確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("first\nsecond")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("first")
    dialog.exclusion_text_edit.setText("second")
    dialog.replace_text_edit.setText("done")
    dialog.case_sensitive_check_box.setChecked(True)
    dialog.close()
    cursor = window.editor.textCursor()
    cursor.setPosition(len("first\n"))
    cursor.setPosition(len("first\nsecond"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    assert dialog.find_text_edit.text() == "first"
    assert dialog.exclusion_text_edit.text() == "second"
    assert dialog.replace_text_edit.text() == "done"
    assert dialog.case_sensitive_check_box.isChecked()

    dialog.clear_text_button.click()
    dialog.close()
    window.show_find_replace_dialog()
    assert dialog.find_text_edit.text() == ""
    assert dialog.exclusion_text_edit.text() == ""
    assert dialog.replace_text_edit.text() == ""
    assert dialog.case_sensitive_check_box.isChecked()


def test_selected_only_find_then_replace_uses_current_match_not_old_scope(
    app: QApplication, tmp_path: Path,
) -> None:
    """選択範囲限定の検索の続いての置換が現在の一致のしないの古いの対象範囲を使うことを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("A target\nB target")
    cursor = window.editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len("A target"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("target")
    dialog.replace_text_edit.setText("done")
    dialog.selected_only_check_box.setChecked(True)
    dialog.find_button.click()
    assert window.search_scope is None

    dialog.replace_button.click()

    assert window.editor.toPlainText() == "A done\nB target"
    assert window.search_scope is None
    assert window.editor.search_matches == []
    assert dialog.find_text_edit.text() == "target"
    assert dialog.selected_only_check_box.isChecked()


def test_close_cancels_pending_markers_after_replacement(
    app: QApplication, tmp_path: Path,
) -> None:
    """置換後に閉じると、保留中のマーカー更新を取り消すことを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("target\n😀 target\n")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("target")
    dialog.replace_text_edit.setText("longer")
    assert len(window.editor.search_matches) == 2
    dialog.replace_all_button.click()
    cursor_after_replace = window.editor.textCursor().position()
    dialog.close()
    _process_delayed_ui_events(300)
    assert window.editor.toPlainText() == "longer\n😀 longer\n"
    assert window.editor.textCursor().position() == cursor_after_replace
    assert window.editor.search_matches == []
    assert window.editor.search_exclusion_matches == []
    assert window.editor.search_scope_bounds is None
    assert not hasattr(window, "search_highlight_timer")


def test_manual_edit_invalidates_scope_and_does_not_mark_another_tab(
    app: QApplication, tmp_path: Path,
) -> None:
    """手動の編集が対象範囲と行わないの目印の別のタブを無効にすることを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("target\n😀 target\n")
    cursor = window.editor.textCursor()
    cursor.setPosition(len("target\n"))
    cursor.setPosition(len("target\n😀 target"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("target")
    dialog.selected_only_check_box.setChecked(True)
    assert window.search_scope is not None

    cursor = window.editor.textCursor()
    cursor.setPosition(0)
    window.editor.setTextCursor(cursor)
    cursor.insertText("X")
    assert window.search_scope is None
    assert window.editor.search_matches == []
    assert window.editor.search_matches == []

    dialog.selected_only_check_box.setChecked(False)
    source = window.editor.toPlainText()
    assert all(source[item.start:item.end] == item.text for item in window.editor.search_matches)
    previous_editor = window.editor
    dialog.find_text_edit.setText("target")
    window.create_editor_tab("target in new tab")
    assert previous_editor.search_matches == []
    assert window.editor.search_matches == []


def test_find_replace_dialog_stays_bound_to_opening_tab(
    app: QApplication, tmp_path: Path,
) -> None:
    """検索・置換ダイアログの維持されるの関連付けたのへの開始のタブを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    source_editor = window.editor
    source_editor.setPlainText("target target")
    window._set_current_file_state(tmp_path / "source.md")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    assert "source.md" in dialog.windowTitle()
    assert "source.md" in dialog.target_file_label.text()
    dialog.find_text_edit.setText("target")
    dialog.replace_text_edit.setText("done")

    other_editor = window.create_editor_tab(text="target in other tab")
    window.show_find_replace_dialog()  # Ctrl+F while already open must retain the original target.
    assert window.editor is source_editor
    window.tab_widget.setCurrentIndex(1)
    dialog.find_button.click()
    assert window.editor is source_editor
    assert source_editor.textCursor().selectedText() == "target"
    window.tab_widget.setCurrentIndex(1)
    dialog.replace_all_button.click()
    assert source_editor.toPlainText() == "done done"
    assert other_editor.toPlainText() == "target in other tab"
    assert dialog.target_file_name == "source.md"


def test_find_replace_dialog_rebinds_only_after_close_and_reopen(
    app: QApplication, tmp_path: Path,
) -> None:
    """検索・置換ダイアログをいったん閉じて開き直した場合にだけ対象文書が切り替わることを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    source_editor = window.editor
    source_editor.setPlainText("target")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    other_editor = window.create_editor_tab(text="target elsewhere")

    window.remove_tab(0)
    assert not dialog.isVisible()
    assert window._find_replace_target is None
    assert window.editor is other_editor
    dialog.replace_all_requested.emit("target", "wrong", SearchOptions())
    assert other_editor.toPlainText() == "target elsewhere"

    window.show_find_replace_dialog()
    assert window._find_replace_target is other_editor
    dialog.replace_all_requested.emit("target", "done", SearchOptions())
    assert other_editor.toPlainText() == "done elsewhere"


def test_find_replace_dialog_close_then_reopen_from_other_tab(
    app: QApplication, tmp_path: Path,
) -> None:
    """検索・置換ダイアログの閉じる操作の続いての開き直す操作のからの別のタブを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    original_editor = window.editor
    original_editor.setPlainText("target A")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    other_editor = window.create_editor_tab(text="target B")

    dialog.close()
    assert window._find_replace_target is None
    window.show_find_replace_dialog()
    assert window._find_replace_target is other_editor
    dialog.replace_all_requested.emit("target", "done", SearchOptions())
    assert original_editor.toPlainText() == "target A"
    assert other_editor.toPlainText() == "done B"


def test_selected_search_scope_survives_switching_tabs(
    app: QApplication, tmp_path: Path,
) -> None:
    """選択中の検索範囲が切り替えのタブが起きても動作することを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    source_editor = window.editor
    source_editor.setPlainText("target outside\ntarget inside")
    cursor = source_editor.textCursor()
    cursor.setPosition(len("target outside\n"))
    cursor.setPosition(len(source_editor.toPlainText()), QTextCursor.MoveMode.KeepAnchor)
    source_editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.selected_only_check_box.setChecked(True)
    dialog.find_text_edit.setText("target")
    dialog.replace_text_edit.setText("done")
    scope = window.search_scope

    other_editor = window.create_editor_tab(text="target in another tab")
    assert window.search_scope == scope
    dialog.replace_all_button.click()
    assert source_editor.toPlainText() == "target outside\ndone inside"
    assert other_editor.toPlainText() == "target in another tab"


def test_find_replace_dialog_uses_editor_identity_for_same_named_tabs(
    app: QApplication, tmp_path: Path,
) -> None:
    """検索・置換ダイアログがエディターの識別情報の用の同じ名前付きのタブを使うことを確認する。"""
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    source_editor = window.editor
    source_editor.setPlainText("target A")
    window._set_current_file_state(tmp_path / "same.md")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    other_editor = window.create_editor_tab(text="target B", save_file_path=tmp_path / "same.md")
    dialog.replace_all_requested.emit("target", "done", SearchOptions())
    assert window.editor is source_editor
    assert source_editor.toPlainText() == "done A"
    assert other_editor.toPlainText() == "target B"

    window._set_current_file_state(tmp_path / "renamed.md")
    assert "renamed.md" in dialog.target_file_label.text()


def test_find_next_can_target_visible_text_only(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """次を検索するときに、画面に表示されている範囲だけを対象にできることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("visible target\nhidden target")
    monkeypatch.setattr(
        window,
        "_visible_search_bounds",
        lambda source_length: (0, len("visible target\n")),
    )
    cursor = window.editor.textCursor()
    cursor.setPosition(len(window.editor.toPlainText()))
    window.editor.setTextCursor(cursor)

    window.find_next("target", SearchOptions(visible_only=True))

    assert window.editor.textCursor().selectedText() == "target"
    assert window.editor.textCursor().selectionStart() == 8


def test_replace_all_can_target_visible_text_only(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """全置換が表示中の文字列のだけを対象にできることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("visible target\nhidden target")
    monkeypatch.setattr(
        window,
        "_visible_search_bounds",
        lambda source_length: (0, len("visible target\n")),
    )

    window.replace_all("target", "match", SearchOptions(visible_only=True))

    assert window.editor.toPlainText() == "visible match\nhidden target"


def test_replace_marked_matches_replaces_current_markers_only(
    app: QApplication,
) -> None:
    """現在のマーカーが指す一致箇所だけを置換することを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("target keep target")
    window.update_search_highlights("target", SearchOptions())
    window.editor.search_matches = window.editor.search_matches[:1]

    window.replace_marked_matches("target", "done", SearchOptions())

    assert window.editor.toPlainText() == "done keep target"


def test_replace_marked_matches_supports_regex_groups(app: QApplication) -> None:
    """マーカー付きの一致の置換で正規表現のグループ参照が使えることを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("item-01 keep item-20")
    options = SearchOptions(regular_expression=True)
    window.update_search_highlights(r"item-(\d+)", options)

    window.replace_marked_matches(r"item-(\d+)", r"code-\1", options)

    assert window.editor.toPlainText() == "code-01 keep code-20"


def test_selected_and_visible_options_use_intersection(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """選択中のと表示中のオプションの使用の共通部分を確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("first target\nsecond target\nthird target")
    window.search_scope = (len("first target\n"), len("first target\nsecond target\n"))
    monkeypatch.setattr(
        window,
        "_visible_search_bounds",
        lambda source_length: (0, len("first target\nsecond target\n")),
    )

    window.update_search_highlights(
        "target",
        SearchOptions(selected_only=True, visible_only=True),
    )

    assert len(window.editor.search_matches) == 1
    assert window.editor.search_matches[0].start == 20


def test_invalid_regex_clears_search_highlights(app: QApplication) -> None:
    """不正な正規表現が検索の強調表示を消すことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("alpha")
    window.update_search_highlights("alpha", SearchOptions())

    window.update_search_highlights("[", SearchOptions(regular_expression=True))

    assert window.editor.search_matches == []
    assert window.editor.extraSelections() == []


def test_search_refresh_clears_stale_highlights_immediately(app: QApplication) -> None:
    """検索の再表示が古くなったの強調表示のすぐにを消すことを確認する。"""
    _ = app
    window = MainWindow()
    window.editor.setPlainText("alpha beta")
    window.update_search_highlights("alpha", SearchOptions())

    window.refresh_search_highlights("nomatch", SearchOptions())

    assert window.editor.search_matches == []


def test_dialog_exclusion_is_shared_by_find_highlight_preview_and_replace(
    app: QApplication, tmp_path: Path,
) -> None:
    """ダイアログの除外条件が検索、マーカー表示、プレビュー、置換に共通して使われることを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    source = "<br><br>\nplain\n<p>\ncomma、\n"
    window.editor.setPlainText(source)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText(r"\n")
    dialog.replace_text_edit.setText(" / ")
    dialog.regular_expression_check_box.setChecked(True)
    dialog.exclusion_text_edit.setText(r"<br><br>\n|>\n")
    options = dialog.current_search_options()

    window.update_search_highlights(r"\n", options)
    assert [match.start for match in window.editor.search_matches] == [source.index("plain") + 5, len(source) - 1]
    dialog.find_button.click()
    assert window.editor.textCursor().selectionStart() == source.index("plain") + 5
    dialog.preview_button.click()
    assert dialog.preview_table.rowCount() == 2
    assert window.editor.toPlainText() == source
    dialog.replace_all_button.click()
    assert window.editor.toPlainText() == "<br><br>\nplain / <p>\ncomma、 / "


def test_preview_keeps_exclusions_that_span_lines(app: QApplication, tmp_path: Path) -> None:
    """プレビューが複数行にまたがる除外範囲を保持することを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("BEGIN\nkeep target\nEND\nchange target")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    options = SearchOptions(regular_expression=True, exclusion_text=r"BEGIN[\s\S]*?END")
    window.preview_matches("target", "done", options)
    assert dialog.preview_table.rowCount() == 1
    item = dialog.preview_table.item(0, 2)
    assert item is not None and item.text() == "change done"
    window.replace_all("target", "done", options)
    assert window.editor.toPlainText() == "BEGIN\nkeep target\nEND\nchange done"


def test_marked_replace_rechecks_changed_exclusion(app: QApplication, tmp_path: Path) -> None:
    """マーカー付きの置換が変更された除外を再確認することを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("[target] target")
    window.update_search_highlights("target", SearchOptions())
    window.replace_marked_matches("target", "done", SearchOptions(exclusion_text="[target]"))
    assert window.editor.toPlainText() == "[target] done"


@pytest.mark.parametrize("visible_only", [False, True])
def test_exclusion_inside_search_scope(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, visible_only: bool,
) -> None:
    """除外内の検索範囲を確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("outside target\n[target] target\noutside target")
    bounds = (len("outside target\n"), len("outside target\n[target] target\n"))
    window.search_scope = bounds
    monkeypatch.setattr(window, "_visible_search_bounds", lambda length: bounds)
    options = SearchOptions(
        selected_only=not visible_only, visible_only=visible_only, exclusion_text="[target]",
    )
    window.replace_all("target", "done", options)
    assert window.editor.toPlainText() == "outside target\n[target] done\noutside target"


def test_invalid_exclusion_never_modifies_document(app: QApplication, tmp_path: Path) -> None:
    """除外条件が不正な場合に本文を変更しないことを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("target")
    window.show_find_replace_dialog()
    options = SearchOptions(regular_expression=True, exclusion_text="[")
    window.replace_all("target", "done", options)
    assert window.editor.toPlainText() == "target"
    assert window.find_replace_dialog is not None
    assert window.find_replace_dialog.error_label.text()


def test_current_replace_refuses_manually_selected_excluded_newline(
    app: QApplication, tmp_path: Path,
) -> None:
    """除外対象の改行を手動で選択しても、1件置換の対象にならないことを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("<p>\nplain\n")
    cursor = window.editor.textCursor()
    cursor.setPosition(3)
    cursor.setPosition(4, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.replace_current(r"\n", "X", SearchOptions(regular_expression=True, exclusion_text=r">\n"))
    assert window.editor.toPlainText() == "<p>\nplain\n"


def test_current_replace_evaluates_exclusion_inside_selected_scope(
    app: QApplication, tmp_path: Path,
) -> None:
    """1件置換で選択範囲内の除外条件を評価することを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("KEEP target")
    cursor = window.editor.textCursor()
    cursor.setPosition(5)
    cursor.setPosition(11, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.search_scope = (5, 11)
    window.replace_current("target", "done", SearchOptions(
        selected_only=True, exclusion_text="KEEP target",
    ))
    assert window.editor.toPlainText() == "KEEP done"


def test_preview_same_line_preserves_excluded_result(app: QApplication, tmp_path: Path) -> None:
    """プレビューの同じ行が除外した結果を維持することを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("[target] target target")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    window.preview_matches("target", "done", SearchOptions(exclusion_text="[target]"))
    assert dialog.preview_table.rowCount() == 2
    for row in range(2):
        item = dialog.preview_table.item(row, 2)
        assert item is not None and item.text() == "[target] done done"
    assert [match.text for match in window.editor.search_matches] == ["target", "target"]
    assert [match.text for match in window.editor.search_exclusion_matches] == ["[target]"]


def test_main_window_can_switch_display_language(app: QApplication) -> None:
    """メインウインドウが切り替えの表示の言語が可能であることを確認する。"""
    _ = app
    window = MainWindow()

    try:
        window.set_language("en")
        assert window.search_menu.title() == "&Search"
        assert window.help_menu.title() == "&Help"
        assert window.find_action.text() == "&Find / Replace..."
        assert window.user_help_action.text() == "&Help..."

        window.set_language("ja")
        assert window.search_menu.title() == "検索(&S)"
        assert window.help_menu.title() == "ヘルプ(&H)"
        assert window.find_action.text() == "検索 / 置換(&F)..."
        assert window.user_help_action.text() == "使い方(&H)..."
    finally:
        Path("settings.json").unlink(missing_ok=True)


def test_reload_file_can_use_cp932_encoding(app: QApplication, tmp_path) -> None:
    """再読込のファイルが使用のCP932の文字コードが可能であることを確認する。"""
    _ = app
    load_file_path = tmp_path / "sample_cp932.txt"
    load_file_path.write_text("日本語の文章です。", encoding="cp932")
    window = MainWindow()
    window.current_save_file_path = load_file_path

    window.reload_file("cp932")

    assert window.editor.toPlainText() == "日本語の文章です。"
    assert window.current_encoding == "cp932"


@pytest.mark.parametrize("replace_kind", ["current", "all", "marked"])
def test_successful_replacement_clears_markers_until_explicit_search(
    app: QApplication, tmp_path: Path, replace_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """置換後は、利用者が改めて検索するまでマーカーが消えた状態を保つことを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("target target")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("target")
    assert len(window.editor.search_matches) == 2
    options = dialog.current_search_options()
    if replace_kind == "current":
        window.find_next("target", options)
        window.replace_current("target", "done", options)
        assert window.editor.toPlainText() == "done target"
    elif replace_kind == "all":
        window.replace_all("target", "done", options)
        assert window.editor.toPlainText() == "done done"
    else:
        window.replace_marked_matches("target", "done", options)
        assert window.editor.toPlainText() == "done done"

    assert window.editor.search_matches == []
    assert window.editor.search_exclusion_matches == []
    assert window.editor.search_scope_bounds is None
    assert not hasattr(window, "search_highlight_timer")
    _process_delayed_ui_events(300)
    assert window.editor.search_matches == []

    with monkeypatch.context() as patcher:
        patcher.setattr(
            window,
            "update_search_highlights",
            lambda *_args: pytest.fail("replacement scheduled a search rescan"),
        )
        cursor = window.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText("!")
        _process_delayed_ui_events(300)
    assert window.editor.search_matches == []
    assert not hasattr(window, "search_highlight_timer")

    if replace_kind == "current":
        window.find_next("target", options)
        assert window.editor.textCursor().selectedText() == "target"
        assert window.editor.search_matches == []

    dialog.find_text_edit.setText("done")
    expected = 1 if replace_kind == "current" else 2
    assert len(window.editor.search_matches) == expected


def test_normalise_operation_clears_markers_after_replacement(
    app: QApplication, tmp_path: Path,
) -> None:
    """置換後、正規化の操作がマーカーを消すことを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("\uff21 \uff21")
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("\uff21")
    assert len(window.editor.search_matches) == 2

    window.apply_regex_normalise_operation("fullwidth_alphabet_to_halfwidth")

    assert window.editor.toPlainText() == "A A"
    assert window.editor.search_matches == []
    assert not hasattr(window, "search_highlight_timer")


def test_empty_search_clears_all_markers_and_scope_background(
    app: QApplication, tmp_path: Path,
) -> None:
    """空の検索がすべてのマーカーと対象範囲の背景を消すことを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    window.editor.setPlainText("target [target]\n")
    cursor = window.editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len("target [target]"), QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window.show_find_replace_dialog()
    dialog = window.find_replace_dialog
    assert dialog is not None
    dialog.find_text_edit.setText("target")
    dialog.exclusion_text_edit.setText("[target]")
    dialog.selected_only_check_box.setChecked(True)
    assert window.editor.search_matches
    assert window.editor.search_exclusion_matches
    assert window.editor.search_scope_bounds is not None

    dialog.find_text_edit.setText("")
    assert window.editor.search_matches == []
    assert window.editor.search_exclusion_matches == []
    assert window.editor.search_scope_bounds is None
    assert window.editor.textCursor().selectedText() == "target [target]"


def test_cursor_motion_does_not_rebuild_unchanged_search_markers(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """カーソル移動の行わないの再構築の維持されるの検索マーカーを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json", restore_unsaved_backup=False)
    editor = window.editor
    editor.setPlainText("😀 target\ntarget\n")
    editor.set_search_matches([
        SearchMatch(2, 8, "target"),
        SearchMatch(9, 15, "target"),
    ])
    marked_text = [
        selection.cursor.selectedText() for selection in editor.extraSelections()
    ]
    assert marked_text == ["target", "target"]
    calls = 0
    original_apply = editor._apply_extra_selections

    def count_apply() -> None:
        """検索マーカーの更新回数を数える。"""
        nonlocal calls
        calls += 1
        original_apply()

    monkeypatch.setattr(editor, "_apply_extra_selections", count_apply)
    cursor = editor.textCursor()
    cursor.setPosition(1)
    editor.setTextCursor(cursor)
    cursor.setPosition(2)
    editor.setTextCursor(cursor)
    assert calls == 0
    cursor.setPosition(8, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)
    assert calls == 1


def test_save_file_runs_pre_save_grammar_check_and_can_cancel(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """ファイル保存前に文法チェックが実行され、保存を取り消せることを確認する。"""
    _ = app
    save_file_path = tmp_path / "sample.wp.html"
    save_file_path.write_text("original", encoding="utf-8")
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.current_save_file_path = save_file_path
    window.editor.setPlainText(
        "<!-- wp:paragraph -->\n"
        "段落分割後にp開始タグが抜けています。</p>\n"
        "<!-- /wp:paragraph -->"
    )
    captured: dict[str, str] = {}

    def capture_question(
        _parent: object,
        title: str,
        text: str,
        *_args: object,
        **_kwargs: object,
    ) -> QMessageBox.StandardButton:
        """保存前に表示される確認の内容を記録する。"""
        captured["title"] = title
        captured["text"] = text
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", capture_question)

    assert not window.save_file()
    assert save_file_path.read_text(encoding="utf-8") == "original"
    assert captured["title"] == "保存前の文法チェック"
    assert "段落ブロック内に `<p>` 開始タグが見つかりません" in captured["text"]
