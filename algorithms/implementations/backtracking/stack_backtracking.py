"""Stack-based iterative DFS that can emit all candidate/placement/backtrack steps."""
from time import perf_counter

from algorithms.base import BaseAlgorithm
from algorithms.registry import AlgorithmRegistry
from algorithms.implementations.backtracking.data import BacktrackingState
from core.solution import Solution


class StackBacktracking(BaseAlgorithm):
    algorithm_id = "stack_backtracking"
    display_name = "Stack Backtracking"

    def __init__(self, n: int):
        super().__init__(n)
        self.stack: list[int] = []
        self.solutions: list[Solution] = []
        self.max_depth_reached = 0
        self.root_branches_completed = 0
        self.root_branch_nodes_completed = 0
        self.first_root_branch_seconds: float | None = None
        self._solve_started_at: float | None = None
        self._state = BacktrackingState(
            next_row_by_column=[0] * n,
            positions=[-1] * n,
        )

    def _is_safe(self, row: int, column: int) -> bool:
        state = self._state
        return (
            row not in state.occupied_rows
            and (row - column) not in state.occupied_diag_down
            and (row + column) not in state.occupied_diag_up
        )

    def _place(self, row: int, column: int) -> None:
        state = self._state
        state.positions[column] = row
        state.occupied_rows.add(row)
        state.occupied_diag_down.add(row - column)
        state.occupied_diag_up.add(row + column)
        state.depth = column + 1
        self.stack.append(row)
        self.max_depth_reached = max(self.max_depth_reached, state.depth)

    def _remove(self, column: int) -> None:
        state = self._state
        row = state.positions[column]
        if row == -1:
            return
        state.occupied_rows.remove(row)
        state.occupied_diag_down.remove(row - column)
        state.occupied_diag_up.remove(row + column)
        state.positions[column] = -1
        state.next_row_by_column[column] = row + 1
        state.depth = column
        if self.stack:
            self.stack.pop()
        if column == 0:
            self.root_branches_completed += 1
            self.root_branch_nodes_completed = self.explored_nodes
            if self.first_root_branch_seconds is None and self._solve_started_at is not None:
                self.first_root_branch_seconds = perf_counter() - self._solve_started_at
            self.notify_checkpoint()
        self.emit_step("backtrack", state.positions, column=column, row=row,
                       message=f"({column + 1}열, {row + 1}행) 퀸 제거 → 되돌아감")

    def solve(self) -> list[Solution]:
        if self.is_finished or self.is_cancelled:
            return self.solutions
        self._solve_started_at = perf_counter()
        state = self._state
        column = 0
        self.emit_step("start", state.positions, message="탐색 시작")

        while column >= 0:
            if self.stop_requested:
                self.is_cancelled = True
                break
            if state.next_row_by_column[column] >= self.n:
                state.next_row_by_column[column] = 0
                state.positions[column] = -1
                if column == 0:
                    break
                column -= 1
                self._remove(column)
                continue

            row = state.next_row_by_column[column]
            state.next_row_by_column[column] += 1
            self.explored_nodes += 1
            if self.explored_nodes in (16, 32, 64, 128) or self.explored_nodes % 256 == 0:
                self.notify_checkpoint()
            self.emit_step("consider", state.positions, column=column, row=row,
                           message=f"({column + 1}열, {row + 1}행) 배치 가능 여부 검사")
            if not self._is_safe(row, column):
                self.emit_step("reject", state.positions, column=column, row=row,
                               message="이미 배치된 퀸과 충돌 → 후보 제외")
                continue

            self._place(row, column)
            self.emit_step("place", state.positions, column=column, row=row,
                           message=f"({column + 1}열, {row + 1}행) 퀸 배치")
            if column == self.n - 1:
                self.solution_count += 1
                self.solutions.append(Solution(tuple(state.positions)))
                self.emit_step("solution", state.positions, column=column, row=row,
                               message=f"{self.solution_count}번째 완성된 해답 발견!")
                self._remove(column)
            else:
                column += 1
                state.next_row_by_column[column] = 0

        if not self.is_cancelled:
            self.is_finished = True
        self.emit_step("cancelled" if self.is_cancelled else "complete", state.positions,
                       message="탐색 중단" if self.is_cancelled else "전체 탐색 완료")
        return self.solutions


AlgorithmRegistry.register(StackBacktracking)
