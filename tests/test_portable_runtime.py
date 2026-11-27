"""ポータブルの実行環境を検証する。"""

from __future__ import annotations

import sys
from pathlib import Path

from portable_runtime import bundled_base_dir


def test_bundled_base_dir_uses_meipass_when_frozen(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """固定されたの場合、同梱の基準のフォルダーが_MEIPASSを使うことを確認する。"""
    bundled_path = tmp_path / "_internal"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundled_path), raising=False)

    assert bundled_base_dir() == bundled_path.resolve()
