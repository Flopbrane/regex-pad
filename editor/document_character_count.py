"""Count Python characters from changed QTextBlocks without rereading a document."""

from PySide6.QtGui import QTextDocument


class DocumentCharacterCount:
    """Track text length across Qt UTF-16 edits, including astral characters."""

    def __init__(self, document: QTextDocument) -> None:
        self.document = document
        self.text_lengths: list[int] = []
        self.text_total = 0
        block = document.firstBlock()
        while block.isValid():
            length = len(block.text())
            self.text_lengths.append(length)
            self.text_total += length
            block = block.next()

    @property
    def count(self) -> int:
        """Return the length of QTextDocument.toPlainText() in Python characters."""
        return self.text_total + max(len(self.text_lengths) - 1, 0)

    def apply_change(self, position: int, removed: int, added: int) -> None:
        """Recount only the blocks touched by one contentsChange signal."""
        first_block = self.document.findBlock(position)
        last_block = self.document.findBlock(position + added)
        if not last_block.isValid():
            last_block = self.document.lastBlock()

        first_index = first_block.blockNumber()
        new_lengths: list[int] = []
        block = first_block
        while block.isValid():
            new_lengths.append(len(block.text()))
            if block == last_block:
                break
            block = block.next()

        old_block_count = len(self.text_lengths)
        changed_old_blocks = len(new_lengths) - (self.document.blockCount() - old_block_count)
        old_lengths = self.text_lengths[first_index:first_index + changed_old_blocks]
        self.text_total += sum(new_lengths) - sum(old_lengths)
        self.text_lengths[first_index:first_index + changed_old_blocks] = new_lengths
