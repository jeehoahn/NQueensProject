from typing import Iterable

from analysis.aggregator_base import BaseAggregator
from analysis.comparator import ComparisonRow, ResultComparator
from analysis.result import AlgorithmResult
from analysis.aggregator_registry import AggregatorRegistry


class PerformanceAggregator(BaseAggregator):
    aggregator_id = "performance"
    display_name = "실행 시간 기준"

    def aggregate(self, results: Iterable[AlgorithmResult]) -> list[ComparisonRow]:
        return ResultComparator.compare(results)


AggregatorRegistry.register(PerformanceAggregator)
