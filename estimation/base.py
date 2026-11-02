from abc import ABC, abstractmethod

from algorithms.base import BaseAlgorithm


class BaseTimeEstimator(ABC):
    """Predict total wall-clock runtime, in seconds, from a running algorithm.

    The prediction is sampled ONCE while the algorithm is still running,
    then frozen. Return None while there is insufficient information.
    """

    estimator_id = "base"
    display_name = "Base Time Estimator"

    def prepare(self, algorithm: BaseAlgorithm) -> None:
        """Optional pre-run calibration excluded from the search runtime."""

    def estimate_solutions(self, algorithm: BaseAlgorithm) -> int | None:
        """Optional predicted solution count, independent of runtime prediction."""
        return None

    def prediction_note(self, algorithm: BaseAlgorithm) -> str | None:
        """Optional explanation of data inputs used for the forecast."""
        return None

    @abstractmethod
    def estimate(self, algorithm: BaseAlgorithm, elapsed_seconds: float) -> float | None:
        """Return predicted total seconds, or None when not ready."""
        raise NotImplementedError
