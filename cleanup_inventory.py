"""手動整理向けにローカルの一覧を記録する。一覧に載せたデータは削除しない。"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from html import escape
from importlib.metadata import distributions
from pathlib import Path
from typing import Any

LIST_NAME = "DELET_ITEMS_LIST.md"
BEGIN = "<!-- REGEXPAD-INVENTORY-BEGIN -->"
END = "<!-- REGEXPAD-INVENTORY-END -->"
ENV_NAMES = ("PIP_CACHE_DIR", "MPLCONFIGDIR", "XDG_CACHE_HOME", "MYAPP_BASE_DIR", "MYAPP_MODULES_DIR")
_LOCK = threading.Lock()


def _read_json(path: Path) -> dict[str, Any]:
    """指定ファイルからJSONを読み込む。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path: Path, text: str, app_root: Path) -> None:
    """整理用の一覧をファイルに書き出す。"""
    if not path.resolve().is_relative_to(app_root):
        raise OSError(f"Inventory output must stay inside the app: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _cell(value: object) -> str:
    """一覧の表に表示するセルの内容を整える。"""
    return escape(str(value), quote=False).replace("|", "\\|").replace("\r", " ").replace("\n", " ").replace("`", "'")


def _presence(value: bool | None) -> str:
    """パスの存在状態を表示用に表す。"""
    if value is None:
        return "確認不可（権限等）"
    return "あり" if value else "なし／未作成・削除済み"


def _generated(data: dict[str, Any]) -> str:
    """一覧に載せる生成時刻を作る。"""
    rows = [f"初回記録: {data['created_at']}  ", f"最終更新: {data['updated_at']}  ", f"配置先: `{_cell(data['app_root'])}`", "",
            "## 資材・設定ファイルの保存先", "", "| 区分 | パス | 現在 | 所在・注意 |", "|---|---|---|---|"]
    for entry in data["entries"]:
        if entry["shared"]:
            continue
        rows.append(f"| {_cell(entry['kind'])} | `{_cell(entry['path'])}` | {_presence(entry['exists'])} | {_cell(entry['origin'])} |")
    for key, title in (("python_modules", "Python追加モジュール"), ("npm_modules", "WordPress実行部品（npm）")):
        rows.extend(["", f"## {title}", "", "| 名前 | バージョン | 保存先 | 現在 |", "|---|---|---|---|"])
        for module in data[key]:
            if module["shared"]:
                continue
            rows.append(f"| {_cell(module['name'])} | {_cell(module['version'])} | `{_cell(module['path'])}` | {_presence(module['exists'])} |")
        if not any(not module["shared"] for module in data[key]):
            rows.append("| 該当記録なし | — | — | — |")
    rows.extend(["", "## プロセス内の環境変数", "", "| 名前 | 値・参照先 | 適用範囲 |", "|---|---|---|"])
    for name, entry in data["environment"].items():
        if not entry["set_by_app"]:
            continue
        rows.append(f"| {_cell(name)} | `{_cell(entry['value'])}` | {'この起動で設定' if entry['set_by_app'] else '既存値を保持'}・プロセス内のみ |")
    rows.extend(["", "## 永続的な環境変数・レジストリ", "", "本アプリによる作成なし。削除する永続環境変数・レジストリキーはありません。",
                 "既存の共有Node・Python・PATH設定を削除しないでください。INI等は内容を読まず、上の保存先一覧にパスだけを記録します。"])
    if data["warnings"]:
        rows.extend(["", "## 記録時の注意", "", *[f"- {_cell(note)}" for note in data["warnings"]]])
    rows.extend(["", "---", "", "# (警告)共有する可能性が高いファイル", "",
                 "## 以下のファイル・フォルダなどは、他のソフトから共有されている可能性が有ります。", "",
                 "他のソフトでの利用と所有を確認してから、削除の要否を判断してください。自動削除対象にはしません。既存の環境変数の参照先もこちらに記載します。", "",
                 "| 区分 | Path | 現在 | 参照元・注意 |", "|---|---|---|---|"])
    shared = [entry for entry in data["entries"] if entry["shared"]]
    for entry in shared:
        rows.append(f"| {_cell(entry['kind'])} | `{_cell(entry['path'])}` | {_presence(entry['exists'])} | {_cell(entry['origin'])} |")
    shared_modules = [module for key in ("python_modules", "npm_modules") for module in data[key] if module["shared"]]
    for module in shared_modules:
        rows.append(f"| モジュール {_cell(module['name'])} | `{_cell(module['path'])}` | {_presence(module['exists'])} | 版 {_cell(module['version'])}・アプリ外の保存先・他ソフトでの利用を要確認 |")
    if not shared and not shared_modules:
        rows.append("| 該当記録なし | — | — | — |")
    return "\n".join(rows)


def refresh_inventory(
    app_root: Path, bundled_root: Path | None = None, *,
    runtime_root: Path | None = None, selected_node: Path | None = None,
    environment: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """アプリ内に実在するパスと、明示された外部参照だけを一覧に反映する。"""
    app_root = app_root.resolve()
    bundled_root = (bundled_root or app_root / "_internal").resolve()
    with _LOCK:
        warnings: list[str] = []

        def exists(path: Path) -> bool | None:
            """候補パスが存在するか確認する。"""
            try:
                return path.exists()
            except OSError as error:
                warnings.append(f"存在を確認できません: {path}: {error}")
                return None

        records = app_root / "install_records"
        previous = _read_json(records / "deletion_inventory.json")
        same_location = previous.get("app_root") == str(app_root)
        prior_entries = previous.get("entries", [])
        if not isinstance(prior_entries, list):
            prior_entries = []
        entries = {entry["path"]: entry for entry in prior_entries if same_location and isinstance(entry, dict)
                   and all(isinstance(entry.get(key), str) for key in ("path", "kind", "origin"))}

        def add(path: Path, kind: str, origin: str, *, shared: bool = False) -> None:
            """一覧に候補パスと説明を追加する。"""
            path = path.resolve()
            if not path.is_relative_to(app_root):
                shared = True
                origin += "／アプリ外・共有や所有を要確認（自動削除対象外）"
            entries[str(path)] = {"path": str(path), "kind": kind, "origin": origin, "exists": exists(path), "shared": shared}

        for relative, kind in (
            ("runtime/venv", "Python実行環境"), ("modules/site-packages", "Python追加モジュール"),
            ("modules/wheels", "Python取得ファイル"), ("cache", "アプリ用キャッシュ"),
            ("logs", "ログ"), ("data/temp", "一時データ"),
            ("runtime/wordpress-preview", "WordPress取得先"),
            ("_internal/runtime/wordpress-preview", "WordPress同梱資材"),
            ("Temp/WordPressPreview", "WordPress初期化・書き出し"),
            ("_internal/resources/wordpress_preview", "WordPressプレビュー用資材"),
            ("config.json", "アプリ設定"), ("settings.json", "旧アプリ設定"),
            ("settings.ini", "INI設定（未作成の場合は使用なし）"),
        ):
            add(app_root / relative, kind, "アプリ専用領域（同梱分または起動後に作成）")
        runtime_roots = {app_root / "runtime/wordpress-preview", bundled_root / "runtime/wordpress-preview"}
        if runtime_root is not None:
            runtime_roots.add(runtime_root.resolve())
            add(runtime_root, "WordPress追加処理先", "実際に指定された準備先")
        if selected_node is not None:
            add(selected_node, "使用するNode", "選択された実行ファイル（外部の既存Nodeは削除しない）",
                shared=not any(selected_node.resolve().is_relative_to(root.resolve()) for root in runtime_roots))
        for item in _read_json(records / "install_diff.json").get("added_files", []):
            if isinstance(item, dict) and item.get("owned_by_this_app") is True and isinstance(item.get("path"), str) and item["path"]:
                path = Path(item["path"])
                add(path if path.is_absolute() else app_root / path, "追加記録", "install_diff.jsonの追加記録（削除判断は別途確認）")

        site_paths = [app_root / "modules/site-packages", app_root / "runtime/venv/Lib/site-packages"]
        site_paths.extend((app_root / "runtime/venv/lib").glob("python*/site-packages"))
        python_modules = []
        for distribution in distributions(path=[str(path) for path in site_paths if path.is_dir()]):
            path = Path(str(distribution.locate_file(""))).resolve()
            python_modules.append({"name": distribution.metadata.get("Name", "unknown"), "version": distribution.version, "path": str(path), "exists": exists(path), "shared": not path.is_relative_to(app_root)})
        npm_modules = []
        for root in sorted(runtime_roots):
            packages = _read_json(root / "package-lock.json").get("packages", {})
            if isinstance(packages, dict):
                for name, package in packages.items():
                    if isinstance(name, str) and name.startswith("node_modules/") and isinstance(package, dict):
                        path = (root / name).resolve()
                        npm_modules.append({"name": name.removeprefix("node_modules/"), "version": str(package.get("version", "不明")), "path": str(path), "exists": exists(path), "shared": not path.is_relative_to(app_root)})
            for plugin_root in (root / "wordpress/wp-content/plugins", root / "wp-content/plugins"):
                if plugin_root.is_dir():
                    add(plugin_root, "ホスト側の追加プラグイン", "指定WordPress領域内で検出（仮想FS内のものは終了時解放）")

        # Do not scan other drives or follow links into shared installations.
        for root in (app_root, app_root / "modules", app_root / "runtime", bundled_root):
            if not root.is_dir() or root.is_symlink() or root.is_junction():
                continue
            for current, directories, files in os.walk(root, followlinks=False, onerror=lambda error: warnings.append(f"一覧を取得できません: {error}")):
                current_path = Path(current)
                directories[:] = [name for name in directories if name not in {".git", "build", "dist", "Temp", "cache", "logs", "data", "install_records", "npm-cache"}
                                  and not (current_path / name).is_symlink() and not (current_path / name).is_junction()]
                if root == app_root:
                    directories.clear()  # Root-level INI/JSON only; scoped trees below.
                for name in files:
                    if name.lower().endswith(".ini") or name.lower() in {"qt.conf", "pyvenv.cfg"} or current_path == app_root and name in {"config.json", "settings.json"}:
                        add(current_path / name, "設定ファイル", "検出したパスのみ（内容は未収集、所有は個別確認）")

        env = previous.get("environment", {}) if same_location else {}
        if environment is not None:
            env = environment
        if not isinstance(env, dict):
            env = {}
        env = {name: {"value": item["value"], "set_by_app": item.get("set_by_app") is True} for name, item in env.items()
               if name in ENV_NAMES and isinstance(item, dict) and isinstance(item.get("value"), str)}
        for name, item in env.items():
            if name in ENV_NAMES and isinstance(item, dict) and isinstance(item.get("value"), str):
                add(Path(item["value"]), "環境変数の参照先", f"{name}（既存値の場合はアプリ作成とみなさない）", shared=not item["set_by_app"])
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        for entry in entries.values():
            entry["exists"] = exists(Path(entry["path"]))
            entry.setdefault("shared", not Path(entry["path"]).is_relative_to(app_root))
        data = {"schema_version": 1, "app_root": str(app_root), "created_at": previous.get("created_at", now) if same_location else now,
                "updated_at": now, "entries": sorted(entries.values(), key=lambda entry: entry["path"].casefold()),
                "python_modules": python_modules, "npm_modules": npm_modules,
                "environment": {name: item for name, item in env.items() if name in ENV_NAMES},
                "persistent_environment_variables": [], "registry_keys": [], "warnings": warnings}
        template_path = bundled_root / LIST_NAME
        try:
            template = template_path.read_text(encoding="utf-8")
        except OSError:
            template = f"# RegexPad 追加資材・手動削除用一覧\n\n{BEGIN}\n{END}\n"
        generated = f"{BEGIN}\n{_generated(data)}\n{END}"
        successes = []
        for path in (app_root / "_internal" / LIST_NAME, records / LIST_NAME):
            try:
                source = path.read_text(encoding="utf-8") if path.exists() else template
                if BEGIN in source and END in source and source.index(BEGIN) < source.index(END):
                    start, end = source.index(BEGIN), source.index(END) + len(END)
                    text = source[:start] + generated + source[end:]
                else:
                    text = source.rstrip() + "\n\n" + generated + "\n"
                _write(path, text, app_root)
                successes.append(str(path))
            except OSError as error:
                data["warnings"].append(f"一覧を書き込めません: {path}: {error}")
        data["written_lists"] = successes
        _write(records / "deletion_inventory.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n", app_root)
        return data


def record_inventory_safely(app_root: Path, bundled_root: Path | None = None, **kwargs: Any) -> None:
    """一覧の記録に失敗しても、エディターやダウンロードの開始を妨げない。"""
    try:
        refresh_inventory(app_root, bundled_root, **kwargs)
    except Exception as error:  # noqa: BLE001 - Optional inventory must not break startup/preparation.
        try:
            path = app_root / "logs/deletion_inventory.log"
            if not path.resolve().is_relative_to(app_root.resolve()):
                return
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as output:
                output.write(f"Inventory update failed: {error}\n")
        except OSError:
            pass
