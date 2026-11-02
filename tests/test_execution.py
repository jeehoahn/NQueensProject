import time
import unittest

from algorithms.base import BaseAlgorithm
from algorithms.registry import AlgorithmRegistry
from execution.controller import ExecutionController


class TestExecution(unittest.TestCase):
    def test_complete_run_and_metric_contract(self):
        c = ExecutionController(poll_interval=.001, save_history=False)
        c.start(8, estimator_ids=['worst_case', 'first_branch'])
        r = c.wait(10)
        self.assertIsNotNone(r)
        self.assertEqual(r.solution_count, 92)
        self.assertTrue(r.is_complete_result)
        self.assertEqual(set(r.time_estimates), {'worst_case', 'first_branch'})
        for m in r.time_estimates.values():
            if m.predicted_seconds is not None:
                self.assertGreaterEqual(m.error_percent, 0)
                self.assertLess(m.prediction_at_seconds, r.elapsed_seconds)

    def test_sequential_runs(self):
        c = ExecutionController(poll_interval=.001, save_history=False)
        c.start(4)
        self.assertEqual(c.wait(10).solution_count, 2)
        c.start(8)
        self.assertEqual(c.wait(10).solution_count, 92)

    def test_snapshot_before_run(self):
        self.assertIsNone(ExecutionController(save_history=False).snapshot())

    def test_stop_on_visualization_backpressure(self):
        c = ExecutionController(poll_interval=.001, save_history=False)
        c.start(12, visualize_steps=True)
        # Never dequeue: worker eventually blocks on bounded event queue.
        time.sleep(.06)
        self.assertTrue(c.snapshot().is_running)
        c.request_stop()
        r = c.wait(5)
        self.assertIsNotNone(r)
        self.assertTrue(r.is_cancelled)
        self.assertIsNone(r.time_estimates['worst_case'].error_percent)

    def test_ordered_steps_on_small_solver(self):
        c = ExecutionController(poll_interval=.001, save_history=False)
        c.start(4, visualize_steps=True)
        output = []
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            step = c.take_step()
            if step:
                output.append(step)
            elif not c.snapshot().is_running and c.snapshot().pending_steps == 0:
                break
            else:
                time.sleep(.001)
        r = c.wait(5)
        self.assertTrue(r.is_complete_result)
        self.assertEqual(output[-1].kind, 'complete')
        self.assertEqual([s.sequence for s in output], list(range(1, len(output) + 1)))

    def test_exception_returns_error_result(self):
        class BrokenSolver(BaseAlgorithm):
            algorithm_id = 'test_broken_solver_time'
            display_name = 'Broken Solver'
            def solve(self):
                raise RuntimeError('intentional')
        AlgorithmRegistry.register(BrokenSolver)
        c = ExecutionController(poll_interval=.001, save_history=False)
        c.start(4, algorithm_id='test_broken_solver_time')
        r = c.wait(5)
        self.assertIn('intentional', r.error_message)
        self.assertIsNone(r.time_estimates['worst_case'].error_percent)


class TestIndividualStop(unittest.TestCase):
    def test_cancelled_algorithm_does_not_prevent_next_run(self):
        controller = ExecutionController(poll_interval=0.001, save_history=False)
        controller.start(13, visualize_steps=False)
        controller.request_stop()
        stopped = controller.wait(10)
        self.assertIsNotNone(stopped)
        self.assertTrue(stopped.is_cancelled)
        self.assertFalse(stopped.is_complete_result)
        controller.start(4, visualize_steps=False)
        finished = controller.wait(10)
        self.assertTrue(finished.is_complete_result)
        self.assertEqual(finished.solution_count, 2)
