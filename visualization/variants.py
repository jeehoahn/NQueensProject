"""Step presenter registrations for added DFS and BFS strategies.

Each algorithm controls step boundaries; the presenter interprets them.
Currently all share one neutral chessboard and event-specific captions.
"""
from algorithms.steps import SearchStep
from visualization.base import BaseStepPresenter, StepPresentation
from visualization.registry import StepPresenterRegistry


class VariantStepPresenter(BaseStepPresenter):
    _COLORS = {
        'start': 'neutral', 'consider': 'blue', 'reject': 'red',
        'place': 'green', 'enqueue': 'green', 'solution': 'gold',
        'symmetry': 'gold', 'symmetry_prune': 'orange', 'dequeue': 'blue', 'backtrack': 'orange',
        'complete': 'green', 'cancelled': 'red',
    }

    def present(self, step: SearchStep) -> StepPresentation:
        return StepPresentation(step.message or step.kind,
                                self._COLORS.get(step.kind, 'neutral'))


for _aid in (
    'center_stack', 'bit_stack', 'center_bit_stack',
    'symmetric_stack', 'symmetric_bit_stack', 'center_symmetric_bit_stack',
    'pure_bfs', 'center_bfs',
):
    StepPresenterRegistry.register(type(
        f'{_aid}_Presenter', (VariantStepPresenter,), {'algorithm_id': _aid}
    ))
