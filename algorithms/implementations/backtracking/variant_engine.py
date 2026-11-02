"""Iterative N-Queens DFS shared by the opt-in experimental variants.

positions[column] = row, -1 when unoccupied. A 'node' is one tested
candidate row (or a valid bit candidate when bit pruning is enabled).
Symmetry-pruned mirrored solutions are materialized but never counted as
explored nodes. Optional spiral variants start at the central *candidate*
without fixing any queen there.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from algorithms.base import BaseAlgorithm
from algorithms.implementations.spiral_order import clockwise_spiral_order
from core.solution import Solution


def horizontal_reflection(positions: tuple[int, ...]) -> tuple[int, ...]:
    """Reflect rows around horizontal board axis."""
    n = len(positions)
    return tuple(n - 1 - r for r in positions)


@dataclass
class _Frame:
    column: int
    limit: int  # maximum row for plain scanning (exclusive)
    next_row: int = 0
    remaining_bits: int | None = None  # populated only after bitmask optimization activates
    ordered_rows: tuple[int, ...] | None = None


class ConfiguredStackDFS(BaseAlgorithm):
    """Extend via class-level flags, never duplicate solver bookkeeping."""

    centered = False  # compatibility with estimators; no fixed-center solvers remain
    spiral_order = False
    bit_optimized = False
    remove_symmetry = False

    def __init__(self, n: int):
        super().__init__(n)
        self.solution_scope = "all"
        self.fixed_queen = None
        self.positions = [-1] * n
        # Plain stack variants use sets; optimized variants use bitmasks.
        self.occupied_rows: set[int] = set()
        self.occupied_diag_down: set[int] = set()
        self.occupied_diag_up: set[int] = set()
        self.row_mask = 0
        self.down_mask = 0  # bit index row - column + n - 1
        self.up_mask = 0  # bit index row + column
        self.stack: list[int] = []
        self.solutions: list[Solution] = []
        self.max_depth_reached = 0
        self.root_branches_completed = 0
        self.root_branch_nodes_completed = 0
        self.first_root_branch_seconds: float | None = None
        self._solve_started_at: float | None = None
        self._all_rows = (1 << n) - 1
        if self.spiral_order:
            self._order, self._rows_by_col = clockwise_spiral_order(n)
        else:
            self._order = tuple(range(n))
            self._rows_by_col = None

    def _make_frame(self, column: int, depth: int) -> _Frame:
        limit = self.n
        minimum_row = 0
        if self.remove_symmetry:
            if self.spiral_order:
                # Select the BOTTOM half instead of the top half to preserve
                # center-first candidate order (even n starts at n//2).
                if depth == 0:
                    minimum_row = self.n // 2
                elif depth == 1 and self.n % 2 and self.positions[self._order[0]] == self.n // 2:
                    # A first queen on the horizontal reflection axis needs
                    # a second-queen tie break, also keeping the lower half.
                    minimum_row = self.n // 2 + 1
            else:
                # Preserve the legacy non-spiral variants' top-half pruning.
                if depth == 0:
                    limit = (self.n + 1) // 2
                elif depth == 1 and self.n % 2 and self.positions[self._order[0]] == self.n // 2:
                    limit = self.n // 2
        ordered_rows = (
            self._rows_by_col[column] if minimum_row == 0 and limit == self.n
            else tuple(row for row in self._rows_by_col[column] if minimum_row <= row < limit)
        ) if self._rows_by_col is not None else None
        if self.bit_optimized and depth > 0:
            # Shift occupied diagonals to local candidate-row bits. The
            # first queen is still plain scanned as in the original variant.
            forbidden = (self.row_mask | (self.down_mask >> (self.n - 1 - column))
                         | (self.up_mask >> column))
            allowed_range = ((1 << limit) - 1) & ~((1 << minimum_row) - 1)
            allowed = self._all_rows & ~forbidden & allowed_range
            return _Frame(column, limit, next_row=0 if ordered_rows is not None else minimum_row,
                          remaining_bits=allowed, ordered_rows=ordered_rows)
        return _Frame(column, limit, next_row=0 if ordered_rows is not None else minimum_row,
                      ordered_rows=ordered_rows)

    @staticmethod
    def _next_candidate(frame: _Frame) -> int | None:
        if frame.ordered_rows is not None:
            # Preserve the clockwise spiral order even with bit-optimized
            # candidate pruning; only safe bit candidates are returned.
            while frame.next_row < len(frame.ordered_rows):
                row = frame.ordered_rows[frame.next_row]
                frame.next_row += 1
                if frame.remaining_bits is None:
                    return row
                bit = 1 << row
                if frame.remaining_bits & bit:
                    frame.remaining_bits ^= bit
                    return row
            return None
        if frame.remaining_bits is not None:
            if not frame.remaining_bits:
                return None
            lowest = frame.remaining_bits & -frame.remaining_bits
            frame.remaining_bits ^= lowest
            return lowest.bit_length() - 1
        if frame.next_row >= frame.limit:
            return None
        row = frame.next_row
        frame.next_row += 1
        return row

    def _safe(self, col: int, row: int) -> bool:
        if not self.bit_optimized:
            return (row not in self.occupied_rows
                    and row - col not in self.occupied_diag_down
                    and row + col not in self.occupied_diag_up)
        return not (
            (self.row_mask & (1 << row))
            or (self.down_mask & (1 << (row - col + self.n - 1)))
            or (self.up_mask & (1 << (row + col)))
        )

    def _add(self, col: int, row: int):
        self.positions[col] = row
        if self.bit_optimized:
            self.row_mask |= 1 << row
            self.down_mask |= 1 << (row - col + self.n - 1)
            self.up_mask |= 1 << (row + col)
        else:
            self.occupied_rows.add(row)
            self.occupied_diag_down.add(row - col)
            self.occupied_diag_up.add(row + col)
        self.stack.append(row)
        self.max_depth_reached = max(self.max_depth_reached, len(self.stack))
        self.emit_step("place", self.positions, column=col, row=row,
                       message=f"{col + 1}열 {row + 1}행 퀸 배치")

    def _remove(self, col: int):
        row = self.positions[col]
        if row < 0:
            return
        self.positions[col] = -1
        if self.bit_optimized:
            self.row_mask ^= 1 << row
            self.down_mask ^= 1 << (row - col + self.n - 1)
            self.up_mask ^= 1 << (row + col)
        else:
            self.occupied_rows.remove(row)
            self.occupied_diag_down.remove(row - col)
            self.occupied_diag_up.remove(row + col)
        self.stack.pop()
        self.emit_step("backtrack", self.positions, column=col, row=row,
                       message=f"{col + 1}열 {row + 1}행 퀸 제거")

    def _record(self):
        original = tuple(self.positions)
        self.solutions.append(Solution(original))
        self.solution_count += 1
        self.emit_step("solution", original, message=f"{self.solution_count}번째 해답")
        if self.remove_symmetry and self.n > 1:
            other = horizontal_reflection(original)
            if other != original:
                self.solutions.append(Solution(other))
                self.solution_count += 1
                self.emit_step("symmetry", other, message="대칭 해답 복원 (탐색 노드 증가 없음)")

    def _finished_branch(self):
        self.root_branches_completed += 1
        self.root_branch_nodes_completed = self.explored_nodes
        if self.first_root_branch_seconds is None and self._solve_started_at is not None:
            self.first_root_branch_seconds = perf_counter() - self._solve_started_at
        self.notify_checkpoint()

    def solve(self) -> list[Solution]:
        if self.is_finished or self.is_cancelled:
            return self.solutions
        self._solve_started_at = perf_counter()
        self.emit_step("start", self.positions, message="탐색 시작")
        # Spiral order changes only *which* positions are checked first.
        # No queen is placed permanently; every complete solution is eligible.
        frames = [self._make_frame(self._order[0], 0)]
        while frames:
            if self.stop_requested:
                self.is_cancelled = True
                break
            depth = len(frames) - 1
            frame = frames[-1]
            row = self._next_candidate(frame)
            if row is None:
                frames.pop()
                if frames:
                    parent_col = frames[-1].column
                    self._remove(parent_col)
                    if len(frames) == 1:
                        self._finished_branch()
                continue

            col = frame.column
            self.explored_nodes += 1
            if self.explored_nodes in (16, 32, 64, 128) or self.explored_nodes % 256 == 0:
                self.notify_checkpoint()
            self.emit_step("consider", self.positions, column=col, row=row,
                           message=f"{col + 1}열 {row + 1}행 후보 검사")
            if not self._safe(col, row):
                self.emit_step("reject", self.positions, column=col, row=row, message="충돌로 제외")
                continue
            self._add(col, row)
            if depth + 1 == self.n:
                self._record()
                self._remove(col)
                if depth == 0:
                    self._finished_branch()
                continue
            next_col = self._order[depth + 1]
            frames.append(self._make_frame(next_col, depth + 1))
        if not self.is_cancelled:
            self.is_finished = True
        self.emit_step("cancelled" if self.is_cancelled else "complete", self.positions,
                       message="탐색 중단" if self.is_cancelled else "탐색 완료")
        return self.solutions
