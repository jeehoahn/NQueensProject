"""Run one search at a time, estimate runtimes, publish steps, persist JSON."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from threading import Event, Lock, Thread
from time import perf_counter
from typing import Iterable

import algorithms.implementations  # register all nine solvers
import estimation.implementations.worst_case  # noqa: F401
import estimation.implementations.first_branch  # noqa: F401
import estimation.implementations.history_growth  # noqa: F401
import estimation.implementations.node_average  # noqa: F401
import estimation.implementations.knuth_monte_carlo  # noqa: F401
import estimation.implementations.depth_branching  # noqa: F401
from algorithms.registry import AlgorithmRegistry
from algorithms.steps import SearchStep
from analysis.node_metrics import average_node_ms
from analysis.result import AlgorithmResult, TimeEstimateMetric, prediction_error_percent
from estimation.registry import TimeEstimatorRegistry
from execution.step_channel import StepChannel
from storage.history import HistoryStore


@dataclass(frozen=True)
class ExecutionSnapshot:
    algorithm_id: str
    algorithm_name: str
    board_size: int
    explored_nodes: int
    solution_count: int
    elapsed_seconds: float
    is_running: bool
    is_finished: bool
    is_cancelled: bool
    estimates: dict[str, float | None] = field(default_factory=dict)
    prediction_at: dict[str, float | None] = field(default_factory=dict)
    estimator_errors: dict[str, str] = field(default_factory=dict)
    predicted_solutions: dict[str, int | None] = field(default_factory=dict)
    estimator_notes: dict[str, str] = field(default_factory=dict)
    pending_steps: int = 0

    @property
    def average_node_ms(self) -> float | None:
        return average_node_ms(self.elapsed_seconds, self.explored_nodes)


class ExecutionController:
    """One active search. All selected estimators observe the same worker."""

    def __init__(self, poll_interval: float = 0.015, *,
                 history_store: HistoryStore | None = None, save_history: bool = True):
        if poll_interval <= 0:
            raise ValueError('poll_interval must be positive')
        self.poll_interval = poll_interval
        self.history_store = history_store if history_store is not None else HistoryStore()
        self.save_history = save_history
        self.algorithm = None
        self.estimators = {}
        self._lock = Lock()
        self._finished_event = Event()
        self._worker: Thread | None = None
        self._monitor: Thread | None = None
        self._started_at: float | None = None
        self._completed_elapsed: float | None = None
        self._running = False
        self._result: AlgorithmResult | None = None
        self._estimates: dict[str, float | None] = {}
        self._prediction_at: dict[str, float | None] = {}
        self._estimator_errors: dict[str, str] = {}
        self._predicted_solutions: dict[str, int | None] = {}
        self._estimator_notes: dict[str, str] = {}
        self._steps: StepChannel | None = None
        self._visualize_steps = False

    def start(self, n: int, algorithm_id: str = 'stack_backtracking', *,
              estimator_ids: Iterable[str] | None = None,
              visualize_steps: bool = False) -> None:
        chosen = (list(estimator_ids) if estimator_ids is not None
                  else list(TimeEstimatorRegistry.available()))
        if not chosen or len(chosen) != len(set(chosen)):
            raise ValueError('At least one unique estimator must be selected')
        with self._lock:
            if self._running:
                raise RuntimeError('An execution is already running')
        if self._worker is not None:
            self._worker.join()
        if self._monitor is not None:
            self._monitor.join()
        algorithm = AlgorithmRegistry.create(algorithm_id, n)
        estimators = {key: TimeEstimatorRegistry.create(key) for key in chosen}
        for estimator in estimators.values():
            binder = getattr(estimator, 'bind_history_store', None)
            if callable(binder):
                binder(self.history_store)
        # Pilot probes are outside the measured search interval, so all
        # experimental estimators share one cached probe with zero impact
        # on the measured algorithm's explored-node count or elapsed time.
        prepare_errors = {}
        for key, estimator in estimators.items():
            try:
                estimator.prepare(algorithm)
            except Exception as exc:
                prepare_errors[key] = f'{type(exc).__name__}: {exc}'
        steps = StepChannel(lambda: algorithm.stop_requested) if visualize_steps else None
        if steps is not None:
            algorithm.set_step_sink(steps.publish)
        algorithm.set_checkpoint_observer(self._sample_estimates)
        with self._lock:
            self.algorithm = algorithm
            self.estimators = estimators
            self._steps = steps
            self._visualize_steps = visualize_steps
            self._result = None
            self._completed_elapsed = None
            self._estimates = {key: None for key in chosen}
            self._prediction_at = {key: None for key in chosen}
            self._estimator_errors = prepare_errors
            self._predicted_solutions = {key: None for key in chosen}
            self._estimator_notes = {}
            self._started_at = perf_counter()
            self._running = True
            self._finished_event.clear()
            self._monitor = Thread(target=self._monitor_estimates, daemon=True)
            self._worker = Thread(target=self._run_algorithm, daemon=True)
        # Historical estimates do not depend on current N search progress.
        # Sampling before worker start makes fast runs deterministic too.
        self._sample_estimates()
        self._monitor.start()
        self._worker.start()

    def _sample_estimates(self) -> None:
        algorithm = self.algorithm
        if algorithm is None or algorithm.stop_requested:
            return
        elapsed = perf_counter() - self._started_at
        for key, estimator in self.estimators.items():
            with self._lock:
                already_done = self._estimates[key] is not None or key in self._estimator_errors
            if already_done or algorithm.is_finished or algorithm.is_cancelled:
                continue
            try:
                estimated = estimator.estimate(algorithm, elapsed)
                if estimated is None:
                    note = estimator.prediction_note(algorithm)
                    if note:
                        with self._lock:
                            self._estimator_notes[key] = note
                    continue
                estimated = float(estimated)
                if not math.isfinite(estimated) or estimated < 0:
                    raise ValueError('Predicted seconds must be finite and nonnegative')
                predicted_count = estimator.estimate_solutions(algorithm)
                note = estimator.prediction_note(algorithm)
            except Exception as exc:
                with self._lock:
                    self._estimator_errors[key] = f'{type(exc).__name__}: {exc}'
            else:
                with self._lock:
                    if self._estimates[key] is None:
                        self._estimates[key] = estimated
                        self._prediction_at[key] = elapsed
                        self._predicted_solutions[key] = predicted_count
                        if note:
                            self._estimator_notes[key] = note

    def _monitor_estimates(self):
        while not self._finished_event.is_set():
            self._sample_estimates()
            self._finished_event.wait(self.poll_interval)

    def _run_algorithm(self):
        error = None
        try:
            self.algorithm.solve()
        except Exception as exc:
            error = f'{type(exc).__name__}: {exc}'
        finally:
            self._finished_event.set()
            if self._monitor is not None:
                self._monitor.join()
            elapsed = perf_counter() - self._started_at
            complete = self.algorithm.is_finished and not self.algorithm.is_cancelled and error is None
            with self._lock:
                metrics = {}
                for key, estimator in self.estimators.items():
                    predicted = self._predicted_solutions[key]
                    count_error = None
                    if complete and predicted is not None:
                        if self.algorithm.solution_count > 0:
                            count_error = 100.0 * abs(predicted - self.algorithm.solution_count) / self.algorithm.solution_count
                        elif predicted == 0:
                            count_error = 0.0
                    metrics[key] = TimeEstimateMetric(
                        estimator_id=key,
                        estimator_name=estimator.display_name,
                        predicted_seconds=self._estimates[key],
                        prediction_at_seconds=self._prediction_at[key],
                        error_percent=prediction_error_percent(self._estimates[key], elapsed, complete=complete),
                        error_message=self._estimator_errors.get(key),
                        predicted_solutions=predicted,
                        solution_error_percent=count_error,
                        prediction_note=self._estimator_notes.get(key),
                    )
                result = AlgorithmResult(
                    algorithm_id=self.algorithm.algorithm_id,
                    algorithm_name=self.algorithm.display_name,
                    board_size=self.algorithm.n,
                    solution_count=self.algorithm.solution_count,
                    solutions=list(self.algorithm.solutions),
                    explored_nodes=self.algorithm.explored_nodes,
                    elapsed_seconds=elapsed,
                    is_finished=self.algorithm.is_finished,
                    is_cancelled=self.algorithm.is_cancelled,
                    error_message=error,
                    time_estimates=metrics,
                    solution_scope=getattr(self.algorithm, 'solution_scope', 'all'),
                    fixed_queen=getattr(self.algorithm, 'fixed_queen', None),
                )
                self._result = result
                self._completed_elapsed = elapsed
            if self.save_history:
                try:
                    saved = self.history_store.save_result(result, visualize_steps=self._visualize_steps)
                    result.history_file = str(saved)
                except Exception as exc:
                    result.history_error = f'{type(exc).__name__}: {exc}'
            with self._lock:
                self._running = False

    def snapshot(self) -> ExecutionSnapshot | None:
        with self._lock:
            if self.algorithm is None or self._started_at is None:
                return None
            elapsed = (perf_counter() - self._started_at if self._running
                       else self._completed_elapsed)
            return ExecutionSnapshot(
                algorithm_id=self.algorithm.algorithm_id,
                algorithm_name=self.algorithm.display_name,
                board_size=self.algorithm.n,
                explored_nodes=self.algorithm.explored_nodes,
                solution_count=self.algorithm.solution_count,
                elapsed_seconds=elapsed,
                is_running=self._running,
                is_finished=self.algorithm.is_finished,
                is_cancelled=self.algorithm.is_cancelled,
                estimates=dict(self._estimates),
                prediction_at=dict(self._prediction_at),
                estimator_errors=dict(self._estimator_errors),
                predicted_solutions=dict(self._predicted_solutions),
                estimator_notes=dict(self._estimator_notes),
                pending_steps=self._steps.pending if self._steps else 0,
            )

    def take_step(self) -> SearchStep | None:
        return self._steps.take() if self._steps is not None else None

    def request_stop(self) -> None:
        with self._lock:
            if self._running and self.algorithm is not None:
                self.algorithm.request_stop()

    def wait(self, timeout: float | None = None) -> AlgorithmResult | None:
        if self._worker is None:
            raise RuntimeError('No execution has been started')
        if not self._finished_event.wait(timeout):
            return None
        if timeout == 0 and self._worker.is_alive():
            return None
        self._worker.join()
        if self._monitor is not None:
            self._monitor.join()
        with self._lock:
            return self._result

    @property
    def result(self) -> AlgorithmResult | None:
        with self._lock:
            return self._result
