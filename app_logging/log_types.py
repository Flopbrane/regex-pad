"""Shared data types for the recording-only application logger."""

from __future__ import annotations

from enum import Enum
from typing import Any, NotRequired, TypedDict


class LogOutput(str, Enum):
    """Destination used for one log record."""

    CONSOLE = "console"
    FILE = "file"
    BOTH = "both"


class LogLevel(str, Enum):
    """Supported application log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogWhere(TypedDict, total=False):
    """Source location that produced a log record."""

    file: str
    line: int
    function: str
    module: str


class LogWhat(TypedDict):
    """Human-readable description of a log record."""

    message: str
    action: NotRequired[str]
    status: NotRequired[str]
    category: NotRequired[str]


class LogRecord(TypedDict):
    """Stable JSONL representation written by the logger."""

    level: str
    time: str
    trace_id: str
    where: LogWhere
    what: LogWhat
    context: dict[str, Any]
    output: str
