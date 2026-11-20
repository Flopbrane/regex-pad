"""Independent modeless window for structured pseudo-macro editing."""

from collections.abc import Callable
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QBrush, QCloseEvent, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dialogs.macro_diagnostic_table import MacroDiagnosticTable
from dialogs.macro_step_editor_widget import MacroStepEditorWidget
from localization.translator import Translator
from macro.editor_session import MacroEditorSession


class MacroEditorWindow(QMainWindow):
    new_requested = Signal()
    open_requested = Signal()
    save_requested = Signal()
    save_as_requested = Signal()
    validate_requested = Signal()
    preview_requested = Signal()
    run_requested = Signal()
    folder_requested = Signal()
    step_add_requested = Signal()
    step_duplicate_requested = Signal(int)
    step_delete_requested = Signal(int)
    step_move_requested = Signal(int, int)

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.translator = translator
        self.confirm_close: Callable[[], bool] = lambda: True
        self.resize(1050, 760)
        self.setMinimumSize(640, 480)
        self.editor_actions: dict[str, QAction] = {}
        toolbar = self.addToolBar(translator.text("macro.editor.title"))
        file_menu = self.menuBar().addMenu(translator.text("menu.file"))
        self.file_menu = file_menu
        self.toolbar = toolbar
        for name, signal, shortcut in (
            ("new", self.new_requested, "Ctrl+N"),
            ("open", self.open_requested, "Ctrl+O"),
            ("save", self.save_requested, "Ctrl+S"),
            ("save_as", self.save_as_requested, "Ctrl+Shift+S"),
            ("validate", self.validate_requested, "F5"),
            ("preview", self.preview_requested, ""),
            ("run", self.run_requested, ""),
        ):
            action = QAction(translator.text("macro.editor." + name), self)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(signal.emit)
            toolbar.addAction(action)
            file_menu.addAction(action)
            self.editor_actions[name] = action
        close_action = toolbar.addAction(translator.text("macro.editor.close"))
        close_action.triggered.connect(self.close)
        self.close_action = close_action
        file_menu.addAction(close_action)
        central = QWidget()
        layout = QVBoxLayout(central)
        self.path_label = QLabel()
        self.path_label.setTextFormat(Qt.TextFormat.PlainText)
        self.path_label.setWordWrap(True)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path_label, 1)
        folder_button = QPushButton(translator.text("macro.editor.folder"))
        folder_button.clicked.connect(self.folder_requested.emit)
        self.folder_button = folder_button
        path_row.addWidget(folder_button)
        layout.addLayout(path_row)
        self.version = QComboBox()
        self.version.setEditable(False)
        self.version.addItem("1", 1)
        self.macro_name = QLineEdit()
        self.description = QLineEdit()
        form = QFormLayout()
        self.metadata_form = form
        for name, widget in (
            ("format_version", self.version),
            ("macro_name", self.macro_name),
            ("description", self.description),
        ):
            form.addRow(translator.text("macro.editor." + name), widget)
        layout.addLayout(form)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel(translator.text("macro.editor.outline"))
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.tree)
        buttons = QHBoxLayout()
        move_buttons = QHBoxLayout()
        self.step_buttons: dict[str, QPushButton] = {}
        for name in ("add", "duplicate", "delete", "up", "down"):
            button = QPushButton(translator.text("macro.editor." + name))
            self.step_buttons[name] = button
            (move_buttons if name in {"up", "down"} else buttons).addWidget(button)
        self.step_buttons["add"].clicked.connect(self.step_add_requested.emit)
        self.step_buttons["duplicate"].clicked.connect(
            lambda: self.step_duplicate_requested.emit(self.selected_step())
        )
        self.step_buttons["delete"].clicked.connect(
            lambda: self.step_delete_requested.emit(self.selected_step())
        )
        self.step_buttons["up"].clicked.connect(
            lambda: self.step_move_requested.emit(self.selected_step(), -1)
        )
        self.step_buttons["down"].clicked.connect(
            lambda: self.step_move_requested.emit(self.selected_step(), 1)
        )
        left_layout.addLayout(buttons)
        left_layout.addLayout(move_buttons)
        self.step_editor = MacroStepEditorWidget(translator)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.step_editor)
        self.splitter = QSplitter()
        self.splitter.addWidget(left)
        self.splitter.addWidget(scroll)
        self.splitter.setSizes([310, 710])
        self.diagnostics = MacroDiagnosticTable(translator)
        self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.vertical_splitter.addWidget(self.splitter)
        self.vertical_splitter.addWidget(self.diagnostics)
        self.vertical_splitter.setSizes([440, 150])
        layout.addWidget(self.vertical_splitter, 1)
        self.setCentralWidget(central)

    def retranslate_ui(self) -> None:
        text = self.translator.text
        self.file_menu.setTitle(text("menu.file"))
        self.toolbar.setWindowTitle(text("macro.editor.title"))
        for name, action in self.editor_actions.items():
            action.setText(text("macro.editor." + name))
        self.close_action.setText(text("macro.editor.close"))
        self.folder_button.setText(text("macro.editor.folder"))
        self.tree.setHeaderLabel(text("macro.editor.outline"))
        for name, button in self.step_buttons.items():
            button.setText(text("macro.editor." + name))
        for name, widget in (
            ("format_version", self.version),
            ("macro_name", self.macro_name),
            ("description", self.description),
        ):
            label = self.metadata_form.labelForField(widget)
            if isinstance(label, QLabel):
                label.setText(text("macro.editor." + name))
        self.step_editor.retranslate_ui()
        self.diagnostics.setHorizontalHeaderLabels(
            [
                text("macro.editor." + name)
                for name in ("severity", "step", "field", "message")
            ]
        )

    def selected_step(self) -> int:
        item = self.tree.currentItem()
        parent = item.parent() if item is not None else None
        if item is None or parent is None:
            return -1
        return parent.indexOfChild(item)

    def render_tree(self, session: MacroEditorSession, selected: int) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        root = QTreeWidgetItem(
            [f'<macro name="{escape(session.document.macro_name, quote=True)}">']
        )
        self.tree.addTopLevelItem(root)
        for index, step in enumerate(session.document.steps):
            item = QTreeWidgetItem(
                [
                    (
                        f'<step name="{escape(step.step_name, quote=True)}" '
                        f'enabled="{str(step.enabled).lower()}" />'
                    )
                ]
            )
            root.addChild(item)
            item.setToolTip(0, item.text(0))
            findings = [
                d
                for d in session.validation_result.diagnostics
                if d.step_index == index
            ]
            if findings:
                color = (
                    "#c62828"
                    if any(d.severity.value == "error" for d in findings)
                    else "#9a6700"
                )
                item.setForeground(0, QBrush(QColor(color)))
        root.setExpanded(True)
        selected_item = (
            root.child(selected) if 0 <= selected < root.childCount() else root
        )
        if selected_item is not None:
            self.tree.setCurrentItem(selected_item)
        self.tree.blockSignals(False)
        self.update_status(session)

    def update_status(self, session: MacroEditorSession) -> None:
        destination = str(session.save_file_path or session.macro_folder)
        self.path_label.setText(destination)
        self.setWindowTitle(
            self.translator.text("macro.editor.title")
            + " — "
            + (
                session.save_file_path.name
                if session.save_file_path
                else self.translator.text("macro.editor.new")
            )
            + (" *" if session.modified else "")
        )
        self.statusBar().showMessage(
            self.translator.text(
                "macro.editor.status",
                count=len(session.document.steps),
                errors=len(session.validation_result.errors),
                warnings=len(session.validation_result.warnings),
            )
        )
        self.editor_actions["save"].setEnabled(session.validation_result.is_valid)
        self.editor_actions["save_as"].setEnabled(session.validation_result.is_valid)
        self.editor_actions["run"].setEnabled(session.validation_result.is_valid)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.confirm_close():
            event.accept()
        else:
            event.ignore()
