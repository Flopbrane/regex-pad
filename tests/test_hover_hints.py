"""マウスを重ねたときのヒントを検証する。"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMenu

from dialogs.options_dialog import OptionsDialog
from dialogs.tag_insert_dialog import TagInsertDialog
from editor.tag_insert import ordered_tag_snippet_groups
from main import MainWindow


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance() or QApplication([])
    assert isinstance(application, QApplication)
    return application


def test_menu_hover_signal_reaches_status_bar(app: QApplication) -> None:
    """メニュー項目にマウスを重ねたときのシグナルがステータスバーに届くことを確認する。"""
    window = MainWindow()
    try:
        for root in (
            window.insert_tag_menu,
            window._create_editor_context_menu(),
        ):
            menus = [root, *root.findChildren(QMenu)]
            action = next(
                action
                for menu in menus
                for action in menu.actions()
                if action.statusTip()
            )
            window.statusBar().clearMessage()
            action.hover()
            app.processEvents()
            assert window.statusBar().currentMessage() == action.statusTip()
            assert action.toolTip()
    finally:
        window.close()


def test_picker_hover_setting_preserves_keyboard_hint(app: QApplication) -> None:
    """選択画面のマウスを重ねたときの設定がキーボードのヒントを維持することを確認する。"""
    window = MainWindow()
    dialog = TagInsertDialog(window.translator)
    try:
        dialog.set_snippet_groups(ordered_tag_snippet_groups(None))
        item = dialog.snippet_list.item(1)
        assert item is not None

        dialog.hint_label.clear()
        dialog.snippet_list.itemEntered.emit(item)
        assert dialog.hint_label.text()
        assert item.toolTip()

        dialog.set_hover_hints_enabled(False)
        assert item.toolTip() == ""
        dialog.hint_label.clear()
        dialog.snippet_list.itemEntered.emit(item)
        assert dialog.hint_label.text() == ""

        dialog.snippet_list.setCurrentRow(1)
        assert dialog.hint_label.text()
        dialog.search_edit.setText("div")
        assert dialog.snippet_list.count() > 0
        assert all(
            dialog.snippet_list.item(index).toolTip() == ""
            for index in range(dialog.snippet_list.count())
        )

        dialog.set_hover_hints_enabled(True)
        item = dialog.snippet_list.item(0)
        assert item is not None
        dialog.hint_label.clear()
        dialog.snippet_list.itemEntered.emit(item)
        assert dialog.hint_label.text()
        assert item.toolTip()
        app.processEvents()
    finally:
        dialog.close()
        window.close()


def test_options_reach_reused_picker_and_saved_settings(
    app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """オプションの到達の再利用した選択画面と保存済みの設定を確認する。"""
    window = MainWindow()
    states: list[bool] = []
    enabled = False

    def accept_options(dialog: OptionsDialog) -> int:
        """テストで指定したオプションを確定する。"""
        dialog.hover_hints_checkbox.setChecked(enabled)
        return QDialog.DialogCode.Accepted

    def inspect_picker(dialog: TagInsertDialog) -> int:
        """再利用されるタグ選択画面の状態を確認する。"""
        states.append(dialog.hover_hints_enabled)
        assert bool(dialog.snippet_list.item(0).toolTip()) is enabled
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(OptionsDialog, "exec", accept_options)
    monkeypatch.setattr(TagInsertDialog, "exec", inspect_picker)
    try:
        for enabled in (False, True):
            window.show_options_dialog()
            assert window.hover_hints_enabled is enabled
            assert window.insert_tag_menu.toolTipsVisible() is enabled
            assert window.settings_manager.load().hover_hints_enabled is enabled
            window.show_tag_insert_dialog()
            app.processEvents()
        assert states == [False, True]
    finally:
        window.close()
