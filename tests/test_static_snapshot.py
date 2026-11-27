"""静的なスナップショットを検証する。"""

from __future__ import annotations

import base64
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from preview.static_snapshot import SnapshotAssets, SnapshotCancelled, write_snapshot


@pytest.fixture
def assets_server():
    """静的プレビュー用資材を返すローカルのテストサーバーを用意する。"""
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        """静的プレビュー用の資材要求を扱うテスト用HTTPハンドラー。"""
        def do_GET(self):
            """GET要求に対しテスト用のデータを返す。"""
            requests.append(self.path)
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "http://example.invalid/blocked")
                self.end_headers()
                return
            mime, data = {
                "/css/main.css": ("text/css", b'@import "extra.css"; .box{background:url(../image.svg)}'),
                "/css/extra.css": ("text/css", b'@font-face{font-family:test;src:url(../font.woff2)}'),
                "/image.svg": ("image/svg+xml", b'<svg xmlns="http://www.w3.org/2000/svg"/>'),
                "/font.woff2": ("font/woff2", b"fixture-font"),
            }[self.path]
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            """テストサーバーの要求ログを抑制する。"""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", requests
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_snapshot_embeds_local_css_dependencies_and_keeps_native_details(
    tmp_path: Path, assets_server,
) -> None:
    """スナップショットのを埋め込むのローカルのCSSの依存関係とが標準の詳細を保持することを確認する。"""
    origin, requests = assets_server
    path = tmp_path / "snapshot.html"
    html = '''<!doctype html><html><head><link rel="stylesheet" href="/css/main.css">
    <script src="/not-fetched.js"></script><link rel="preload" href="/not-fetched.woff2">
    <style>.x{background:url('/image.svg')}</style></head><body>
    <img src="/image.svg" srcset="/image.svg 1x, /image.svg 2x">
    <img src="https://example.invalid/external.png">
    <details><summary>Open</summary>Body &amp; text<br></details>
    <div style="color:red;background:url('/image.svg')" onclick="alert(1)">Text</div>
    </body></html>'''
    write_snapshot(html, origin + "/?p=2", path, {"wordpress": "fixture"}, threading.Event())
    saved = path.read_text(encoding="utf-8")
    assert 'href="data:text/css;base64,' in saved
    assert "data:image/svg+xml;base64," in saved
    css = base64.b64decode(saved.split('href="data:text/css;base64,')[1].split('"')[0]).decode()
    assert "data:text/css;base64," in css and "data:image/svg+xml;base64," in css
    imported = base64.b64decode(css.split('data:text/css;base64,')[1].split('"')[0]).decode()
    assert "data:font/woff2;base64," in imported
    assert "<script" not in saved and "onclick" not in saved and "preload" not in saved
    assert "<details><summary>Open</summary>Body &amp; text<br></details>" in saved
    assert "https://example.invalid/external.png" in saved
    assert "color:red" in saved and origin not in saved
    assert requests.count("/image.svg") == 1
    assert len(requests) == 4
    assert path.with_suffix(".json").exists()


def test_snapshot_never_follows_foreign_redirect(assets_server) -> None:
    """スナップショットの決してが別の転送に従うことを確認する。"""
    origin, requests = assets_server
    assets = SnapshotAssets(origin, threading.Event())
    with pytest.raises(ValueError, match="redirect"):
        assets.asset("/redirect", origin)
    assert requests == ["/redirect"]


def test_cancelled_snapshot_preserves_existing_file(tmp_path: Path) -> None:
    """取り消したスナップショットが既存のファイルを維持することを確認する。"""
    path = tmp_path / "snapshot.html"
    path.write_text("original", encoding="utf-8")
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(SnapshotCancelled):
        write_snapshot("<p>new</p>", "http://127.0.0.1:1234/", path, {}, cancel)
    assert path.read_text(encoding="utf-8") == "original"
