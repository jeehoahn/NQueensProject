"""Online estimate from completed root branches and average measured node cost.

Unlike the worst-case combinatorial upper bound, this projects actual work
from completed root subtrees. BFS does not finish root subtrees in a useful
order and intentionally reports insufficient information instead of guessing.
"""
from __future__ import annotations
import math
from estimation.base import BaseTimeEstimator
from estimation.registry import TimeEstimatorRegistry
from estimation.tree_probe import probe_for_algorithm


class AverageNodeTimeEstimator(BaseTimeEstimator):
    estimator_id = 'node_average'
    display_name = '평균 노드 처리 시간 기반 (완료 분기 외삽)'

    def __init__(self):
        self.root_count: int = 0

    def prepare(self, algorithm) -> None:
        self.root_count = probe_for_algorithm(algorithm, trials=1).root_children

    def estimate(self, algorithm, elapsed_seconds: float) -> float | None:
        completed = getattr(algorithm, 'root_branches_completed', 0)
        # A root branch must have finished before extrapolation is meaningful.
        if elapsed_seconds < 0.001 or completed < 1 or algorithm.explored_nodes < 2:
            return None
        finished_nodes = getattr(algorithm, 'root_branch_nodes_completed', 0)
        if finished_nodes <= 0 or self.root_count < 1:
            return None
        total_nodes = (finished_nodes / completed) * self.root_count
        node_seconds = elapsed_seconds / algorithm.explored_nodes
        predicted = total_nodes * node_seconds
        return predicted if math.isfinite(predicted) and predicted >= 0 else None

    def prediction_note(self, algorithm) -> str:
        completed = getattr(algorithm, 'root_branches_completed', 0)
        if not completed:
            return '완료한 루트 분기 1개가 필요합니다. BFS에서는 이 추정법을 적용하지 않습니다.'
        return f'완료 루트 분기 {completed}개 × 평균 후보 검사 노드 수/분기 × 현재 평균 초/노드; 예상 루트 분기 {self.root_count}개'


TimeEstimatorRegistry.register(AverageNodeTimeEstimator)
