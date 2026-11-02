"""Presentation strategy is separate from the solver and Qt widget."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from algorithms.steps import SearchStep


@dataclass(frozen=True)
class StepPresentation:
    caption: str
    accent: str  # safe named color, interpreted by Qt UI


class BaseStepPresenter(ABC):
    algorithm_id = "base"

    @abstractmethod
    def present(self, step: SearchStep) -> StepPresentation:
        """Interpret algorithm-specific events for the generic board view."""
        raise NotImplementedError
