"""色候補を検証する。"""

from __future__ import annotations

import json
from pathlib import Path

from settings.color_presets import load_color_preset_catalog


def test_project_color_presets_load_text_and_background_values() -> None:
    """プロジェクトの色候補の読み込みの文字列と背景の値を確認する。"""
    catalog = load_color_preset_catalog(
        Path("color_presets.json"),
        Path("resources/color_presets.json"),
    )

    assert [preset.identifier for preset in catalog.text_colors] == [
        "red",
        "blue",
        "green",
        "orange",
        "purple",
        "pink",
        "gray",
    ]
    assert catalog.text_colors[1].display_name("ja") == "青"
    assert catalog.text_colors[1].display_name("en") == "Blue"
    assert catalog.text_colors[1].value == "#0057b8"
    assert catalog.text_colors[1].shortcuts == ("Ctrl+Alt+2",)
    assert catalog.background_colors[0].name_ja == "ローズ"
    assert catalog.background_colors[0].value == "#FFE4E4"


def test_missing_editable_color_presets_are_copied_from_bundle(
    tmp_path: Path,
) -> None:
    """不足した編集可能な色候補がコピー済みのからの配布物であることを確認する。"""
    editable_path = tmp_path / "app" / "color_presets.json"
    bundled_path = tmp_path / "bundle" / "resources" / "color_presets.json"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(
        Path("resources/color_presets.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    catalog = load_color_preset_catalog(editable_path, bundled_path)

    assert editable_path.is_file()
    assert catalog.source_path == editable_path
    assert json.loads(editable_path.read_text(encoding="utf-8")) == json.loads(
        bundled_path.read_text(encoding="utf-8")
    )


def test_invalid_editable_color_presets_fall_back_to_bundle(tmp_path: Path) -> None:
    """不正な編集可能な色候補の代替の逆戻りのへの配布物を確認する。"""
    editable_path = tmp_path / "app" / "color_presets.json"
    bundled_path = tmp_path / "bundle" / "resources" / "color_presets.json"
    editable_path.parent.mkdir(parents=True)
    bundled_path.parent.mkdir(parents=True)
    editable_path.write_text("{invalid", encoding="utf-8")
    bundled_path.write_text(
        Path("resources/color_presets.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    catalog = load_color_preset_catalog(editable_path, bundled_path)

    assert catalog.source_path == bundled_path
    assert editable_path.read_text(encoding="utf-8") == "{invalid"
    assert catalog.text_colors[0].identifier == "red"


def test_editable_color_names_values_and_shortcuts_override_bundle(
    tmp_path: Path,
) -> None:
    """編集可能な色が値とショートカットの上書き設定の配布物に名前を付けることを確認する。"""
    editable_path = tmp_path / "color_presets.json"
    editable_path.write_text(
        json.dumps(
            {
                "text_colors": [
                    {
                        "id": "custom",
                        "name": {"ja": "事業所色", "en": "Office color"},
                        "value": "#123456",
                        "shortcuts": ["Ctrl+Alt+9"],
                    }
                ],
                "background_colors": [
                    {
                        "id": "custom_background",
                        "name": {"ja": "事業所背景", "en": "Office background"},
                        "value": "#F0F0F0",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    catalog = load_color_preset_catalog(
        editable_path,
        tmp_path / "missing-bundle.json",
    )

    assert catalog.text_colors[0].name_ja == "事業所色"
    assert catalog.text_colors[0].value == "#123456"
    assert catalog.text_colors[0].shortcuts == ("Ctrl+Alt+9",)
    assert catalog.background_colors[0].name_ja == "事業所背景"
