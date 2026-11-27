"""設定画面を検証する。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QCheckBox

from dialogs.options_dialog import OptionsDialog
from localization.translator import Translator
from settings.settings_manager import EditorSettings


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_options_dialog_groups_items_by_tabs(app: QApplication) -> None:
    """設定画面のグループの項目によるのタブを確認する。"""
    _ = app
    dialog = OptionsDialog(Translator(Path("resources"), "ja"), EditorSettings())

    assert [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())] == [
        "一般",
        "表示",
        "タグ挿入",
        "バックアップ",
        "フォント",
        "配色",
        "検索",
    ]
    assert dialog.wordpress_mode_combo.count() == 3
    assert dialog.frame_alignment_combo.count() == 3
    assert dialog.frame_display_combo.count() == 4
    assert dialog.frame_outer_spacing_combo.count() == 4
    assert dialog.frame_background_color_combo.count() == 6
    assert dialog.frame_text_color_combo.count() == 6
    assert dialog.editor_theme_combo.count() == 5
    assert dialog.editor_background_color_combo.currentText() == "#ffffff"
    assert dialog.editor_text_color_combo.currentText() == "#202124"
    assert dialog.html_tag_color_combo.currentText() == "#0b5cad"
    assert dialog.wordpress_core_block_color_combo.currentText() == "#667085"
    assert dialog.editor_background_color_button.text() == "色選択..."
    assert dialog.frame_alignment_combo.currentText() == "左寄せ"
    assert dialog.frame_display_combo.currentText() == (
        "文字幅に合わせる（inline-block）"
    )
    assert dialog.frame_outer_spacing_combo.currentText() == (
        "標準（1.5em 0 2em 0）"
    )
    assert dialog.frame_background_color_combo.currentText() == (
        "やさしいオレンジ（#fffaf0）"
    )
    assert dialog.frame_text_color_combo.currentText() == "濃いグレー（#333333）"
    assert dialog.frame_display_description_label.text() == (
        "文章の長さに合わせて枠幅を縮めます。通常の補足枠向けです。"
    )
    assert dialog.hover_hints_checkbox.text() == "ホーバーヒントを表示する"
    assert dialog.startup_restore_checkbox.text() == "起動時の復元"
    assert dialog.dictionary_check_checkbox.text() == "Dict 検証"
    assert dialog.regex_lint_checkbox.text() == "正規表現チェック"
    assert dialog.html_typo_lint_checkbox.text() == "HTML/WP表記チェック"
    assert dialog.reduced_error_check_checkbox.text() == (
        "低負荷モード（入力中の自動チェックを抑制）"
    )
    assert dialog.line_numbers_checkbox.text() == "行番号"
    assert dialog.word_wrap_checkbox.text() == "折り返し"
    assert dialog.fixed_column_wrap_checkbox.text() == "設定文字数で折り返す"
    assert dialog.ruler_checkbox.text() == "文字数ルーラー"
    assert dialog.visible_spaces_checkbox.text() == "空白を表示"
    assert dialog.visible_tabs_checkbox.text() == "TABを表示"
    assert dialog.visible_newlines_checkbox.text() == "改行を表示"
    assert dialog.visible_space_marker_color_combo.count() > 0
    assert dialog.visible_tab_marker_color_combo.count() > 0
    assert dialog.visible_newline_marker_color_combo.count() > 0
    assert dialog.search_marker_color_combo.itemIcon(0).isNull() is False
    assert dialog.search_marker_color_button.text() == "色選択..."
    backup_tab = dialog.tabs.widget(3)
    assert backup_tab is not None
    backup_tab_text = " ".join(
        child.text() for child in backup_tab.findChildren(QCheckBox)
    )
    assert "ローカル設定ファイル" not in backup_tab_text
    assert "環境変数を変更しない" not in backup_tab_text
    assert "復元方法" not in backup_tab_text


def test_options_dialog_returns_editable_values(app: QApplication) -> None:
    """設定画面が編集可能な値を返すことを確認する。"""
    _ = app
    dialog = OptionsDialog(
        Translator(Path("resources"), "ja"),
        EditorSettings(
            word_wrap_enabled=True,
            line_numbers_enabled=False,
            ruler_enabled=True,
            visible_spaces_enabled=True,
            visible_tabs_enabled=False,
            visible_newlines_enabled=True,
            fixed_column_wrap_enabled=True,
            fixed_column_wrap_column=72,
            startup_restore_enabled=False,
            language_code="en",
            default_encoding="cp932",
            newline_code="crlf",
            wordpress_mode_label_key="tag.wordpress_mode.high_security",
            hover_hints_enabled=False,
            user_dictionary_folder="D:/dicts",
            dictionary_check_enabled=False,
            backup_folder="D:/backup",
            backup_retention_count=12,
            backup_retention_days=45,
            auto_backup_interval_minutes=7,
            font_family="Consolas",
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
            frame_alignment="right",
            frame_display="grid",
            frame_outer_spacing="2em 0 3em 0",
            frame_background_color="#f0f9ff",
            frame_text_color="#14384f",
        ),
    )

    values = dialog.values()

    assert values.word_wrap_enabled is True
    assert values.line_numbers_enabled is False
    assert values.ruler_enabled is True
    assert values.visible_spaces_enabled is True
    assert values.visible_tabs_enabled is False
    assert values.visible_newlines_enabled is True
    assert values.fixed_column_wrap_enabled is True
    assert values.fixed_column_wrap_column == 72
    assert values.startup_restore_enabled is False
    assert values.language_code == "en"
    assert values.default_encoding == "cp932"
    assert values.newline_code == "crlf"
    assert values.wordpress_mode_label_key == "tag.wordpress_mode.high_security"
    assert values.hover_hints_enabled is False
    assert values.user_dictionary_folder == "D:/dicts"
    assert values.dictionary_check_enabled is False
    assert values.backup_folder == "D:/backup"
    assert values.backup_retention_count == 12
    assert values.backup_retention_days == 45
    assert values.auto_backup_interval_minutes == 7
    assert values.font_size == 14
    assert values.tab_width == 8
    assert values.editor_theme == "dark"
    assert values.editor_background_color == "#1f2933"
    assert values.editor_text_color == "#f5f7fa"
    assert values.html_tag_color == "#7cc4ff"
    assert values.wordpress_core_block_color == "#a8b3c2"
    assert values.search_marker_color == "#9ed8ff"
    assert values.current_match_marker_color == "#ffb3d9"
    assert values.visible_space_marker_color == "#d9d9d9"
    assert values.visible_tab_marker_color == "#b6f2a5"
    assert values.visible_newline_marker_color == "#ff9900"
    assert values.regex_lint_enabled is False
    assert values.html_typo_lint_enabled is False
    assert values.reduced_error_check_enabled is True
    assert values.frame_alignment == "right"
    assert values.frame_display == "grid"
    assert values.frame_outer_spacing == "2em 0 3em 0"
    assert values.frame_background_color == "#f0f9ff"
    assert values.frame_text_color == "#14384f"


def test_options_dialog_shows_default_backup_folder_hint(
    app: QApplication,
) -> None:
    """設定画面が既定のバックアップ先のヒントを表示することを確認する。"""
    _ = app
    dialog = OptionsDialog(Translator(Path("resources"), "en"), EditorSettings())

    assert dialog.backup_folder_edit.placeholderText().startswith("Blank: ")
    assert dialog.backup_folder_edit.placeholderText().endswith("_internal/backup")
    assert dialog.default_backup_folder_edit.text().endswith("_internal/backup")
    assert dialog.unsaved_backup_path_edit.text().endswith(
        "_internal/autosave/unsaved_backup.json"
    )
