from algorithms.steps import SearchStep
from visualization.base import BaseStepPresenter, StepPresentation
from visualization.registry import StepPresenterRegistry


class BacktrackingStepPresenter(BaseStepPresenter):
    algorithm_id = "stack_backtracking"

    _COLORS = {
        "start": "neutral", "consider": "blue", "reject": "red",
        "place": "green", "solution": "gold", "backtrack": "orange",
        "complete": "green", "cancelled": "red",
    }

    def present(self, step: SearchStep) -> StepPresentation:
        return StepPresentation(step.message, self._COLORS.get(step.kind, "neutral"))


StepPresenterRegistry.register(BacktrackingStepPresenter)
