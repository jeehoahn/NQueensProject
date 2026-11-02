import unittest

from algorithms.registry import AlgorithmRegistry
from algorithms.implementations.backtracking.stack_backtracking import StackBacktracking


class TestStackBacktracking(unittest.TestCase):

    def test_known_solution_counts(self):
        expected = {
            1: 1,
            2: 0,
            3: 0,
            4: 2,
            5: 10,
            6: 4,
            7: 40,
            8: 92,
        }

        for n, expected_count in expected.items():
            with self.subTest(n=n):
                algorithm = StackBacktracking(n)
                solutions = algorithm.solve()

                self.assertEqual(algorithm.solution_count, expected_count)
                self.assertEqual(len(solutions), expected_count)
                self.assertTrue(algorithm.is_finished)
                self.assertFalse(algorithm.is_cancelled)

    def test_registry_creation(self):
        algorithm = AlgorithmRegistry.create("stack_backtracking", 8)
        self.assertIsInstance(algorithm, StackBacktracking)
        self.assertEqual(algorithm.n, 8)

    def test_stop_before_search(self):
        algorithm = StackBacktracking(8)
        algorithm.request_stop()
        algorithm.solve()

        self.assertTrue(algorithm.is_cancelled)
        self.assertFalse(algorithm.is_finished)
        self.assertEqual(algorithm.solution_count, 0)


if __name__ == "__main__":
    unittest.main()
