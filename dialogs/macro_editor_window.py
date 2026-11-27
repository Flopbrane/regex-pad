"""構造化した疑似マクロを編集する独立したモードレスウインドウを提供する。"""

from collections.abc import Callable
from html import escape

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QCloseEvent,
    QColor,
    QContextMenuEvent,
    QKeyEvent,
    QKeySequence,
)
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
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dialogs.macro_diagnostic_table import MacroDiagnosticTable
from dialogs.macro_step_editor_widget import MacroStepEditorWidget
from dialogs.macro_step_tree import MacroStepTree
from dialogs.regex_input_edit import RegexInputEdit
from localization.translator import Translator
from macro.editor_session import MacroEditorSession


class MacroEditorWindow(QMainWindow):
    """定義と複数の手順を編集する独立ウインドウ。"""
    new_requested = Signal()
    open_requested = Signal()
    save_requested = Signal()
    save_as_requested = Signal()
    validate_requested = Signal()
    preview_requested = Signal()
    run_requested = Signal()
    folder_requested = Signal()
    dictionary_requested = Signal()
    step_add_requested = Signal()
    step_duplicate_requested = Signal(int)
    step_delete_requested = Signal(int)
    step_move_requested = Signal(int, int)
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        """手順ツリー、フォーム、診断表と操作メニューを用意する。"""
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
        self.edit_menu = self.menuBar().addMenu(translator.text("menu.edit"))
        self.undo_action = QAction(translator.text("action.undo"), self)
        self.redo_action = QAction(translator.text("action.redo"), self)
        self.undo_action.setShortcuts(QKeySequence.StandardKey.Undo)
        self.redo_action.setShortcuts(QKeySequence.StandardKey.Redo)
        self.undo_action.triggered.connect(self.undo_requested.emit)
        self.redo_action.triggered.connect(self.redo_requested.emit)
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)
        self.edit_menu.addActions([self.undo_action, self.redo_action])
        toolbar.addActions([self.undo_action, self.redo_action])
        toolbar.addSeparator()
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
        dictionary_action = QAction(translator.text("dictionary.editor.open"), self)
        dictionary_action.triggered.connect(self.dictionary_requested.emit)
        toolbar.addSeparator()
        toolbar.addAction(dictionary_action)
        file_menu.addAction(dictionary_action)
        self.dictionary_action = dictionary_action
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
        self.version.addItem("2", 2)
        self.version.addItem("3", 3)
        self.version.setEnabled(False)
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
        self.tree = MacroStepTree()
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
        for widget in (
            self.macro_name,
            self.description,
            *self.step_editor.fields.values(),
        ):
            if isinstance(widget, (QLineEdit, RegexInputEdit)):
                widget.installEventFilter(self)
                if isinstance(widget, RegexInputEdit):
                    widget.viewport().installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """ウインドウ内の入力イベントを振り分ける。"""
        if isinstance(event, QKeyEvent) and event.type() in (
            QEvent.Type.ShortcutOverride,
            QEvent.Type.KeyPress,
        ):
            undo = event.matches(QKeySequence.StandardKey.Undo)
            redo = event.matches(QKeySequence.StandardKey.Redo)
            if undo or redo:
                event.accept()
                if event.type() == QEvent.Type.KeyPress:
                    (self.undo_action if undo else self.redo_action).trigger()
                return True
        if isinstance(event, QContextMenuEvent):
            widget = (
                watched.parent()
                if isinstance(watched, QWidget)
                and not isinstance(watched, (QLineEdit, RegexInputEdit))
                else watched
            )
            if isinstance(widget, (QLineEdit, RegexInputEdit)):
                menu = widget.createStandardContextMenu()
                for action in menu.actions()[:2]:
                    menu.removeAction(action)
                anchor = menu.actions()[0] if menu.actions() else None
                if anchor is not None:
                    menu.insertAction(anchor, self.undo_action)
                    menu.insertAction(anchor, self.redo_action)
                else:
                    menu.addActions([self.undo_action, self.redo_action])
                menu.exec(event.globalPos())
                menu.deleteLater()
                return True
        return super().eventFilter(watched, event)

    def retranslate_ui(self) -> None:
        """現在の言語で画面の各項目を更新する。"""
        text = self.translator.text
        self.file_menu.setTitle(text("menu.file"))
        self.edit_menu.setTitle(text("menu.edit"))
        self.undo_action.setText(text("action.undo"))
        self.redo_action.setText(text("action.redo"))
        self.toolbar.setWindowTitle(text("macro.editor.title"))
        for name, action in self.editor_actions.items():
            action.setText(text("macro.editor." + name))
        self.dictionary_action.setText(text("dictionary.editor.open"))
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
        """ツリーで選択中の手順の位置を返す。"""
        item = self.tree.currentItem()
        parent = item.parent() if item is not None else None
        if item is None or parent is None:
            return -1
        return parent.indexOfChild(item)

    def render_tree(self, session: MacroEditorSession, selected: int) -> None:
        """マクロ定義から手順ツリーを描き直す。"""
        self.tree.blockSignals(True)
        self.tree.clear()
        root = QTreeWidgetItem(
            [f'<macro name="{escape(session.document.macro_name, quote=True)}">']
        )
        self.tree.addTopLevelItem(root)
        root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
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
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
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
        """手順数や診断件数をステータス表示に反映する。"""
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
        """未保存状態を確認し、許可された場合に閉じる。"""
        if self.confirm_close():
            event.accept()
        else:
            event.ignore()
