"""WordPressでレンダリングした結果を、PHPサーバー不要の自己完結した表示用ファイルにする。"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

CSS_URL = re.compile(r'''url\(\s*(?:"([^"]*)"|'([^']*)'|([^)]*?))\s*\)''', re.IGNORECASE)
CSS_IMPORT = re.compile(r'''(@import\s+)(["'])([^"']+)\2''', re.IGNORECASE)
MAX_ASSET_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 80 * 1024 * 1024
MAX_ASSETS = 128


class SnapshotCancelled(Exception):
    """書き出し中に利用者がプレビューを停止した場合に発生する。"""


class LocalAssetRedirect(HTTPRedirectHandler):
    """静的プレビューの資材が外部へ転送されないようリダイレクトを検査する。"""
    def __init__(self, origin: str) -> None:
        """リダイレクトを許可する取得先を設定する。"""
        super().__init__()
        self.origin = urlsplit(origin)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """転送先が許可範囲内の場合にだけリダイレクトを処理する。"""
        target = urlsplit(newurl)
        if (target.scheme, target.netloc) != (self.origin.scheme, self.origin.netloc):
            raise ValueError("Unexpected preview asset redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class SnapshotAssets:
    """プレビューに埋め込むCSSと関連資材を収集する。"""
    def __init__(self, origin: str, cancel: threading.Event) -> None:
        """資材の取得元と中止条件を設定する。"""
        self.origin = origin
        self.cancel = cancel
        self.cached: dict[str, str] = {}
        self.visiting: set[str] = set()
        self.total_bytes = 0
        self.opener = build_opener(LocalAssetRedirect(origin))

    def check_cancel(self) -> None:
        """プレビューの書き出しが中止されたか確認する。"""
        if self.cancel.is_set():
            raise SnapshotCancelled()

    def css(self, text: str, base_url: str) -> str:
        """CSSを取得し、依存する資材の参照を解決する。"""
        text = CSS_IMPORT.sub(
            lambda match: f'{match[1]}"{self.asset(match[3], base_url)}"', text,
        )
        return CSS_URL.sub(
            lambda match: f'url("{self.asset(next(value for value in match.groups() if value is not None).strip(), base_url)}")',
            text,
        )

    def asset(self, value: str, base_url: str) -> str:
        """プレビューに含める資材を取得する。"""
        self.check_cancel()
        if not value or value.startswith(("data:", "#")):
            return value
        url = urljoin(base_url, value)
        parts = urlsplit(url)
        if (parts.scheme, parts.netloc) != (urlsplit(self.origin).scheme, urlsplit(self.origin).netloc):
            return url  # External images/styles stay external; never fetch them here.
        if url in self.cached:
            return self.cached[url]
        if url in self.visiting:
            raise ValueError("Circular local CSS dependency in preview snapshot")
        if len(self.cached) + len(self.visiting) >= MAX_ASSETS:
            raise ValueError("Too many local assets in preview snapshot")
        self.visiting.add(url)
        try:
            with self.opener.open(url, timeout=5) as response:
                if urlsplit(response.url).netloc != parts.netloc:
                    raise ValueError("Unexpected preview asset redirect")
                mime = response.headers.get_content_type()
                chunks: list[bytes] = []
                size = 0
                while True:
                    self.check_cancel()
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    self.total_bytes += len(chunk)
                    if size > MAX_ASSET_BYTES or self.total_bytes > MAX_TOTAL_BYTES:
                        raise ValueError("Preview snapshot assets exceed the size limit")
                    chunks.append(chunk)
                data = b"".join(chunks)
            if mime == "text/css":
                data = self.css(data.decode("utf-8-sig"), url).encode("utf-8")
            result = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
            self.cached[url] = result
            return result
        finally:
            self.visiting.remove(url)


class SnapshotHTML(HTMLParser):
    """表示用HTMLとネイティブのコントロールを保持し、実行されるスクリプトは除く。"""

    def __init__(self, page_url: str, assets: SnapshotAssets) -> None:
        """プレビューHTMLの出力と解析状態を初期化する。"""
        super().__init__(convert_charrefs=False)
        self.page_url = page_url
        self.assets = assets
        self.output: list[str] = []
        self.in_script = False
        self.in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """開始タグを処理し、表示に必要なHTMLを組み立てる。"""
        self._tag(tag, attrs, False)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """自己終了タグを処理し、表示用の出力に加える。"""
        self._tag(tag, attrs, True)

    def _tag(self, tag: str, attrs: list[tuple[str, str | None]], self_closing: bool) -> None:
        """タグと属性を静的プレビュー用に変換する。"""
        self.assets.check_cancel()
        if tag == "script":
            self.in_script = not self_closing
            return
        if self.in_script or tag == "base":
            return
        attributes = dict(attrs)
        if tag == "link" and any(
            rel in (attributes.get("rel") or "").split()
            for rel in ("preload", "modulepreload", "prefetch")
        ):
            return
        rendered: list[str] = []
        for name, value in attrs:
            if name.startswith("on"):
                continue
            if value is None:
                rendered.append(name)
                continue
            if name == "style":
                value = self.assets.css(value, self.page_url)
            elif name == "src" or (
                tag == "link" and name == "href"
                and any(rel in (attributes.get("rel") or "").split() for rel in ("stylesheet", "icon"))
            ) or tag == "video" and name == "poster":
                value = self.assets.asset(value, self.page_url)
            elif name == "srcset" and "data:" not in value:
                candidates = []
                for candidate in value.split(","):
                    parts = candidate.strip().split(maxsplit=1)
                    if parts:
                        candidates.append(self.assets.asset(parts[0], self.page_url) + (" " + parts[1] if len(parts) == 2 else ""))
                value = ", ".join(candidates)
            rendered.append(f'{name}="{escape(value, quote=True)}"')
        suffix = " /" if self_closing else ""
        self.output.append(f"<{tag}{' ' if rendered else ''}{' '.join(rendered)}{suffix}>")
        if tag == "style":
            self.in_style = True

    def handle_endtag(self, tag: str) -> None:
        """終了タグを処理し、表示用の出力を組み立てる。"""
        if tag == "script":
            self.in_script = False
        elif not self.in_script:
            self.output.append(f"</{tag}>")
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        """表示に必要な本文を出力に加える。"""
        if not self.in_script:
            self.output.append(self.assets.css(data, self.page_url) if self.in_style else data)

    def handle_entityref(self, name: str) -> None:
        """名前付き文字参照を出力に加える。"""
        if not self.in_script:
            self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        """数値文字参照を出力に加える。"""
        if not self.in_script:
            self.output.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        """HTMLコメントを解析したときの処理を行う。"""
        if not self.in_script:
            self.output.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        """文書型などの宣言を処理する。"""
        self.output.append(f"<!{decl}>")


def write_snapshot(
    html: str, page_url: str, save_file_path: Path,
    metadata: dict[str, object], cancel: threading.Event,
) -> None:
    """WordPressから得たHTMLを静的プレビューとして書き出す。"""
    parts = urlsplit(page_url)
    if parts.scheme != "http" or parts.hostname != "127.0.0.1" or not parts.port:
        raise ValueError("Unexpected WordPress snapshot origin")
    assets = SnapshotAssets(f"{parts.scheme}://{parts.netloc}", cancel)
    parser = SnapshotHTML(page_url, assets)
    parser.feed(html)
    parser.close()
    assets.check_cancel()
    data = "".join(parser.output).encode("utf-8")
    save_file_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = save_file_path.with_suffix(".html.tmp")
    temporary.write_bytes(data)
    assets.check_cancel()
    temporary.replace(save_file_path)
    saved = {**metadata, "sha256": hashlib.sha256(data).hexdigest()}
    metadata_path = save_file_path.with_suffix(".json")
    temporary = metadata_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    temporary.replace(metadata_path)


