"""候補を個別に選び、変更前後を確認するダイアログ。"""

from __future__ import annotations

from PySide6.QtCore import Qt
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
        self.candidates = candidates
        self.translator = translator
        self.setWindowTitle(translator.text("core_repair.title"))
        self.resize(820, 480)
        layout = QVBoxLayout(self)
        target_label = QLabel(target, self)
        target_label.setTextFormat(Qt.TextFormat.PlainText)
        target_label.setWordWrap(True)
        layout.addWidget(target_label)
        message = QLabel(translator.text("core_repair.instructions" if candidates else "core_repair.empty"), self)
        message.setWordWrap(True)
        layout.addWidget(message)

        self.list = QListWidget(self)
        for candidate in candidates:
            item = QListWidgetItem(translator.text(
                "core_repair.row", line=candidate.line, block=candidate.block,
                changes=" / ".join(candidate.details),
            ))
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list.addItem(item)
        layout.addWidget(self.list, 1)
        self.reason = QLabel(self)
        self.reason.setWordWrap(True)
        layout.addWidget(self.reason)

        split = QSplitter(Qt.Orientation.Horizontal, self)
        self.before = self._preview_panel(split, translator.text("core_repair.before"))
        self.after = self._preview_panel(split, translator.text("core_repair.after"))
        layout.addWidget(split, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel, self,
        )
        self.apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.apply_button.setText(translator.text("core_repair.apply"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(translator.text("core_repair.cancel"))
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.list.itemChanged.connect(self._update_apply)
        self.list.currentRowChanged.connect(self._show_candidate)
        if candidates:
            self.list.setCurrentRow(0)

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
        self.apply_button.setEnabled(bool(self.selected_repairs()))

    def _show_candidate(self, row: int) -> None:
        """指定候補の根拠と変更前後の文字列を表示する。"""
        candidate = self.candidates[row] if 0 <= row < len(self.candidates) else None
        self.reason.setText(self.translator.text(f"core_repair.reason.{candidate.reason}") if candidate else "")
        self.before.setPlainText((candidate.preview_before or candidate.before) if candidate else "")
        self.after.setPlainText((candidate.preview_after or candidate.after) if candidate else "")
