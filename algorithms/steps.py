"""Algorithm-neutral immutable search event.

Each algorithm chooses *which* events to emit and what they mean.  The
renderer interprets the event using a registered algorithm-specific presenter.
positions[column] = row, -1 means empty; no Qt dependencies here.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchStep:
    algorithm_id: str
    sequence: int
    kind: str
    positions: tuple[int, ...]
    column: int | None
    row: int | None
    message: str
    explored_nodes: int
    solution_count: int
