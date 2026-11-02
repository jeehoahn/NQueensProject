from typing import Iterable

from analysis.aggregator_base import BaseAggregator
from analysis.comparator import ComparisonRow, ResultComparator
from analysis.result import AlgorithmResult
from analysis.aggregator_registry import AggregatorRegistry


class SolutionCountAggregator(BaseAggregator):
    aggregator_id = "solution_count"
    display_name = "해답 수 기준"

    def aggregate(self, results: Iterable[AlgorithmResult]) -> list[ComparisonRow]:
        rows = ResultComparator.compare(results)
        return sorted(
            rows,
            key=lambda row: (
                not row.is_complete,
                -row.solution_count,
                row.elapsed_seconds,
            ),
        )


AggregatorRegistry.register(SolutionCountAggregator)
