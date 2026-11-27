# pylint: disable=C0301,no-name-in-module
"""検索・置換ダイアログを提供する。"""
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
    """テキスト検索と置換を行い、正規表現にも対応するダイアログ。"""
    find_requested = Signal(str, SearchOptions)
    find_previous_requested = Signal(str, SearchOptions)
    replace_requested = Signal(str, str, SearchOptions)
    replace_all_requested = Signal(str, str, SearchOptions)
    replace_marked_requested = Signal(str, str, SearchOptions)
    preview_requested = Signal(str, str, SearchOptions)
    preview_line_requested = Signal(int)
    preview_cleared = Signal()
    search_parameters_changed = Signal(str, SearchOptions)
    selection_scope_reset_requested = Signal()
    regex_help_requested = Signal()
    normalise_requested = Signal(str)
    preset_requested = Signal(str, str, SearchOptions)
    REGEX_INPUT_TEXT_COLOR: QColor = REGEX_TOKEN_COLOR

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        """検索・置換の入力欄、検索条件、操作ボタンを初期化する。"""
        super().__init__(parent)
        self.translator: Translator = translator
        self.setModal(False)
        self.regex_lint = RegexLint()
        self.regex_lint_enabled: bool = True
        self.reduced_error_check_enabled: bool = False
        self.target_file_name = ""

        self.target_file_label = QLabel(self)
        self.find_text_edit = RegexInputEdit(self)
        self.exclusion_text_edit = RegexInputEdit(self)
        self.replace_text_edit = RegexInputEdit(self)
        self.find_text_label = QLabel(self)
        self.replace_text_label = QLabel(self)
        self.exclusion_text_label = QLabel(self)

        self.case_sensitive_check_box = QCheckBox("Case-sensitive", self)
        self.regular_expression_check_box = QCheckBox("Regular expression", self)
        self.whole_word_check_box = QCheckBox("Whole word", self)
        self.selected_only_check_box = QCheckBox("Search/replace only selected text", self)
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
        self.clear_text_button = QPushButton("Clear", self)
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
        self.preset_separator = QFrame(self)
        self.preset_separator.setFrameShape(QFrame.Shape.HLine)
        self.preset_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.preset_button = QPushButton(self)
        self.reset_selection_scope_button = QPushButton(
            "Reset selection reference",
            self,
        )
        self.reset_selection_scope_button.setEnabled(False)
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
        """検索欄に文字列を設定し、その全文を選択する。"""
        self.find_text_edit.setText(text)
        self.find_text_edit.selectAll()

    def set_target_file_name(self, name: str) -> None:
        """ダイアログを開いた時点の対象ファイルを表示する。"""
        self.target_file_name = name
        title = self.translator.text("find.title")
        self.setWindowTitle(f"{title} — {name}" if name else title)
        self.target_file_label.setText(
            self.translator.text("find.target_file", name=name) if name else ""
        )
        self.target_file_label.setVisible(bool(name))

    def set_error(self, message: str) -> None:
        """エラー欄に指定のメッセージを表示する。"""
        self.error_label.setText(message)

    def clear_error(self) -> None:
        """エラー欄のメッセージを消す。"""
        self.error_label.clear()

    def insert_find_text(self, text: str, cursor_offset: int | None = None) -> None:
        """検索欄のカーソル位置に挿入し、選択中なら選択文字列を置き換える。"""
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
        """チェックボックスの状態から現在の検索条件を取得する。"""
        return self._search_options()

    def set_regex_lint_enabled(self, enabled: bool) -> None:
        """正規表現の検査を切り替え、診断表示を更新する。"""
        self.regex_lint_enabled: bool = enabled
        self._update_regex_lint()

    def set_reduced_error_check_enabled(self, enabled: bool) -> None:
        """低負荷モードを切り替え、検査の状態を更新する。"""
        self.reduced_error_check_enabled: bool = enabled
        self._update_regex_lint()

    def set_search_recipe(self, search_text: str, replace_text: str) -> None:
        """指定されたレシピの検索文字列と置換文字列を入力欄に設定する。"""
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
        """受け取ったデータをプレビューの行と要約欄に表示する。"""
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
        """プレビューの行と要約欄を消す。"""
        self.preview_summary_label.clear()
        self.preview_table.setRowCount(0)
        self.preview_cleared.emit()

    def clear_text_fields(self) -> None:
        """検索、除外、置換の入力欄を空にする。"""
        self.find_text_edit.clear()
        self.exclusion_text_edit.clear()
        self.replace_text_edit.clear()
        self.clear_error()
        self.clear_preview_rows()
        self.find_text_edit.setFocus()

    def apply_language(self) -> None:
        """現在の言語の翻訳を画面全体に適用する。"""
        self.set_target_file_name(self.target_file_name)
        self.find_text_label.setText(self.translator.text("find.find_text"))
        self.replace_text_label.setText(self.translator.text("find.replace_text"))
        self.exclusion_text_label.setText(self.translator.text("find.exclusion_text"))
        self.exclusion_text_edit.setToolTip(self.translator.text("find.exclusion_hint"))
        self.case_sensitive_check_box.setText(self.translator.text("find.case_sensitive"))
        self.regular_expression_check_box.setText(self.translator.text("find.regex"))
        self.whole_word_check_box.setText(self.translator.text("find.whole_word"))
        self.selected_only_check_box.setText(self.translator.text("find.selected_only"))
        self.reset_selection_scope_button.setText(
            self.translator.text("find.reset_selection_scope")
        )
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
        self.clear_text_button.setText(self.translator.text("find.clear_text_fields"))
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
        self.preset_button.setText(self.translator.text("preset.capture"))
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
        """グリッドと縦方向のレイアウトを使い、ダイアログの部品を配置する。"""
        form_layout = QGridLayout()
        find_input_layout = QGridLayout()
        find_input_layout.setContentsMargins(0, 0, 0, 0)
        find_input_layout.addWidget(self.find_text_edit, 0, 0)
        find_input_layout.addWidget(self.find_previous_button, 0, 1)
        find_input_layout.addWidget(self.find_next_button, 0, 2)
        find_input_layout.addWidget(self.clear_text_button, 0, 3)

        selected_scope_layout = QGridLayout()
        selected_scope_layout.setContentsMargins(0, 0, 0, 0)
        selected_scope_layout.addWidget(self.selected_only_check_box, 0, 0)
        selected_scope_layout.addWidget(self.reset_selection_scope_button, 0, 1)

        form_layout.addWidget(self.find_text_label, 0, 0)
        form_layout.addLayout(find_input_layout, 0, 1)
        form_layout.addWidget(self.exclusion_text_label, 1, 0)
        form_layout.addWidget(self.exclusion_text_edit, 1, 1)
        form_layout.addWidget(self.replace_text_label, 2, 0)
        form_layout.addWidget(self.replace_text_edit, 2, 1)
        form_layout.addWidget(self.case_sensitive_check_box, 3, 1)
        form_layout.addWidget(self.regular_expression_check_box, 4, 1)
        form_layout.addWidget(self.whole_word_check_box, 5, 1)
        form_layout.addLayout(selected_scope_layout, 6, 1)
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
        root_layout.addWidget(self.target_file_label)
        root_layout.addLayout(form_layout)
        root_layout.addLayout(button_layout)
        root_layout.addWidget(self.preset_separator)
        root_layout.addWidget(self.preset_button)
        root_layout.addWidget(self.warning_label)
        root_layout.addWidget(self.error_label)
        root_layout.addWidget(self.preview_summary_label)
        root_layout.addWidget(self.preview_table)
        root_layout.setStretch(1, 1)
        root_layout.setStretch(9, 2)
        self.setLayout(root_layout)

    def _create_regex_insert_menu(self) -> None:
        """正規表現の定型パターンを分類した挿入メニューを作る。"""
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
        """検索欄へ正規表現パターンを挿入する項目をメニューに追加する。"""
        label = self.translator.text(label_key)
        action = QAction(f"{label}    {pattern}", self)
        action.triggered.connect(
            lambda checked=False,
            value=pattern,
            offset=cursor_offset: self.insert_find_text(value, offset)
        )
        menu.addAction(action)

    def _create_recipe_menu(self) -> None:
        """定義済みの正規表現検索・置換パターンのメニューを作る。"""
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
        """検索欄や置換欄に改行を挿入するショートカットを作る。"""
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
        """指定文字列をフォーカス中の検索欄または置換欄に挿入する。"""
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
        """ボタンや入力欄のシグナルを対応する処理に接続する。"""
        self.find_button.clicked.connect(self._emit_find_requested)
        self.clear_text_button.clicked.connect(self.clear_text_fields)
        self.find_previous_button.clicked.connect(self._emit_find_previous_requested)
        self.find_next_button.clicked.connect(self._emit_find_requested)
        self.find_text_edit.returnPressed.connect(self._emit_find_requested)
        self.replace_button.clicked.connect(self._emit_replace_requested)
        self.replace_all_button.clicked.connect(self._emit_replace_all_requested)
        self.replace_marked_button.clicked.connect(self._emit_replace_marked_requested)
        self.preview_button.clicked.connect(self._emit_preview_requested)
        self.preview_table.cellClicked.connect(self._emit_preview_line_requested)
        self.regex_help_button.clicked.connect(self.regex_help_requested.emit)
        self.normalise_button.clicked.connect(self._choose_normalise_operation)
        self.close_button.clicked.connect(self.close)
        self.preset_button.clicked.connect(
            lambda: self.preset_requested.emit(
                self.find_text_edit.text(),
                self.replace_text_edit.text(),
                self._search_options(),
            )
        )
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
        self.selected_only_check_box.toggled.connect(
            self.reset_selection_scope_button.setEnabled
        )
        self.reset_selection_scope_button.clicked.connect(
            self.selection_scope_reset_requested.emit
        )
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

    def _emit_preview_line_requested(self, row: int, _column: int) -> None:
        """クリックしたプレビュー行の元の行へ移動するよう通知する。"""
        line_item = self.preview_table.item(row, 0)
        if line_item is not None:
            self.preview_line_requested.emit(int(line_item.text()))

    def _search_options(self) -> SearchOptions:
        """チェックボックスの状態から検索条件を取得する。"""
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
        """正規表現の検査状態を更新し、エラーや警告を表示する。"""
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
        """正規表現の設定に応じて、検索欄と置換欄の色付けを更新する。"""
        regex_enabled = self.regular_expression_check_box.isChecked()
        self.find_text_edit.set_regex_highlighting_enabled(regex_enabled)
        self.replace_text_edit.set_regex_highlighting_enabled(regex_enabled)
        self.exclusion_text_edit.set_regex_highlighting_enabled(regex_enabled)

    def _lint_message_text(self, message: RegexLintMessage) -> str:
        """正規表現の診断メッセージを現在の言語で取得する。"""
        return self.translator.text(message.message_key, **(message.values or {}))

    def _emit_find_requested(self) -> None:
        """現在の検索文字列と検索条件で次の一致を探すよう通知する。"""
        self.find_requested.emit(self.find_text_edit.text(), self._search_options())

    def _emit_find_previous_requested(self) -> None:
        """現在の検索文字列と検索条件で前の一致を探すよう通知する。"""
        self.find_previous_requested.emit(
            self.find_text_edit.text(),
            self._search_options(),
        )

    def _emit_replace_requested(self) -> None:
        """現在の検索・置換文字列と検索条件で1件の置換を要求する。"""
        self.replace_requested.emit(
            self.find_text_edit.text(),
            self.replace_text_edit.text(),
            self._search_options(),
        )

    def _emit_replace_all_requested(self) -> None:
        """現在の検索・置換文字列と検索条件で全件置換を要求する。"""
        self.replace_all_requested.emit(
            self.find_text_edit.text(),
            self.replace_text_edit.text(),
            self._search_options(),
        )

    def _emit_replace_marked_requested(self) -> None:
        """現在の検索・置換文字列と検索条件でマーカーのある箇所の置換を要求する。"""
        self.replace_marked_requested.emit(
            self.find_text_edit.text(),
            self.replace_text_edit.text(),
            self._search_options(),
        )

    def _emit_preview_requested(self) -> None:
        """現在の検索・置換文字列と検索条件でプレビューを要求する。"""
        self.preview_requested.emit(
            self.find_text_edit.text(),
            self.replace_text_edit.text(),
            self._search_options(),
        )

    def _choose_normalise_operation(self) -> None:
        """正規化操作を選ぶ画面を表示し、選んだ操作を通知する。"""
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
        """検索条件の変更に合わせて、入力欄の色付けと診断を更新する。"""
        self._update_regex_input_colors()
        self._update_regex_lint()
        self._emit_search_parameters_changed()

    def _handle_unicode_normalize_changed(self, *_args: object) -> None:
        """Unicode正規化置換の切り替えに合わせて、各入力欄の状態を更新する。"""
        self._update_unicode_normalize_controls()
        self._update_regex_lint()
        self._emit_search_parameters_changed()

    def _update_unicode_normalize_controls(self) -> None:
        """現在選ばれている置換方式で使う入力欄だけを有効にする。"""
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
        """現在の検索文字列と検索条件が変わったことを通知する。"""
        self.clear_preview_rows()
        if self.reduced_error_check_enabled:
            return
        self.search_parameters_changed.emit(
            self.find_text_edit.text(),
            self._search_options(),
        )
