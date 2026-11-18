from __future__ import annotations

from pathlib import Path

import pytest

from app_logging import AppLogger


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
