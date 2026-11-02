from dataclasses import dataclass


@dataclass(frozen=True)
class Solution:
    """A completed N-Queens arrangement.

    positions[column] gives the row containing the queen in that column.
    """

    positions: tuple[int, ...]

    def __post_init__(self):
        n = len(self.positions)
        if n == 0:
            raise ValueError("A solution cannot have an empty board.")
        if any(not 0 <= row < n for row in self.positions):
            raise ValueError("A queen position is outside the board.")
        if len(set(self.positions)) != n:
            raise ValueError("Two queens cannot share a row.")
        if len({col - row for col, row in enumerate(self.positions)}) != n:
            raise ValueError("Two queens cannot share one diagonal.")
        if len({col + row for col, row in enumerate(self.positions)}) != n:
            raise ValueError("Two queens cannot share one diagonal.")

    @property
    def size(self) -> int:
        return len(self.positions)
