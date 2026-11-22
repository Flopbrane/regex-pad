"""Editable insertion dictionaries keep bundled and Linter references intact."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from dialogs.dictionary_editor_dialog import DictionaryEditorDialog
from dialogs.macro_editor_window import MacroEditorWindow
from editor.dictionary_edit_service import (
    EDITABLE_DICTIONARIES,
    DictionaryEditError,
    DictionaryEditService,
)
from editor.paragraph_insert_rules import load_paragraph_insert_rule_book
from editor.tag_insert import tag_snippet_groups
from localization.translator import Translator
from main import MainWindow

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_only_insertion_dictionaries_are_editable(tmp_path: Path) -> None:
    service = DictionaryEditService(tmp_path)
    assert set(EDITABLE_DICTIONARIES) == {
        "html_dict.json", "markdown_dict.json", "wordpress_html_dict.json",
        "paragraph_insert_dict.json",
    }
    for name in ("lint_reference.json", "standards/core_blocks.json", "../html_dict.json"):
        with pytest.raises(DictionaryEditError, match="not editable"):
            service.load(name)
        with pytest.raises(DictionaryEditError, match="not editable"):
            service.save(name, {})


def test_save_custom_html_template_without_touching_bundled_file(tmp_path: Path) -> None:
    service = DictionaryEditService(tmp_path)
    bundled_text = (PROJECT_ROOT / "dictionaries" / "html_dict.json").read_bytes()
    data = service.load("html_dict.json")
    assert isinstance(data, list)
    strong = next(item for item in data if item["label_key"] == "tag.html.strong")
    strong["template"] = '<strong style="{cursor}">{selection}</strong>'

    result = service.save("html_dict.json", data)

    assert result == tmp_path / "html_dict.json"
    assert (PROJECT_ROOT / "dictionaries" / "html_dict.json").read_bytes() == bundled_text
    assert all((tmp_path / name).is_file() for name in EDITABLE_DICTIONARIES[:3])
    snippet = next(
        item for group in tag_snippet_groups(tmp_path)
        for item in group.snippets if item.label_key == "tag.html.strong"
    )
    assert snippet.render("文章") == ('<strong style="">文章</strong>', len('<strong style="'))


def test_invalid_edit_does_not_replace_existing_user_copy(tmp_path: Path) -> None:
    service = DictionaryEditService(tmp_path)
    data = service.load("html_dict.json")
    service.save("html_dict.json", data)
    saved_text = (tmp_path / "html_dict.json").read_bytes()
    assert isinstance(data, list)
    data[0]["template"] = "{unknown}"

    with pytest.raises(DictionaryEditError):
        service.save("html_dict.json", data)

    assert (tmp_path / "html_dict.json").read_bytes() == saved_text


def test_paragraph_shortcut_template_can_be_customized(tmp_path: Path) -> None:
    service = DictionaryEditService(tmp_path)
    data = service.load("paragraph_insert_dict.json")
    assert isinstance(data, dict)
    data["shortcut_insertions"]["inline_strong"] = "<strong >{selection}{cursor}</strong>"
    service.save("paragraph_insert_dict.json", data)

    rule_book = load_paragraph_insert_rule_book(tmp_path)
    assert rule_book.render_shortcut("inline_strong", "文章")[0] == "<strong >文章</strong>"


def test_editor_lists_no_linter_dictionary_and_saves_raw_json(
    app: QApplication, tmp_path: Path,
) -> None:
    translator = Translator(PROJECT_ROOT / "resources", "ja")
    saved: list[Path] = []
    dialog = DictionaryEditorDialog(translator, DictionaryEditService(tmp_path), saved.append)
    listed = [dialog.files.itemData(i) for i in range(dialog.files.count())]
    assert listed == list(EDITABLE_DICTIONARIES)
    dialog.tabs.setCurrentIndex(1)
    data = json.loads(dialog.raw_edit.toPlainText())
    strong = next(item for item in data if item["label_key"] == "tag.html.strong")
    strong["template"] = "<strong >{selection}{cursor}</strong>"
    dialog.raw_edit.setPlainText(json.dumps(data, ensure_ascii=False))

    assert dialog.save_current()
    assert saved == [tmp_path / "html_dict.json"]
    assert json.loads(saved[0].read_text(encoding="utf-8")) == data
    dialog.close()


def test_editor_field_change_updates_dictionary_model(
    app: QApplication, tmp_path: Path,
) -> None:
    translator = Translator(PROJECT_ROOT / "resources", "ja")
    dialog = DictionaryEditorDialog(
        translator, DictionaryEditService(tmp_path), lambda _path: None
    )
    root = dialog.tree.topLevelItem(0)
    assert root is not None
    strong = root.child(5)
    assert strong is not None
    template = strong.child(2)
    assert template is not None
    dialog.tree.setCurrentItem(template)
    dialog.value_edit.setPlainText("<strong >{selection}{cursor}</strong>")
    assert dialog.save_current()
    saved = json.loads((tmp_path / "html_dict.json").read_text(encoding="utf-8"))
    assert saved[5]["template"] == "<strong >{selection}{cursor}</strong>"
    dialog.close()


def test_preset_editor_opens_dictionary_action_and_saved_copy_becomes_active(
    app: QApplication, tmp_path: Path,
) -> None:
    translator = Translator(PROJECT_ROOT / "resources", "ja")
    preset_window = MacroEditorWindow(translator)
    requested: list[bool] = []
    preset_window.dictionary_requested.connect(lambda: requested.append(True))
    preset_window.dictionary_action.trigger()
    assert requested == [True]

    main = MainWindow(settings_path=tmp_path / "config.json", restore_unsaved_backup=False)
    user_folder = tmp_path / "user_dictionaries"
    service = DictionaryEditService(user_folder)
    data = service.load("html_dict.json")
    assert isinstance(data, list)
    save_file_path = service.save("html_dict.json", data)
    main._dictionary_saved(save_file_path)
    assert main.user_dictionary_folder == str(user_folder)
    assert main._tag_dictionaries_path() == user_folder
    assert main.insert_tag_menu.actions()
    assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))[
        "user_dictionary_folder"
    ] == str(user_folder)
    main.editor.document().setModified(False)
    main.close()
    preset_window.close()
    app.processEvents()
