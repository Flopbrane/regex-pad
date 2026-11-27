"""Regex Padのポータブル実行時に使うパスを設定する。"""
from __future__ import annotations

import os
import site
import sys
from pathlib import Path


def app_base_dir() -> Path:
    """実行時データ、キャッシュ、モデルを置くフォルダーを返す。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_base_dir() -> Path:
    """読み取り専用の同梱データを置くフォルダーを返す。"""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", app_base_dir())).resolve()
    return Path(__file__).resolve().parent


def _add_site_dir(site_dir: Path) -> None:
    """指定したサイトディレクトリをPythonの検索パスに追加する。"""
    if site_dir.exists():
        site.addsitedir(str(site_dir))


def configure_portable_runtime() -> Path:
    """アプリが使うモジュールとキャッシュをアプリフォルダーの下に置く。"""
    base_dir = app_base_dir()
    runtime_dir = base_dir / "runtime"
    venv_dir = runtime_dir / "venv"
    modules_dir = base_dir / "modules"
    cache_dir = base_dir / "cache"
    data_dir = base_dir / "data"

    for folder_path in (
        venv_dir,
        modules_dir / "site-packages",
        modules_dir / "wheels",
        cache_dir / "pip",
        cache_dir / "app_cache",
        data_dir / "input",
        data_dir / "output",
        data_dir / "temp",
        base_dir / "logs",
        base_dir / "install_records",
    ):
        folder_path.mkdir(parents=True, exist_ok=True)

    _add_site_dir(modules_dir / "site-packages")
    _add_site_dir(venv_dir / "Lib" / "site-packages")
    _add_site_dir(venv_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages")

    overrides = {
        "PIP_CACHE_DIR": str(cache_dir / "pip"),
        "MPLCONFIGDIR": str(cache_dir / "matplotlib"),
        "XDG_CACHE_HOME": str(cache_dir / "xdg"),
        "MYAPP_BASE_DIR": str(base_dir),
        "MYAPP_MODULES_DIR": str(modules_dir / "site-packages"),
    }
    environment = {}
    for name, value in overrides.items():
        set_by_app = name not in os.environ
        os.environ.setdefault(name, value)
        environment[name] = {"value": os.environ[name], "set_by_app": set_by_app}
    if getattr(sys, "frozen", False):
        from cleanup_inventory import record_inventory_safely

        record_inventory_safely(base_dir, bundled_base_dir(), environment=environment)

    return base_dir
