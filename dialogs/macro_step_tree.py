"""Flat step drag/drop: request model reordering without mutating Qt items."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget


class MacroStepTree(QTreeWidget):
    step_reorder_requested = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.source() is self:
            super().dragEnterEvent(event)
        else:
            event.ignore()

    def startDrag(self, supportedActions: Qt.DropAction) -> None:
        selected = self.currentItem()
        if selected is None or selected.parent() is None:
            return
        drag = QDrag(self)
        drag.setMimeData(self.mimeData([selected]))
        drag.exec(Qt.DropAction.MoveAction)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.source() is self:
            super().dragMoveEvent(event)
        else:
            event.ignore()

    def request_reorder(self, source: int, insertion: int) -> bool:
        root = self.topLevelItem(0)
        count = root.childCount() if root is not None else 0
        if not 0 <= source < count or not 0 <= insertion <= count:
            return False
        destination = insertion - (1 if insertion > source else 0)
        if destination == source:
            return False
        self.step_reorder_requested.emit(source, destination)
        return True

    def dropEvent(self, event: QDropEvent) -> None:
        selected = self.currentItem()
        root = self.topLevelItem(0)
        if (
            event.source() is not self
            or root is None
            or selected is None
            or selected.parent() is not root
        ):
            event.ignore()
            return
        source = root.indexOfChild(selected)
        target = self.itemAt(event.position().toPoint())
        if target is None:
            insertion = root.childCount()
        elif target is root:
            insertion = 0
        elif target.parent() is root:
            insertion = root.indexOfChild(target)
            if event.position().y() >= self.visualItemRect(target).center().y():
                insertion += 1
        else:
            event.ignore()
            return
        # Our startDrag does not remove Qt items after the model is rebuilt.
        self.request_reorder(source, insertion)
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
