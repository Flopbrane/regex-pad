"""整理用一覧を検証する。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication

import cleanup_inventory as inventory
import module_installer
import portable_runtime
from main import MainWindow
from preview import wordpress_preview


def write(path: Path, text: str) -> Path:
    """指定パスにテスト用の内容を書き込む。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def template(app_root: Path) -> Path:
    """整理用一覧のテストで使うテンプレートを用意する。"""
    root = app_root / "_internal"
    write(root / inventory.LIST_NAME, Path(inventory.LIST_NAME).read_text(encoding="utf-8"))
    return root


def test_first_frozen_start_records_actual_paths_and_groups_shared_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """最初の固定された先頭が実際のパスとグループの共有の参照資料を記録することを確認する。"""
    root = tmp_path / "app"
    bundled = template(root)
    shared_cache = tmp_path / "shared-cache"
    for name in inventory.ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PIP_CACHE_DIR", str(shared_cache))
    monkeypatch.setenv("SECRET_TOKEN", "must-never-be-collected")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(root / "regex-pad.exe"))
    monkeypatch.setattr(sys, "_MEIPASS", str(bundled), raising=False)
    monkeypatch.setattr(portable_runtime, "_add_site_dir", lambda path: None)
    assert portable_runtime.configure_portable_runtime() == root
    md = (bundled / inventory.LIST_NAME).read_text(encoding="utf-8")
    ordinary, shared = md.split("# (警告)共有する可能性が高いファイル", 1)
    assert str(shared_cache) not in ordinary and str(shared_cache) in shared
    data = json.loads((root / "install_records/deletion_inventory.json").read_text(encoding="utf-8"))
    assert data["environment"]["PIP_CACHE_DIR"]["set_by_app"] is False
    assert data["environment"]["MYAPP_BASE_DIR"]["set_by_app"] is True
    assert data["registry_keys"] == [] and data["persistent_environment_variables"] == []
    assert "must-never-be-collected" not in md and "SECRET_TOKEN" not in json.dumps(data)
    assert (root / "install_records" / inventory.LIST_NAME).exists()


def test_python_npm_plugins_and_ini_paths_are_recorded_without_file_contents(tmp_path: Path) -> None:
    """ファイルの内容を省いた場合、PythonのnpmのプラグインとINIのパスが記録済みのであることを確認する。"""
    root = tmp_path / "app"
    template(root)
    write(root / "modules/site-packages/example-1.2.dist-info/METADATA", "Metadata-Version: 2.1\nName: example\nVersion: 1.2\n")
    runtime = root / "runtime/wordpress-preview"
    write(runtime / "package-lock.json", json.dumps({"packages": {"node_modules/@php-wasm/example": {"version": "3.4"}}}))
    write(runtime / "wp-content/plugins/example/plugin.php", "PRIVATE_PLUGIN_BODY")
    config = write(runtime / "php.ini", "PRIVATE_INI_VALUE")
    result = inventory.refresh_inventory(root)
    assert result["python_modules"][0]["name"] == "example"
    assert result["python_modules"][0]["version"] == "1.2"
    assert result["npm_modules"][0]["name"] == "@php-wasm/example"
    md = (root / "_internal" / inventory.LIST_NAME).read_text(encoding="utf-8")
    assert str(config) in md and str(runtime / "wp-content/plugins") in md
    assert "PRIVATE_INI_VALUE" not in md and "PRIVATE_PLUGIN_BODY" not in md


def test_refresh_keeps_manual_notes_and_history_after_a_resource_disappears(tmp_path: Path) -> None:
    """リソースが見つからなくなった場合も、再取得時に手動の補足と履歴を保持することを確認する。"""
    root = tmp_path / "app"
    template(root)
    external = tmp_path / "external-runtime"
    external.mkdir()
    first = inventory.refresh_inventory(root, runtime_root=external)
    for directory in (root / "_internal", root / "install_records"):
        path = directory / inventory.LIST_NAME
        path.write_text(path.read_text(encoding="utf-8") + "\nmanual note survives\n", encoding="utf-8")
    external.rmdir()
    result = inventory.refresh_inventory(root)
    assert first["created_at"] == result["created_at"]
    assert any(entry["path"] == str(external) and not entry["exists"] for entry in result["entries"])
    for directory in (root / "_internal", root / "install_records"):
        md = (directory / inventory.LIST_NAME).read_text(encoding="utf-8")
        assert "manual note survives" in md and md.count(inventory.BEGIN) == 1


def test_download_completion_and_failure_refresh_inventory_with_external_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ダウンロードの完了のとの失敗の再表示の一覧（外部のパスあり）を確認する。"""
    application = QApplication.instance() or QApplication([])
    root = tmp_path / "app"
    bundled = template(root)
    runtime = tmp_path / "external-wp"
    node = write(tmp_path / "shared-node/node.exe", "fixture")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(wordpress_preview, "app_base_dir", lambda: root)
    monkeypatch.setattr(wordpress_preview, "bundled_base_dir", lambda: bundled)

    def prepare(*args):
        """実行環境の準備が成功した場合の処理を代用する。"""
        write(runtime / "wordpress.zip.partial", "fixture")
        return node

    monkeypatch.setattr(wordpress_preview, "prepare_runtime", prepare)
    worker = wordpress_preview.RuntimePreparation(runtime, application)
    worker.run()
    md = (bundled / inventory.LIST_NAME).read_text(encoding="utf-8")
    ordinary, shared = md.split("# (警告)共有する可能性が高いファイル", 1)
    assert str(runtime) not in ordinary and str(runtime) in shared and str(node) in shared

    def fail(*args):
        """処理が失敗する場合をテスト用に発生させる。"""
        raise RuntimeError("fixture download interrupted")

    failures = []
    worker.failed.connect(failures.append)
    monkeypatch.setattr(wordpress_preview, "prepare_runtime", fail)
    worker.run()
    assert failures == ["fixture download interrupted"]
    assert (root / "install_records/deletion_inventory.json").exists()


def test_inventory_handles_bad_metadata_and_keeps_a_writable_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """一覧のメタデータが不正でも、書き込み可能なコピーを保持できることを確認する。"""
    root = tmp_path / "app"
    bundled = template(root)
    write(root / "install_records/deletion_inventory.json", json.dumps({"app_root": str(root), "entries": None, "environment": []}))
    original = inventory._write

    def write_with_locked_internal(path, text, app_root):
        """内部フォルダーに書き込めない状況を再現する。"""
        if path.parent == bundled:
            raise PermissionError("fixture locked internal")
        original(path, text, app_root)

    monkeypatch.setattr(inventory, "_write", write_with_locked_internal)
    result = inventory.refresh_inventory(root)
    assert result["warnings"] and result["written_lists"] == [str(root / "install_records" / inventory.LIST_NAME)]
    assert "# (警告)共有する可能性が高いファイル" in (root / "install_records" / inventory.LIST_NAME).read_text(encoding="utf-8")


def test_module_install_failure_still_updates_manual_cleanup_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """モジュールの導入の失敗の引き続きが手動の整理のリストを更新することを確認する。"""
    template(tmp_path)
    monkeypatch.setattr(module_installer, "create_venv_if_needed", lambda path: None)

    def interrupted(*args, **kwargs):
        """インストールが中断する状況を再現する。"""
        write(tmp_path / "modules/site-packages/partial/file.py", "fixture")
        raise OSError("fixture pip failure")

    monkeypatch.setattr(module_installer.subprocess, "run", interrupted)
    with pytest.raises(OSError, match="fixture pip failure"):
        module_installer.install_requirements(tmp_path, tmp_path / "requirements.txt")
    assert (tmp_path / "install_records" / inventory.LIST_NAME).exists()


def test_packaging_includes_template_but_excludes_machine_specific_inventory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """配布物にテンプレートを含め、利用環境固有の一覧を除外することを確認する。"""
    write(tmp_path / inventory.LIST_NAME, "template")
    write(tmp_path / "resources/sample.json", "{}")
    for folder in ("install_records", "cache", "data", "modules", "logs", "Temp"):
        write(tmp_path / folder / "private.json", '{"private":"developer-path"}')
    monkeypatch.setenv("REGEXPAD_SKIP_WORDPRESS_RUNTIME", "1")
    prefix = Path("regex-pad.spec").read_text(encoding="utf-8").split("a = Analysis", 1)[0]
    namespace: dict[str, Any] = {"SPECPATH": str(tmp_path)}
    exec(prefix, namespace)  # noqa: S102 - Validate the project-owned packaging data collection.
    assert (str(tmp_path / inventory.LIST_NAME), ".") in namespace["DATAS"]
    assert ("resources/sample.json", "resources") in namespace["app_datas"]
    assert all("private.json" not in source for source, _target in namespace["app_datas"])


def test_packaged_editor_close_records_its_newly_saved_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """パッケージ化したエディターの閉じる操作がその新たにの保存済みの設定を記録することを確認する。"""
    import main as main_module

    application = QApplication.instance() or QApplication([])
    assert application is not None
    template(tmp_path)
    window = MainWindow(
        settings_path=tmp_path / "config.json", restore_unsaved_backup=False
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(main_module, "app_base_dir", lambda: tmp_path)
    monkeypatch.setattr(main_module, "bundled_base_dir", lambda: tmp_path / "_internal")
    window.close()
    data = json.loads((tmp_path / "install_records/deletion_inventory.json").read_text(encoding="utf-8"))
    assert any(entry["path"] == str(tmp_path / "config.json") and entry["exists"] for entry in data["entries"])


def test_directory_access_errors_are_reported_for_manual_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ディレクトリのアクセスのエラーが報告された用の手動の整理であることを確認する。"""
    template(tmp_path)
    (tmp_path / "modules").mkdir()
    original_walk = inventory.os.walk

    def blocked_walk(root, **kwargs):
        """フォルダーの列挙がアクセスエラーになる状況を再現する。"""
        if root == tmp_path / "modules":
            kwargs["onerror"](PermissionError(f"access denied: {root}"))
            return iter(())
        return original_walk(root, **kwargs)

    monkeypatch.setattr(inventory.os, "walk", blocked_walk)
    result = inventory.refresh_inventory(tmp_path)
    assert any(str(tmp_path / "modules") in warning for warning in result["warnings"])
    assert "access denied" in (tmp_path / "_internal" / inventory.LIST_NAME).read_text(encoding="utf-8")
