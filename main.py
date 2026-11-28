# pylint: disable=C0302,C0301,C0411,C0413,C0116
# ruff: noqa:E402,RUF100
"""Regex Padのメインウインドウを提供する。"""
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
from bisect import bisect_right
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from html import escape, unescape
from pathlib import Path
from re import error as RegexError

from portable_runtime import app_base_dir, bundled_base_dir, configure_portable_runtime

configure_portable_runtime()

from app_logging import LogLevel, get_logger, install_exception_hooks

LOGGER = get_logger()

# PySide6 exposes Qt modules dynamically; Pylint may report false no-name-in-module.
from PySide6.QtCore import (  # pylint: disable=no-name-in-module
    QByteArray,
    QPoint,
    Qt,
    QTimer,
)
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
from dialogs.core_block_repair_controller import repair_core_blocks
from dialogs.dictionary_editor_dialog import DictionaryEditorDialog
from dialogs.find_replace_dialog import FindReplaceDialog
from dialogs.grammar_check_dialog import GrammarCheckDialog
from dialogs.inline_color_dialog import InlineColorDialog
from dialogs.macro_editor_controller import MacroEditorController
from dialogs.macro_editor_window import MacroEditorWindow
from dialogs.macro_execution_controller import MacroExecutionController
from dialogs.options_dialog import OptionsDialog
from dialogs.regex_help_dialog import RegexHelpDialog
from dialogs.schema_reference_dialog import SchemaReferenceDialog
from dialogs.shortcut_settings_dialog import (
    ShortcutActionInfo,
    ShortcutSettingsDialog,
    validate_shortcut_settings,
)
from dialogs.tag_insert_dialog import TagInsertDialog
from dialogs.unicode_character_info_dialog import UnicodeCharacterInfoDialog
from dialogs.user_help_dialog import UserHelpDialog
from editor.dictionary_edit_service import DictionaryEditService
from editor.document_character_count import DocumentCharacterCount
from editor.editor_tab import EditorTab
from editor.paragraph_insert_rules import (
    ParagraphInsertDictionaryError,
    load_paragraph_insert_rule_book,
)
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
from editor.unicode_character_info import character_at_cursor, inspect_character
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
from macro.editor_data_model import MacroEditorDocumentData, MacroEditorStepData
from macro.json_loader import MacroJsonLoader, MacroJsonLoadError
from macro.json_paths import configured_macro_folder, default_macro_folder
from normalise import apply_normalise_operation
from preview.wordpress_preview import WordPressPreview
from preview.wordpress_runtime import default_runtime_root
from search.css_lint import CssLintIssue, lint_stylesheet
from search.html_typo_lint import HtmlTypoLintMessage, lint_html_typos
from search.incremental_markers import IndexedSource
from search.local_structure_lint import CoreBlockIndex
from search.search_engine import SearchEngine, SearchMatch, SearchOptions
from settings.color_presets import ColorPreset, load_color_preset_catalog
from settings.settings_manager import EditorSettings, SettingsManager
from settings.shortcut_settings import (
    ShortcutSettings,
    ShortcutSettingsError,
    load_shortcut_settings,
    save_shortcut_settings,
)

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
    """CSS宣言を、引用符や括弧内のセミコロンを保って分割する。"""
    return [part.strip() for part in style_text.split(";") if part.strip()]


class MainWindow(QMainWindow):
    """Regex Padのメインウインドウを表す。"""
    def __init__(
        self,
        settings_path: Path | None = None,
        unsaved_backup_path: Path | None = None,
        restore_unsaved_backup: bool = True,
        window_id: str | None = None,
    ) -> None:
        """設定と復元データを読み、メニュー、タブ、編集処理を初期化する。"""
        super().__init__()
        self.window_id: str = window_id or str(uuid.uuid4())
        self.setObjectName(f"main-window-{self.window_id}")
        self.resources_path: Path = bundled_base_dir() / "resources"
        config_path = settings_path or default_config_path()
        migrate_legacy_settings_if_needed(config_path)
        self.settings_manager = SettingsManager(config_path)
        self.shortcut_settings_path = config_path.with_name("shortcutkey_ref.json")
        self.shortcut_settings_error = ""
        try:
            self.shortcut_settings = load_shortcut_settings(self.shortcut_settings_path)
        except ShortcutSettingsError as error:
            self.shortcut_settings = ShortcutSettings()
            self.shortcut_settings_error = str(error)
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
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self._save_unsaved_backup_snapshot)
        self.current_save_file_path: Path | None = None
        self.default_encoding = settings.default_encoding
        self.current_encoding = settings.default_encoding
        self.newline_code = settings.newline_code
        self.find_replace_dialog: FindReplaceDialog | None = None
        self._find_replace_target: TextEditor | None = None
        self._activating_find_replace_target = False
        self._preview_source: tuple[TextEditor, int] | None = None
        self.macro_editor_window: MacroEditorWindow | None = None
        self.macro_editor_controller: MacroEditorController | None = None
        self.macro_execution_controller: MacroExecutionController | None = None
        self.macro_folder = str(configured_macro_folder(settings.macro_folder))
        self.macro_editor_geometry = settings.macro_editor_geometry
        self.macro_editor_splitter_state = settings.macro_editor_splitter_state
        self.grammar_check_dialog: GrammarCheckDialog | None = None
        self.regex_help_dialog: RegexHelpDialog | None = None
        self.tag_insert_dialog: TagInsertDialog | None = None
        self.user_help_dialog: UserHelpDialog | None = None
        self.schema_reference_dialog: SchemaReferenceDialog | None = None
        self.unicode_character_info_dialog: UnicodeCharacterInfoDialog | None = None
        self.options_dialog: OptionsDialog | None = None
        self.wordpress_preview: WordPressPreview | None = None
        self.wordpress_theme_preview: WordPressPreview | None = None
        self.wordpress_preview_snapshot: tuple[TextEditor, str] | None = None
        self.wordpress_theme_preview_snapshot: tuple[TextEditor, str] | None = None
        self.search_scope: tuple[int, int] | None = None
        self._scope_selection_to_ignore: tuple[TextEditor, int, int] | None = None
        self._search_internal_text_change = False
        self._search_highlights_suspended = False
        self._marked_source: IndexedSource | None = None
        self._marked_editor: TextEditor | None = None
        self._marked_query = ""
        self._marked_options = SearchOptions()
        self._structure_sources: dict[TextEditor, IndexedSource] = {}
        self._structure_indices: dict[TextEditor, CoreBlockIndex] = {}
        self._structure_issues: dict[TextEditor, dict[int, list[int]]] = {}
        self._document_character_counts: dict[TextEditor, DocumentCharacterCount] = {}
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
        self.show_full_path_in_title = settings.show_full_path_in_title
        self.inline_color_preview_enabled = settings.inline_color_preview_enabled
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
        self._shortcut_action_info = self._collect_shortcut_actions()
        # Keep older portable overrides for newly fixed actions on disk, but
        # ignore them in memory so other valid custom shortcuts keep working.
        self.shortcut_settings.overrides = {
            identifier: key for identifier, key in self.shortcut_settings.overrides.items()
            if identifier not in self._shortcut_action_info
            or not self._shortcut_action_info[identifier].locked
        }
        if not self.shortcut_settings_error:
            problem = validate_shortcut_settings(
                self.shortcut_settings, self._shortcut_action_info
            )
            if problem:
                self.shortcut_settings_error = self.translator.text(problem)
                self.shortcut_settings = ShortcutSettings()
        self._create_menus()
        self._apply_shortcut_settings()
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
        self._update_wordpress_status_label()

    def closeEvent(self, event: QCloseEvent) -> None:  # pylint: disable=invalid-name
        """メインウインドウを閉じるイベントを処理する。"""
        for tab_index in range(self.tab_widget.count()):
            editor: TextEditor | None = self._editor_at(tab_index)
            if editor is None:
                continue
            self.tab_widget.setCurrentIndex(tab_index)
            if not self._confirm_save_or_discard_editor(editor):
                event.ignore()
                return
        if self.macro_editor_window is not None and not self.macro_editor_window.close():
            event.ignore()
            return
        self._save_settings()
        self.auto_save_timer.stop()
        self._clear_grammar_lint_results_on_window_close()
        self.stop_wordpress_preview()
        if getattr(sys, "frozen", False):
            from cleanup_inventory import record_inventory_safely

            record_inventory_safely(app_base_dir(), bundled_base_dir())
        event.accept()

    def _create_actions(self) -> None:
        """メインウインドウで使うアクションを作る。"""
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
        self.insert_br_action.triggered.connect(
            lambda: self.insert_shortcut_template("insert_br")
        )

        self.insert_br_br_action = QAction(self)
        self.insert_br_br_action.setShortcut("F9")
        self.insert_br_br_action.triggered.connect(
            lambda: self.insert_shortcut_template("insert_br_br")
        )

        self.inline_strong_action = QAction(self)
        self.inline_strong_action.setShortcut("Ctrl+B")
        self.inline_strong_action.triggered.connect(
            lambda: self.insert_shortcut_template("inline_strong")
        )

        self.inline_underline_action = QAction(self)
        self.inline_underline_action.setShortcut("Ctrl+U")
        self.inline_underline_action.triggered.connect(
            lambda: self.insert_shortcut_template("inline_underline")
        )

        self.inline_color_actions: dict[str, QAction] = {}
        for preset in self.color_presets.text_colors:
            action = QAction(self)
            action.setIcon(self._background_color_swatch_icon(preset.value))
            action.setShortcuts(
                [QKeySequence(shortcut) for shortcut in preset.shortcuts]
            )
            action.triggered.connect(
                lambda checked=False, value=preset.value: self.insert_shortcut_template(
                    "inline_color", value
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
        self.core_block_repair_action = QAction(self)
        self.core_block_repair_action.triggered.connect(self.show_core_block_repair)

        self.unicode_character_info_action = QAction(self)
        self.unicode_character_info_action.triggered.connect(
            self.show_unicode_character_info_dialog
        )

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

        self.shortcut_settings_action = QAction(self)
        self.shortcut_settings_action.triggered.connect(self.show_shortcut_settings_dialog)

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

    def _collect_shortcut_actions(self) -> dict[str, ShortcutActionInfo]:
        """ポータブル設定で上書きする前に、既定のショートカットを記録する。"""
        actions = {
            "new": self.new_action, "open": self.open_action,
            "save": self.save_action, "save_as": self.save_as_action,
            "exit": self.exit_action, "undo": self.undo_action,
            "redo": self.redo_action, "select_all": self.select_all_action,
            "copy_rectangular": self.copy_rectangular_selection_action,
            "insert_br": self.insert_br_action,
            "insert_br_br": self.insert_br_br_action,
            "inline_strong": self.inline_strong_action,
            "inline_underline": self.inline_underline_action,
            "insert_tag": self.insert_tag_picker_action,
            "find": self.find_action, "grammar_check": self.grammar_check_action,
            "wordpress_preview": self.wordpress_preview_action,
            "wordpress_theme_preview": self.wordpress_theme_preview_action,
            "options": self.options_action, "help": self.user_help_action,
        }
        actions.update({
            f"color_{identifier}": action
            for identifier, action in self.inline_color_actions.items()
        })
        locked = {
            "new", "open", "save", "save_as", "find",
            "exit", "undo", "redo", "select_all", "help",
        }
        return {
            identifier: ShortcutActionInfo(
                action,
                tuple(key.toString(QKeySequence.SequenceFormat.PortableText)
                      for key in action.shortcuts()),
                identifier in locked,
            )
            for identifier, action in actions.items()
            if action.shortcuts()
        }

    def _apply_shortcut_settings(self) -> None:
        """保存済みのキーを適用し、定型文の挿入アクションを作り直す。"""
        for identifier, info in self._shortcut_action_info.items():
            primary = (
                info.defaults[0] if info.locked else
                self.shortcut_settings.overrides.get(identifier, info.defaults[0])
            )
            info.action.setShortcuts([
                QKeySequence(value) for value in (primary, *info.defaults[1:])
            ])
        for action in getattr(self, "_custom_shortcut_actions", []):
            self.custom_snippet_menu.removeAction(action)
            action.deleteLater()
        self._custom_shortcut_actions: list[QAction] = []
        for snippet in self.shortcut_settings.snippets:
            action = QAction(snippet.name, self)
            action.setShortcut(QKeySequence(snippet.shortcut))
            action.triggered.connect(
                lambda checked=False, text=snippet.text: self.insert_text_at_cursor(text)
            )
            self.custom_snippet_menu.addAction(action)
            self._custom_shortcut_actions.append(action)
        self.custom_snippet_menu.setEnabled(bool(self._custom_shortcut_actions))

    def _create_menus(self) -> None:
        """メインウインドウのメニューを作る。"""
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
        self.custom_snippet_menu = QMenu(self)
        self.edit_menu.addMenu(self.custom_snippet_menu)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.insert_tag_picker_action)
        self.edit_menu.addMenu(self.insert_tag_menu)
        menu_bar.addMenu(self.edit_menu)

        self.search_menu = QMenu(self)
        self.search_menu.addAction(self.find_action)
        self.search_menu.addAction(self.grammar_check_action)
        self.search_menu.addAction(self.core_block_repair_action)
        self.preset_menu = QMenu(self)
        self.preset_new_action = QAction(self)
        self.preset_run_action = QAction(self)
        self.preset_edit_action = QAction(self)
        self.preset_delete_action = QAction(self)
        self.preset_new_action.triggered.connect(self.new_search_preset)
        self.preset_run_action.triggered.connect(self.run_search_preset)
        self.preset_edit_action.triggered.connect(self.edit_search_preset)
        self.preset_delete_action.triggered.connect(self.delete_search_preset)
        for action in (
            self.preset_new_action, self.preset_run_action,
            self.preset_edit_action, self.preset_delete_action,
        ):
            self.preset_menu.addAction(action)
        self.search_menu.addSeparator()
        self.search_menu.addMenu(self.preset_menu)
        menu_bar.addMenu(self.search_menu)

        self.view_menu = QMenu(self)
        self.view_menu.addAction(self.line_numbers_action)
        self.view_menu.addAction(self.word_wrap_action)
        self.view_menu.addAction(self.ruler_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.unicode_character_info_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.wordpress_preview_action)
        self.view_menu.addAction(self.wordpress_theme_preview_action)
        self.view_menu.addAction(self.stop_wordpress_preview_action)
        menu_bar.addMenu(self.view_menu)

        self.options_menu = QMenu(self)
        self.options_menu.addAction(self.options_action)
        self.options_menu.addAction(self.shortcut_settings_action)
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
        """メインウインドウのステータスバーを作る。"""
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
        """指定された設定と内容でエディターのタブを作る。"""
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
        self.tab_file_paths[editor] = save_file_path
        # Rehighlighting can emit editor signals before the tab becomes active.
        self._apply_inline_color_preview(editor)
        self._document_character_counts[editor] = DocumentCharacterCount(editor.document())
        editor.document().contentsChange.connect(
            lambda position, removed, added, editor=editor: (
                self._document_character_counts[editor].apply_change(position, removed, added)
            )
        )
        editor.textChanged.connect(self._update_status_bar)
        editor.textChanged.connect(lambda editor=editor: self._update_tab_title(editor))
        editor.textChanged.connect(self._save_unsaved_backup)
        if "wp:" in text and "<!--" in text:
            self._structure_sources[editor] = IndexedSource(text)
            self._structure_indices[editor] = CoreBlockIndex(text)
        editor.document().contentsChange.connect(
            lambda position, removed, added, editor=editor: self._editor_contents_changed_for_search(
                editor, position, removed, added
            )
        )
        editor.document().contentsChange.connect(
            lambda position, removed, added, editor=editor: self._editor_contents_changed_for_structure(
                editor, position, removed, added
            )
        )
        editor.textChanged.connect(
            lambda editor=editor: self._invalidate_grammar_lint_result(editor)
        )
        editor.cursorPositionChanged.connect(self._update_status_bar)
        editor.document().modificationChanged.connect(
            lambda _modified, editor=editor: self._update_tab_title(editor)
        )
        editor.document().modificationChanged.connect(self._update_window_title)

        editor.inline_color_clicked.connect(
            lambda start, code: self._choose_inline_color(editor, start, code)
        )
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
        """別ウインドウから利用できるエディターのタブを作る。"""
        return self._create_editor_tab(
            text=text,
            save_file_path=save_file_path,
            encoding=encoding,
            modified=modified,
        )

    def _handle_current_tab_changed(self, index: int) -> None:
        """現在のタブが変わったときの切り替え処理を行う。"""
        editor = self._editor_at(index)
        if editor is None:
            return
        previous_editor = getattr(self, "editor", None)
        self._marked_source = None
        self._marked_editor = None
        if previous_editor is not None and previous_editor is not editor:
            previous_editor.clear_search_matches()
        self.editor = editor
        self._sync_current_tab_state()
        if self._find_replace_target is None:
            self.search_scope = None
        editor.clear_search_matches()
        if (
            editor is self._find_replace_target
            and not self._activating_find_replace_target
            and self.find_replace_dialog is not None
            and self.find_replace_dialog.isVisible()
        ):
            self.refresh_search_highlights(
                self.find_replace_dialog.find_text_edit.text(),
                self.find_replace_dialog.current_search_options(),
            )
        self._update_status_bar()
        self._update_window_title()
        self._rebuild_insert_tag_menu()
        self._refresh_grammar_dialog_for_current_tab()

    def _sync_current_tab_state(self) -> None:
        """現在のタブの状態をメインウインドウに反映する。"""
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
        """保存先と文字コードを含む、現在のファイルの状態を設定する。"""
        self.current_save_file_path = save_file_path
        self.tab_file_paths[self.editor] = save_file_path
        self._apply_inline_color_preview(self.editor)
        if encoding is not None:
            self.current_encoding = encoding
            self.tab_encodings[self.editor] = encoding
        self._update_tab_titles()
        if self.editor is self._find_replace_target and self.find_replace_dialog is not None:
            self.find_replace_dialog.set_target_file_name(self._find_replace_target_name())

    def _tab_title(self, editor: TextEditor) -> str:
        """指定エディターのタブのタイトルを返す。"""
        save_file_path = self.tab_file_paths.get(editor)
        title = save_file_path.name if save_file_path is not None else self._draft_title(editor)
        return f"*{title}" if editor.document().isModified() else title

    def _draft_title(self, editor: TextEditor) -> str:
        """指定エディターの本文から未保存タブのタイトルを取得する。"""
        first_line = editor.document().firstBlock().text().strip()
        if not first_line:
            return self.translator.text("document.untitled")
        return first_line[:30]

    def _update_tab_titles(self) -> None:
        """現在の状態を全タブのタイトルに反映する。"""
        for index in range(self.tab_widget.count()):
            editor = self._editor_at(index)
            if editor is not None:
                self.tab_widget.setTabText(index, self._tab_title(editor))

    def _update_tab_title(self, editor: TextEditor) -> None:
        """本文または変更状態が変わったタブのタイトルを更新する。"""
        for index in range(self.tab_widget.count()):
            if self._editor_at(index) is editor:
                self.tab_widget.setTabText(index, self._tab_title(editor))
                return

    def _set_current_word_wrap_enabled(self, enabled: bool) -> None:
        """開いている全エディターの行折り返しを切り替える。"""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.set_word_wrap_enabled(enabled)

    def _set_current_line_numbers_enabled(self, enabled: bool) -> None:
        """開いている全エディターの行番号表示を切り替える。"""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.set_line_numbers_enabled(enabled)
            editor_tab = self._editor_tab_at(tab_index)
            if editor_tab is not None:
                editor_tab.ruler.update()

    def _set_ruler_enabled(self, enabled: bool) -> None:
        """文字位置を示すルーラーの表示を切り替える。"""
        for tab_index in range(self.tab_widget.count()):
            editor_tab = self._editor_tab_at(tab_index)
            if editor_tab is not None:
                editor_tab.set_ruler_visible(enabled)

    def _set_fixed_wrap_column_from_ruler(self, column: int) -> None:
        """クリックしたルーラーの桁を固定折り返し位置に設定する。"""
        self.fixed_column_wrap_column = max(1, column)
        if self.fixed_column_wrap_enabled:
            self._apply_fixed_column_wrap_options_to_all_tabs()
        self._save_settings()

    def _show_tab_context_menu(self, position: QPoint) -> None:
        """指定位置にあるタブのコンテキストメニューを開く。"""
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
        """指定番号のタブを閉じ、必要なら保存を確認する。"""
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
        """指定番号のタブを、同じ本文を持つ新しいタブに複製する。"""
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
        """指定番号のタブを新しいウインドウに移す。"""
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
        """指定番号のタブのエディターを返す。存在しない場合はNoneを返す。"""
        widget = self.tab_widget.widget(tab_index)
        if isinstance(widget, EditorTab):
            return widget.editor
        return widget if isinstance(widget, TextEditor) else None

    def _editor_tab_at(self, tab_index: int) -> EditorTab | None:
        """指定番号のタブのコンテナを返す。存在しない場合はNoneを返す。"""
        widget = self.tab_widget.widget(tab_index)
        return widget if isinstance(widget, EditorTab) else None

    def _current_editor(self) -> TextEditor | None:
        """現在のタブのエディターを返す。存在しない場合はNoneを返す。"""
        return self._editor_at(self.tab_widget.currentIndex())

    def _undo_current_editor(self) -> None:
        """エディターがある場合に、現在のタブの操作を元に戻す。"""
        editor = self._current_editor()
        if editor is not None:
            editor.undo()

    def _redo_current_editor(self) -> None:
        """エディターがある場合に、現在のタブで元に戻した操作をやり直す。"""
        editor = self._current_editor()
        if editor is not None:
            editor.redo()

    def _select_all_current_editor(self) -> None:
        """エディターがある場合に、現在のタブの全文を選択する。"""
        editor = self._current_editor()
        if editor is not None:
            editor.selectAll()

    def copy_rectangular_selection(self) -> None:
        """現在の複数行選択を矩形としてコピーする。"""
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
        """指定番号のタブを外し、関連する情報やウィジェットを片付ける。"""
        widget = self.tab_widget.widget(tab_index)
        editor = self._editor_at(tab_index)
        if editor is self._find_replace_target and self.find_replace_dialog is not None:
            self.find_replace_dialog.close()
        self.tab_widget.removeTab(tab_index)
        if editor is not None:
            if self._preview_source is not None and self._preview_source[0] is editor:
                if self.find_replace_dialog is not None:
                    self.find_replace_dialog.clear_preview_rows()
                self._preview_source = None
            if editor is self._marked_editor:
                self._marked_source = None
                self._marked_editor = None
            self._delete_grammar_lint_result(editor)
            self.tab_file_paths.pop(editor, None)
            self.tab_encodings.pop(editor, None)
            self.tab_grammar_result_paths.pop(editor, None)
            self._structure_sources.pop(editor, None)
            self._structure_indices.pop(editor, None)
            self._structure_issues.pop(editor, None)
            self._document_character_counts.pop(editor, None)
        if widget is not None:
            widget.deleteLater()

    def remove_tab(self, tab_index: int) -> None:
        """保存確認を行わずに指定タブを外す。"""
        self._remove_tab(tab_index)

    def _restore_settings(self, settings: EditorSettings) -> None:
        """EditorSettingsからメインウインドウとエディターの設定を復元する。"""
        self.line_numbers_action.setChecked(settings.line_numbers_enabled)
        self.word_wrap_action.setChecked(settings.word_wrap_enabled)
        self.ruler_action.setChecked(settings.ruler_enabled)
        self._set_ruler_enabled(settings.ruler_enabled)
        self.fixed_column_wrap_enabled = settings.fixed_column_wrap_enabled
        self.fixed_column_wrap_column = settings.fixed_column_wrap_column
        self._apply_fixed_column_wrap_options_to_all_tabs()
        self.startup_restore_enabled = settings.startup_restore_enabled
        self.show_full_path_in_title = settings.show_full_path_in_title
        self.inline_color_preview_enabled = settings.inline_color_preview_enabled
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
        """メインウインドウとエディターの現在の設定を保存する。"""
        if self.macro_editor_window is not None and self.macro_editor_controller is not None:
            self.macro_folder = str(self.macro_editor_controller.session.macro_folder)
            self.macro_editor_geometry = bytes(self.macro_editor_window.saveGeometry().toBase64().data()).decode("ascii")
            self.macro_editor_splitter_state = bytes(self.macro_editor_window.splitter.saveState().toBase64().data()).decode("ascii")
        self.settings_manager.save(
            macro_folder=self.macro_folder,
            macro_editor_geometry=self.macro_editor_geometry,
            macro_editor_splitter_state=self.macro_editor_splitter_state,
            word_wrap_enabled=self.word_wrap_action.isChecked(),
            line_numbers_enabled=self.line_numbers_action.isChecked(),
            ruler_enabled=self.ruler_action.isChecked(),
            visible_spaces_enabled=self.visible_spaces_enabled,
            visible_tabs_enabled=self.visible_tabs_enabled,
            visible_newlines_enabled=self.visible_newlines_enabled,
            fixed_column_wrap_enabled=self.fixed_column_wrap_enabled,
            fixed_column_wrap_column=self.fixed_column_wrap_column,
            startup_restore_enabled=self.startup_restore_enabled,
            show_full_path_in_title=self.show_full_path_in_title,
            inline_color_preview_enabled=self.inline_color_preview_enabled,
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
        """アプリの表示言語を設定し、画面を更新する。"""
        self.translator.set_language(language_code)
        self.english_action.setChecked(language_code == "en")
        self.japanese_action.setChecked(language_code == "ja")
        self._apply_language()
        self._save_settings()

    def _apply_language(self) -> None:
        """現在の言語を画面全体に適用する。"""
        self.preset_menu.setTitle(self.translator.text("preset.menu"))
        self.preset_new_action.setText(self.translator.text("preset.new"))
        self.preset_run_action.setText(self.translator.text("preset.run"))
        self.preset_edit_action.setText(self.translator.text("preset.edit"))
        self.preset_delete_action.setText(self.translator.text("preset.delete"))
        if self.macro_editor_window is not None:
            self.macro_editor_window.retranslate_ui()
            if self.macro_editor_controller is not None:
                self.macro_editor_controller.validate()
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
        self.core_block_repair_action.setText(self.translator.text("core_repair.title"))
        self.unicode_character_info_action.setText(
            self.translator.text("action.unicode_character_info")
        )
        self.wordpress_preview_action.setText(self.translator.text("action.wordpress_preview"))
        self.wordpress_theme_preview_action.setText(self.translator.text("action.wordpress_theme_preview"))
        self.stop_wordpress_preview_action.setText(self.translator.text("action.stop_wordpress_preview"))
        self.word_wrap_action.setText(self.translator.text("action.word_wrap"))
        self.line_numbers_action.setText(self.translator.text("action.line_numbers"))
        self.ruler_action.setText(self.translator.text("options.item.ruler"))
        self.options_action.setText(self.translator.text("action.options"))
        self.shortcut_settings_action.setText(self.translator.text("shortcut.menu"))
        self.custom_snippet_menu.setTitle(self.translator.text("shortcut.snippets_menu"))
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
        if self.unicode_character_info_dialog is not None:
            self.unicode_character_info_dialog.apply_language()
        if self.options_dialog is not None:
            self.options_dialog.apply_language()
        self._update_status_bar()
        self._update_wordpress_status_label()
        self._update_window_title()

    def _rebuild_insert_tag_menu(self) -> None:
        """現在の言語と使用可能な定型項目からタグ挿入メニューを作り直す。"""
        self.insert_tag_menu.clear()
        self.insert_tag_menu.setTitle(self.translator.text("action.insert_tag"))
        self._set_tag_menu_tooltips_visible(self.insert_tag_menu)
        self._populate_insert_tag_menu(self.insert_tag_menu)

    def _populate_insert_tag_menu(self, root_menu: QMenu) -> None:
        """タグ挿入メニューに定型項目のグループを追加する。"""
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
        """タグ挿入メニューにWordPressのモード別サブメニューを追加する。"""
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
        """指定した定型項目をタグ分類メニューに追加する。"""
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
        """タグメニューの説明をマウス位置に応じて表示するか設定する。"""
        menu.setToolTipsVisible(self.hover_hints_enabled)

    def _create_tag_snippet_action(self, snippet: TagSnippet) -> QAction:
        """定型項目のラベル、ヒント、挿入処理を持つQActionを作る。"""
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
        """指定位置にエディターのコンテキストメニューを開く。"""
        if not self.editor.textCursor().hasSelection():
            self.editor.setTextCursor(self.editor.cursorForPosition(position))
        context_menu = self._create_editor_context_menu()
        context_menu.exec(self.editor.mapToGlobal(position))

    def _create_editor_context_menu(self) -> QMenu:
        """標準の操作とタグ挿入を含むエディター用メニューを作って返す。"""
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

    def show_macro_editor(self) -> None:
        """独立したマクロエディターを開く。開いていれば前面に出す。"""
        if self.macro_editor_window is None:
            self.macro_editor_window = MacroEditorWindow(self.translator, self)
            self.macro_editor_window.dictionary_requested.connect(self.show_dictionary_editor)
            self.macro_editor_controller = MacroEditorController(self.macro_editor_window, LOGGER)
            self.macro_execution_controller = MacroExecutionController(
                self.translator, LOGGER,
                lambda: self.editor,
                lambda target: target in self.tab_file_paths and any(
                    self._editor_at(index) is target for index in range(self.tab_widget.count())
                ),
                lambda target: str(self.tab_file_paths.get(target) or self._draft_title(target)),
                self.macro_editor_window,
                lambda target: self._preset_selected_scope(target),
                lambda target: self._visible_search_bounds(len(target.toPlainText())),
            )
            self.macro_editor_controller.execution_requested.connect(self.macro_execution_controller.preview_and_apply)
            if self.macro_folder:
                self.macro_editor_controller.session.macro_folder = Path(self.macro_folder)
            if self.macro_editor_geometry:
                self.macro_editor_window.restoreGeometry(QByteArray.fromBase64(self.macro_editor_geometry.encode("ascii", errors="ignore")))
            if self.macro_editor_splitter_state:
                self.macro_editor_window.splitter.restoreState(QByteArray.fromBase64(self.macro_editor_splitter_state.encode("ascii", errors="ignore")))
            self.macro_editor_window.update_status(self.macro_editor_controller.session)
        self.macro_editor_window.show()
        self.macro_editor_window.raise_()
        self.macro_editor_window.activateWindow()

    def show_dictionary_editor(self) -> None:
        """プリセットエディターから編集可能な挿入辞書を開く。"""
        user_folder = (
            self._resolve_user_dictionary_folder(self.user_dictionary_folder)
            if self.user_dictionary_folder else None
        )
        dialog = DictionaryEditorDialog(
            self.translator,
            DictionaryEditService(user_folder),
            self._dictionary_saved,
            self.macro_editor_window or self,
        )
        dialog.exec()

    def _dictionary_saved(self, save_file_path: Path) -> None:
        """検証済みのユーザー辞書を保存後に有効化する。"""
        default_user_folder = app_base_dir() / "user_dictionaries"
        self.user_dictionary_folder = (
            "user_dictionaries"
            if save_file_path.parent.resolve() == default_user_folder.resolve()
            else str(save_file_path.parent)
        )
        self._rebuild_insert_tag_menu()
        self._save_settings()

    def new_search_preset(self) -> None:
        """新しい検索・置換プリセットの編集を始める。"""
        self.show_macro_editor()
        if self.macro_editor_controller is not None:
            self.macro_editor_controller.new_document()
            self.macro_editor_window.macro_name.setFocus()  # type: ignore[union-attr]

    def run_search_preset(self) -> None:
        """保存済みのプリセットを開き、実行プレビューの前に内容を確認できるようにする。"""
        self.show_macro_editor()
        if self.macro_editor_controller is not None:
            self.macro_editor_controller.open_document()

    def edit_search_preset(self) -> None:
        """選択した検索・置換プリセットを編集画面で開く。"""
        self.run_search_preset()

    def capture_search_preset(
        self, find_text: str, replacement_text: str, options: SearchOptions
    ) -> None:
        """検索条件を開いているプリセットに追加し、必要なら新規定義を開く。"""
        editor_was_open = (
            self.macro_editor_window is not None and self.macro_editor_window.isVisible()
        )
        self.show_macro_editor()
        controller = self.macro_editor_controller
        if controller is None:
            return
        step = MacroEditorStepData(
            search_text=find_text,
            exclusion_enabled=bool(options.exclusion_text),
            exclusion_text=options.exclusion_text,
            replacement_enabled=not options.unicode_normalize,
            replacement_text=replacement_text,
            regular_expression=options.regular_expression,
            unicode_normalize=options.unicode_normalize,
            unicode_normalize_form=(
                options.unicode_normalize_form if options.unicode_normalize else None
            ),
            append_dot_to_circled_number=options.append_dot_to_circled_number,
            case_sensitive=options.case_sensitive,
            whole_word=options.whole_word,
            selected_only=options.selected_only,
            visible_only=options.visible_only,
        )
        if editor_was_open:
            controller.append_captured_step(step)
            return
        if controller.confirm_discard():
            controller.start_document(
                MacroEditorDocumentData(format_version=2, steps=[step]), needs_save=True
            )
            self.macro_editor_window.macro_name.setFocus()  # type: ignore[union-attr]

    def delete_search_preset(self) -> None:
        """検証済みのプリセットを復元可能な場所へ移動し、選択一覧から外す。"""
        folder = (
            self.macro_editor_controller.session.macro_folder
            if self.macro_editor_controller is not None
            else Path(self.macro_folder) if self.macro_folder else default_macro_folder()
        )
        name, _ = QFileDialog.getOpenFileName(
            self, self.translator.text("preset.delete"), str(folder), "JSON (*.json)"
        )
        if not name:
            return
        load_file_path = Path(name)
        try:
            MacroJsonLoader(folder).load(load_file_path)
        except (MacroJsonLoadError, OSError) as error:
            QMessageBox.warning(
                self, self.translator.text("preset.delete"),
                self.translator.text("preset.load_failed", error=str(error)),
            )
            return
        if QMessageBox.question(
            self, self.translator.text("preset.delete"),
            self.translator.text("preset.confirm_delete", path=str(load_file_path)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            deleted_folder = load_file_path.parent / ".deleted_presets"
            deleted_folder.mkdir(exist_ok=True)
            archived_name = (
                f"{load_file_path.stem}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}."
                f"{uuid.uuid4().hex[:8]}.json"
            )
            load_file_path.rename(deleted_folder / archived_name)
        except OSError as error:
            QMessageBox.critical(
                self, self.translator.text("preset.delete"),
                self.translator.text("preset.delete_failed", error=str(error)),
            )
            return
        controller = self.macro_editor_controller
        if controller is not None and controller.session.save_file_path == load_file_path:
            controller.session.save_file_path = None
            controller.session.load_file_path = None
            controller.window.update_status(controller.session)

    @staticmethod
    def _preset_selected_scope(editor: TextEditor) -> tuple[int, int] | None:
        """プリセット実行時に使う現在の選択範囲を取得する。"""
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            return None
        return (
            editor.cursor_position_to_text_position(cursor.selectionStart()),
            editor.cursor_position_to_text_position(cursor.selectionEnd()),
        )

    def show_tag_insert_dialog(self) -> None:
        """タグの定型項目を選んで挿入するダイアログを開く。"""
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

    def show_shortcut_settings_dialog(self) -> None:
        """ポータブルなショートカットとユーザー定義の定型文を編集する。"""
        if self.shortcut_settings_error:
            QMessageBox.warning(
                self, self.translator.text("shortcut.title"),
                self.translator.text("shortcut.load_error", error=self.shortcut_settings_error),
            )
            return
        dialog = ShortcutSettingsDialog(
            self.translator, self._shortcut_action_info, self.shortcut_settings, self
        )
        if dialog.exec() != ShortcutSettingsDialog.DialogCode.Accepted:
            return
        try:
            save_shortcut_settings(self.shortcut_settings_path, dialog.settings)
        except ShortcutSettingsError as error:
            QMessageBox.warning(
                self, self.translator.text("shortcut.title"),
                self.translator.text("shortcut.save_error", error=str(error)),
            )
            return
        self.shortcut_settings = dialog.settings
        self._apply_shortcut_settings()

    def show_options_dialog(self) -> None:
        """エディターとアプリの設定を変更するオプション画面を開く。"""
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
            show_full_path_in_title=self.show_full_path_in_title,
            inline_color_preview_enabled=self.inline_color_preview_enabled,
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
        self.show_full_path_in_title = values.show_full_path_in_title
        self.inline_color_preview_enabled = values.inline_color_preview_enabled
        self._update_window_title()
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
        """ユーザー辞書を検証し、問題があれば利用者に知らせる。"""
        if not dictionary_check_enabled or not user_dictionary_folder:
            return True
        try:
            dictionaries_path = self._resolve_user_dictionary_folder(user_dictionary_folder)
            tag_snippet_groups(dictionaries_path)
            load_paragraph_insert_rule_book(dictionaries_path)
        except (OSError, TypeError, ValueError) as error:
            LOGGER(
                error,
                "User dictionary validation failed",
                level=LogLevel.WARNING,
                action="validate_user_dictionaries",
                context={"load_file_path": user_dictionary_folder},
            )
            QMessageBox.critical(
                self,
                self.translator.text("dialog.dictionary_check_failed.title"),
                str(error),
            )
            return False
        return True

    def _tag_dictionaries_path(self) -> Path | None:
        """タグ挿入に使う辞書の場所を返す。"""
        if not self.user_dictionary_folder:
            return None
        return self._resolve_user_dictionary_folder(self.user_dictionary_folder)

    @staticmethod
    def _resolve_user_dictionary_folder(folder: str) -> Path:
        """ユーザー辞書の相対パスをアプリのフォルダーを基準に解決する。"""
        candidate = Path(folder)
        return candidate if candidate.is_absolute() else app_base_dir() / candidate

    def _internal_data_folder(self) -> Path:
        """ポータブル実行データ用のアプリ内部フォルダーを返す。"""
        return app_base_dir() / "_internal"

    def _unsaved_backup_path(self) -> Path:
        """未保存セッションを復元するファイルのパスを返す。"""
        return self._internal_data_folder() / "autosave" / "unsaved_backup.json"

    def _file_backup_folder_for_folder(self, backup_folder: str) -> Path:
        """保存済みファイルの世代バックアップを置くフォルダーを返す。"""
        if backup_folder:
            return Path(backup_folder)
        return self._internal_data_folder() / "backup"

    def _set_auto_save_timer_interval(self, interval_minutes: int) -> None:
        """復旧用履歴バックアップの実行間隔を設定する。"""
        self.auto_save_timer.setInterval(max(1, interval_minutes) * 60 * 1000)

    def _apply_editor_font_to_all_tabs(self) -> None:
        """現在のフォント設定を全タブに適用する。"""
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
        """現在のテーマの配色を全タブに適用する。"""
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
        """指定エディターに設定済みのタブ幅を適用する。"""
        space_width = editor.fontMetrics().horizontalAdvance(" ")
        editor.setTabStopDistance(space_width * self.tab_width)

    def _apply_search_marker_colors_to_all_tabs(self) -> None:
        """現在の検索マーカー色を全タブに適用する。"""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.set_search_marker_colors(
                    self.search_marker_color,
                    self.current_match_marker_color,
                )

    def _apply_visible_whitespace_options_to_all_tabs(self) -> None:
        """空白類の表示設定を全タブに適用する。"""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                self._apply_inline_color_preview(editor)
                editor.set_visible_whitespace_options(
                    spaces_enabled=self.visible_spaces_enabled,
                    tabs_enabled=self.visible_tabs_enabled,
                    newlines_enabled=self.visible_newlines_enabled,
                )

    def _apply_inline_color_preview(self, editor: TextEditor) -> None:
        """指定エディターに色見本の設定とファイル種別を反映する。"""
        path = self.tab_file_paths.get(editor)
        editor.set_inline_color_preview(
            self.inline_color_preview_enabled,
            stylesheet=path is not None and path.suffix.lower() == ".css",
        )

    def _choose_inline_color(self, editor: TextEditor, start: int, code: str) -> None:
        """選択パネルの確定時に、クリックした色だけを更新する。"""
        document = editor.document()
        revision = document.revision()
        cursor = QTextCursor(document)
        cursor.setPosition(start)
        cursor.setPosition(start + len(code), QTextCursor.MoveMode.KeepAnchor)
        if cursor.selectedText() != code:
            return
        dialog = InlineColorDialog(code, self.translator, self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        def apply_color() -> None:
            """対象文書と元の値を再照合して、選んだ色を適用する。"""
            if (
                editor not in self.tab_file_paths or self.editor is not editor
                or editor.document() is not document or document.revision() != revision
                or cursor.selectedText() != code
            ):
                self.statusBar().showMessage(self.translator.text("inline_color.stale"), 6000)
                return
            replacement = dialog.selectedColor().name(QColor.NameFormat.HexRgb)
            if replacement.lower() != code.lower():
                cursor.beginEditBlock()
                cursor.insertText(replacement.upper())
                cursor.endEditBlock()

        dialog.accepted.connect(apply_color)
        dialog.open()

    def _apply_visible_whitespace_marker_colors_to_all_tabs(self) -> None:
        """空白類のマーカー色を全タブに適用する。"""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.set_visible_whitespace_marker_colors(
                    space_color=self.visible_space_marker_color,
                    tab_color=self.visible_tab_marker_color,
                    newline_color=self.visible_newline_marker_color,
                )

    def _apply_fixed_column_wrap_options_to_all_tabs(self) -> None:
        """固定桁での折り返し設定を全タブに適用する。"""
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
        """既存の検索・置換ダイアログに正規表現の診断表示設定を適用する。"""
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.set_regex_lint_enabled(self.regex_lint_enabled)
            self.find_replace_dialog.set_reduced_error_check_enabled(
                self.reduced_error_check_enabled
            )

    def show_wordpress_preview(self) -> None:
        """現在の原稿をレンダリングし、簡易表示用のページを書き出してWordPressを停止する。"""
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

    def _ensure_simple_wordpress_preview(self) -> None:
        """簡易WordPressプレビューのコントローラーを用意する。"""
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
        """Twenty Twenty-Fiveのプレビューを、停止操作が行われるまで維持する。"""
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
        """プレビューの状態に合わせて停止アクションを更新する。"""
        self.stop_wordpress_preview_action.setEnabled(any(
            preview is not None and preview.running
            for preview in (self.wordpress_preview, self.wordpress_theme_preview)
        ))

    def _update_wordpress_status_label(self, _state: str = "") -> None:
        """WordPressプレビューの状態をステータス欄に表示する。"""
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
            entries.append(self.translator.text("wordpress_preview.status.stopped"))
        self.wordpress_status_label.setText(
            self.translator.text("wordpress_preview.status.label", details=" / ".join(entries))
        )
        details.insert(0, self.translator.text("wordpress_preview.status.help"))
        tooltip = escape("\n".join(details), quote=False).replace("\n", "<br>")
        self.wordpress_status_label.setToolTip(f"<qt>{tooltip}</qt>")

    def _wordpress_preview_progress(self, stage: str) -> None:
        """WordPressプレビューの準備や描画の進捗を表示する。"""
        self.statusBar().showMessage(self.translator.text(f"wordpress_preview.stage.{stage}"))

    def _wordpress_preview_failed(self, message: str) -> None:
        """プレビューの失敗を利用者へ知らせる。"""
        self.statusBar().showMessage(self.translator.text("wordpress_preview.failed"))
        QMessageBox.warning(self, self.translator.text("wordpress_preview.title"), message)

    def _wordpress_preview_rendered(self, version: str, _url: str) -> None:
        """簡易プレビューの描画完了を画面に反映する。"""
        self.statusBar().showMessage(self.translator.text("wordpress_preview.rendered", version=version))

    def _wordpress_theme_preview_rendered(self, version: str, _url: str) -> None:
        """テーマ付きプレビューの描画完了を画面に反映する。"""
        self.statusBar().showMessage(self.translator.text("wordpress_preview.theme_rendered", version=version))

    def _wordpress_preview_feedback(self, _request_id: int, status: int, warnings: str) -> None:
        """簡易プレビューの実行結果を受け取る。"""
        self._apply_wordpress_preview_feedback(self.wordpress_preview_snapshot, status, warnings)

    def _wordpress_theme_preview_feedback(self, _request_id: int, status: int, warnings: str) -> None:
        """テーマ付きプレビューの実行結果を受け取る。"""
        self._apply_wordpress_preview_feedback(self.wordpress_theme_preview_snapshot, status, warnings)

    def _apply_wordpress_preview_feedback(self, snapshot: tuple[TextEditor, str] | None, status: int, warnings: str) -> None:
        """元原稿との対応を確認し、プレビューの実行結果を表示する。"""
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
        """このウインドウのWordPressプレビューを停止する。"""
        if self.wordpress_preview is not None:
            self.wordpress_preview.stop()
        if self.wordpress_theme_preview is not None:
            self.wordpress_theme_preview.stop()
        self.wordpress_preview_snapshot = None
        self.wordpress_theme_preview_snapshot = None
        self.stop_wordpress_preview_action.setEnabled(False)
        self._update_wordpress_status_label()

    def show_core_block_repair(self) -> None:
        """元タブのWordPress修復候補を確認する。"""
        repair_core_blocks(
            self.editor, lambda: self._editor_at(self.tab_widget.currentIndex()),
            str(self.current_save_file_path or self._draft_title(self.editor)), self.translator, self,
            self.tab_widget,
        )

    def run_grammar_check(self) -> None:
        """現在の文書についてCSSまたはHTML・WordPressの文法を検査する。"""
        source_text = self.editor.toPlainText()
        messages = self._lint_document(source_text)
        if not messages:
            index = self._structure_indices.get(self.editor)
            if index is not None and any(pair.broken for pair in index.pairs):
                # A clean full check supersedes delimiter positions kept during editing.
                self._structure_sources[self.editor] = IndexedSource(source_text)
                self._structure_indices[self.editor] = CoreBlockIndex(source_text)
                self._structure_issues.pop(self.editor, None)
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
        """文書の現時点の内容を識別するハッシュを返す。"""
        return sha256(source_text.encode("utf-8")).hexdigest()

    def _lint_document(self, source_text: str) -> list[GrammarLintMessage]:
        """文書の形式に応じて文法チェッカーを実行する。"""
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
        """診断を重大度の高い順に並べ、同じ重大度では行順に並べる。"""
        return sorted(
            messages,
            key=lambda message: (
                GRAMMAR_SEVERITY_ORDER.get(message.severity, 99),
                message.line_number,
                message.message_key,
            ),
        )

    def _grammar_result_path_for_editor(self, editor: TextEditor) -> Path:
        """文書に対応する文法チェック結果の保存先を取得する。"""
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
        """本文と対応付けて文法チェックの結果を保存する。"""
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
        """現在の文書と一致する文法チェック結果を読み込む。"""
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
        """本文が変更された文書の文法チェック結果を無効にする。"""
        self._delete_grammar_lint_result(editor)
        if editor is self._current_editor() and self.grammar_check_dialog is not None:
            self._set_grammar_check_dialog_document_label(editor)
            self.grammar_check_dialog.set_result(
                self.translator.text("grammar_check.not_checked"),
                [],
            )

    def _delete_grammar_lint_result(self, editor: TextEditor) -> None:
        """指定文書の文法チェック結果を削除する。"""
        result_path = self.tab_grammar_result_paths.get(editor)
        if result_path is not None:
            self.grammar_lint_result_store.delete(result_path)

    def _clear_grammar_lint_results_on_window_close(self) -> None:
        """ウインドウの終了時に一時的な文法チェック結果を片付ける。"""
        for result_path in list(self.tab_grammar_result_paths.values()):
            self.grammar_lint_result_store.delete(result_path)
        self.tab_grammar_result_paths.clear()

        if not self._other_main_windows_are_open():
            self.grammar_lint_result_store.clear_result_folder()

    def _other_main_windows_are_open(self) -> bool:
        """ほかに開いているメインウインドウがあるか確認する。"""
        application = QApplication.instance()
        if not isinstance(application, QApplication):
            return False
        return any(
            isinstance(widget, MainWindow) and widget is not self and widget.isVisible()
            for widget in application.topLevelWidgets()
        )

    def _refresh_grammar_dialog_for_current_tab(self) -> None:
        """現在のタブに合わせて診断結果の表示を更新する。"""
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
        """文法チェックの対象となる文書の表示名を返す。"""
        save_file_path = self.tab_file_paths.get(editor)
        if save_file_path is not None:
            return save_file_path.name
        return self._draft_title(editor)

    def _set_grammar_check_dialog_document_label(self, editor: TextEditor) -> None:
        """文法チェック画面に対象文書の名前を表示する。"""
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
        """指定エディターの結果を文法チェック画面に表示する。"""
        self._show_grammar_check_dialog(summary, rows)
        self._set_grammar_check_dialog_document_label(editor)

    def _show_grammar_check_dialog(
        self,
        summary: str,
        rows: list[tuple[int, str]],
    ) -> None:
        """文法チェック画面を開き、要約と結果の一覧を表示する。"""
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
        """保存前の文法診断を確認し、保存を続けるか決める。"""
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
        """文法上の指摘がある行にマーカーを付ける。"""
        self.editor.set_grammar_issue_lines(
            [message.line_number for message in messages]
        )

    def _clear_grammar_issue_highlights(self) -> None:
        """文法チェックによる行マーカーを消す。"""
        self.editor.clear_grammar_issue_lines()

    def _grammar_check_summary(
        self,
        messages: list[GrammarLintMessage],
        limit: int = 20,
    ) -> str:
        """文法チェック結果の要約を表示用にまとめる。"""
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
        """文法診断の重大度と内容を表示用に整える。"""
        severity_label = self.translator.text(
            f"grammar_check.severity.{message.severity}"
        )
        kind_label = (
            self.translator.text(f"grammar_check.kind.{message.diagnostic_kind}") + " "
            if isinstance(message, HtmlTypoLintMessage) and message.diagnostic_kind
            else ""
        )
        return (
            f"{severity_label} {kind_label}"
            f"{self._html_typo_lint_message_text(message)}"
        )

    def _grammar_severity_count_text(
        self,
        messages: list[GrammarLintMessage],
    ) -> str:
        """文法診断を重大度ごとに数えて表示文字列にする。"""
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
        """HTMLやWordPressの診断を翻訳し、詳細を埋め込む。"""
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
        """1始まりで指定された行の先頭にカーソルを移動する。"""
        block = self.editor.document().findBlockByNumber(max(0, line_number - 1))
        if not block.isValid():
            return
        cursor = self.editor.textCursor()
        cursor.setPosition(block.position())
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def insert_tag_snippet(self, snippet: TagSnippet) -> None:
        """指定されたタグ定型文を現在のエディターのカーソル位置に挿入する。"""
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

    def insert_shortcut_template(self, key: str, value: str = "") -> None:
        """使用中の段落辞書からショートカット用テンプレートを挿入する。"""
        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText().replace("\u2029", "\n")
        try:
            insert_text, cursor_offset = load_paragraph_insert_rule_book(
                self._tag_dictionaries_path()
            ).render_shortcut(key, selected_text, value)
        except ParagraphInsertDictionaryError as error:
            QMessageBox.warning(
                self,
                self.translator.text("paragraph_split.error_title"),
                self.translator.text("paragraph_split.dictionary_error", error=str(error)),
            )
            return
        self.insert_text_at_cursor(insert_text, cursor_offset)

    def insert_paragraph_split_spacer(self) -> None:
        """現在の段落を分割し、WordPressのスペーサーブロックを挿入する。"""
        self._apply_paragraph_split_operation(
            lambda text, start, _end: split_paragraph_insert_spacer(
                text,
                start,
                self._tag_dictionaries_path(),
            )
        )

    def insert_paragraph_split_html(self) -> None:
        """現在の段落を分割し、選択部分をHTMLコードブロックで囲む。"""
        self._apply_paragraph_split_operation(
            lambda text, start, end: wrap_selection_as_code_block(
                text,
                start,
                end,
                self._tag_dictionaries_path(),
            )
        )

    def wrap_paragraph_split_decorated_block(self) -> None:
        """現在の段落を分割し、選択部分を装飾ブロックで囲む。"""
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
        """段落を分割する操作を検証し、現在の文書に適用する。"""
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
        """選択本文にタグ定型文を当てはめ、挿入する内容を作る。"""
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
        """現在の設定に合わせて枠ブロックのテンプレートを選ぶ。"""
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
        """枠の内側に設定するCSSを組み立てる。"""
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
        """設定から枠の配置に使う値を取得する。"""
        if self.frame_alignment in FRAME_ALIGNMENT_VALUES:
            return self.frame_alignment
        return "left"

    def _frame_outer_spacing_value(self) -> str:
        """設定から枠の外側の余白を取得する。"""
        if self.frame_outer_spacing.strip():
            return self.frame_outer_spacing.strip()
        return DEFAULT_FRAME_OUTER_SPACING

    def _frame_background_color_value(self) -> str:
        """設定から枠内の背景色を取得する。"""
        if self.frame_background_color.strip():
            return self.frame_background_color.strip()
        return "#fffaf0"

    def _frame_text_color_value(self) -> str:
        """設定から枠内の文字色を取得する。"""
        if self.frame_text_color.strip():
            return self.frame_text_color.strip()
        return "#333333"

    def insert_text_at_cursor(
        self,
        insert_text: str,
        cursor_offset: int | None = None,
    ) -> None:
        """現在のエディターのカーソル位置に指定文字列を挿入する。"""
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
        """可能な場合、最寄りの開始タグの内側に `style=""` を挿入する。"""
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
        """可能な場合、最寄りのstyle属性にCSS宣言を挿入する。"""
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
        """編集可能な背景色宣言を挿入し、推奨の色を表示する。"""
        self.insert_css_declaration_at_cursor(
            "background-color: ;",
            len("background-color: "),
        )
        self._show_background_color_preset_menu()

    def insert_text_color_at_cursor(self) -> None:
        """編集可能な文字色宣言を挿入し、色の選択肢を表示する。"""
        self.insert_css_declaration_at_cursor("color: ;", len("color: "))
        self._show_text_color_preset_menu()

    def _show_background_color_preset_menu(self) -> None:
        """現在のカーソルの下にWordPress向けの推奨背景色を表示する。"""
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
        """Ctrl+Altのインライン色ショートカットと同じ文字色を表示する。"""
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
        """編集可能なJSONから、インライン色のアクション名を現在の言語で取得する。"""
        color_name = preset.display_name(self.translator.language_code)
        return (
            f"{color_name} Text <span>"
            if self.translator.language_code == "en"
            else f"{color_name}文字 <span>"
        )

    @staticmethod
    def _background_color_swatch_icon(color_value: str) -> QIcon:
        """推奨背景色の小さな色見本を作る。"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(color_value))
        return QIcon(pixmap)

    def _replace_background_color_value(self, color_value: str) -> None:
        """エディターのカーソル位置にあるbackground-colorの値を置き換える。"""
        self._replace_css_color_value("background-color", color_value)

    def _replace_css_color_value(self, property_name: str, color_value: str) -> None:
        """既存のセミコロンを保持して、現在のCSS色プロパティの値を置き換える。"""
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
        """エディターの絶対位置へ指定文字列を挿入する。"""
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
        """カーソルに最も近い同一行の開始タグの範囲を返す。"""
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
        """カーソルに最も近い開始タグのstyle属性値の範囲を返す。"""
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
        """挿入先のstyle値に合う空白を付けたCSS宣言を返す。"""
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
        """引用符を保持したまま、選択した文字列だけをHTMLエスケープする。"""
        self._replace_selected_text(
            lambda selected_text: escape(selected_text, quote=False)
        )

    def unescape_selected_html(self) -> None:
        """選択した文字列だけのHTMLエスケープを解除する。"""
        self._replace_selected_text(unescape)

    def wrap_selected_as_wordpress_code_block(self) -> None:
        """選択した文字列をWordPressのカスタムHTMLコードブロックで囲む。"""

        def build_wordpress_code_block(selected_text: str) -> str:
            """選択本文からWordPress向けのコードブロックを組み立てる。"""
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
        """選択したMarkdownの表とリストをWordPressのブロックに変換する。"""
        self._convert_selected_markdown_to_wordpress(
            convert_complex_markdown_blocks_to_wordpress_html
        )

    def convert_selected_markdown_tables_to_wordpress_tables(self) -> None:
        """選択したMarkdownの表をWordPressの表に変換する。"""
        self._convert_selected_markdown_to_wordpress(
            convert_markdown_tables_to_wordpress_html
        )

    def convert_selected_markdown_lists_to_wordpress_lists(self) -> None:
        """選択したMarkdownのリストをWordPressのリストに変換する。"""
        self._convert_selected_markdown_to_wordpress(
            convert_markdown_lists_to_wordpress_html
        )

    def convert_selected_list_to_wordpress_frame(self) -> None:
        """選択したMarkdownまたはWordPressのリストを1つのHTML枠に変換する。"""
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
        """現在のMarkdown選択範囲をWordPressのブロックHTMLに変換する。"""
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
        """WordPress段落が入れ子にならないように、選択したMarkdownを置き換える。"""
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
        """段落の中身全体が選択されている場合は、ブロック全体の範囲を返す。"""
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
        """選択範囲がある場合に、変換後の文字列で置き換える。"""
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
        """現在のカーソル位置と文字数をステータスバーに反映する。"""
        cursor = self.editor.textCursor()
        line_number = cursor.blockNumber() + 1
        column_number = cursor.positionInBlock() + 1
        character_count = self._document_character_counts[self.editor].count
        self.statusBar().showMessage(
            self.translator.text(
                "status.position",
                line=line_number,
                column=column_number,
                characters=character_count,
            )
        )

    def _update_window_title(self) -> None:
        """現在の文書名と変更状態をメインウインドウのタイトルに反映する。"""
        load_file_path = self.current_save_file_path
        document_name = self.translator.text("document.untitled")
        if load_file_path is not None:
            document_name = (
                str(load_file_path.absolute())
                if self.show_full_path_in_title
                else load_file_path.name
            )
        changed_mark = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(
            f"{changed_mark}{document_name} - {self.translator.text('app.title')}"
        )

    def _confirm_discard_changes(self) -> bool:
        """内容を失う可能性がある操作の前に、未保存の変更を自動保存する。"""
        if not self.editor.document().isModified():
            return True
        return self._autosave_before_risky_operation()

    def _confirm_reload_current_file(self) -> bool:
        """未保存の本文が置き換わる場合に、ファイルを再読込するか確認する。"""
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
        """タブを閉じる前に変更内容を自動保存する。"""
        if not editor.document().isModified():
            return True

        tab_index = self.tab_widget.indexOf(editor)
        if tab_index >= 0:
            self.tab_widget.setCurrentIndex(tab_index)
        return self._autosave_before_risky_operation()

    def new_file(self) -> None:
        """無題の文書を持つエディターのタブを作る。"""
        self._create_editor_tab()
        self._update_window_title()

    def open_file(self, encoding: str | None = None) -> None:
        """ファイル選択画面を開き、選ばれたテキストファイルを新しいタブに読み込む。"""
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
            LOGGER(
                error,
                "File open failed",
                action="open_file",
                context={
                    "load_file_path": load_file_path,
                    "encoding": selected_encoding,
                },
            )
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
        """必要に応じて文字コードを指定し、現在のファイルをディスクから読み直す。"""
        if self.current_save_file_path is None:
            self._set_search_error(
                self.translator.text("dialog.reload_no_file"), clear_results=False
            )
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
            LOGGER(
                error,
                "File reload failed",
                action="reload_file",
                context={
                    "load_file_path": self.current_save_file_path,
                    "encoding": selected_encoding,
                },
            )
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
        """現在のファイルを保存し、成功した場合はTrueを返す。"""
        if self.current_save_file_path is None:
            return self.save_file_as()
        return self._save_to_path(self.current_save_file_path)

    def save_file_as(self) -> bool:
        """保存先を選ぶ画面を開いて現在のファイルを保存し、成功した場合はTrueを返す。"""
        selected_save_file_path, selected_encoding = self._get_save_file_path()
        if selected_save_file_path is None:
            return False
        self.current_encoding = selected_encoding
        return self._save_to_path(selected_save_file_path)

    def _suggest_unsaved_file_name(self) -> str:
        """未保存タブの1行目から安全なファイル名候補を作る。"""
        draft_title = self._draft_title(self.editor)
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", draft_title).strip(" .")
        if not name:
            name = self.translator.text("document.untitled")
        if name.split(".", 1)[0].upper() in {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
            "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
            "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
        }:
            name = f"_{name}"
        return name if Path(name).suffix else f"{name}.md"

    def _get_save_file_path(self) -> tuple[Path | None, str]:
        """保存先の画面を表示し、選択されたパスと文字コードを返す。"""
        dialog = QFileDialog(self, self.translator.text("dialog.save_as.title"))
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.selectFile(
            self.current_save_file_path.name
            if self.current_save_file_path
            else self._suggest_unsaved_file_name()
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
        """現在の本文を指定パスに保存し、成功した場合はTrueを返す。"""
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
            LOGGER(
                error,
                "File save failed",
                action="save_file",
                context={
                    "save_file_path": save_file_path,
                    "encoding": self.current_encoding,
                },
            )
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
        """保存済みファイルのバックアップまたは未保存のスナップショットを復元する。"""
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
            LOGGER(
                error,
                "File backup restore failed",
                action="restore_file_backup",
                context={
                    "load_file_path": backup_path,
                    "encoding": self.current_encoding,
                },
            )
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
        """保存済みファイルのバックアップを画面に表示する名前を返す。"""
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
        """未保存の自動バックアップを画面に表示する名前を返す。"""
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
        """タブの状態を失う可能性がある操作の前に、変更済みタブを自動保存する。"""
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
        """未保存の変更があるタブが1つでもあればTrueを返す。"""
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None and editor.document().isModified():
                return True
        return False

    def _save_unsaved_backup(self) -> bool:
        """変更済みタブを復元可能なセッションとして保存する。"""
        if not self.unsaved_backup_enabled or self.restoring_unsaved_backup:
            return True
        session = self._build_unsaved_backup_session()
        if session is None:
            self._clear_unsaved_backup()
            return True
        return self.unsaved_backup_manager.save_session(session)

    def _save_unsaved_backup_snapshot(self) -> bool:
        """最新の未保存バックアップと履歴用のスナップショットを保存する。"""
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
        """変更済みタブをまとめて復元できるセッションを作る。"""
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
        """未保存バックアップがある場合に、復元するかを確認して読み込む。"""
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
        """未保存バックアップのセッションをエディターのタブに復元する。"""
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
        """未保存バックアップが有効でファイルが存在する場合に削除する。"""
        if self.unsaved_backup_enabled:
            self.unsaved_backup_manager.clear()

    def _find_replace_target_name(self) -> str:
        """検索窓を開いた元のタブの現在の表示名を返す。"""
        target = self._find_replace_target
        if target is None:
            return ""
        save_file_path = self.tab_file_paths.get(target)
        return save_file_path.name if save_file_path is not None else self._draft_title(target)

    def _activate_find_replace_target(self) -> bool:
        """検索窓からの操作前に元のタブを表示する。別のタブへは切り替えない。"""
        target = self._find_replace_target
        if target is None:
            return False
        for index in range(self.tab_widget.count()):
            if self._editor_at(index) is target:
                if self.editor is not target:
                    self._activating_find_replace_target = True
                    try:
                        self.tab_widget.setCurrentIndex(index)
                    finally:
                        self._activating_find_replace_target = False
                return self.editor is target
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.close()
        return False

    def _run_bound_find_replace(self, action: Callable[..., object], *args: object) -> None:
        """検索・置換ダイアログの操作を元のエディターにだけ渡す。"""
        if self._activate_find_replace_target():
            action(*args)

    def show_find_replace_dialog(self) -> None:
        """検索・置換ダイアログを開く。初回は本文の選択文字列があれば検索欄に入れる。"""
        first_open = self.find_replace_dialog is None
        if self.find_replace_dialog is None:
            self.find_replace_dialog = FindReplaceDialog(self.translator, self)
            self.find_replace_dialog.set_regex_lint_enabled(self.regex_lint_enabled)
            self.find_replace_dialog.set_reduced_error_check_enabled(
                self.reduced_error_check_enabled
            )
            self.find_replace_dialog.find_requested.connect(
                lambda *args: self._run_bound_find_replace(self.find_next, *args)
            )
            self.find_replace_dialog.find_previous_requested.connect(
                lambda *args: self._run_bound_find_replace(self.find_previous, *args)
            )
            self.find_replace_dialog.replace_requested.connect(
                lambda *args: self._run_bound_find_replace(self.replace_current, *args)
            )
            self.find_replace_dialog.replace_all_requested.connect(
                lambda *args: self._run_bound_find_replace(self._replace_all_from_dialog, *args)
            )
            self.find_replace_dialog.replace_marked_requested.connect(
                lambda *args: self._run_bound_find_replace(self.replace_marked_matches, *args)
            )
            self.find_replace_dialog.preview_requested.connect(
                lambda *args: self._run_bound_find_replace(self.preview_matches, *args)
            )
            self.find_replace_dialog.preview_line_requested.connect(
                lambda *args: self._run_bound_find_replace(self._jump_to_preview_line, *args)
            )
            self.find_replace_dialog.preview_cleared.connect(
                self._clear_preview_source
            )
            self.find_replace_dialog.search_parameters_changed.connect(
                lambda *args: self._run_bound_find_replace(self._search_parameters_changed, *args)
            )
            self.find_replace_dialog.selection_scope_reset_requested.connect(
                lambda: self._run_bound_find_replace(self.reset_search_scope_reference)
            )
            self.find_replace_dialog.regex_help_requested.connect(self.show_regex_help_dialog)
            self.find_replace_dialog.normalise_requested.connect(
                lambda *args: self._run_bound_find_replace(self.apply_regex_normalise_operation, *args)
            )
            self.find_replace_dialog.preset_requested.connect(
                lambda *args: self._run_bound_find_replace(self.capture_search_preset, *args)
            )
            self.find_replace_dialog.finished.connect(self._on_find_replace_dialog_closed)

        if self.find_replace_dialog.isVisible():
            if not self._activate_find_replace_target():
                return
            self.find_replace_dialog.raise_()
            self.find_replace_dialog.activateWindow()
            return

        self._find_replace_target = self.editor
        self.find_replace_dialog.set_target_file_name(self._find_replace_target_name())

        selected_text = self.editor.textCursor().selectedText()
        if selected_text:
            cursor = self.editor.textCursor()
            selection = (
                self.editor,
                self.editor.cursor_position_to_text_position(cursor.selectionStart()),
                self.editor.cursor_position_to_text_position(cursor.selectionEnd()),
            )
            self.search_scope = (
                None if selection == self._scope_selection_to_ignore
                else selection[1:]
            )
            if first_open:
                self.find_replace_dialog.set_find_text(selected_text.replace("\u2029", "\n"))
        else:
            self.search_scope = None
        self.find_replace_dialog.clear_error()
        self.find_replace_dialog.show()
        self.find_replace_dialog.raise_()
        self.find_replace_dialog.activateWindow()

    def _on_find_replace_dialog_closed(self, _result: int) -> None:
        """本文の選択を保ったまま検索の表示マーカーを破棄する。"""
        self._preview_source = None
        self._find_replace_target = None
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.clear_preview_rows()
            self.find_replace_dialog.set_target_file_name("")
        self._marked_source = None
        self._marked_editor = None
        self.search_scope = None
        for tab_index in range(self.tab_widget.count()):
            editor = self._editor_at(tab_index)
            if editor is not None:
                editor.clear_search_matches()

    def _clear_preview_source(self) -> None:
        """プレビューの行を消すときに、元文書への参照も破棄する。"""
        self._preview_source = None

    def reset_search_scope_reference(self) -> None:
        """古い検索範囲を破棄し、エディターの現在の選択範囲を取り直す。"""
        self.search_scope = None
        self._scope_selection_to_ignore = None
        self._search_highlights_suspended = False
        if self.find_replace_dialog is None:
            return
        self.update_search_highlights(
            self.find_replace_dialog.find_text_edit.text(),
            self.find_replace_dialog.current_search_options(),
        )

    def find_next(self, search_text: str, options: SearchOptions) -> None:
        """指定された検索条件で次の一致箇所を探す。"""
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
        """指定された検索条件で前の一致箇所を探す。"""
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
        """現在選択されている一致箇所を、指定された文字列と条件で置き換える。"""
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
        selected_reference = (self.editor, selected_match.start, selected_match.end)
        if (
            options.selected_only
            and scope_text is None
            and cursor.hasSelection()
            and selected_reference == self._scope_selection_to_ignore
        ):
            scope_text, scope_offset = selected_match.text, selected_match.start
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
        replaced_end = len(result.text) - (len(source_text) - selected_match.end)
        self._set_cursor_position(replaced_end)
        self._clear_search_results_after_operation()
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
        """指定された条件で一致するすべての箇所を置換する。"""
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
                self._set_search_preview(rows, summary)
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
        else:
            result_text = result.text

        self._replace_document_text(result_text)
        self._clear_search_results_after_operation()
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
        """検索窓の条件で全置換を開始する。"""
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
        """全置換の範囲と件数を確認して続行を決める。"""
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
            self._set_search_preview(rows, summary)
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
        """指定された条件で、マーカーのあるすべての一致箇所を置換する。"""
        if not search_text:
            self._set_search_error(self.translator.text("search.empty"))
            return
        if not self.editor.search_matches:
            self._set_search_error(self.translator.text("search.no_replacements"))
            return

        result_text = self.editor.toPlainText()
        original_text = result_text
        replacement_count = 0
        try:
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
                if match.start < 0 or match.end > len(original_text):
                    continue
                if (
                    (match.start, match.end) not in allowed_ranges
                    or original_text[match.start:match.end] != match.text
                ):
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
        self._clear_search_results_after_operation()
        self._set_search_status(
            self.translator.text("search.replaced_many", count=replacement_count)
        )
        self._focus_find_text_after_replace_all()

    def apply_regex_normalise_operation(self, operation_id: str) -> None:
        """指定された正規化操作を対象文書に適用する。"""
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
        else:
            result_text = result.text

        self._replace_document_text(result_text)
        self._clear_search_results_after_operation()
        self._set_search_status(
            self.translator.text("normalise.applied", count=result.count)
        )
        self._focus_find_text_after_replace_all()

    def _search_parameters_changed(
        self,
        search_text: str,
        options: SearchOptions,
    ) -> None:
        """利用者が検索条件を変更したときに、マーカーの再計算を再開する。"""
        self._search_highlights_suspended = False
        self.refresh_search_highlights(search_text, options)

    def _clear_search_results_after_operation(self) -> None:
        """古い結果マーカー、プレビュー、選択範囲の参照を破棄する。"""
        self._search_highlights_suspended = True
        self._marked_source = None
        self._marked_editor = None
        self.search_scope = None
        self._preview_source = None
        cursor = self.editor.textCursor()
        self._scope_selection_to_ignore = (
            (
                self.editor,
                self.editor.cursor_position_to_text_position(cursor.selectionStart()),
                self.editor.cursor_position_to_text_position(cursor.selectionEnd()),
            ) if cursor.hasSelection() else None
        )
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.clear_preview_rows()
        self.editor.clear_search_matches()

    def refresh_search_highlights(
        self,
        search_text: str,
        options: SearchOptions,
    ) -> None:
        """現在の明示的な検索操作に応じてマーカーを再計算する。"""
        if (
            self.reduced_error_check_enabled
            or self._search_highlights_suspended
            or self.find_replace_dialog is None
            or not self.find_replace_dialog.isVisible()
        ):
            self._marked_source = None
            self._marked_editor = None
            self.editor.clear_search_matches()
            return
        self.update_search_highlights(search_text, options)

    def _focus_find_text_after_replace_all(self) -> None:
        """全置換後に検索欄へフォーカスを戻す。"""
        self._focus_find_text_after_replace_all_now()

    def _focus_find_text_after_replace_all_now(self) -> None:
        """検索欄へフォーカスを移して入力内容を編集できるようにする。"""
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
        """現在の検索文字列と検索条件からエディターのマーカーを更新する。"""
        self._marked_source = None
        self._marked_editor = None
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
            exclusion_matches = self.search_engine.find_exclusion_matches(
                source_text,
                options,
                max_matches=MAX_AUTO_SEARCH_HIGHLIGHTS,
            )
        except RegexError:
            self.editor.clear_search_matches()
            return

        scope_bounds: tuple[int, int] | None = None
        if options.selected_only:
            scope_bounds = (scope_offset, scope_offset + len(source_text))

        indexed_source = IndexedSource(self.editor.toPlainText())
        adjusted_matches = [
                SearchMatch(
                    match.start + scope_offset,
                    match.end + scope_offset,
                    match.text,
                )
                for match in matches
            ]
        adjusted_exclusions = [
                SearchMatch(
                    match.start + scope_offset,
                    match.end + scope_offset,
                    match.text,
                )
                for match in exclusion_matches
            ]
        positions = {position for match in (*adjusted_matches, *adjusted_exclusions)
                     for position in (match.start, match.end)}
        if scope_bounds is not None:
            positions.update(scope_bounds)
        self.editor.set_search_matches(
            adjusted_matches,
            adjusted_exclusions,
            scope_bounds,
            position_map={position: indexed_source.qt_position(position) for position in positions},
        )
        self._marked_source = indexed_source
        self._marked_editor = self.editor
        self._marked_query = search_text
        self._marked_options = options

    def _editor_contents_changed_for_search(
        self, editor: TextEditor, qt_position: int, removed: int, added: int
    ) -> None:
        """編集箇所の周辺だけで単純検索のマーカーを更新し、局所更新できない条件では古いマーカーを破棄する。"""
        if self._preview_source is not None and editor is self._preview_source[0]:
            self._preview_source = None
            if (
                not self._search_internal_text_change
                and self.find_replace_dialog is not None
            ):
                self.find_replace_dialog.clear_preview_rows()
        scope_owner = self._find_replace_target or self.editor
        if editor is scope_owner and not self._search_internal_text_change:
            self.search_scope = None
        indexed_source = self._marked_source
        if indexed_source is None or editor is not self._marked_editor:
            return
        if self._search_internal_text_change or self._search_highlights_suspended:
            self._marked_source = None
            self._marked_editor = None
            editor.clear_search_matches()
            return

        options = self._marked_options
        if (
            options.regular_expression
            or options.exclusion_text
            or options.selected_only
            or options.visible_only
            or options.unicode_normalize
        ):
            self._marked_source = None
            self._marked_editor = None
            editor.clear_search_matches()
            return

        added_cursor = QTextCursor(editor.document())
        added_cursor.setPosition(qt_position)
        added_cursor.setPosition(
            min(qt_position + added, editor.document().characterCount() - 1),
            QTextCursor.MoveMode.KeepAnchor,
        )
        added_text = added_cursor.selectedText().replace("\u2029", "\n")
        old_text_length = len(indexed_source.text)
        start, old_end, delta = indexed_source.replace(qt_position, removed, added_text)

        query_length = len(self._marked_query)
        affected_left = max(0, start - query_length + 1)
        affected_right = min(old_text_length, old_end + query_length)
        scan_left = max(0, affected_left - 1)
        scan_right = min(old_text_length, affected_right + 1)
        new_affected_right = affected_right + delta
        new_scan_right = scan_right + delta
        retained = [
            match for match in editor.search_matches if match.end <= affected_left
        ]
        retained.extend(
            SearchMatch(match.start + delta, match.end + delta, match.text)
            for match in editor.search_matches
            if match.start >= affected_right
        )
        local_text = indexed_source.text[scan_left:new_scan_right]
        try:
            nearby = self.search_engine.find_all(
                local_text, self._marked_query, options,
                max_matches=MAX_AUTO_SEARCH_HIGHLIGHTS,
            )
        except RegexError:
            self._marked_source = None
            self._marked_editor = None
            editor.clear_search_matches()
            return
        retained.extend(
            SearchMatch(match.start + scan_left, match.end + scan_left, match.text)
            for match in nearby
            if match.end + scan_left > affected_left
            and match.start + scan_left < new_affected_right
        )
        updated = sorted(retained, key=lambda match: match.start)[
            :MAX_AUTO_SEARCH_HIGHLIGHTS
        ]
        if updated != editor.search_matches:
            positions = {position for match in updated for position in (match.start, match.end)}
            editor.set_search_matches(
                updated,
                position_map={position: indexed_source.qt_position(position) for position in positions},
            )

    def _editor_contents_changed_for_structure(
        self, editor: TextEditor, qt_position: int, removed: int, added: int
    ) -> None:
        """文書の編集箇所の周辺にあるWordPressコメントの対応を検査する。"""
        source = self._structure_sources.get(editor)
        if source is None:
            block = editor.document().findBlock(qt_position)
            if block.isValid() and "wp:" in block.text() and "<!--" in block.text():
                source_text = editor.toPlainText()
                source = IndexedSource(source_text)
                index = CoreBlockIndex(source_text)
                self._structure_sources[editor] = source
                self._structure_indices[editor] = index
                editor.set_grammar_issue_lines(
                    [
                        bisect_right(source.python_line_starts, pair.open_start)
                        for pair in index.pairs if pair.broken
                    ]
                )
            else:
                editor.clear_grammar_issue_lines()
            return

        added_cursor = QTextCursor(editor.document())
        added_cursor.setPosition(qt_position)
        added_cursor.setPosition(
            min(qt_position + added, editor.document().characterCount() - 1),
            QTextCursor.MoveMode.KeepAnchor,
        )
        added_text = added_cursor.selectedText().replace("\u2029", "\n")
        previous_length = len(source.text)
        start, old_end, delta = source.replace(qt_position, removed, added_text)
        if start == 0 and old_end == previous_length and removed > 0:
            self._structure_indices[editor] = CoreBlockIndex(source.text)
            self._structure_issues.pop(editor, None)
            touched = []
        else:
            fragment_start = source.text.rfind("\n", 0, start) + 1
            fragment_end = source.text.find("\n", start + len(added_text))
            if fragment_end < 0:
                fragment_end = len(source.text)
            touched = self._structure_indices[editor].apply_change(
                start, old_end, delta, added_text, source.text,
                fragment=source.text[fragment_start:fragment_end],
                fragment_start=fragment_start,
            )
        issues = self._structure_issues.setdefault(editor, {})
        for pair in touched:
            if pair.broken or pair.close_end is None:
                issues.pop(id(pair), None)
                continue
            block_text = source.text[pair.open_start:pair.close_end]
            issues[id(pair)] = [
                message.line_number
                for message in lint_html_typos(block_text)
                if message.severity != "info"
                # 色メニューで値を選ぶ間の空欄は一時的。手動・保存時の全文チェックでは検出する。
                and message.message_key != "css_lint.empty_value"
            ]
        issue_lines: set[int] = set()
        for pair in self._structure_indices[editor].pairs:
            first_line = bisect_right(source.python_line_starts, pair.open_start)
            if pair.broken:
                issue_lines.add(first_line)
            else:
                issue_lines.update(
                    first_line + relative_line - 1
                    for relative_line in issues.get(id(pair), [])
                )
        if sorted(issue_lines) != editor.grammar_issue_lines:
            editor.set_grammar_issue_lines(sorted(issue_lines))

    def preview_matches(
        self,
        search_text: str,
        replace_text: str,
        options: SearchOptions,
    ) -> None:
        """現在の検索・置換条件で見つかる箇所をダイアログにプレビューする。"""
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

        self._set_search_preview(rows, summary)
        self._set_search_status(summary)
        self._search_highlights_suspended = False
        self.refresh_search_highlights(search_text, options)

    def _set_search_preview(
        self, rows: list[tuple[int, str, str]], summary: str
    ) -> None:
        """表示したプレビュー行を現在の文書リビジョンと対応付ける。"""
        if self.find_replace_dialog is None:
            return
        self._preview_source = (self.editor, self.editor.document().revision())
        self.find_replace_dialog.set_preview_rows(rows, summary)

    def _jump_to_preview_line(self, line_number: int) -> None:
        """プレビュー元のタブを表示し、指定行にカーソルを置く。"""
        if self._preview_source is None or self.find_replace_dialog is None:
            return
        preview_editor, revision = self._preview_source
        tab_index = next(
            (
                index
                for index in range(self.tab_widget.count())
                if self._editor_at(index) is preview_editor
            ),
            -1,
        )
        if tab_index < 0 or preview_editor.document().revision() != revision:
            self.find_replace_dialog.clear_preview_rows()
            self._preview_source = None
            return
        block = preview_editor.document().findBlockByNumber(line_number - 1)
        if not block.isValid():
            return
        self.tab_widget.setCurrentIndex(tab_index)
        cursor = preview_editor.textCursor()
        cursor.setPosition(block.position())
        preview_editor.setTextCursor(cursor)
        preview_editor.ensureCursorVisible()
        preview_editor.setFocus()

    def _replacement_preview_summary(self, match_count: int, shown_count: int) -> str:
        """置換プレビューの件数や制限を要約する。"""
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
        """必要なら作成して正規表現ヘルプを開く。"""
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
        """必要なら作成して操作ヘルプを開く。"""
        if self.user_help_dialog is None:
            self.user_help_dialog = UserHelpDialog(self.translator, self)

        self.user_help_dialog.show()
        self.user_help_dialog.raise_()
        self.user_help_dialog.activateWindow()

    def show_schema_reference_dialog(self) -> None:
        """HTMLやWordPressなどの参考表をエディターの横にモードレスで表示する。"""
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

    def show_unicode_character_info_dialog(self) -> None:
        """選択先頭またはカーソル位置の1文字を読み取り専用で表示する。"""
        cursor = self.editor.textCursor()
        from_selection = cursor.hasSelection()
        character = character_at_cursor(cursor)
        info = inspect_character(character[0]) if character else None
        if self.unicode_character_info_dialog is None:
            self.unicode_character_info_dialog = UnicodeCharacterInfoDialog(
                info, from_selection, self.translator, self
            )
        else:
            self.unicode_character_info_dialog.set_character(info, from_selection)
        self.unicode_character_info_dialog.show()
        self.unicode_character_info_dialog.raise_()
        self.unicode_character_info_dialog.activateWindow()

    def _insert_regex_pattern(self, pattern: str) -> None:
        """検索・置換ダイアログの検索欄に指定の正規表現パターンを挿入する。"""
        if self.find_replace_dialog is None:
            self.show_find_replace_dialog()
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.insert_find_text(pattern)

    def _search_scope_text(self, options: SearchOptions) -> tuple[str | None, int]:
        """検索条件から現在の対象範囲の文字列と文書内の開始位置を求める。"""
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
        """検索対象となる選択範囲の両端を求め、有効な選択がなければNoneを返す。"""
        if self.search_scope is None:
            cursor = self.editor.textCursor()
            if not cursor.hasSelection():
                return None
            selection = (
                self.editor,
                self.editor.cursor_position_to_text_position(cursor.selectionStart()),
                self.editor.cursor_position_to_text_position(cursor.selectionEnd()),
            )
            if selection == self._scope_selection_to_ignore:
                return None
            self.search_scope = selection[1:]

        scope_start, scope_end = self.search_scope
        if scope_start >= scope_end or scope_end > source_length:
            return None
        return scope_start, scope_end

    def _visible_search_bounds(self, source_length: int) -> tuple[int, int] | None:
        """検索対象となる表示範囲の両端を求め、有効な表示範囲がなければNoneを返す。"""
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
        """一致箇所全体が指定の検索範囲に収まるかを確認する。"""
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
        """対象範囲内の一致箇所から置換プレビューを生成する。"""
        rows: list[tuple[int, str, str]] = []
        preview_options = replace(options, exclusion_text="")
        full_source_text = self.editor.toPlainText()
        line_starts = [0] + [
            index + 1 for index, character in enumerate(full_source_text)
            if character == "\n"
        ]
        for match in matches[:200]:
            absolute_start = scope_offset + match.start
            line_number = bisect_right(line_starts, absolute_start)
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
        """置換後の文字列を含む行の表示用情報を返す。"""
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
        """一致した箇所を含む行の前後を取り出し、一致部分を区別する。"""
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
        """一致箇所を置換後の文字列にした場合の行の前後を取り出す。"""
        line_start = source_text.rfind("\n", 0, match.start) + 1
        line_end = source_text.find("\n", match.end)
        if line_end == -1:
            line_end = len(source_text)
        prefix = source_text[line_start : match.start]
        suffix = source_text[match.end : line_end]
        return self._visible_preview_text(f"{prefix}{replacement_text}{suffix}")

    def _visible_preview_text(self, text: str) -> str:
        """タブと改行を見える表記にし、必要なら省略してプレビュー文字列を作る。"""
        visible_text = text.replace("\t", "\\t").replace("\n", "\\n")
        if len(visible_text) > 140:
            return f"{visible_text[:137]}..."
        return visible_text

    def _replace_document_text(self, text: str) -> None:
        """エディターの文書全体を指定文字列で置き換える。"""
        cursor = self.editor.textCursor()
        self._search_internal_text_change = True
        try:
            cursor.beginEditBlock()
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText(text)
            cursor.endEditBlock()
        finally:
            self._search_internal_text_change = False

    def _select_match(self, match: SearchMatch) -> None:
        """一致箇所の先頭を基準に、現在の検索結果をエディターの中央付近に表示する。"""
        cursor = self.editor.textCursor()
        cursor.setPosition(self.editor.text_position_to_cursor_position(match.end))
        cursor.setPosition(
            self.editor.text_position_to_cursor_position(match.start),
            QTextCursor.MoveMode.KeepAnchor,
        )
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()
        self.editor.centerCursor()
        self._clear_search_results_after_operation()
        self.editor.mark_current_search_match()

    def _set_cursor_position(self, position: int) -> None:
        """指定された本文位置へエディターのカーソルを移動する。"""
        cursor = self.editor.textCursor()
        cursor.setPosition(self.editor.text_position_to_cursor_position(position))
        self.editor.setTextCursor(cursor)

    def _set_search_error(self, message: str, *, clear_results: bool = True) -> None:
        """指定された検索エラーを検索・置換ダイアログとステータスバーに表示する。"""
        if clear_results:
            self._clear_search_results_after_operation()
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.set_error(message)
        self.statusBar().showMessage(message)

    def _set_search_status(self, message: str) -> None:
        """検索状況をステータスバーに表示し、検索・置換ダイアログのエラーを消す。"""
        if self.find_replace_dialog is not None:
            self.find_replace_dialog.clear_error()
        self.statusBar().showMessage(message)

    def _set_encoding_status(self) -> None:
        """現在の文字コードをステータスバーに表示する。"""
        self.statusBar().showMessage(
            self.translator.text("status.encoding", encoding=self.current_encoding)
        )


def main() -> int:
    """アプリケーションを起動する。"""
    install_exception_hooks(LOGGER)
    LOGGER.info("Regex Pad started", action="application_start")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = MainWindow()
    window.setWindowIcon(QIcon(str(ICON_PATH)))
    window.show()
    exit_code = app.exec()
    LOGGER.info(
        "Regex Pad stopped",
        action="application_stop",
        context={"exit_code": exit_code},
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
