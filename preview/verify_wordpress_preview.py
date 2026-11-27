"""`python -m preview.verify_wordpress_preview` で実行する任意の統合検証。

ブラウザーや公開サイトを開かず、実際のWordPress、PHP.wasm、HTTPを使う。実行環境の準備やダウンロードがあり得るため、通常のpytestからは切り離す。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import queue
import re
import subprocess
import threading
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from portable_runtime import app_base_dir, bundled_base_dir
from preview.package_runtime import RUNTIME_FILES
from preview.wordpress_runtime import CREATE_NO_WINDOW, prepare_runtime
from search.html_typo_lint import lint_html_typos


class PreviewAssets(HTMLParser):
    """実際のWordPressのフロントエンドから配信されたCSSを集める。"""

    def __init__(self) -> None:
        """WordPressのHTMLからCSSを追跡する解析状態を初期化する。"""
        super().__init__()
        self.stylesheets: list[str] = []
        self.inline_styles: list[str] = []
        self.in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """CSSに関連する開始タグを処理する。"""
        attributes = dict(attrs)
        if tag == "style":
            self.in_style = True
        if tag == "link" and "stylesheet" in (attributes.get("rel") or "").split():
            self.stylesheets.append(attributes.get("href") or "")

    def handle_endtag(self, tag: str) -> None:
        """CSSに関連する終了タグを処理する。"""
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        """タグ内に埋め込まれたCSSを集める。"""
        if self.in_style:
            self.inline_styles.append(data)


def verify(runtime_root: Path, theme: str = "regexpad-preview") -> dict[str, object]:
    """実際のWordPressプレビューの起動、描画、停止を検証する。"""
    if theme not in {"regexpad-preview", "twentytwentyfive"}:
        raise ValueError(f"Unsupported preview theme: {theme}")
    runtime_root = runtime_root.resolve()
    node = prepare_runtime(runtime_root, lambda stage: print(f"Preparing: {stage}", flush=True), threading.Event())
    runtime_sources = [runtime_root / name for name in RUNTIME_FILES]
    runtime_sources.extend(path for path in (runtime_root / "node_modules").rglob("*") if path.is_file())
    if node.is_relative_to(runtime_root):
        runtime_sources.extend((node, node.with_name("LICENSE")))
    runtime_before = {
        str(source): hashlib.sha256(source.read_bytes()).hexdigest()
        for source in runtime_sources
    }
    messages: queue.Queue[dict[str, object]] = queue.Queue()
    bridge = bundled_base_dir() / "resources/wordpress_preview/bridge.mjs"
    log_path = runtime_root / "verification.log"
    with log_path.open("w", encoding="utf-8") as errors, subprocess.Popen(
        [str(node), str(bridge), str(runtime_root), theme], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=errors, text=True, encoding="utf-8",
        creationflags=CREATE_NO_WINDOW,
    ) as process:
        assert process.stdin is not None and process.stdout is not None

        def read_messages() -> None:
            """ブリッジの出力メッセージを読み取る。"""
            assert process.stdout is not None
            for line in process.stdout:
                if line.startswith("REGEXPAD_PREVIEW "):
                    messages.put(json.loads(line.split(" ", 1)[1]))
            messages.put({"event": "stopped"})

        reader = threading.Thread(target=read_messages, daemon=True)
        reader.start()

        def wait_for(event: str) -> dict[str, object]:
            """ブリッジから必要な通知を受け取るまで待つ。"""
            while True:
                message = messages.get(timeout=90)
                if message.get("event") in {"error", "stopped"}:
                    raise RuntimeError(f"Backend failed: {message}. Details: {log_path}")
                if message.get("event") == event:
                    return message

        def render(request_id: int, content: str) -> tuple[dict[str, object], str, str]:
            """原稿をブリッジで描画して出力を検査する。"""
            assert process.stdin is not None
            process.stdin.write(json.dumps({
                "command": "render", "id": request_id, "title": "RegexPad normal preview",
                "content": content,
            }, ensure_ascii=False) + "\n")
            process.stdin.flush()
            feedback = wait_for("feedback")
            page = wait_for("rendered")
            url = str(page["url"])
            with urlopen(url, timeout=30) as response:
                assert response.status == 200
                html = response.read().decode("utf-8")
            return feedback, url, html

        url = ""
        try:
            ready = wait_for("ready")
            assert ready["theme"] == theme
            content = (
                '<!-- wp:heading {"level":3} --><h3>Normal preview test</h3><!-- /wp:heading -->'
                '<!-- wp:spacer {"height":"37px"} -->'
                '<div style="height:37px" aria-hidden="true" class="wp-block-spacer"></div>'
                '<!-- /wp:spacer -->'
                '<!-- wp:html --><div id="regexpad-inline-check" '
                'style="display:inline-block;color:#123456;background-color:#ffeecc">'
                'Inline style test<br>second line</div><!-- /wp:html -->'
                '<!-- wp:latest-posts /-->'
            )
            _feedback, url, html = render(1, content)
            assert _feedback["status"] == 200 and not _feedback.get("warnings")
            assert "Normal preview test" in html and "wp-block-latest-posts" in html
            assert 'style="height:37px"' in html
            assert 'style="display:inline-block;color:#123456;background-color:#ffeecc"' in html
            assert "Inline style test<br>second line" in html
            assets = PreviewAssets()
            assets.feed(html)
            styles = list(assets.inline_styles)
            for stylesheet in assets.stylesheets:
                asset_url = urljoin(url, stylesheet)
                assert asset_url.startswith(str(ready["origin"]) + "/")
                with urlopen(asset_url, timeout=30) as response:
                    assert response.status == 200
                    styles.append(response.read().decode("utf-8"))
            css = "\n".join(styles)
            assert ".wp-block-spacer" in css and ".wp-block-latest-posts" in css
            if theme == "regexpad-preview":
                assert "wp-theme-regexpad-preview" in html
                assert "twentytwentyfive" not in html.lower()
                assert "Manrope" not in css and "645px" not in css
                assert re.search(r"--wp--style--global--content-size:\s*100%", css)
                assert re.search(r"--wp--style--global--wide-size:\s*100%", css)
                # A deliberately requested latest-posts block may list the
                # fixture site's Hello world post. Check template chrome on an
                # article without that block, separately from dynamic rendering.
                _feedback, url, article_html = render(2, content.replace('<!-- wp:latest-posts /-->', ""))
                assert "Normal preview test" in article_html
                for unwanted in (
                    "wp-block-site-title", "wp-block-post-author", "wp-block-post-terms",
                    "wp-block-post-navigation-link", "wp-block-template-part", "wp-block-query",
                    "More Posts", "Written by", "Uncategorized", "Hello world!",
                ):
                    assert unwanted not in article_html, unwanted
                assert "<header" not in article_html and "<footer" not in article_html
            else:
                assert "wp-content/themes/twentytwentyfive/" in html
            for method, host, expected in (("POST", None, 405), ("GET", "example.com", 403)):
                headers = {"Host": host} if host else {}
                try:
                    with urlopen(Request(url, method=method, headers=headers), timeout=10):
                        raise AssertionError("Unexpectedly accepted a write or foreign Host")
                except HTTPError as error:
                    assert error.code == expected

            case_root = app_base_dir() / "tests/fixtures/linter_cases/qualification_article_20261023"
            results = []
            for request_id, name, count in ((3, "broken.wp_html", 11), (4, "fixed.wp_html", 0)):
                source = (case_root / name).read_text(encoding="utf-8-sig")
                feedback, url, html = render(request_id, source)
                findings = lint_html_typos(source)
                assert len(findings) == count
                assert feedback["status"] == 200
                assert "事務職" in html
                results.append({
                    "sample": name, "static_findings": len(findings),
                    "wordpress_http": feedback["status"], "runtime_warnings": feedback.get("warnings", ""),
                })
            return {
                "wordpress": ready["version"], "theme": ready["theme"],
                "dynamic_block": "latest-posts rendered", "loopback_only": True,
                "core_block_css": "spacer and latest-posts CSS served",
                "inline_styles": "preserved", "runtime_files_checked": len(runtime_before),
                "runtime_unchanged": True,
                "wordpress_zip_sha256": runtime_before[str(runtime_root / "wordpress.zip")],
                "http_writes_rejected": True, "article_results": results,
            }
        finally:
            if process.poll() is None:
                process.stdin.write('{"command":"shutdown"}\n')
                process.stdin.flush()
                process.stdin.close()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            reader.join(timeout=2)
            assert all(
                hashlib.sha256(Path(source).read_bytes()).hexdigest() == digest
                for source, digest in runtime_before.items()
            ), "Existing WordPress runtime data changed"
            if url:
                try:
                    with urlopen(url, timeout=2):
                        raise AssertionError("Preview server remained running after shutdown")
                except (URLError, OSError):
                    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=app_base_dir() / "runtime/wordpress-preview")
    parser.add_argument("--theme", choices=("regexpad-preview", "twentytwentyfive"), default="regexpad-preview")
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.runtime_root, arguments.theme), ensure_ascii=False, indent=2))
