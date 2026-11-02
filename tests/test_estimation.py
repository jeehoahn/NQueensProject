import unittest

from algorithms.implementations.backtracking.stack_backtracking import StackBacktracking
from analysis.result import prediction_error_percent
from estimation.implementations.worst_case import candidate_check_upper_bound, WorstCaseTimeEstimator
from estimation.implementations.first_branch import FirstBranchTimeEstimator
from estimation.registry import TimeEstimatorRegistry


class TestEstimators(unittest.TestCase):
    def test_registry_contains_two_default_estimators(self):
        names = TimeEstimatorRegistry.available()
        self.assertIn('worst_case', names)
        self.assertIn('first_branch', names)
        self.assertIsInstance(TimeEstimatorRegistry.create('first_branch'), FirstBranchTimeEstimator)

    def test_upper_bound(self):
        self.assertEqual(candidate_check_upper_bound(1), 1)
        # n=4 -> 4 * (1+4+12+24) = 164 checks
        self.assertEqual(candidate_check_upper_bound(4), 164)

    def test_worst_case_uses_rate(self):
        algo = StackBacktracking(4)
        algo.explored_nodes = 100
        est = WorstCaseTimeEstimator()
        self.assertAlmostEqual(est.estimate(algo, 2), 164 / 50)
        self.assertIsNone(est.estimate(algo, 0.00001))

    def test_first_branch_time(self):
        algo = StackBacktracking(4)
        method = FirstBranchTimeEstimator()
        self.assertIsNone(method.estimate(algo, 0.1))
        algo.first_root_branch_seconds = 0.25
        self.assertEqual(method.estimate(algo, 0.3), 1.0)

    def test_error_percent_complete_only(self):
        self.assertEqual(prediction_error_percent(12, 10, complete=True), 20)
        self.assertIsNone(prediction_error_percent(12, 10, complete=False))
        self.assertIsNone(prediction_error_percent(None, 10, complete=True))
        self.assertIsNone(prediction_error_percent(1, 0, complete=True))
