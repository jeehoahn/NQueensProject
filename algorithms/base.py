"""Extend this class with a new solver; the constructor always receives n only."""
from abc import ABC, abstractmethod
from collections.abc import Callable

from algorithms.steps import SearchStep


class BaseAlgorithm(ABC):
    algorithm_id = "base"
    display_name = "Base Algorithm"
    solution_scope = "all"  # fixed_center algorithms report conditional solutions
    fixed_queen = None

    def __init__(self, n: int):
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise ValueError("Board size n must be a positive integer.")
        self.n = n
        self.explored_nodes = 0
        self.solution_count = 0
        self.is_finished = False
        self.is_cancelled = False
        self.stop_requested = False
        self.solutions = []
        self._step_sink: Callable[[SearchStep], None] | None = None
        self._step_sequence = 0
        self._checkpoint_observer: Callable[[], None] | None = None

    def set_step_sink(self, sink: Callable[[SearchStep], None] | None) -> None:
        """Opt in/out of detailed event emission without changing solve(n)."""
        self._step_sink = sink

    def emit_step(
        self,
        kind: str,
        positions: tuple[int, ...] | list[int],
        *,
        column: int | None = None,
        row: int | None = None,
        message: str = "",
    ) -> None:
        """Only subclasses decide meaningful step boundaries and event kinds."""
        if self._step_sink is None:
            return
        self._step_sequence += 1
        step = SearchStep(
            algorithm_id=self.algorithm_id,
            sequence=self._step_sequence,
            kind=kind,
            positions=tuple(positions),
            column=column,
            row=row,
            message=message,
            explored_nodes=self.explored_nodes,
            solution_count=self.solution_count,
        )
        self._step_sink(step)

    def set_checkpoint_observer(self, observer: Callable[[], None] | None) -> None:
        """Optional checkpoint observer used by time estimators, no Qt dependency."""
        self._checkpoint_observer = observer

    def notify_checkpoint(self) -> None:
        if self._checkpoint_observer is not None:
            self._checkpoint_observer()

    def request_stop(self) -> None:
        self.stop_requested = True

    @abstractmethod
    def solve(self):
        raise NotImplementedError
