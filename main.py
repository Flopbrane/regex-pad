# pylint: disable=C0302,C0301,C0411,C0413,C0116
# ruff: noqa:E402,RUF100
"""Main window class for the Regex Pad application."""
#########################
# Author: F.Kurokawa
# Description:
# Main window class for the Regex Pad application.
#########################

from __future__ import annotations

import os
import re
import sys
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from html import escape, unescape
from pathlib import Path
from re import error as RegexError

from portable_runtime import app_base_dir, bundled_base_dir, configure_portable_runtime

configure_portable_runtime()

# PySide6 exposes Qt modules dynamically; Pylint may report false no-name-in-module.
from PySide6.QtCore import QPoint, Qt, QTimer  # pylint: disable=no-name-in-module
from PySide6.QtGui import (  # pylint: disable=no-name-in-module
    QAction,
    QActionGroup,
    QCloseEvent,
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QPixmap,
    QTextCursor,
)
from PySide6.QtWidgets import (  # pylint: disable=no-name-in-module
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import default_config_path, migrate_legacy_settings_if_needed
from dialogs.find_replace_dialog import FindReplaceDialog
from dialogs.grammar_check_dialog import GrammarCheckDialog
from dialogs.options_dialog import OptionsDialog
from dialogs.regex_help_dialog import RegexHelpDialog
from dialogs.schema_reference_dialog import SchemaReferenceDialog
from dialogs.tag_insert_dialog import TagInsertDialog
from dialogs.user_help_dialog import UserHelpDialog
from editor.editor_tab import EditorTab
from editor.paragraph_insert_rules import load_paragraph_insert_rule_book
from editor.paragraph_splitter import (
    ParagraphBlock,
    ParagraphReplacement,
    ParagraphSplitError,
    find_current_paragraph_block,
    split_paragraph_insert_spacer,
    wrap_selection_as_code_block,
    wrap_selection_as_decorated_block,
)
from editor.rectangular_selection import (
    rectangular_selection_from_text_positions,
    rectangular_text,
)
from editor.tag_insert import (
    WORDPRESS_GROUP_LABEL_KEY,
    TagSnippet,
    TagSnippetGroup,
    ordered_tag_snippet_groups,
    tag_snippet_category_key,
    tag_snippet_groups,
    wordpress_mode_label_keys,
    wordpress_snippets_for_mode,
)
from editor.text_editor import TextEditor
from editor.wordpress_markdown_converter import (
    WordPressMarkdownConversionError,
    convert_complex_markdown_blocks_to_wordpress_html,
    convert_list_to_wordpress_frame_html,
    convert_markdown_lists_to_wordpress_html,
    convert_markdown_tables_to_wordpress_html,
)
from fileio.file_backup_manager import FileBackupManager
from fileio.file_manager import FileManager
from fileio.grammar_lint_result_store import (
    GrammarLintResult,
    GrammarLintResultStore,
)
from fileio.unsaved_backup_manager import (
    UnsavedBackup,
    UnsavedBackupManager,
    UnsavedBackupSession,
)
from localization.translator import Translator
from normalise import apply_normalise_operation
from preview.wordpress_preview import WordPressPreview
from preview.wordpress_runtime import default_runtime_root
from search.css_lint import CssLintIssue, lint_stylesheet
from search.html_typo_lint import HtmlTypoLintMessage, lint_html_typos
from search.search_engine import SearchEngine, SearchMatch, SearchOptions
from settings.color_presets import ColorPreset, load_color_preset_catalog
from settings.settings_manager import EditorSettings, SettingsManager

GrammarLintMessage = HtmlTypoLintMessage | CssLintIssue
GRAMMAR_SEVERITY_ORDER = {
    "error": 0,
    "warning": 1,
    "info": 2,
}

ENCODING_OPTIONS: dict[str, str] = {
    "UTF-8": "utf-8",
    "UTF-8 with BOM": "utf-8-sig",
    "CP932 / Shift_JIS": "cp932",
    "Shift_JIS": "shift_jis",
    "EUC-JP": "euc_jp",
    "UTF-16": "utf-16",
    "UTF-16 LE": "utf-16-le",
    "UTF-16 BE": "utf-16-be",
}
SEARCH_HIGHLIGHT_DELAY_MS = 250
MAX_AUTO_SEARCH_HIGHLIGHTS = 2000
DEFAULT_AUTO_BACKUP_INTERVAL_MINUTES = 3
FRAME_BLOCK_LABEL_KEYS = {
    "tag.wordpress.custom_frame_block",
    "tag.wordpress.notice_frame_block",
    "tag.wordpress.info_frame_block",
    "tag.wordpress.important_frame_block",
}
DEFAULT_FRAME_OUTER_SPACING = "1.5em 0 2em 0"
DEFAULT_LIST_FRAME_STYLE = (
    "display: inline-block; border: 2px solid #f0b84a; "
    "background-color: #fffaf0; color: #333333; padding: 14px 16px; "
    "border-radius: 8px;"
)
FRAME_ALIGNMENT_VALUES = {"left", "center", "right"}
FRAME_DISPLAY_STYLES = {
    "block": "display: block; width: 100%; box-sizing: border-box;",
    "grid": "display: grid; width: 100%; box-sizing: border-box;",
    "inline-block": "display: inline-block; max-width: 100%;",
    "inline-grid": "display: inline-grid; max-width: 100%;",
}
FRAME_STYLE_PREFIXES_REPLACED_BY_SETTINGS = (
    "display:",
    "margin:",
    "width:",
    "max-width:",
    "box-sizing:",
    "text-align:",
    "background-color:",
    "color:",
)
CSS_PARAMETER_INSERT_ACTIONS: tuple[tuple[str, str, str, int], ...] = (
    ("style_attribute", "action.css_insert_style_attribute", 'style=""', len('style="')),
    ("color", "action.css_insert_color", "color: ;", len("color: ")),
    (
        "background_color",
        "action.css_insert_background_color",
        "background-color: ;",
        len("background-color: "),
    ),
    ("font_size", "action.css_insert_font_size", "font-size: ;", len("font-size: ")),
    (
        "font_weight",
        "action.css_insert_font_weight",
        "font-weight: bold;",
        len("font-weight: "),
    ),
    ("text_align", "action.css_insert_text_align", "text-align: ;", len("text-align: ")),
    ("margin", "action.css_insert_margin", "margin: ;", len("margin: ")),
    ("padding", "action.css_insert_padding", "padding: ;", len("padding: ")),
    ("border", "action.css_insert_border", "border: 1px solid #999;", len("border: ")),
    (
        "border_radius",
        "action.css_insert_border_radius",
        "border-radius: ;",
        len("border-radius: "),
    ),
    (
        "display_inline_block",
        "action.css_insert_display_inline_block",
        "display: inline-block;",
        len("display: "),
    ),
)

BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "assets" / "icons" / "regex_pad_icon.png"

def _split_style_parts(style_text: str) -> list[str]:
    return [part.strip() for part in style_text.split(";") if part.strip()]


class MainWindow(QMainWindow):
    """Main window class for the Regex Pad application."""
    def __init__(
        self,
        settings_path: Path | None = None,
        unsaved_backup_path: Path | None = None,
        restore_unsaved_backup: bool = True,
        window_id: str | None = None,
    ) -> None:
        super().__init__()
        self.window_id: str = window_id or str(uuid.uuid4())
        self.setObjectName(f"main-window-{self.window_id}")
        self.resources_path: Path = bundled_base_dir() / "resources"
        config_path = settings_path or default_config_path()
        migrate_legacy_settings_if_needed(config_path)
        self.settings_manager = SettingsManager(config_path)
        self.unsaved_backup_enabled = (
            unsaved_backup_path is not None
            or os.environ.get("QT_QPA_PLATFORM") != "offscreen"
        )
        self.unsaved_backup_manager = UnsavedBackupManager(
            unsaved_backup_path or self._unsaved_backup_path()
        )
        self.grammar_lint_result_store = GrammarLintResultStore(
            Path(tempfile.gettempdir()) / "regex_pad" / "lint_results"
        )
        settings: EditorSettings = self.settings_manager.load()
        self.translator = Translator(self.resources_path, settings.language_code)
        self.color_presets = load_color_preset_catalog()
        self.file_manager = FileManager()
        self.file_backup_manager = FileBackupManager(
            self._file_backup_folder_for_folder(settings.backup_folder)
        )
        self.search_engine = SearchEngine()
        self.search_highlight_timer = QTimer(self)
        self.search_highlight_timer.setSingleShot(True)
        self.search_highlight_timer.setInterval(SEARCH_HIGHLIGHT_DELAY_MS)
        self.search_highlight_timer.timeout.connect(self._run_pending_search_highlight)
        self.pending_search_highlight: tuple[str, SearchOptions] | None = None
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self._save_unsaved_backup_snapshot)
        self.current_save_file_path: Path | None = None
        self.default_encoding = settings.default_encoding
        self.current_encoding = settings.default_encoding
        self.newline_code = settings.newline_code
        self.find_replace_dialog: FindReplaceDialog | None = None
        self.grammar_check_dialog: GrammarCheckDialog | None = None
        self.regex_help_dialog: RegexHelpDialog | None = None
        self.tag_insert_dialog: TagInsertDialog | None = None
        self.user_help_dialog: UserHelpDialog | None = None
        self.schema_reference_dialog: SchemaReferenceDialog | None = None
        self.options_dialog: OptionsDialog | None = None
        self.wordpress_preview: WordPressPreview | None = None
        self.wordpress_theme_preview: WordPressPreview | None = None
        self.wordpress_preview_snapshot: tuple[TextEditor, str] | None = None
        self.wordpress_theme_preview_snapshot: tuple[TextEditor, str] | None = None
        self.wordpress_warmup_timer = QTimer(self)
        self.wordpress_warmup_timer.setSingleShot(True)
        self.wordpress_warmup_timer.setInterval(10000)
        self.wordpress_warmup_timer.timeout.connect(self._warm_wordpress_preview)
        self.search_scope: tuple[int, int] | None = None
        self.wordpress_mode_label_key = settings.wordpress_mode_label_key
        self.hover_hints_enabled = settings.hover_hints_enabled
        self.user_dictionary_folder = settings.user_dictionary_folder
        self.dictionary_check_enabled = settings.dictionary_check_enabled
        self.backup_folder = settings.backup_folder
        self.backup_retention_count = settings.backup_retention_count
        self.backup_retention_days = settings.backup_retention_days
        self.auto_backup_interval_minutes = settings.auto_backup_interval_minutes
        self._set_auto_save_timer_interval(self.auto_backup_interval_minutes)
        self.font_family = settings.font_family
        self.font_size = settings.font_size
        self.tab_width = settings.tab_width
        self.editor_theme = settings.editor_theme
        self.editor_background_color = settings.editor_background_color
        self.editor_text_color = settings.editor_text_color
        self.html_tag_color = settings.html_tag_color
        self.wordpress_core_block_color = settings.wordpress_core_block_color
        self.startup_restore_enabled = settings.startup_restore_enabled
        self.search_marker_color = settings.search_marker_color
        self.current_match_marker_color = settings.current_match_marker_color
        self.visible_space_marker_color = settings.visible_space_marker_color
        self.visible_tab_marker_color = settings.visible_tab_marker_color
        self.visible_newline_marker_color = settings.visible_newline_marker_color
        self.regex_lint_enabled = settings.regex_lint_enabled
        self.html_typo_lint_enabled = settings.html_typo_lint_enabled
        self.reduced_error_check_enabled = settings.reduced_error_check_enabled
        self.frame_alignment = settings.frame_alignment
        self.frame_display = settings.frame_display
        self.frame_outer_spacing = settings.frame_outer_spacing
        self.frame_background_color = settings.frame_background_color
        self.frame_text_color = settings.frame_text_color
        self.visible_spaces_enabled = settings.visible_spaces_enabled
        self.visible_tabs_enabled = settings.visible_tabs_enabled
        self.visible_newlines_enabled = settings.visible_newlines_enabled
        self.fixed_column_wrap_enabled = settings.fixed_column_wrap_enabled
        self.fixed_column_wrap_column = settings.fixed_column_wrap_column
        self.tab_file_paths: dict[TextEditor, Path | None] = {}
        self.tab_encodings: dict[TextEditor, str] = {}
        self.tab_grammar_result_paths: dict[TextEditor, Path] = {}
        self.tab_windows: list[MainWindow] = []
        self.child_windows: dict[str, MainWindow] = {}
        self.restoring_unsaved_backup = True
        self.editor: TextEditor

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.currentChanged.connect(self._handle_current_tab_changed)
        self.tab_widget.tabBar().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.tab_widget.tabBar().customContextMenuRequested.connect(
            self._show_tab_context_menu
        )
        central_widget = QWidget(self)
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.tab_widget)
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

        self.resize(900, 650)
        self._create_actions()
        self._create_menus()
        self._create_status_bar()
        self.editor = self._create_editor_tab()
        self._restore_settings(settings)
        self._apply_language()

        self._update_status_bar()
        self._update_window_title()
        self.restoring_unsaved_backup = False
        if restore_unsaved_backup and self.startup_restore_enabled:
            self._restore_unsaved_backup_if_available()
        if self.unsaved_backup_enabled:
            self.auto_save_timer.start()
        # Normal pytest/offscreen runs must not start an optional WordPress runtime.
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            self.wordpress_warmup_timer.start()
        self._update_wordpress_status_label()

    def closeEvent(self, event: QCloseEvent) -> None:  # pylint: disable=invalid-name
        """Handle the close event for the main window."""
        for tab_index in range(self.tab_widget.count()):
            editor: TextEditor | None = self._editor_at(tab_index)
            if editor is None:
                continue
            self.tab_widget.setCurrentIndex(tab_index)
            if not self._confirm_save_or_discard_editor(editor):
                event.ignore()
                return
        self._save_settings()
        self._clear_grammar_lint_results_on_window_close()
        self.stop_wordpress_preview()
        if getattr(sys, "frozen", False):
            from cleanup_inventory import record_inventory_safely

            record_inventory_safely(app_base_dir(), bundled_base_dir())
        event.accept()

    def _create_actions(self) -> None:
        """Create actions for the main window."""
        self.new_action = QAction("&New", self)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self.new_file)

        self.open_action = QAction("&Open...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_file)

        self.open_with_encoding_menu = QMenu(self)
        self.open_encoding_actions: dict[str, QAction] = {}
        for label, encoding in ENCODING_OPTIONS.items():
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked=False, value=encoding: self.open_file(value)
            )
            self.open_encoding_actions[encoding] = action
            self.open_with_encoding_menu.addAction(action)

        self.reload_action = QAction(self)
        self.reload_action.triggered.connect(self.reload_file)

        self.reload_with_encoding_menu = QMenu(self)
        self.reload_encoding_actions: dict[str, QAction] = {}
        for label, encoding in ENCODING_OPTIONS.items():
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked=False, value=encoding: self.reload_file(value)
            )
            self.reload_encoding_actions[encoding] = action
            self.reload_with_encoding_menu.addAction(action)

        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_file)

        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self.save_file_as)

        self.restore_file_backup_action = QAction(self)
        self.restore_file_backup_action.triggered.connect(self.restore_file_backup)

        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut("Alt+F4")
        self.exit_action.triggered.connect(self.close)

        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self._undo_current_editor)

        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcuts(
            [QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")]
        )
        self.redo_action.triggered.connect(self._redo_current_editor)

        self.select_all_action = QAction("Select &All", self)
        self.select_all_action.setShortcut("Ctrl+A")
        self.select_all_action.triggered.connect(self._select_all_current_editor)

        self.copy_rectangular_selection_action = QAction(self)
        self.copy_rectangular_selection_action.setShortcut("Ctrl+Alt+C")
        self.copy_rectangular_selection_action.triggered.connect(
            self.copy_rectangular_selection
        )

        self.insert_br_action = QAction(self)
        self.insert_br_action.setShortcut("F8")
        self.insert_br_action.triggered.connect(lambda: self.insert_text_at_cursor("<br>"))

        self.insert_br_br_action = QAction(self)
        self.insert_br_br_action.setShortcut("F9")
        self.insert_br_br_action.triggered.connect(
            lambda: self.insert_text_at_cursor("<br><br>")
        )

        self.inline_strong_action = QAction(self)
        self.inline_strong_action.setShortcut("Ctrl+B")
        self.inline_strong_action.triggered.connect(
            lambda: self.wrap_selection_with_inline_html("<strong>", "</strong>")
        )

        self.inline_underline_action = QAction(self)
        self.inline_underline_action.setShortcut("Ctrl+U")
        self.inline_underline_action.triggered.connect(
            lambda: self.wrap_selection_with_inline_html("<u>", "</u>")
        )

        self.inline_color_actions: dict[str, QAction] = {}
        for preset in self.color_presets.text_colors:
            action = QAction(self)
            action.setIcon(self._background_color_swatch_icon(preset.value))
            action.setShortcuts(
                [QKeySequence(shortcut) for shortcut in preset.shortcuts]
            )
            action.triggered.connect(
                lambda checked=False, value=preset.value: self.wrap_selection_with_inline_html(
                    f'<span style="color: {value}">',
                    "</span>",
                )
            )
            self.inline_color_actions[preset.identifier] = action
        self.inline_red_span_action = self.inline_color_actions.get(
            "red",
            next(iter(self.inline_color_actions.values())),
        )

        self.html_escape_action = QAction(self)
        self.html_escape_action.triggered.connect(self.escape_selected_html)

        self.html_unescape_action = QAction(self)
        self.html_unescape_action.triggered.connect(self.unescape_selected_html)

        self.wordpress_code_block_action = QAction(self)
        self.wordpress_code_block_action.triggered.connect(
            self.wrap_selected_as_wordpress_code_block
        )

        self.wordpress_complex_blocks_action = QAction(self)
        self.wordpress_complex_blocks_action.triggered.connect(
            self.convert_selected_markdown_blocks_to_wordpress_blocks
        )

        self.wordpress_table_transform_action = QAction(self)
        self.wordpress_table_transform_action.triggered.connect(
            self.convert_selected_markdown_tables_to_wordpress_tables
        )

        self.wordpress_list_transform_action = QAction(self)
        self.wordpress_list_transform_action.triggered.connect(
            self.convert_selected_markdown_lists_to_wordpress_lists
        )

        self.wordpress_list_frame_transform_action = QAction(self)
        self.wordpress_list_frame_transform_action.triggered.connect(
            self.convert_selected_list_to_wordpress_frame
        )

        self.css_parameter_actions: dict[str, QAction] = {}
        for action_id, _text_key, insert_text, cursor_offset in CSS_PARAMETER_INSERT_ACTIONS:
            action = QAction(self)
            if action_id == "style_attribute":
                action.triggered.connect(self.insert_style_attribute_at_cursor)
            elif action_id == "color":
                action.triggered.connect(self.insert_text_color_at_cursor)
            elif action_id == "background_color":
                action.triggered.connect(self.insert_background_color_at_cursor)
            else:
                action.triggered.connect(
                    lambda checked=False,
                    text=insert_text,
                    offset=cursor_offset: self.insert_css_declaration_at_cursor(
                        text,
                        offset,
                    ),
                )
            self.css_parameter_actions[action_id] = action
        self.background_color_preset_menu: QMenu | None = None
        self.text_color_preset_menu: QMenu | None = None

        self.paragraph_split_spacer_action = QAction(self)
        self.paragraph_split_spacer_action.triggered.connect(
            self.insert_paragraph_split_spacer
        )

        self.paragraph_split_html_action = QAction(self)
        self.paragraph_split_html_action.triggered.connect(
            self.insert_paragraph_split_html
        )

        self.paragraph_split_decorated_action = QAction(self)
        self.paragraph_split_decorated_action.triggered.connect(
            self.wrap_paragraph_split_decorated_block
        )

        self.insert_tag_menu = QMenu(self)
        self.insert_tag_picker_action = QAction(self)
        self.insert_tag_picker_action.setShortcut("Ctrl+Shift+T")
        self.insert_tag_picker_action.triggered.connect(self.show_tag_insert_dialog)

        self.find_action = QAction(self)
        self.find_action.setShortcut("Ctrl+F")
        self.find_action.triggered.connect(self.show_find_replace_dialog)

        self.grammar_check_action = QAction(self)
        self.grammar_check_action.setShortcut("F7")
        self.grammar_check_action.triggered.connect(self.run_grammar_check)

        self.wordpress_preview_action = QAction(self)
        self.wordpress_preview_action.setShortcut("Ctrl+Alt+P")
        self.wordpress_preview_action.triggered.connect(self.show_wordpress_preview)
        self.wordpress_theme_preview_action = QAction(self)
        self.wordpress_theme_preview_action.setShortcut("Ctrl+Alt+Shift+P")
        self.wordpress_theme_preview_action.triggered.connect(self.show_wordpress_theme_preview)
        self.stop_wordpress_preview_action = QAction(self)
        self.stop_wordpress_preview_action.setEnabled(False)
        self.stop_wordpress_preview_action.triggered.connect(self.stop_wordpress_preview)

        self.word_wrap_action = QAction(self)
        self.word_wrap_action.setCheckable(True)
        self.word_wrap_action.toggled.connect(self._set_current_word_wrap_enabled)

        self.line_numbers_action = QAction(self)
        self.line_numbers_action.setCheckable(True)
        self.line_numbers_action.toggled.connect(self._set_current_line_numbers_enabled)

        self.ruler_action = QAction(self)
        self.ruler_action.setCheckable(True)
        self.ruler_action.toggled.connect(self._set_ruler_enabled)

        self.options_action = QAction(self)
        self.options_action.setShortcut("Ctrl+,")
        self.options_action.triggered.connect(self.show_options_dialog)

        self.user_help_action = QAction(self)
        self.user_help_action.setShortcut("F1")
        self.user_help_action.triggered.connect(self.show_user_help_dialog)

        self.schema_reference_action = QAction(self)
        self.schema_reference_action.triggered.connect(self.show_schema_reference_dialog)

        self.english_action = QAction(self)
        self.english_action.setCheckable(True)
        self.english_action.triggered.connect(lambda: self.set_language("en"))

        self.japanese_action = QAction(self)
        self.japanese_action.setCheckable(True)
        self.japanese_action.triggered.connect(lambda: self.set_language("ja"))

        self.language_action_group = QActionGroup(self)
        self.language_action_group.setExclusive(True)
        self.language_action_group.addAction(self.english_action)
        self.language_action_group.addAction(self.japanese_action)

    def _create_menus(self) -> None:
        """Create menus for the main window."""
        menu_bar = self.menuBar()

        self.file_menu = QMenu(self)
        self.file_menu.addAction(self.new_action)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addMenu(self.open_with_encoding_menu)
        self.file_menu.addAction(self.reload_action)
        self.file_menu.addMenu(self.reload_with_encoding_menu)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_as_action)
        self.file_menu.addAction(self.restore_file_backup_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)
        menu_bar.addMenu(self.file_menu)

        self.edit_menu = QMenu(self)
        self.edit_menu.addAction(self.undo_action)
        self.edit_menu.addAction(self.redo_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.select_all_action)
        self.edit_menu.addAction(self.copy_rectangular_selection_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.insert_br_action)
        self.edit_menu.addAction(self.insert_br_br_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.inline_strong_action)
        self.edit_menu.addAction(self.inline_underline_action)
        for preset in self.color_presets.text_colors:
            self.edit_menu.addAction(self.inline_color_actions[preset.identifier])
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.insert_tag_picker_action)
        self.edit_menu.addMenu(self.insert_tag_menu)
        menu_bar.addMenu(self.edit_menu)

        self.search_menu = QMenu(self)
        self.search_menu.addAction(self.find_action)
        self.search_menu.addAction(self.grammar_check_action)
        menu_bar.addMenu(self.search_menu)

        self.view_menu = QMenu(self)
        self.view_menu.addAction(self.line_numbers_action)
        self.view_menu.addAction(self.word_wrap_action)
        self.view_menu.addAction(self.ruler_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.wordpress_preview_action)
        self.view_menu.addAction(self.wordpress_theme_preview_action)
        self.view_menu.addAction(self.stop_wordpress_preview_action)
        menu_bar.addMenu(self.view_menu)

        self.options_menu = QMenu(self)
        self.options_menu.addAction(self.options_action)
        menu_bar.addMenu(self.options_menu)

        self.language_menu = QMenu(self)
        self.language_menu.addAction(self.english_action)
        self.language_menu.addAction(self.japanese_action)
        menu_bar.addMenu(self.language_menu)

        self.help_menu = QMenu(self)
        self.help_menu.addAction(self.user_help_action)
        self.help_menu.addAction(self.schema_reference_action)
        menu_bar.addMenu(self.help_menu)

    def _create_status_bar(self) -> None:
        """Create the status bar for the main window."""
        self.setStatusBar(QStatusBar(self))
        self.wordpress_status_label = QLabel(self)
        self.wordpress_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.wordpress_status_label.setContentsMargins(8, 0, 4, 0)
        self.statusBar().addPermanentWidget(self.wordpress_status_label)

    def _create_editor_tab(
        self,
        text: str = "",
        save_file_path: Path | None = None,
        encoding: str | None = None,
        modified: bool = False,
    ) -> TextEditor:
        """Create a new editor tab with the specified parameters."""
        editor = TextEditor()
        editor.setPlainText(text)
        editor.document().setModified(modified)
        line_numbers_action = getattr(self, "line_numbers_action", None)
        word_wrap_action = getattr(self, "word_wrap_action", None)
        editor.set_line_numbers_enabled(
            line_numbers_action.isChecked()
            if isinstance(line_numbers_action, QAction)
            else True
        )
        editor.set_word_wrap_enabled(
            word_wrap_action.isChecked() if isinstance(word_wrap_action, QAction) else False
        )
        editor.set_search_marker_colors(
            self.search_marker_color,
            self.current_match_marker_color,
        )
        editor.set_visible_whitespace_options(
            spaces_enabled=self.visible_spaces_enabled,
            tabs_enabled=self.visible_tabs_enabled,
            newlines_enabled=self.visible_newlines_enabled,
        )
        editor.set_visible_whitespace_marker_colors(
            space_color=self.visible_space_marker_color,
            tab_color=self.visible_tab_marker_color,
            newline_color=self.visible_newline_marker_color,
        )
        editor.setFont(QFont(self.font_family, self.font_size))
        self._set_editor_tab_width(editor)
        editor.set_editor_colors(
            background_color=self.editor_background_color,
            text_color=self.editor_text_color,
            html_tag_color=self.html_tag_color,
            wordpress_core_block_color=self.wordpress_core_block_color,
        )
        editor.set_fixed_column_wrap_options(
            enabled=self.fixed_column_wrap_enabled,
            column=self.fixed_column_wrap_column,
        )
        editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        editor.customContextMenuRequested.connect(self._show_editor_context_menu)
        editor.textChanged.connect(self._update_status_bar)
        editor.textChanged.connect(self._update_tab_titles)
        editor.textChanged.connect(self._save_unsaved_backup)
        editor.textChanged.connect(self._refresh_search_highlights_from_dialog)
        editor.textChanged.connect(editor.clear_grammar_issue_lines)
        editor.textChanged.connect(
            lambda editor=editor: self._invalidate_grammar_lint_result(editor)
        )
        editor.cursorPositionChanged.connect(self._update_status_bar)
        editor.document().modificationChanged.connect(self._update_tab_titles)
        editor.document().modificationChanged.connect(self._update_window_title)

        self.tab_file_paths[editor] = save_file_path
        self.tab_encodings[editor] = encoding or self.default_encoding
        self.tab_grammar_result_paths[editor] = (
            self.grammar_lint_result_store.create_result_path(
                self.window_id,
                uuid.uuid4().hex,
            )
        )
        editor_tab = EditorTab(editor)
        editor_tab.set_ruler_visible(self.ruler_action.isChecked())
        editor_tab.ruler.column_clicked.connect(self._set_fixed_wrap_column_from_ruler)
        tab_index = self.tab_widget.addTab(editor_tab, self._tab_title(editor))
        self.tab_widget.setCurrentIndex(tab_index)
        self._sync_current_tab_state()
        return editor

    def create_editor_tab(
        self,
        text: str = "",
        save_file_path: Path | None = None,
        encoding: str | None = None,
        modified: bool = False,
    ) -> TextEditor:
        """Create an editor tab for external window operations."""
        return self._create_editor_tab(
            text=text,
            save_file_path=save_file_path,
            encoding=encoding,
            modified=modified,
        )

    def _handle_current_tab_changed(self, index: int) -> None:
        """Handle the event when the current tab is changed."""
        editor = self._editor_at(index)
        if editor is None:
            return
        self.editor = editor
        self._sync_current_tab_state()
        self.search_scope = None
        self._update_status_bar()
        self._update_window_title()
        self._rebuild_insert_tag_menu()
        self._refresh_grammar_dialog_for_current_tab()

    def _sync_current_tab_state(self) -> None:
        """Synchronize the state of the current tab with the main window."""
        self.current_save_file_path = self.tab_file_paths.get(self.editor)
        self.current_encoding = self.tab_encodings.get(
            self.editor,
            self.default_encoding,
        )

    def _set_current_file_state(
        self,
        save_file_path: Path | None,
        encoding: str | None = None,
    ) -> None:
        """Set the current file state, including the save file path and encoding."""
        self.current_save_file_path = save_file_path
        self.tab_file_paths[self.editor] = save_file_path
        if encoding is not None:
            self.current_encoding = encoding
            self.tab_encodings[self.editor] = encoding
        self._update_tab_titles()

    def _tab_title(self, editor: TextEditor) -> str:
        """Get the title for the tab corresponding to the given editor."""
        save_file_path = self.tab_file_paths.get(editor)
        title = save_file_path.name if save_file_path is not None else self._draft_title(editor)
        return f"*{title}" if editor.document().isModified() else title

    def _draft_title(self, editor: TextEditor) -> str:
        """Get the draft title for the given editor based on its content."""
        lines = editor.toPlainText().splitlines()
        first_line = lines[0].strip() if lines else ""
        if not first_line:
            return self.translator.text("document.untitled")
        return first_line[:30]

    def _update_tab_titles(self) -> None:
        """Update the titles of all tabs based on their current state."""
        for index in range(self.tab_widget.count()):
            editor = self._editor_at(index)
            if editor is not None:
                self.tab_widget.setTabText(index, self._tab_title(editor))

    def _set_current_word_wrap_enabled(self, enabled: bool) -> None:
        """Enable or disable word wrap for all open editors."""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.set_word_wrap_enabled(enabled)

    def _set_current_line_numbers_enabled(self, enabled: bool) -> None:
        """Enable or disable line numbers for all open editors."""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.set_line_numbers_enabled(enabled)
            editor_tab = self._editor_tab_at(tab_index)
            if editor_tab is not None:
                editor_tab.ruler.update()

    def _set_ruler_enabled(self, enabled: bool) -> None:
        """Enable or disable the character ruler."""
        for tab_index in range(self.tab_widget.count()):
            editor_tab = self._editor_tab_at(tab_index)
            if editor_tab is not None:
                editor_tab.set_ruler_visible(enabled)

    def _set_fixed_wrap_column_from_ruler(self, column: int) -> None:
        """Set the fixed wrap column from a ruler click."""
        self.fixed_column_wrap_column = max(1, column)
        if self.fixed_column_wrap_enabled:
            self._apply_fixed_column_wrap_options_to_all_tabs()
        self._save_settings()

    def _show_tab_context_menu(self, position: QPoint) -> None:
        """Show the context menu for the tab at the given position."""
        tab_index = self.tab_widget.tabBar().tabAt(position)
        if tab_index < 0:
            return

        menu = QMenu(self)
        close_action = menu.addAction(self.translator.text("tab.close"))
        duplicate_action = menu.addAction(self.translator.text("tab.duplicate"))
        move_to_window_action = menu.addAction(self.translator.text("tab.move_to_window"))
        selected_action = menu.exec(self.tab_widget.tabBar().mapToGlobal(position))
        if selected_action == close_action:
            self.close_tab(tab_index)
        elif selected_action == duplicate_action:
            self.duplicate_tab(tab_index)
        elif selected_action == move_to_window_action:
            self.move_tab_to_new_window(tab_index)

    def close_tab(self, tab_index: int) -> bool:
        """Close the tab at the given index, prompting to save if necessary."""
        editor = self._editor_at(tab_index)
        if editor is None:
            return False
        if not self._confirm_save_or_discard_editor(editor):
            return False

        self._remove_tab(tab_index)
        if self.tab_widget.count() == 0:
            self._create_editor_tab()
        self._sync_current_tab_state()
        self._update_status_bar()
        self._update_window_title()
        self._save_unsaved_backup()
        return True

    def duplicate_tab(self, tab_index: int) -> TextEditor | None:
        """Duplicate the tab at the given index, creating a new editor with the same content."""
        editor = self._editor_at(tab_index)
        if editor is None:
            return None

        duplicate_editor = self._create_editor_tab(
            text=editor.toPlainText(),
            save_file_path=None,
            encoding=self.tab_encodings.get(editor, self.default_encoding),
            modified=True,
        )
        duplicate_editor.moveCursor(QTextCursor.MoveOperation.Start)
        self._save_unsaved_backup()
        return duplicate_editor

    def move_tab_to_new_window(self, tab_index: int) -> MainWindow | None:
        """Move the tab at the given index to a new window."""
        editor = self._editor_at(tab_index)
        if editor is None:
            return None
        if not self._autosave_before_risky_operation():
            return None

        new_window = MainWindow(
            settings_path=self.settings_manager.settings_path,
            restore_unsaved_backup=False,
        )
        new_window.remove_tab(0)
        new_window.create_editor_tab(
            text=editor.toPlainText(),
            save_file_path=self.tab_file_paths.get(editor),
            encoding=self.tab_encodings.get(editor, self.default_encoding),
            modified=editor.document().isModified(),
        )
        new_window.show()
        self.tab_windows.append(new_window)
        self.child_windows[new_window.window_id] = new_window
        new_window.destroyed.connect(
            lambda _object=None, child_window_id=new_window.window_id: (
                self.child_windows.pop(child_window_id, None)
            )
        )
        self._remove_tab(tab_index)
        if self.tab_widget.count() == 0:
            self._create_editor_tab()
        self._sync_current_tab_state()
        self._update_window_title()
        self._save_unsaved_backup()
        return new_window

    def _editor_at(self, tab_index: int) -> TextEditor | None:
        """Return the editor widget at the given tab index, or None if it doesn't exist."""
        widget = self.tab_widget.widget(tab_index)
        if isinstance(widget, EditorTab):
            return widget.editor
        return widget if isinstance(widget, TextEditor) else None

    def _editor_tab_at(self, tab_index: int) -> EditorTab | None:
        """Return the editor tab container at the given tab index, if it exists."""
        widget = self.tab_widget.widget(tab_index)
        return widget if isinstance(widget, EditorTab) else None

    def _current_editor(self) -> TextEditor | None:
        """Return the editor widget in the current tab, or None if it doesn't exist."""
        return self._editor_at(self.tab_widget.currentIndex())

    def _undo_current_editor(self) -> None:
        """Undo in the current editor tab if one exists."""
        editor = self._current_editor()
        if editor is not None:
            editor.undo()

    def _redo_current_editor(self) -> None:
        """Redo in the current editor tab if one exists."""
        editor = self._current_editor()
        if editor is not None:
            editor.redo()

    def _select_all_current_editor(self) -> None:
        """Select all text in the current editor tab if one exists."""
        editor = self._current_editor()
        if editor is not None:
            editor.selectAll()

    def copy_rectangular_selection(self) -> None:
        """Copy the current multi-line selection as a rectangular text block."""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            self.statusBar().showMessage(
                self.translator.text("rectangular.copy_no_selection")
            )
            return

        source_text = self.editor.toPlainText()
        selection = rectangular_selection_from_text_positions(
            source_text,
            self.editor.cursor_position_to_text_position(cursor.selectionStart()),
            self.editor.cursor_position_to_text_position(cursor.selectionEnd()),
        )
        copied_text = rectangular_text(source_text, selection)
        if not copied_text:
            self.statusBar().showMessage(
                self.translator.text("rectangular.copy_empty")
            )
            return

        QApplication.clipboard().setText(copied_text)
        copied_line_count = copied_text.count("\n") + 1
        self.statusBar().showMessage(
            self.translator.text(
                "rectangular.copy_done",
                lines=copied_line_count,
            )
        )

    def _remove_tab(self, tab_index: int) -> None:
        """Remove the tab at the given index and clean up its associated resources."""
        widget = self.tab_widget.widget(tab_index)
        editor = self._editor_at(tab_index)
        self.tab_widget.removeTab(tab_index)
        if editor is not None:
            self._delete_grammar_lint_result(editor)
            self.tab_file_paths.pop(editor, None)
            self.tab_encodings.pop(editor, None)
            self.tab_grammar_result_paths.pop(editor, None)
        if widget is not None:
            widget.deleteLater()

    def remove_tab(self, tab_index: int) -> None:
        """Remove a tab without prompting to save."""
        self._remove_tab(tab_index)

    def _restore_settings(self, settings: EditorSettings) -> None:
        """Restore the main window and editor settings from the given EditorSettings object."""
        self.line_numbers_action.setChecked(settings.line_numbers_enabled)
        self.word_wrap_action.setChecked(settings.word_wrap_enabled)
        self.ruler_action.setChecked(settings.ruler_enabled)
        self._set_ruler_enabled(settings.ruler_enabled)
        self.fixed_column_wrap_enabled = settings.fixed_column_wrap_enabled
        self.fixed_column_wrap_column = settings.fixed_column_wrap_column
        self._apply_fixed_column_wrap_options_to_all_tabs()
        self.startup_restore_enabled = settings.startup_restore_enabled
        self.auto_backup_interval_minutes = settings.auto_backup_interval_minutes
        self._set_auto_save_timer_interval(self.auto_backup_interval_minutes)
        self.default_encoding = settings.default_encoding
        self.newline_code = settings.newline_code
        self.search_marker_color = settings.search_marker_color
        self.current_match_marker_color = settings.current_match_marker_color
        self._apply_search_marker_colors_to_all_tabs()
        self.visible_space_marker_color = settings.visible_space_marker_color
        self.visible_tab_marker_color = settings.visible_tab_marker_color
        self.visible_newline_marker_color = settings.visible_newline_marker_color
        self._apply_visible_whitespace_marker_colors_to_all_tabs()
        self.visible_spaces_enabled = settings.visible_spaces_enabled
        self.visible_tabs_enabled = settings.visible_tabs_enabled
        self.visible_newlines_enabled = settings.visible_newlines_enabled
        self._apply_visible_whitespace_options_to_all_tabs()
        self.editor_theme = settings.editor_theme
        self.editor_background_color = settings.editor_background_color
        self.editor_text_color = settings.editor_text_color
        self.html_tag_color = settings.html_tag_color
        self.wordpress_core_block_color = settings.wordpress_core_block_color
        self._apply_editor_colors_to_all_tabs()
        self._apply_editor_font_to_all_tabs()
        self.english_action.setChecked(settings.language_code == "en")
        self.japanese_action.setChecked(settings.language_code != "en")
        if settings.window_width > 0 and settings.window_height > 0:
            self.resize(settings.window_width, settings.window_height)

    def _save_settings(self) -> None:
        """Save the current main window and editor settings to the settings manager."""
        self.settings_manager.save(
            word_wrap_enabled=self.word_wrap_action.isChecked(),
            line_numbers_enabled=self.line_numbers_action.isChecked(),
            ruler_enabled=self.ruler_action.isChecked(),
            visible_spaces_enabled=self.visible_spaces_enabled,
            visible_tabs_enabled=self.visible_tabs_enabled,
            visible_newlines_enabled=self.visible_newlines_enabled,
            fixed_column_wrap_enabled=self.fixed_column_wrap_enabled,
            fixed_column_wrap_column=self.fixed_column_wrap_column,
            startup_restore_enabled=self.startup_restore_enabled,
            language_code=self.translator.language_code,
            default_encoding=self.default_encoding,
            newline_code=self.newline_code,
            window_width=self.width(),
            window_height=self.height(),
            wordpress_mode_label_key=self.wordpress_mode_label_key,
            hover_hints_enabled=self.hover_hints_enabled,
            user_dictionary_folder=self.user_dictionary_folder,
            dictionary_check_enabled=self.dictionary_check_enabled,
            backup_folder=self.backup_folder,
            backup_retention_count=self.backup_retention_count,
            backup_retention_days=self.backup_retention_days,
            auto_backup_interval_minutes=self.auto_backup_interval_minutes,
            font_family=self.font_family,
            font_size=self.font_size,
            tab_width=self.tab_width,
            editor_theme=self.editor_theme,
            editor_background_color=self.editor_background_color,
            editor_text_color=self.editor_text_color,
            html_tag_color=self.html_tag_color,
            wordpress_core_block_color=self.wordpress_core_block_color,
            search_marker_color=self.search_marker_color,
            current_match_marker_color=self.current_match_marker_color,
            visible_space_marker_color=self.visible_space_marker_color,
            visible_tab_marker_color=self.visible_tab_marker_color,
            visible_newline_marker_color=self.visible_newline_marker_color,
            regex_lint_enabled=self.regex_lint_enabled,
            html_typo_lint_enabled=self.html_typo_lint_enabled,
            reduced_error_check_enabled=self.reduced_error_check_enabled,
            frame_alignment=self.frame_alignment,
            frame_display=self.frame_display,
            frame_outer_spacing=self.frame_outer_spacing,
            frame_background_color=self.frame_background_color,
            frame_text_color=self.frame_text_color,
        )

    def set_language(self, language_code: str) -> None:
        """Set the application's language and update the UI accordingly."""
        self.translator.set_language(language_code)
        self.english_action.setChecked(language_code == "en")
        self.japanese_action.setChecked(language_code == "ja")
        self._apply_language()
        self._save_settings()

    def _apply_language(self) -> None:
        """Apply the current language to all UI elements."""
        self.file_menu.setTitle(self.translator.text("menu.file"))
        self.edit_menu.setTitle(self.translator.text("menu.edit"))
        self.search_menu.setTitle(self.translator.text("menu.search"))
        self.view_menu.setTitle(self.translator.text("menu.view"))
        self.options_menu.setTitle(self.translator.text("menu.options"))
        self.language_menu.setTitle(self.translator.text("menu.language"))
        self.help_menu.setTitle(self.translator.text("menu.help"))

        self.new_action.setText(self.translator.text("action.new"))
        self.open_action.setText(self.translator.text("action.open"))
        self.open_with_encoding_menu.setTitle(
            self.translator.text("action.open_with_encoding")
        )
        self.reload_action.setText(self.translator.text("action.reload"))
        self.reload_with_encoding_menu.setTitle(
            self.translator.text("action.reload_with_encoding")
        )
        self.save_action.setText(self.translator.text("action.save"))
        self.save_as_action.setText(self.translator.text("action.save_as"))
        self.restore_file_backup_action.setText(
            self.translator.text("action.restore_file_backup")
        )
        self.exit_action.setText(self.translator.text("action.exit"))
        self.undo_action.setText(self.translator.text("action.undo"))
        self.redo_action.setText(self.translator.text("action.redo"))
        self.select_all_action.setText(self.translator.text("action.select_all"))
        self.copy_rectangular_selection_action.setText(
            self.translator.text("action.copy_rectangular_selection")
        )
        self.insert_br_action.setText(self.translator.text("action.insert_br"))
        self.insert_br_br_action.setText(self.translator.text("action.insert_br_br"))
        self.inline_strong_action.setText(
            self.translator.text("action.inline_strong")
        )
        self.inline_underline_action.setText(
            self.translator.text("action.inline_underline")
        )
        for preset in self.color_presets.text_colors:
            self.inline_color_actions[preset.identifier].setText(
                self._inline_color_action_text(preset)
            )
        self.html_escape_action.setText(self.translator.text("action.html_escape"))
        self.html_unescape_action.setText(self.translator.text("action.html_unescape"))
        self.wordpress_code_block_action.setText(
            self.translator.text("action.wordpress_code_block")
        )
        self.wordpress_complex_blocks_action.setText(
            self.translator.text("action.wordpress_complex_blocks")
        )
        self.wordpress_table_transform_action.setText(
            self.translator.text("action.wordpress_table_transform")
        )
        self.wordpress_list_transform_action.setText(
            self.translator.text("action.wordpress_list_transform")
        )
        self.wordpress_list_frame_transform_action.setText(
            self.translator.text("action.wordpress_list_frame_transform")
        )
        for action_id, text_key, _insert_text, _cursor_offset in CSS_PARAMETER_INSERT_ACTIONS:
            self.css_parameter_actions[action_id].setText(self.translator.text(text_key))
        self.paragraph_split_spacer_action.setText(
            self.translator.text("paragraph_split.insert_spacer")
        )
        self.paragraph_split_html_action.setText(
            self.translator.text("paragraph_split.insert_html")
        )
        self.paragraph_split_decorated_action.setText(
            self.translator.text("paragraph_split.decorated_block")
        )
        self.insert_tag_picker_action.setText(
            self.translator.text("action.insert_tag_picker")
        )
        self._rebuild_insert_tag_menu()
        self.find_action.setText(self.translator.text("action.find_replace"))
        self.grammar_check_action.setText(self.translator.text("action.grammar_check"))
        self.wordpress_preview_action.setText(self.translator.text("action.wordpress_preview"))
        self.wordpress_theme_preview_action.setText(self.translator.text("action.wordpress_theme_preview"))
        self.stop_wordpress_preview_action.setText(self.translator.text("action.stop_wordpress_preview"))
        self.word_wrap_action.setText(self.translator.text("action.word_wrap"))
        self.line_numbers_action.setText(self.translator.text("action.line_numbers"))
        self.ruler_action.setText(self.translator.text("options.item.ruler"))
        self.options_action.setText(self.translator.text("action.options"))
        self.user_help_action.setText(self.translator.text("action.user_help"))
        self.schema_reference_action.setText(
            self.translator.text("action.schema_reference")
        )
        self.english_action.setText(self.translator.text("language.english"))
        self.japanese_action.setText(self.translator.text("language.japanese"))

        if self.find_replace_dialog is not None:
            self.find_replace_dialog.apply_language()
        if self.grammar_check_dialog is not None:
            self.grammar_check_dialog.apply_language()
        if self.regex_help_dialog is not None:
            self.regex_help_dialog.apply_language()
        if self.tag_insert_dialog is not None:
            self.tag_insert_dialog.apply_language()
        if self.user_help_dialog is not None:
            self.user_help_dialog.apply_language()
        if self.schema_reference_dialog is not None:
            self.schema_reference_dialog.apply_language()
        if self.options_dialog is not None:
            self.options_dialog.apply_language()
        self._update_status_bar()
        self._update_wordpress_status_label()
        self._update_window_title()

    def _rebuild_insert_tag_menu(self) -> None:
        """Rebuild the insert tag menu based on the current language and available tag snippets."""
        self.insert_tag_menu.clear()
        self.insert_tag_menu.setTitle(self.translator.text("action.insert_tag"))
        self._set_tag_menu_tooltips_visible(self.insert_tag_menu)
        self._populate_insert_tag_menu(self.insert_tag_menu)

    def _populate_insert_tag_menu(self, root_menu: QMenu) -> None:
        """Populate the insert tag menu with tag snippet groups."""
        self._set_tag_menu_tooltips_visible(root_menu)
        for group in ordered_tag_snippet_groups(
            self.current_save_file_path,
            self._tag_dictionaries_path(),
        ):
            group_menu = root_menu.addMenu(self.translator.text(group.label_key))
            assert group_menu is not None
            self._set_tag_menu_tooltips_visible(group_menu)
            if group.label_key == WORDPRESS_GROUP_LABEL_KEY:
                self._populate_wordpress_tag_mode_menus(group_menu, group)
            else:
                self._populate_tag_category_menu(
                    group_menu,
                    group.label_key,
                    group.snippets,
                )

    def _populate_wordpress_tag_mode_menus(
        self,
        group_menu: QMenu,
        group: TagSnippetGroup,
    ) -> None:
        """Populate the WordPress tag mode submenus within the insert tag menu."""
        mode_label_keys = sorted(
            wordpress_mode_label_keys(),
            key=lambda mode_label_key: (
                0 if mode_label_key == self.wordpress_mode_label_key else 1
            ),
        )
        for mode_label_key in mode_label_keys:
            mode_menu = group_menu.addMenu(self.translator.text(mode_label_key))
            assert mode_menu is not None
            self._set_tag_menu_tooltips_visible(mode_menu)
            self._populate_tag_category_menu(
                mode_menu,
                group.label_key,
                wordpress_snippets_for_mode(group.snippets, mode_label_key),
            )

    def _populate_tag_category_menu(
        self,
        root_menu: QMenu,
        group_label_key: str,
        snippets: tuple[TagSnippet, ...],
    ) -> None:
        """Populate a tag category menu with the given tag snippets."""
        category_menus: dict[str, QMenu] = {}
        for snippet in snippets:
            category_key = tag_snippet_category_key(group_label_key, snippet)
            category_menu = category_menus.get(category_key)
            if category_menu is None:
                category_menu = root_menu.addMenu(self.translator.text(category_key))
                assert category_menu is not None
                self._set_tag_menu_tooltips_visible(category_menu)
                category_menus[category_key] = category_menu
            category_menu.addAction(self._create_tag_snippet_action(snippet))

    def _set_tag_menu_tooltips_visible(self, menu: QMenu) -> None:
        menu.setToolTipsVisible(self.hover_hints_enabled)

    def _create_tag_snippet_action(self, snippet: TagSnippet) -> QAction:
        """Create a QAction for the given tag snippet, including its label, hint, and triggered behavior."""
        label = self.translator.text(snippet.label_key)
        hint = self.translator.text(snippet.hint_key)
        action = QAction(label, self)
        if self.hover_hints_enabled:
            action.setStatusTip(hint)
            action.setToolTip(escape(hint, quote=False))
            action.hovered.connect(
                lambda hint_text=hint: self.statusBar().showMessage(hint_text)
            )
        action.triggered.connect(
            lambda checked=False, value=snippet: self.insert_tag_snippet(value)
        )
        return action

    def _show_editor_context_menu(self, position: QPoint) -> None:
        """Show the context menu for the editor at the given position."""
        if not self.editor.textCursor().hasSelection():
            self.editor.setTextCursor(self.editor.cursorForPosition(position))
        context_menu = self._create_editor_context_menu()
        context_menu.exec(self.editor.mapToGlobal(position))

    def _create_editor_context_menu(self) -> QMenu:
        """Create and return the context menu for the editor, including standard actions and the insert tag menu."""
        context_menu = self.editor.createStandardContextMenu()
        context_menu.addSeparator()
        paragraph_split_menu = QMenu(
            self.translator.text("paragraph_split.menu"),
            context_menu,
        )
        paragraph_split_menu.addAction(self.paragraph_split_spacer_action)
        paragraph_split_menu.addAction(self.paragraph_split_html_action)
        paragraph_split_menu.addAction(self.paragraph_split_decorated_action)
        paragraph_split_menu.addSeparator()
        paragraph_split_menu.addAction(self.wordpress_table_transform_action)
        paragraph_split_menu.addAction(self.wordpress_list_transform_action)
        paragraph_split_menu.addAction(self.wordpress_list_frame_transform_action)
        paragraph_split_menu.addAction(self.wordpress_complex_blocks_action)
        context_menu.addMenu(paragraph_split_menu)
        insert_tag_menu = QMenu(self.translator.text("action.insert_tag"), context_menu)
        self._set_tag_menu_tooltips_visible(insert_tag_menu)
        self._populate_insert_tag_menu(insert_tag_menu)
        context_menu.addMenu(insert_tag_menu)
        inline_color_menu = QMenu(
            self.translator.text("action.inline_color_menu"),
            context_menu,
        )
        for preset in self.color_presets.text_colors:
            inline_color_menu.addAction(self.inline_color_actions[preset.identifier])
        context_menu.addMenu(inline_color_menu)
        css_insert_menu = QMenu(
            self.translator.text("action.css_insert"),
            context_menu,
        )
        for action_id, _text_key, _insert_text, _cursor_offset in CSS_PARAMETER_INSERT_ACTIONS:
            css_insert_menu.addAction(self.css_parameter_actions[action_id])
        context_menu.addMenu(css_insert_menu)
        context_menu.addAction(self.insert_tag_picker_action)
        html_transform_menu = QMenu(
            self.translator.text("action.html_transform"),
            context_menu,
        )
        html_transform_menu.addAction(self.html_escape_action)
        html_transform_menu.addAction(self.html_unescape_action)
        html_transform_menu.addSeparator()
        html_transform_menu.addAction(self.wordpress_code_block_action)
        context_menu.addMenu(html_transform_menu)
        return context_menu

    def show_tag_insert_dialog(self) -> None:
        """Show the tag insert dialog, allowing the user to select and insert a tag snippet."""
        if self.tag_insert_dialog is None:
            self.tag_insert_dialog = TagInsertDialog(self.translator, self)

        self.tag_insert_dialog.set_hover_hints_enabled(self.hover_hints_enabled)
        self.tag_insert_dialog.set_snippet_groups(
            ordered_tag_snippet_groups(
                self.current_save_file_path,
                self._tag_dictionaries_path(),
            )
        )
        self.tag_insert_dialog.search_edit.clear()
        self.tag_insert_dialog.selected_snippet = None
        if self.tag_insert_dialog.exec() != TagInsertDialog.DialogCode.Accepted:
            return
        selected_snippet = self.tag_insert_dialog.selected_choice()
        if selected_snippet is not None:
            self.insert_tag_snippet(selected_snippet)

    def show_options_dialog(self) -> None:
        """Show the options dialog, allowing the user to modify editor and application settings."""
        settings = EditorSettings(
            word_wrap_enabled=self.word_wrap_action.isChecked(),
            line_numbers_enabled=self.line_numbers_action.isChecked(),
            ruler_enabled=self.ruler_action.isChecked(),
            visible_spaces_enabled=self.visible_spaces_enabled,
            visible_tabs_enabled=self.visible_tabs_enabled,
            visible_newlines_enabled=self.visible_newlines_enabled,
            fixed_column_wrap_enabled=self.fixed_column_wrap_enabled,
            fixed_column_wrap_column=self.fixed_column_wrap_column,
            startup_restore_enabled=self.startup_restore_enabled,
            language_code=self.translator.language_code,
            default_encoding=self.default_encoding,
            newline_code=self.newline_code,
            window_width=self.width(),
            window_height=self.height(),
            wordpress_mode_label_key=self.wordpress_mode_label_key,
            hover_hints_enabled=self.hover_hints_enabled,
            user_dictionary_folder=self.user_dictionary_folder,
            dictionary_check_enabled=self.dictionary_check_enabled,
            backup_folder=self.backup_folder,
            backup_retention_count=self.backup_retention_count,
            backup_retention_days=self.backup_retention_days,
            auto_backup_interval_minutes=self.auto_backup_interval_minutes,
            font_family=self.font_family,
            font_size=self.font_size,
            tab_width=self.tab_width,
            editor_theme=self.editor_theme,
            editor_background_color=self.editor_background_color,
            editor_text_color=self.editor_text_color,
            html_tag_color=self.html_tag_color,
            wordpress_core_block_color=self.wordpress_core_block_color,
            search_marker_color=self.search_marker_color,
            current_match_marker_color=self.current_match_marker_color,
            visible_space_marker_color=self.visible_space_marker_color,
            visible_tab_marker_color=self.visible_tab_marker_color,
            visible_newline_marker_color=self.visible_newline_marker_color,
            regex_lint_enabled=self.regex_lint_enabled,
            html_typo_lint_enabled=self.html_typo_lint_enabled,
            reduced_error_check_enabled=self.reduced_error_check_enabled,
            frame_alignment=self.frame_alignment,
            frame_display=self.frame_display,
            frame_outer_spacing=self.frame_outer_spacing,
            frame_background_color=self.frame_background_color,
            frame_text_color=self.frame_text_color,
        )
        dialog = OptionsDialog(
            self.translator,
            settings,
            self,
            default_backup_folder_path=self._file_backup_folder_for_folder(""),
            unsaved_backup_path=self._unsaved_backup_path(),
        )
        self.options_dialog = dialog
        if dialog.exec() != OptionsDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not self._validate_user_dictionaries(
            values.user_dictionary_folder,
            values.dictionary_check_enabled,
        ):
            return
        self.line_numbers_action.setChecked(values.line_numbers_enabled)
        self.word_wrap_action.setChecked(values.word_wrap_enabled)
        self.ruler_action.setChecked(values.ruler_enabled)
        if values.language_code != self.translator.language_code:
            self.set_language(values.language_code)
        self.default_encoding = values.default_encoding
        self.newline_code = values.newline_code
        self.wordpress_mode_label_key = values.wordpress_mode_label_key
        self.hover_hints_enabled = values.hover_hints_enabled
        self.user_dictionary_folder = values.user_dictionary_folder
        self.dictionary_check_enabled = values.dictionary_check_enabled
        self.backup_folder = values.backup_folder
        self.backup_retention_count = values.backup_retention_count
        self.backup_retention_days = values.backup_retention_days
        self.auto_backup_interval_minutes = values.auto_backup_interval_minutes
        self._set_auto_save_timer_interval(self.auto_backup_interval_minutes)
        self.font_family = values.font_family
        self.font_size = values.font_size
        self.editor_theme = values.editor_theme
        self.editor_background_color = values.editor_background_color
        self.editor_text_color = values.editor_text_color
        self.html_tag_color = values.html_tag_color
        self.wordpress_core_block_color = values.wordpress_core_block_color
        self.search_marker_color = values.search_marker_color
        self.current_match_marker_color = values.current_match_marker_color
        self.visible_space_marker_color = values.visible_space_marker_color
        self.visible_tab_marker_color = values.visible_tab_marker_color
        self.visible_newline_marker_color = values.visible_newline_marker_color
        self.regex_lint_enabled = values.regex_lint_enabled
        self.html_typo_lint_enabled = values.html_typo_lint_enabled
        self.reduced_error_check_enabled = values.reduced_error_check_enabled
        self.frame_alignment = values.frame_alignment
        self.frame_display = values.frame_display
        self.frame_outer_spacing = values.frame_outer_spacing
        self.frame_background_color = values.frame_background_color
        self.frame_text_color = values.frame_text_color
        self.visible_spaces_enabled = values.visible_spaces_enabled
        self.visible_tabs_enabled = values.visible_tabs_enabled
        self.visible_newlines_enabled = values.visible_newlines_enabled
        self.fixed_column_wrap_enabled = values.fixed_column_wrap_enabled
        self.fixed_column_wrap_column = values.fixed_column_wrap_column
        self.startup_restore_enabled = values.startup_restore_enabled
        self.tab_width = values.tab_width
        self.unsaved_backup_manager = UnsavedBackupManager(
            self._unsaved_backup_path()
        )
        self.file_backup_manager = FileBackupManager(
            self._file_backup_folder_for_folder(self.backup_folder)
        )
        self._apply_editor_font_to_all_tabs()
        self._apply_editor_colors_to_all_tabs()
        self._apply_search_marker_colors_to_all_tabs()
        self._apply_visible_whitespace_options_to_all_tabs()
        self._apply_visible_whitespace_marker_colors_to_all_tabs()
        self._apply_fixed_column_wrap_options_to_all_tabs()
        self._apply_regex_lint_option_to_find_dialog()
        self._rebuild_insert_tag_menu()
        self._save_settings()

    def _validate_user_dictionaries(
        self,
        user_dictionary_folder: str,
        dictionary_check_enabled: bool,
    ) -> bool:
        if not dictionary_check_enabled or not user_dictionary_folder:
            return True
        try:
            tag_snippet_groups(Path(user_dictionary_folder))
            load_paragraph_insert_rule_book(Path(user_dictionary_folder))
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.critical(
                self,
                self.translator.text("dialog.dictionary_check_failed.title"),
                str(error),
            )
            return False
        return True

    def _tag_dictionaries_path(self) -> Path | None:
        if not self.user_dictionary_folder:
            return None
        return Path(self.user_dictionary_folder)

    def _internal_data_folder(self) -> Path:
        """Return the app-owned internal data folder for portable runtime files."""
        return app_base_dir() / "_internal"

    def _unsaved_backup_path(self) -> Path:
        """Return the path to the unsaved session restore file."""
        return self._internal_data_folder() / "autosave" / "unsaved_backup.json"

    def _file_backup_folder_for_folder(self, backup_folder: str) -> Path:
        """Return the folder for saved-file generation backups."""
        if backup_folder:
            return Path(backup_folder)
        return self._internal_data_folder() / "backup"

    def _set_auto_save_timer_interval(self, interval_minutes: int) -> None:
        """Set the automatic unsaved backup timer interval in minutes."""
        self.auto_save_timer.setInterval(
            max(1, interval_minutes) * 60 * 1000
        )

    def _apply_editor_font_to_all_tabs(self) -> None:
        """Apply the current editor font settings to all open tabs."""
        editor_font = QFont(self.font_family, self.font_size)
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is None:
                continue
            editor.setFont(editor_font)
            self._set_editor_tab_width(editor)
            editor.update_line_number_area_width()
            editor_tab = self._editor_tab_at(tab_index)
            if editor_tab is not None:
                editor_tab.ruler.set_editor(editor)
                editor_tab.ruler.update()

    def _apply_editor_colors_to_all_tabs(self) -> None:
        """Apply the current editor theme colors to all open tabs."""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.set_editor_colors(
                    background_color=self.editor_background_color,
                    text_color=self.editor_text_color,
                    html_tag_color=self.html_tag_color,
                    wordpress_core_block_color=self.wordpress_core_block_color,
                )

    def _set_editor_tab_width(self, editor: TextEditor) -> None:
        """Apply the configured TAB width to one editor."""
        space_width = editor.fontMetrics().horizontalAdvance(" ")
        editor.setTabStopDistance(space_width * self.tab_width)

    def _apply_search_marker_colors_to_all_tabs(self) -> None:
        """Apply the current search marker colors to all open tabs."""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.set_search_marker_colors(
                    self.search_marker_color,
                    self.current_match_marker_color,
                )

    def _apply_visible_whitespace_options_to_all_tabs(self) -> None:
        """Apply visible whitespace option flags to all open tabs."""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.set_visible_whitespace_options(
                    spaces_enabled=self.visible_spaces_enabled,
                    tabs_enabled=self.visible_tabs_enabled,
                    newlines_enabled=self.visible_newlines_enabled,
                )

    def _apply_visible_whitespace_marker_colors_to_all_tabs(self) -> None:
        """Apply visible whitespace marker colors to all open tabs."""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.set_visible_whitespace_marker_colors(
                    space_color=self.visible_space_marker_color,
                    tab_color=self.visible_tab_marker_color,
                    newline_color=self.visible_newline_marker_color,
                )

    def _apply_fixed_column_wrap_options_to_all_tabs(self) -> None:
        """Apply fixed-column wrap options to all open tabs."""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is None:
                continue
            editor.set_fixed_column_wrap_options(
                enabled=self.fixed_column_wrap_enabled,
                column=self.fixed_column_wrap_column,
            )
            editor_tab = self._editor_tab_at(tab_index)
            if editor_tab is not None:
                editor_tab.ruler.update()

    def _apply_regex_lint_option_to_find_dialog(self) -> None:
        """Apply the regex lint display option to the existing Find/Replace dialog."""
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.set_regex_lint_enabled(self.regex_lint_enabled)
            self.find_replace_dialog.set_reduced_error_check_enabled(
                self.reduced_error_check_enabled
            )

    def show_wordpress_preview(self) -> None:
        """Render the current source, export a neutral page, then stop WordPress."""
        self.wordpress_warmup_timer.stop()
        self._ensure_simple_wordpress_preview()
        assert self.wordpress_preview is not None
        source_text = self.editor.toPlainText()
        self.wordpress_preview_snapshot = (self.editor, self._source_hash(source_text))
        title = (
            self.current_save_file_path.stem if self.current_save_file_path
            else self.translator.text("wordpress_preview.title")
        )
        self.stop_wordpress_preview_action.setEnabled(True)
        self.wordpress_preview.show_preview(title, source_text)

    def _warm_wordpress_preview(self) -> None:
        if any(preview is not None and preview.sequence > 0 for preview in (self.wordpress_preview, self.wordpress_theme_preview)):
            return
        self._ensure_simple_wordpress_preview()
        assert self.wordpress_preview is not None
        self.wordpress_preview.warm_up()

    def _ensure_simple_wordpress_preview(self) -> None:
        if self.wordpress_preview is None:
            preview = WordPressPreview(
                default_runtime_root(),
                bundled_base_dir() / "resources" / "wordpress_preview" / "bridge.mjs",
                self,
                mode="simple",
            )
            preview.progress.connect(self._wordpress_preview_progress)
            preview.failed.connect(self._wordpress_preview_failed)
            preview.feedback.connect(self._wordpress_preview_feedback)
            preview.rendered.connect(self._wordpress_preview_rendered)
            preview.running_changed.connect(self._update_wordpress_stop_action)
            preview.state_changed.connect(self._update_wordpress_status_label)
            self.wordpress_preview = preview

    def show_wordpress_theme_preview(self) -> None:
        """Keep a Twenty Twenty-Five preview alive until explicitly stopped."""
        self.wordpress_warmup_timer.stop()
        if self.wordpress_preview is not None and self.wordpress_preview.warming_up:
            self.wordpress_preview.stop()
        if self.wordpress_theme_preview is None:
            preview = WordPressPreview(
                default_runtime_root(),
                bundled_base_dir() / "resources/wordpress_preview/bridge.mjs",
                self, mode="theme",
            )
            preview.progress.connect(self._wordpress_preview_progress)
            preview.failed.connect(self._wordpress_preview_failed)
            preview.feedback.connect(self._wordpress_theme_preview_feedback)
            preview.rendered.connect(self._wordpress_theme_preview_rendered)
            preview.running_changed.connect(self._update_wordpress_stop_action)
            preview.state_changed.connect(self._update_wordpress_status_label)
            self.wordpress_theme_preview = preview
        source_text = self.editor.toPlainText()
        self.wordpress_theme_preview_snapshot = (self.editor, self._source_hash(source_text))
        title = self.current_save_file_path.stem if self.current_save_file_path else self.translator.text("wordpress_preview.title")
        self.stop_wordpress_preview_action.setEnabled(True)
        self.wordpress_theme_preview.show_preview(title, source_text)

    def _update_wordpress_stop_action(self, _running: bool) -> None:
        self.stop_wordpress_preview_action.setEnabled(any(
            preview is not None and preview.running
            for preview in (self.wordpress_preview, self.wordpress_theme_preview)
        ))

    def _update_wordpress_status_label(self, _state: str = "") -> None:
        entries: list[str] = []
        details: list[str] = []
        for preview in (self.wordpress_preview, self.wordpress_theme_preview):
            if preview is None or preview.state == "stopped":
                continue
            mode = self.translator.text(f"wordpress_preview.mode.{preview.mode}")
            state = self.translator.text(f"wordpress_preview.status.{preview.state}")
            entries.append(self.translator.text("wordpress_preview.status.entry", mode=mode, state=state))
            if preview.state == "failed" and preview.last_error:
                details.append(f"{mode}: {preview.last_error}")
        if not entries:
            state = "waiting" if self.wordpress_warmup_timer.isActive() else "stopped"
            entries.append(self.translator.text(f"wordpress_preview.status.{state}"))
        self.wordpress_status_label.setText(
            self.translator.text("wordpress_preview.status.label", details=" / ".join(entries))
        )
        details.insert(0, self.translator.text("wordpress_preview.status.help"))
        tooltip = escape("\n".join(details), quote=False).replace("\n", "<br>")
        self.wordpress_status_label.setToolTip(f"<qt>{tooltip}</qt>")

    def _wordpress_preview_progress(self, stage: str) -> None:
        self.statusBar().showMessage(self.translator.text(f"wordpress_preview.stage.{stage}"))

    def _wordpress_preview_failed(self, message: str) -> None:
        self.statusBar().showMessage(self.translator.text("wordpress_preview.failed"))
        QMessageBox.warning(self, self.translator.text("wordpress_preview.title"), message)

    def _wordpress_preview_rendered(self, version: str, _url: str) -> None:
        self.statusBar().showMessage(self.translator.text("wordpress_preview.rendered", version=version))

    def _wordpress_theme_preview_rendered(self, version: str, _url: str) -> None:
        self.statusBar().showMessage(self.translator.text("wordpress_preview.theme_rendered", version=version))

    def _wordpress_preview_feedback(self, _request_id: int, status: int, warnings: str) -> None:
        self._apply_wordpress_preview_feedback(self.wordpress_preview_snapshot, status, warnings)

    def _wordpress_theme_preview_feedback(self, _request_id: int, status: int, warnings: str) -> None:
        self._apply_wordpress_preview_feedback(self.wordpress_theme_preview_snapshot, status, warnings)

    def _apply_wordpress_preview_feedback(self, snapshot: tuple[TextEditor, str] | None, status: int, warnings: str) -> None:
        if snapshot is None or snapshot[0] is not self.editor:
            return
        if snapshot[1] != self._source_hash(self.editor.toPlainText()):
            return
        # Runtime messages refer to PHP internals, not source article lines.
        # Keep them separate from the existing line-aware structural diagnostics.
        self.run_grammar_check()
        assert self.grammar_check_dialog is not None
        text = self.translator.text(
            "wordpress_preview.feedback", status=status,
            details=warnings.strip() or self.translator.text("wordpress_preview.no_runtime_warnings"),
        )
        self.grammar_check_dialog.set_runtime_feedback(text)

    def stop_wordpress_preview(self) -> None:
        self.wordpress_warmup_timer.stop()
        if self.wordpress_preview is not None:
            self.wordpress_preview.stop()
        if self.wordpress_theme_preview is not None:
            self.wordpress_theme_preview.stop()
        self.wordpress_preview_snapshot = None
        self.wordpress_theme_preview_snapshot = None
        self.stop_wordpress_preview_action.setEnabled(False)
        self._update_wordpress_status_label()

    def run_grammar_check(self) -> None:
        """Run the CSS or HTML / WordPress grammar check for the current document."""
        source_text = self.editor.toPlainText()
        messages = self._lint_document(source_text)
        if not messages:
            self.editor.clear_grammar_issue_lines()
            status_message = self.translator.text("grammar_check.no_issues")
            self.statusBar().showMessage(status_message)
            self._save_grammar_lint_result(
                self.editor,
                source_text=source_text,
                summary=status_message,
                rows=[],
                issue_lines=[],
            )
            self._show_grammar_check_dialog_for_editor(
                self.editor,
                status_message,
                [],
            )
            return

        sorted_messages = self._sort_grammar_messages(messages)
        self._set_grammar_issue_highlights(sorted_messages)
        self._set_cursor_to_line(sorted_messages[0].line_number)
        status_message = self.translator.text(
            "grammar_check.issues_found_with_severity",
            count=len(sorted_messages),
            details=self._grammar_severity_count_text(sorted_messages),
        )
        self.statusBar().showMessage(status_message)
        rows = [
            (message.line_number, self._grammar_lint_message_text(message))
            for message in sorted_messages
        ]
        self._save_grammar_lint_result(
            self.editor,
            source_text=source_text,
            summary=status_message,
            rows=rows,
            issue_lines=[message.line_number for message in sorted_messages],
        )
        self._show_grammar_check_dialog_for_editor(
            self.editor,
            status_message,
            rows,
        )

    def _source_hash(self, source_text: str) -> str:
        return sha256(source_text.encode("utf-8")).hexdigest()

    def _lint_document(self, source_text: str) -> list[GrammarLintMessage]:
        messages: list[GrammarLintMessage] = []
        if (
            self.current_save_file_path is not None
            and self.current_save_file_path.suffix.lower() == ".css"
        ):
            messages.extend(lint_stylesheet(source_text))
        else:
            messages.extend(lint_html_typos(source_text))
        return messages

    def _sort_grammar_messages(
        self,
        messages: list[GrammarLintMessage],
    ) -> list[GrammarLintMessage]:
        """Show more serious grammar findings first, then keep line order."""
        return sorted(
            messages,
            key=lambda message: (
                GRAMMAR_SEVERITY_ORDER.get(message.severity, 99),
                message.line_number,
                message.message_key,
            ),
        )

    def _grammar_result_path_for_editor(self, editor: TextEditor) -> Path:
        result_path = self.tab_grammar_result_paths.get(editor)
        if result_path is None:
            result_path = self.grammar_lint_result_store.create_result_path(
                self.window_id,
                uuid.uuid4().hex,
            )
            self.tab_grammar_result_paths[editor] = result_path
        return result_path

    def _save_grammar_lint_result(
        self,
        editor: TextEditor,
        *,
        source_text: str,
        summary: str,
        rows: list[tuple[int, str]],
        issue_lines: list[int],
    ) -> None:
        result_path = self._grammar_result_path_for_editor(editor)
        self.grammar_lint_result_store.save(
            result_path,
            GrammarLintResult(
                summary=summary,
                rows=rows,
                issue_lines=issue_lines,
                source_hash=self._source_hash(source_text),
                document_label=self._grammar_document_label(editor),
                save_file_path=self.tab_file_paths.get(editor),
                checked_at=datetime.now(timezone.utc),
            ),
        )

    def _load_current_grammar_lint_result(self) -> GrammarLintResult | None:
        editor = self._current_editor()
        if editor is None:
            return None
        result_path = self.tab_grammar_result_paths.get(editor)
        if result_path is None:
            return None
        result = self.grammar_lint_result_store.load(result_path)
        if result is None:
            return None
        if result.source_hash != self._source_hash(editor.toPlainText()):
            return None
        return result

    def _invalidate_grammar_lint_result(self, editor: TextEditor) -> None:
        self._delete_grammar_lint_result(editor)
        if editor is self._current_editor() and self.grammar_check_dialog is not None:
            self._set_grammar_check_dialog_document_label(editor)
            self.grammar_check_dialog.set_result(
                self.translator.text("grammar_check.not_checked"),
                [],
            )

    def _delete_grammar_lint_result(self, editor: TextEditor) -> None:
        result_path = self.tab_grammar_result_paths.get(editor)
        if result_path is not None:
            self.grammar_lint_result_store.delete(result_path)

    def _clear_grammar_lint_results_on_window_close(self) -> None:
        for result_path in list(self.tab_grammar_result_paths.values()):
            self.grammar_lint_result_store.delete(result_path)
        self.tab_grammar_result_paths.clear()

        if not self._other_main_windows_are_open():
            self.grammar_lint_result_store.clear_result_folder()

    def _other_main_windows_are_open(self) -> bool:
        application = QApplication.instance()
        if not isinstance(application, QApplication):
            return False
        return any(
            isinstance(widget, MainWindow) and widget is not self and widget.isVisible()
            for widget in application.topLevelWidgets()
        )

    def _refresh_grammar_dialog_for_current_tab(self) -> None:
        if self.grammar_check_dialog is None or not self.grammar_check_dialog.isVisible():
            return

        result = self._load_current_grammar_lint_result()
        current_editor = self._current_editor()
        if result is None or current_editor is None:
            if current_editor is not None:
                current_editor.clear_grammar_issue_lines()
                self._set_grammar_check_dialog_document_label(current_editor)
            self.grammar_check_dialog.set_result(
                self.translator.text("grammar_check.not_checked"),
                [],
            )
            return

        current_editor.set_grammar_issue_lines(result.issue_lines)
        self._set_grammar_check_dialog_document_label(current_editor)
        self.grammar_check_dialog.set_result(result.summary, result.rows)

    def _grammar_document_label(self, editor: TextEditor) -> str:
        save_file_path = self.tab_file_paths.get(editor)
        if save_file_path is not None:
            return save_file_path.name
        return self._draft_title(editor)

    def _set_grammar_check_dialog_document_label(self, editor: TextEditor) -> None:
        if self.grammar_check_dialog is not None:
            self.grammar_check_dialog.set_document_label(
                self._grammar_document_label(editor)
            )

    def _show_grammar_check_dialog_for_editor(
        self,
        editor: TextEditor,
        summary: str,
        rows: list[tuple[int, str]],
    ) -> None:
        self._show_grammar_check_dialog(summary, rows)
        self._set_grammar_check_dialog_document_label(editor)

    def _show_grammar_check_dialog(
        self,
        summary: str,
        rows: list[tuple[int, str]],
    ) -> None:
        if self.grammar_check_dialog is None:
            self.grammar_check_dialog = GrammarCheckDialog(self.translator, self)
            self.grammar_check_dialog.line_selected.connect(self._set_cursor_to_line)
            self.grammar_check_dialog.refresh_requested.connect(self.run_grammar_check)
            self.grammar_check_dialog.dismissed.connect(
                self._clear_grammar_issue_highlights
            )
        self.grammar_check_dialog.set_result(summary, rows)
        self.grammar_check_dialog.show()
        self.grammar_check_dialog.raise_()
        self.grammar_check_dialog.activateWindow()

    def _confirm_save_after_grammar_check(self, save_data: str) -> bool:
        if not self.html_typo_lint_enabled:
            return True

        messages = self._lint_document(save_data)
        if not messages or all(message.severity == "info" for message in messages):
            self.editor.clear_grammar_issue_lines()
            return True

        sorted_messages = self._sort_grammar_messages(messages)
        self._set_grammar_issue_highlights(sorted_messages)
        self._set_cursor_to_line(sorted_messages[0].line_number)
        summary = self._grammar_check_summary(sorted_messages)
        try:
            result = QMessageBox.question(
                self,
                self.translator.text("grammar_check.save_warning.title"),
                "\n\n".join(
                    (
                        self.translator.text("grammar_check.save_warning.message"),
                        summary,
                    )
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
        finally:
            self.editor.clear_grammar_issue_lines()
        return result == QMessageBox.StandardButton.Yes

    def _set_grammar_issue_highlights(
        self,
        messages: list[GrammarLintMessage],
    ) -> None:
        self.editor.set_grammar_issue_lines(
            [message.line_number for message in messages]
        )

    def _clear_grammar_issue_highlights(self) -> None:
        self.editor.clear_grammar_issue_lines()

    def _grammar_check_summary(
        self,
        messages: list[GrammarLintMessage],
        limit: int = 20,
    ) -> str:
        shown_messages = messages[:limit]
        rows = [
            self.translator.text(
                "grammar_check.issues_found_with_severity",
                count=len(messages),
                details=self._grammar_severity_count_text(messages),
            ),
            "",
        ]
        rows.extend(
            self.translator.text(
                "grammar_check.issue_row",
                line=message.line_number,
                message=self._grammar_lint_message_text(message),
            )
            for message in shown_messages
        )
        if len(messages) > limit:
            rows.append("")
            rows.append(
                self.translator.text(
                    "grammar_check.more_issues",
                    count=len(messages) - limit,
                )
            )
        return "\n".join(rows)

    def _grammar_lint_message_text(self, message: GrammarLintMessage) -> str:
        severity_label = self.translator.text(
            f"grammar_check.severity.{message.severity}"
        )
        return (
            f"{severity_label} "
            f"{self._html_typo_lint_message_text(message)}"
        )

    def _grammar_severity_count_text(
        self,
        messages: list[GrammarLintMessage],
    ) -> str:
        counts = {"error": 0, "warning": 0, "info": 0}
        for message in messages:
            if message.severity in counts:
                counts[message.severity] += 1
        return self.translator.text(
            "grammar_check.severity_counts",
            error=counts["error"],
            warning=counts["warning"],
            info=counts["info"],
        )

    def _html_typo_lint_message_text(self, message: GrammarLintMessage) -> str:
        values = message.values or {}
        if message.message_key == "html_typo_lint.unknown_wordpress_block":
            suggestion = values.get("suggestion")
            if suggestion:
                return self.translator.text(
                    "html_typo_lint.unknown_wordpress_block_with_suggestion",
                    block=values.get("block", ""),
                    suggestion=suggestion,
                )
            return self.translator.text(
                "html_typo_lint.unknown_wordpress_block",
                block=values.get("block", ""),
            )
        if message.message_key == "html_typo_lint.unknown_html_tag":
            suggestion = values.get("suggestion")
            if suggestion:
                return self.translator.text(
                    "html_typo_lint.unknown_html_tag_with_suggestion",
                    tag=values.get("tag", ""),
                    suggestion=suggestion,
                )
            return self.translator.text(
                "html_typo_lint.unknown_html_tag",
                tag=values.get("tag", ""),
            )
        if message.message_key == "html_typo_lint.unknown_html_attribute":
            suggestion = values.get("suggestion")
            if suggestion:
                return self.translator.text(
                    "html_typo_lint.unknown_html_attribute_with_suggestion",
                    tag=values.get("tag", ""),
                    attribute=values.get("attribute", ""),
                    suggestion=suggestion,
                )
            return self.translator.text(
                "html_typo_lint.unknown_html_attribute",
                tag=values.get("tag", ""),
                attribute=values.get("attribute", ""),
            )
        if message.message_key == "html_typo_lint.unknown_wordpress_block_attribute":
            suggestion = values.get("suggestion")
            if suggestion:
                return self.translator.text(
                    "html_typo_lint.unknown_wordpress_block_attribute_with_suggestion",
                    block=values.get("block", ""),
                    attribute=values.get("attribute", ""),
                    suggestion=suggestion,
                )
            return self.translator.text(
                "html_typo_lint.unknown_wordpress_block_attribute",
                block=values.get("block", ""),
                attribute=values.get("attribute", ""),
            )
        if (
            message.message_key
            == "html_typo_lint.invalid_wordpress_block_attribute_value"
        ):
            suggestion = values.get("suggestion")
            if suggestion:
                return self.translator.text(
                    "html_typo_lint.invalid_wordpress_block_attribute_value_with_suggestion",
                    block=values.get("block", ""),
                    attribute=values.get("attribute", ""),
                    allowed_values=values.get("allowed_values", ""),
                    actual_value=values.get("actual_value", ""),
                    suggestion=suggestion,
                )
        return self.translator.text(message.message_key, **values)

    def _set_cursor_to_line(self, line_number: int) -> None:
        """Move the cursor to the start of the given one-based line number."""
        block = self.editor.document().findBlockByNumber(max(0, line_number - 1))
        if not block.isValid():
            return
        cursor = self.editor.textCursor()
        cursor.setPosition(block.position())
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def insert_tag_snippet(self, snippet: TagSnippet) -> None:
        """Insert the given tag snippet into the current editor at the cursor position."""
        cursor = self.editor.textCursor()
        insert_start = cursor.selectionStart()
        selected_text = cursor.selectedText().replace("\u2029", "\n")
        insert_text, cursor_offset = self._render_tag_snippet(snippet, selected_text)

        cursor.beginEditBlock()
        cursor.insertText(insert_text)
        cursor.endEditBlock()
        cursor.setPosition(insert_start + cursor_offset)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def wrap_selection_with_inline_html(self, opening_tag: str, closing_tag: str) -> None:
        cursor = self.editor.textCursor()
        insert_start = cursor.selectionStart()
        selected_text = cursor.selectedText().replace("\u2029", "\n")
        insert_text = f"{opening_tag}{selected_text}{closing_tag}"

        cursor.beginEditBlock()
        cursor.insertText(insert_text)
        cursor.endEditBlock()
        cursor.setPosition(insert_start + len(opening_tag) + len(selected_text))
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def insert_paragraph_split_spacer(self) -> None:
        """Split the current paragraph and insert a WordPress spacer block."""
        self._apply_paragraph_split_operation(
            lambda text, start, _end: split_paragraph_insert_spacer(
                text,
                start,
                self._tag_dictionaries_path(),
            )
        )

    def insert_paragraph_split_html(self) -> None:
        """Split the current paragraph and wrap the selection as an HTML code block."""
        self._apply_paragraph_split_operation(
            lambda text, start, end: wrap_selection_as_code_block(
                text,
                start,
                end,
                self._tag_dictionaries_path(),
            )
        )

    def wrap_paragraph_split_decorated_block(self) -> None:
        """Split the current paragraph and wrap the selection as a decorated block."""
        self._apply_paragraph_split_operation(
            lambda text, start, end: wrap_selection_as_decorated_block(
                text,
                start,
                end,
                self._tag_dictionaries_path(),
            )
        )

    def _apply_paragraph_split_operation(
        self,
        operation: Callable[[str, int, int], ParagraphReplacement],
    ) -> None:
        cursor = self.editor.textCursor()
        text = self.editor.toPlainText()
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        try:
            replacement = operation(text, selection_start, selection_end)
        except ParagraphSplitError as error:
            QMessageBox.warning(
                self,
                self.translator.text("paragraph_split.error_title"),
                self.translator.text(error.message_key, **error.values),
            )
            return

        edit_cursor = self.editor.textCursor()
        edit_cursor.beginEditBlock()
        edit_cursor.setPosition(0)
        edit_cursor.setPosition(len(text), QTextCursor.MoveMode.KeepAnchor)
        edit_cursor.insertText(replacement.text)
        edit_cursor.endEditBlock()
        edit_cursor.setPosition(replacement.cursor_position)
        self.editor.setTextCursor(edit_cursor)
        self.editor.setFocus()

    def _render_tag_snippet(
        self,
        snippet: TagSnippet,
        selected_text: str,
    ) -> tuple[str, int]:
        if snippet.label_key not in FRAME_BLOCK_LABEL_KEYS:
            return snippet.render(selected_text)

        adjusted_template = self._frame_block_template_for_settings(snippet.template)
        return TagSnippet(
            snippet.label_key,
            snippet.hint_key,
            adjusted_template,
            snippet.parameters,
            snippet.default_selection,
        ).render(selected_text)

    def _frame_block_template_for_settings(self, template: str) -> str:
        style_marker = '<div style="'
        div_start = template.find(style_marker)
        if div_start == -1:
            return template

        style_start = div_start + len(style_marker)
        style_end = template.find('">', style_start)
        if style_end == -1:
            return template

        original_style = template[style_start:style_end]
        original_body_start = style_end + len('">')
        original_close_start = template.rfind("\n</div>\n<!-- /wp:html -->")
        if original_close_start == -1 or original_close_start <= original_body_start:
            return template

        alignment = self._frame_alignment_value()
        inner_style = self._frame_inner_style(original_style)
        outer_open = (
            f'<div style="text-align: {alignment}; '
            f'margin: {self._frame_outer_spacing_value()};">\n'
            f'<div style="{inner_style}">'
        )
        return (
            template[:div_start]
            + outer_open
            + template[original_body_start:original_close_start]
            + "\n</div>"
            + template[original_close_start:]
        )

    def _frame_inner_style(self, original_style: str) -> str:
        display_style = FRAME_DISPLAY_STYLES.get(
            self.frame_display,
            FRAME_DISPLAY_STYLES["inline-block"],
        )
        preserved_parts = [
            part
            for part in _split_style_parts(original_style)
            if not part.lower().startswith(FRAME_STYLE_PREFIXES_REPLACED_BY_SETTINGS)
        ]
        style_parts = [
            *_split_style_parts(display_style),
            *preserved_parts,
            f"background-color: {self._frame_background_color_value()}",
            f"color: {self._frame_text_color_value()}",
            "text-align: left",
        ]
        return "; ".join(style_parts) + ";"

    def _frame_alignment_value(self) -> str:
        if self.frame_alignment in FRAME_ALIGNMENT_VALUES:
            return self.frame_alignment
        return "left"

    def _frame_outer_spacing_value(self) -> str:
        if self.frame_outer_spacing.strip():
            return self.frame_outer_spacing.strip()
        return DEFAULT_FRAME_OUTER_SPACING

    def _frame_background_color_value(self) -> str:
        if self.frame_background_color.strip():
            return self.frame_background_color.strip()
        return "#fffaf0"

    def _frame_text_color_value(self) -> str:
        if self.frame_text_color.strip():
            return self.frame_text_color.strip()
        return "#333333"

    def insert_text_at_cursor(
        self,
        insert_text: str,
        cursor_offset: int | None = None,
    ) -> None:
        """Insert fixed text into the current editor at the cursor position."""
        cursor = self.editor.textCursor()
        insert_start = cursor.selectionStart()
        cursor.beginEditBlock()
        cursor.insertText(insert_text)
        cursor.endEditBlock()
        if cursor_offset is not None:
            cursor.setPosition(insert_start + cursor_offset)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def insert_style_attribute_at_cursor(self) -> None:
        """Insert style="" inside the nearest opening tag when possible."""
        source_text = self.editor.toPlainText()
        cursor = self.editor.textCursor()
        tag_bounds = self._opening_tag_bounds_near_cursor(source_text, cursor.position())
        if tag_bounds is None:
            self.insert_text_at_cursor('style=""', len('style="'))
            return

        _tag_start, tag_end = tag_bounds
        insert_position = tag_end - 1
        prefix = "" if source_text[insert_position - 1].isspace() else " "
        insert_text = f'{prefix}style=""'
        self._insert_text_at_position(
            insert_position,
            insert_text,
            len(prefix) + len('style="'),
        )

    def insert_css_declaration_at_cursor(
        self,
        declaration_text: str,
        cursor_offset: int,
    ) -> None:
        """Insert a CSS declaration in the nearest style attribute when possible."""
        source_text = self.editor.toPlainText()
        cursor = self.editor.textCursor()
        cursor_position = cursor.position()
        style_bounds = self._style_attribute_value_bounds_near_cursor(
            source_text,
            cursor_position,
        )
        if style_bounds is not None:
            value_start, value_end = style_bounds
            insert_position = (
                cursor_position
                if value_start <= cursor_position <= value_end
                else value_end
            )
            insert_text = self._css_declaration_insert_text(
                source_text,
                insert_position,
                value_start,
                value_end,
                declaration_text,
            )
            self._insert_text_at_position(
                insert_position,
                insert_text,
                insert_text.find(";") if ";" in insert_text else cursor_offset,
            )
            return

        tag_bounds = self._opening_tag_bounds_near_cursor(source_text, cursor_position)
        if tag_bounds is not None:
            _tag_start, tag_end = tag_bounds
            insert_text = f' style="{declaration_text}"'
            self._insert_text_at_position(
                tag_end - 1,
                insert_text,
                insert_text.find(";") if ";" in insert_text else cursor_offset,
            )
            return

        self.insert_text_at_cursor(declaration_text, cursor_offset)

    def insert_background_color_at_cursor(self) -> None:
        """Insert an editable background color declaration and show recommended colors."""
        self.insert_css_declaration_at_cursor(
            "background-color: ;",
            len("background-color: "),
        )
        self._show_background_color_preset_menu()

    def insert_text_color_at_cursor(self) -> None:
        """Insert an editable text color declaration and show text color choices."""
        self.insert_css_declaration_at_cursor("color: ;", len("color: "))
        self._show_text_color_preset_menu()

    def _show_background_color_preset_menu(self) -> None:
        """Show recommended WordPress background colors below the current cursor."""
        menu = QMenu(self.editor)
        for preset in self.color_presets.background_colors:
            action = QAction(
                f"{preset.display_name(self.translator.language_code)}  {preset.value}",
                menu,
            )
            action.setData(preset.value)
            action.setIcon(self._background_color_swatch_icon(preset.value))
            action.triggered.connect(
                lambda checked=False, value=preset.value: self._replace_background_color_value(
                    value
                )
            )
            menu.addAction(action)
        self.background_color_preset_menu = menu
        cursor_rect = self.editor.cursorRect()
        menu.popup(self.editor.viewport().mapToGlobal(cursor_rect.bottomLeft()))

    def _show_text_color_preset_menu(self) -> None:
        """Show the same text colors used by the Ctrl+Alt inline shortcuts."""
        menu = QMenu(self.editor)
        for preset in self.color_presets.text_colors:
            action = QAction(
                f"{preset.display_name(self.translator.language_code)}  {preset.value}",
                menu,
            )
            action.setData(preset.value)
            action.setIcon(self._background_color_swatch_icon(preset.value))
            action.triggered.connect(
                lambda checked=False, value=preset.value: self._replace_css_color_value(
                    "color",
                    value,
                )
            )
            menu.addAction(action)
        self.text_color_preset_menu = menu
        cursor_rect = self.editor.cursorRect()
        menu.popup(self.editor.viewport().mapToGlobal(cursor_rect.bottomLeft()))

    def _inline_color_action_text(self, preset: ColorPreset) -> str:
        """Return a localized inline-color action label from the editable JSON."""
        color_name = preset.display_name(self.translator.language_code)
        return (
            f"{color_name} Text <span>"
            if self.translator.language_code == "en"
            else f"{color_name}文字 <span>"
        )

    @staticmethod
    def _background_color_swatch_icon(color_value: str) -> QIcon:
        """Create a small color swatch for a recommended background color."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(color_value))
        return QIcon(pixmap)

    def _replace_background_color_value(self, color_value: str) -> None:
        """Replace the background-color value containing the editor cursor."""
        self._replace_css_color_value("background-color", color_value)

    def _replace_css_color_value(self, property_name: str, color_value: str) -> None:
        """Replace the current CSS color property value without altering its semicolon."""
        source_text = self.editor.toPlainText()
        cursor = self.editor.textCursor()
        cursor_position = cursor.position()
        property_pattern = re.escape(property_name)
        for match in re.finditer(rf"{property_pattern}\s*:\s*([^;\n]*)", source_text):
            value_start, value_end = match.span(1)
            if value_start <= cursor_position <= value_end:
                cursor.beginEditBlock()
                cursor.setPosition(value_start)
                cursor.setPosition(value_end, QTextCursor.MoveMode.KeepAnchor)
                cursor.insertText(color_value)
                cursor.endEditBlock()
                cursor.setPosition(value_start + len(color_value))
                self.editor.setTextCursor(cursor)
                self.editor.setFocus()
                return

    def _insert_text_at_position(
        self,
        insert_position: int,
        insert_text: str,
        cursor_offset: int | None = None,
    ) -> None:
        """Insert fixed text at an absolute editor position."""
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        cursor.setPosition(insert_position)
        cursor.insertText(insert_text)
        cursor.endEditBlock()
        if cursor_offset is not None:
            cursor.setPosition(insert_position + cursor_offset)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _opening_tag_bounds_near_cursor(
        self,
        source_text: str,
        cursor_position: int,
    ) -> tuple[int, int] | None:
        """Return the nearest same-line opening tag around the cursor."""
        line_start = source_text.rfind("\n", 0, cursor_position) + 1
        line_end = source_text.find("\n", cursor_position)
        if line_end == -1:
            line_end = len(source_text)
        line_text = source_text[line_start:line_end]
        for match in re.finditer(r"<(?!/|!|\?)[A-Za-z][^<>\n]*>", line_text):
            tag_start = line_start + match.start()
            tag_end = line_start + match.end()
            if tag_start <= cursor_position <= tag_end:
                return tag_start, tag_end
        return None

    def _style_attribute_value_bounds_near_cursor(
        self,
        source_text: str,
        cursor_position: int,
    ) -> tuple[int, int] | None:
        """Return value bounds for a style attribute in the nearest opening tag."""
        tag_bounds = self._opening_tag_bounds_near_cursor(
            source_text,
            cursor_position,
        )
        if tag_bounds is None:
            return None
        tag_start, tag_end = tag_bounds
        tag_text = source_text[tag_start:tag_end]
        style_match = re.search(r"\sstyle\s*=\s*([\"'])(.*?)\1", tag_text)
        if style_match is None:
            return None
        value_start = tag_start + style_match.start(2)
        value_end = tag_start + style_match.end(2)
        return value_start, value_end

    def _css_declaration_insert_text(
        self,
        source_text: str,
        insert_position: int,
        value_start: int,
        value_end: int,
        declaration_text: str,
    ) -> str:
        """Return a CSS declaration with spacing suited to the target style value."""
        if value_start == value_end:
            return declaration_text
        needs_leading_space = (
            insert_position > value_start
            and source_text[insert_position - 1] not in {" ", "\t", ";", "\n"}
        )
        needs_trailing_space = (
            insert_position < value_end
            and source_text[insert_position] not in {" ", "\t", ";", "\n"}
        )
        return (
            (" " if needs_leading_space else "")
            + declaration_text
            + (" " if needs_trailing_space else "")
        )

    def escape_selected_html(self) -> None:
        """HTML-escape only the selected text, preserving quote characters."""
        self._replace_selected_text(
            lambda selected_text: escape(selected_text, quote=False)
        )

    def unescape_selected_html(self) -> None:
        """HTML-unescape only the selected text."""
        self._replace_selected_text(unescape)

    def wrap_selected_as_wordpress_code_block(self) -> None:
        """Wrap the selected text in a WordPress custom HTML code block."""

        def build_wordpress_code_block(selected_text: str) -> str:
            escaped_text = escape(selected_text, quote=False)
            return (
                "<!-- wp:html -->\n"
                "<pre\n"
                '    class="wp-block-code"\n'
                '    style="display: inline-block; border: 1px solid #999; '
                "padding: 16px; border-radius: 8px; "
                'background-color: #f9f9f9;"\n'
                f"><code>{escaped_text}</code></pre>\n"
                "<!-- /wp:html -->"
            )

        self._replace_selected_text(build_wordpress_code_block)

    def convert_selected_markdown_blocks_to_wordpress_blocks(self) -> None:
        """Convert selected Markdown table/list blocks to WordPress blocks."""
        self._convert_selected_markdown_to_wordpress(
            convert_complex_markdown_blocks_to_wordpress_html
        )

    def convert_selected_markdown_tables_to_wordpress_tables(self) -> None:
        """Convert selected Markdown table blocks to WordPress table blocks."""
        self._convert_selected_markdown_to_wordpress(
            convert_markdown_tables_to_wordpress_html
        )

    def convert_selected_markdown_lists_to_wordpress_lists(self) -> None:
        """Convert selected Markdown list blocks to WordPress list blocks."""
        self._convert_selected_markdown_to_wordpress(
            convert_markdown_lists_to_wordpress_html
        )

    def convert_selected_list_to_wordpress_frame(self) -> None:
        """Convert selected Markdown or WordPress list content to one HTML frame."""
        self._convert_selected_markdown_to_wordpress(
            lambda source_text: convert_list_to_wordpress_frame_html(
                source_text,
                alignment=self._frame_alignment_value(),
                outer_spacing=self._frame_outer_spacing_value(),
                inner_style=self._frame_inner_style(DEFAULT_LIST_FRAME_STYLE),
            )
        )

    def _convert_selected_markdown_to_wordpress(
        self,
        converter: Callable[[str], str],
    ) -> None:
        """Convert the current Markdown selection to WordPress block HTML."""
        try:
            self._replace_selected_markdown_text(converter)
        except WordPressMarkdownConversionError as error:
            self.statusBar().showMessage(
                self.translator.text(
                    "status.wordpress_complex_blocks_conversion_failed",
                    error=str(error),
                )
            )

    def _replace_selected_markdown_text(self, transform: Callable[[str], str]) -> None:
        """Replace selected Markdown, avoiding nested WordPress paragraph blocks."""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            self.statusBar().showMessage(self.translator.text("status.select_text"))
            return

        source_text = self.editor.toPlainText()
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        paragraph_block = find_current_paragraph_block(source_text, selection_start)
        if paragraph_block is None:
            self._replace_selected_text(transform)
            return

        replacement_range = self._wordpress_paragraph_replacement_range(
            source_text,
            paragraph_block,
            selection_start,
            selection_end,
        )
        if replacement_range is None:
            self.statusBar().showMessage(
                self.translator.text("status.wordpress_paragraph_nested_conversion")
            )
            return

        replacement_start, replacement_end = replacement_range
        selected_text = source_text[selection_start:selection_end]
        insert_text = transform(selected_text)
        cursor.beginEditBlock()
        cursor.setPosition(replacement_start)
        cursor.setPosition(replacement_end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(insert_text)
        cursor.endEditBlock()
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _wordpress_paragraph_replacement_range(
        self,
        source_text: str,
        paragraph_block: ParagraphBlock,
        selection_start: int,
        selection_end: int,
    ) -> tuple[int, int] | None:
        """Return a whole paragraph block range when the content is fully selected."""
        if selection_end <= selection_start:
            return None
        if (
            selection_start < paragraph_block.content_start
            or selection_end > paragraph_block.content_end
        ):
            return None

        before_selection = source_text[paragraph_block.content_start : selection_start]
        after_selection = source_text[selection_end : paragraph_block.content_end]
        if before_selection.strip() or after_selection.strip():
            return None
        return paragraph_block.block_start, paragraph_block.block_end

    def _replace_selected_text(self, transform: Callable[[str], str]) -> None:
        """Replace the current selection with transformed text if text is selected."""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            self.statusBar().showMessage(self.translator.text("status.select_text"))
            return

        selected_text = cursor.selectedText().replace("\u2029", "\n")
        insert_text = transform(selected_text)
        cursor.beginEditBlock()
        cursor.insertText(insert_text)
        cursor.endEditBlock()
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _update_status_bar(self) -> None:
        """Update the status bar with the current cursor position and character count."""
        cursor = self.editor.textCursor()
        line_number = cursor.blockNumber() + 1
        column_number = cursor.positionInBlock() + 1
        character_count = len(self.editor.toPlainText())
        self.statusBar().showMessage(
            self.translator.text(
                "status.position",
                line=line_number,
                column=column_number,
                characters=character_count,
            )
        )

    def _update_window_title(self) -> None:
        """Update the main window title to reflect the current document name and modification status."""
        load_file_path = self.current_save_file_path
        document_name = (
            load_file_path.name
            if load_file_path
            else self.translator.text("document.untitled")
        )
        changed_mark = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(
            f"{changed_mark}{document_name} - {self.translator.text('app.title')}"
        )

    def _confirm_discard_changes(self) -> bool:
        """Autosave unsaved changes before continuing with a risky operation."""
        if not self.editor.document().isModified():
            return True
        return self._autosave_before_risky_operation()

    def _confirm_reload_current_file(self) -> bool:
        """Confirm reloading when it would replace unsaved editor text."""
        if not self.editor.document().isModified():
            return True
        if not self._autosave_before_risky_operation():
            return False

        result = QMessageBox.question(
            self,
            self.translator.text("dialog.reload_confirm.title"),
            self.translator.text("dialog.reload_confirm.message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def _confirm_save_or_discard_editor(self, editor: TextEditor) -> bool:
        """Autosave tab changes before allowing the tab to be closed."""
        if not editor.document().isModified():
            return True

        tab_index = self.tab_widget.indexOf(editor)
        if tab_index >= 0:
            self.tab_widget.setCurrentIndex(tab_index)
        return self._autosave_before_risky_operation()

    def new_file(self) -> None:
        """Create a new editor tab with an untitled document."""
        self._create_editor_tab()
        self._update_window_title()

    def open_file(self, encoding: str | None = None) -> None:
        """Open a file dialog to select and load a text file into a new editor tab."""
        if not self._autosave_before_risky_operation():
            return
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translator.text("dialog.open.title"),
        )
        if not selected_path:
            return

        load_file_path = Path(selected_path)
        selected_encoding = encoding or self.default_encoding
        try:
            load_data = self.file_manager.load_text(load_file_path, selected_encoding)
        except (OSError, UnicodeError) as error:
            QMessageBox.critical(
                self,
                self.translator.text("dialog.open_failed.title"),
                str(error),
            )
            return

        editor = self._create_editor_tab(
            text=load_data,
            save_file_path=load_file_path,
            encoding=selected_encoding,
            modified=False,
        )
        editor.moveCursor(QTextCursor.MoveOperation.Start)
        self._set_current_file_state(load_file_path, selected_encoding)
        self._save_unsaved_backup()
        self._update_window_title()
        self._set_encoding_status()

    def reload_file(self, encoding: str | None = None) -> None:
        """Reload the current file from disk, optionally using a specified encoding."""
        if self.current_save_file_path is None:
            self._set_search_error(self.translator.text("dialog.reload_no_file"))
            return
        if not self._confirm_reload_current_file():
            return

        selected_encoding = encoding or self.current_encoding
        try:
            load_data = self.file_manager.load_text(
                self.current_save_file_path,
                selected_encoding,
            )
        except (OSError, UnicodeError) as error:
            QMessageBox.critical(
                self,
                self.translator.text("dialog.reload_failed.title"),
                self.translator.text(
                    "dialog.encoding_failed",
                    encoding=selected_encoding,
                    error=error,
                ),
            )
            return

        self.current_encoding = selected_encoding
        self.editor.setPlainText(load_data)
        self.editor.moveCursor(QTextCursor.MoveOperation.Start)
        self.editor.document().setModified(False)
        self._set_current_file_state(self.current_save_file_path, selected_encoding)
        self._save_unsaved_backup()
        self._update_window_title()
        self._set_encoding_status()

    def save_file(self) -> bool:
        """Save the current file, returning True if successful."""
        if self.current_save_file_path is None:
            return self.save_file_as()
        return self._save_to_path(self.current_save_file_path)

    def save_file_as(self) -> bool:
        """Prompt the user to select a save location and save the current file, returning True if successful."""
        selected_save_file_path, selected_encoding = self._get_save_file_path()
        if selected_save_file_path is None:
            return False
        self.current_encoding = selected_encoding
        return self._save_to_path(selected_save_file_path)

    def _get_save_file_path(self) -> tuple[Path | None, str]:
        """Show the save file dialog and return the selected file path and encoding."""
        dialog = QFileDialog(self, self.translator.text("dialog.save_as.title"))
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.selectFile(
            self.current_save_file_path.name if self.current_save_file_path else ""
        )

        encoding_combo_box = QComboBox(dialog)
        for label, encoding in ENCODING_OPTIONS.items():
            encoding_combo_box.addItem(label, encoding)
        current_encoding_index = encoding_combo_box.findData(self.current_encoding)
        if current_encoding_index >= 0:
            encoding_combo_box.setCurrentIndex(current_encoding_index)

        encoding_layout = QHBoxLayout()
        encoding_layout.addWidget(QLabel(self.translator.text("dialog.save_encoding")))
        encoding_layout.addWidget(encoding_combo_box)

        dialog_layout = dialog.layout()
        if isinstance(dialog_layout, QVBoxLayout):
            dialog_layout.addLayout(encoding_layout)
        elif dialog_layout is not None:
            dialog_layout.addWidget(QLabel(self.translator.text("dialog.save_encoding")))
            dialog_layout.addWidget(encoding_combo_box)

        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return None, self.current_encoding

        selected_files = dialog.selectedFiles()
        if not selected_files:
            return None, self.current_encoding

        return Path(selected_files[0]), str(encoding_combo_box.currentData())

    def _save_to_path(self, save_file_path: Path) -> bool:
        """Save the current editor content to the specified file path, returning True if successful."""
        save_data = self.editor.toPlainText()
        if not self._confirm_save_after_grammar_check(save_data):
            return False

        try:
            self.file_backup_manager.backup_existing_file(
                save_file_path,
                retention_count=self.backup_retention_count,
                retention_days=self.backup_retention_days,
            )
            self.file_manager.save_text(
                save_file_path,
                save_data,
                self.current_encoding,
                self.newline_code,
            )
        except OSError as error:
            QMessageBox.critical(
                self,
                self.translator.text("dialog.save_failed.title"),
                str(error),
            )
            return False

        self._set_current_file_state(save_file_path, self.current_encoding)
        self.editor.document().setModified(False)
        self._save_unsaved_backup()
        self._update_window_title()
        return True

    def restore_file_backup(self) -> None:
        """Restore a saved-file backup or unsaved auto-backup snapshot."""
        restore_choices: list[tuple[str, Path, str]] = []
        if self.current_save_file_path is not None:
            for backup_path in self.file_backup_manager.backups_for_file(
                self.current_save_file_path
            ):
                restore_choices.append(
                    (
                        "file",
                        backup_path,
                        self._file_backup_label(backup_path),
                    )
                )

        if self.unsaved_backup_enabled:
            if self.unsaved_backup_manager.load_session() is not None:
                restore_choices.append(
                    (
                        "unsaved",
                        self.unsaved_backup_manager.backup_path,
                        self._unsaved_backup_label(
                            self.unsaved_backup_manager.backup_path,
                            "dialog.file_backup_restore.unsaved_latest_item",
                        ),
                    )
                )
            for snapshot_path in self.unsaved_backup_manager.history_snapshots():
                if self.unsaved_backup_manager.load_session_from_path(snapshot_path):
                    restore_choices.append(
                        (
                            "unsaved",
                            snapshot_path,
                            self._unsaved_backup_label(
                                snapshot_path,
                                "dialog.file_backup_restore.unsaved_history_item",
                            ),
                        )
                    )

        if not restore_choices:
            QMessageBox.information(
                self,
                self.translator.text("dialog.file_backup_restore.title"),
                self.translator.text("dialog.file_backup_restore.no_backup"),
            )
            return

        backup_labels = [label for _kind, _path, label in restore_choices]
        selected_label, accepted = QInputDialog.getItem(
            self,
            self.translator.text("dialog.file_backup_restore.title"),
            self.translator.text("dialog.file_backup_restore.message"),
            backup_labels,
            0,
            False,
        )
        if not accepted:
            return
        try:
            backup_kind, backup_path, _label = restore_choices[
                backup_labels.index(selected_label)
            ]
        except ValueError:
            return

        if not self._confirm_discard_changes():
            return

        if backup_kind == "unsaved":
            session = self.unsaved_backup_manager.load_session_from_path(backup_path)
            if session is None:
                QMessageBox.critical(
                    self,
                    self.translator.text("dialog.file_backup_restore.failed_title"),
                    self.translator.text(
                        "dialog.file_backup_restore.unsaved_failed"
                    ),
                )
                return
            self._restore_unsaved_backup_session(session)
            self._save_unsaved_backup_snapshot()
            self.statusBar().showMessage(
                self.translator.text("dialog.file_backup_restore.restored_unsaved")
            )
            return

        try:
            load_data = self.file_manager.load_text(backup_path, self.current_encoding)
        except (OSError, UnicodeError) as error:
            QMessageBox.critical(
                self,
                self.translator.text("dialog.file_backup_restore.failed_title"),
                self.translator.text(
                    "dialog.encoding_failed",
                    encoding=self.current_encoding,
                    error=error,
                ),
            )
            return

        self.editor.setPlainText(load_data)
        self.editor.moveCursor(QTextCursor.MoveOperation.Start)
        self.editor.document().setModified(True)
        self._set_current_file_state(self.current_save_file_path, self.current_encoding)
        self._save_unsaved_backup()
        self._update_window_title()
        self._set_encoding_status()
        self.statusBar().showMessage(
            self.translator.text("dialog.file_backup_restore.restored")
        )

    def _file_backup_label(self, backup_path: Path) -> str:
        """Return a user-facing label for a saved-file backup."""
        modified_at = datetime.fromtimestamp(
            backup_path.stat().st_mtime,
            timezone.utc,
        ).astimezone()
        return self.translator.text(
            "dialog.file_backup_restore.item",
            timestamp=modified_at.strftime("%Y-%m-%d %H:%M:%S"),
            name=backup_path.name,
        )

    def _unsaved_backup_label(self, backup_path: Path, label_key: str) -> str:
        """Return a user-facing label for an unsaved auto-backup snapshot."""
        modified_at = datetime.fromtimestamp(
            backup_path.stat().st_mtime,
            timezone.utc,
        ).astimezone()
        return self.translator.text(
            label_key,
            timestamp=modified_at.strftime("%Y-%m-%d %H:%M:%S"),
            name=backup_path.name,
        )

    def _autosave_before_risky_operation(self) -> bool:
        """Autosave modified tabs before an operation that may discard editor state."""
        if not self._has_modified_tabs():
            return True
        if self._save_unsaved_backup_snapshot():
            return True
        QMessageBox.critical(
            self,
            self.translator.text("dialog.autosave_failed.title"),
            self.translator.text("dialog.autosave_failed.message"),
        )
        return False

    def _has_modified_tabs(self) -> bool:
        """Return True if any editor tab has unsaved modifications."""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None and editor.document().isModified():
                return True
        return False

    def _save_unsaved_backup(self) -> bool:
        """Save a restorable session of all modified editor tabs."""
        if not self.unsaved_backup_enabled or self.restoring_unsaved_backup:
            return True
        session = self._build_unsaved_backup_session()
        if session is None:
            self._clear_unsaved_backup()
            return True
        return self.unsaved_backup_manager.save_session(session)

    def _save_unsaved_backup_snapshot(self) -> bool:
        """Save the latest unsaved backup and an additional history snapshot."""
        if not self.unsaved_backup_enabled or self.restoring_unsaved_backup:
            return True
        session = self._build_unsaved_backup_session()
        if session is None:
            self._clear_unsaved_backup()
            return True
        if not self.unsaved_backup_manager.save_session(session):
            return False
        return self.unsaved_backup_manager.save_history_snapshot(session) is not None

    def _build_unsaved_backup_session(self) -> UnsavedBackupSession | None:
        """Build a restorable session for all modified editor tabs."""
        tabs: list[UnsavedBackup] = []
        current_backup_index = 0
        current_editor = self._current_editor()
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is None or not editor.document().isModified():
                continue
            save_data = editor.toPlainText()
            if editor is current_editor:
                current_backup_index = len(tabs)
            tabs.append(
                UnsavedBackup(
                    text=save_data,
                    encoding=self.tab_encodings.get(editor, self.default_encoding),
                    save_file_path=self.tab_file_paths.get(editor),
                )
            )

        if not tabs:
            return None

        return UnsavedBackupSession(
            tabs=tabs,
            current_index=current_backup_index,
        )

    def _restore_unsaved_backup_if_available(self) -> None:
        """Restore an unsaved backup if available and prompt the user for confirmation."""
        if not self.unsaved_backup_enabled:
            return
        session = self.unsaved_backup_manager.load_session()
        if session is None or not session.tabs:
            return

        result = QMessageBox.question(
            self,
            self.translator.text("dialog.restore_backup.title"),
            self.translator.text("dialog.restore_backup.message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        self._restore_unsaved_backup_session(session)

    def _restore_unsaved_backup_session(self, session: UnsavedBackupSession) -> None:
        """Restore an unsaved backup session into editor tabs."""
        self.restoring_unsaved_backup = True
        try:
            while self.tab_widget.count():
                self.remove_tab(0)
            for backup in session.tabs:
                editor = self.create_editor_tab(
                    text=backup.text,
                    save_file_path=backup.save_file_path,
                    encoding=backup.encoding,
                    modified=True,
                )
                editor.moveCursor(QTextCursor.MoveOperation.Start)
            self.tab_widget.setCurrentIndex(
                min(max(session.current_index, 0), self.tab_widget.count() - 1)
            )
            self._sync_current_tab_state()
            self._update_window_title()
            self._set_encoding_status()
        finally:
            self.restoring_unsaved_backup = False

    def _clear_unsaved_backup(self) -> None:
        """Clear the unsaved backup if it exists and unsaved backups are enabled."""
        if self.unsaved_backup_enabled:
            self.unsaved_backup_manager.clear()

    def show_find_replace_dialog(self) -> None:
        """Show the find and replace dialog, initializing it with the current selection if available."""
        if self.find_replace_dialog is None:
            self.find_replace_dialog = FindReplaceDialog(self.translator, self)
            self.find_replace_dialog.set_regex_lint_enabled(self.regex_lint_enabled)
            self.find_replace_dialog.set_reduced_error_check_enabled(
                self.reduced_error_check_enabled
            )
            self.find_replace_dialog.find_requested.connect(self.find_next)
            self.find_replace_dialog.find_previous_requested.connect(self.find_previous)
            self.find_replace_dialog.replace_requested.connect(self.replace_current)
            self.find_replace_dialog.replace_all_requested.connect(
                self._replace_all_from_dialog
            )
            self.find_replace_dialog.replace_marked_requested.connect(
                self.replace_marked_matches
            )
            self.find_replace_dialog.preview_requested.connect(self.preview_matches)
            self.find_replace_dialog.search_parameters_changed.connect(
                self.schedule_search_highlights
            )
            self.find_replace_dialog.regex_help_requested.connect(self.show_regex_help_dialog)
            self.find_replace_dialog.normalise_requested.connect(
                self.apply_regex_normalise_operation
            )

        selected_text = self.editor.textCursor().selectedText()
        if selected_text:
            cursor = self.editor.textCursor()
            self.search_scope = (
                self.editor.cursor_position_to_text_position(cursor.selectionStart()),
                self.editor.cursor_position_to_text_position(cursor.selectionEnd()),
            )
            self.find_replace_dialog.set_find_text(selected_text.replace("\u2029", "\n"))
        else:
            self.search_scope = None
        self.find_replace_dialog.clear_error()
        if not self.reduced_error_check_enabled:
            self.update_search_highlights(
                self.find_replace_dialog.find_text_edit.text(),
                self.find_replace_dialog.current_search_options(),
            )
        self.find_replace_dialog.show()
        self.find_replace_dialog.raise_()
        self.find_replace_dialog.activateWindow()

    def find_next(self, search_text: str, options: SearchOptions) -> None:
        """Find the next occurrence of the search text using the specified search options.""" 
        if not search_text:
            self._set_search_error(self.translator.text("search.empty"))
            return

        cursor = self.editor.textCursor()
        scope_text, scope_offset = self._search_scope_text(options)
        if options.selected_only and scope_text is None:
            self._set_search_error(self.translator.text("search.select_before_find"))
            return

        source_text = scope_text if scope_text is not None else self.editor.toPlainText()
        cursor_position = cursor.selectionEnd() if cursor.hasSelection() else cursor.position()
        start_position = self.editor.cursor_position_to_text_position(cursor_position)
        start_position = min(max(start_position - scope_offset, 0), len(source_text))

        try:
            match = self.search_engine.find_next(
                source_text,
                search_text,
                start_position,
                options,
            )
        except RegexError as error:
            self._set_search_error(self.translator.text("search.invalid_regex", error=error))
            return

        if match is None:
            self._set_search_error(self.translator.text("search.no_matches"))
            return

        self._select_match(
            SearchMatch(
                match.start + scope_offset,
                match.end + scope_offset,
                match.text,
            )
        )
        self._set_search_status(self.translator.text("search.match_found"))

    def find_previous(self, search_text: str, options: SearchOptions) -> None:
        """Find the previous occurrence of the search text using the specified search options."""
        if not search_text:
            self._set_search_error(self.translator.text("search.empty"))
            return

        cursor = self.editor.textCursor()
        scope_text, scope_offset = self._search_scope_text(options)
        if options.selected_only and scope_text is None:
            self._set_search_error(self.translator.text("search.select_before_find"))
            return

        source_text = scope_text if scope_text is not None else self.editor.toPlainText()
        cursor_position = (
            cursor.selectionStart() if cursor.hasSelection() else cursor.position()
        )
        start_position = self.editor.cursor_position_to_text_position(cursor_position)
        start_position = min(max(start_position - scope_offset, 0), len(source_text))

        try:
            match = self.search_engine.find_previous(
                source_text,
                search_text,
                start_position,
                options,
            )
        except RegexError as error:
            self._set_search_error(
                self.translator.text("search.invalid_regex", error=error)
            )
            return

        if match is None:
            self._set_search_error(self.translator.text("search.no_matches"))
            return

        self._select_match(
            SearchMatch(
                match.start + scope_offset,
                match.end + scope_offset,
                match.text,
            )
        )
        self._set_search_status(self.translator.text("search.match_found"))

    def replace_current(
        self,
        search_text: str,
        replace_text: str,
        options: SearchOptions,
    ) -> None:
        """Replace the currently selected occurrence of the search text with the replacement text using the specified search options."""
        if not search_text:
            self._set_search_error(self.translator.text("search.empty"))
            return

        cursor = self.editor.textCursor()
        source_text = self.editor.toPlainText()
        selected_match = SearchMatch(
            self.editor.cursor_position_to_text_position(cursor.selectionStart()),
            self.editor.cursor_position_to_text_position(cursor.selectionEnd()),
            cursor.selectedText().replace("\u2029", "\n"),
        )
        scope_text, scope_offset = self._search_scope_text(options)
        if options.selected_only and scope_text is None:
            self._set_search_error(self.translator.text("search.select_before_replace"))
            return
        if scope_text is not None and not self._match_is_inside_scope(
            selected_match,
            scope_offset,
            len(scope_text),
        ):
            self.find_next(search_text, options)
            return

        try:
            current_selection_matches = self.search_engine.find_all(
                selected_match.text,
                search_text,
                replace(options, exclusion_text=""),
            )
            if (
                not cursor.hasSelection()
                or len(current_selection_matches) != 1
                or current_selection_matches[0].start != 0
                or current_selection_matches[0].end != len(selected_match.text)
            ):
                self.find_next(search_text, options)
                return

            replacement_options = options
            if options.exclusion_text:
                allowed_matches = self.search_engine.find_all(
                    scope_text if scope_text is not None else source_text,
                    search_text, options,
                )
                if not any(
                    match.start + scope_offset == selected_match.start
                    and match.end + scope_offset == selected_match.end
                    for match in allowed_matches
                ):
                    self._set_search_error(self.translator.text("search.no_current_match"))
                    return
                replacement_options = replace(options, exclusion_text="")
            result = self.search_engine.replace_match(
                source_text,
                selected_match,
                replace_text,
                search_text,
                replacement_options,
            )
        except RegexError as error:
            self._set_search_error(self.translator.text("search.invalid_regex", error=error))
            return

        if result.count == 0:
            self._set_search_error(self.translator.text("search.no_current_match"))
            return

        self._replace_document_text(result.text)
        self._update_search_highlights_when_allowed(search_text, options)
        replaced_end = len(result.text) - (len(source_text) - selected_match.end)
        self._set_cursor_position(replaced_end)
        self._set_search_status(self.translator.text("search.replaced_one"))
        self._focus_find_text_after_replace_all()

    def replace_all(
        self,
        search_text: str,
        replace_text: str,
        options: SearchOptions,
        *,
        confirm: bool = False,
    ) -> None:
        """Replace all occurrences of the search text with the replacement text using the specified search options."""
        if not search_text:
            self._set_search_error(self.translator.text("search.empty"))
            return

        scope_text, scope_offset = self._search_scope_text(options)
        if options.selected_only and scope_text is None:
            self._set_search_error(self.translator.text("search.select_before_replace"))
            return

        source_text = self.editor.toPlainText()
        target_text = scope_text if scope_text is not None else source_text

        try:
            matches = self.search_engine.find_all(target_text, search_text, options)
            if not matches:
                self._set_search_error(self.translator.text("search.no_replacements"))
                return
            if not confirm and self.find_replace_dialog is not None:
                rows = self._preview_rows(
                    target_text,
                    matches,
                    search_text,
                    replace_text,
                    options,
                    scope_offset,
                )
                summary = self._replacement_preview_summary(len(matches), len(rows))
                self.find_replace_dialog.set_preview_rows(rows, summary)
                self._set_search_status(summary)
            if confirm and not self._confirm_replace_all(
                target_text,
                matches,
                search_text,
                replace_text,
                options,
                scope_offset,
            ):
                return
            result = self.search_engine.replace_all(
                target_text,
                search_text,
                replace_text,
                options,
            )
        except RegexError as error:
            self._set_search_error(self.translator.text("search.invalid_regex", error=error))
            return

        if result.count == 0:
            self._set_search_error(self.translator.text("search.no_replacements"))
            return

        if scope_text is not None:
            scope_start = scope_offset
            scope_end = scope_offset + len(scope_text)
            result_text = source_text[:scope_start] + result.text + source_text[scope_end:]
            if options.selected_only:
                self.search_scope = (scope_start, scope_start + len(result.text))
        else:
            result_text = result.text

        self._replace_document_text(result_text)
        self._update_search_highlights_when_allowed(search_text, options)
        self._set_search_status(
            self.translator.text("search.replaced_many", count=result.count)
        )
        self._focus_find_text_after_replace_all()

    def _replace_all_from_dialog(
        self,
        search_text: str,
        replace_text: str,
        options: SearchOptions,
    ) -> None:
        self.replace_all(search_text, replace_text, options, confirm=False)

    def _confirm_replace_all(
        self,
        target_text: str,
        matches: list[SearchMatch],
        search_text: str,
        replace_text: str,
        options: SearchOptions,
        scope_offset: int,
    ) -> bool:
        rows = self._preview_rows(
            target_text,
            matches,
            search_text,
            replace_text,
            options,
            scope_offset,
        )
        summary = self._replacement_preview_summary(len(matches), len(rows))
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.set_preview_rows(rows, summary)
        self._set_search_status(summary)

        result = QMessageBox.question(
            self,
            self.translator.text("search.replace_all_confirm.title"),
            "\n\n".join(
                (
                    self.translator.text(
                        "search.replace_all_confirm.message",
                        count=len(matches),
                    ),
                    summary,
                )
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            self._set_search_status(
                self.translator.text("search.replace_all_cancelled")
            )
            return False
        return True

    def replace_marked_matches(
        self,
        search_text: str,
        replace_text: str,
        options: SearchOptions,
    ) -> None:
        """Replace all marked occurrences of the search text with the replacement text using the specified search options."""
        if not search_text:
            self._set_search_error(self.translator.text("search.empty"))
            return
        if not self.editor.search_matches:
            self._set_search_error(self.translator.text("search.no_replacements"))
            return

        result_text = self.editor.toPlainText()
        replacement_count = 0
        try:
            original_text = result_text
            allowed_ranges = None
            if options.exclusion_text:
                scope_text, scope_offset = self._search_scope_text(options)
                if options.selected_only and scope_text is None:
                    self._set_search_error(self.translator.text("search.select_before_replace"))
                    return
                allowed_ranges = {
                    (match.start + scope_offset, match.end + scope_offset)
                    for match in self.search_engine.find_all(
                        scope_text if scope_text is not None else original_text,
                        search_text, options,
                    )
                }
            preview_options = replace(options, exclusion_text="")
            for match in sorted(
                self.editor.search_matches,
                key=lambda search_match: search_match.start,
                reverse=True,
            ):
                if match.start < 0 or match.end > len(result_text):
                    continue
                if allowed_ranges is not None and (match.start, match.end) not in allowed_ranges:
                    continue
                target_text = result_text[match.start : match.end]
                preview_result = self.search_engine.preview_replacement(
                    target_text,
                    search_text,
                    replace_text,
                    preview_options,
                )
                if preview_result.count == 0:
                    continue
                result_text = (
                    result_text[: match.start]
                    + preview_result.text
                    + result_text[match.end :]
                )
                replacement_count += 1
        except RegexError as error:
            self._set_search_error(
                self.translator.text("search.invalid_regex", error=error)
            )
            return

        if replacement_count == 0:
            self._set_search_error(self.translator.text("search.no_replacements"))
            return

        self._replace_document_text(result_text)
        self._update_search_highlights_when_allowed(search_text, options)
        self._set_search_status(
            self.translator.text("search.replaced_many", count=replacement_count)
        )
        self._focus_find_text_after_replace_all()

    def apply_regex_normalise_operation(self, operation_id: str) -> None:
        if self.find_replace_dialog is None:
            return

        options = self.find_replace_dialog.current_search_options()
        scope_text, scope_offset = self._search_scope_text(options)
        if options.selected_only and scope_text is None:
            self._set_search_error(self.translator.text("search.select_before_replace"))
            return

        source_text = self.editor.toPlainText()
        target_text = scope_text if scope_text is not None else source_text
        result = apply_normalise_operation(target_text, operation_id)
        if result.count == 0:
            self._set_search_error(self.translator.text("search.no_replacements"))
            return

        if scope_text is not None:
            scope_start = scope_offset
            scope_end = scope_offset + len(scope_text)
            result_text = source_text[:scope_start] + result.text + source_text[scope_end:]
            if options.selected_only:
                self.search_scope = (scope_start, scope_start + len(result.text))
        else:
            result_text = result.text

        self._replace_document_text(result_text)
        self._refresh_search_highlights_from_dialog()
        self._set_search_status(
            self.translator.text("normalise.applied", count=result.count)
        )
        self._focus_find_text_after_replace_all()

    def _update_search_highlights_when_allowed(
        self,
        search_text: str,
        options: SearchOptions,
    ) -> None:
        if self.reduced_error_check_enabled:
            self.editor.clear_search_matches()
            return
        self.schedule_search_highlights(search_text, options)

    def schedule_search_highlights(
        self,
        search_text: str,
        options: SearchOptions,
    ) -> None:
        """Delay automatic search highlighting so typing does not rescan on every key."""
        self.editor.clear_search_matches()
        self.pending_search_highlight = (search_text, options)
        self.search_highlight_timer.start()

    def _run_pending_search_highlight(self) -> None:
        if self.pending_search_highlight is None:
            return
        search_text, options = self.pending_search_highlight
        self.pending_search_highlight = None
        self.update_search_highlights(search_text, options)

    def _focus_find_text_after_replace_all(self) -> None:
        QTimer.singleShot(0, self._focus_find_text_after_replace_all_now)

    def _focus_find_text_after_replace_all_now(self) -> None:
        if self.find_replace_dialog is None or not self.find_replace_dialog.isVisible():
            return
        dialog = self.find_replace_dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.replace_text_edit.stabilize_visible_text()
        dialog.find_text_edit.stabilize_visible_text()
        dialog.find_text_edit.setFocus()

    def update_search_highlights(
        self,
        search_text: str,
        options: SearchOptions,
    ) -> None:
        """Update the search highlights in the editor based on the current search text and options."""
        if not search_text:
            self.editor.clear_search_matches()
            return

        scope_text, scope_offset = self._search_scope_text(options)
        if options.selected_only and scope_text is None:
            self.editor.clear_search_matches()
            return

        source_text = scope_text if scope_text is not None else self.editor.toPlainText()
        try:
            matches = self.search_engine.find_all(
                source_text,
                search_text,
                options,
                max_matches=MAX_AUTO_SEARCH_HIGHLIGHTS,
            )
        except RegexError:
            self.editor.clear_search_matches()
            return

        self.editor.set_search_matches(
            [
                SearchMatch(
                    match.start + scope_offset,
                    match.end + scope_offset,
                    match.text,
                )
                for match in matches
            ]
        )

    def _refresh_search_highlights_from_dialog(self) -> None:
        """Refresh the search highlights in the editor based on the current state of the find and replace dialog."""
        if self.find_replace_dialog is None or not self.find_replace_dialog.isVisible():
            return
        self.update_search_highlights(
            self.find_replace_dialog.find_text_edit.text(),
            self.find_replace_dialog.current_search_options(),
        )

    def preview_matches(
        self,
        search_text: str,
        replace_text: str,
        options: SearchOptions,
    ) -> None:
        """Preview the matches for the current search and replacement settings in the find and replace dialog."""
        if self.find_replace_dialog is None:
            return
        if not search_text:
            self._set_search_error(self.translator.text("search.empty"))
            return

        scope_text, scope_offset = self._search_scope_text(options)
        if options.selected_only and scope_text is None:
            self._set_search_error(self.translator.text("search.select_before_find"))
            return

        source_text = scope_text if scope_text is not None else self.editor.toPlainText()
        try:
            matches = self.search_engine.find_all(source_text, search_text, options)
            rows = self._preview_rows(
                source_text,
                matches,
                search_text,
                replace_text,
                options,
                scope_offset,
            )
        except RegexError as error:
            self._set_search_error(self.translator.text("search.invalid_regex", error=error))
            return

        summary = self._replacement_preview_summary(len(matches), len(rows))

        self.find_replace_dialog.set_preview_rows(rows, summary)
        self._set_search_status(summary)

    def _replacement_preview_summary(self, match_count: int, shown_count: int) -> str:
        if match_count == 0:
            return self.translator.text("search.preview.no_matches")
        if shown_count < match_count:
            return self.translator.text(
                "search.preview.limited",
                shown=shown_count,
                total=match_count,
            )
        return self.translator.text("search.preview.matches", count=match_count)

    def show_regex_help_dialog(self) -> None:
        """Show the regex help dialog, initializing it if necessary."""
        if self.regex_help_dialog is None:
            regex_help_paths = {
                "EN_Ver.": self.resources_path / "regex_help_en.json",
                "JP_Ver.": self.resources_path / "regex_help_ja.json",
            }
            self.regex_help_dialog = RegexHelpDialog(
                regex_help_paths,
                self.translator,
                self,
            )
            self.regex_help_dialog.pattern_insert_requested.connect(
                self._insert_regex_pattern
            )

        self.regex_help_dialog.show()
        self.regex_help_dialog.raise_()
        self.regex_help_dialog.activateWindow()

    def show_user_help_dialog(self) -> None:
        """Show the user help dialog, initializing it if necessary."""
        if self.user_help_dialog is None:
            self.user_help_dialog = UserHelpDialog(self.translator, self)

        self.user_help_dialog.show()
        self.user_help_dialog.raise_()
        self.user_help_dialog.activateWindow()

    def show_schema_reference_dialog(self) -> None:
        """Show modeless HTML and WordPress schema tables beside the editor."""
        is_new_dialog = self.schema_reference_dialog is None
        if self.schema_reference_dialog is None:
            self.schema_reference_dialog = SchemaReferenceDialog(
                bundled_base_dir() / "dictionaries" / "standards",
                self.translator,
                self,
            )

        self.schema_reference_dialog.show()
        if is_new_dialog:
            self.schema_reference_dialog.place_next_to(self)
        self.schema_reference_dialog.raise_()
        self.schema_reference_dialog.activateWindow()

    def _insert_regex_pattern(self, pattern: str) -> None:
        """Insert the given regex pattern into the find text field of the find and replace dialog."""
        if self.find_replace_dialog is None:
            self.show_find_replace_dialog()
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.insert_find_text(pattern)

    def _search_scope_text(self, options: SearchOptions) -> tuple[str | None, int]:
        """Determine the text and offset for the current search scope based on the search options."""
        if not options.selected_only and not options.visible_only:
            return None, 0

        source_text = self.editor.toPlainText()
        scope_bounds: tuple[int, int] | None = None

        if options.selected_only:
            selected_bounds = self._selected_search_bounds(len(source_text))
            if selected_bounds is None:
                return None, 0
            scope_bounds = selected_bounds

        if options.visible_only:
            visible_bounds = self._visible_search_bounds(len(source_text))
            if visible_bounds is None:
                return "", 0
            scope_bounds = (
                visible_bounds
                if scope_bounds is None
                else (
                    max(scope_bounds[0], visible_bounds[0]),
                    min(scope_bounds[1], visible_bounds[1]),
                )
            )

        if scope_bounds is None:
            return None, 0

        scope_start, scope_end = scope_bounds
        if scope_start >= scope_end:
            return "", scope_start
        return source_text[scope_start:scope_end], scope_start

    def _selected_search_bounds(self, source_length: int) -> tuple[int, int] | None:
        """Determine the start and end bounds of the selected text for searching, or return None if no valid selection exists."""
        if self.search_scope is None:
            cursor = self.editor.textCursor()
            if not cursor.hasSelection():
                return None
            self.search_scope = (
                self.editor.cursor_position_to_text_position(cursor.selectionStart()),
                self.editor.cursor_position_to_text_position(cursor.selectionEnd()),
            )

        scope_start, scope_end = self.search_scope
        if scope_start >= scope_end or scope_end > source_length:
            return None
        return scope_start, scope_end

    def _visible_search_bounds(self, source_length: int) -> tuple[int, int] | None:
        """Determine the start and end bounds of the visible text for searching, or return None if no valid visible text exists."""
        first_block = self.editor.firstVisibleBlock()
        if not first_block.isValid():
            return None

        viewport_rect = self.editor.viewport().rect()
        block = first_block
        top = round(
            self.editor.blockBoundingGeometry(block)
            .translated(self.editor.contentOffset())
            .top()
        )
        bottom = top + round(self.editor.blockBoundingRect(block).height())
        visible_start: int | None = None
        visible_end: int | None = None

        while block.isValid() and top <= viewport_rect.bottom():
            if block.isVisible() and bottom >= viewport_rect.top():
                if visible_start is None:
                    visible_start = self.editor.cursor_position_to_text_position(
                        block.position()
                    )
                visible_end = min(
                    self.editor.cursor_position_to_text_position(
                        block.position() + block.length()
                    ),
                    source_length,
                )

            block = block.next()
            top = bottom
            bottom = top + round(self.editor.blockBoundingRect(block).height())

        if visible_start is None or visible_end is None:
            return None
        return visible_start, visible_end

    def _match_is_inside_scope(
        self,
        match: SearchMatch,
        scope_offset: int,
        scope_length: int,
    ) -> bool:
        """Check if the given match is entirely within the specified search scope."""
        return scope_offset <= match.start and match.end <= scope_offset + scope_length

    def _preview_rows(
        self,
        source_text: str,
        matches: list[SearchMatch],
        search_text: str,
        replace_text: str,
        options: SearchOptions,
        scope_offset: int,
    ) -> list[tuple[int, str, str]]:
        """Generate a preview of the replacement results for the given matches within the specified search scope."""
        rows: list[tuple[int, str, str]] = []
        preview_options = replace(options, exclusion_text="")
        for match in matches[:200]:
            absolute_start = scope_offset + match.start
            line_number = self.editor.toPlainText().count("\n", 0, absolute_start) + 1
            before_text = self._line_context(source_text, match)
            preview_result = self.search_engine.preview_replacement(
                match.text,
                search_text,
                replace_text,
                preview_options,
            )
            replacement_context_text = self._line_replacement_context(
                source_text,
                match,
                search_text,
                replace_text,
                options,
                matches,
            )
            after_text = (
                self._visible_preview_text(replacement_context_text)
                if preview_result.count
                else self._replacement_context(source_text, match, match.text)
            )
            rows.append(
                (
                    line_number,
                    before_text,
                    after_text,
                )
            )
        return rows

    def _line_replacement_context(
        self,
        source_text: str,
        match: SearchMatch,
        search_text: str,
        replace_text: str,
        options: SearchOptions,
        allowed_matches: list[SearchMatch],
    ) -> str:
        line_start = source_text.rfind("\n", 0, match.start) + 1
        line_end = source_text.find("\n", match.end)
        if line_end == -1:
            line_end = len(source_text)
        line_text = source_text[line_start:line_end]
        if options.exclusion_text:
            # Test exclusions against the original scope, before slicing a line.
            preview_options = replace(options, exclusion_text="")
            for line_match in reversed(allowed_matches):
                if line_match.start < line_start or line_match.end > line_end:
                    continue
                preview = self.search_engine.preview_replacement(
                    line_match.text, search_text, replace_text, preview_options,
                )
                start = line_match.start - line_start
                end = line_match.end - line_start
                line_text = line_text[:start] + preview.text + line_text[end:]
            return line_text
        result = self.search_engine.replace_all(
            line_text,
            search_text,
            replace_text,
            options,
        )
        return result.text if result.count else match.text

    def _line_context(self, source_text: str, match: SearchMatch) -> str:
        """Extract the context of the line containing the given match, highlighting the match itself."""
        line_start = source_text.rfind("\n", 0, match.start) + 1
        line_end = source_text.find("\n", match.end)
        if line_end == -1:
            line_end = len(source_text)
        prefix = source_text[line_start : match.start]
        suffix = source_text[match.end : line_end]
        context_text = f"{prefix}{match.text}{suffix}"
        return self._visible_preview_text(context_text)

    def _replacement_context(
        self,
        source_text: str,
        match: SearchMatch,
        replacement_text: str,
    ) -> str:
        """Extract the context of the line containing the given match, showing the replacement text in place of the match."""
        line_start = source_text.rfind("\n", 0, match.start) + 1
        line_end = source_text.find("\n", match.end)
        if line_end == -1:
            line_end = len(source_text)
        prefix = source_text[line_start : match.start]
        suffix = source_text[match.end : line_end]
        return self._visible_preview_text(f"{prefix}{replacement_text}{suffix}")

    def _visible_preview_text(self, text: str) -> str:
        """Convert the given text into a visible preview by escaping tabs and newlines, and truncating if necessary."""
        visible_text = text.replace("\t", "\\t").replace("\n", "\\n")
        if len(visible_text) > 140:
            return f"{visible_text[:137]}..."
        return visible_text

    def _replace_document_text(self, text: str) -> None:
        """Replace the entire text of the document in the editor with the given text."""
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(text)
        cursor.endEditBlock()

    def _select_match(self, match: SearchMatch) -> None:
        """Select the text corresponding to the given match in the editor and focus the editor."""
        cursor = self.editor.textCursor()
        cursor.setPosition(self.editor.text_position_to_cursor_position(match.start))
        cursor.setPosition(
            self.editor.text_position_to_cursor_position(match.end),
            QTextCursor.MoveMode.KeepAnchor,
        )
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _set_cursor_position(self, position: int) -> None:
        """Set the cursor position in the editor to the specified text position."""
        cursor = self.editor.textCursor()
        cursor.setPosition(self.editor.text_position_to_cursor_position(position))
        self.editor.setTextCursor(cursor)

    def _set_search_error(self, message: str) -> None:
        """Display the given search error message in the find and replace dialog and the status bar."""
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.set_error(message)
        self.statusBar().showMessage(message)

    def _set_search_status(self, message: str) -> None:
        """Display the given search status message in the status bar and clear any error in the find and replace dialog."""
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.clear_error()
        self.statusBar().showMessage(message)

    def _set_encoding_status(self) -> None:
        """Display the current encoding status in the status bar."""
        self.statusBar().showMessage(
            self.translator.text("status.encoding", encoding=self.current_encoding)
        )


def main() -> int:
    """Entry point for the application."""
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = MainWindow()
    window.setWindowIcon(QIcon(str(ICON_PATH)))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
