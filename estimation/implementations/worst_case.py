"""Upper-bound work estimate based on candidate checks during DFS.

This is an upper bound for a row-uniqueness-pruning backtracker, NOT a
rigorous time bound for every possible future algorithm implementation.
"""

import math

from estimation.base import BaseTimeEstimator
from estimation.registry import TimeEstimatorRegistry


def candidate_check_upper_bound(n: int) -> int:
    """At each depth k, at most P(n,k) states test n candidate rows."""
    if n < 1:
        raise ValueError("n must be positive")
    product = 1
    total = 0
    for k in range(n):
        if k:
            product *= n - (k - 1)
        total += n * product
    return total


class WorstCaseTimeEstimator(BaseTimeEstimator):
    estimator_id = "worst_case"
    display_name = "최악의 탐색량 상한"

    def estimate(self, algorithm, elapsed_seconds: float) -> float | None:
        # Brief warm-up avoids unstable rates from the first few instructions.
        if elapsed_seconds < 0.002 or algorithm.explored_nodes < 16:
            return None
        speed = algorithm.explored_nodes / elapsed_seconds
        if speed <= 0:
            return None
        total = candidate_check_upper_bound(algorithm.n) / speed
        if not math.isfinite(total):
            raise ValueError("Time estimate is not finite")
        return total


TimeEstimatorRegistry.register(WorstCaseTimeEstimator)
