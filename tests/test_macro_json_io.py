"""マクロのJSONの入出力を検証する。"""

from __future__ import annotations

from pathlib import Path

import pytest

from macro import json_paths
from macro.json_bridge import MacroJsonBridge, MacroJsonBridgeError
from macro.json_data_model import MacroJsonData, MacroJsonStepData
from macro.json_loader import MacroJsonLoader, MacroJsonLoadError
from macro.json_saver import MacroJsonSaveError, MacroJsonSaver


def _model() -> MacroJsonData:
    """指定された手順を持つテスト用マクロ定義を作る。"""
    return MacroJsonData(
        format_version=1,
        macro_name="日本語マクロ",
        description="保存と読込のテスト",
        steps=(
            MacroJsonStepData(
                step_name="replace",
                enabled=True,
                regular_expression=False,
                unicode_normalize=False,
                unicode_normalize_form=None,
                append_dot_to_circled_number=False,
                search_text="検索\n文字列",
                exclusion_text=None,
                replacement_text="置換文字列",
            ),
        ),
    )


def test_default_folder_is_portable_preset_folder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """既定のフォルダーがポータブルのプリセットのフォルダーになることを確認する。"""
    monkeypatch.setattr(json_paths, "app_base_dir", lambda: tmp_path)

    expected = tmp_path / "macro" / "preset_json_files"
    assert MacroJsonLoader().macro_folder == expected
    assert MacroJsonSaver().macro_folder == expected
    assert json_paths.configured_macro_folder("") == expected
    assert json_paths.configured_macro_folder(tmp_path / "macro") == expected
    custom_folder = tmp_path / "other_presets"
    assert json_paths.configured_macro_folder(custom_folder) == custom_folder


def test_saver_and_loader_round_trip_model_in_custom_folder(tmp_path: Path) -> None:
    """保存処理とローダーの往復変換のモデル内のカスタムのフォルダーを確認する。"""
    saver = MacroJsonSaver(tmp_path)
    loader = MacroJsonLoader(tmp_path)
    expected = _model()

    save_file_path = saver.save(expected, "nested/sample.json")
    actual = loader.load("nested/sample.json")

    assert save_file_path == (tmp_path / "nested/sample.json").resolve()
    assert MacroJsonBridge.to_dict(actual) == MacroJsonBridge.to_dict(expected)
    saved_text = save_file_path.read_text(encoding="utf-8")
    assert "日本語マクロ" in saved_text
    assert '"除外文字列": null' in saved_text
    assert saved_text.endswith("\n")


def test_loader_reads_version_one_reference_file() -> None:
    """ローダーがバージョンの1件の参照資料のファイルを読み取ることを確認する。"""
    model = MacroJsonLoader(Path("macro")).load("macro_format_v1.json")

    assert model.format_version == 1
    assert len(model.steps) == 2
    assert model.steps[0].step_name == "insert_@@@"
    assert model.steps[1].unicode_normalize_form == "NFKC"


def test_loader_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    """ローダーが重複したJSONのキーを拒否することを確認する。"""
    load_file_path = tmp_path / "duplicate.json"
    load_file_path.write_text(
        '{"形式バージョン": 1, "形式バージョン": 1}',
        encoding="utf-8",
    )

    with pytest.raises(MacroJsonLoadError, match="duplicate JSON key"):
        MacroJsonLoader(tmp_path).load(load_file_path.name)


def test_bridge_rejects_unknown_keys_to_prevent_lossy_save() -> None:
    """変換処理が未登録のキーのへの防止の情報を失うの保存を拒否することを確認する。"""
    load_data = MacroJsonBridge.to_dict(_model())
    load_data["未対応項目"] = "保存時に消してはいけない"

    with pytest.raises(MacroJsonBridgeError, match="unknown keys"):
        MacroJsonBridge.from_dict(load_data)


def test_relative_paths_cannot_escape_configured_folder(tmp_path: Path) -> None:
    """相対のパスのできないのエスケープの設定済みのフォルダーを確認する。"""
    with pytest.raises(MacroJsonLoadError, match="must stay inside"):
        MacroJsonLoader(tmp_path).load("../outside.json")
    with pytest.raises(MacroJsonSaveError, match="must stay inside"):
        MacroJsonSaver(tmp_path).save(_model(), "../outside.json")


def test_failed_atomic_replace_preserves_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """失敗した安全なファイル置換が既存のファイルを維持することを確認する。"""
    save_file_path = tmp_path / "macro.json"
    save_file_path.write_text("original", encoding="utf-8")
    original_replace = Path.replace

    def fail_destination_replace(source: Path, target: Path) -> Path:
        """ファイルの安全な置き換えに失敗した場合を再現する。"""
        if Path(target) == save_file_path:
            raise OSError("replace denied")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_destination_replace)

    with pytest.raises(MacroJsonSaveError, match="replace denied"):
        MacroJsonSaver(tmp_path).save(_model(), save_file_path.name)

    assert save_file_path.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.iterdir()) == [save_file_path]
