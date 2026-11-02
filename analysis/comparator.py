from dataclasses import dataclass
from typing import Iterable

from analysis.result import AlgorithmResult


@dataclass(frozen=True)
class ComparisonRow:
    algorithm_id: str
    algorithm_name: str
    solution_count: int
    explored_nodes: int
    elapsed_seconds: float
    nodes_per_second: float
    is_complete: bool
    is_cancelled: bool


class ResultComparator:
    """Compare full runs; rank estimation methods *within each algorithm*."""

    @staticmethod
    def compare(results: Iterable[AlgorithmResult]) -> list[ComparisonRow]:
        rows = [ComparisonRow(
            algorithm_id=result.algorithm_id,
            algorithm_name=result.algorithm_name,
            solution_count=result.solution_count,
            explored_nodes=result.explored_nodes,
            elapsed_seconds=result.elapsed_seconds,
            nodes_per_second=result.nodes_per_second,
            is_complete=result.is_complete_result,
            is_cancelled=result.is_cancelled,
        ) for result in results]
        return sorted(rows, key=lambda row: (not row.is_complete, row.elapsed_seconds))

    @staticmethod
    def comparable_solution_counts(results: Iterable[AlgorithmResult]) -> bool:
        results = list(results)
        # Fixed-center searches only enumerate solutions under that anchor;
        # those counts must never be compared as complete all-solution totals.
        return (bool(results) and all(r.is_complete_result for r in results)
                and len({(r.board_size, r.solution_scope, r.fixed_queen) for r in results}) == 1)

    @staticmethod
    def estimation_ranks(result: AlgorithmResult) -> dict[str, int]:
        """Competition ranks (1, 1, 3) on error%, ignoring missing estimates."""
        valid = sorted(
            ((key, metric.error_percent) for key, metric in result.time_estimates.items()
             if metric.error_percent is not None),
            key=lambda pair: pair[1],
        )
        ranks: dict[str, int] = {}
        previous_error = None
        last_rank = 0
        for index, (key, error) in enumerate(valid, start=1):
            if previous_error is None or abs(error - previous_error) > 1e-9:
                last_rank = index
            ranks[key] = last_rank
            previous_error = error
        return ranks
