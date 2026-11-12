# ruff: noqa: F821
import os
import sys
from pathlib import Path

# ======================================================
# regex-pad PyInstaller spec
# ======================================================
# - EXE名は regex-pad.exe
# - module_cleaner.exe も同じフォルダに作成
# - dist側フォルダ名は regex-pad
# - resources / assets を _internal 配下へ同梱
# - exeアイコンに assets/icons/regex_pad_icon.ico を使用
# ======================================================

PROJECT_ROOT = Path(SPECPATH)
PROJECT_DIR = PROJECT_ROOT
sys.path.insert(0, str(PROJECT_DIR))

from preview.package_runtime import runtime_datas

APP_NAME = "regex-pad"
DIST_FOLDER_NAME = "regex-pad"

ICON_FILE = PROJECT_DIR / "assets" / "icons" / "regex_pad_icon.ico"
ICON_PATH = str(ICON_FILE) if ICON_FILE.exists() else None

def _project_json_datas():
    ignored_parts = {"build", "dist", "_internal", ".git", ".vscode", "runtime", "Temp", "install_records", "logs", "cache", "modules", "data"}
    ignored_names = {"pyrightconfig.json"}
    user_editable_root_json = {Path("config.json"), Path("color_presets.json")}
    datas = []
    for json_path in PROJECT_ROOT.rglob("*.json"):
        relative_path = json_path.relative_to(PROJECT_ROOT)
        if relative_path.name in ignored_names:
            continue
        if relative_path in user_editable_root_json:
            continue
        if any(part in ignored_parts for part in relative_path.parts):
            continue
        datas.append(
            (
                relative_path.as_posix(),
                relative_path.parent.as_posix()
                if relative_path.parent != Path(".")
                else ".",
            )
        )
    return datas


app_datas = [
    *_project_json_datas(),
]

DATAS = [*app_datas]
deletion_list = PROJECT_DIR / "DELET_ITEMS_LIST.md"
if not deletion_list.is_file():
    raise RuntimeError("DELET_ITEMS_LIST.md is required for the packaged cleanup inventory.")
DATAS.append((str(deletion_list), "."))

# An onedir distribution carries all preview dependencies under _internal.
# Direct spec builds require prepared data; build.ps1 prepares it automatically.
if os.environ.get("REGEXPAD_SKIP_WORDPRESS_RUNTIME") != "1":
    DATAS.extend(runtime_datas(PROJECT_DIR / "runtime" / "wordpress-preview"))

resources_dir = PROJECT_DIR / "resources"
if resources_dir.exists():
    DATAS.append((str(resources_dir), "resources"))

assets_dir = PROJECT_DIR / "assets"
if assets_dir.exists():
    DATAS.append((str(assets_dir), "assets"))


a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=DATAS,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
)

cleaner_a = Analysis(
    ["module_cleaner.py"],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
cleaner_pyz = PYZ(cleaner_a.pure)

cleaner_exe = EXE(
    cleaner_pyz,
    cleaner_a.scripts,
    [],
    exclude_binaries=True,
    name="module_cleaner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    cleaner_exe,
    a.binaries,
    cleaner_a.binaries,
    a.datas,
    cleaner_a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='regex-pad',
)
