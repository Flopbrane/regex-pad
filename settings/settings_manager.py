from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EditorSettings:
    word_wrap_enabled: bool = False
    line_numbers_enabled: bool = True
    ruler_enabled: bool = False
    visible_spaces_enabled: bool = False
    visible_tabs_enabled: bool = False
    visible_newlines_enabled: bool = False
    fixed_column_wrap_enabled: bool = False
    fixed_column_wrap_column: int = 80
    startup_restore_enabled: bool = True
    language_code: str = "ja"
    default_encoding: str = "utf-8"
    newline_code: str = "lf"
    window_width: int = 900
    window_height: int = 650
    wordpress_mode_label_key: str = "tag.wordpress_mode.normal"
    hover_hints_enabled: bool = True
    user_dictionary_folder: str = ""
    dictionary_check_enabled: bool = True
    backup_folder: str = ""
    backup_retention_count: int = 20
    backup_retention_days: int = 30
    auto_backup_interval_minutes: int = 3
    font_family: str = "Consolas"
    font_size: int = 11
    tab_width: int = 4
    editor_theme: str = "light"
    editor_background_color: str = "#ffffff"
    editor_text_color: str = "#202124"
    html_tag_color: str = "#0b5cad"
    wordpress_core_block_color: str = "#667085"
    search_marker_color: str = "#ffff00"
    current_match_marker_color: str = "#ff9900"
    visible_space_marker_color: str = "#9a9a9a"
    visible_tab_marker_color: str = "#9ed8ff"
    visible_newline_marker_color: str = "#ff9900"
    regex_lint_enabled: bool = True
    html_typo_lint_enabled: bool = True
    reduced_error_check_enabled: bool = False
    frame_alignment: str = "left"
    frame_display: str = "inline-block"
    frame_outer_spacing: str = "1.5em 0 2em 0"
    frame_background_color: str = "#fffaf0"
    frame_text_color: str = "#333333"
    macro_folder: str = ""
    macro_editor_geometry: str = ""
    macro_editor_splitter_state: str = ""


class SettingsManager:
    def __init__(self, settings_path: Path) -> None:
        self.settings_path = settings_path

    def load(self) -> EditorSettings:
        if not self.settings_path.exists():
            return EditorSettings()

        try:
            load_data: dict[str, Any] = json.loads(
                self.settings_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return EditorSettings()
        if not isinstance(load_data, dict):
            return EditorSettings()

        return EditorSettings(
            word_wrap_enabled=_setting_bool(load_data, "word_wrap_enabled", False),
            line_numbers_enabled=_setting_bool(
                load_data, "line_numbers_enabled", True
            ),
            ruler_enabled=_setting_bool(load_data, "ruler_enabled", False),
            visible_spaces_enabled=_setting_bool(
                load_data, "visible_spaces_enabled", False
            ),
            visible_tabs_enabled=_setting_bool(
                load_data, "visible_tabs_enabled", False
            ),
            visible_newlines_enabled=_setting_bool(
                load_data, "visible_newlines_enabled", False
            ),
            fixed_column_wrap_enabled=_setting_bool(
                load_data, "fixed_column_wrap_enabled", False
            ),
            fixed_column_wrap_column=_setting_int_min(
                load_data, "fixed_column_wrap_column", 80, minimum=1
            ),
            startup_restore_enabled=_setting_bool(
                load_data, "startup_restore_enabled", True
            ),
            language_code=_setting_str(load_data, "language_code", "ja"),
            default_encoding=_setting_str(load_data, "default_encoding", "utf-8"),
            newline_code=_setting_str(load_data, "newline_code", "lf"),
            window_width=_setting_int_min(load_data, "window_width", 900, minimum=1),
            window_height=_setting_int_min(load_data, "window_height", 650, minimum=1),
            wordpress_mode_label_key=_setting_str(
                load_data, "wordpress_mode_label_key", "tag.wordpress_mode.normal"
            ),
            hover_hints_enabled=_setting_bool(load_data, "hover_hints_enabled", True),
            user_dictionary_folder=_setting_str(
                load_data, "user_dictionary_folder", ""
            ),
            dictionary_check_enabled=_setting_bool(
                load_data, "dictionary_check_enabled", True
            ),
            backup_folder=_setting_str(load_data, "backup_folder", ""),
            backup_retention_count=_setting_int_min(
                load_data, "backup_retention_count", 20, minimum=1
            ),
            backup_retention_days=_setting_int_min(
                load_data, "backup_retention_days", 30, minimum=1
            ),
            auto_backup_interval_minutes=_setting_int_min(
                load_data, "auto_backup_interval_minutes", 3, minimum=1
            ),
            font_family=_setting_str(load_data, "font_family", "Consolas"),
            font_size=_setting_int_min(load_data, "font_size", 11, minimum=1),
            tab_width=_setting_int_min(load_data, "tab_width", 4, minimum=1),
            editor_theme=_setting_str(load_data, "editor_theme", "light"),
            editor_background_color=_setting_str(
                load_data, "editor_background_color", "#ffffff"
            ),
            editor_text_color=_setting_str(load_data, "editor_text_color", "#202124"),
            html_tag_color=_setting_str(load_data, "html_tag_color", "#0b5cad"),
            wordpress_core_block_color=_setting_str(
                load_data, "wordpress_core_block_color", "#667085"
            ),
            search_marker_color=_setting_str(
                load_data, "search_marker_color", "#ffff00"
            ),
            current_match_marker_color=_setting_str(
                load_data, "current_match_marker_color", "#ff9900"
            ),
            visible_space_marker_color=_setting_str(
                load_data, "visible_space_marker_color", "#9a9a9a"
            ),
            visible_tab_marker_color=_setting_str(
                load_data, "visible_tab_marker_color", "#9ed8ff"
            ),
            visible_newline_marker_color=_setting_str(
                load_data, "visible_newline_marker_color", "#ff9900"
            ),
            regex_lint_enabled=_setting_bool(load_data, "regex_lint_enabled", True),
            html_typo_lint_enabled=_setting_bool(
                load_data, "html_typo_lint_enabled", True
            ),
            reduced_error_check_enabled=_setting_bool(
                load_data, "reduced_error_check_enabled", False
            ),
            frame_alignment=_setting_str(load_data, "frame_alignment", "left"),
            frame_display=_setting_str(load_data, "frame_display", "inline-block"),
            frame_outer_spacing=_setting_str(
                load_data, "frame_outer_spacing", "1.5em 0 2em 0"
            ),
            frame_background_color=_setting_str(
                load_data, "frame_background_color", "#fffaf0"
            ),
            frame_text_color=_setting_str(load_data, "frame_text_color", "#333333"),
            macro_folder=_setting_str(load_data, "macro_folder", ""),
            macro_editor_geometry=_setting_str(load_data, "macro_editor_geometry", ""),
            macro_editor_splitter_state=_setting_str(load_data, "macro_editor_splitter_state", ""),
        )

    def save(
        self,
        *,
        word_wrap_enabled: bool,
        line_numbers_enabled: bool,
        ruler_enabled: bool,
        visible_spaces_enabled: bool,
        visible_tabs_enabled: bool,
        visible_newlines_enabled: bool,
        fixed_column_wrap_enabled: bool,
        fixed_column_wrap_column: int,
        startup_restore_enabled: bool,
        language_code: str,
        default_encoding: str,
        newline_code: str,
        window_width: int,
        window_height: int,
        wordpress_mode_label_key: str = "tag.wordpress_mode.normal",
        hover_hints_enabled: bool = True,
        user_dictionary_folder: str = "",
        dictionary_check_enabled: bool = True,
        backup_folder: str = "",
        backup_retention_count: int = 20,
        backup_retention_days: int = 30,
        auto_backup_interval_minutes: int = 3,
        font_family: str = "Consolas",
        font_size: int = 11,
        tab_width: int = 4,
        editor_theme: str = "light",
        editor_background_color: str = "#ffffff",
        editor_text_color: str = "#202124",
        html_tag_color: str = "#0b5cad",
        wordpress_core_block_color: str = "#667085",
        search_marker_color: str = "#ffff00",
        current_match_marker_color: str = "#ff9900",
        visible_space_marker_color: str = "#9a9a9a",
        visible_tab_marker_color: str = "#9ed8ff",
        visible_newline_marker_color: str = "#ff9900",
        regex_lint_enabled: bool = True,
        html_typo_lint_enabled: bool = True,
        reduced_error_check_enabled: bool = False,
        frame_alignment: str = "left",
        frame_display: str = "inline-block",
        frame_outer_spacing: str = "1.5em 0 2em 0",
        frame_background_color: str = "#fffaf0",
        frame_text_color: str = "#333333",
        macro_folder: str = "",
        macro_editor_geometry: str = "",
        macro_editor_splitter_state: str = "",
    ) -> None:
        save_data = {
            "word_wrap_enabled": word_wrap_enabled,
            "line_numbers_enabled": line_numbers_enabled,
            "ruler_enabled": ruler_enabled,
            "visible_spaces_enabled": visible_spaces_enabled,
            "visible_tabs_enabled": visible_tabs_enabled,
            "visible_newlines_enabled": visible_newlines_enabled,
            "fixed_column_wrap_enabled": fixed_column_wrap_enabled,
            "fixed_column_wrap_column": max(1, fixed_column_wrap_column),
            "startup_restore_enabled": startup_restore_enabled,
            "language_code": language_code,
            "default_encoding": default_encoding,
            "newline_code": newline_code,
            "window_width": window_width,
            "window_height": window_height,
            "wordpress_mode_label_key": wordpress_mode_label_key,
            "hover_hints_enabled": hover_hints_enabled,
            "user_dictionary_folder": user_dictionary_folder,
            "dictionary_check_enabled": dictionary_check_enabled,
            "backup_folder": backup_folder,
            "backup_retention_count": max(1, backup_retention_count),
            "backup_retention_days": max(1, backup_retention_days),
            "auto_backup_interval_minutes": max(1, auto_backup_interval_minutes),
            "font_family": font_family,
            "font_size": font_size,
            "tab_width": max(1, tab_width),
            "editor_theme": editor_theme,
            "editor_background_color": editor_background_color,
            "editor_text_color": editor_text_color,
            "html_tag_color": html_tag_color,
            "wordpress_core_block_color": wordpress_core_block_color,
            "search_marker_color": search_marker_color,
            "current_match_marker_color": current_match_marker_color,
            "visible_space_marker_color": visible_space_marker_color,
            "visible_tab_marker_color": visible_tab_marker_color,
            "visible_newline_marker_color": visible_newline_marker_color,
            "regex_lint_enabled": regex_lint_enabled,
            "html_typo_lint_enabled": html_typo_lint_enabled,
            "reduced_error_check_enabled": reduced_error_check_enabled,
            "frame_alignment": frame_alignment,
            "frame_display": frame_display,
            "frame_outer_spacing": frame_outer_spacing,
            "frame_background_color": frame_background_color,
            "frame_text_color": frame_text_color,
            "macro_folder": macro_folder,
            "macro_editor_geometry": macro_editor_geometry,
            "macro_editor_splitter_state": macro_editor_splitter_state,
        }
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.settings_path.parent,
            delete=False,
        ) as temporary_file:
            json.dump(save_data, temporary_file, indent=2)
            temporary_file.flush()
            temporary_file_path = Path(temporary_file.name)

        temporary_file_path.replace(self.settings_path)


def _setting_bool(load_data: dict[str, Any], key: str, default: bool) -> bool:
    value = load_data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized_value = value.strip().lower()
        if normalized_value in {"true", "1", "yes", "on"}:
            return True
        if normalized_value in {"false", "0", "no", "off"}:
            return False
    return default


def _setting_int_min(
    load_data: dict[str, Any],
    key: str,
    default: int,
    *,
    minimum: int,
) -> int:
    value = load_data.get(key, default)
    if isinstance(value, bool):
        return default
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError):
        return default


def _setting_str(load_data: dict[str, Any], key: str, default: str) -> str:
    value = load_data.get(key, default)
    if isinstance(value, str):
        return value
    return default
