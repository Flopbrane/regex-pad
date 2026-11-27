"""文法チェックの結果を文書ごとのファイルに保管する。"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GrammarLintResult:
    """文法診断の要約、一覧と強調行を表す。"""
    summary: str
    rows: list[tuple[int, str]]
    issue_lines: list[int]
    source_hash: str
    document_label: str
    save_file_path: Path | None
    checked_at: datetime


class GrammarLintResultStore:
    """文法診断の一時結果の保存と削除を管理する。"""
    def __init__(self, result_folder: Path) -> None:
        """文法チェック結果の保存フォルダーを設定する。"""
        self.result_folder = result_folder

    def create_result_path(self, window_id: str, result_id: str) -> Path:
        """画面と文書を識別する結果ファイルのパスを作る。"""
        return self.result_folder / f"{window_id}-{result_id}.json"

    def save(self, result_path: Path, result: GrammarLintResult) -> None:
        """文法チェックの結果を保存する。"""
        result_path.parent.mkdir(parents=True, exist_ok=True)
        save_data = {
            "summary": result.summary,
            "rows": [
                {"line": line_number, "message": message_text}
                for line_number, message_text in result.rows
            ],
            "issue_lines": result.issue_lines,
            "source_hash": result.source_hash,
            "document_label": result.document_label,
            "save_file_path": (
                str(result.save_file_path)
                if result.save_file_path is not None
                else None
            ),
            "checked_at": result.checked_at.isoformat(),
        }
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=result_path.parent,
            delete=False,
        ) as temporary_file:
            json.dump(save_data, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.flush()
            temporary_file_path = Path(temporary_file.name)

        temporary_file_path.replace(result_path)

    def load(self, result_path: Path) -> GrammarLintResult | None:
        """保存された文法チェックの結果を読み込む。"""
        if not result_path.exists():
            return None

        try:
            load_data: dict[str, Any] = json.loads(
                result_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return None

        summary = load_data.get("summary")
        rows_data = load_data.get("rows")
        issue_lines_data = load_data.get("issue_lines")
        source_hash = load_data.get("source_hash")
        document_label = load_data.get("document_label")
        checked_at_text = load_data.get("checked_at")
        if (
            not isinstance(summary, str)
            or not isinstance(rows_data, list)
            or not isinstance(issue_lines_data, list)
            or not isinstance(source_hash, str)
            or not isinstance(document_label, str)
            or not isinstance(checked_at_text, str)
        ):
            return None

        rows: list[tuple[int, str]] = []
        for row_data in rows_data:
            if not isinstance(row_data, dict):
                return None
            line_number = row_data.get("line")
            message_text = row_data.get("message")
            if not isinstance(line_number, int) or not isinstance(message_text, str):
                return None
            rows.append((line_number, message_text))

        issue_lines = [
            line_number
            for line_number in issue_lines_data
            if isinstance(line_number, int)
        ]
        save_file_path = load_data.get("save_file_path")
        try:
            checked_at = datetime.fromisoformat(checked_at_text)
        except ValueError:
            return None

        return GrammarLintResult(
            summary=summary,
            rows=rows,
            issue_lines=issue_lines,
            source_hash=source_hash,
            document_label=document_label,
            save_file_path=Path(save_file_path)
            if isinstance(save_file_path, str)
            else None,
            checked_at=checked_at,
        )

    def delete(self, result_path: Path) -> None:
        """指定された文法診断の結果を削除する。"""
        result_path.unlink(missing_ok=True)

    def clear_result_folder(self) -> None:
        """文法診断の一時結果をまとめて片付ける。"""
        if not self.result_folder.exists():
            return
        if (
            self.result_folder.name != "lint_results"
            or self.result_folder.parent.name != "regex_pad"
        ):
            return

        try:
            shutil.rmtree(self.result_folder)
        except OSError:
            return

        try:
            self.result_folder.parent.rmdir()
        except OSError:
            pass
