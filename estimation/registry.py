from estimation.base import BaseTimeEstimator


class TimeEstimatorRegistry:
    """Extensible ID -> estimator class registry."""

    _estimators: dict[str, type[BaseTimeEstimator]] = {}

    @classmethod
    def register(cls, estimator_class: type[BaseTimeEstimator]) -> None:
        if not issubclass(estimator_class, BaseTimeEstimator):
            raise TypeError("Time estimator must inherit BaseTimeEstimator.")
        key = estimator_class.estimator_id
        if not key or key == "base":
            raise ValueError("A concrete estimator must define estimator_id.")
        if key in cls._estimators:
            raise ValueError(f"Time estimator already registered: {key}")
        cls._estimators[key] = estimator_class

    @classmethod
    def create(cls, estimator_id: str) -> BaseTimeEstimator:
        try:
            estimator_class = cls._estimators[estimator_id]
        except KeyError:
            raise KeyError(f"Unknown time estimator: {estimator_id}") from None
        return estimator_class()

    @classmethod
    def available(cls) -> dict[str, str]:
        return {key: typ.display_name for key, typ in cls._estimators.items()}
