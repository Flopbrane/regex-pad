"""Review and edit application shortcuts while keeping standard keys fixed."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QKeySequenceEdit,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from localization.translator import Translator
from settings.shortcut_settings import ShortcutSettings, TextShortcut

WINDOWS_SHORTCUTS = (
    ("Meta+E", "shortcut.os.explorer"),
    ("Meta+D", "shortcut.os.desktop"),
    ("Meta+L", "shortcut.os.lock"),
    ("Meta+R", "shortcut.os.run"),
    ("Alt+Tab", "shortcut.os.switch"),
    ("Ctrl+Shift+Esc", "shortcut.os.task_manager"),
    ("Ctrl+C", "shortcut.os.copy"),
    ("Ctrl+X", "shortcut.os.cut"),
    ("Ctrl+V", "shortcut.os.paste"),
    ("Ctrl+Z", "shortcut.os.undo"),
    ("Ctrl+Y", "shortcut.os.redo"),
    ("Ctrl+A", "shortcut.os.select_all"),
    ("Alt+F4", "shortcut.os.close_window"),
)

LOCKED_TEXT_COLOR = QColor("#4C3163")
LOCKED_BACKGROUND_COLOR = QColor("#DEDEDE")


def canonical_shortcut(value: str) -> str:
    """Normalize a single Qt shortcut so collisions use one spelling."""
    sequence = QKeySequence(value)
    return sequence.toString(QKeySequence.SequenceFormat.PortableText) or ""


@dataclass(frozen=True, slots=True)
class ShortcutActionInfo:
    """One existing app action and its original key assignments."""

    action: QAction
    defaults: tuple[str, ...]
    locked: bool = False


def shortcut_problem(
    key: str, current: tuple[str, str] | None,
    actions: dict[str, ShortcutActionInfo], settings: ShortcutSettings,
) -> str | None:
    """Return the message key for an invalid or already assigned shortcut."""
    sequence = QKeySequence(key)
    if not key or sequence.count() != 1:
        return "shortcut.invalid_key"
    normalized = canonical_shortcut(key)
    occupied = {canonical_shortcut(item[0]) for item in WINDOWS_SHORTCUTS}
    for identifier, info in actions.items():
        if current != ("app", identifier):
            occupied.add(canonical_shortcut(settings.overrides.get(identifier, info.defaults[0])))
        occupied.update(canonical_shortcut(value) for value in info.defaults[1:])
    occupied.update(
        canonical_shortcut(item.shortcut) for item in settings.snippets
        if current != ("snippet", item.identifier)
    )
    if normalized in occupied or normalized.startswith("Meta+"):
        return "shortcut.conflict"
    return None


def validate_shortcut_settings(
    settings: ShortcutSettings, actions: dict[str, ShortcutActionInfo]
) -> str | None:
    """Reject invalid manual JSON edits before any shortcut is activated."""
    for identifier, key in settings.overrides.items():
        if identifier not in actions or actions[identifier].locked:
            return "shortcut.invalid_config"
        if problem := shortcut_problem(key, ("app", identifier), actions, settings):
            return problem
    for snippet in settings.snippets:
        if problem := shortcut_problem(
            snippet.shortcut, ("snippet", snippet.identifier), actions, settings
        ):
            return problem
    return None


class ShortcutEditorDialog(QDialog):
    """Edit one key and, for custom entries, its name and inserted text."""

    def __init__(
        self, translator: Translator, name: str, shortcut: str,
        text: str | None, parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self.translator = translator
        self.setWindowTitle(translator.text("shortcut.edit_title"))
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(name)
        self.name_edit.setReadOnly(text is None)
        form.addRow(translator.text("shortcut.name"), self.name_edit)
        self.key_edit = QKeySequenceEdit(QKeySequence(shortcut))
        form.addRow(translator.text("shortcut.key"), self.key_edit)
        self.text_edit: QPlainTextEdit | None = None
        if text is not None:
            self.text_edit = QPlainTextEdit(text)
            form.addRow(translator.text("shortcut.insert_text"), self.text_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def shortcut(self) -> str:
        return self.key_edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText) or ""


class ShortcutSettingsDialog(QDialog):
    """Draft shortcut changes and validate all conflicts before accepting."""

    def __init__(
        self, translator: Translator, actions: dict[str, ShortcutActionInfo],
        settings: ShortcutSettings, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.translator = translator
        self.action_info = actions
        self.settings = ShortcutSettings(dict(settings.overrides), list(settings.snippets))
        self.setWindowTitle(translator.text("shortcut.title"))
        self.resize(760, 540)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(translator.text("shortcut.explanation")))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            translator.text("shortcut.category"), translator.text("shortcut.name"),
            translator.text("shortcut.key"), translator.text("shortcut.status"),
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setColumnWidth(0, 120)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(2, 170)
        self.table.setColumnWidth(3, 100)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        self.add_button = QPushButton(translator.text("shortcut.add"))
        self.edit_button = QPushButton(translator.text("shortcut.edit"))
        self.delete_button = QPushButton(translator.text("shortcut.delete"))
        self.add_button.clicked.connect(self.add_snippet)
        self.edit_button.clicked.connect(self.edit_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        for button in (self.add_button, self.edit_button, self.delete_button):
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._render()

    def _render(self) -> None:
        self.table.setRowCount(0)
        for identifier, info in self.action_info.items():
            keys = (self.settings.overrides.get(identifier, info.defaults[0]), *info.defaults[1:])
            self._add_row(
                "app", identifier, info.action.text().replace("&", ""),
                ", ".join(keys), info.locked,
            )
        for key, label_key in WINDOWS_SHORTCUTS:
            display_key = key.replace("Meta+", "Win+")
            self._add_row("windows", key, self.translator.text(label_key), display_key, True)
        for snippet in self.settings.snippets:
            self._add_row("snippet", snippet.identifier, snippet.name, snippet.shortcut, False)
        self._update_buttons()

    def _add_row(
        self, kind: str, identifier: str, name: str, shortcut: str, locked: bool
    ) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        category = "fixed_app" if locked and kind == "app" else (
            "standard" if locked else kind
        )
        labels = (
            self.translator.text("shortcut.category_" + category), name, shortcut,
            self.translator.text("shortcut.locked" if locked else "shortcut.editable"),
        )
        for column, value in enumerate(labels):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if locked:
                item.setForeground(LOCKED_TEXT_COLOR)
                item.setBackground(LOCKED_BACKGROUND_COLOR)
            if column == 0:
                item.setData(Qt.ItemDataRole.UserRole, (kind, identifier))
            self.table.setItem(row, column, item)

    def _selected(self) -> tuple[str, str] | None:
        item = self.table.item(self.table.currentRow(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _update_buttons(self) -> None:
        selected = self._selected()
        editable = selected is not None and (
            selected[0] == "snippet" or
            (selected[0] == "app" and not self.action_info[selected[1]].locked)
        )
        self.edit_button.setEnabled(editable)
        self.delete_button.setEnabled(selected is not None and selected[0] == "snippet")

    def add_snippet(self) -> None:
        editor = ShortcutEditorDialog(self.translator, "", "", "", self)
        if editor.exec() != QDialog.DialogCode.Accepted:
            return
        name = editor.name_edit.text().strip()
        key = editor.shortcut()
        if not name:
            self._warning("shortcut.name_required")
            return
        assert editor.text_edit is not None
        if not editor.text_edit.toPlainText():
            self._warning("shortcut.text_required")
            return
        if not self._check_key(key):
            return
        self.settings.snippets.append(TextShortcut(uuid4().hex, name, key, editor.text_edit.toPlainText()))
        self._render()

    def edit_selected(self) -> None:
        selected = self._selected()
        if selected is None:
            return
        kind, identifier = selected
        if kind == "app":
            info = self.action_info[identifier]
            if info.locked:
                return
            key = self.settings.overrides.get(identifier, info.defaults[0])
            editor = ShortcutEditorDialog(self.translator, info.action.text(), key, None, self)
            if editor.exec() != QDialog.DialogCode.Accepted:
                return
            new_key = editor.shortcut()
            if not self._check_key(new_key, selected):
                return
            if new_key == info.defaults[0]:
                self.settings.overrides.pop(identifier, None)
            else:
                self.settings.overrides[identifier] = new_key
        elif kind == "snippet":
            index = next(i for i, item in enumerate(self.settings.snippets) if item.identifier == identifier)
            item = self.settings.snippets[index]
            editor = ShortcutEditorDialog(self.translator, item.name, item.shortcut, item.text, self)
            if editor.exec() != QDialog.DialogCode.Accepted:
                return
            name = editor.name_edit.text().strip()
            new_key = editor.shortcut()
            if not name:
                self._warning("shortcut.name_required")
                return
            assert editor.text_edit is not None
            if not editor.text_edit.toPlainText():
                self._warning("shortcut.text_required")
                return
            if not self._check_key(new_key, selected):
                return
            self.settings.snippets[index] = TextShortcut(identifier, name, new_key, editor.text_edit.toPlainText())
        self._render()

    def delete_selected(self) -> None:
        selected = self._selected()
        if selected is None or selected[0] != "snippet":
            return
        self.settings.snippets = [
            item for item in self.settings.snippets if item.identifier != selected[1]
        ]
        self._render()

    def _check_key(self, key: str, current: tuple[str, str] | None = None) -> bool:
        if problem := shortcut_problem(key, current, self.action_info, self.settings):
            self._warning(problem)
            return False
        return True

    def _warning(self, key: str) -> None:
        QMessageBox.warning(self, self.translator.text("shortcut.title"), self.translator.text(key))

    def accept(self) -> None:
        """Commit the draft only when every editable key remains unique."""
        for identifier, key in self.settings.overrides.items():
            if identifier in self.action_info and not self._check_key(key, ("app", identifier)):
                return
        for snippet in self.settings.snippets:
            if not self._check_key(snippet.shortcut, ("snippet", snippet.identifier)):
                return
        super().accept()
