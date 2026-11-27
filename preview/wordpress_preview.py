"""必要に応じてWordPressのプレビューを非同期で生成し、既定ブラウザーに表示する。"""
from __future__ import annotations

import base64
import json
import sys
import threading
import uuid
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QObject, QProcess, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from app_logging import LogLevel, get_logger
from portable_runtime import app_base_dir, bundled_base_dir
from preview.static_snapshot import SnapshotCancelled, write_snapshot
from preview.wordpress_runtime import (
    PreparationCancelled,
    find_node,
    prepare_runtime,
    runtime_ready,
)

PROTOCOL_PREFIX = b"REGEXPAD_PREVIEW "


def _update_cleanup_inventory(runtime_root: Path | None = None, selected_node: Path | None = None) -> None:
    """準備したプレビュー環境を手動整理用の一覧に反映する。"""
    if getattr(sys, "frozen", False):
        from cleanup_inventory import record_inventory_safely

        record_inventory_safely(app_base_dir(), bundled_base_dir(), runtime_root=runtime_root, selected_node=selected_node)


class RuntimePreparation(QThread):
    """WordPress実行環境を準備するワーカー。"""
    progress = Signal(str)
    prepared = Signal(str)
    failed = Signal(str)

    def __init__(self, runtime_root: Path, parent: QObject, *, cached_only: bool = False) -> None:
        """実行環境の準備先と中止条件を設定する。"""
        super().__init__(parent)
        self.runtime_root = runtime_root
        self.cancel = threading.Event()
        self.cached_only = cached_only

    def run(self) -> None:
        """必要な実行環境を準備し、結果を通知する。"""
        node = None
        try:
            if self.cached_only:
                node = find_node(self.runtime_root) if runtime_ready(self.runtime_root) else None
                if node is None:
                    return  # Never download/install during automatic warm-up.
            else:
                node = prepare_runtime(self.runtime_root, self.progress.emit, self.cancel)
            if not self.cancel.is_set():
                self.prepared.emit(str(node))
        except PreparationCancelled:
            pass
        except Exception as error:  # noqa: BLE001 - report all failures at the QThread boundary.
            get_logger()(
                error,
                "WordPress preview runtime preparation failed",
                action="prepare_wordpress_preview_runtime",
                context={"runtime_root": self.runtime_root},
            )
            self.failed.emit(str(error))
        finally:
            _update_cleanup_inventory(self.runtime_root, node)


class SnapshotExport(QThread):
    """WordPressの静的プレビューを書き出すワーカー。"""
    def __init__(self, html: str, url: str, save_file_path: Path, metadata: dict[str, object], parent: QObject) -> None:
        """書き出しの入力、出力先と中止条件を設定する。"""
        super().__init__(parent)
        self.html = html
        self.url = url
        self.save_file_path = save_file_path
        self.metadata = metadata
        self.cancel = threading.Event()
        self.error = ""

    def run(self) -> None:
        """静的プレビューを書き出し、結果を通知する。"""
        try:
            write_snapshot(self.html, self.url, self.save_file_path, self.metadata, self.cancel)
        except SnapshotCancelled:
            pass
        except Exception as error:  # noqa: BLE001 - report errors across the Qt thread boundary.
            get_logger()(
                error,
                "WordPress preview snapshot export failed",
                action="export_wordpress_preview_snapshot",
                context={"save_file_path": self.save_file_path},
            )
            self.error = str(error)
        finally:
            _update_cleanup_inventory()


class WordPressPreview(QObject):
    """WordPressプレビューの起動、描画と停止を管理する。"""
    progress = Signal(str)
    rendered = Signal(str, str)
    failed = Signal(str)
    active_changed = Signal(bool)
    feedback = Signal(int, int, str)
    running_changed = Signal(bool)
    state_changed = Signal(str)

    def __init__(
        self, runtime_root: Path, bridge_path: Path, parent: QObject | None = None,
        *, mode: Literal["simple", "theme"] = "theme", output_root: Path | None = None,
    ) -> None:
        """プレビューの状態と関連するプロセスの参照を初期化する。"""
        super().__init__(parent)
        self.mode = mode
        self.output_root = (output_root or app_base_dir() / "Temp/WordPressPreview").resolve()
        self.running = False
        self.state = "stopped"
        self.last_error = ""
        self.warming_up = False
        self.exporter: SnapshotExport | None = None
        self.export_sequence = 0
        self.runtime_root = runtime_root.resolve()
        self.bridge_path = bridge_path.resolve()
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.readyReadStandardError.connect(self._read_errors)
        self.process.errorOccurred.connect(self._process_error)
        self.process.finished.connect(self._process_finished)
        self.preparation: RuntimePreparation | None = None
        self.pending: tuple[int, str, str] | None = None
        self.sequence = 0
        self.ready = False
        self.closing = False
        self.version = ""
        self.boot_cache = False
        self.origin = ""
        self.buffer = b""
        self.error_tail = ""
        self.reported_failure = False

    def show_preview(self, title: str, source_text: str) -> None:
        # Every request sends the current source to WordPress. No article HTML cache.
        """指定の原稿をプレビューする。"""
        self.closing = False
        self.warming_up = False
        self.reported_failure = False
        self.last_error = ""
        self.sequence += 1
        self.pending = (self.sequence, title, source_text)
        self.active_changed.emit(True)
        self.running = True
        self.running_changed.emit(True)
        self._ensure_started()

    def warm_up(self) -> None:
        """原稿送信やダウンロードをせず、準備済みのWordPressを起動する。"""
        if self.running:
            return
        if not runtime_ready(self.runtime_root):
            self._set_state("not_prepared")
            return
        self.closing = False
        self.reported_failure = False
        self.last_error = ""
        self.warming_up = True
        self.running = True
        self.running_changed.emit(True)
        self._ensure_started()

    def _report_progress(self, stage: str) -> None:
        """プレビューの進捗を利用者側へ通知する。"""
        self._set_state(stage if stage in {"prepare", "node", "packages", "wordpress", "download", "boot", "render", "export"} else "prepare")
        if not self.warming_up:
            self.progress.emit(stage)

    def _set_state(self, state: str) -> None:
        """プレビューの状態を更新し、変更を通知する。"""
        if self.state != state:
            self.state = state
            self.state_changed.emit(state)

    def _ensure_started(self) -> None:
        """プレビュー処理が起動している状態にする。"""
        if self.ready:
            self._send_pending()
        elif self.preparation is not None and self.preparation.isRunning() or self.process.state() != QProcess.ProcessState.NotRunning:
            return
        else:
            self._report_progress("prepare")
            preparation = RuntimePreparation(self.runtime_root, self, cached_only=self.warming_up)
            self.preparation = preparation
            preparation.progress.connect(self._report_progress)
            preparation.prepared.connect(self._start_bridge)
            preparation.failed.connect(self._fail)
            preparation.finished.connect(self._preparation_finished)
            preparation.start()

    def _preparation_finished(self) -> None:
        # Cached-only preparation may find no compatible Node. Keep it quiet and
        # let a later explicit request perform normal preparation if necessary.
        """実行環境の準備結果を受け取り、ブリッジを起動する。"""
        if self.process.state() != QProcess.ProcessState.NotRunning or self.closing:
            return
        if self.pending is not None:
            self._ensure_started()
        elif self.warming_up:
            self.running = False
            self.warming_up = False
            self.running_changed.emit(False)
            self._set_state("not_prepared")

    def _start_bridge(self, node_path: str) -> None:
        """WordPressと通信するブリッジを起動する。"""
        if self.closing:
            return
        self.buffer = b""
        self.error_tail = ""
        self._report_progress("boot")
        self.process.setWorkingDirectory(str(self.runtime_root))
        theme = "regexpad-preview" if self.mode == "simple" else "twentytwentyfive"
        self.process.start(node_path, [str(self.bridge_path), str(self.runtime_root), theme, str(self.output_root / "boot")])

    def _send_pending(self) -> None:
        """保留していた原稿をブリッジに送る。"""
        if not self.ready or self.pending is None or self.exporter is not None:
            return
        request_id, title, content = self.pending
        self.pending = None
        self._report_progress("render")
        command = {"command": "render", "id": request_id, "title": title, "content": content}
        if self.mode == "simple":
            command["snapshot"] = True
        self.process.write((json.dumps(command, ensure_ascii=False) + "\n").encode("utf-8"))

    def _read_output(self) -> None:
        """ブリッジの標準出力を読み取って通知を処理する。"""
        self.buffer += bytes(self.process.readAllStandardOutput().data())
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            if line.startswith(PROTOCOL_PREFIX):
                try:
                    message = json.loads(line[len(PROTOCOL_PREFIX):])
                    self._handle_message(message)
                except (ValueError, TypeError, AttributeError) as error:
                    get_logger().exception(
                        error,
                        "Invalid WordPress preview response",
                        level=LogLevel.WARNING,
                        action="parse_wordpress_preview_response",
                    )
                    self._fail(f"Invalid preview response: {error}")

    def _handle_message(self, message: dict[str, object]) -> None:
        """ブリッジから届いた状態や描画結果を処理する。"""
        if self.closing:
            return
        event = message.get("event")
        if event == "ready":
            origin = QUrl(str(message.get("origin", "")))
            if origin.scheme() != "http" or origin.host() != "127.0.0.1" or origin.port() <= 0:
                self._fail("Unexpected WordPress preview origin.")
                return
            self.origin = origin.toString().rstrip("/")
            self.version = str(message.get("version", ""))
            self.boot_cache = bool(message.get("bootCache", False))
            self.ready = True
            _update_cleanup_inventory(self.runtime_root)
            self._set_state("ready")
            self._send_pending()
        elif event == "rendered" and message.get("id") == self.sequence:
            url = QUrl(str(message.get("url", "")))
            if url.scheme() != "http" or url.host() != "127.0.0.1" or (
                f"http://127.0.0.1:{url.port()}" != self.origin
            ):
                self._fail("Unexpected WordPress preview URL.")
                return
            if self.mode == "simple":
                try:
                    html = base64.b64decode(str(message.get("html", "")), validate=True).decode("utf-8")
                    if not html:
                        raise ValueError("WordPress returned an empty snapshot")
                except ValueError as error:
                    get_logger().exception(
                        error,
                        "Invalid WordPress preview snapshot",
                        level=LogLevel.WARNING,
                        action="decode_wordpress_preview_snapshot",
                    )
                    self._fail(str(error))
                    return
                self._report_progress("export")
                save_file_path = self.output_root / f"snapshot-{uuid.uuid4().hex}.html"
                exporter = SnapshotExport(html, url.toString(), save_file_path, {"wordpress": self.version}, self)
                self.exporter = exporter
                self.export_sequence = self.sequence
                exporter.finished.connect(self._snapshot_finished)
                exporter.start()
                return
            if not QDesktopServices.openUrl(url):
                self._fail("The default browser could not be opened.")
                return
            self.active_changed.emit(False)
            self._set_state("ready")
            self.rendered.emit(self.version, url.toString())
        elif event == "error" and message.get("id", self.sequence) == self.sequence:
            self._fail(str(message.get("message", "WordPress preview failed.")))
        elif event == "feedback" and message.get("id") == self.sequence:
            self.feedback.emit(self.sequence, int(str(message.get("status", 0))), str(message.get("warnings", "")))
        elif event == "progress":
            self._report_progress(str(message.get("stage", "boot")))

    def _snapshot_finished(self) -> None:
        """静的プレビューの書き出し結果を処理する。"""
        exporter = self.exporter
        self.exporter = None
        if exporter is not None:
            exporter.deleteLater()
        if exporter is None or self.closing:
            return
        if self.pending is not None:
            self._send_pending()
            return
        if self.export_sequence != self.sequence:
            return
        error = exporter.error
        version = self.version
        url = QUrl.fromLocalFile(str(exporter.save_file_path))
        self.stop()  # Release PHP/WordPress before opening the standalone snapshot.
        if not error and not QDesktopServices.openUrl(url):
            error = "The default browser could not be opened."
        if error:
            self.last_error = error
            self._set_state("failed")
            self.failed.emit(error)
        else:
            self.rendered.emit(version, url.toString())

    def _read_errors(self) -> None:
        """ブリッジの標準エラー出力を読み取る。"""
        self.error_tail = (self.error_tail + bytes(self.process.readAllStandardError().data()).decode(
            "utf-8", errors="replace",
        ))[-3000:]

    def _process_error(self, error: QProcess.ProcessError) -> None:
        """ブリッジのプロセスエラーを処理する。"""
        if not self.closing and error == QProcess.ProcessError.FailedToStart:
            self._fail(self.process.errorString())

    def _process_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        """プレビュープロセスの終了を処理する。"""
        self.ready = False
        self.running = False
        self.running_changed.emit(False)
        if not self.closing:
            self._fail(self.error_tail or f"WordPress preview stopped ({exit_code}).")

    def _fail(self, message: str) -> None:
        """プレビューを失敗状態にし、理由を通知する。"""
        if self.closing or self.reported_failure:
            return
        self.reported_failure = True
        self.last_error = message
        was_warming_up = self.warming_up
        self.active_changed.emit(False)
        if self.mode == "simple":
            self.stop()
        self._set_state("failed")
        if not was_warming_up:
            self.failed.emit(message)

    def stop(self) -> None:
        """このエディターのプレビューだけを停止し、無関係なサーバーは維持する。"""
        self.closing = True
        self.warming_up = False
        self.ready = False
        self.pending = None
        if self.exporter is not None:
            self.exporter.cancel.set()
            self.exporter.wait(12000)
        if self.preparation is not None and self.preparation.isRunning():
            self.preparation.cancel.set()
            self.preparation.wait(25000)
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.write(b'{"command":"shutdown"}\n')
            self.process.closeWriteChannel()
            if not self.process.waitForFinished(3000):
                self.process.kill()
                self.process.waitForFinished(3000)
        self.active_changed.emit(False)
        self.running = False
        self.running_changed.emit(False)
        self._set_state("stopped")
