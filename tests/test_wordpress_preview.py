"""WordPressのプレビューを検証する。"""

from __future__ import annotations

import io
import json
import os
import threading
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from dialogs.grammar_check_dialog import GrammarCheckDialog
from localization.translator import Translator
from main import MainWindow
from preview import wordpress_runtime
from preview.wordpress_preview import (
    RuntimePreparation,
    SnapshotExport,
    WordPressPreview,
)


@pytest.fixture(scope="session")
def app() -> QApplication:
    """GUIテストで共用するQApplicationを用意する。"""
    application = QApplication.instance() or QApplication([])
    assert isinstance(application, QApplication)
    return application


def test_cached_runtime_preparation_needs_no_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """キャッシュ済みの実行環境の準備がなしのネットワークが必要になることを確認する。"""
    (tmp_path / "ready.json").write_text(json.dumps({"playground": wordpress_runtime.PLAYGROUND_VERSION}))
    for relative in (
        "wordpress.zip", "sqlite.zip", "node_modules/@wp-playground/wordpress/index.js",
        "node_modules/@php-wasm/node-8-3/index.js",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"cached")
    node = tmp_path / "node.exe"
    monkeypatch.setattr(wordpress_runtime, "find_node", lambda root: node)
    monkeypatch.setattr(wordpress_runtime, "urlopen", lambda *args, **kwargs: pytest.fail("unexpected network"))
    assert wordpress_runtime.prepare_runtime(tmp_path, lambda stage: None, threading.Event()) == node


def test_incomplete_runtime_is_not_ready(tmp_path: Path) -> None:
    """必要な構成がそろっていない実行環境を利用可能と判定しないことを確認する。"""
    (tmp_path / "ready.json").write_text(json.dumps({"playground": wordpress_runtime.PLAYGROUND_VERSION}))
    assert not wordpress_runtime.runtime_ready(tmp_path)


def test_cancelled_download_preserves_previous_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """取り消したダウンロードが前のアーカイブを維持することを確認する。"""
    save_file_path = tmp_path / "wordpress.zip"
    save_file_path.write_bytes(b"original")
    cancel = threading.Event()

    class Response(io.BytesIO):
        """途中で中断されるダウンロードのテスト用レスポンス。"""
        def read(self, size: int | None = -1) -> bytes:
            """ダウンロードの途中までの読み込みを再現する。"""
            cancel.set()
            return super().read(size)

    monkeypatch.setattr(wordpress_runtime, "urlopen", lambda *args, **kwargs: Response(b"incomplete"))
    with pytest.raises(wordpress_runtime.PreparationCancelled):
        wordpress_runtime._download("https://wordpress.org/latest.zip", save_file_path, cancel)
    assert save_file_path.read_bytes() == b"original"
    assert not save_file_path.with_suffix(".zip.partial").exists()


def test_cancelled_setup_does_not_start_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """取り消した準備の行わないの先頭の導入を確認する。"""
    cancel = threading.Event()
    cancel.set()
    monkeypatch.setattr(wordpress_runtime, "find_node", lambda root: pytest.fail("should cancel first"))
    with pytest.raises(wordpress_runtime.PreparationCancelled):
        wordpress_runtime.prepare_runtime(tmp_path, lambda stage: None, cancel)
    assert not (tmp_path / "ready.json").exists()


@pytest.mark.parametrize("url", ["https://example.com/", "http://localhost:4321/", "http://127.0.0.1:4322/"])
def test_preview_rejects_foreign_or_wrong_port_url(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, url: str,
) -> None:
    """プレビューが別のまたは誤ったのポートのURLを拒否することを確認する。"""
    preview = WordPressPreview(tmp_path, tmp_path / "bridge.mjs")
    preview.origin = "http://127.0.0.1:4321"
    preview.sequence = 1
    failures = []
    preview.failed.connect(failures.append)
    monkeypatch.setattr("preview.wordpress_preview.QDesktopServices.openUrl", lambda url: pytest.fail("opened foreign URL"))
    preview._handle_message({"event": "rendered", "id": 1, "url": url})
    assert len(failures) == 1


def test_preview_ignores_stale_results_and_opens_current_page(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """プレビューが古くなったの結果を無視するとともに、現在のページを開くことを確認する。"""
    preview = WordPressPreview(tmp_path, tmp_path / "bridge.mjs")
    preview.origin = "http://127.0.0.1:4321"
    preview.sequence = 2
    opened = []
    failures = []
    monkeypatch.setattr("preview.wordpress_preview.QDesktopServices.openUrl", lambda url: opened.append(url.toString()) or True)
    preview.failed.connect(failures.append)
    preview._handle_message({"event": "rendered", "id": 1, "url": "http://127.0.0.1:4321/old"})
    preview._handle_message({"event": "error", "id": 1, "message": "old error"})
    assert opened == [] and failures == []
    preview._handle_message({"event": "rendered", "id": 2, "url": "http://127.0.0.1:4321/current"})
    assert opened == ["http://127.0.0.1:4321/current"]


def test_runtime_failure_is_reported_once(app: QApplication, tmp_path: Path) -> None:
    """実行環境の失敗が1回だけが報告されることを確認する。"""
    preview = WordPressPreview(tmp_path, tmp_path / "bridge.mjs")
    failures = []
    preview.failed.connect(failures.append)
    preview._handle_message({"event": "error", "message": "original error"})
    preview._process_finished(1, preview.process.exitStatus())
    assert failures == ["original error"]


def test_main_preview_sends_unsaved_snapshot_without_modifying_document(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """変更するの文書を省いた場合、メインのプレビューが未保存のスナップショットを送ることを確認する。"""
    snapshots = []
    monkeypatch.setattr(WordPressPreview, "show_preview", lambda self, title, source: snapshots.append((title, source)))
    window = MainWindow(settings_path=tmp_path / "settings.json")
    source = '<!-- wp:html --><div>style="color:red"</div><!-- /wp:html -->'
    window.editor.setPlainText(source)
    modified = window.editor.document().isModified()
    window.wordpress_preview_action.trigger()
    assert window.wordpress_preview_action in window.view_menu.actions()
    assert window.wordpress_preview_action.shortcut().toString() == "Ctrl+Alt+P"
    assert snapshots[0][1] == source
    assert window.editor.toPlainText() == source
    assert window.editor.document().isModified() == modified
    window.stop_wordpress_preview()
    assert not window.stop_wordpress_preview_action.isEnabled()


def test_wordpress_success_feedback_does_not_hide_static_structure_errors(app: QApplication, tmp_path: Path) -> None:
    """WordPressの成功のフィードバックの行わないの非表示の静的な構造のエラーを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    source = '<!-- wp:html -->\n<div>\nstyle="color:red"\n>\nBody</div>\n<!-- /wp:html -->'
    window.editor.setPlainText(source)
    window.wordpress_preview_snapshot = (window.editor, window._source_hash(source))
    window._wordpress_preview_feedback(1, 200, "")
    assert window.grammar_check_dialog is not None
    assert window.grammar_check_dialog.message_list.count() == 1
    assert window.editor.grammar_issue_lines == [3]
    assert "200" in window.grammar_check_dialog.runtime_feedback_label.text()
    assert window.editor.toPlainText() == source
    window.editor.insertPlainText("changed")
    assert window.grammar_check_dialog.runtime_feedback_label.text() == ""


def test_stale_feedback_is_not_applied_to_edited_document(app: QApplication, tmp_path: Path) -> None:
    """古くなったのフィードバックがしないの適用されたへの編集中の文書になることを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("original")
    window.wordpress_preview_snapshot = (window.editor, window._source_hash("original"))
    window.editor.setPlainText("edited")
    window._wordpress_preview_feedback(1, 200, "old warning")
    assert window.grammar_check_dialog is None


def test_engine_feedback_has_no_fake_article_line_and_can_be_copied(app: QApplication) -> None:
    """エンジンのフィードバックがなしの偽の原稿の行を持つとともに、コピー済みのが可能であることを確認する。"""
    dialog = GrammarCheckDialog(Translator(Path("resources"), "ja"))
    dialog.set_result("Static check", [])
    dialog.set_runtime_feedback("WordPress internal warning")
    assert dialog.message_list.count() == 0
    assert dialog.copy_button.isEnabled()
    dialog.copy_results_to_clipboard()
    assert QApplication.clipboard().text() == "WordPress internal warning"
    dialog.set_result("New document", [])
    assert not dialog.runtime_feedback_label.text()


def test_both_preview_actions_send_current_source_and_stop_independently(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """両方のプレビューの操作の送信の現在の原文と停止の独立にを確認する。"""
    sent = []

    def show(preview, title, source):
        """指定された原稿のプレビュー要求を記録する。"""
        sent.append((preview.mode, source))
        preview.running = True

    monkeypatch.setattr(WordPressPreview, "show_preview", show)
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.editor.setPlainText("old")
    window.wordpress_theme_preview_action.trigger()
    live_preview = window.wordpress_theme_preview
    window.editor.setPlainText("fixed")
    window.wordpress_theme_preview_action.trigger()
    assert window.wordpress_theme_preview is live_preview
    window.wordpress_preview_action.trigger()
    assert sent == [("theme", "old"), ("theme", "fixed"), ("simple", "fixed")]
    assert window.wordpress_theme_preview_action in window.view_menu.actions()
    assert window.wordpress_preview is not None and window.wordpress_theme_preview is not None
    window.wordpress_preview.stop()
    assert window.wordpress_theme_preview.running
    assert window.stop_wordpress_preview_action.isEnabled()
    window.stop_wordpress_preview_action.trigger()
    assert not window.wordpress_theme_preview.running
    assert not window.stop_wordpress_preview_action.isEnabled()
    stopped = []
    original_stop = window.wordpress_theme_preview.stop

    def stop_on_close():
        """画面を閉じたときのプレビュー停止を記録する。"""
        stopped.append(True)
        original_stop()

    window.wordpress_theme_preview.running = True
    monkeypatch.setattr(window.wordpress_theme_preview, "stop", stop_on_close)
    window.editor.document().setModified(False)
    window.close()
    assert stopped == [True] and not window.wordpress_theme_preview.running


def test_simple_preview_stops_wordpress_before_opening_file(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """開始のファイル前、単純なプレビューがWordPressを停止することを確認する。"""
    preview = WordPressPreview(tmp_path, tmp_path / "bridge.mjs", mode="simple", output_root=tmp_path)
    events = []
    monkeypatch.setattr(preview, "stop", lambda: events.append("stop"))
    monkeypatch.setattr("preview.wordpress_preview.QDesktopServices.openUrl", lambda url: events.append(url.scheme()) or True)
    preview.exporter = SnapshotExport("<p>new</p>", "http://127.0.0.1:1234/", tmp_path / "new.html", {}, preview)
    preview._snapshot_finished()
    assert events == ["stop", "file"]


def test_simple_preview_queues_latest_source_without_reusing_html(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """簡易プレビューが古いHTMLを再利用せず、最新の本文を変換することを確認する。"""
    import base64

    preview = WordPressPreview(tmp_path, tmp_path / "bridge.mjs", mode="simple", output_root=tmp_path)
    preview.ready = True
    preview.origin = "http://127.0.0.1:1234"
    sent = []
    monkeypatch.setattr(preview.process, "write", lambda data: sent.append(json.loads(data)) or len(data))
    monkeypatch.setattr(SnapshotExport, "start", lambda self: None)
    monkeypatch.setattr("preview.wordpress_preview.QDesktopServices.openUrl", lambda url: pytest.fail("opened obsolete snapshot"))
    preview.show_preview("title", "old")
    preview._handle_message({"event": "rendered", "id": 1, "url": preview.origin + "/", "html": base64.b64encode(b"old").decode()})
    preview.show_preview("title", "fixed")
    preview._snapshot_finished()
    assert [request["content"] for request in sent] == ["old", "fixed"]
    assert all(request["snapshot"] is True for request in sent)
    preview.stop()


def test_prestart_has_no_article_and_manual_preview_uses_current_text(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """事前起動がなしの原稿と手動のプレビューのを使うの現在の文字列を持つことを確認する。"""
    preview = WordPressPreview(tmp_path, tmp_path / "bridge.mjs", mode="simple")
    prepared = []
    sent = []
    monkeypatch.setattr("preview.wordpress_preview.runtime_ready", lambda root: True)
    monkeypatch.setattr(RuntimePreparation, "start", lambda thread: prepared.append(thread.cached_only))
    monkeypatch.setattr(preview.process, "write", lambda data: sent.append(json.loads(data)) or len(data))
    preview.warm_up()
    assert prepared == [True] and preview.pending is None and not sent
    preview._handle_message({"event": "ready", "origin": "http://127.0.0.1:1234", "version": "fixture"})
    assert preview.ready and not sent
    preview.show_preview("Current", "latest unsaved text")
    assert sent[0]["content"] == "latest unsaved text"
    assert not preview.warming_up and prepared == [True]
    preview.stop()


def test_prestart_does_not_download_or_report_background_error(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """事前起動の行わないのダウンロードまたは報告の背景のエラーを確認する。"""
    preview = WordPressPreview(tmp_path, tmp_path / "bridge.mjs", mode="simple")
    monkeypatch.setattr("preview.wordpress_preview.runtime_ready", lambda root: False)
    monkeypatch.setattr(RuntimePreparation, "start", lambda thread: pytest.fail("started without cached runtime"))
    preview.warm_up()
    assert not preview.running and preview.preparation is None
    monkeypatch.setattr("preview.wordpress_preview.runtime_ready", lambda root: True)
    monkeypatch.setattr("preview.wordpress_preview.find_node", lambda root: None)
    monkeypatch.setattr("preview.wordpress_preview.prepare_runtime", lambda *args: pytest.fail("background download"))
    preparation = RuntimePreparation(tmp_path, preview, cached_only=True)
    preparation.run()
    failures = []
    preview.failed.connect(failures.append)
    preview.warming_up = True
    preview._fail("background-only failure")
    assert not failures and not preview.running


def test_preview_starts_on_explicit_request_and_theme_handoff(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """プレビューが明示的な要求とテーマの引き渡しを開始することを確認する。"""
    window = MainWindow(settings_path=tmp_path / "settings.json")
    warmed = []
    monkeypatch.setattr(WordPressPreview, "warm_up", lambda preview: warmed.append(preview.mode))
    monkeypatch.setattr(WordPressPreview, "show_preview", lambda *args: None)
    assert window.wordpress_preview is None
    window.show_wordpress_preview()
    assert warmed == []
    assert window.wordpress_preview is not None
    window.wordpress_preview.warming_up = True
    window.show_wordpress_theme_preview()
    assert not window.wordpress_preview.warming_up
    assert window.wordpress_theme_preview is not None
    window.close()
