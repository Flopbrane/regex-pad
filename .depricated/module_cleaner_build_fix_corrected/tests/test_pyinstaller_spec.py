from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_pyinstaller_spec_collects_project_json_files() -> None:
    spec_text = Path("regex-pad.spec").read_text(encoding="utf-8")

    assert "def _project_json_datas():" in spec_text
    assert 'PROJECT_ROOT.rglob("*.json")' in spec_text
    assert "*_project_json_datas()," in spec_text
    assert '"build"' in spec_text
    assert '"dist"' in spec_text
    assert '"_internal"' in spec_text


def test_pyinstaller_spec_json_datas_include_current_project_json() -> None:
    spec_path = Path("regex-pad.spec")
    spec_prefix = spec_path.read_text(encoding="utf-8").split("a = Analysis", maxsplit=1)[0]
    namespace: dict[str, object] = {"SPECPATH": str(spec_path.resolve().parent)}
    exec(spec_prefix, namespace)  # noqa: S102 - The project-owned spec prefix is evaluated for packaging coverage.

    app_datas = namespace["app_datas"]
    assert isinstance(app_datas, list)
    assert ("resources/app_text_ja.json", "resources") in app_datas
    assert ("dictionaries/standards/standard_css.json", "dictionaries/standards") in app_datas
    assert ("config.json", ".") in app_datas
    assert all(not source.startswith("_internal/") for source, _target in app_datas)


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


def test_spec_collects_both_executables_and_their_dependencies() -> None:
    """Evaluate the spec without running PyInstaller or creating binaries."""
    analyses: dict[str, SimpleNamespace] = {}
    executables: dict[str, SimpleNamespace] = {}
    collections: list[SimpleNamespace] = []

    def analysis(scripts: list[str], **_kwargs: object) -> SimpleNamespace:
        result = SimpleNamespace(
            pure=object(), scripts=scripts, binaries=object(), datas=object(),
        )
        analyses[scripts[0]] = result
        return result

    def executable(*args: object, **kwargs: object) -> SimpleNamespace:
        result = SimpleNamespace(args=args, options=kwargs)
        executables[str(kwargs["name"])] = result
        return result

    def collect(*args: object, **kwargs: object) -> SimpleNamespace:
        result = SimpleNamespace(args=args, options=kwargs)
        collections.append(result)
        return result

    spec_path = Path("regex-pad.spec")
    namespace: dict[str, object] = {
        "SPECPATH": str(spec_path.resolve().parent),
        "Analysis": analysis,
        "PYZ": lambda pure: pure,
        "EXE": executable,
        "COLLECT": collect,
    }
    exec(spec_path.read_text(encoding="utf-8"), namespace)  # noqa: S102

    assert set(analyses) == {"main.py", "module_cleaner.py"}
    assert set(executables) == {"regex-pad", "module_cleaner"}
    assert executables["regex-pad"].options["console"] is False
    assert executables["module_cleaner"].options["console"] is True
    assert executables["module_cleaner"].args[1] == ["module_cleaner.py"]
    assert len(collections) == 1
    assert collections[0].options["name"] == "regex-pad"
    for exe in executables.values():
        assert any(item is exe for item in collections[0].args)
    for entry in analyses.values():
        assert any(item is entry.binaries for item in collections[0].args)
        assert any(item is entry.datas for item in collections[0].args)
