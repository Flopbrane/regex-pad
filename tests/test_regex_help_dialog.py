"""正規表現ヘルプのダイアログを検証する。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QHeaderView

from dialogs.regex_help_dialog import RegexHelpDialog
from localization.translator import Translator


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_regex_help_loads_examples(app: QApplication) -> None:
    """正規表現ヘルプが例を読み込むことを確認する。"""
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = RegexHelpDialog(Path("resources/regex_help_en.json"), translator)

    assert dialog.table.rowCount() >= 30
    assert dialog.table.columnCount() == 8
    assert dialog.table.item(0, 0) is not None
    assert dialog.table.item(0, 3) is not None
    usage_item = dialog.table.item(0, 5)
    assert usage_item is not None
    assert usage_item.text() == "cat"


def test_regex_help_columns_are_resizable_and_wide_enough(app: QApplication) -> None:
    """正規表現ヘルプの列がサイズを変更できると幅の広いの十分なであることを確認する。"""
    _ = app
    translator = Translator(Path("resources"), "ja")
    dialog = RegexHelpDialog(Path("resources/regex_help_ja.json"), translator)

    header = dialog.table.horizontalHeader()

    assert header.sectionsMovable() is True
    assert dialog.table.wordWrap() is False
    for column in range(dialog.table.columnCount()):
        assert header.sectionResizeMode(column) == QHeaderView.ResizeMode.Interactive
    assert dialog.table.columnWidth(2) >= 220
    assert dialog.table.columnWidth(3) >= 170
    assert dialog.table.columnWidth(6) >= 190
    assert dialog.table.columnWidth(7) >= 380


def test_regex_help_can_switch_between_english_and_japanese(app: QApplication) -> None:
    """正規表現ヘルプが切り替えの間の英語と日本語が可能であることを確認する。"""
    _ = app
    translator = Translator(Path("resources"), "ja")
    dialog = RegexHelpDialog(
        {
            "EN_Ver.": Path("resources/regex_help_en.json"),
            "JP_Ver.": Path("resources/regex_help_ja.json"),
        },
        translator,
    )

    assert dialog.language_combo_box.currentText() == "EN_Ver."
    dialog.language_combo_box.setCurrentText("JP_Ver.")

    assert dialog.language_combo_box.currentText() == "JP_Ver."
    header_item = dialog.table.horizontalHeaderItem(0)
    category_item = dialog.table.item(0, 0)
    assert header_item is not None
    assert category_item is not None
    assert header_item.text() == "区分"
    assert category_item.text() == "検索：基本形"
    usage_header_item = dialog.table.horizontalHeaderItem(5)
    assert usage_header_item is not None
    assert usage_header_item.text() == "一致部分"


def test_help_headers_follow_help_language_not_app_language(app: QApplication) -> None:
    """ヘルプの見出しの追従のヘルプの言語のしないのアプリの言語を確認する。"""
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = RegexHelpDialog(
        {
            "EN_Ver.": Path("resources/regex_help_en.json"),
            "JP_Ver.": Path("resources/regex_help_ja.json"),
        },
        translator,
    )

    dialog.language_combo_box.setCurrentText("JP_Ver.")

    header_item = dialog.table.horizontalHeaderItem(0)
    assert header_item is not None
    assert header_item.text() == "区分"


def test_regex_help_emits_selected_pattern(app: QApplication) -> None:
    """正規表現ヘルプが選択中のパターンを通知することを確認する。"""
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = RegexHelpDialog(Path("resources/regex_help_en.json"), translator)
    emitted_patterns: list[str] = []
    dialog.pattern_insert_requested.connect(emitted_patterns.append)
    dialog.table.selectRow(0)

    dialog._emit_selected_pattern()

    assert emitted_patterns == ["cat"]


def test_regex_help_double_click_emits_pattern_column(app: QApplication) -> None:
    """正規表現ヘルプの二重のクリックがパターンの列を通知することを確認する。"""
    _ = app
    translator = Translator(Path("resources"), "en")
    dialog = RegexHelpDialog(Path("resources/regex_help_en.json"), translator)
    emitted_patterns: list[str] = []
    dialog.pattern_insert_requested.connect(emitted_patterns.append)
    item = dialog.table.item(1, 1)
    assert item is not None

    dialog._emit_item_pattern(item)

    assert emitted_patterns == [r"^cat"]
