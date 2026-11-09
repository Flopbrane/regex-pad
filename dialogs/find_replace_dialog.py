# pylint: disable=C0301,no-name-in-module
"""Find and Replace Dialog"""
from __future__ import annotations

from typing import cast

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dialogs.regex_input_edit import REGEX_TOKEN_COLOR, RegexInputEdit
from localization.translator import Translator
from normalise import NormaliseOperation, normalise_operations
from search.regex_lint import RegexLint, RegexLintMessage
from search.search_engine import SearchOptions
from unicode_normalize import NORMALIZATION_FORMS, NormalizationForm


class FindReplaceDialog(QDialog):
    """Dialog for finding and replacing text with regex support."""
    find_requested = Signal(str, SearchOptions)
    find_previous_requested = Signal(str, SearchOptions)
    replace_requested = Signal(str, str, SearchOptions)
    replace_all_requested = Signal(str, str, SearchOptions)
    replace_marked_requested = Signal(str, str, SearchOptions)
    preview_requested = Signal(str, str, SearchOptions)
    search_parameters_changed = Signal(str, SearchOptions)
    regex_help_requested = Signal()
    normalise_requested = Signal(str)
    REGEX_INPUT_TEXT_COLOR: QColor = REGEX_TOKEN_COLOR

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.translator: Translator = translator
        self.setModal(False)
        self.regex_lint = RegexLint()
        self.regex_lint_enabled: bool = True
        self.reduced_error_check_enabled: bool = False

        self.find_text_edit = RegexInputEdit(self)
        self.exclusion_text_edit = RegexInputEdit(self)
        self.replace_text_edit = RegexInputEdit(self)
        self.find_text_label = QLabel(self)
        self.replace_text_label = QLabel(self)
        self.exclusion_text_label = QLabel(self)

        self.case_sensitive_check_box = QCheckBox("Case-sensitive", self)
        self.regular_expression_check_box = QCheckBox("Regular expression", self)
        self.whole_word_check_box = QCheckBox("Whole word", self)
        self.selected_only_check_box = QCheckBox("Search only selected text", self)
        self.visible_only_check_box = QCheckBox("Search only visible text", self)
        self.unicode_normalize_separator = QFrame(self)
        self.unicode_normalize_separator.setFrameShape(QFrame.Shape.HLine)
        self.unicode_normalize_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.unicode_normalize_check_box = QCheckBox(
            "Unicode normalization replacement",
            self,
        )
        self.unicode_normalize_form_label = QLabel(self)
        self.unicode_normalize_form_combo_box = QComboBox(self)
        self.unicode_normalize_form_combo_box.addItems(NORMALIZATION_FORMS)
        self.unicode_normalize_form_combo_box.setCurrentText("NFKC")
        self.unicode_normalize_form_help_label = QLabel(self)
        self.unicode_normalize_form_help_label.setWordWrap(True)
        self.append_dot_to_circled_number_check_box = QCheckBox(
            'Append "." after converted circled numbers',
            self,
        )

        self.find_button = QPushButton("Find", self)
        self.find_previous_button = QPushButton("↑", self)
        self.find_next_button = QPushButton("↓", self)
        self.replace_button = QPushButton("Replace", self)
        self.replace_all_button = QPushButton("Replace All", self)
        self.replace_marked_button = QPushButton("Replace Marked", self)
        self.insert_regex_button = QPushButton("Insert Regex", self)
        self.recipe_button = QPushButton("Recipes", self)
        self.normalise_button = QPushButton("Regex Rewrite", self)
        self.preview_button = QPushButton("Preview", self)
        self.regex_help_button = QPushButton("Regex Help", self)
        self.close_button = QPushButton("Close", self)
        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)
        self.warning_label = QLabel(self)
        self.warning_label.setStyleSheet("color: #8a5a00;")
        self.warning_label.setWordWrap(True)
        self.preview_summary_label = QLabel(self)
        self.preview_table = QTableWidget(0, 3, self)
        self.preview_table.setMinimumHeight(180)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._create_layout()
        self._create_regex_insert_menu()
        self._create_recipe_menu()
        self._create_shortcuts()
        self._connect_signals()
        self.apply_language()
        self._update_regex_input_colors()
        self._update_unicode_normalize_controls()

    def set_find_text(self, text: str) -> None:
        """Set the text in the find input field and select all of it."""
        self.find_text_edit.setText(text)
        self.find_text_edit.selectAll()

    def set_error(self, message: str) -> None:
        """Set the error message in the error label."""
        self.error_label.setText(message)

    def clear_error(self) -> None:
        """Clear the error message in the error label."""
        self.error_label.clear()

    def insert_find_text(self, text: str, cursor_offset: int | None = None) -> None:
        """Insert text into the find input field at the current cursor position or selection."""
        insert_position: int = (
            self.find_text_edit.selectionStart()
            if self.find_text_edit.hasSelectedText()
            else self.find_text_edit.cursorPosition()
        )
        self.regular_expression_check_box.setChecked(True)
        self.find_text_edit.insert(text)
        if cursor_offset is not None:
            self.find_text_edit.setCursorPosition(insert_position + cursor_offset)
        self.find_text_edit.setFocus()

    def current_search_options(self) -> SearchOptions:
        """Get the current search options based on the state of the checkboxes."""
        return self._search_options()

    def set_regex_lint_enabled(self, enabled: bool) -> None:
        """Enable or disable regex linting and update the linting state."""
        self.regex_lint_enabled: bool = enabled
        self._update_regex_lint()

    def set_reduced_error_check_enabled(self, enabled: bool) -> None:
        """Enable or disable reduced error checking and update the linting state."""
        self.reduced_error_check_enabled: bool = enabled
        self._update_regex_lint()

    def set_search_recipe(self, search_text: str, replace_text: str) -> None:
        """Set the find and replace text fields to the specified recipe values."""
        self.unicode_normalize_check_box.setChecked(False)
        self.find_text_edit.setText(search_text)
        self.replace_text_edit.setText(replace_text)
        self.regular_expression_check_box.setChecked(True)
        self.find_text_edit.setFocus()
        self.find_text_edit.selectAll()

    def set_preview_rows(
        self,
        rows: list[tuple[int, str, str]],
        summary: str,
    ) -> None:
        """Set the preview table rows and summary label with the provided data."""
        self.preview_summary_label.setText(summary)
        self.preview_table.setRowCount(len(rows))
        for row_index, (line_number, before_text, after_text) in enumerate(rows):
            values = (str(line_number), before_text, after_text)
            for column_index, value in enumerate(values):
                self.preview_table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(value),
                )
        self.preview_table.resizeColumnsToContents()

    def clear_preview_rows(self) -> None:
        """Clear the preview table rows and summary label."""
        self.preview_summary_label.clear()
        self.preview_table.setRowCount(0)

    def apply_language(self) -> None:
        """Apply the current language translations to all UI elements."""
        self.setWindowTitle(self.translator.text("find.title"))
        self.find_text_label.setText(self.translator.text("find.find_text"))
        self.replace_text_label.setText(self.translator.text("find.replace_text"))
        self.exclusion_text_label.setText(self.translator.text("find.exclusion_text"))
        self.exclusion_text_edit.setToolTip(self.translator.text("find.exclusion_hint"))
        self.case_sensitive_check_box.setText(self.translator.text("find.case_sensitive"))
        self.regular_expression_check_box.setText(self.translator.text("find.regex"))
        self.whole_word_check_box.setText(self.translator.text("find.whole_word"))
        self.selected_only_check_box.setText(self.translator.text("find.selected_only"))
        self.visible_only_check_box.setText(self.translator.text("find.visible_only"))
        self.unicode_normalize_check_box.setText(
            self.translator.text("find.unicode_normalize")
        )
        self.unicode_normalize_check_box.setToolTip(
            self.translator.text("find.unicode_normalize_hint")
        )
        self.unicode_normalize_form_label.setText(
            self.translator.text("find.unicode_normalize_form")
        )
        form_help_text = self.translator.text("find.unicode_normalize_form_help")
        self.unicode_normalize_form_help_label.setText(form_help_text)
        self.unicode_normalize_form_help_label.setToolTip(form_help_text)
        self.append_dot_to_circled_number_check_box.setText(
            self.translator.text("find.unicode_normalize_append_dot")
        )
        self.find_button.setText(self.translator.text("find.find"))
        self.find_previous_button.setToolTip(self.translator.text("find.previous"))
        self.find_next_button.setToolTip(self.translator.text("find.next"))
        self.replace_button.setText(self.translator.text("find.replace"))
        self.replace_all_button.setText(self.translator.text("find.replace_all"))
        self.replace_marked_button.setText(
            self.translator.text("find.replace_marked")
        )
        self.insert_regex_button.setText(self.translator.text("find.insert_regex"))
        self.recipe_button.setText(self.translator.text("find.regex_recipes"))
        self.normalise_button.setText(self.translator.text("find.normalise"))
        self.preview_button.setText(self.translator.text("find.preview"))
        self.regex_help_button.setText(self.translator.text("find.regex_help"))
        self.close_button.setText(self.translator.text("find.close"))
        self.preview_table.setHorizontalHeaderLabels(
            [
                self.translator.text("find.preview.line"),
                self.translator.text("find.preview.before"),
                self.translator.text("find.preview.after"),
            ]
        )
        self._create_regex_insert_menu()
        self._create_recipe_menu()
        self._update_unicode_normalize_controls()
        self._update_regex_lint()

    def _create_layout(self) -> None:
        """Create the layout for the dialog, arranging all widgets in a grid and vertical layout."""
        form_layout = QGridLayout()
        find_input_layout = QGridLayout()
        find_input_layout.setContentsMargins(0, 0, 0, 0)
        find_input_layout.addWidget(self.find_text_edit, 0, 0)
        find_input_layout.addWidget(self.find_previous_button, 0, 1)
        find_input_layout.addWidget(self.find_next_button, 0, 2)

        form_layout.addWidget(self.find_text_label, 0, 0)
        form_layout.addLayout(find_input_layout, 0, 1)
        form_layout.addWidget(self.exclusion_text_label, 1, 0)
        form_layout.addWidget(self.exclusion_text_edit, 1, 1)
        form_layout.addWidget(self.replace_text_label, 2, 0)
        form_layout.addWidget(self.replace_text_edit, 2, 1)
        form_layout.addWidget(self.case_sensitive_check_box, 3, 1)
        form_layout.addWidget(self.regular_expression_check_box, 4, 1)
        form_layout.addWidget(self.whole_word_check_box, 5, 1)
        form_layout.addWidget(self.selected_only_check_box, 6, 1)
        form_layout.addWidget(self.visible_only_check_box, 7, 1)
        form_layout.addWidget(self.unicode_normalize_separator, 8, 0, 1, 2)
        form_layout.addWidget(self.unicode_normalize_check_box, 9, 1)
        form_layout.addWidget(self.unicode_normalize_form_label, 10, 0)
        form_layout.addWidget(self.unicode_normalize_form_combo_box, 10, 1)
        form_layout.addWidget(self.unicode_normalize_form_help_label, 11, 1)
        form_layout.addWidget(self.append_dot_to_circled_number_check_box, 12, 1)
        form_layout.setRowStretch(0, 1)
        form_layout.setRowStretch(2, 1)

        button_layout = QGridLayout()
        button_layout.addWidget(self.find_button, 0, 0)
        button_layout.addWidget(self.replace_button, 0, 1)
        button_layout.addWidget(self.replace_all_button, 0, 2)
        button_layout.addWidget(self.replace_marked_button, 0, 3)
        button_layout.addWidget(self.preview_button, 1, 0)
        button_layout.addWidget(self.insert_regex_button, 1, 1)
        button_layout.addWidget(self.recipe_button, 1, 2)
        button_layout.addWidget(self.normalise_button, 1, 3)
        button_layout.addWidget(self.regex_help_button, 2, 0)
        button_layout.addWidget(self.close_button, 2, 2)

        root_layout = QVBoxLayout()
        root_layout.addLayout(form_layout)
        root_layout.addLayout(button_layout)
        root_layout.addWidget(self.warning_label)
        root_layout.addWidget(self.error_label)
        root_layout.addWidget(self.preview_summary_label)
        root_layout.addWidget(self.preview_table)
        root_layout.setStretch(0, 1)
        root_layout.setStretch(4, 2)
        self.setLayout(root_layout)

    def _create_regex_insert_menu(self) -> None:
        """Create the regex insert menu with categorized regex snippets."""
        regex_menu = QMenu(self)
        snippet_groups = [
            (
                "regex.snippet_group.characters",
                [
                    ("regex.snippet.digit", r"\d", None),
                    ("regex.snippet.not_digit", r"\D", None),
                    ("regex.snippet.word", r"\w", None),
                    ("regex.snippet.not_word", r"\W", None),
                    ("regex.snippet.whitespace", r"\s", None),
                    ("regex.snippet.not_whitespace", r"\S", None),
                    ("regex.snippet.any", ".", None),
                    ("regex.snippet.literal_dot", r"\.", None),
                    ("regex.snippet.line_break", r"\n", None),
                    ("regex.snippet.tab", r"\t", None),
                ],
            ),
            (
                "regex.snippet_group.positions",
                [
                    ("regex.snippet.start", "^", None),
                    ("regex.snippet.end", "$", None),
                    ("regex.snippet.word_boundary", r"\b", None),
                ],
            ),
            (
                "regex.snippet_group.repetition",
                [
                    ("regex.snippet.one_or_more", "+", None),
                    ("regex.snippet.zero_or_more", "*", None),
                    ("regex.snippet.optional", "?", None),
                    ("regex.snippet.exact_count", r"{1}", 1),
                    ("regex.snippet.count_range", r"{1,3}", 1),
                ],
            ),
            (
                "regex.snippet_group.groups",
                [
                    ("regex.snippet.capture", r"()", 1),
                    ("regex.snippet.class", r"[]", 1),
                    ("regex.snippet.non_capture", r"(?:)", 3),
                    ("regex.snippet.alternative", "|", None),
                ],
            ),
        ]
        for group_key, snippets in snippet_groups:
            group_menu = regex_menu.addMenu(self.translator.text(group_key))
            assert group_menu is not None
            for label_key, pattern, cursor_offset in snippets:
                self._add_regex_snippet_action(group_menu, label_key, pattern, cursor_offset)
        self.insert_regex_button.setMenu(regex_menu)

    def _add_regex_snippet_action(
        self,
        menu: QMenu,
        label_key: str,
        pattern: str,
        cursor_offset: int | None,
    ) -> None:
        """Add an action to the regex snippet menu that inserts a regex pattern into the find input field."""
        label = self.translator.text(label_key)
        action = QAction(f"{label}    {pattern}", self)
        action.triggered.connect(
            lambda checked=False,
            value=pattern,
            offset=cursor_offset: self.insert_find_text(value, offset)
        )
        menu.addAction(action)

    def _create_recipe_menu(self) -> None:
        """Create the recipe menu with predefined regex find and replace patterns."""
        recipe_menu = QMenu(self)
        recipes: list[tuple[str, str, str]] = [
            ("regex.recipe.collapse_blank_lines", r"\n{3,}", "\n\n"),
            ("regex.recipe.trim_trailing_space", r"[ \t]+$", ""),
            ("regex.recipe.remove_blank_lines", r"^[ \t]*\n", ""),
            ("regex.recipe.paragraph_boundary_to_breaks", r"</p>\r?\n<p>", "<br><br>\n"),
            (
                "regex.recipe.paragraph_boundary_to_breaks_spaces",
                r"</p>[ \t]*\r?\n[ \t]*<p>",
                "<br><br>\n",
            ),
            ("regex.recipe.tabs_to_spaces", r"\t", "    "),
            ("regex.recipe.date_yyyy_mm_dd_to_slash", r"(\d{4})-(\d{2})-(\d{2})", r"\1/\2/\3"),
            ("regex.recipe.numbered_to_bullets", r"^\d+\.\s+", "- "),
        ]
        for label_key, search_text, replace_text in recipes:
            label = self.translator.text(label_key)
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked=False,
                search_value=search_text,
                replace_value=replace_text: self.set_search_recipe(
                    search_value,
                    replace_value,
                )
            )
            recipe_menu.addAction(action)
        self.recipe_button.setMenu(recipe_menu)

    def _create_shortcuts(self) -> None:
        """Create keyboard shortcuts for inserting line breaks into the find or replace input fields."""
        self.insert_br_action = QAction(self)
        self.insert_br_action.setShortcut("F8")
        self.insert_br_action.triggered.connect(
            lambda: self._insert_text_into_focused_input("<br>")
        )
        self.addAction(self.insert_br_action)

        self.insert_br_br_action = QAction(self)
        self.insert_br_br_action.setShortcut("F9")
        self.insert_br_br_action.triggered.connect(
            lambda: self._insert_text_into_focused_input("<br><br>")
        )
        self.addAction(self.insert_br_br_action)

    def _insert_text_into_focused_input(self, text: str) -> None:
        """Insert the specified text into the currently focused input field (find or replace)."""
        focused_widget = self.focusWidget()
        if focused_widget is self.replace_text_edit:
            self.replace_text_edit.insert(text)
            self.replace_text_edit.setFocus()
            return
        if focused_widget is self.exclusion_text_edit:
            self.exclusion_text_edit.insert(text)
            self.exclusion_text_edit.setFocus()
            return
        self.find_text_edit.insert(text)
        self.find_text_edit.setFocus()

    def _connect_signals(self) -> None:
        """Connect signals from buttons and input fields to their respective slots."""
        self.find_button.clicked.connect(self._emit_find_requested)
        self.find_previous_button.clicked.connect(self._emit_find_previous_requested)
        self.find_next_button.clicked.connect(self._emit_find_requested)
        self.find_text_edit.returnPressed.connect(self._emit_find_requested)
        self.replace_button.clicked.connect(self._emit_replace_requested)
        self.replace_all_button.clicked.connect(self._emit_replace_all_requested)
        self.replace_marked_button.clicked.connect(self._emit_replace_marked_requested)
        self.preview_button.clicked.connect(self._emit_preview_requested)
        self.regex_help_button.clicked.connect(self.regex_help_requested.emit)
        self.normalise_button.clicked.connect(self._choose_normalise_operation)
        self.close_button.clicked.connect(self.close)
        self.find_text_edit.textChanged.connect(self._update_regex_lint)
        self.find_text_edit.textChanged.connect(self._emit_search_parameters_changed)
        self.replace_text_edit.textChanged.connect(self._update_regex_lint)
        self.exclusion_text_edit.textChanged.connect(self._update_regex_lint)
        self.exclusion_text_edit.textChanged.connect(self._emit_search_parameters_changed)
        self.exclusion_text_edit.returnPressed.connect(self._emit_find_requested)
        self.regular_expression_check_box.toggled.connect(
            self._handle_search_option_changed
        )
        self.case_sensitive_check_box.toggled.connect(
            self._emit_search_parameters_changed
        )
        self.whole_word_check_box.toggled.connect(self._emit_search_parameters_changed)
        self.selected_only_check_box.toggled.connect(self._emit_search_parameters_changed)
        self.visible_only_check_box.toggled.connect(self._emit_search_parameters_changed)
        self.unicode_normalize_check_box.toggled.connect(
            self._handle_unicode_normalize_changed
        )
        self.unicode_normalize_form_combo_box.currentTextChanged.connect(
            self._emit_search_parameters_changed
        )
        self.append_dot_to_circled_number_check_box.toggled.connect(
            self._emit_search_parameters_changed
        )

    def _search_options(self) -> SearchOptions:
        """Get the current search options based on the state of the checkboxes."""
        return SearchOptions(
            case_sensitive=self.case_sensitive_check_box.isChecked(),
            regular_expression=self.regular_expression_check_box.isChecked(),
            whole_word=self.whole_word_check_box.isChecked(),
            selected_only=self.selected_only_check_box.isChecked(),
            visible_only=self.visible_only_check_box.isChecked(),
            exclusion_text=self.exclusion_text_edit.text(),
            unicode_normalize=self.unicode_normalize_check_box.isChecked(),
            unicode_normalize_form=cast(
                NormalizationForm,
                self.unicode_normalize_form_combo_box.currentText(),
            ),
            append_dot_to_circled_number=(
                self.append_dot_to_circled_number_check_box.isChecked()
            ),
        )

    def _update_regex_lint(self) -> None:
        """Update the regex linting state and display any errors or warnings."""
        if (
            not self.regex_lint_enabled
            or self.reduced_error_check_enabled
            or not self.regular_expression_check_box.isChecked()
        ):
            self.warning_label.clear()
            return

        messages = self.regex_lint.lint(
            self.find_text_edit.text(),
            self.replace_text_edit.text(),
            check_replacement=not self.unicode_normalize_check_box.isChecked(),
        )
        exclusion_text = self.exclusion_text_edit.text()
        if exclusion_text:
            exclusion_messages = self.regex_lint.lint(exclusion_text)
            exclusion_errors = [
                message for message in exclusion_messages if message.severity == "error"
            ]
            if exclusion_errors:
                self.warning_label.setText(
                    self.translator.text("find.exclusion_text") + ": "
                    + self._lint_message_text(exclusion_errors[0])
                )
                return
        errors = [message for message in messages if message.severity == "error"]
        warnings = [
            message for message in messages if message.severity == "warning"
        ]
        if errors:
            self.warning_label.setText(self._lint_message_text(errors[0]))
        elif warnings:
            self.warning_label.setText(self._lint_message_text(warnings[0]))
        else:
            self.warning_label.clear()

    def _update_regex_input_colors(self) -> None:
        """Update the regex highlighting state of the find and replace input fields based on the regex checkbox."""
        regex_enabled = self.regular_expression_check_box.isChecked()
        self.find_text_edit.set_regex_highlighting_enabled(regex_enabled)
        self.replace_text_edit.set_regex_highlighting_enabled(regex_enabled)
        self.exclusion_text_edit.set_regex_highlighting_enabled(regex_enabled)

    def _lint_message_text(self, message: RegexLintMessage) -> str:
        """Get the translated text for a regex lint message."""
        return self.translator.text(message.message_key, **(message.values or {}))

    def _emit_find_requested(self) -> None:
        """Emit the find_requested signal with the current find text and search options."""
        self.find_requested.emit(self.find_text_edit.text(), self._search_options())

    def _emit_find_previous_requested(self) -> None:
        """Emit the find_previous_requested signal with the current find text and search options."""
        self.find_previous_requested.emit(
            self.find_text_edit.text(),
            self._search_options(),
        )

    def _emit_replace_requested(self) -> None:
        """Emit the replace_requested signal with the current find text, replace text, and search options."""
        self.replace_requested.emit(
            self.find_text_edit.text(),
            self.replace_text_edit.text(),
            self._search_options(),
        )

    def _emit_replace_all_requested(self) -> None:
        """Emit the replace_all_requested signal with the current find text, replace text, and search options."""
        self.replace_all_requested.emit(
            self.find_text_edit.text(),
            self.replace_text_edit.text(),
            self._search_options(),
        )

    def _emit_replace_marked_requested(self) -> None:
        """Emit the replace_marked_requested signal with the current find text, replace text, and search options."""
        self.replace_marked_requested.emit(
            self.find_text_edit.text(),
            self.replace_text_edit.text(),
            self._search_options(),
        )

    def _emit_preview_requested(self) -> None:
        """Emit the preview_requested signal with the current find text, replace text, and search options."""
        self.preview_requested.emit(
            self.find_text_edit.text(),
            self.replace_text_edit.text(),
            self._search_options(),
        )

    def _choose_normalise_operation(self) -> None:
        """Show a dialog to choose a normalise operation and emit the normalise_requested signal."""
        operations: tuple[NormaliseOperation, ...] = normalise_operations()
        labels = [self.translator.text(operation.label_key) for operation in operations]
        selected_label, accepted = QInputDialog.getItem(
            self,
            self.translator.text("normalise.title"),
            self.translator.text("normalise.operation"),
            labels,
            0,
            False,
        )
        if not accepted:
            return
        try:
            selected_index = labels.index(selected_label)
        except ValueError:
            return
        self.normalise_requested.emit(operations[selected_index].operation_id)

    def _handle_search_option_changed(self, *_args: object) -> None:
        """Handle changes to the search options, updating regex input colors and linting."""
        self._update_regex_input_colors()
        self._update_regex_lint()
        self._emit_search_parameters_changed()

    def _handle_unicode_normalize_changed(self, *_args: object) -> None:
        """Update controls when the dedicated Unicode replacement route changes."""
        self._update_unicode_normalize_controls()
        self._update_regex_lint()
        self._emit_search_parameters_changed()

    def _update_unicode_normalize_controls(self) -> None:
        """Enable only controls that participate in the active replacement route."""
        enabled = self.unicode_normalize_check_box.isChecked()
        self.unicode_normalize_form_label.setEnabled(enabled)
        self.unicode_normalize_form_combo_box.setEnabled(enabled)
        self.unicode_normalize_form_help_label.setEnabled(enabled)
        self.append_dot_to_circled_number_check_box.setEnabled(enabled)
        self.replace_text_label.setEnabled(not enabled)
        self.replace_text_edit.setEnabled(not enabled)
        self.replace_text_edit.setToolTip(
            self.translator.text(
                "find.unicode_normalize_replace_disabled"
                if enabled
                else "find.replace_text_hint"
            )
        )

    def _emit_search_parameters_changed(self, *_args: object) -> None:
        """Emit the search_parameters_changed signal with the current find text and search options."""
        if self.reduced_error_check_enabled:
            return
        self.clear_preview_rows()
        self.search_parameters_changed.emit(
            self.find_text_edit.text(),
            self._search_options(),
        )
