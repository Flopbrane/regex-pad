"""削除予定を先に表示するRegex Padのポータブルフォルダー整理ツール。"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

APP_NAME = "regex-pad"
WORDPRESS_DATA_DIRS = (
    Path("runtime/wordpress-preview"),
    Path("_internal/runtime/wordpress-preview"),
    Path("Temp/WordPressPreview"),
)


def default_app_root() -> Path:
    """ポータブルアプリの既定フォルダーを求める。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent / "dist" / APP_NAME


def records_dir(app_root: Path) -> Path:
    """インストール時の記録を置くフォルダーを求める。"""
    return app_root / "install_records"


def append_log(app_root: Path, message: str) -> None:
    """整理処理のログを追記する。"""
    path = app_root / "logs" / "cleaner.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    old_text = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(old_text + message + "\n", encoding="utf-8")


def load_install_diff(app_root: Path) -> dict[str, Any]:
    """過去のインストール差分を読み込む。"""
    path = records_dir(app_root) / "install_diff.json"
    if not path.exists():
        return {"added_files": [], "added_pip_packages": []}
    return json.loads(path.read_text(encoding="utf-8"))


def is_inside(child_path: Path, parent_path: Path) -> bool:
    """対象パスが基準フォルダー内に収まるか判定する。"""
    try:
        resolved_child = child_path.resolve()
        resolved_parent = parent_path.resolve()
        resolved_child.relative_to(resolved_parent)
    except (ValueError, OSError, RuntimeError):
        return False
    return resolved_child != resolved_parent


def validate_delete_target(candidate: Path, app_root: Path) -> None:
    """アプリのルート、フォルダー外への脱出、再解析ポイントの経由を削除対象から除外する。"""
    if not is_inside(candidate, app_root):
        raise ValueError(f"Refusing cleanup outside the app folder: {candidate}")
    for path in (candidate, *candidate.parents):
        if path == app_root:
            break
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"Refusing cleanup through a link/junction: {path}")
    if candidate.is_dir():
        for current, directories, files in os.walk(candidate, followlinks=False):
            for name in (*directories, *files):
                path = Path(current) / name
                if path.is_symlink() or path.is_junction():
                    raise ValueError(f"Refusing cleanup containing a link/junction: {path}")


def delete_candidates(app_root: Path) -> list[Path]:
    """指定された候補を再検証して削除する。"""
    app_root = app_root.resolve()
    candidates: list[Path] = []
    for item in load_install_diff(app_root).get("added_files", []):
        if not isinstance(item, dict) or item.get("owned_by_this_app") is not True or item.get("delete_candidate") is not True:
            continue
        value = item.get("path")
        if not isinstance(value, str) or not value:
            continue
        candidate_path = Path(value)
        if not candidate_path.is_absolute():
            candidate_path = app_root / candidate_path
        candidate_path = Path(os.path.abspath(candidate_path))
        if candidate_path.exists() and is_inside(candidate_path, app_root):
            candidates.append(candidate_path)
    # These app-owned namespaces also cover cached/bundled/partial downloads
    # that were never recorded by the optional Python module installer.
    for relative in WORDPRESS_DATA_DIRS:
        path = app_root / relative
        if path.is_dir() or path.is_symlink() or path.is_junction():
            candidates.append(path)
    selected: list[Path] = []
    for path in sorted(set(candidates), key=lambda value: (len(value.parts), str(value).casefold())):
        if any(path.is_relative_to(parent) for parent in selected):
            continue
        validate_delete_target(path, app_root)
        selected.append(path)
    return selected


def write_report(
    app_root: Path, mode: str, candidates: list[Path], *,
    deleted: list[Path] | None = None, errors: list[str] | None = None,
) -> None:
    """整理の結果をレポートに書く。"""
    report = {
        "app_name": APP_NAME,
        "mode": mode,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "app_root": str(app_root),
        "candidates": [str(path) for path in candidates],
        "deleted": [str(path) for path in (deleted or [])],
        "errors": errors or [],
        "persistent_environment_variables": [],
        "registry_keys": [],
        "settings_note": "RegexPad uses process-local environment variables and creates no persistent environment or registry settings.",
    }
    report_path = records_dir(app_root) / "cleaner_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def scan(app_root: Path) -> int:
    """インストール記録から整理対象を調べる。"""
    candidates = delete_candidates(app_root)
    write_report(app_root, "scan", candidates)
    print(f"App folder: {app_root}")
    print(f"Delete candidates: {len(candidates)}")
    for candidate in candidates:
        print(candidate)
    return 0


def dry_run(app_root: Path) -> int:
    """削除予定を表示する。"""
    candidates = delete_candidates(app_root)
    write_report(app_root, "dry-run", candidates)
    print("Dry-run only. No files were deleted.")
    print("No persistent environment variables or registry keys are created by RegexPad.")
    for candidate in candidates:
        print(candidate)
    return 0


def clean(app_root: Path, yes: bool) -> int:
    """確認された整理処理を実行する。"""
    app_root = app_root.resolve()
    candidates = delete_candidates(app_root)
    write_report(app_root, "clean", candidates)
    if not candidates:
        print("No delete candidates were found.")
        return 0
    for candidate in candidates:
        print(candidate)
    print("Close RegexPad and its WordPress previews before cleaning.")
    if not yes and input("Type DELETE to continue: ") != "DELETE":
        print("Cancelled.")
        return 1
    # Revalidate the entire plan after confirmation, before deleting anything.
    for candidate in candidates:
        validate_delete_target(candidate, app_root)
    deleted: list[Path] = []
    errors: list[str] = []
    for candidate in candidates:
        try:
            validate_delete_target(candidate, app_root)
            if candidate.is_dir():
                shutil.rmtree(candidate)
            elif candidate.exists():
                candidate.unlink()
            deleted.append(candidate)
            append_log(app_root, f"deleted: {candidate}")
        except OSError as error:
            errors.append(f"{candidate}: {error}")
            append_log(app_root, f"failed: {candidate}: {error}")
    write_report(app_root, "clean", candidates, deleted=deleted, errors=errors)
    if errors:
        print("Clean incomplete. Close the app/previews, check cleaner_report.json, and retry.")
        return 2
    print("Clean completed. You may delete the app folder manually after closing this cleaner.")
    return 0


def main() -> int:
    """整理ツールのコマンドライン入口。"""
    parser = argparse.ArgumentParser(description="Review/remove recorded app additions and local WordPress preview data.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--scan", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--clean", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--app-root", default=str(default_app_root()))
    args = parser.parse_args()

    app_root = Path(args.app_root).resolve()
    try:
        if args.scan:
            return scan(app_root)
        if args.dry_run:
            return dry_run(app_root)
        return clean(app_root, args.yes)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Cleanup refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
