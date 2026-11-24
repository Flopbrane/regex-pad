from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from app_logging import AppLogger


@pytest.fixture(autouse=True)
def dispose_test_windows() -> Iterator[None]:
    """Release windows and their timers before the next GUI test starts."""
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
