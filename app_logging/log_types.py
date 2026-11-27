"""ログ記録専用ロガーで共有するデータ型を定義する。"""

from __future__ import annotations

from enum import Enum
from typing import Any, NotRequired, TypedDict


class LogOutput(str, Enum):
    """ログレコード1件の出力先を表す。"""

    CONSOLE = "console"
    FILE = "file"
    BOTH = "both"


class LogLevel(str, Enum):
    """アプリで使えるログレベルを定義する。"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogWhere(TypedDict, total=False):
    """ログを発生させたソースコード上の位置を表す。"""

    file: str
    line: int
    function: str
    module: str


class LogWhat(TypedDict):
    """人が読めるログレコードの説明を表す。"""

    message: str
    action: NotRequired[str]
    status: NotRequired[str]
    category: NotRequired[str]


class LogRecord(TypedDict):
    """ロガーが出力するJSONLレコードの形式を表す。"""

    level: str
    time: str
    trace_id: str
    where: LogWhere
    what: LogWhat
    context: dict[str, Any]
    output: str
