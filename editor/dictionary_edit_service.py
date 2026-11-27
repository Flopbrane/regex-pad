"""挿入辞書のユーザー用コピーを安全に編集する。Linterの参照辞書は対象外。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from editor.paragraph_insert_rules import load_paragraph_insert_rule_book
from editor.tag_insert import tag_snippet_groups
from portable_runtime import app_base_dir, bundled_base_dir

TAG_DICTIONARIES = ("html_dict.json", "markdown_dict.json", "wordpress_html_dict.json")
EDITABLE_DICTIONARIES = (*TAG_DICTIONARIES, "paragraph_insert_dict.json")


class DictionaryEditError(ValueError):
    """辞書を読み込み、検証、保存できない場合に発生する。"""


class DictionaryEditService:
    """同梱辞書を保ち、検証済みのユーザー用コピーを書き込む。"""

    def __init__(self, user_folder: Path | None = None) -> None:
        """同梱辞書とユーザー用辞書の場所を設定する。"""
        self.bundled_folder = bundled_base_dir() / "dictionaries"
        target = user_folder or app_base_dir() / "user_dictionaries"
        self.user_folder = (
            app_base_dir() / "user_dictionaries"
            if target.resolve() == self.bundled_folder.resolve()
            else target
        )

    def load(self, name: str) -> object:
        """編集対象の辞書1件をユーザーフォルダーまたは同梱辞書から読み込む。"""
        self._check_name(name)
        load_file_path = self.user_folder / name
        if not load_file_path.is_file():
            load_file_path = self.bundled_folder / name
        try:
            return json.loads(load_file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise DictionaryEditError(f"Cannot read {load_file_path}: {error}") from error

    def validate(self, name: str, data: object) -> None:
        """書き込む前に、挿入時と同じ検証を辞書に適用する。"""
        self._check_name(name)
        if name in TAG_DICTIONARIES and not isinstance(data, list):
            raise DictionaryEditError("Tag dictionary root must be an array.")
        if name == "paragraph_insert_dict.json" and not isinstance(data, dict):
            raise DictionaryEditError("Paragraph dictionary root must be an object.")
        try:
            with tempfile.TemporaryDirectory(prefix="regexpad-dict-check-") as folder:
                temporary_folder = Path(folder)
                if name in TAG_DICTIONARIES:
                    for tag_name in TAG_DICTIONARIES:
                        if tag_name == name:
                            continue
                        source = self.user_folder / tag_name
                        if not source.is_file():
                            source = self.bundled_folder / tag_name
                        shutil.copyfile(source, temporary_folder / tag_name)
                    (temporary_folder / name).write_text(
                        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    tag_snippet_groups(temporary_folder)
                else:
                    (temporary_folder / name).write_text(
                        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    load_paragraph_insert_rule_book(temporary_folder)
        except (OSError, TypeError, ValueError) as error:
            raise DictionaryEditError(str(error)) from error

    def save(self, name: str, data: object) -> Path:
        """辞書を検証し、必要ならユーザー用コピーの場所を用意して、ファイルを安全に置き換える。"""
        self.validate(name, data)
        save_file_path = self.user_folder / name
        temporary_path: Path | None = None
        try:
            self.user_folder.mkdir(parents=True, exist_ok=True)
            # All three tag dictionaries are needed when a user folder is active.
            for tag_name in TAG_DICTIONARIES:
                target = self.user_folder / tag_name
                if tag_name != name and not target.exists():
                    shutil.copyfile(self.bundled_folder / tag_name, target)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="\n", delete=False,
                prefix=f".{save_file_path.stem}-", suffix=".tmp",
                dir=self.user_folder,
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(data, temporary, ensure_ascii=False, indent=2)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            temporary_path.replace(save_file_path)
        except OSError as error:
            raise DictionaryEditError(f"Cannot save {save_file_path}: {error}") from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return save_file_path

    @staticmethod
    def _check_name(name: str) -> None:
        """指定された辞書名が編集対象かを確認する。"""
        if name not in EDITABLE_DICTIONARIES:
            raise DictionaryEditError(f"Dictionary is not editable: {name}")
