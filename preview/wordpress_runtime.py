"""システム全体へインストールせず、任意で使うポータブルなWordPressとPHP.wasmの環境を準備する。"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import threading
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from urllib.request import urlopen

from portable_runtime import app_base_dir, bundled_base_dir

PLAYGROUND_VERSION = "3.1.60"
MINIMUM_NODE_VERSION = (24, 18, 0)
PACKAGES = ("@wp-playground/wordpress", "@php-wasm/node-8-3")
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class PreparationCancelled(Exception):
    """任意の実行環境を準備中に、利用者がプレビューを閉じた場合に発生する。"""


def _check_cancel(cancel: threading.Event) -> None:
    """実行環境の準備が中止されたか確認する。"""
    if cancel.is_set():
        raise PreparationCancelled()


def find_node(runtime_root: Path, *, include_installed: bool = True) -> Path | None:
    """同じフォルダーにあるポータブル版Nodeを優先し、次に互換性のあるインストール済みのNodeを探す。"""
    candidates = list((runtime_root / "node").glob("node-*/node.exe"))
    installed = shutil.which("node") if include_installed else None
    if installed:
        candidates.append(Path(installed))
    for candidate in candidates:
        try:
            result = subprocess.run(
                [str(candidate), "--version"], capture_output=True, text=True,
                timeout=10, check=True, creationflags=CREATE_NO_WINDOW,
            )
            version = tuple(int(part) for part in result.stdout.strip().lstrip("v").split(".")[:3])
            if version >= MINIMUM_NODE_VERSION:
                return candidate.resolve()
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
    return None


def default_runtime_root() -> Path:
    """同梱データが揃っていれば直接使い、初回に取得したデータはEXEの横に置く。"""
    bundled_root = bundled_base_dir() / "runtime/wordpress-preview"
    if bundled_base_dir() != app_base_dir() and runtime_ready(bundled_root):
        return bundled_root
    return app_base_dir() / "runtime/wordpress-preview"


def runtime_ready(runtime_root: Path) -> bool:
    """WordPressプレビューに必要な実行環境が揃っているか判定する。"""
    try:
        manifest = json.loads((runtime_root / "ready.json").read_text(encoding="utf-8"))
        if manifest.get("playground") != PLAYGROUND_VERSION:
            return False
        return all((runtime_root / relative).is_file() for relative in (
            "wordpress.zip", "sqlite.zip", "node_modules/@wp-playground/wordpress/index.js",
            "node_modules/@php-wasm/node-8-3/index.js",
        ))
    except (OSError, ValueError, AttributeError):
        return False


def _download(url: str, save_file_path: Path, cancel: threading.Event) -> None:
    """ダウンロードした内容を安全に書き込む。中断時に正常な既存アーカイブを置き換えない。"""
    temporary_path = save_file_path.with_suffix(save_file_path.suffix + ".partial")
    try:
        _check_cancel(cancel)
        with urlopen(url, timeout=15) as response, temporary_path.open("wb") as output:
            while True:
                _check_cancel(cancel)
                block = response.read(1024 * 256)
                if not block:
                    break
                output.write(block)
        _check_cancel(cancel)
        temporary_path.replace(save_file_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _portable_node(runtime_root: Path, cancel: threading.Event) -> Path:
    """同梱Nodeの実行ファイルを探す。"""
    if os.name != "nt":
        raise RuntimeError("Node.js 24.18 or later is required on this platform.")
    with urlopen("https://nodejs.org/dist/index.json", timeout=15) as response:
        releases = json.load(response)
    compatible = [
        release for release in releases
        if tuple(int(part) for part in release["version"].lstrip("v").split(".")) >= MINIMUM_NODE_VERSION
        and release.get("lts")
    ]
    if not compatible:
        raise RuntimeError("No compatible Node.js LTS release was found.")
    _check_cancel(cancel)
    version = compatible[0]["version"]
    architecture = "arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "x64"
    name = f"node-{version}-win-{architecture}"
    node_folder = runtime_root / "node"
    node_folder.mkdir(exist_ok=True)
    archive_path = node_folder / f"{name}.zip"
    base_url = f"https://nodejs.org/dist/{version}"
    with urlopen(f"{base_url}/SHASUMS256.txt", timeout=15) as response:
        hashes = {line.split()[1]: line.split()[0] for line in response.read().decode().splitlines()}
    _check_cancel(cancel)
    _download(f"{base_url}/{archive_path.name}", archive_path, cancel)
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != hashes[archive_path.name]:
        raise RuntimeError("Node.js archive checksum mismatch.")
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            _check_cancel(cancel)
            if not (node_folder / member.filename).resolve().is_relative_to(node_folder.resolve()):
                raise RuntimeError("Invalid Node.js archive path.")
            archive.extract(member, node_folder)
    return node_folder / name / "node.exe"


def _npm_cli(node: Path) -> Path | None:
    """Nodeからnpmを呼び出すためのスクリプトを探す。"""
    paths = [node.parent / "node_modules/npm/bin/npm-cli.js"]
    npm = shutil.which("npm")
    if npm:
        paths.extend([Path(npm).resolve(), Path(npm).parent / "node_modules/npm/bin/npm-cli.js"])
    return next((path for path in paths if path.is_file() and path.suffix == ".js"), None)


def _run_install(command: list[str], runtime_root: Path, cancel: threading.Event) -> None:
    """必要な依存関係を導入するコマンドを実行する。"""
    _check_cancel(cancel)
    log_path = runtime_root / "setup.log"
    with log_path.open("ab") as output, subprocess.Popen(
        command, cwd=runtime_root, stdout=output, stderr=output,
        creationflags=CREATE_NO_WINDOW,
    ) as process:
        deadline = time.monotonic() + 600
        try:
            while process.poll() is None:
                if cancel.wait(0.1):
                    raise PreparationCancelled()
                if time.monotonic() > deadline:
                    raise RuntimeError(f"Preview setup timed out. Details: {log_path}")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        if process.returncode:
            raise RuntimeError(f"Preview setup failed ({process.returncode}). Details: {log_path}")


def prepare_runtime(
    runtime_root: Path, progress: Callable[[str], None], cancel: threading.Event,
) -> Path:
    """PHP 8.3、WordPressに必要な構成、コアアーカイブをローカルにだけ準備する。"""
    runtime_root = runtime_root.resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    _check_cancel(cancel)
    node = find_node(runtime_root)
    if node is not None and runtime_ready(runtime_root):
        return node
    npm_cli = _npm_cli(node) if node else None
    if node is None or npm_cli is None:
        progress("node")
        node = _portable_node(runtime_root, cancel)
        npm_cli = _npm_cli(node)
    if npm_cli is None:
        raise RuntimeError("The portable Node.js distribution does not contain npm.")
    progress("packages")
    common = [str(node), str(npm_cli), "--cache", str(runtime_root / "npm-cache"), "--loglevel=error"]
    _run_install(common + [
        "install", "--prefix", str(runtime_root), "--no-audit", "--no-fund", "--ignore-scripts",
        "--save-exact", *(f"{package}@{PLAYGROUND_VERSION}" for package in PACKAGES),
    ], runtime_root, cancel)
    # Obtain only SQLite's 239 KB archive from the official CLI tarball. Installing
    # the CLI itself would pull every PHP version into the portable application.
    _run_install(common + [
        "pack", f"@wp-playground/cli@{PLAYGROUND_VERSION}", "--ignore-scripts",
        "--pack-destination", str(runtime_root),
    ], runtime_root, cancel)
    with tarfile.open(runtime_root / f"wp-playground-cli-{PLAYGROUND_VERSION}.tgz") as archive:
        sqlite = archive.extractfile("package/sqlite-database-integration.zip")
        if sqlite is None:
            raise RuntimeError("SQLite integration archive is missing.")
        (runtime_root / "sqlite.zip").write_bytes(sqlite.read())
    progress("wordpress")
    if not (runtime_root / "wordpress.zip").exists():
        progress("download")
        _download("https://wordpress.org/latest.zip", runtime_root / "wordpress.zip", cancel)
    with zipfile.ZipFile(runtime_root / "wordpress.zip") as archive:
        version_source = archive.read("wordpress/wp-includes/version.php").decode("utf-8")
        match = re.search(r"\$wp_version\s*=\s*'([^']+)'", version_source)
        if archive.testzip() is not None or match is None:
            raise RuntimeError("WordPress archive validation failed.")
    with zipfile.ZipFile(runtime_root / "sqlite.zip") as archive:
        if archive.testzip() is not None:
            raise RuntimeError("SQLite integration archive validation failed.")
    _check_cancel(cancel)
    data = {"playground": PLAYGROUND_VERSION, "wordpress": match.group(1), "php": "8.3"}
    temporary_path = runtime_root / "ready.partial"
    temporary_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(runtime_root / "ready.json")
    return node
