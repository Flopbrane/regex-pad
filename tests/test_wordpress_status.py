from __future__ import annotations

import io
import os
import tarfile
import threading
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from main import MainWindow
from preview import wordpress_runtime
from preview.wordpress_preview import RuntimePreparation, WordPressPreview


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance() or QApplication([])
    assert isinstance(application, QApplication)
    return application


def test_prestart_status_is_not_ready_until_wordpress_acknowledges(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    preview = WordPressPreview(tmp_path, tmp_path / "bridge.mjs", mode="simple")
    monkeypatch.setattr("preview.wordpress_preview.runtime_ready", lambda root: True)
    monkeypatch.setattr(RuntimePreparation, "start", lambda self: None)
    monkeypatch.setattr(preview.process, "start", lambda *args: None)
    monkeypatch.setattr(preview.process, "write", lambda data: len(data))
    states = []
    progress = []
    preview.state_changed.connect(states.append)
    preview.progress.connect(progress.append)
    preview.warm_up()
    assert preview.state == "prepare" and not preview.ready
    preview._start_bridge("node.exe")
    assert preview.state == "boot" and not preview.ready
    assert progress == []  # Background status is visible without transient messages.
    preview._handle_message({"event": "ready", "origin": "http://127.0.0.1:1234"})
    assert preview.ready and preview.state == "ready"
    assert states == ["prepare", "boot", "ready"]
    preview.show_preview("current", "latest text")
    assert preview.state == "render"
    preview.stop()
    assert preview.state == "stopped"


def test_download_error_and_cancellation_report_truthful_status(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    preview = WordPressPreview(tmp_path, tmp_path / "bridge.mjs", mode="simple")
    monkeypatch.setattr("preview.wordpress_preview.runtime_ready", lambda root: False)
    preview.warm_up()
    assert preview.state == "not_prepared" and not preview.running
    for stage in ("prepare", "node", "packages", "wordpress", "download", "boot"):
        preview._report_progress(stage)
        assert preview.state == stage and not preview.ready
    failures = []
    preview.failed.connect(failures.append)
    preview.warming_up = True
    preview._fail("cache could not be loaded")
    assert preview.state == "failed" and not preview.running
    assert preview.last_error == "cache could not be loaded" and not failures
    preview.stop()
    assert preview.state == "stopped"


def test_right_status_persists_during_editing_and_language_changes(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    try:
        window._update_wordpress_status_label()
        assert window.wordpress_status_label.text() == "WP：停止"
        monkeypatch.setattr("preview.wordpress_preview.runtime_ready", lambda root: False)
        window._ensure_simple_wordpress_preview()
        assert window.wordpress_preview is not None
        window.wordpress_preview.warm_up()
        assert window.wordpress_status_label.text() == "WP：簡易 未準備"
        window.wordpress_preview._report_progress("boot")
        window.show()
        app.processEvents()
        expected = "WP：簡易 起動中"
        assert window.wordpress_status_label.text() == expected
        window.editor.setPlainText("edited text")
        window.statusBar().showMessage("unrelated operation")
        app.processEvents()
        assert window.wordpress_status_label.text() == expected
        assert window.wordpress_status_label.isVisible()
        window.set_language("en")
        assert window.wordpress_status_label.text() == "WP: Simple Starting"
        window.set_language("ja")
        assert window.wordpress_status_label.text() == expected
    finally:
        window.editor.document().setModified(False)
        window.close()


def test_simple_stop_does_not_hide_live_status_or_background_failure(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    monkeypatch.setattr(WordPressPreview, "show_preview", lambda *args: None)
    try:
        window.show_wordpress_theme_preview()
        window._ensure_simple_wordpress_preview()
        simple = window.wordpress_preview
        theme = window.wordpress_theme_preview
        assert simple is not None and theme is not None
        theme._handle_message({"event": "ready", "origin": "http://127.0.0.1:1234"})
        simple._report_progress("export")
        assert window.wordpress_status_label.text() == "WP：簡易 書出中 / 本格 使用可能"
        simple.stop()
        assert window.wordpress_status_label.text() == "WP：本格 使用可能"
        simple.closing = False
        simple.warming_up = True
        simple._fail("missing <asset>")
        assert window.wordpress_status_label.text() == "WP：簡易 失敗 / 本格 使用可能"
        assert "missing &lt;asset&gt;" in window.wordpress_status_label.toolTip()
        window.stop_wordpress_preview()
        assert window.wordpress_status_label.text() == "WP：停止"
    finally:
        window.close()


def test_core_download_state_is_emitted_only_when_an_archive_is_downloaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    sqlite_bytes = io.BytesIO()
    with zipfile.ZipFile(sqlite_bytes, "w") as archive:
        archive.writestr("sqlite.php", "fixture")
    with tarfile.open(tmp_path / f"wp-playground-cli-{wordpress_runtime.PLAYGROUND_VERSION}.tgz", "w:gz") as archive:
        info = tarfile.TarInfo("package/sqlite-database-integration.zip")
        info.size = len(sqlite_bytes.getvalue())
        archive.addfile(info, io.BytesIO(sqlite_bytes.getvalue()))
    monkeypatch.setattr(wordpress_runtime, "find_node", lambda root: tmp_path / "node.exe")
    monkeypatch.setattr(wordpress_runtime, "_npm_cli", lambda node: tmp_path / "npm.js")
    monkeypatch.setattr(wordpress_runtime, "_run_install", lambda *args: None)
    stages = []

    def download(url, save_file_path, cancel):
        assert stages[-1] == "download"
        with zipfile.ZipFile(save_file_path, "w") as archive:
            archive.writestr("wordpress/wp-includes/version.php", "<?php $wp_version = 'fixture';")

    monkeypatch.setattr(wordpress_runtime, "_download", download)
    wordpress_runtime.prepare_runtime(tmp_path, stages.append, threading.Event())
    assert stages[-2:] == ["wordpress", "download"]
    stages.clear()
    wordpress_runtime.prepare_runtime(tmp_path, stages.append, threading.Event())
    assert stages[-1] == "wordpress" and "download" not in stages
