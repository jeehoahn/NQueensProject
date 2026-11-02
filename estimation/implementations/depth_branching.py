"""Heuristic extrapolation of average branch factors by tree depth."""
from __future__ import annotations
import math
from estimation.base import BaseTimeEstimator
from estimation.registry import TimeEstimatorRegistry
from estimation.tree_probe import probe_for_algorithm, TreeProbeResult


class DepthBranchingEstimator(BaseTimeEstimator):
    estimator_id = 'depth_branching'
    display_name = '탐색 깊이별 평균 분기 계수 추정'

    def __init__(self):
        self.profile: TreeProbeResult | None = None

    def prepare(self, algorithm) -> None:
        self.profile = probe_for_algorithm(algorithm)

    def estimate(self, algorithm, elapsed_seconds: float) -> float | None:
        if self.profile is None:
            return None
        if elapsed_seconds < .001 or algorithm.explored_nodes < 8:
            return None
        result = self.profile.depth_candidate_nodes * elapsed_seconds / algorithm.explored_nodes
        return result if math.isfinite(result) and result >= 0 else None

    def prediction_note(self, algorithm) -> str:
        if self.profile is None:
            return '깊이별 표본 준비 중'
        return (f'깊이별 평균 분기 계수 {self.profile.trials}개 표본 경로로 추정; '
                f'평균 분기 수를 깊이마다 곱한 탐색 후보 ≈ {self.profile.depth_candidate_nodes:,.1f}개 × 현재 초/노드; '
                '독립 평균 곱 근사로 편향 가능')


TimeEstimatorRegistry.register(DepthBranchingEstimator)
