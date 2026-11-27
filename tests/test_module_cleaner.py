"""モジュールの整理を検証する。"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

import module_cleaner as cleaner


def write_file(path: Path, text: str = "fixture") -> Path:
    """テスト用のファイルを指定場所に作る。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def record(app_root: Path, items: list[dict[str, object]]) -> None:
    """整理ツールのテスト用インストール記録を用意する。"""
    write_file(app_root / "install_records/install_diff.json", json.dumps({"added_files": items}))


def owned(path: Path) -> dict[str, object]:
    """テスト対象のパスをアプリ所有として記録する。"""
    return {"path": str(path), "owned_by_this_app": True, "delete_candidate": True}


def directory_link(path: Path, target: Path) -> None:
    """整理処理の境界を試すためディレクトリリンクを作る。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(path), str(target)], capture_output=True, check=False)
        if result.returncode:
            pytest.skip("Directory junction unavailable in this test environment")
    else:
        path.symlink_to(target, target_is_directory=True)


def remove_link(path: Path) -> None:
    """テストで作ったディレクトリリンクを片付ける。"""
    if path.is_junction():
        path.rmdir()  # Remove only this junction, never its target contents.
    elif path.is_symlink():
        path.unlink()


def test_wordpress_cleanup_includes_downloads_bundle_and_snapshots_without_records(tmp_path: Path) -> None:
    """記録を省いた場合、WordPressの整理がを取得するの配布物とスナップショットを含めることを確認する。"""
    app_root = tmp_path / "portable"
    for name in (
        "runtime/wordpress-preview/wordpress.zip",
        "runtime/wordpress-preview/wordpress.zip.partial",
        "runtime/wordpress-preview/node/node-test/node.exe",
        "runtime/wordpress-preview/npm-cache/entry",
        "_internal/runtime/wordpress-preview/node_modules/php.wasm",
        "Temp/WordPressPreview/boot/bootstrap.json",
        "Temp/WordPressPreview/snapshot.html",
    ):
        write_file(app_root / name)
    preserved = [write_file(app_root / name) for name in (
        "config.json", "data/output/article.html", "runtime/venv/keep.txt",
        "_internal/keep.dll", "resources/wordpress_preview/bridge.mjs",
    )]
    assert set(cleaner.delete_candidates(app_root)) == {app_root / relative for relative in cleaner.WORDPRESS_DATA_DIRS}
    assert cleaner.clean(app_root, yes=True) == 0
    assert all(not (app_root / relative).exists() for relative in cleaner.WORDPRESS_DATA_DIRS)
    assert all(path.exists() for path in preserved)
    report = json.loads((app_root / "install_records/cleaner_report.json").read_text(encoding="utf-8"))
    assert len(report["deleted"]) == 3 and not report["errors"]
    assert report["persistent_environment_variables"] == [] and report["registry_keys"] == []


def test_manifest_is_scoped_deduplicated_and_resolves_relative_paths(tmp_path: Path) -> None:
    """一覧が範囲が限定された重複を除いたになるとともに、相対のパスを解決することを確認する。"""
    app_root = tmp_path / "app"
    nested = write_file(app_root / "runtime/wordpress-preview/wordpress.zip")
    module = write_file(app_root / "modules/owned.whl")
    external = write_file(tmp_path / "app-other/external.txt")
    unowned = write_file(app_root / "data/input/user.txt")
    record(app_root, [
        owned(nested), owned(module.relative_to(app_root)), owned(external), owned(app_root),
        {**owned(unowned), "owned_by_this_app": False},
        {**owned(unowned), "delete_candidate": "false"}, owned(Path("../app-other/external.txt")),
    ])
    assert set(cleaner.delete_candidates(app_root)) == {module, app_root / "runtime/wordpress-preview"}
    assert cleaner.clean(app_root, yes=True) == 0
    assert external.exists() and unowned.exists() and app_root.exists()


def test_scan_and_dry_run_do_not_delete_wordpress_data(tmp_path: Path) -> None:
    """走査と試行表示の行わないの削除のWordPressのデータを確認する。"""
    data = write_file(tmp_path / "runtime/wordpress-preview/wordpress.zip")
    assert cleaner.scan(tmp_path) == 0
    assert cleaner.dry_run(tmp_path) == 0
    assert data.exists()
    report = json.loads((tmp_path / "install_records/cleaner_report.json").read_text(encoding="utf-8"))
    assert report["mode"] == "dry-run" and report["deleted"] == []


def test_clean_requires_confirmation_unless_yes_is_supplied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """確認を省くオプションがないときは、整理処理を実行する前に確認を求めることを確認する。"""
    data = write_file(tmp_path / "Temp/WordPressPreview/snapshot.html")
    monkeypatch.setattr("builtins.input", lambda prompt: "cancel")
    assert cleaner.clean(tmp_path, yes=False) == 1
    assert data.exists()


@pytest.mark.parametrize("nested", [False, True])
def test_cleanup_refuses_directory_junctions_and_preserves_targets(tmp_path: Path, nested: bool) -> None:
    """整理がディレクトリのジャンクションを拒否するとともに、対象を維持することを確認する。"""
    app_root = tmp_path / "app"
    external = write_file(tmp_path / "outside/article.txt")
    runtime = app_root / "runtime/wordpress-preview"
    link = runtime / "linked" if nested else runtime
    original = write_file(app_root / "Temp/WordPressPreview/snapshot.html")
    directory_link(link, external.parent)
    try:
        with pytest.raises(ValueError, match="outside|junction"):
            cleaner.clean(app_root, yes=True)
        assert external.exists() and original.exists()
    finally:
        remove_link(link)


def test_links_inside_the_app_are_not_treated_as_owned_runtime_data(tmp_path: Path) -> None:
    """リンク内のアプリがしないの扱われるのとしてのアプリ所有の実行環境のデータであることを確認する。"""
    target = write_file(tmp_path / "app/data/user/article.txt")
    link = tmp_path / "app/runtime/wordpress-preview"
    directory_link(link, target.parent)
    try:
        with pytest.raises(ValueError, match="junction"):
            cleaner.delete_candidates(tmp_path / "app")
        assert target.exists()
    finally:
        remove_link(link)


def test_targets_are_rechecked_after_confirmation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """利用者が確認した後、対象を改めて検証することを確認する。"""
    app_root = tmp_path / "app"
    data = write_file(app_root / "runtime/wordpress-preview/wordpress.zip")
    external = write_file(tmp_path / "outside/keep.txt")
    link = data.parent / "late-junction"

    def confirm(prompt: str) -> str:
        """確認ダイアログへの利用者の応答をテスト用に代用する。"""
        directory_link(link, external.parent)
        return "DELETE"

    monkeypatch.setattr("builtins.input", confirm)
    try:
        with pytest.raises(ValueError, match="junction"):
            cleaner.clean(app_root, yes=False)
        assert data.exists() and external.exists()
    finally:
        remove_link(link)


def test_locked_files_report_incomplete_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """ロックされたファイルの報告の未完了の整理を確認する。"""
    data = write_file(tmp_path / "runtime/wordpress-preview/wordpress.zip")

    def fail(path: Path) -> None:
        """処理が失敗する場合をテスト用に発生させる。"""
        raise PermissionError("fixture file is locked")

    monkeypatch.setattr(cleaner.shutil, "rmtree", fail)
    assert cleaner.clean(tmp_path, yes=True) == 2
    assert data.exists()
    report = json.loads((tmp_path / "install_records/cleaner_report.json").read_text(encoding="utf-8"))
    assert report["deleted"] == [] and len(report["errors"]) == 1
    assert "Clean completed" not in capsys.readouterr().out
