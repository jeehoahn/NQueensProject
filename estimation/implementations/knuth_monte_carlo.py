"""Knuth-style Monte Carlo search tree work estimate (random root-to-leaf walks)."""
from __future__ import annotations
import math
from estimation.base import BaseTimeEstimator
from estimation.registry import TimeEstimatorRegistry
from estimation.tree_probe import probe_for_algorithm, TreeProbeResult


class KnuthMonteCarloEstimator(BaseTimeEstimator):
    estimator_id = 'knuth_monte_carlo'
    display_name = 'Knuth Monte Carlo 탐색 트리 추정'

    def __init__(self):
        self.profile: TreeProbeResult | None = None

    def prepare(self, algorithm) -> None:
        self.profile = probe_for_algorithm(algorithm)

    def estimate(self, algorithm, elapsed_seconds: float) -> float | None:
        if self.profile is None:
            return None
        if elapsed_seconds < .001 or algorithm.explored_nodes < 8:
            return None
        result = self.profile.knuth_candidate_nodes * elapsed_seconds / algorithm.explored_nodes
        return result if math.isfinite(result) and result >= 0 else None

    def prediction_note(self, algorithm) -> str:
        if self.profile is None:
            return '탐색 경로 표본 준비 중'
        return (f'실행 전 무작위 경로 {self.profile.trials}회: '
                f'경로별 분기 수 누적곱의 평균 탐색 후보 ≈ {self.profile.knuth_candidate_nodes:,.1f}개 × 현재 초/노드; '
                '표본 경로 탐색은 실제 노드 수에 포함하지 않음')


TimeEstimatorRegistry.register(KnuthMonteCarloEstimator)
