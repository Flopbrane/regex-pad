"""設定の管理処理を検証する。"""

from __future__ import annotations

import json

from settings.settings_manager import SettingsManager


def test_load_returns_defaults_when_settings_file_does_not_exist(tmp_path) -> None:
    """設定のファイルの行わないの存在するの場合、読み込みがを既定値にするを返すことを確認する。"""
    settings_manager = SettingsManager(tmp_path / "settings.json")

    settings = settings_manager.load()

    assert settings.word_wrap_enabled is False
    assert settings.line_numbers_enabled is True
    assert settings.ruler_enabled is False
    assert settings.visible_spaces_enabled is False
    assert settings.visible_tabs_enabled is False
    assert settings.visible_newlines_enabled is False
    assert settings.fixed_column_wrap_enabled is False
    assert settings.fixed_column_wrap_column == 80
    assert settings.startup_restore_enabled is True
    assert settings.language_code == "ja"
    assert settings.default_encoding == "utf-8"
    assert settings.newline_code == "lf"
    assert settings.window_width == 900
    assert settings.window_height == 650
    assert settings.wordpress_mode_label_key == "tag.wordpress_mode.normal"
    assert settings.hover_hints_enabled is True
    assert settings.user_dictionary_folder == ""
    assert settings.dictionary_check_enabled is True
    assert settings.backup_folder == ""
    assert settings.backup_retention_count == 20
    assert settings.backup_retention_days == 30
    assert settings.auto_backup_interval_minutes == 3
    assert settings.font_family == "Consolas"
    assert settings.font_size == 11
    assert settings.tab_width == 4
    assert settings.editor_theme == "light"
    assert settings.editor_background_color == "#ffffff"
    assert settings.editor_text_color == "#202124"
    assert settings.html_tag_color == "#0b5cad"
    assert settings.wordpress_core_block_color == "#667085"
    assert settings.search_marker_color == "#ffff00"
    assert settings.current_match_marker_color == "#ff9900"
    assert settings.visible_space_marker_color == "#9a9a9a"
    assert settings.visible_tab_marker_color == "#9ed8ff"
    assert settings.visible_newline_marker_color == "#ff9900"
    assert settings.regex_lint_enabled is True
    assert settings.html_typo_lint_enabled is True
    assert settings.reduced_error_check_enabled is False
    assert settings.frame_alignment == "left"
    assert settings.frame_display == "inline-block"
    assert settings.frame_outer_spacing == "1.5em 0 2em 0"
    assert settings.frame_background_color == "#fffaf0"
    assert settings.frame_text_color == "#333333"


def test_save_and_load_settings(tmp_path) -> None:
    """保存と読み込みの設定を確認する。"""
    settings_manager = SettingsManager(tmp_path / "settings.json")

    settings_manager.save(
        word_wrap_enabled=True,
        line_numbers_enabled=False,
        ruler_enabled=True,
        visible_spaces_enabled=True,
        visible_tabs_enabled=True,
        visible_newlines_enabled=False,
        fixed_column_wrap_enabled=True,
        fixed_column_wrap_column=72,
        startup_restore_enabled=False,
        language_code="en",
        default_encoding="cp932",
        newline_code="crlf",
        window_width=1200,
        window_height=800,
        wordpress_mode_label_key="tag.wordpress_mode.high_security",
        hover_hints_enabled=False,
        user_dictionary_folder="D:/dicts",
        dictionary_check_enabled=False,
        backup_folder="D:/backup",
        backup_retention_count=12,
        backup_retention_days=45,
        auto_backup_interval_minutes=7,
        font_family="Meiryo",
        font_size=14,
        tab_width=8,
        editor_theme="dark",
        editor_background_color="#1f2933",
        editor_text_color="#f5f7fa",
        html_tag_color="#7cc4ff",
        wordpress_core_block_color="#a8b3c2",
        search_marker_color="#9ed8ff",
        current_match_marker_color="#ffb3d9",
        visible_space_marker_color="#d9d9d9",
        visible_tab_marker_color="#b6f2a5",
        visible_newline_marker_color="#ff9900",
        regex_lint_enabled=False,
        html_typo_lint_enabled=False,
        reduced_error_check_enabled=True,
        frame_alignment="center",
        frame_display="inline-grid",
        frame_outer_spacing="2em 0 3em 0",
        frame_background_color="#f0f9ff",
        frame_text_color="#14384f",
    )
    settings = settings_manager.load()

    assert settings.word_wrap_enabled is True
    assert settings.line_numbers_enabled is False
    assert settings.ruler_enabled is True
    assert settings.visible_spaces_enabled is True
    assert settings.visible_tabs_enabled is True
    assert settings.visible_newlines_enabled is False
    assert settings.fixed_column_wrap_enabled is True
    assert settings.fixed_column_wrap_column == 72
    assert settings.startup_restore_enabled is False
    assert settings.language_code == "en"
    assert settings.default_encoding == "cp932"
    assert settings.newline_code == "crlf"
    assert settings.window_width == 1200
    assert settings.window_height == 800
    assert settings.wordpress_mode_label_key == "tag.wordpress_mode.high_security"
    assert settings.hover_hints_enabled is False
    assert settings.user_dictionary_folder == "D:/dicts"
    assert settings.dictionary_check_enabled is False
    assert settings.backup_folder == "D:/backup"
    assert settings.backup_retention_count == 12
    assert settings.backup_retention_days == 45
    assert settings.auto_backup_interval_minutes == 7
    assert settings.font_family == "Meiryo"
    assert settings.font_size == 14
    assert settings.tab_width == 8
    assert settings.editor_theme == "dark"
    assert settings.editor_background_color == "#1f2933"
    assert settings.editor_text_color == "#f5f7fa"
    assert settings.html_tag_color == "#7cc4ff"
    assert settings.wordpress_core_block_color == "#a8b3c2"
    assert settings.search_marker_color == "#9ed8ff"
    assert settings.current_match_marker_color == "#ffb3d9"
    assert settings.visible_space_marker_color == "#d9d9d9"
    assert settings.visible_tab_marker_color == "#b6f2a5"
    assert settings.visible_newline_marker_color == "#ff9900"
    assert settings.regex_lint_enabled is False
    assert settings.html_typo_lint_enabled is False
    assert settings.reduced_error_check_enabled is True
    assert settings.frame_alignment == "center"
    assert settings.frame_display == "inline-grid"
    assert settings.frame_outer_spacing == "2em 0 3em 0"
    assert settings.frame_background_color == "#f0f9ff"
    assert settings.frame_text_color == "#14384f"


def test_load_uses_defaults_for_invalid_setting_value_types(tmp_path) -> None:
    """読み込みがを既定値にするの用の不正な設定の値の型を使うことを確認する。"""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "word_wrap_enabled": "false",
                "line_numbers_enabled": "definitely",
                "window_width": "wide",
                "window_height": None,
                "fixed_column_wrap_column": "0",
                "font_size": [],
                "tab_width": True,
                "font_family": 123,
            }
        ),
        encoding="utf-8",
    )

    settings = SettingsManager(settings_path).load()

    assert settings.word_wrap_enabled is False
    assert settings.line_numbers_enabled is True
    assert settings.window_width == 900
    assert settings.window_height == 650
    assert settings.fixed_column_wrap_column == 1
    assert settings.font_size == 11
    assert settings.tab_width == 4
    assert settings.font_family == "Consolas"


def test_save_creates_parent_folder(tmp_path) -> None:
    """保存が親要素のフォルダーを作ることを確認する。"""
    settings_path = tmp_path / "portable" / "settings.json"

    SettingsManager(settings_path).save(
        word_wrap_enabled=False,
        line_numbers_enabled=True,
        ruler_enabled=False,
        visible_spaces_enabled=False,
        visible_tabs_enabled=False,
        visible_newlines_enabled=False,
        fixed_column_wrap_enabled=False,
        fixed_column_wrap_column=80,
        startup_restore_enabled=True,
        language_code="ja",
        default_encoding="utf-8",
        newline_code="lf",
        window_width=900,
        window_height=650,
    )

    assert settings_path.exists()
    assert SettingsManager(settings_path).load().window_width == 900
