"""複数のテストで使う共通フィクスチャを定義する。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from app_logging import AppLogger


@pytest.fixture(autouse=True)
def dispose_test_windows() -> Iterator[None]:
    """次のGUIテストを始める前に、ウインドウとそのタイマーを解放する。"""
    yield
    application = QApplication.instance()
    if not isinstance(application, QApplication):
        return
    for widget in application.topLevelWidgets():
        if widget.parent() is None:
            widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture(autouse=True)
def isolate_default_config_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """テストの既定設定ファイルを一時フォルダーへ切り離す。"""
    import app_logging.app_logger as logger_module
    import main as main_module

    test_logger = AppLogger(tmp_path / "logs")
    monkeypatch.setattr(logger_module, "_LOGGER", test_logger)
    monkeypatch.setattr(main_module, "LOGGER", test_logger)
    monkeypatch.setattr(
        main_module,
        "default_config_path",
        lambda: tmp_path / "config.json",
    )
