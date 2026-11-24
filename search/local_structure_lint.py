"""Track known WordPress block pairs across small edits without reparsing later blocks."""

from __future__ import annotations

from dataclasses import dataclass

from search.html_typo_lint import BLOCK_COMMENT_PATTERN


@dataclass
class CoreBlockPair:
    """One opening comment and its original closing partner."""

    name: str
    open_start: int
    open_end: int
    close_start: int | None = None
    close_end: int | None = None
    parent_start: int | None = None
    broken: bool = False

    def contains(self, position: int) -> bool:
        return self.open_start <= position <= (self.close_end or self.open_end)


class CoreBlockIndex:
    """Retain known pairs so a damaged delimiter cannot adopt a later sibling."""

    def __init__(self, source_text: str) -> None:
        self.pairs: list[CoreBlockPair] = []
        self._read_fragment(source_text, 0)

    def _read_fragment(self, fragment: str, offset: int) -> None:
        stack: list[CoreBlockPair] = []
        for token in BLOCK_COMMENT_PATTERN.finditer(fragment):
            start, end = offset + token.start(), offset + token.end()
            name = token.group(2)
            if not token.group(1):
                if any(pair.open_start == start for pair in self.pairs):
                    continue
                pair = CoreBlockPair(
                    name, start, end,
                    parent_start=stack[-1].open_start if stack else None,
                )
                self.pairs.append(pair)
                if token.group(4):
                    pair.close_start = start
                    pair.close_end = end
                else:
                    stack.append(pair)
            elif stack and stack[-1].name == name:
                pair = stack.pop()
                pair.close_start = start
                pair.close_end = end
            elif any(pair.close_start == start for pair in self.pairs):
                continue
            elif not stack:
                candidate = next(
                    (
                        pair for pair in reversed(self.pairs)
                        if pair.name == name and pair.close_start is None
                        and pair.open_end < start
                    ),
                    None,
                )
                if candidate is not None and not any(
                    pair.open_start > candidate.open_start
                    and pair.open_start < start
                    for pair in self.pairs
                ):
                    candidate.close_start = start
                    candidate.close_end = end
                    candidate.broken = False
            elif stack:
                # Never search deeper or into following blocks for a new partner.
                stack.pop().broken = True
        for pair in stack:
            pair.broken = True

    def enclosing(self, position: int) -> CoreBlockPair | None:
        candidates = (pair for pair in self.pairs if pair.contains(position))
        return max(candidates, key=lambda pair: pair.open_start, default=None)

    def apply_change(
        self, old_start: int, old_end: int, delta: int, added_text: str,
        source_text: str, *, fragment: str = "", fragment_start: int = 0,
    ) -> list[CoreBlockPair]:
        """Shift known pairs, then recheck only touched delimiters and new fragment."""
        touched: list[CoreBlockPair] = []
        for pair in self.pairs:
            old_open_start, old_open_end = pair.open_start, pair.open_end
            old_close_start, old_close_end = pair.close_start, pair.close_end
            repairing_open = (
                pair.broken and old_start == old_end == old_open_end
                and old_open_end - old_open_start < len(f"<!-- wp:{pair.name} -->")
            )
            repairing_close = (
                pair.broken and old_close_start is not None
                and old_close_end is not None
                and old_start == old_end == old_close_end
                and old_close_end - old_close_start < len(f"<!-- /wp:{pair.name} -->")
            )
            affected = pair.contains(old_start) or (
                old_start <= pair.open_start < old_end
            )
            delimiter_touched = repairing_open or repairing_close or self._intersects(
                old_start, old_end, pair.open_start, pair.open_end
            ) or (
                pair.close_start is not None
                and pair.close_end is not None
                and self._intersects(
                    old_start, old_end, pair.close_start, pair.close_end
                )
            )
            pair.open_start = self._shift_start(pair.open_start, old_start, old_end, delta)
            pair.open_end = self._shift_end(pair.open_end, old_start, old_end, delta)
            if old_start == old_end and old_open_end > old_open_start:
                if old_start == old_open_start:
                    pair.open_start += delta
                if old_start == old_open_end and not repairing_open:
                    pair.open_end -= delta
            if pair.close_start is not None:
                pair.close_start = self._shift_start(
                    pair.close_start, old_start, old_end, delta
                )
                if pair.close_end is not None:
                    pair.close_end = self._shift_end(
                        pair.close_end, old_start, old_end, delta
                    )
                    if (
                        old_start == old_end
                        and old_close_start is not None
                        and old_close_end is not None
                        and old_close_end > old_close_start
                    ):
                        if old_start == old_close_start:
                            pair.close_start += delta
                        if old_start == old_close_end and not repairing_close:
                            pair.close_end -= delta
            if affected or delimiter_touched:
                touched.append(pair)
            if delimiter_touched:
                pair.broken = not self._pair_is_valid(pair, source_text)
        if fragment and "wp:" in fragment:
            previous_count = len(self.pairs)
            previous_state = {
                id(pair): (pair.close_start, pair.close_end, pair.broken)
                for pair in self.pairs
            }
            self._read_fragment(fragment, fragment_start)
            touched.extend(self.pairs[previous_count:])
            touched.extend(
                pair for pair in self.pairs[:previous_count]
                if previous_state[id(pair)] != (
                    pair.close_start, pair.close_end, pair.broken
                )
            )
        return touched

    @staticmethod
    def _intersects(start: int, end: int, token_start: int, token_end: int) -> bool:
        if start == end:
            return token_start < start < token_end or (
                token_start == token_end == start
            )
        return start < token_end and end > token_start

    @staticmethod
    def _shift_start(point: int, start: int, end: int, delta: int) -> int:
        if point >= end and (start != end or point > start):
            return point + delta
        if point > start:
            return start
        return point

    @staticmethod
    def _shift_end(point: int, start: int, end: int, delta: int) -> int:
        if point >= end:
            return point + delta
        if point > start:
            return start + max(delta, 0)
        return point

    @staticmethod
    def _pair_is_valid(pair: CoreBlockPair, source_text: str) -> bool:
        if pair.close_start is None or pair.close_end is None:
            return False
        opening = BLOCK_COMMENT_PATTERN.fullmatch(
            source_text[pair.open_start:pair.open_end]
        )
        if pair.close_start == pair.open_start:
            return bool(
                opening and not opening.group(1)
                and opening.group(2) == pair.name and opening.group(4)
            )
        closing = BLOCK_COMMENT_PATTERN.fullmatch(
            source_text[pair.close_start:pair.close_end]
        )
        return bool(
            opening and closing
            and not opening.group(1)
            and closing.group(1)
            and opening.group(2) == closing.group(2) == pair.name
        )
