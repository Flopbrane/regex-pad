"""実際のWordPressとQtを使い、ブラウザーを開かず終了処理や所要時間を確認する任意の検証。"""
from __future__ import annotations

import argparse
import base64
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import urlopen

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QProcess, QThread, QUrl
from PySide6.QtWidgets import QApplication

from portable_runtime import app_base_dir, bundled_base_dir
from preview.wordpress_preview import WordPressPreview


def verify(runtime_root: Path) -> dict[str, object]:
    """実際のWordPressでプレビューモードの起動と停止を検証する。"""
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    opened: list[QUrl] = []
    failures: list[str] = []
    rendered: list[tuple[str, str]] = []
    feedback: list[tuple[int, int, str]] = []

    def wait_for(count: int) -> None:
        """Qtイベントを処理しながら指定条件の成立を待つ。"""
        deadline = time.monotonic() + 90
        while len(rendered) < count and not failures:
            if time.monotonic() > deadline:
                raise TimeoutError("WordPress preview lifecycle check timed out")
            app.processEvents()
            QThread.msleep(10)
        if failures:
            raise RuntimeError(failures[-1])

    with tempfile.TemporaryDirectory(prefix="regexpad-preview-check-") as temporary:
        output_root = Path(temporary)
        bridge = bundled_base_dir() / "resources/wordpress_preview/bridge.mjs"
        simple = WordPressPreview(runtime_root, bridge, mode="simple", output_root=output_root)
        theme = WordPressPreview(runtime_root, bridge, mode="theme", output_root=output_root)
        for preview in (simple, theme):
            preview.failed.connect(failures.append)
            preview.rendered.connect(lambda version, url: rendered.append((version, url)))
            preview.feedback.connect(lambda request_id, status, warnings: feedback.append((request_id, status, warnings)))
        source = (
            '<!-- wp:html --><div style="color:#123456;background:url(/wp-includes/images/blank.gif)">'
            'OLD_TOKEN<details><summary>Open</summary>Native details</details></div><!-- /wp:html -->'
        )
        timings: dict[str, float] = {}
        try:
            with patch("preview.wordpress_preview.QDesktopServices.openUrl", side_effect=lambda url: opened.append(QUrl(url)) or True):
                for index, text in enumerate((source, source.replace("OLD_TOKEN", "FIXED_TOKEN"), source.replace("OLD_TOKEN", "FIXED_TOKEN")), 1):
                    started = time.perf_counter()
                    simple.show_preview("Simple preview", text)
                    wait_for(index)
                    timings[f"simple_{index}_seconds"] = round(time.perf_counter() - started, 3)
                    assert not simple.running and not simple.ready
                    assert simple.process.state() == QProcess.ProcessState.NotRunning
                    assert opened[-1].isLocalFile()
                    html = Path(opened[-1].toLocalFile()).read_text(encoding="utf-8")
                    assert ("OLD_TOKEN" if index == 1 else "FIXED_TOKEN") in html
                    if index > 1:
                        assert "OLD_TOKEN" not in html and simple.boot_cache
                    assert "data:image/gif;base64," in html and "<details>" in html
                    assert "twentytwentyfive" not in html.lower()
                    print(f"Verified simple render {index}: {timings[f'simple_{index}_seconds']}s", flush=True)
                assert len({url.toLocalFile() for url in opened}) == 3
                assert len(feedback) == 3  # Even unchanged source went through WordPress again.
                first_snapshot = Path(opened[0].toLocalFile())
                started = time.perf_counter()
                theme.show_preview("Theme preview", source)
                wait_for(4)
                timings["theme_start_seconds"] = round(time.perf_counter() - started, 3)
                assert theme.running and theme.boot_cache
                live_process_id = theme.process.processId()
                assert live_process_id > 0
                live_url = opened[-1].toString()
                with urlopen(live_url, timeout=10) as response:
                    assert "twentytwentyfive" in response.read().decode("utf-8").lower()
                started = time.perf_counter()
                theme.show_preview("Theme preview", source.replace("OLD_TOKEN", "LIVE_FIXED"))
                wait_for(5)
                timings["theme_update_seconds"] = round(time.perf_counter() - started, 3)
                assert theme.process.processId() == live_process_id
                with urlopen(opened[-1].toString(), timeout=10) as response:
                    assert "LIVE_FIXED" in response.read().decode("utf-8")
                simple.show_preview("Independent simple preview", source.replace("OLD_TOKEN", "CONCURRENT_FIXED"))
                wait_for(6)
                assert not simple.running and theme.running
                with urlopen(live_url, timeout=10) as response:
                    assert response.status == 200
                count_before = len(rendered)
                simple.warm_up()
                deadline = time.monotonic() + 90
                while not simple.ready and not failures:
                    if time.monotonic() > deadline:
                        raise TimeoutError("Prestarting WordPress timed out")
                    app.processEvents()
                    QThread.msleep(10)
                assert not failures and len(rendered) == count_before
                assert simple.pending is None and simple.warming_up
                started = time.perf_counter()
                simple.show_preview("Prestarted simple preview", source.replace("OLD_TOKEN", "PRESTART_FIXED"))
                wait_for(7)
                timings["simple_prestarted_seconds"] = round(time.perf_counter() - started, 3)
                assert not simple.running and theme.running
                assert "PRESTART_FIXED" in Path(opened[-1].toLocalFile()).read_text(encoding="utf-8")
                theme.stop()
                assert theme.process.state() == QProcess.ProcessState.NotRunning
                try:
                    with urlopen(live_url, timeout=2):
                        raise AssertionError("WordPress remained available after explicit stop")
                except (URLError, OSError):
                    pass
                assert "OLD_TOKEN" in first_snapshot.read_text(encoding="utf-8")
                bootstrap_files = list((output_root / "boot").glob("bootstrap-*.json"))
                assert len(bootstrap_files) == 1
                database = base64.b64decode(json.loads(bootstrap_files[0].read_text(encoding="utf-8"))["database"])
                assert all(token not in database for token in (b"OLD_TOKEN", b"FIXED_TOKEN", b"LIVE_FIXED", b"CONCURRENT_FIXED", b"PRESTART_FIXED"))
                assert all(status == 200 and not warnings for _id, status, warnings in feedback)
                return {
                    "timings": timings, "simple_auto_stop": True, "theme_manual_stop": True,
                    "current_source_each_time": True, "article_html_reused": False,
                    "same_source_rerendered": True, "simple_does_not_stop_theme": True,
                    "theme_process_reused_across_previews": True,
                    "initialization_cache_has_no_article_text": True,
                    "prestart_has_no_article_or_browser_open": True,
                    "local_display_assets_embedded": True, "native_details_markup_preserved": True,
                    "snapshots_survive_wordpress_stop": True, "physical_browser_acceptance": False,
                }
        finally:
            simple.stop()
            theme.stop()
            app.processEvents()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=app_base_dir() / "runtime/wordpress-preview")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = verify(args.runtime_root)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
