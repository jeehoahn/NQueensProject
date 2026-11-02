"""Tests for the supported (execution-time and solution-count) aggregators."""
import unittest

from analysis.aggregator_registry import AggregatorRegistry
from analysis.result import AlgorithmResult
import analysis.aggregators.performance  # noqa: F401
import analysis.aggregators.solution_count  # noqa: F401


def make_result(name, solutions, elapsed, complete=True):
    return AlgorithmResult(
        algorithm_id=name,
        algorithm_name=name,
        board_size=8,
        solution_count=solutions,
        solutions=[],
        explored_nodes=100,
        elapsed_seconds=elapsed,
        is_finished=complete,
        is_cancelled=not complete,
    )


class TestAggregatorRegistry(unittest.TestCase):
    def test_supported_aggregators_are_registered(self):
        available = AggregatorRegistry.available()
        self.assertIn('performance', available)
        self.assertIn('solution_count', available)

    def test_registry_creates_aggregator(self):
        aggregator = AggregatorRegistry.create('performance')
        self.assertEqual(aggregator.aggregator_id, 'performance')

    def test_performance_aggregator_orders_by_elapsed_time(self):
        results = [make_result('slower', 92, 2.0), make_result('faster', 92, 1.0)]
        rows = AggregatorRegistry.create('performance').aggregate(results)
        self.assertEqual([row.algorithm_id for row in rows], ['faster', 'slower'])

    def test_solution_count_aggregator_orders_by_solution_count(self):
        results = [make_result('few', 2, 1.0), make_result('many', 92, 2.0)]
        rows = AggregatorRegistry.create('solution_count').aggregate(results)
        self.assertEqual([row.algorithm_id for row in rows], ['many', 'few'])

    def test_incomplete_results_come_after_complete_results(self):
        results = [
            make_result('partial', 1, 0.1, complete=False),
            make_result('complete', 92, 10.0, complete=True),
        ]
        rows = AggregatorRegistry.create('solution_count').aggregate(results)
        self.assertEqual([row.algorithm_id for row in rows], ['complete', 'partial'])

    def test_unknown_aggregator_raises_key_error(self):
        with self.assertRaises(KeyError):
            AggregatorRegistry.create('does_not_exist')


if __name__ == '__main__':
    unittest.main()
