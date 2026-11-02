from typing import Type

from algorithms.base import BaseAlgorithm


class AlgorithmRegistry:
    """Maps stable algorithm IDs to algorithm classes."""

    _algorithms: dict[str, Type[BaseAlgorithm]] = {}

    @classmethod
    def register(cls, algorithm_class: Type[BaseAlgorithm]) -> None:
        algorithm_id = algorithm_class.algorithm_id
        if not algorithm_id or algorithm_id == "base":
            raise ValueError("A concrete algorithm must define algorithm_id.")
        if algorithm_id in cls._algorithms:
            raise ValueError(f"Algorithm already registered: {algorithm_id}")
        cls._algorithms[algorithm_id] = algorithm_class

    @classmethod
    def get(cls, algorithm_id: str) -> Type[BaseAlgorithm]:
        try:
            return cls._algorithms[algorithm_id]
        except KeyError:
            raise KeyError(f"Unknown algorithm: {algorithm_id}") from None

    @classmethod
    def create(cls, algorithm_id: str, n: int) -> BaseAlgorithm:
        """Create an algorithm. Only n is passed to its constructor."""
        return cls.get(algorithm_id)(n)

    @classmethod
    def available(cls) -> dict[str, str]:
        return {
            algorithm_id: algorithm_class.display_name
            for algorithm_id, algorithm_class in cls._algorithms.items()
        }
