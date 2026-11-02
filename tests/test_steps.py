import threading
import time
import unittest

from algorithms.implementations.backtracking.stack_backtracking import StackBacktracking
from algorithms.steps import SearchStep
from execution.step_channel import StepChannel
from visualization.registry import StepPresenterRegistry
import visualization.backtracking  # noqa: F401


class TestSearchSteps(unittest.TestCase):
    def test_full_n4_step_sequence_and_solution(self):
        algorithm = StackBacktracking(4)
        steps = []
        algorithm.set_step_sink(steps.append)
        algorithm.solve()
        self.assertEqual(algorithm.solution_count, 2)
        self.assertTrue(algorithm.is_finished)
        self.assertGreater(len(steps), 10)
        self.assertEqual([x.sequence for x in steps], list(range(1, len(steps) + 1)))
        self.assertEqual(steps[0].kind, 'start')
        self.assertEqual(steps[-1].kind, 'complete')
        self.assertEqual(sum(x.kind == 'solution' for x in steps), 2)
        self.assertTrue({'consider', 'reject', 'place', 'backtrack'} <= {x.kind for x in steps})
        for step in steps:
            self.assertEqual(len(step.positions), 4)
            self.assertTrue(all(-1 <= p < 4 for p in step.positions))

    def test_presenter_interprets_algorithm_specific_kind(self):
        step = SearchStep('stack_backtracking', 1, 'solution', (1, 3, 0, 2), 3, 2, 'found', 20, 1)
        presentation = StepPresenterRegistry.present(step)
        self.assertEqual(presentation.accent, 'gold')
        self.assertEqual(presentation.caption, 'found')
        fallback = SearchStep('unknown', 1, 'custom', (-1,), None, None, 'hello', 0, 0)
        self.assertEqual(StepPresenterRegistry.present(fallback).caption, 'hello')

    def test_bounded_channel_preserves_order_and_supports_stop(self):
        stop = threading.Event()
        channel = StepChannel(stop.is_set, maxsize=1)
        events = [SearchStep('x', i, 'foo', (-1,), None, None, '', i, 0) for i in range(1, 4)]
        worker = threading.Thread(target=lambda: [channel.publish(s) for s in events])
        worker.start()
        output = []
        deadline = time.monotonic() + 2
        while len(output) < 3 and time.monotonic() < deadline:
            item = channel.take()
            if item:
                output.append(item)
            else:
                time.sleep(.001)
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual([s.sequence for s in output], [1, 2, 3])
        # Stopping a producer blocked on a full queue must not deadlock.
        channel2 = StepChannel(stop.is_set, maxsize=1)
        stop.clear()
        channel2.publish(events[0])
        waiting = threading.Thread(target=lambda: channel2.publish(events[1]))
        waiting.start()
        time.sleep(.05)
        stop.set()
        waiting.join(1)
        self.assertFalse(waiting.is_alive())
