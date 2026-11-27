"""ポータブルEXEに同梱するWordPressファイルを準備し、対象を選ぶ。"""
from __future__ import annotations

import argparse
import threading
from pathlib import Path

from portable_runtime import app_base_dir
from preview.wordpress_runtime import (
    _portable_node,
    find_node,
    prepare_runtime,
    runtime_ready,
)

RUNTIME_FILES = ("ready.json", "package.json", "package-lock.json", "wordpress.zip", "sqlite.zip")


def runtime_datas(runtime_root: Path) -> list[tuple[str, str]]:
    """準備用キャッシュとnpmを除き、実行ファイル、必要なデータ、ライセンスを選ぶ。"""
    runtime_root = runtime_root.resolve()
    if not runtime_ready(runtime_root):
        raise RuntimeError("WordPress runtime is not ready. Run build.ps1 to prepare it first.")
    node = find_node(runtime_root, include_installed=False)
    if node is None:
        raise RuntimeError("A portable Node is required. Run build.ps1 to prepare it.")
    paths = [runtime_root / name for name in RUNTIME_FILES]
    paths.extend([node, node.with_name("LICENSE")])
    paths.extend(path for path in (runtime_root / "node_modules").rglob("*") if path.is_file())
    datas = []
    for path in paths:
        if not path.is_file():
            raise RuntimeError(f"Required WordPress bundle file is missing: {path}")
        if not path.resolve().is_relative_to(runtime_root):
            raise RuntimeError(f"WordPress bundle file escapes its runtime directory: {path}")
        relative = path.relative_to(runtime_root)
        datas.append((str(path), (Path("runtime/wordpress-preview") / relative.parent).as_posix()))
    return datas


def prepare_bundle(runtime_root: Path) -> None:
    """ビルド環境にNodeがあっても、配布物に専用のNodeを同梱できるようにする。"""
    cancel = threading.Event()
    prepare_runtime(runtime_root, lambda stage: print(f"Preparing WordPress: {stage}", flush=True), cancel)
    if find_node(runtime_root, include_installed=False) is None:
        _portable_node(runtime_root, cancel)
    if find_node(runtime_root, include_installed=False) is None:
        raise RuntimeError("The portable Node executable could not be started.")
    runtime_datas(runtime_root)


def main() -> None:
    """配布用WordPress環境の準備または検証をコマンドラインから実行する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=app_base_dir() / "runtime/wordpress-preview")
    parser.add_argument("--verify", action="store_true", help="Check prepared data without downloading anything")
    arguments = parser.parse_args()
    if not arguments.verify:
        prepare_bundle(arguments.runtime_root)
    if find_node(arguments.runtime_root, include_installed=False) is None:
        raise RuntimeError("A working bundled Node executable is required.")
    datas = runtime_datas(arguments.runtime_root)
    print(f"WordPress bundle verified: {len(datas)} files.")


if __name__ == "__main__":
    main()
