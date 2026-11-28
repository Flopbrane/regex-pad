"""候補を個別に選び、変更前後を確認するダイアログ。"""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from localization.translator import Translator
from search.core_block_repair import RepairCandidate


class CoreBlockRepairDialog(QDialog):
    """コアブロックの修復候補を選び、変更前後を比較する画面。"""
    def __init__(
        self, candidates: list[RepairCandidate], target: str, translator: Translator, parent: QWidget,
    ) -> None:
        """候補一覧、比較欄と確定ボタンを組み立てる。"""
        super().__init__(parent)
        self.candidates: list[RepairCandidate] = []
        self.fresh = False
        self.translator = translator
        self.setWindowTitle(translator.text("core_repair.title"))
        self.resize(820, 480)
        layout = QVBoxLayout(self)
        target_label = QLabel(target, self)
        target_label.setTextFormat(Qt.TextFormat.PlainText)
        target_label.setWordWrap(True)
        layout.addWidget(target_label)
        self.message = QLabel(self)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        self.list = QListWidget(self)
        layout.addWidget(self.list, 1)
        self.reason = QLabel(self)
        self.reason.setWordWrap(True)
        layout.addWidget(self.reason)

        split = QSplitter(Qt.Orientation.Horizontal, self)
        self.before = self._preview_panel(split, translator.text("core_repair.before"))
        self.after = self._preview_panel(split, translator.text("core_repair.after"))
        layout.addWidget(split, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close, self,
        )
        self.apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.refresh_button = buttons.addButton(
            translator.text("core_repair.refresh"), QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.apply_button.setText(translator.text("core_repair.apply"))
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(translator.text("core_repair.close"))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.list.itemChanged.connect(self._update_apply)
        self.list.currentRowChanged.connect(self._show_candidate)
        self.set_candidates(candidates)

    def set_candidates(self, candidates: list[RepairCandidate], applied: bool = False) -> None:
        """最新の候補を未選択で表示する。"""
        self.candidates = candidates
        self.fresh = True
        with QSignalBlocker(self.list):
            self.list.clear()
            for candidate in candidates:
                item = QListWidgetItem(self.translator.text(
                    "core_repair.row", line=candidate.line, block=candidate.block,
                    changes=" / ".join(candidate.details),
                ))
                item.setCheckState(Qt.CheckState.Unchecked)
                self.list.addItem(item)
            self.list.setCurrentRow(0 if candidates else -1)
        status = self.translator.text("core_repair.instructions" if candidates else "core_repair.empty")
        self.message.setText(self.translator.text("core_repair.applied", status=status) if applied else status)
        self.list.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self._show_candidate(self.list.currentRow())
        self._update_apply()

    def invalidate(self, available: bool) -> None:
        """古い候補の選択と適用を停止し、再チェックの可否を反映する。"""
        if not self.fresh and self.refresh_button.isEnabled() == available:
            return
        self.fresh = False
        self.list.setEnabled(False)
        self.refresh_button.setEnabled(available)
        self.message.setText(self.translator.text(
            "core_repair.stale" if available else "core_repair.target_unavailable",
        ))
        self._show_candidate(-1)
        self._update_apply()

    @staticmethod
    def _preview_panel(split: QSplitter, label: str) -> QPlainTextEdit:
        """ラベル付きの読み取り専用プレビュー欄を作る。"""
        panel = QWidget(split)
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel(label, panel))
        preview = QPlainTextEdit(panel)
        preview.setReadOnly(True)
        layout.addWidget(preview)
        split.addWidget(panel)
        return preview

    def selected_repairs(self) -> list[RepairCandidate]:
        """チェックされた修復候補を返す。"""
        return [
            candidate for row, candidate in enumerate(self.candidates)
            if self.list.item(row).checkState() == Qt.CheckState.Checked
        ]

    def _update_apply(self) -> None:
        """候補が選択されている場合だけ適用ボタンを有効にする。"""
        self.apply_button.setEnabled(self.fresh and bool(self.selected_repairs()))

    def _show_candidate(self, row: int) -> None:
        """指定候補の根拠と変更前後の文字列を表示する。"""
        candidate = self.candidates[row] if 0 <= row < len(self.candidates) else None
        self.reason.setText(self.translator.text(f"core_repair.reason.{candidate.reason}") if candidate else "")
        self.before.setPlainText((candidate.preview_before or candidate.before) if candidate else "")
        self.after.setPlainText((candidate.preview_after or candidate.after) if candidate else "")
