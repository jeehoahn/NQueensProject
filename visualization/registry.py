from visualization.base import BaseStepPresenter, StepPresentation
from algorithms.steps import SearchStep


class StepPresenterRegistry:
    _presenters: dict[str, type[BaseStepPresenter]] = {}

    @classmethod
    def register(cls, presenter_type: type[BaseStepPresenter]) -> None:
        if not issubclass(presenter_type, BaseStepPresenter):
            raise TypeError("Presenter must subclass BaseStepPresenter")
        if not presenter_type.algorithm_id or presenter_type.algorithm_id == "base":
            raise ValueError("Concrete presenter needs an algorithm_id")
        if presenter_type.algorithm_id in cls._presenters:
            raise ValueError("Duplicate presenter")
        cls._presenters[presenter_type.algorithm_id] = presenter_type

    @classmethod
    def present(cls, step: SearchStep) -> StepPresentation:
        presenter_type = cls._presenters.get(step.algorithm_id)
        if presenter_type is None:
            return StepPresentation(step.message or step.kind, "neutral")
        return presenter_type().present(step)
