import unittest

from analysis.node_metrics import average_node_ms, nodes_per_second
from analysis.result import AlgorithmResult
from execution.controller import ExecutionController


class TestNodeMetrics(unittest.TestCase):
    def test_average_node_duration(self):
        self.assertAlmostEqual(average_node_ms(2.0, 1000), 2.0)
        self.assertAlmostEqual(average_node_ms(0.00005, 100), 0.0005)
        self.assertIsNone(average_node_ms(0, 0))
        self.assertIsNone(average_node_ms(-1, 100))
        self.assertIsNone(nodes_per_second(0, 100))
        self.assertAlmostEqual(nodes_per_second(2, 100), 50.0)

    def test_snapshot_and_completed_result_have_same_metric(self):
        c = ExecutionController(poll_interval=0.001, save_history=False)
        c.start(8)
        result = c.wait(10)
        snap = c.snapshot()
        self.assertIsNotNone(result)
        self.assertGreater(result.explored_nodes, 0)
        self.assertAlmostEqual(result.average_node_ms, snap.average_node_ms)
        self.assertAlmostEqual(result.average_node_ms, result.elapsed_seconds * 1000 / result.explored_nodes)

    def test_no_nodes_is_unknown(self):
        r = AlgorithmResult('x', 'X', 4, 0, [], 0, .5, True, False)
        self.assertIsNone(r.average_node_ms)
