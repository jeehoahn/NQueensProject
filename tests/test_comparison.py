import unittest
from analysis.comparator import ResultComparator
from analysis.result import AlgorithmResult, TimeEstimateMetric


def result(name='A', elapsed=10, complete=True):
    return AlgorithmResult(
        algorithm_id=name, algorithm_name=name, board_size=8,
        solution_count=92 if complete else 10, solutions=[], explored_nodes=100,
        elapsed_seconds=elapsed, is_finished=complete, is_cancelled=not complete,
    )


class TestComparison(unittest.TestCase):
    def test_sorted_by_runtime(self):
        rows = ResultComparator.compare([result('A', 2), result('B', 1)])
        self.assertEqual([x.algorithm_name for x in rows], ['B', 'A'])

    def test_incomplete_not_comparable(self):
        self.assertFalse(ResultComparator.comparable_solution_counts([result(), result(complete=False)]))

    def test_rank_same_algorithm_ties(self):
        r = result()
        r.time_estimates = {
            k: TimeEstimateMetric(k, k, 10.0, 1.0, err)
            for k, err in [('a', 5.0), ('b', 2.0), ('c', 2.0), ('d', None)]
        }
        self.assertEqual(ResultComparator.estimation_ranks(r), {'b': 1, 'c': 1, 'a': 3})
