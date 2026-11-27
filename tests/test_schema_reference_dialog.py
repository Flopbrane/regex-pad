"""スキーマの参照資料のダイアログを検証する。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from dialogs.schema_reference_dialog import SchemaReferenceDialog
from localization.translator import Translator
from main import MainWindow

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STANDARDS_PATH = PROJECT_ROOT / "dictionaries" / "standards"


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_schema_reference_dialog_is_modeless_and_has_separate_tables(
    app: QApplication,
) -> None:
    """スキーマの参照資料のダイアログがモードレスのになるとともに、別々の表を持つことを確認する。"""
    _ = app
    translator = Translator(PROJECT_ROOT / "resources", "ja")
    dialog = SchemaReferenceDialog(STANDARDS_PATH, translator)

    assert dialog.windowModality() == Qt.WindowModality.NonModal
    assert dialog.isModal() is False
    assert dialog.tab_widget.count() == 3
    assert dialog.tab_widget.tabText(0) == "HTMLタグ・属性表"
    assert dialog.tab_widget.tabText(1) == "CSSプロパティ表"
    assert dialog.tab_widget.tabText(2) == "WordPressブロックJSON表"
    assert "<img>" in dialog.html_browser.toPlainText()
    assert "src" in dialog.html_browser.toPlainText()
    assert "border-collapse" in dialog.css_browser.toPlainText()
    assert "text-aling" in dialog.css_browser.toPlainText()
    assert "wp:paragraph" in dialog.wordpress_browser.toPlainText()
    assert "level" in dialog.wordpress_browser.toPlainText()


def test_schema_reference_dialog_follows_language_change(app: QApplication) -> None:
    """スキーマの参照資料のダイアログが言語の変更に従うことを確認する。"""
    _ = app
    translator = Translator(PROJECT_ROOT / "resources", "ja")
    dialog = SchemaReferenceDialog(STANDARDS_PATH, translator)

    translator.set_language("en")
    dialog.apply_language()

    assert dialog.windowTitle() == "HTML / CSS / WordPress Reference Tables"
    assert dialog.tab_widget.tabText(0) == "HTML Tag / Attribute Table"
    assert dialog.tab_widget.tabText(1) == "CSS Property Table"
    assert dialog.tab_widget.tabText(2) == "WordPress Block JSON Table"
    html_reference_text = dialog.html_browser.toPlainText()
    assert "Description" in html_reference_text
    assert "Sets the destination URL for a link or linked resource." in html_reference_text
    css_reference_text = dialog.css_browser.toPlainText()
    assert "Description" in css_reference_text
    assert "color / keyword / css_variable" in css_reference_text
    assert "Sets the background color." in css_reference_text
    wordpress_reference_text = dialog.wordpress_browser.toPlainText()
    assert "Description" in wordpress_reference_text
    assert "Stores the block's editable content text." in wordpress_reference_text


def test_main_window_opens_reference_without_disabling_editor(
    app: QApplication,
) -> None:
    """無効化のエディターを省いた場合、メインウインドウが参照資料を開くことを確認する。"""
    _ = app
    window = MainWindow()
    window.show()

    window.show_schema_reference_dialog()

    assert window.schema_reference_dialog is not None
    assert window.schema_reference_dialog.isVisible()
    assert window.schema_reference_dialog.isModal() is False
    assert window.editor.isEnabled()
    assert window.schema_reference_action.text() == (
        "HTML / CSS / WordPress 参考表(&R)..."
    )

    window.close()
