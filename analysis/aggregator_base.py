from abc import ABC, abstractmethod
from typing import Iterable

from analysis.comparator import ComparisonRow
from analysis.result import AlgorithmResult


class BaseAggregator(ABC):
    """Common contract for result aggregation and ranking strategies.

    Aggregators receive completed AlgorithmResult objects and return rows for
    presentation. They must not modify the supplied results.
    """

    aggregator_id = "base"
    display_name = "Base Aggregator"

    @abstractmethod
    def aggregate(
        self, results: Iterable[AlgorithmResult]
    ) -> list[ComparisonRow]:
        raise NotImplementedError
