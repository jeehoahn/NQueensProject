from analysis.aggregator_base import BaseAggregator


class AggregatorRegistry:
    """Registry for pluggable result aggregation strategies."""

    _aggregators: dict[str, type[BaseAggregator]] = {}

    @classmethod
    def register(cls, aggregator_class: type[BaseAggregator]) -> None:
        if not issubclass(aggregator_class, BaseAggregator):
            raise TypeError("Aggregator must inherit BaseAggregator.")
        aggregator_id = aggregator_class.aggregator_id
        if not aggregator_id or aggregator_id == "base":
            raise ValueError("A concrete aggregator must define aggregator_id.")
        cls._aggregators[aggregator_id] = aggregator_class

    @classmethod
    def get(cls, aggregator_id: str) -> type[BaseAggregator]:
        try:
            return cls._aggregators[aggregator_id]
        except KeyError as exc:
            raise KeyError(f"Unknown aggregator: {aggregator_id}") from exc

    @classmethod
    def create(cls, aggregator_id: str) -> BaseAggregator:
        return cls.get(aggregator_id)()

    @classmethod
    def available(cls) -> dict[str, str]:
        return {
            aggregator_id: aggregator_class.display_name
            for aggregator_id, aggregator_class in cls._aggregators.items()
        }
