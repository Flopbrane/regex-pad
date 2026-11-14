from __future__ import annotations

import json
from pathlib import Path

import pytest

from editor.paragraph_insert_rules import (
    ParagraphInsertDictionaryError,
    load_paragraph_insert_rule_book,
)
from localization.translator import Translator


def test_default_dictionary_registers_context_menu_operation_keys() -> None:
    load_file_path = Path("dictionaries/paragraph_insert_dict.json")
    load_data = json.loads(load_file_path.read_text(encoding="utf-8"))

    assert set(load_data["operations"]) == {
        "insert_spacer",
        "insert_html",
        "decorated_block",
    }
    for operation in load_data["operations"].values():
        assert {"search", "exclude", "replacement"} <= operation.keys()


def test_default_dictionary_is_valid_and_keeps_output_text_out_of_python() -> None:
    rule_book = load_paragraph_insert_rule_book()

    assert rule_book.operation("insert_spacer").replacement.startswith("<!-- wp:spacer")
    assert rule_book.operation("insert_html").replacement.startswith("<!-- wp:html")
    assert rule_book.operation("decorated_block").replacement.startswith("<!-- wp:html")

    source = Path("editor/paragraph_splitter.py").read_text(encoding="utf-8")
    assert "<!-- wp:" not in source
    assert "<pre" not in source
    assert "ここでは" not in source


def test_user_dictionary_folder_without_paragraph_dictionary_uses_bundled_fallback(
    tmp_path: Path,
) -> None:
    rule_book = load_paragraph_insert_rule_book(tmp_path)

    assert rule_book.load_file_path == Path("dictionaries/paragraph_insert_dict.json").resolve()


def test_invalid_replacement_without_cursor_is_rejected(tmp_path: Path) -> None:
    load_data = json.loads(
        Path("dictionaries/paragraph_insert_dict.json").read_text(encoding="utf-8")
    )
    load_data["operations"]["insert_spacer"]["replacement"] = "invalid"
    (tmp_path / "paragraph_insert_dict.json").write_text(
        json.dumps(load_data, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ParagraphInsertDictionaryError, match="cursor"):
        load_paragraph_insert_rule_book(tmp_path)


def test_invalid_dictionary_with_unknown_placeholder_is_rejected(tmp_path: Path) -> None:
    load_data = json.loads(
        Path("dictionaries/paragraph_insert_dict.json").read_text(encoding="utf-8")
    )
    load_data["operations"]["insert_spacer"]["replacement"] += "{heigth}"
    (tmp_path / "paragraph_insert_dict.json").write_text(
        json.dumps(load_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(ParagraphInsertDictionaryError, match="heigth"):
        load_paragraph_insert_rule_book(tmp_path)


@pytest.mark.parametrize("language", ["ja", "en"])
def test_paragraph_insertion_linter_messages_are_available(language: str) -> None:
    translator = Translator(Path("resources"), language)
    keys = {
        "paragraph_split.dictionary_error": {"error": "sample"},
        "paragraph_split.invalid_rule": {"operation": "sample", "error": "sample"},
        "paragraph_split.not_available": {},
        "paragraph_split.cross_block": {},
        "paragraph_split.paragraph_attributes": {},
        "paragraph_split.paragraph_structure": {},
        "paragraph_split.insert_spacer_not_available": {},
        "paragraph_split.insert_html_not_available": {},
        "paragraph_split.decorated_block_not_available": {},
    }

    for key, values in keys.items():
        assert translator.text(key, **values) != key


def test_pyinstaller_spec_collects_paragraph_insert_dictionary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REGEXPAD_SKIP_WORDPRESS_RUNTIME", "1")
    spec_path = Path("regex-pad.spec")
    spec_prefix = spec_path.read_text(encoding="utf-8").split("a = Analysis", maxsplit=1)[0]
    namespace: dict[str, object] = {"SPECPATH": str(spec_path.resolve().parent)}

    exec(spec_prefix, namespace)  # noqa: S102 - Verify the project-owned spec data list.

    app_datas = namespace["app_datas"]
    assert isinstance(app_datas, list)
    assert (
        "dictionaries/paragraph_insert_dict.json",
        "dictionaries",
    ) in app_datas
