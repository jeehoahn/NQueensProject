"""Records remain intact and historical extrapolation uses only earlier N."""
import json
from pathlib import Path
import tempfile
import unittest

import algorithms.implementations
from algorithms.registry import AlgorithmRegistry
from analysis.result import AlgorithmResult
from execution.controller import ExecutionController
from estimation.implementations.history_growth import HistoryGrowthTimeEstimator
from storage.history import HistoryStore


def result(n, seconds, sols, *, scope='all', finished=True):
    return AlgorithmResult(
        'stack_backtracking', 'Stack Backtracking', n, sols, [], 40,
        seconds, finished, not finished, solution_scope=scope,
    )


class TestHistoryGrowth(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store = HistoryStore(self.temp_dir.name)

    def add(self, n, time, count, **flags):
        visualized = flags.pop('visualized', False)
        record = result(n, time, count, **flags)
        return self.store.save_result(record, visualize_steps=visualized)

    def test_append_only_separate_json_files(self):
        one = self.add(4, 2., 2)
        two = self.add(4, 3., 2)
        self.assertNotEqual(one, two)
        self.assertEqual(len(list(Path(self.temp_dir.name).rglob('*.json'))), 2)
        for path in (one, two):
            item = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(item['n'], 4)
            self.assertEqual(item['solution_count'], 2)
            self.assertTrue(item['finished'])

    def test_repeated_n_average_and_exponential_slope(self):
        self.add(4, 4., 2)
        self.add(4, 6., 2)
        self.add(5, 8., 4)
        self.add(5, 12., 4)
        estimator = HistoryGrowthTimeEstimator()
        estimator.bind_history_store(self.store)
        algo = AlgorithmRegistry.create('stack_backtracking', 6)
        self.assertAlmostEqual(estimator.estimate(algo, .1), 20.0)
        self.assertEqual(estimator.estimate_solutions(algo), 7)
        note = estimator.prediction_note(algo)
        self.assertIn('N=4', note)
        self.assertIn('N=5', note)

    def test_exclude_visualized_cancelled_or_other_scope(self):
        self.add(4, 5., 2)
        self.add(5, 10., 4, visualized=True)
        self.add(5, 900., 200, finished=False)
        self.add(5, 800., 200, scope='fixed_center')
        est = HistoryGrowthTimeEstimator()
        est.bind_history_store(self.store)
        self.assertIsNone(est.estimate(AlgorithmRegistry.create('stack_backtracking', 6), 0))
        self.add(5, 10., 4)
        est = HistoryGrowthTimeEstimator()
        est.bind_history_store(self.store)
        self.assertAlmostEqual(est.estimate(AlgorithmRegistry.create('stack_backtracking', 6), 0), 20.)

    def test_zero_solution_training_counts_are_supported(self):
        self.add(2, 3., 0)
        self.add(3, 6., 0)
        est = HistoryGrowthTimeEstimator()
        est.bind_history_store(self.store)
        algo = AlgorithmRegistry.create('stack_backtracking', 4)
        self.assertEqual(est.estimate_solutions(algo), 0)
        self.assertAlmostEqual(est.estimate(algo, 0), 12.)

    def test_controller_round_trip_and_independent_history(self):
        self.add(4, .5, 2)
        self.add(5, 1., 10)
        control = ExecutionController(poll_interval=.001, history_store=self.store)
        control.start(6, 'stack_backtracking', estimator_ids=['history_growth'])
        output = control.wait(10)
        self.assertTrue(output.is_complete_result)
        self.assertIsNotNone(output.history_file)
        self.assertTrue(Path(output.history_file).exists())
        metric = output.time_estimates['history_growth']
        self.assertAlmostEqual(metric.predicted_seconds, 2.0)
        self.assertEqual(metric.predicted_solutions, 39)
        self.assertIsNotNone(metric.error_percent)
        self.assertIsNotNone(metric.solution_error_percent)
        self.assertIn('N=4', metric.prediction_note)
        data = json.loads(Path(output.history_file).read_text(encoding='utf-8'))
        self.assertEqual(data['solution_count'], 4)
        self.assertFalse(data['step_visualization_enabled'])

    def test_visualized_run_record_is_not_used_for_forecast(self):
        control = ExecutionController(history_store=self.store)
        control.start(3, 'stack_backtracking', estimator_ids=['history_growth'], visualize_steps=True)
        # Consume ordered steps so worker can finish, don't let a full queue block.
        while True:
            step = control.take_step()
            snap = control.snapshot()
            if not snap.is_running and snap.pending_steps == 0:
                break
        output = control.wait(5)
        self.assertTrue(output.is_complete_result)
        rec = self.store.records('stack_backtracking')
        self.assertEqual(len(rec), 1)
        self.assertTrue(rec[0]['step_visualization_enabled'])
        self.assertEqual(self.store.smaller_n_averages('stack_backtracking', 4, scope='all'), [])
