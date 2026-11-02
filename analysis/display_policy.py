from dataclasses import dataclass
from typing import Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class SolutionDisplayPolicy:
    """Controls how many already-found solutions are shown to the user.

    If total_count is at least threshold, only limit solutions are displayed.
    Otherwise all available solutions are displayed.
    """

    threshold: int = 100
    limit: int = 10

    def __post_init__(self):
        if self.threshold < 1:
            raise ValueError("threshold must be at least 1.")
        if self.limit < 1:
            raise ValueError("limit must be at least 1.")

    def select(self, solutions: Sequence[T], total_count: int) -> list[T]:
        if total_count < self.threshold:
            return list(solutions)
        return list(solutions[:self.limit])
