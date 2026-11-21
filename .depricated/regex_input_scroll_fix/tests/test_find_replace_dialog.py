from __future__ import annotations

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMenu,
    QPlainTextEdit,
    QSizePolicy,
)

from dialogs.find_replace_dialog import FindReplaceDialog
from dialogs.regex_input_edit import RegexInputHighlighter
from localization.translator import Translator


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_recipe_sets_find_replace_and_regex_mode(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "ja")
    dialog = FindReplaceDialog(translator)

    dialog.set_search_recipe(r"[ \t]+$", "")

    assert dialog.find_text_edit.text() == r"[ \t]+$"
    assert dialog.replace_text_edit.text() == ""
    assert dialog.regular_expression_check_box.isChecked()


def test_paragraph_boundary_recipe_matches_lf_and_crlf(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)
    menu = dialog.recipe_button.menu()
    assert menu is not None
    matching_actions = [
        action
        for action in menu.actions()
        if action.text() == "Paragraph boundary to line breaks"
    ]
    assert len(matching_actions) == 1

    matching_actions[0].trigger()

    assert dialog.find_text_edit.text() == r"</p>\r?\n<p>"
    assert dialog.replace_text_edit.text() == "<br><br>\n"
    assert re.sub(
        dialog.find_text_edit.text(),
        dialog.replace_text_edit.text(),
        "before</p>\r\n<p>after",
    ) == "before<br><br>\nafter"


def test_paragraph_boundary_recipe_can_allow_surrounding_spaces(
    app: QApplication,
) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)
    menu = dialog.recipe_button.menu()
    assert menu is not None
    matching_actions = [
        action
        for action in menu.actions()
        if action.text() == "Paragraph boundary with spaces to line breaks"
    ]
    assert len(matching_actions) == 1

    matching_actions[0].trigger()

    assert dialog.find_text_edit.text() == r"</p>[ \t]*\r?\n[ \t]*<p>"
    assert dialog.replace_text_edit.text() == "<br><br>\n"
    assert re.sub(
        dialog.find_text_edit.text(),
        dialog.replace_text_edit.text(),
        "before</p>  \r\n  <p>after",
    ) == "before<br><br>\nafter"


def test_preview_table_displays_rows(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)

    dialog.set_preview_rows(
        [(2, "second  ", "second")],
        "Previewing 1 match(es).",
    )

    assert dialog.preview_summary_label.text() == "Previewing 1 match(es)."
    assert dialog.preview_table.rowCount() == 1
    line_item = dialog.preview_table.item(0, 0)
    before_item = dialog.preview_table.item(0, 1)
    after_item = dialog.preview_table.item(0, 2)
    assert line_item is not None
    assert before_item is not None
    assert after_item is not None
    assert line_item.text() == "2"
    assert before_item.text() == "second  "
    assert after_item.text() == "second"


def test_preview_table_clears_when_search_parameters_change(
    app: QApplication,
) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)

    dialog.set_preview_rows(
        [(2, "second  ", "second")],
        "Previewing 1 match(es).",
    )

    dialog.find_text_edit.setText("changed")

    assert dialog.preview_summary_label.text() == ""
    assert dialog.preview_table.rowCount() == 0


def test_dialog_returns_visible_only_search_option(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)

    dialog.visible_only_check_box.setChecked(True)

    assert dialog.current_search_options().visible_only


def test_regex_inputs_resize_for_multiline_patterns(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)
    multiline_pattern = "first line\nsecond line"
    dialog.show()
    QApplication.processEvents()
    single_line_height = dialog.find_text_edit.height()

    dialog.find_text_edit.setText(multiline_pattern)
    QApplication.processEvents()

    assert dialog.find_text_edit.text() == multiline_pattern
    assert dialog.find_text_edit.height() > single_line_height
    assert dialog.find_text_edit.minimumHeight() == dialog.find_text_edit.maximumHeight()
    assert (
        dialog.find_text_edit.verticalScrollBarPolicy()
        == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    assert (
        dialog.find_text_edit.sizePolicy().verticalPolicy()
        == QSizePolicy.Policy.Fixed
    )
    assert (
        dialog.find_text_edit.lineWrapMode()
        == QPlainTextEdit.LineWrapMode.WidgetWidth
    )
    assert (
        dialog.replace_text_edit.lineWrapMode()
        == QPlainTextEdit.LineWrapMode.WidgetWidth
    )


def test_multiline_regex_input_keeps_text_visible_around_blank_line(
    app: QApplication,
) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)
    multiline_pattern = "<!-- /wp:heading -->\n\n<!-- wp:paragraph -->"
    blank_line_position = multiline_pattern.index("\n") + 1

    dialog.show()
    dialog.find_text_edit.setText(multiline_pattern)
    dialog.regular_expression_check_box.setChecked(True)
    dialog.find_text_edit.setCursorPosition(blank_line_position)
    dialog.find_text_edit.ensureCursorVisible()
    QApplication.processEvents()

    assert dialog.find_text_edit.text() == multiline_pattern
    assert dialog.find_text_edit.textCursor().blockNumber() == 1
    assert dialog.find_text_edit.firstVisibleBlock().blockNumber() == 0
    assert dialog.find_text_edit.viewport().height() >= (
        dialog.find_text_edit.fontMetrics().lineSpacing()
        * 3
    )


def test_regex_input_height_is_capped_for_many_lines(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)

    dialog.show()
    dialog.find_text_edit.setText("\n".join(f"line {index}" for index in range(10)))
    QApplication.processEvents()

    edit = dialog.find_text_edit
    metrics = edit.fontMetrics()
    line_height = max(metrics.height(), metrics.lineSpacing())
    # The field must fit five lines and its real frame/document margins,
    # while remaining shorter than an input that displays a sixth line.
    minimum_height = (
        line_height * edit.MAXIMUM_VISIBLE_LINES
        + edit.document().documentMargin() * 2
        + edit.frameWidth() * 2
    )
    assert minimum_height <= edit.height() < minimum_height + line_height
    assert dialog.find_text_edit.verticalScrollBar().maximum() > 0


def test_regex_inputs_refresh_visible_text_after_selection(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)
    long_pattern = r"</p>[ \t]*\r?\n[ \t]*<p>" * 4

    dialog.find_text_edit.setText(long_pattern)
    dialog.replace_text_edit.setText(long_pattern)
    dialog.find_text_edit.setSelection(0, len(long_pattern))
    dialog.replace_text_edit.setSelection(0, len(long_pattern))
    QApplication.processEvents()

    assert dialog.find_text_edit.text() == long_pattern
    assert dialog.replace_text_edit.text() == long_pattern
    assert dialog.find_text_edit.horizontalScrollBar().value() == 0
    assert dialog.replace_text_edit.horizontalScrollBar().value() == 0


def test_dialog_has_explicit_previous_next_buttons(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "ja")
    dialog = FindReplaceDialog(translator)

    assert dialog.find_previous_button.text() == "↑"
    assert dialog.find_next_button.text() == "↓"
    assert dialog.find_previous_button.toolTip() == "前へ"
    assert dialog.find_next_button.toolTip() == "次へ"
    assert dialog.replace_marked_button.text() == "マーカー部分を全て置換"
    assert dialog.normalise_button.text() == "正規表現書き換え"


def test_normalise_button_emits_selected_operation(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = app
    translator = Translator(Path("resources"), "ja")
    dialog = FindReplaceDialog(translator)
    emitted: list[str] = []
    dialog.normalise_requested.connect(emitted.append)

    def select_operation(*_args: object, **_kwargs: object) -> tuple[str, bool]:
        return "全角アルファベット → 半角アルファベット", True

    monkeypatch.setattr(QInputDialog, "getItem", select_operation)

    dialog.normalise_button.click()

    assert emitted == ["fullwidth_alphabet_to_halfwidth"]


def test_normalise_button_cancel_does_not_emit(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = app
    translator = Translator(Path("resources"), "ja")
    dialog = FindReplaceDialog(translator)
    emitted: list[str] = []
    dialog.normalise_requested.connect(emitted.append)

    def cancel_operation(*_args: object, **_kwargs: object) -> tuple[str, bool]:
        return "", False

    monkeypatch.setattr(QInputDialog, "getItem", cancel_operation)

    dialog.normalise_button.click()

    assert emitted == []


def test_regex_snippet_insert_enables_regex_mode_and_places_cursor(
    app: QApplication,
) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)
    dialog.find_text_edit.setText("prefix suffix")
    dialog.find_text_edit.setSelection(7, 6)

    dialog.insert_find_text("()", cursor_offset=1)

    assert dialog.regular_expression_check_box.isChecked()
    assert dialog.find_text_edit.text() == "prefix ()"
    assert dialog.find_text_edit.cursorPosition() == 8


def test_line_break_shortcuts_insert_into_focused_find_replace_input(
    app: QApplication,
) -> None:
    _ = app
    dialog = FindReplaceDialog(Translator(Path("resources"), "en"))

    dialog.find_text_edit.setFocus()
    dialog.insert_br_action.trigger()
    dialog.replace_text_edit.setFocus()
    dialog.insert_br_br_action.trigger()

    assert dialog.insert_br_action.shortcut().toString() == "F8"
    assert dialog.insert_br_br_action.shortcut().toString() == "F9"
    assert dialog.find_text_edit.text() == "<br>"
    assert dialog.replace_text_edit.text() == "<br><br>"


def test_regex_insert_menu_is_grouped(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)

    regex_menu = dialog.insert_regex_button.menu()
    assert regex_menu is not None
    group_menus: list[QMenu] = []
    for action in regex_menu.actions():
        child_menu = action.menu()
        if isinstance(child_menu, QMenu):
            group_menus.append(child_menu)

    assert [menu.title() for menu in group_menus] == [
        "Characters",
        "Positions",
        "Repetition",
        "Groups",
    ]


def test_regex_lint_can_be_disabled(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)
    dialog.regular_expression_check_box.setChecked(True)
    dialog.find_text_edit.setText("example.com")

    assert dialog.warning_label.text()

    dialog.set_regex_lint_enabled(False)

    assert dialog.warning_label.text() == ""


def test_low_load_mode_suppresses_regex_lint_and_auto_search_signal(
    app: QApplication,
) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)
    emitted: list[str] = []
    dialog.search_parameters_changed.connect(
        lambda search_text, _options: emitted.append(search_text)
    )
    dialog.regular_expression_check_box.setChecked(True)
    dialog.find_text_edit.setText("example.com")

    assert dialog.warning_label.text()
    assert emitted

    emitted.clear()
    dialog.set_reduced_error_check_enabled(True)
    dialog.find_text_edit.setText("example.org")

    assert dialog.warning_label.text() == ""
    assert emitted == []


def test_regex_mode_toggles_find_and_replace_highlighting(app: QApplication) -> None:
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = FindReplaceDialog(translator)

    dialog.regular_expression_check_box.setChecked(True)

    assert dialog.find_text_edit.highlighter.enabled is True
    assert dialog.replace_text_edit.highlighter.enabled is True

    dialog.regular_expression_check_box.setChecked(False)

    assert dialog.find_text_edit.highlighter.enabled is False
    assert dialog.replace_text_edit.highlighter.enabled is False


def test_regex_highlighter_marks_regex_tokens_without_escaped_literals(
    app: QApplication,
) -> None:
    _ = app
    highlighter = RegexInputHighlighter(FindReplaceDialog(Translator(Path("resources"), "en")).find_text_edit.document())
    text = (
        r'<!-- wp:heading \{"level":3\} -->'
        r'<h3 class="wp-block-heading">(.*?)</h3>\s*'
        r'<!-- /wp:heading -->'
    )

    ranges = highlighter._regex_token_ranges(text)
    highlighted_text = " ".join(text[start : start + length] for start, length in ranges)

    assert r"(.*?)" in highlighted_text
    assert r"\s*" in highlighted_text
    assert r"\{" not in highlighted_text
    assert r"\}" not in highlighted_text
