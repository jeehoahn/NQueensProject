"""Simple empirical estimator: n times the runtime of the first root branch.

Requires an algorithm to expose first_root_branch_seconds after that branch
has fully finished (StackBacktracking does so). This projection assumes each
root branch costs roughly the same and is intentionally very simple.
"""

from estimation.base import BaseTimeEstimator
from estimation.registry import TimeEstimatorRegistry


class FirstBranchTimeEstimator(BaseTimeEstimator):
    estimator_id = "first_branch"
    display_name = "첫 분기 시간 × N (단순)"

    def estimate(self, algorithm, elapsed_seconds: float) -> float | None:
        branch_time = getattr(algorithm, "first_root_branch_seconds", None)
        if branch_time is None or branch_time <= 0:
            return None
        return float(algorithm.n * branch_time)


TimeEstimatorRegistry.register(FirstBranchTimeEstimator)
