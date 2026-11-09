from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QMessageBox

from main import MainWindow
from search.html_typo_lint import HtmlTypoLintMessage
from search.search_engine import SearchOptions


def _process_delayed_ui_events(delay_ms: int = 75) -> None:
    loop = QEventLoop()
    QTimer.singleShot(delay_ms, loop.quit)
    loop.exec()
    QApplication.processEvents()


@pytest.mark.parametrize("severity,confirmations", [("info", 0), ("warning", 1), ("error", 1)])
def test_save_lint_confirmation_respects_severity(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    severity: str, confirmations: int,
) -> None:
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json", unsaved_backup_path=tmp_path / "backup.json")
    window.html_typo_lint_enabled = True
    original = "KEEP THIS TEXT"
    window.editor.setPlainText(original)
    message = HtmlTypoLintMessage(severity, "html_typo_lint.missing_html_closing_tag", 1, {"tag": "p"})
    monkeypatch.setattr(window, "_lint_document", lambda text: [message])
    requests = []

    def confirm(*args, **kwargs):
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
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_find_next_selects_regex_match(app: QApplication) -> None:
    _ = app
    window = MainWindow()
    window.editor.setPlainText("abc item-123 xyz")

    window.find_next(
        r"item-\d+",
        SearchOptions(regular_expression=True),
    )

    assert window.editor.textCursor().selectedText() == "item-123"


def test_replace_all_uses_regex_groups(app: QApplication) -> None:
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
    assert dialog.preview_table.rowCount() == 4
    window.editor.undo()
    assert window.editor.toPlainText() == "① ＡＢＣ １２３ ② ⑩ ⑳"


def test_replace_current_uses_unicode_normalization_route(app: QApplication) -> None:
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
    assert window.find_replace_dialog.preview_table.rowCount() == 2


def test_replace_all_button_replaces_wordpress_paragraph_gap_regex(
    app: QApplication,
    tmp_path,
) -> None:
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
    assert window.find_replace_dialog.preview_table.rowCount() == 2


def test_low_load_mode_skips_auto_search_highlights(
    app: QApplication,
    tmp_path,
) -> None:
    _ = app
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.reduced_error_check_enabled = True
    window.editor.setPlainText("target target")
    window.show_find_replace_dialog()
    assert window.find_replace_dialog is not None

    window.find_replace_dialog.find_text_edit.setText("target")

    assert window.editor.search_matches == []


def test_replace_current_keeps_cursor_after_replaced_text(app: QApplication) -> None:
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
    _ = app
    window = MainWindow()
    window.editor.setPlainText("alpha, beta, gamma")

    window.find_next(",", SearchOptions())
    window.replace_current(",", "\n", SearchOptions())

    assert window.editor.toPlainText() == "alpha\n beta, gamma"
    assert window.editor.textCursor().blockNumber() == 1
    assert window.editor.textCursor().positionInBlock() == 0


def test_invalid_regex_does_not_modify_document(app: QApplication) -> None:
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


def test_regex_normalise_rewrites_document_text(app: QApplication) -> None:
    _ = app
    window = MainWindow()
    window.editor.setPlainText("ＷｏｒｄＰｒｅｓｓとＨＴＭＬ")
    window.show_find_replace_dialog()

    window.apply_regex_normalise_operation("fullwidth_alphabet_to_halfwidth")

    assert window.editor.toPlainText() == "WordPressとHTML"


def test_regex_normalise_can_target_selected_text_only(app: QApplication) -> None:
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
    _ = app
    window = MainWindow()
    window.editor.setPlainText("alpha beta alpha")
    cursor = window.editor.textCursor()
    cursor.setPosition(len(window.editor.toPlainText()))
    window.editor.setTextCursor(cursor)

    window.find_previous("alpha", SearchOptions())

    assert window.editor.textCursor().selectedText() == "alpha"
    assert window.editor.textCursor().selectionStart() == 11


def test_grammar_check_action_is_available_from_search_menu(
    app: QApplication,
) -> None:
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


def test_preview_matches_shows_line_after_all_same_line_replacements(
    app: QApplication,
) -> None:
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


def test_preview_matches_uses_selected_text_only(app: QApplication) -> None:
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
    _ = app
    window = MainWindow()
    window.editor.setPlainText("alpha\nbeta alpha\nalpha")

    window.update_search_highlights("alpha", SearchOptions())

    assert [match.start for match in window.editor.search_matches] == [0, 11, 17]
    assert len(window.editor.extraSelections()) == 3


def test_search_highlight_positions_stay_aligned_after_emoji(
    app: QApplication,
) -> None:
    _ = app
    window = MainWindow()
    window.editor.setPlainText("emoji 💦 before\n<p><strong>target</strong></p>")

    window.update_search_highlights("<strong>", SearchOptions())

    selections = window.editor.extraSelections()
    assert len(selections) == 1
    assert selections[0].cursor.selectedText() == "<strong>"
    assert selections[0].format.background().color().name() == "#ffff00"


def test_find_next_positions_stay_aligned_after_emoji(app: QApplication) -> None:
    _ = app
    window = MainWindow()
    window.editor.setPlainText("emoji 💦 before\n<p><strong>target</strong></p>")

    window.find_next("<strong>", SearchOptions())

    assert window.editor.textCursor().selectedText() == "<strong>"


def test_search_highlights_can_target_selected_text_only(app: QApplication) -> None:
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
    assert len(window.editor.extraSelections()) == 1


def test_find_next_can_target_visible_text_only(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    _ = app
    window = MainWindow()
    window.editor.setPlainText("target keep target")
    window.update_search_highlights("target", SearchOptions())
    window.editor.search_matches = window.editor.search_matches[:1]

    window.replace_marked_matches("target", "done", SearchOptions())

    assert window.editor.toPlainText() == "done keep target"


def test_replace_marked_matches_supports_regex_groups(app: QApplication) -> None:
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
    _ = app
    window = MainWindow()
    window.editor.setPlainText("alpha")
    window.update_search_highlights("alpha", SearchOptions())

    window.update_search_highlights("[", SearchOptions(regular_expression=True))

    assert window.editor.search_matches == []
    assert window.editor.extraSelections() == []


def test_scheduled_search_clears_stale_highlights_immediately(app: QApplication) -> None:
    _ = app
    window = MainWindow()
    window.editor.setPlainText("alpha beta")
    window.update_search_highlights("alpha", SearchOptions())

    window.schedule_search_highlights("nomatch", SearchOptions())

    assert window.editor.search_matches == []


def test_dialog_exclusion_is_shared_by_find_highlight_preview_and_replace(
    app: QApplication, tmp_path: Path,
) -> None:
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
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("[target] target")
    window.update_search_highlights("target", SearchOptions())
    window.replace_marked_matches("target", "done", SearchOptions(exclusion_text="[target]"))
    assert window.editor.toPlainText() == "[target] done"


@pytest.mark.parametrize("visible_only", [False, True])
def test_exclusion_inside_search_scope(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, visible_only: bool,
) -> None:
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
    assert window.editor.extraSelections() == []


def test_main_window_can_switch_display_language(app: QApplication) -> None:
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
    _ = app
    load_file_path = tmp_path / "sample_cp932.txt"
    load_file_path.write_text("日本語の文章です。", encoding="cp932")
    window = MainWindow()
    window.current_save_file_path = load_file_path

    window.reload_file("cp932")

    assert window.editor.toPlainText() == "日本語の文章です。"
    assert window.current_encoding == "cp932"


def test_save_file_runs_pre_save_grammar_check_and_can_cancel(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
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
        captured["title"] = title
        captured["text"] = text
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", capture_question)

    assert not window.save_file()
    assert save_file_path.read_text(encoding="utf-8") == "original"
    assert captured["title"] == "保存前の文法チェック"
    assert "段落ブロック内に `<p>` 開始タグが見つかりません" in captured["text"]
