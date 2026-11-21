"""Document-level Undo/Redo for macro definitions, independent of article Undo."""

from collections.abc import Callable
from copy import deepcopy
from time import monotonic

from PySide6.QtGui import QUndoCommand, QUndoStack

from macro.editor_data_model import MacroEditorDocumentData


class MacroDocumentChange(QUndoCommand):
    def __init__(
        self,
        before: MacroEditorDocumentData,
        after: MacroEditorDocumentData,
        before_selection: int,
        after_selection: int,
        restore: Callable[[MacroEditorDocumentData, int], None],
        merge_key: str | None,
        generation: int,
    ) -> None:
        super().__init__()
        self.before = deepcopy(before)
        self.after = deepcopy(after)
        self.before_selection = before_selection
        self.after_selection = after_selection
        self.restore = restore
        self.merge_key = merge_key
        self.generation = generation
        self.timestamp = monotonic()
        self._first_redo = True

    def id(self) -> int:
        return 1 if self.merge_key is not None else -1

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, MacroDocumentChange):
            return False
        if (
            self.merge_key != other.merge_key
            or self.generation != other.generation
            or other.timestamp - self.timestamp > 0.75
            or self.after != other.before
        ):
            return False
        self.after = deepcopy(other.after)
        self.after_selection = other.after_selection
        self.timestamp = other.timestamp
        return True

    def undo(self) -> None:
        self.restore(deepcopy(self.before), self.before_selection)

    def redo(self) -> None:
        # The initial push records an already-visible user edit.
        if self._first_redo:
            self._first_redo = False
            return
        self.restore(deepcopy(self.after), self.after_selection)


class MacroEditorHistory:
    def __init__(
        self, stack: QUndoStack, restore: Callable[[MacroEditorDocumentData, int], None]
    ) -> None:
        self.stack = stack
        self.restore = restore
        self.generation = 0

    def break_merge(self) -> None:
        self.generation += 1

    def record(
        self,
        before: MacroEditorDocumentData,
        after: MacroEditorDocumentData,
        before_selection: int,
        after_selection: int,
        merge_key: str | None = None,
    ) -> None:
        if before == after:
            return
        if merge_key is None:
            self.break_merge()
        self.stack.push(
            MacroDocumentChange(
                before,
                after,
                before_selection,
                after_selection,
                self.restore,
                merge_key,
                self.generation,
            )
        )
