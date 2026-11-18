"""Recording-only core ported from logger_project for Regex Pad.

This module intentionally contains no query, summary, triage, or analysis
features.  Logging is best effort: a failure to serialize or append a record
is reported to stderr and is never allowed to stop the editor.
"""

from __future__ import annotations

import inspect
import sys
import threading
import traceback
import uuid
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time, timezone
from enum import Enum
from pathlib import Path
from types import FrameType, TracebackType
from typing import Any, cast

from app_logging.log_storage import append_log_record
from app_logging.log_types import LogLevel, LogOutput, LogRecord, LogWhat, LogWhere
from portable_runtime import app_base_dir


class AppLogger:
    """Write structured daily JSONL logs to the portable application folder."""

    _trace_id: ContextVar[str | None] = ContextVar(
        "regex_pad_trace_id",
        default=None,
    )

    def __init__(
        self,
        log_dir: Path | None = None,
        *,
        app_name: str = "regex_pad",
        default_output: LogOutput = LogOutput.FILE,
    ) -> None:
        self.log_dir = log_dir or app_base_dir() / "logs"
        self.app_name = app_name
        self.default_output = default_output

    def new_trace_id(self) -> str:
        """Create and activate a new trace identifier."""
        trace_id = uuid.uuid4().hex
        self._trace_id.set(trace_id)
        return trace_id

    def get_trace_id(self) -> str:
        """Return the current trace identifier, creating it when necessary."""
        return self._trace_id.get() or self.new_trace_id()

    def set_trace_id(self, trace_id: str) -> None:
        """Use an externally supplied trace identifier."""
        self._trace_id.set(trace_id)

    def _log_file(self, timestamp: datetime) -> Path:
        return self.log_dir / f"{self.app_name}_{timestamp.date().isoformat()}.jsonl"

    def _caller_where(self) -> LogWhere:
        frame: FrameType | None = inspect.currentframe()
        logger_folder = Path(__file__).resolve().parent
        try:
            while frame is not None:
                source_path = Path(frame.f_code.co_filename).resolve()
                if source_path.parent != logger_folder:
                    return {
                        "file": str(source_path),
                        "line": frame.f_lineno,
                        "function": frame.f_code.co_name,
                        "module": frame.f_globals.get("__name__", ""),
                    }
                frame = frame.f_back
        finally:
            del frame
        return {}

    def _safe(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, time):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value) and not isinstance(value, type):
            return self._safe(asdict(value))
        if isinstance(value, Mapping):
            return {str(key): self._safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [self._safe(item) for item in value]
        return str(value)

    def log(
        self,
        level: LogLevel,
        message: str,
        *,
        action: str | None = None,
        status: str | None = None,
        category: str | None = None,
        context: Mapping[str, Any] | None = None,
        where: LogWhere | None = None,
        output: LogOutput | None = None,
    ) -> bool:
        """Build and emit one structured log record."""
        try:
            timestamp = datetime.now(timezone.utc)
            resolved_output = output or self.default_output
            what: LogWhat = {"message": message}
            if action is not None:
                what["action"] = action
            if status is not None:
                what["status"] = status
            if category is not None:
                what["category"] = category

            record: LogRecord = {
                "level": level.value,
                "time": timestamp.isoformat(),
                "trace_id": self.get_trace_id(),
                "where": where or self._caller_where(),
                "what": what,
                "context": cast(
                    dict[str, Any],
                    self._safe(dict(context or {})),
                ),
                "output": resolved_output.value,
            }
            save_data = cast(dict[str, Any], self._safe(record))
            if resolved_output in (LogOutput.CONSOLE, LogOutput.BOTH):
                print(
                    f"[{record['level']}] [{record['trace_id']}] {message}",
                    file=sys.stderr,
                )
            if resolved_output in (LogOutput.FILE, LogOutput.BOTH):
                return append_log_record(self._log_file(timestamp), save_data)
            return True
        except Exception as error:  # noqa: BLE001 - the logger must never stop the app.
            print(f"[LOGGER ERROR] {error}", file=sys.stderr)
            return False

    def exception(
        self,
        error: BaseException,
        message: str | None = None,
        *,
        traceback_object: TracebackType | None = None,
        context: Mapping[str, Any] | None = None,
        level: LogLevel = LogLevel.ERROR,
        action: str | None = None,
        status: str = "failed",
        category: str = "exception",
    ) -> bool:
        """Record an exception and its traceback without re-raising it."""
        try:
            resolved_traceback = traceback_object or error.__traceback__
            exception_context = dict(context or {})
            exception_context.update(
                {
                    "exception_type": type(error).__name__,
                    "exception_message": str(error),
                    "traceback": "".join(
                        traceback.format_exception(
                            type(error),
                            error,
                            resolved_traceback,
                        )
                    ),
                }
            )
            return self.log(
                level,
                message or str(error) or type(error).__name__,
                action=action,
                status=status,
                category=category,
                context=exception_context,
            )
        except Exception as formatting_error:  # noqa: BLE001 - logging must be safe.
            return self.log(
                level,
                message or type(error).__name__,
                action=action,
                status=status,
                category=category,
                context={
                    "exception_type": type(error).__name__,
                    "exception_render_error": type(formatting_error).__name__,
                    "traceback": "unavailable",
                },
            )

    def __call__(
        self,
        error: BaseException,
        message: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """Allow the requested ``logger(error)`` recording form."""
        return self.exception(error, message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> bool:
        return self.log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> bool:
        return self.log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> bool:
        return self.log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> bool:
        return self.log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> bool:
        return self.log(LogLevel.CRITICAL, message, **kwargs)


_LOGGER: AppLogger | None = None


def get_logger() -> AppLogger:
    """Return the process-wide Regex Pad logger."""
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = AppLogger()
    return _LOGGER


def install_exception_hooks(app_logger: AppLogger | None = None) -> None:
    """Record uncaught main-thread and Python-thread exceptions.

    The original hooks are still called because execution cannot safely resume
    after an arbitrary uncaught exception.  Expected recoverable errors should
    instead be caught at their operation boundary and passed to ``logger(error)``.
    """
    resolved_logger = app_logger or get_logger()
    original_sys_hook = sys.excepthook
    original_thread_hook = threading.excepthook

    def sys_hook(
        exception_type: type[BaseException],
        error: BaseException,
        traceback_object: TracebackType | None,
    ) -> None:
        del exception_type
        resolved_logger.exception(
            error,
            "Unhandled application exception",
            traceback_object=traceback_object,
            action="sys.excepthook",
            category="unhandled_exception",
        )
        original_sys_hook(type(error), error, traceback_object)

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        if args.exc_value is None:
            original_thread_hook(args)
            return
        resolved_logger.exception(
            args.exc_value,
            "Unhandled worker-thread exception",
            traceback_object=args.exc_traceback,
            action="threading.excepthook",
            category="unhandled_exception",
            context={"thread_name": args.thread.name if args.thread else ""},
        )
        original_thread_hook(args)

    sys.excepthook = sys_hook
    threading.excepthook = thread_hook
