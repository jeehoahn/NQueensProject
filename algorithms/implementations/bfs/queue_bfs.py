"""Pure FIFO breadth-first state expansion, optionally center-out clockwise."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from algorithms.base import BaseAlgorithm
from algorithms.implementations.spiral_order import clockwise_spiral_order
from algorithms.registry import AlgorithmRegistry
from core.solution import Solution


@dataclass(frozen=True)
class BFSState:
    positions: tuple[int, ...]
    depth: int


class BaseQueueBFS(BaseAlgorithm):
    centered = False
    spiral_order = False

    def __init__(self, n: int):
        super().__init__(n)
        self.solution_scope = "all"
        self.fixed_queen = None
        self.max_queue_length = 0
        if self.spiral_order:
            self._order, self._rows_by_col = clockwise_spiral_order(n)
        else:
            self._order = tuple(range(n))
            self._rows_by_col = None

    @staticmethod
    def _safe(positions: tuple[int, ...], col: int, row: int) -> bool:
        return all(
            occupied_row != row
            and abs(occupied_col - col) != abs(occupied_row - row)
            for occupied_col, occupied_row in enumerate(positions)
            if occupied_row >= 0
        )

    def solve(self) -> list[Solution]:
        if self.is_finished or self.is_cancelled:
            return self.solutions
        base = [-1] * self.n
        self.emit_step("start", base, message="BFS 탐색 시작")
        queue = deque([BFSState(tuple(base), 0)])
        self.max_queue_length = 1
        while queue:
            if self.stop_requested:
                self.is_cancelled = True
                break
            state = queue.popleft()
            self.emit_step("dequeue", state.positions, message=f"BFS 대기열에서 깊이 {state.depth} 상태 꺼냄")
            if state.depth == self.n:
                self.solutions.append(Solution(state.positions))
                self.solution_count += 1
                self.emit_step("solution", state.positions, message=f"{self.solution_count}번째 완성 해답")
                continue
            col = self._order[state.depth]
            for row in (self._rows_by_col[col] if self._rows_by_col is not None else range(self.n)):
                if self.stop_requested:
                    self.is_cancelled = True
                    break
                self.explored_nodes += 1
                if self.explored_nodes in (16, 32, 64, 128) or self.explored_nodes % 256 == 0:
                    self.notify_checkpoint()
                self.emit_step("consider", state.positions, column=col, row=row,
                               message=f"BFS 깊이 {state.depth}: {col + 1}열 {row + 1}행 검사")
                if not self._safe(state.positions, col, row):
                    self.emit_step("reject", state.positions, column=col, row=row, message="충돌")
                    continue
                new_positions = list(state.positions)
                new_positions[col] = row
                queue.append(BFSState(tuple(new_positions), state.depth + 1))
                self.max_queue_length = max(self.max_queue_length, len(queue))
                self.emit_step("enqueue", new_positions, column=col, row=row,
                               message=f"BFS 대기열에 깊이 {state.depth + 1} 상태 추가")
            if self.is_cancelled:
                break
        if not self.is_cancelled:
            self.is_finished = True
        self.emit_step("cancelled" if self.is_cancelled else "complete", base,
                       message="탐색 중단" if self.is_cancelled else "BFS 탐색 완료")
        return self.solutions


class PureBFS(BaseQueueBFS):
    algorithm_id = "pure_bfs"
    display_name = "순수 BFS (FIFO 큐)"


class CenterBFS(BaseQueueBFS):
    algorithm_id = "center_bfs"
    display_name = "중앙 시작 달팽이 · BFS"
    spiral_order = True


AlgorithmRegistry.register(PureBFS)
AlgorithmRegistry.register(CenterBFS)
