from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor, QFontDatabase, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from editor.tag_insert import wordpress_mode_label_keys
from localization.translator import Translator
from portable_runtime import app_base_dir
from settings.settings_manager import EditorSettings

COLOR_PRESETS: tuple[tuple[str, str], ...] = (
    ("Yellow", "#ffff00"),
    ("Orange", "#ff9900"),
    ("Green", "#b6f2a5"),
    ("Blue", "#9ed8ff"),
    ("Pink", "#ffb3d9"),
    ("Gray", "#d9d9d9"),
)
ENCODING_PRESETS: tuple[tuple[str, str], ...] = (
    ("UTF-8", "utf-8"),
    ("UTF-8 with BOM", "utf-8-sig"),
    ("CP932 / Shift_JIS", "cp932"),
    ("Shift_JIS", "shift_jis"),
    ("EUC-JP", "euc_jp"),
    ("UTF-16", "utf-16"),
    ("UTF-16 LE", "utf-16-le"),
    ("UTF-16 BE", "utf-16-be"),
)
NEWLINE_PRESETS: tuple[tuple[str, str], ...] = (
    ("LF", "lf"),
    ("CRLF", "crlf"),
    ("CR", "cr"),
)
FRAME_ALIGNMENT_PRESETS: tuple[tuple[str, str], ...] = (
    ("options.frame_alignment.left", "left"),
    ("options.frame_alignment.center", "center"),
    ("options.frame_alignment.right", "right"),
)
FRAME_DISPLAY_PRESETS: tuple[tuple[str, str], ...] = (
    ("options.frame_display.inline_block", "inline-block"),
    ("options.frame_display.inline_grid", "inline-grid"),
    ("options.frame_display.block", "block"),
    ("options.frame_display.grid", "grid"),
)
FRAME_OUTER_SPACING_PRESETS: tuple[tuple[str, str], ...] = (
    ("options.frame_outer_spacing.none", "0"),
    ("options.frame_outer_spacing.narrow", "0.75em 0 1em 0"),
    ("options.frame_outer_spacing.standard", "1.5em 0 2em 0"),
    ("options.frame_outer_spacing.wide", "2em 0 3em 0"),
)
FRAME_BACKGROUND_COLOR_PRESETS: tuple[tuple[str, str], ...] = (
    ("options.frame_background_color.orange", "#fffaf0"),
    ("options.frame_background_color.white", "#ffffff"),
    ("options.frame_background_color.blue", "#f0f9ff"),
    ("options.frame_background_color.green", "#f7fff2"),
    ("options.frame_background_color.gray", "#f7f7f7"),
    ("options.frame_background_color.transparent", "transparent"),
)
FRAME_TEXT_COLOR_PRESETS: tuple[tuple[str, str], ...] = (
    ("options.frame_text_color.dark", "#333333"),
    ("options.frame_text_color.black", "#000000"),
    ("options.frame_text_color.brown", "#5c3b00"),
    ("options.frame_text_color.blue", "#14384f"),
    ("options.frame_text_color.green", "#214c32"),
    ("options.frame_text_color.gray", "#666666"),
)
EDITOR_THEME_PRESETS: tuple[tuple[str, str, str, str, str, str], ...] = (
    ("options.editor_theme.light", "light", "#ffffff", "#202124", "#0b5cad", "#667085"),
    ("options.editor_theme.soft", "soft", "#fffaf0", "#333333", "#8a4b00", "#8a6f4d"),
    ("options.editor_theme.dark", "dark", "#1f2933", "#f5f7fa", "#7cc4ff", "#a8b3c2"),
    (
        "options.editor_theme.high_contrast",
        "high_contrast",
        "#000000",
        "#ffffff",
        "#00d9ff",
        "#c8c8c8",
    ),
    ("options.editor_theme.custom", "custom", "#ffffff", "#202124", "#0b5cad", "#667085"),
)


@dataclass(frozen=True)
class OptionsDialogValues:
    word_wrap_enabled: bool
    line_numbers_enabled: bool
    ruler_enabled: bool
    visible_spaces_enabled: bool
    visible_tabs_enabled: bool
    visible_newlines_enabled: bool
    fixed_column_wrap_enabled: bool
    fixed_column_wrap_column: int
    startup_restore_enabled: bool
    show_full_path_in_title: bool
    inline_color_preview_enabled: bool
    language_code: str
    default_encoding: str
    newline_code: str
    wordpress_mode_label_key: str
    hover_hints_enabled: bool
    user_dictionary_folder: str
    dictionary_check_enabled: bool
    backup_folder: str
    backup_retention_count: int
    backup_retention_days: int
    auto_backup_interval_minutes: int
    font_family: str
    font_size: int
    tab_width: int
    editor_theme: str
    editor_background_color: str
    editor_text_color: str
    html_tag_color: str
    wordpress_core_block_color: str
    search_marker_color: str
    current_match_marker_color: str
    visible_space_marker_color: str
    visible_tab_marker_color: str
    visible_newline_marker_color: str
    regex_lint_enabled: bool
    html_typo_lint_enabled: bool
    reduced_error_check_enabled: bool
    frame_alignment: str
    frame_display: str
    frame_outer_spacing: str
    frame_background_color: str
    frame_text_color: str


class OptionsDialog(QDialog):
    def __init__(
        self,
        translator: Translator,
        settings: EditorSettings,
        parent: QWidget | None = None,
        default_backup_folder_path: Path | None = None,
        unsaved_backup_path: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.translator = translator
        self.wordpress_mode_keys = wordpress_mode_label_keys()
        self.default_backup_folder_path = (
            default_backup_folder_path or app_base_dir() / "_internal" / "backup"
        )
        self.unsaved_backup_path = (
            unsaved_backup_path
            or app_base_dir() / "_internal" / "autosave" / "unsaved_backup.json"
        )

        self.tabs = QTabWidget(self)
        self.line_numbers_checkbox = QCheckBox(self)
        self.word_wrap_checkbox = QCheckBox(self)
        self.ruler_checkbox = QCheckBox(self)
        self.fixed_column_wrap_checkbox = QCheckBox(self)
        self.fixed_column_wrap_column_spin = QSpinBox(self)
        self.visible_spaces_checkbox = QCheckBox(self)
        self.visible_tabs_checkbox = QCheckBox(self)
        self.visible_newlines_checkbox = QCheckBox(self)
        self.startup_restore_checkbox = QCheckBox(self)
        self.show_full_path_checkbox = QCheckBox(self)
        self.inline_color_preview_checkbox = QCheckBox(self)
        self.language_combo = QComboBox(self)
        self.default_encoding_combo = QComboBox(self)
        self.newline_combo = QComboBox(self)
        self.wordpress_mode_combo = QComboBox(self)
        self.frame_alignment_combo = QComboBox(self)
        self.frame_display_combo = QComboBox(self)
        self.frame_outer_spacing_combo = QComboBox(self)
        self.frame_background_color_combo = QComboBox(self)
        self.frame_background_color_button = QPushButton(self)
        self.frame_text_color_combo = QComboBox(self)
        self.frame_text_color_button = QPushButton(self)
        self.frame_display_description_label = QLabel(self)
        self.hover_hints_checkbox = QCheckBox(self)
        self.user_dictionary_folder_edit = QLineEdit(self)
        self.user_dictionary_folder_button = QPushButton(self)
        self.dictionary_check_checkbox = QCheckBox(self)
        self.default_backup_folder_edit = QLineEdit(self)
        self.backup_folder_edit = QLineEdit(self)
        self.backup_folder_button = QPushButton(self)
        self.unsaved_backup_path_edit = QLineEdit(self)
        self.backup_retention_count_spin = QSpinBox(self)
        self.backup_retention_days_spin = QSpinBox(self)
        self.auto_backup_interval_minutes_spin = QSpinBox(self)
        self.font_family_combo = QComboBox(self)
        self.font_size_spin = QSpinBox(self)
        self.tab_width_spin = QSpinBox(self)
        self.editor_theme_combo = QComboBox(self)
        self.editor_background_color_combo = QComboBox(self)
        self.editor_background_color_button = QPushButton(self)
        self.editor_text_color_combo = QComboBox(self)
        self.editor_text_color_button = QPushButton(self)
        self.html_tag_color_combo = QComboBox(self)
        self.html_tag_color_button = QPushButton(self)
        self.wordpress_core_block_color_combo = QComboBox(self)
        self.wordpress_core_block_color_button = QPushButton(self)
        self.search_marker_color_combo = QComboBox(self)
        self.search_marker_color_button = QPushButton(self)
        self.current_match_marker_color_combo = QComboBox(self)
        self.current_match_marker_color_button = QPushButton(self)
        self.visible_space_marker_color_combo = QComboBox(self)
        self.visible_space_marker_color_button = QPushButton(self)
        self.visible_tab_marker_color_combo = QComboBox(self)
        self.visible_tab_marker_color_button = QPushButton(self)
        self.visible_newline_marker_color_combo = QComboBox(self)
        self.visible_newline_marker_color_button = QPushButton(self)
        self.regex_lint_checkbox = QCheckBox(self)
        self.html_typo_lint_checkbox = QCheckBox(self)
        self.reduced_error_check_checkbox = QCheckBox(self)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )

        self._create_tabs()
        self._connect_signals()
        self.apply_language()
        self.set_values(settings)

    def apply_language(self) -> None:
        self.setWindowTitle(self.translator.text("options.title"))
        for index, key in enumerate(
            (
                "options.tab.general",
                "options.tab.view",
                "options.tab.tag_insert",
                "options.tab.backup",
                "options.tab.font",
                "options.tab.colors",
                "options.tab.search",
            )
        ):
            self.tabs.setTabText(index, self.translator.text(key))

        self.line_numbers_checkbox.setText(
            self.translator.text("options.item.line_numbers")
        )
        self.word_wrap_checkbox.setText(self.translator.text("options.item.word_wrap"))
        self.ruler_checkbox.setText(self.translator.text("options.item.ruler"))
        self.fixed_column_wrap_checkbox.setText(
            self.translator.text("options.item.fixed_column_wrap")
        )
        self.visible_spaces_checkbox.setText(
            self.translator.text("options.item.visible_spaces")
        )
        self.visible_tabs_checkbox.setText(
            self.translator.text("options.item.visible_tabs")
        )
        self.visible_newlines_checkbox.setText(
            self.translator.text("options.item.visible_newlines")
        )
        self.startup_restore_checkbox.setText(
            self.translator.text("options.item.startup_restore")
        )
        self.show_full_path_checkbox.setText(
            self.translator.text("options.item.show_full_path")
        )
        self.inline_color_preview_checkbox.setText(self.translator.text("options.item.inline_color_preview"))
        self.hover_hints_checkbox.setText(
            self.translator.text("options.hover_hints_enabled")
        )
        self.user_dictionary_folder_button.setText(
            self.translator.text("options.browse")
        )
        self.dictionary_check_checkbox.setText(
            self.translator.text("options.item.dictionary_check")
        )
        self.backup_folder_button.setText(self.translator.text("options.browse"))
        self.backup_folder_edit.setPlaceholderText(
            self.translator.text(
                "options.backup_folder_placeholder",
                path=self.default_backup_folder_path.as_posix(),
            )
        )
        self.regex_lint_checkbox.setText(
            self.translator.text("options.item.regex_lint")
        )
        self.html_typo_lint_checkbox.setText(
            self.translator.text("options.item.html_typo_lint")
        )
        self.reduced_error_check_checkbox.setText(
            self.translator.text("options.item.reduced_error_check")
        )
        for button in self._color_buttons():
            button.setText(self.translator.text("options.choose_color"))

    def set_values(self, settings: EditorSettings) -> None:
        self.line_numbers_checkbox.setChecked(settings.line_numbers_enabled)
        self.word_wrap_checkbox.setChecked(settings.word_wrap_enabled)
        self.ruler_checkbox.setChecked(settings.ruler_enabled)
        self.fixed_column_wrap_checkbox.setChecked(settings.fixed_column_wrap_enabled)
        self.fixed_column_wrap_column_spin.setRange(1, 500)
        self.fixed_column_wrap_column_spin.setValue(settings.fixed_column_wrap_column)
        self.visible_spaces_checkbox.setChecked(settings.visible_spaces_enabled)
        self.visible_tabs_checkbox.setChecked(settings.visible_tabs_enabled)
        self.visible_newlines_checkbox.setChecked(settings.visible_newlines_enabled)
        self.startup_restore_checkbox.setChecked(settings.startup_restore_enabled)
        self.show_full_path_checkbox.setChecked(settings.show_full_path_in_title)
        self.inline_color_preview_checkbox.setChecked(settings.inline_color_preview_enabled)
        self._set_language_combo(settings.language_code)
        self._set_preset_combo(
            self.default_encoding_combo,
            ENCODING_PRESETS,
            settings.default_encoding,
        )
        self._set_preset_combo(
            self.newline_combo,
            NEWLINE_PRESETS,
            settings.newline_code,
        )
        self.wordpress_mode_combo.clear()
        for mode_label_key in self.wordpress_mode_keys:
            self.wordpress_mode_combo.addItem(
                self.translator.text(mode_label_key),
                mode_label_key,
            )
        mode_index = self.wordpress_mode_combo.findData(settings.wordpress_mode_label_key)
        self.wordpress_mode_combo.setCurrentIndex(max(mode_index, 0))
        self._set_translation_combo(
            self.frame_alignment_combo,
            FRAME_ALIGNMENT_PRESETS,
            settings.frame_alignment,
        )
        self._set_translation_combo(
            self.frame_display_combo,
            FRAME_DISPLAY_PRESETS,
            settings.frame_display,
        )
        self._set_translation_combo(
            self.frame_outer_spacing_combo,
            FRAME_OUTER_SPACING_PRESETS,
            settings.frame_outer_spacing,
            allow_custom=True,
        )
        self._set_translation_combo(
            self.frame_background_color_combo,
            FRAME_BACKGROUND_COLOR_PRESETS,
            settings.frame_background_color,
            allow_custom=True,
        )
        self._set_translation_combo(
            self.frame_text_color_combo,
            FRAME_TEXT_COLOR_PRESETS,
            settings.frame_text_color,
            allow_custom=True,
        )
        self._set_frame_display_description()
        self.hover_hints_checkbox.setChecked(settings.hover_hints_enabled)
        self.user_dictionary_folder_edit.setText(settings.user_dictionary_folder)
        self.dictionary_check_checkbox.setChecked(settings.dictionary_check_enabled)
        self.default_backup_folder_edit.setText(
            self.default_backup_folder_path.as_posix()
        )
        self.default_backup_folder_edit.setReadOnly(True)
        self.backup_folder_edit.setText(settings.backup_folder)
        self.unsaved_backup_path_edit.setText(self.unsaved_backup_path.as_posix())
        self.unsaved_backup_path_edit.setReadOnly(True)
        self.backup_retention_count_spin.setRange(1, 999)
        self.backup_retention_count_spin.setValue(settings.backup_retention_count)
        self.backup_retention_days_spin.setRange(1, 9999)
        self.backup_retention_days_spin.setValue(settings.backup_retention_days)
        self.auto_backup_interval_minutes_spin.setRange(1, 999)
        self.auto_backup_interval_minutes_spin.setValue(
            settings.auto_backup_interval_minutes
        )
        self._set_font_families(settings.font_family)
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setValue(settings.font_size)
        self.tab_width_spin.setRange(1, 16)
        self.tab_width_spin.setValue(settings.tab_width)
        self._set_translation_combo(
            self.editor_theme_combo,
            self._editor_theme_options(),
            settings.editor_theme,
        )
        self._set_color_combo(
            self.editor_background_color_combo,
            settings.editor_background_color,
        )
        self._set_color_combo(
            self.editor_text_color_combo,
            settings.editor_text_color,
        )
        self._set_color_combo(
            self.html_tag_color_combo,
            settings.html_tag_color,
        )
        self._set_color_combo(
            self.wordpress_core_block_color_combo,
            settings.wordpress_core_block_color,
        )
        self._set_color_combo(
            self.search_marker_color_combo,
            settings.search_marker_color,
        )
        self._set_color_combo(
            self.current_match_marker_color_combo,
            settings.current_match_marker_color,
        )
        self._set_color_combo(
            self.visible_space_marker_color_combo,
            settings.visible_space_marker_color,
        )
        self._set_color_combo(
            self.visible_tab_marker_color_combo,
            settings.visible_tab_marker_color,
        )
        self._set_color_combo(
            self.visible_newline_marker_color_combo,
            settings.visible_newline_marker_color,
        )
        self.regex_lint_checkbox.setChecked(settings.regex_lint_enabled)
        self.html_typo_lint_checkbox.setChecked(settings.html_typo_lint_enabled)
        self.reduced_error_check_checkbox.setChecked(
            settings.reduced_error_check_enabled
        )

    def values(self) -> OptionsDialogValues:
        return OptionsDialogValues(
            word_wrap_enabled=self.word_wrap_checkbox.isChecked(),
            line_numbers_enabled=self.line_numbers_checkbox.isChecked(),
            ruler_enabled=self.ruler_checkbox.isChecked(),
            visible_spaces_enabled=self.visible_spaces_checkbox.isChecked(),
            visible_tabs_enabled=self.visible_tabs_checkbox.isChecked(),
            visible_newlines_enabled=self.visible_newlines_checkbox.isChecked(),
            fixed_column_wrap_enabled=self.fixed_column_wrap_checkbox.isChecked(),
            fixed_column_wrap_column=self.fixed_column_wrap_column_spin.value(),
            startup_restore_enabled=self.startup_restore_checkbox.isChecked(),
            show_full_path_in_title=self.show_full_path_checkbox.isChecked(),
            inline_color_preview_enabled=self.inline_color_preview_checkbox.isChecked(),
            language_code=str(self.language_combo.currentData()),
            default_encoding=str(self.default_encoding_combo.currentData()),
            newline_code=str(self.newline_combo.currentData()),
            wordpress_mode_label_key=str(self.wordpress_mode_combo.currentData()),
            hover_hints_enabled=self.hover_hints_checkbox.isChecked(),
            user_dictionary_folder=self.user_dictionary_folder_edit.text().strip(),
            dictionary_check_enabled=self.dictionary_check_checkbox.isChecked(),
            backup_folder=self.backup_folder_edit.text().strip(),
            backup_retention_count=self.backup_retention_count_spin.value(),
            backup_retention_days=self.backup_retention_days_spin.value(),
            auto_backup_interval_minutes=(
                self.auto_backup_interval_minutes_spin.value()
            ),
            font_family=self.font_family_combo.currentText(),
            font_size=self.font_size_spin.value(),
            tab_width=self.tab_width_spin.value(),
            editor_theme=str(self.editor_theme_combo.currentData()),
            editor_background_color=str(
                self.editor_background_color_combo.currentData()
            ),
            editor_text_color=str(self.editor_text_color_combo.currentData()),
            html_tag_color=str(self.html_tag_color_combo.currentData()),
            wordpress_core_block_color=str(
                self.wordpress_core_block_color_combo.currentData()
            ),
            search_marker_color=str(self.search_marker_color_combo.currentData()),
            current_match_marker_color=str(
                self.current_match_marker_color_combo.currentData()
            ),
            visible_space_marker_color=str(
                self.visible_space_marker_color_combo.currentData()
            ),
            visible_tab_marker_color=str(
                self.visible_tab_marker_color_combo.currentData()
            ),
            visible_newline_marker_color=str(
                self.visible_newline_marker_color_combo.currentData()
            ),
            regex_lint_enabled=self.regex_lint_checkbox.isChecked(),
            html_typo_lint_enabled=self.html_typo_lint_checkbox.isChecked(),
            reduced_error_check_enabled=(
                self.reduced_error_check_checkbox.isChecked()
            ),
            frame_alignment=str(self.frame_alignment_combo.currentData()),
            frame_display=str(self.frame_display_combo.currentData()),
            frame_outer_spacing=str(self.frame_outer_spacing_combo.currentData()),
            frame_background_color=str(
                self.frame_background_color_combo.currentData()
            ),
            frame_text_color=str(self.frame_text_color_combo.currentData()),
        )

    def _create_tabs(self) -> None:
        root_layout = QVBoxLayout()
        root_layout.addWidget(self.tabs)
        root_layout.addWidget(self.button_box)
        self.setLayout(root_layout)

        self.tabs.addTab(self._general_tab(), "")
        self.tabs.addTab(self._view_tab(), "")
        self.tabs.addTab(self._tag_insert_tab(), "")
        self.tabs.addTab(self._backup_tab(), "")
        self.tabs.addTab(self._font_tab(), "")
        self.tabs.addTab(self._colors_tab(), "")
        self.tabs.addTab(self._search_tab(), "")
        self.resize(620, 420)

    def _general_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QFormLayout()
        layout.addRow(
            self.translator.text("options.item.language"),
            self.language_combo,
        )
        layout.addRow(
            self.translator.text("options.item.default_encoding"),
            self.default_encoding_combo,
        )
        layout.addRow(
            self.translator.text("options.item.newline"),
            self.newline_combo,
        )
        layout.addRow(self.startup_restore_checkbox)
        tab.setLayout(layout)
        return tab

    def _view_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QFormLayout()
        layout.addRow(self.line_numbers_checkbox)
        layout.addRow(self.word_wrap_checkbox)
        layout.addRow(self.fixed_column_wrap_checkbox)
        layout.addRow(
            self.translator.text("options.fixed_column_wrap_column"),
            self.fixed_column_wrap_column_spin,
        )
        layout.addRow(self.ruler_checkbox)
        layout.addRow(self.show_full_path_checkbox)
        layout.addRow(self.inline_color_preview_checkbox)
        layout.addRow(self.visible_spaces_checkbox)
        layout.addRow(self.visible_tabs_checkbox)
        layout.addRow(self.visible_newlines_checkbox)
        tab.setLayout(layout)
        return tab

    def _tag_insert_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QFormLayout()
        layout.addRow(
            self.translator.text("options.wordpress_mode"),
            self.wordpress_mode_combo,
        )
        layout.addRow(
            self.translator.text("options.frame_alignment"),
            self.frame_alignment_combo,
        )
        layout.addRow(
            self.translator.text("options.frame_display"),
            self.frame_display_combo,
        )
        self.frame_display_description_label.setWordWrap(True)
        layout.addRow(
            self.translator.text("options.frame_display_description"),
            self.frame_display_description_label,
        )
        layout.addRow(
            self.translator.text("options.frame_outer_spacing"),
            self.frame_outer_spacing_combo,
        )
        layout.addRow(
            self.translator.text("options.frame_background_color"),
            self._color_picker_row(
                self.frame_background_color_combo,
                self.frame_background_color_button,
            ),
        )
        layout.addRow(
            self.translator.text("options.frame_text_color"),
            self._color_picker_row(
                self.frame_text_color_combo,
                self.frame_text_color_button,
            ),
        )
        layout.addRow(self.hover_hints_checkbox)
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.user_dictionary_folder_edit)
        folder_layout.addWidget(self.user_dictionary_folder_button)
        layout.addRow(self.translator.text("options.item.user_dictionary"), folder_layout)
        layout.addRow(self.dictionary_check_checkbox)
        tab.setLayout(layout)
        return tab

    def _backup_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QFormLayout()
        layout.addRow(
            self.translator.text("options.default_backup_folder"),
            self.default_backup_folder_edit,
        )
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.backup_folder_edit)
        folder_layout.addWidget(self.backup_folder_button)
        layout.addRow(self.translator.text("options.backup_folder"), folder_layout)
        layout.addRow(
            self.translator.text("options.unsaved_backup_file"),
            self.unsaved_backup_path_edit,
        )
        layout.addRow(
            self.translator.text("options.auto_backup_interval_minutes"),
            self.auto_backup_interval_minutes_spin,
        )
        layout.addRow(
            self.translator.text("options.backup_retention_count"),
            self.backup_retention_count_spin,
        )
        layout.addRow(
            self.translator.text("options.backup_retention_days"),
            self.backup_retention_days_spin,
        )
        tab.setLayout(layout)
        return tab

    def _font_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QFormLayout()
        layout.addRow(self.translator.text("options.font_family"), self.font_family_combo)
        layout.addRow(self.translator.text("options.font_size"), self.font_size_spin)
        layout.addRow(self.translator.text("options.item.tab_width"), self.tab_width_spin)
        tab.setLayout(layout)
        return tab

    def _colors_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QFormLayout()
        self._populate_color_combo(self.editor_background_color_combo)
        self._populate_color_combo(self.editor_text_color_combo)
        self._populate_color_combo(self.html_tag_color_combo)
        self._populate_color_combo(self.wordpress_core_block_color_combo)
        self._populate_color_combo(self.search_marker_color_combo)
        self._populate_color_combo(self.current_match_marker_color_combo)
        self._populate_color_combo(self.visible_space_marker_color_combo)
        self._populate_color_combo(self.visible_tab_marker_color_combo)
        self._populate_color_combo(self.visible_newline_marker_color_combo)
        layout.addRow(
            self.translator.text("options.editor_theme"),
            self.editor_theme_combo,
        )
        layout.addRow(
            self.translator.text("options.editor_background_color"),
            self._color_picker_row(
                self.editor_background_color_combo,
                self.editor_background_color_button,
            ),
        )
        layout.addRow(
            self.translator.text("options.editor_text_color"),
            self._color_picker_row(
                self.editor_text_color_combo,
                self.editor_text_color_button,
            ),
        )
        layout.addRow(
            self.translator.text("options.html_tag_color"),
            self._color_picker_row(
                self.html_tag_color_combo,
                self.html_tag_color_button,
            ),
        )
        layout.addRow(
            self.translator.text("options.wordpress_core_block_color"),
            self._color_picker_row(
                self.wordpress_core_block_color_combo,
                self.wordpress_core_block_color_button,
            ),
        )
        layout.addRow(
            self.translator.text("options.item.search_marker_color"),
            self._color_picker_row(
                self.search_marker_color_combo,
                self.search_marker_color_button,
            ),
        )
        layout.addRow(
            self.translator.text("options.item.current_match_color"),
            self._color_picker_row(
                self.current_match_marker_color_combo,
                self.current_match_marker_color_button,
            ),
        )
        layout.addRow(
            self.translator.text("options.item.visible_space_marker_color"),
            self._color_picker_row(
                self.visible_space_marker_color_combo,
                self.visible_space_marker_color_button,
            ),
        )
        layout.addRow(
            self.translator.text("options.item.visible_tab_marker_color"),
            self._color_picker_row(
                self.visible_tab_marker_color_combo,
                self.visible_tab_marker_color_button,
            ),
        )
        layout.addRow(
            self.translator.text("options.item.visible_newline_marker_color"),
            self._color_picker_row(
                self.visible_newline_marker_color_combo,
                self.visible_newline_marker_color_button,
            ),
        )
        tab.setLayout(layout)
        return tab

    def _search_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QFormLayout()
        layout.addRow(self.regex_lint_checkbox)
        layout.addRow(self.html_typo_lint_checkbox)
        layout.addRow(self.reduced_error_check_checkbox)
        tab.setLayout(layout)
        return tab

    def _placeholder_tab(self, translation_keys: tuple[str, ...]) -> QWidget:
        tab = QWidget(self)
        layout = QVBoxLayout()
        for translation_key in translation_keys:
            layout.addWidget(self._disabled_checkbox(translation_key))
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _disabled_checkbox(self, translation_key: str) -> QCheckBox:
        checkbox = QCheckBox(self.translator.text(translation_key), self)
        checkbox.setEnabled(False)
        return checkbox

    def _connect_signals(self) -> None:
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.backup_folder_button.clicked.connect(self._choose_backup_folder)
        self.user_dictionary_folder_button.clicked.connect(
            self._choose_user_dictionary_folder
        )
        self.frame_display_combo.currentIndexChanged.connect(
            self._set_frame_display_description
        )
        self.editor_theme_combo.currentIndexChanged.connect(
            self._apply_editor_theme_preset
        )
        self.editor_background_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(self.editor_background_color_combo)
        )
        self.editor_text_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(self.editor_text_color_combo)
        )
        self.html_tag_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(self.html_tag_color_combo)
        )
        self.wordpress_core_block_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(
                self.wordpress_core_block_color_combo
            )
        )
        self.frame_background_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(self.frame_background_color_combo)
        )
        self.frame_text_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(self.frame_text_color_combo)
        )
        self.search_marker_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(self.search_marker_color_combo)
        )
        self.current_match_marker_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(self.current_match_marker_color_combo)
        )
        self.visible_space_marker_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(self.visible_space_marker_color_combo)
        )
        self.visible_tab_marker_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(self.visible_tab_marker_color_combo)
        )
        self.visible_newline_marker_color_button.clicked.connect(
            lambda: self._choose_color_for_combo(self.visible_newline_marker_color_combo)
        )

    def _choose_backup_folder(self) -> None:
        selected_folder = QFileDialog.getExistingDirectory(
            self,
            self.translator.text("options.backup_folder"),
            self.backup_folder_edit.text(),
        )
        if selected_folder:
            self.backup_folder_edit.setText(selected_folder)

    def _choose_user_dictionary_folder(self) -> None:
        selected_folder = QFileDialog.getExistingDirectory(
            self,
            self.translator.text("options.item.user_dictionary"),
            self.user_dictionary_folder_edit.text(),
        )
        if selected_folder:
            self.user_dictionary_folder_edit.setText(selected_folder)

    def _set_language_combo(self, current_language_code: str) -> None:
        self.language_combo.clear()
        self.language_combo.addItem(self.translator.text("language.japanese"), "ja")
        self.language_combo.addItem(self.translator.text("language.english"), "en")
        language_index = self.language_combo.findData(current_language_code)
        self.language_combo.setCurrentIndex(max(language_index, 0))

    def _set_preset_combo(
        self,
        combo_box: QComboBox,
        presets: tuple[tuple[str, str], ...],
        current_value: str,
    ) -> None:
        combo_box.clear()
        for label, value in presets:
            combo_box.addItem(label, value)
        current_index = combo_box.findData(current_value)
        if current_index == -1:
            combo_box.insertItem(0, current_value, current_value)
            current_index = 0
        combo_box.setCurrentIndex(current_index)

    def _set_translation_combo(
        self,
        combo_box: QComboBox,
        presets: tuple[tuple[str, str], ...],
        current_value: str,
        *,
        allow_custom: bool = False,
    ) -> None:
        combo_box.clear()
        for label_key, value in presets:
            combo_box.addItem(self.translator.text(label_key), value)
        current_index = combo_box.findData(current_value)
        if current_index == -1:
            if allow_custom:
                combo_box.insertItem(0, current_value, current_value)
                current_index = 0
            else:
                current_index = 0
        combo_box.setCurrentIndex(current_index)

    def _editor_theme_options(self) -> tuple[tuple[str, str], ...]:
        return tuple((label_key, value) for label_key, value, *_ in EDITOR_THEME_PRESETS)

    def _apply_editor_theme_preset(self) -> None:
        theme_value = str(self.editor_theme_combo.currentData())
        for (
            _label_key,
            preset_value,
            background_color,
            text_color,
            html_tag_color,
            core_block_color,
        ) in EDITOR_THEME_PRESETS:
            if preset_value != theme_value or preset_value == "custom":
                continue
            self._set_color_combo(self.editor_background_color_combo, background_color)
            self._set_color_combo(self.editor_text_color_combo, text_color)
            self._set_color_combo(self.html_tag_color_combo, html_tag_color)
            self._set_color_combo(
                self.wordpress_core_block_color_combo,
                core_block_color,
            )
            return

    def _set_frame_display_description(self) -> None:
        display_value = str(self.frame_display_combo.currentData())
        key_suffix = display_value.replace("-", "_")
        self.frame_display_description_label.setText(
            self.translator.text(f"options.frame_display.description.{key_suffix}")
        )

    def _set_font_families(self, current_font_family: str) -> None:
        font_families = sorted(QFontDatabase.families())
        self.font_family_combo.clear()
        self.font_family_combo.addItems(font_families)
        font_index = self.font_family_combo.findText(current_font_family)
        if font_index == -1:
            self.font_family_combo.insertItem(0, current_font_family)
            font_index = 0
        self.font_family_combo.setCurrentIndex(font_index)

    def _populate_color_combo(self, combo_box: QComboBox) -> None:
        combo_box.clear()
        for label, color_code in COLOR_PRESETS:
            combo_box.addItem(_color_icon(color_code), f"{label} ({color_code})", color_code)

    def _set_color_combo(self, combo_box: QComboBox, color_code: str) -> None:
        color_index = combo_box.findData(color_code)
        if color_index == -1:
            combo_box.insertItem(0, _color_icon(color_code), color_code, color_code)
            color_index = 0
        combo_box.setCurrentIndex(color_index)

    def _color_picker_row(self, combo_box: QComboBox, button: QPushButton) -> QWidget:
        widget = QWidget(self)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(combo_box, 1)
        layout.addWidget(button)
        widget.setLayout(layout)
        return widget

    def _choose_color_for_combo(self, combo_box: QComboBox) -> None:
        current_color_code = str(combo_box.currentData())
        initial_color = QColor(current_color_code)
        if not initial_color.isValid():
            initial_color = QColor("#ffffff")
        selected_color = QColorDialog.getColor(
            initial_color,
            self,
            self.translator.text("options.choose_color"),
        )
        if not selected_color.isValid():
            return
        self._set_color_combo(combo_box, selected_color.name())

    def _color_buttons(self) -> tuple[QPushButton, ...]:
        return (
            self.editor_background_color_button,
            self.editor_text_color_button,
            self.html_tag_color_button,
            self.wordpress_core_block_color_button,
            self.frame_background_color_button,
            self.frame_text_color_button,
            self.search_marker_color_button,
            self.current_match_marker_color_button,
            self.visible_space_marker_color_button,
            self.visible_tab_marker_color_button,
            self.visible_newline_marker_color_button,
        )


def _color_icon(color_code: str) -> QIcon:
    pixmap = QPixmap(16, 16)
    color = QColor(color_code)
    pixmap.fill(color if color.isValid() else QColor("#ffffff"))
    return QIcon(pixmap)
