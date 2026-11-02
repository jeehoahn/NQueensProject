"""Search metrics shared by live snapshots and completed runs.

A node is the unit counted by the algorithm's explored_nodes field. For the
provided Stack Backtracking solver this is one candidate-position check.
Elapsed wall-clock time includes loop bookkeeping, prediction sampling and any
Step-by-Step back-pressure; it is not the isolated cost of a candidate check.
"""


def average_node_ms(elapsed_seconds: float, explored_nodes: int) -> float | None:
    """Mean wall-clock milliseconds per visited search node (if any)."""
    if explored_nodes <= 0 or elapsed_seconds < 0:
        return None
    return elapsed_seconds * 1000.0 / explored_nodes


def nodes_per_second(elapsed_seconds: float, explored_nodes: int) -> float | None:
    """Visited nodes per second. Return None before the clock has advanced."""
    if elapsed_seconds <= 0 or explored_nodes < 0:
        return None
    return explored_nodes / elapsed_seconds
