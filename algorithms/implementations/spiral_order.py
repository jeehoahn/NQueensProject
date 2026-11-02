"""Clockwise, center-out candidate order for the optional spiral solvers.

N-Queens still assigns exactly one queen per column.  To preserve complete,
non-redundant search, derive a fixed column order from the *first occurrence*
of each column in the spiral, and for that column visit candidate rows in the
order their (column, row) cells occur along the same spiral.  Invalid queen
placements are skipped by each solver's ordinary collision checks.

Coordinates use (column, row), with row increasing downward.  Even-sized
boards begin at (n//2, n//2) as the former fixed-center variants did.
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=64)
def clockwise_spiral_order(n: int) -> tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]:
    """Return (column_order, candidate_rows_by_column) without fixed queens."""
    if n < 1:
        raise ValueError("n must be positive")
    mid = n // 2
    col = row = mid
    columns: list[int] = []
    rows: list[list[int]] = [[] for _ in range(n)]
    seen_columns: set[int] = set()
    seen_cells = 0

    def visit() -> None:
        nonlocal seen_cells
        if 0 <= col < n and 0 <= row < n:
            seen_cells += 1
            if col not in seen_columns:
                columns.append(col)
                seen_columns.add(col)
            rows[col].append(row)

    visit()
    length = 1
    # Right → down → left → up, each pair of directions one step longer.
    while seen_cells < n * n:
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            for _ in range(length):
                col += dx
                row += dy
                visit()
            if (dx, dy) in ((0, 1), (0, -1)):
                length += 1
    return tuple(columns), tuple(tuple(column_rows) for column_rows in rows)
