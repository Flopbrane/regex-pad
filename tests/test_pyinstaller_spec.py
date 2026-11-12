from __future__ import annotations

from pathlib import Path

import pytest

from preview import package_runtime, wordpress_runtime


def test_pyinstaller_spec_collects_project_json_files() -> None:
    spec_text = Path("regex-pad.spec").read_text(encoding="utf-8")

    assert "def _project_json_datas():" in spec_text
    assert 'PROJECT_ROOT.rglob("*.json")' in spec_text
    assert "*_project_json_datas()," in spec_text
    assert '"build"' in spec_text
    assert '"dist"' in spec_text
    assert '"_internal"' in spec_text


def test_pyinstaller_spec_json_datas_include_current_project_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGEXPAD_SKIP_WORDPRESS_RUNTIME", "1")
    spec_path = Path("regex-pad.spec")
    spec_prefix = spec_path.read_text(encoding="utf-8").split("a = Analysis", maxsplit=1)[0]
    namespace: dict[str, object] = {"SPECPATH": str(spec_path.resolve().parent)}
    exec(spec_prefix, namespace)  # noqa: S102 - The project-owned spec prefix is evaluated for packaging coverage.

    app_datas = namespace["app_datas"]
    assert isinstance(app_datas, list)
    assert ("resources/app_text_ja.json", "resources") in app_datas
    assert ("resources/color_presets.json", "resources") in app_datas
    assert ("dictionaries/standards/standard_css.json", "dictionaries/standards") in app_datas
    assert ("dictionaries/html_dict.json", "dictionaries") in app_datas
    assert ("dictionaries/wordpress_html_dict.json", "dictionaries") in app_datas
    assert ("config.json", ".") not in app_datas
    assert ("color_presets.json", ".") not in app_datas
    assert all(not source.startswith("_internal/") for source, _target in app_datas)
    assert all(not source.startswith("runtime/") for source, _target in app_datas)


def test_pyinstaller_spec_builds_gui_app_without_upx() -> None:
    spec_text = Path("regex-pad.spec").read_text(encoding="utf-8")

    assert "console=False" in spec_text
    assert "upx=False" in spec_text


def test_build_script_uses_clean_build_without_codex_runtime_path() -> None:
    build_script = Path("build.ps1").read_text(encoding="utf-8")

    assert "--clean" in build_script
    assert "codex-runtimes" in build_script
    assert '$PyInstallerCachePath = Join-Path $env:LOCALAPPDATA "pyinstaller"' in build_script
    assert "Remove-Item -LiteralPath $ResolvedCachePath -Recurse -Force" in build_script


def test_build_script_copies_and_verifies_runtime_json_and_portable_settings() -> None:
    build_script = Path("build.ps1").read_text(encoding="utf-8")

    assert '$DictionarySourcePath = Join-Path $ProjectRoot "dictionaries"' in build_script
    assert "Assert-JsonFilesCopied" in build_script
    assert '-DestinationPath (Join-Path $InternalPath "dictionaries")' in build_script
    assert 'Join-Path $DistAppPath "config.json"' in build_script
    assert 'Join-Path $DistAppPath "color_presets.json"' in build_script
    assert "$PreservedConfigPath" in build_script
    assert "$PreservedColorPresetsPath" in build_script


def _prepared_runtime(root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import json

    for name in (
        *package_runtime.RUNTIME_FILES, "node/node-test/node.exe", "node/node-test/LICENSE",
        "node_modules/@wp-playground/wordpress/index.js", "node_modules/@php-wasm/node-8-3/index.js",
        "node_modules/@php-wasm/node-8-3/php.wasm", "node_modules/@php-wasm/node-8-3/LICENSE",
        "npm-cache/unused", "setup.log", "node/node-test/node_modules/npm/index.js", "node/node-test.zip",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    (root / "ready.json").write_text(json.dumps({"playground": wordpress_runtime.PLAYGROUND_VERSION}))
    node = root / "node/node-test/node.exe"
    monkeypatch.setattr(package_runtime, "find_node", lambda root, **kwargs: node)
    return node


def test_spec_bundles_runtime_dependencies_but_not_setup_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "runtime/wordpress-preview"
    _prepared_runtime(root, monkeypatch)
    (tmp_path / "config.json").write_text("{}")
    (tmp_path / "DELET_ITEMS_LIST.md").write_text("inventory template")
    monkeypatch.delenv("REGEXPAD_SKIP_WORDPRESS_RUNTIME", raising=False)
    prefix = Path("regex-pad.spec").read_text(encoding="utf-8").split("a = Analysis", maxsplit=1)[0]
    namespace: dict[str, object] = {"SPECPATH": str(tmp_path)}
    exec(prefix, namespace)  # noqa: S102 - Evaluate the project-owned spec data selection.
    datas = namespace["DATAS"]
    assert isinstance(datas, list)
    collected = {
        (Path(destination) / Path(source).name).as_posix() for source, destination in datas
    }
    base = "runtime/wordpress-preview/"
    assert base + "wordpress.zip" in collected
    assert base + "sqlite.zip" in collected
    assert base + "node/node-test/node.exe" in collected
    assert base + "node/node-test/LICENSE" in collected
    assert base + "node_modules/@php-wasm/node-8-3/php.wasm" in collected
    assert base + "node_modules/@php-wasm/node-8-3/LICENSE" in collected
    assert not any("npm-cache" in name or "setup.log" in name or "node-test.zip" in name for name in collected)
    assert not any("node-test/node_modules/npm" in name for name in collected)


def test_runtime_bundle_fails_when_required_files_are_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _prepared_runtime(tmp_path, monkeypatch)
    (tmp_path / "wordpress.zip").unlink()
    with pytest.raises(RuntimeError, match="not ready"):
        package_runtime.runtime_datas(tmp_path)


def test_runtime_bundle_requires_its_own_node(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _prepared_runtime(tmp_path, monkeypatch)
    monkeypatch.setattr(package_runtime, "find_node", lambda root, **kwargs: None)
    with pytest.raises(RuntimeError, match="portable Node"):
        package_runtime.runtime_datas(tmp_path)


def test_bundle_preparation_does_not_rely_on_build_machine_node(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    node = _prepared_runtime(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(package_runtime, "prepare_runtime", lambda *args: calls.append("runtime"))
    monkeypatch.setattr(package_runtime, "find_node", lambda *args, **kwargs: node if "node" in calls else None)
    monkeypatch.setattr(package_runtime, "_portable_node", lambda *args: calls.append("node") or node)
    package_runtime.prepare_bundle(tmp_path)
    assert calls == ["runtime", "node"]


def test_exe_prefers_complete_bundled_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundled = tmp_path / "_internal"
    root = bundled / "runtime/wordpress-preview"
    _prepared_runtime(root, monkeypatch)
    monkeypatch.setattr(wordpress_runtime, "app_base_dir", lambda: tmp_path)
    monkeypatch.setattr(wordpress_runtime, "bundled_base_dir", lambda: bundled)
    assert wordpress_runtime.default_runtime_root() == root
    (root / "ready.json").unlink()
    assert wordpress_runtime.default_runtime_root() == tmp_path / "runtime/wordpress-preview"
