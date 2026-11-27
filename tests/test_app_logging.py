"""アプリのログ記録を検証する。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import app_logging.app_logger as logger_module
from app_logging import AppLogger


def _load_only_record(log_dir: Path) -> dict[str, object]:
    """出力されたログから期待する1件を読み取る。"""
    log_files = list(log_dir.glob("regex_pad_*.jsonl"))
    assert len(log_files) == 1
    lines = log_files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    return json.loads(lines[0])


def test_default_logger_uses_portable_logs_folder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """既定のロガーがポータブル環境のログフォルダーを使うことを確認する。"""
    monkeypatch.setattr(logger_module, "app_base_dir", lambda: tmp_path)

    logger = AppLogger()

    assert logger.log_dir == tmp_path / "logs"


def test_logger_call_records_exception_as_jsonl(tmp_path: Path) -> None:
    """ロガーから例外を記録すると、JSONL形式のログが出力されることを確認する。"""
    logger = AppLogger(tmp_path)

    try:
        raise ValueError("broken input")
    except ValueError as error:
        result = logger(
            error,
            "Test operation failed",
            action="test_operation",
            context={"load_file_path": tmp_path / "input.txt"},
        )

    assert result is None

    record = _load_only_record(tmp_path)
    assert record["level"] == "ERROR"
    assert record["what"] == {
        "message": "Test operation failed",
        "action": "test_operation",
        "status": "failed",
        "category": "exception",
    }
    context = record["context"]
    assert isinstance(context, dict)
    assert context["exception_type"] == "ValueError"
    assert context["exception_message"] == "broken input"
    assert "raise ValueError" in context["traceback"]
    assert context["load_file_path"].endswith("input.txt")


def test_logger_storage_failure_does_not_raise(tmp_path: Path) -> None:
    """ロガーの保存の失敗が例外を出さないことを確認する。"""
    occupied_path = tmp_path / "not-a-folder"
    occupied_path.write_text("occupied", encoding="utf-8")

    logger = AppLogger(occupied_path)

    assert logger.info("This cannot be persisted") is None


def test_logger_survives_exception_that_cannot_be_rendered(tmp_path: Path) -> None:
    """文字列化できない例外が渡されても、ログの記録処理が失敗しないことを確認する。"""
    class BrokenException(Exception):
        """文字列化に失敗する例外を再現する。"""
        def __str__(self) -> str:
            """例外の文字列化に失敗した状況を再現する。"""
            raise RuntimeError("cannot render")

    logger = AppLogger(tmp_path)

    assert logger(BrokenException(), "Unrenderable exception") is None

    record = _load_only_record(tmp_path)
    context = record["context"]
    assert isinstance(context, dict)
    assert context["exception_type"] == "BrokenException"
    assert context["exception_render_error"] == "RuntimeError"
    assert context["traceback"] == "unavailable"
