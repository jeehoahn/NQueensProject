"""Multiple total-runtime estimators are independent of the old progress API."""
import time
import unittest

from algorithms.base import BaseAlgorithm
from algorithms.registry import AlgorithmRegistry
from estimation.base import BaseTimeEstimator
from estimation.registry import TimeEstimatorRegistry
from analysis.known_solutions import TOTAL_SOLUTIONS, solution_coverage
from execution.controller import ExecutionController


class SlowTestAlgorithm(BaseAlgorithm):
    algorithm_id = 'test_slow_runtime_estimates'
    display_name = 'Slow Runtime Test Algorithm'

    def solve(self):
        for index in range(1, 31):
            if self.stop_requested:
                self.is_cancelled = True
                return self.solutions
            self.explored_nodes = index
            time.sleep(.003)
        self.is_finished = True
        return self.solutions


class FixedRuntimeEstimator(BaseTimeEstimator):
    estimator_id = 'test_fixed_runtime'
    display_name = 'Fixed Runtime Test Estimator'

    def estimate(self, algorithm, elapsed_seconds):
        if algorithm.explored_nodes < 2:
            return None
        return 0.1


class FailingRuntimeEstimator(BaseTimeEstimator):
    estimator_id = 'test_failing_runtime'
    display_name = 'Failing Runtime Test Estimator'

    def estimate(self, algorithm, elapsed_seconds):
        raise RuntimeError('simulated prediction error')


class TestMultiTimeEstimation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AlgorithmRegistry.register(SlowTestAlgorithm)
        TimeEstimatorRegistry.register(FixedRuntimeEstimator)
        TimeEstimatorRegistry.register(FailingRuntimeEstimator)

    def test_multiple_estimators_one_execution(self):
        controller = ExecutionController(poll_interval=.001, save_history=False)
        controller.start(4, SlowTestAlgorithm.algorithm_id,
                         estimator_ids=['test_fixed_runtime', 'worst_case'])
        snap = controller.snapshot()
        self.assertEqual(set(snap.estimates), {'test_fixed_runtime', 'worst_case'})
        result = controller.wait(timeout=5)
        self.assertTrue(result.is_complete_result)
        self.assertEqual(result.explored_nodes, 30)
        self.assertEqual(len(result.time_estimates), 2)
        fixed = result.time_estimates['test_fixed_runtime']
        self.assertEqual(fixed.predicted_seconds, 0.1)
        self.assertIsNotNone(fixed.error_percent)

    def test_failed_estimator_does_not_stop_others(self):
        controller = ExecutionController(poll_interval=.001, save_history=False)
        controller.start(4, SlowTestAlgorithm.algorithm_id,
                         estimator_ids=['test_failing_runtime', 'test_fixed_runtime'])
        result = controller.wait(timeout=5)
        self.assertTrue(result.is_complete_result)
        failed = result.time_estimates['test_failing_runtime']
        self.assertIn('simulated prediction error', failed.error_message)
        self.assertIsNone(failed.error_percent)
        self.assertIsNone(result.time_estimates['test_fixed_runtime'].error_message)
        self.assertEqual(result.time_estimates['test_fixed_runtime'].predicted_seconds, 0.1)

    def test_cancelled_run_has_no_prediction_error_percent(self):
        controller = ExecutionController(poll_interval=.001, save_history=False)
        controller.start(4, SlowTestAlgorithm.algorithm_id,
                         estimator_ids=['test_fixed_runtime', 'worst_case'])
        time.sleep(.02)
        controller.request_stop()
        result = controller.wait(timeout=5)
        self.assertTrue(result.is_cancelled)
        self.assertTrue(all(m.error_percent is None for m in result.time_estimates.values()))

    def test_reject_empty_or_duplicate_estimator_selection(self):
        controller = ExecutionController(save_history=False)
        with self.assertRaises(ValueError):
            controller.start(4, estimator_ids=[])
        with self.assertRaises(ValueError):
            controller.start(4, estimator_ids=['worst_case', 'worst_case'])

    def test_solution_reference_coverage(self):
        self.assertEqual(TOTAL_SOLUTIONS[8], 92)
        self.assertEqual(solution_coverage(8, 92, complete=True), 100.0)
        self.assertAlmostEqual(solution_coverage(8, 46, complete=False), 50)
        self.assertEqual(solution_coverage(2, 0, complete=True), 100.0)
        self.assertIsNone(solution_coverage(2, 0, complete=False))
        self.assertIsNone(solution_coverage(19, 1, complete=True))


if __name__ == '__main__':
    unittest.main()
