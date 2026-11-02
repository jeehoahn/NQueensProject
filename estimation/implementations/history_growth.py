"""Predict runtime AND number of solutions from past smaller-N JSON runs.

Given two last available smaller board sizes n1<n2, extrapolate the slope
in log(runtime) and log1p(solution_count) per N.  Within each N, repeated
runs are averaged. With fewer than two distinct smaller Ns the method is
unavailable (never substitute a fabricated forecast).
"""
from __future__ import annotations
from dataclasses import dataclass
import math

from estimation.base import BaseTimeEstimator
from estimation.registry import TimeEstimatorRegistry
from storage.history import HistoryStore


@dataclass(frozen=True)
class HistoryForecast:
    predicted_seconds: float
    predicted_solutions: int
    source_ns: tuple[int, int]
    run_counts: tuple[int, int]
    seconds_growth_per_n: float
    solution_log_growth_per_n: float


class HistoryGrowthTimeEstimator(BaseTimeEstimator):
    estimator_id = "history_growth"
    display_name = "이전 N 결과 증가 기울기 (JSON 평균)"

    def __init__(self, store: HistoryStore | None = None):
        self.store = store or HistoryStore()
        self._cache: dict[tuple[str, int, str], HistoryForecast | None] = {}

    def bind_history_store(self, store: HistoryStore) -> None:
        """Use the controller's history directory, including test overrides."""
        self.store = store
        self._cache.clear()

    def forecast(self, algorithm) -> HistoryForecast | None:
        scope = getattr(algorithm, "solution_scope", "all")
        key = (algorithm.algorithm_id, algorithm.n, scope)
        if key not in self._cache:
            averages = self.store.smaller_n_averages(algorithm.algorithm_id, algorithm.n, scope=scope)
            if len(averages) < 2:
                self._cache[key] = None
            else:
                old, recent = averages[-2:]
                delta = recent.n - old.n
                elapsed_log_slope = (math.log(recent.mean_seconds) - math.log(old.mean_seconds)) / delta
                solutions_log_slope = (math.log1p(recent.mean_solutions) - math.log1p(old.mean_solutions)) / delta
                distance = algorithm.n - recent.n
                estimated_log_seconds = math.log(recent.mean_seconds) + elapsed_log_slope * distance
                estimated_log_solutions = math.log1p(recent.mean_solutions) + solutions_log_slope * distance
                if estimated_log_seconds > 700 or estimated_log_solutions > 700:
                    self._cache[key] = None
                else:
                    predicted_seconds = math.exp(estimated_log_seconds)
                    predicted_solutions = max(0, round(math.expm1(estimated_log_solutions)))
                    if not math.isfinite(predicted_seconds):
                        self._cache[key] = None
                    else:
                        self._cache[key] = HistoryForecast(
                            predicted_seconds, predicted_solutions,
                            (old.n, recent.n), (old.runs, recent.runs),
                            math.exp(elapsed_log_slope), solutions_log_slope,
                        )
        return self._cache[key]

    def estimate(self, algorithm, elapsed_seconds: float) -> float | None:
        forecast = self.forecast(algorithm)
        return None if forecast is None else forecast.predicted_seconds

    def estimate_solutions(self, algorithm) -> int | None:
        forecast = self.forecast(algorithm)
        return None if forecast is None else forecast.predicted_solutions

    def prediction_note(self, algorithm) -> str | None:
        forecast = self.forecast(algorithm)
        if forecast is None:
            return "같은 알고리즘으로 완료한 서로 다른 작은 N의 기록이 최소 2개 필요합니다 (Step 시각화 OFF)"
        a, b = forecast.source_ns
        ca, cb = forecast.run_counts
        return (
            f"N={a}({ca}회), N={b}({cb}회) 평균 기반 로그 기울기 외삽 | "
            f"시간 증가 배율/N={forecast.seconds_growth_per_n:.4g}, "
            f"해답 ln(1+개수) 기울기/N={forecast.solution_log_growth_per_n:.4g}"
        )


TimeEstimatorRegistry.register(HistoryGrowthTimeEstimator)
