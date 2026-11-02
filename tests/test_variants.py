"""Cross-check all nine independent search configurations against reference DFS."""
import unittest

import algorithms.implementations  # noqa: F401
from algorithms.registry import AlgorithmRegistry
from analysis.comparator import ResultComparator
from analysis.result import AlgorithmResult
from core.solution import Solution

EXPERIMENT_ALGORITHMS = (
    "stack_backtracking", "center_stack", "bit_stack", "center_bit_stack",
    "pure_bfs", "symmetric_stack", "center_bfs", "symmetric_bit_stack",
    "center_symmetric_bit_stack",
)
from visualization.registry import StepPresenterRegistry
import visualization.variants  # noqa: F401


class TestNineAlgorithms(unittest.TestCase):
    def test_nine_are_registered(self):
        self.assertEqual(len(EXPERIMENT_ALGORITHMS), 9)
        self.assertTrue(set(EXPERIMENT_ALGORITHMS).issubset(AlgorithmRegistry.available()))

    def test_every_solution_set_matches_reference_n1_through_n9(self):
        for n in range(1, 10):
            baseline = AlgorithmRegistry.create('stack_backtracking', n)
            reference = {tuple(x.positions) for x in baseline.solve()}
            for aid in EXPERIMENT_ALGORITHMS:
                with self.subTest(algorithm=aid, n=n):
                    solver = AlgorithmRegistry.create(aid, n)
                    found = [tuple(x.positions) for x in solver.solve()]
                    expected = reference
                    self.assertEqual(solver.solution_scope, 'all')
                    self.assertEqual(len(found), len(set(found)), 'duplicated solutions')
                    self.assertEqual(set(found), expected)
                    self.assertEqual(solver.solution_count, len(expected))
                    self.assertTrue(solver.is_finished)
                    self.assertFalse(solver.is_cancelled)
                    self.assertGreaterEqual(solver.explored_nodes, 0)
                    self.assertTrue(all(isinstance(Solution(x), Solution) for x in found))

    def test_plain_variants_scan_rows_without_bitmask_optimization(self):
        for algorithm_id in ("center_stack", "symmetric_stack"):
            solver = AlgorithmRegistry.create(algorithm_id, 8)
            depth = 0
            column = solver._order[depth]
            frame = solver._make_frame(column, depth)
            self.assertIsNone(frame.remaining_bits)
            self.assertEqual(frame.next_row, 0)
        centered = AlgorithmRegistry.create("center_stack", 8)
        centered.solve()
        self.assertEqual(centered.row_mask, 0)
        self.assertEqual(centered.down_mask, 0)
        self.assertEqual(centered.up_mask, 0)

    def test_bitmask_enables_after_first_queen_only(self):
        solver = AlgorithmRegistry.create("bit_stack", 8)
        self.assertIsNone(solver._make_frame(0, 0).remaining_bits)
        solver._add(0, 0)
        self.assertIsNotNone(solver._make_frame(1, 1).remaining_bits)
        solver._remove(0)
        spiral = AlgorithmRegistry.create("center_bit_stack", 8)
        first_col = spiral._order[0]
        second_col = spiral._order[1]
        self.assertEqual(first_col, 4)
        self.assertIsNone(spiral._make_frame(first_col, 0).remaining_bits)
        spiral._add(first_col, 4)
        self.assertIsNotNone(spiral._make_frame(second_col, 1).remaining_bits)
        spiral._remove(first_col)

    def test_spiral_order_starts_at_center_without_fixing_a_queen(self):
        from algorithms.implementations.spiral_order import clockwise_spiral_order
        for n in range(1, 11):
            columns, rows = clockwise_spiral_order(n)
            self.assertEqual(len(columns), n)
            self.assertEqual(set(columns), set(range(n)))
            self.assertEqual(rows[columns[0]][0], n // 2)
            self.assertEqual(columns[0], n // 2)
            self.assertTrue(all(len(row_order) == n and len(set(row_order)) == n
                                for row_order in rows))

        for aid in ('center_stack', 'center_bit_stack', 'center_bfs', 'center_symmetric_bit_stack'):
            solver = AlgorithmRegistry.create(aid, 8)
            self.assertIsNone(solver.fixed_queen)
            self.assertEqual(solver.solution_scope, 'all')
            found = [tuple(sol.positions) for sol in solver.solve()]
            self.assertEqual(len(found), 92)
            self.assertTrue(any(position[4] != 4 for position in found))
            self.assertEqual(len(found), len(set(found)))

    def test_spiral_first_examined_cell_is_center(self):
        for aid in ('center_stack', 'center_bit_stack', 'center_bfs', 'center_symmetric_bit_stack'):
            solver = AlgorithmRegistry.create(aid, 8)
            considered = []
            def receive(step):
                if step.kind == 'consider' and not considered:
                    considered.append((step.column, step.row))
            solver.set_step_sink(receive)
            solver.solve()
            self.assertEqual(considered, [(4, 4)], aid)

    def test_symmetry_adds_solutions_without_node_checks(self):
        ordinary = AlgorithmRegistry.create('bit_stack', 8)
        paired = AlgorithmRegistry.create('symmetric_bit_stack', 8)
        ordinary.solve()
        paired.solve()
        self.assertEqual(ordinary.solution_count, paired.solution_count)
        self.assertLess(paired.explored_nodes, ordinary.explored_nodes)

    def test_bfs_uses_level_order(self):
        algorithm = AlgorithmRegistry.create('pure_bfs', 4)
        steps = []
        algorithm.set_step_sink(steps.append)
        algorithm.solve()
        depths = [sum(row >= 0 for row in x.positions) for x in steps if x.kind == 'dequeue']
        self.assertEqual(depths, sorted(depths))
        self.assertEqual([x.sequence for x in steps], list(range(1, len(steps) + 1)))
        self.assertTrue(StepPresenterRegistry.present(steps[0]).caption)

    def test_center_symmetry_emits_reconstruction(self):
        solver = AlgorithmRegistry.create('center_symmetric_bit_stack', 9)
        kinds = []
        solver.set_step_sink(lambda step: kinds.append(step.kind))
        solver.solve()
        self.assertIn('symmetry', kinds)
        self.assertTrue(solver.remove_symmetry)
        self.assertEqual(solver.solution_count, 352)

    def test_cancelled_new_algorithm(self):
        for aid in ('pure_bfs', 'center_bit_stack', 'symmetric_stack'):
            solver = AlgorithmRegistry.create(aid, 11)
            solver.request_stop()
            solver.solve()
            self.assertTrue(solver.is_cancelled)
            self.assertFalse(solver.is_finished)

    def test_comparing_mixed_scopes_is_invalid(self):
        def make(scope):
            return AlgorithmResult('test', 'Test', 8, 8, [], 100, .02, True, False,
                                   solution_scope=scope)
        self.assertFalse(ResultComparator.comparable_solution_counts([
            make('all'), make('fixed_center')]))
