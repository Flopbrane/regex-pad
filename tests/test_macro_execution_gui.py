"""メインウインドウでプレビュー承認、元文書の照合、1回のUndoを検証する。"""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from dialogs.macro_run_preview_dialog import MacroRunPreviewDialog
from macro.editor_bridge import MacroEditorBridge
from macro.json_data_model import MacroJsonData, MacroJsonStepData
from main import MainWindow


@pytest.fixture
def window(tmp_path: Path, monkeypatch):
    """テスト用の設定パスを持つメインウインドウを用意する。"""
    app = QApplication.instance() or QApplication([])
    main = MainWindow(
        settings_path=tmp_path / "settings.json", restore_unsaved_backup=False
    )
    main.editor.setPlainText("a 😀")
    main.editor.document().setModified(False)
    main.show_macro_editor()
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args: QMessageBox.StandardButton.Ok
    )
    yield main
    if main.macro_editor_controller is not None:
        main.macro_editor_controller.session.modified = False
    for editor in main.tab_file_paths:
        editor.document().setModified(False)
    main.close()
    main.deleteLater()
    app.processEvents()


def macro():
    """テストで実行するマクロ定義を作る。"""
    return MacroJsonData(
        1,
        "two steps",
        "",
        [
            MacroJsonStepData("first", True, False, False, None, False, "a", None, "b"),
            MacroJsonStepData(
                "second", True, False, False, None, False, "b", None, "c"
            ),
        ],
    )


def test_toolbar_runs_once_and_approval_applies_exact_preview_with_one_undo(
    window, monkeypatch
):
    """ツールバーからの実行が1回で、承認するとプレビューどおりに適用され、1回のUndoで戻せることを確認する。"""
    controller = window.macro_execution_controller
    editor_controller = window.macro_editor_controller
    assert controller is not None and editor_controller is not None
    editor_controller.session.document = MacroEditorBridge.from_json_model(macro())
    editor_controller._render_document()
    calls = []
    original_run = controller.manager.runner.run

    def run_once(*args):
        """マクロの実行回数を記録して本来の処理を呼ぶ。"""
        calls.append(True)
        return original_run(*args)

    monkeypatch.setattr(controller.manager.runner, "run", run_once)

    def approve(dialog):
        """プレビュー画面で適用の承認を再現する。"""
        assert window.editor.toPlainText() == "a 😀"
        assert dialog.before.isReadOnly() and dialog.after.isReadOnly()
        assert dialog.after.toPlainText() == "c 😀"
        assert dialog.apply_button.isEnabled()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(MacroRunPreviewDialog, "exec", approve)
    assert window.macro_editor_window is not None
    window.macro_editor_window.editor_actions["run"].trigger()
    assert len(calls) == 1
    assert window.editor.toPlainText() == "c 😀"
    assert window.editor.document().isModified()
    window.editor.undo()
    assert window.editor.toPlainText() == "a 😀"
    window.editor.redo()
    assert window.editor.toPlainText() == "c 😀"


def test_cancel_preserves_document_and_undo_state(window, monkeypatch):
    """キャンセルが文書とUndoの状態を維持することを確認する。"""
    controller = window.macro_execution_controller
    assert controller is not None
    monkeypatch.setattr(
        MacroRunPreviewDialog, "exec", lambda dialog: QDialog.DialogCode.Rejected
    )
    assert not controller.preview_and_apply(macro())
    assert window.editor.toPlainText() == "a 😀"
    assert not window.editor.document().isModified()
    assert not window.editor.document().isUndoAvailable()


@pytest.mark.parametrize(
    "change", ["text", "revision", "switch", "close", "readonly", "macro"]
)
def test_stale_document_or_tab_never_receives_preview_output(
    window, monkeypatch, change
):
    """文書の内容やタブが変わった場合、古いプレビューの結果が適用されないことを確認する。"""
    controller = window.macro_execution_controller
    assert controller is not None
    target = window.editor
    definition = macro()

    def change_before_approval(dialog):
        """プレビューを承認する前に原稿または対象タブを変更する。"""
        if change == "text":
            target.insertPlainText("edited ")
        elif change == "revision":
            target.insertPlainText("temporary")
            target.undo()
        elif change == "switch":
            window._create_editor_tab("other document")
        elif change == "close":
            window.tab_widget.removeTab(window.tab_widget.currentIndex())
            window.tab_file_paths.pop(target)
        elif change == "readonly":
            target.setReadOnly(True)
        else:
            # Editing the macro cannot change an already computed preview.
            definition.steps[0].replacement_text = "changed after preview"
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(MacroRunPreviewDialog, "exec", change_before_approval)
    applied = controller.preview_and_apply(definition)
    if change == "macro":
        assert applied and target.toPlainText() == "c 😀"
    else:
        assert not applied and target.toPlainText() != "c 😀"
        if change == "switch":
            assert window.editor.toPlainText() == "other document"


def test_invalid_or_unchanged_preview_cannot_be_applied_even_if_accepted(
    window, monkeypatch
):
    """不正または変更のないプレビューは、ダイアログで確定しても適用できないことを確認する。"""
    controller = window.macro_execution_controller
    assert controller is not None
    definition = macro()
    definition.steps[1].search_text = "(?=b)"
    definition.steps[1].regular_expression = True

    def try_accept(dialog):
        """適用できないプレビューに対する確定操作を再現する。"""
        assert not dialog.apply_button.isEnabled()
        assert dialog.after.toPlainText() == "a 😀"
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(MacroRunPreviewDialog, "exec", try_accept)
    assert not controller.preview_and_apply(definition)
    assert window.editor.toPlainText() == "a 😀"


def test_unexpected_runner_error_is_reported_without_body_change(window, monkeypatch):
    """本文の変更を省いた場合、想定外の実行処理のエラーが報告されることを確認する。"""
    controller = window.macro_execution_controller
    assert controller is not None

    def fail(*args):
        """処理が失敗する場合をテスト用に発生させる。"""
        raise RuntimeError("unexpected engine failure")

    messages = []
    monkeypatch.setattr(controller.manager, "preview_macro", fail)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: messages.append(args))
    assert not controller.preview_and_apply(macro())
    assert messages and window.editor.toPlainText() == "a 😀"
