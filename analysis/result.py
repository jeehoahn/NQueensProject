"""Algorithm performance and time/solution-count forecast records."""
from dataclasses import dataclass, field
from typing import Any

from analysis.node_metrics import average_node_ms


def prediction_error_percent(predicted_seconds: float | None, actual_seconds: float, *, complete: bool) -> float | None:
    """Absolute time percentage error for a finished search only."""
    if not complete or predicted_seconds is None or actual_seconds <= 0:
        return None
    return abs(predicted_seconds - actual_seconds) / actual_seconds * 100.0


@dataclass(frozen=True)
class TimeEstimateMetric:
    estimator_id: str
    estimator_name: str
    predicted_seconds: float | None
    prediction_at_seconds: float | None
    error_percent: float | None
    error_message: str | None = None
    predicted_solutions: int | None = None
    solution_error_percent: float | None = None
    prediction_note: str | None = None


@dataclass
class AlgorithmResult:
    algorithm_id: str
    algorithm_name: str
    board_size: int
    solution_count: int
    solutions: list[Any]
    explored_nodes: int
    elapsed_seconds: float
    is_finished: bool
    is_cancelled: bool
    error_message: str | None = None
    time_estimates: dict[str, TimeEstimateMetric] = field(default_factory=dict)
    solution_scope: str = 'all'
    fixed_queen: tuple[int, int] | None = None
    history_file: str | None = None
    history_error: str | None = None

    @property
    def average_node_ms(self) -> float | None:
        return average_node_ms(self.elapsed_seconds, self.explored_nodes)

    @property
    def nodes_per_second(self) -> float:
        return self.explored_nodes / self.elapsed_seconds if self.elapsed_seconds > 0 else 0.0

    @property
    def is_complete_result(self) -> bool:
        return self.is_finished and not self.is_cancelled and self.error_message is None
