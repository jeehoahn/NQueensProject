"""Bounded ordered step stream, with real back-pressure (no dropped events)."""
from queue import Empty, Full, Queue
from collections.abc import Callable

from algorithms.steps import SearchStep


class StepChannel:
    def __init__(self, stop_requested: Callable[[], bool], maxsize: int = 4):
        self._queue: Queue[SearchStep] = Queue(maxsize=maxsize)
        self._stop_requested = stop_requested

    def publish(self, step: SearchStep) -> None:
        while not self._stop_requested():
            try:
                self._queue.put(step, timeout=0.03)
                return
            except Full:
                pass

    def take(self) -> SearchStep | None:
        try:
            return self._queue.get_nowait()
        except Empty:
            return None

    @property
    def pending(self) -> int:
        return self._queue.qsize()
