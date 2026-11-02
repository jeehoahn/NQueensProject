"""Deterministic Monte Carlo probes and root-branch estimation integration."""
import unittest
from time import perf_counter

import algorithms.implementations  # noqa: F401
from algorithms.registry import AlgorithmRegistry
from estimation.tree_probe import probe_for_algorithm, probe_search_tree
from estimation.registry import TimeEstimatorRegistry
from estimation.implementations.node_average import AverageNodeTimeEstimator
from estimation.implementations.knuth_monte_carlo import KnuthMonteCarloEstimator
from estimation.implementations.depth_branching import DepthBranchingEstimator
from execution.controller import ExecutionController


PRODUCTION_ALGORITHMS = (
    'stack_backtracking', 'center_stack', 'bit_stack', 'center_bit_stack',
    'pure_bfs', 'symmetric_stack', 'center_bfs', 'symmetric_bit_stack',
    'center_symmetric_bit_stack',
)


class TestTreeForecasts(unittest.TestCase):
    def test_all_six_methods_available(self):
        names = TimeEstimatorRegistry.available()
        self.assertTrue({'worst_case', 'first_branch', 'history_growth',
                         'node_average', 'knuth_monte_carlo', 'depth_branching'} <= set(names))

    def test_pilot_never_modifies_live_solver(self):
        for aid in PRODUCTION_ALGORITHMS:
            with self.subTest(aid=aid):
                a = AlgorithmRegistry.create(aid, 7)
                p = probe_for_algorithm(a)
                self.assertEqual(a.explored_nodes, 0)
                self.assertFalse(a.is_finished)
                self.assertGreater(p.knuth_candidate_nodes, 0)
                self.assertGreater(p.depth_candidate_nodes, 0)
                self.assertEqual(p.trials, 64)

    def test_knuth_and_depth_are_different_calculations(self):
        a = AlgorithmRegistry.create('stack_backtracking', 7)
        p = probe_for_algorithm(a)
        self.assertNotEqual(p.knuth_candidate_nodes, p.depth_candidate_nodes)
        self.assertGreater(p.root_children, 0)

    def test_spiral_probe_uses_exact_candidate_semantics(self):
        from algorithms.implementations.spiral_order import clockwise_spiral_order
        from estimation.tree_probe import _rows_to_inspect, _candidate_options
        for aid in ('center_stack', 'center_bit_stack', 'center_bfs', 'center_symmetric_bit_stack'):
            with self.subTest(aid=aid):
                a = AlgorithmRegistry.create(aid, 8)
                order, rows_by_col = clockwise_spiral_order(8)
                rows = _rows_to_inspect(
                    8, 0, [-1] * 8, order, rows_by_col,
                    spiral_order=True, remove_symmetry=bool(getattr(a, 'remove_symmetry', False)),
                )
                frame = a._make_frame(order[0], 0) if hasattr(a, '_make_frame') else None
                if frame is not None:
                    extracted = []
                    while True:
                        row = a._next_candidate(frame)
                        if row is None:
                            break
                        extracted.append(row)
                    self.assertEqual(tuple(extracted), rows)
                else:
                    self.assertEqual(rows, rows_by_col[order[0]])
                self.assertEqual(probe_for_algorithm(a, trials=64).root_children, len(rows))
                self.assertTrue(probe_for_algorithm(a).knuth_candidate_nodes > 0)

    def test_knuth_work_close_to_actual_for_n6_variants(self):
        for aid in PRODUCTION_ALGORITHMS:
            with self.subTest(aid=aid):
                a = AlgorithmRegistry.create(aid, 6)
                p = probe_for_algorithm(a, trials=2048)
                a.solve()
                self.assertTrue(a.is_finished)
                # Sampling-based estimator, not an exact count.
                self.assertLess(abs(p.knuth_candidate_nodes - a.explored_nodes) / a.explored_nodes, .16)

    def test_small_and_central_boards(self):
        for aid in PRODUCTION_ALGORITHMS:
            with self.subTest(aid=aid):
                a = AlgorithmRegistry.create(aid, 1)
                p = probe_for_algorithm(a)
                self.assertEqual(p.knuth_candidate_nodes, 1)
                self.assertEqual(p.depth_candidate_nodes, 1)

    def test_probe_deterministic_and_cached(self):
        a = AlgorithmRegistry.create('center_symmetric_bit_stack', 9)
        self.assertIs(probe_for_algorithm(a), probe_for_algorithm(a))

    def test_estimates_in_seconds_from_measured_node_rate(self):
        a = AlgorithmRegistry.create('bit_stack', 7)
        a.explored_nodes = 100
        for cls, field in [(KnuthMonteCarloEstimator, 'knuth_candidate_nodes'),
                           (DepthBranchingEstimator, 'depth_candidate_nodes')]:
            with self.subTest(cls=cls):
                e = cls()
                self.assertIsNone(e.estimate(a, .1))  # prep necessary
                e.prepare(a)
                self.assertIsNone(e.estimate(a, .00001))
                self.assertAlmostEqual(e.estimate(a, 2), getattr(e.profile, field) * .02)

    def test_average_node_estimator_uses_completed_branches(self):
        a = AlgorithmRegistry.create('stack_backtracking', 6)
        e = AverageNodeTimeEstimator()
        e.prepare(a)
        a.explored_nodes = 50
        self.assertIsNone(e.estimate(a, .1))
        a.root_branches_completed = 1
        a.root_branch_nodes_completed = 48
        self.assertAlmostEqual(e.estimate(a, 2), (48 * 6) * (2 / 50))

    def test_bfs_reports_unavailable_average_root_estimate(self):
        a = AlgorithmRegistry.create('pure_bfs', 8)
        e = AverageNodeTimeEstimator()
        e.prepare(a)
        a.explored_nodes = 200
        self.assertIsNone(e.estimate(a, 2))
        self.assertIn('BFS', e.prediction_note(a))

    def test_integration_controller_stores_all_three(self):
        controller = ExecutionController(poll_interval=.0005, save_history=False)
        ids = ['node_average', 'knuth_monte_carlo', 'depth_branching']
        controller.start(9, 'stack_backtracking', estimator_ids=ids)
        r = controller.wait(timeout=8)
        self.assertIsNotNone(r)
        self.assertTrue(r.is_complete_result)
        self.assertEqual(set(r.time_estimates), set(ids))
        # All forecasts are frozen no later than the end of the execution.
        for key in ids:
            self.assertIsNone(r.time_estimates[key].error_message)
            self.assertIsNotNone(r.time_estimates[key].predicted_seconds, key)
            self.assertIsNotNone(r.time_estimates[key].prediction_note, key)


if __name__ == '__main__':
    unittest.main()
