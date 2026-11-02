"""Reproducible sampling of the *actual candidate work* in N-Queens search.

The pilot never calls ``solve`` or modifies the live search counters.  It
reproduces the selected solver's column order, candidate row order, symmetry
restrictions and bit-pruned candidate counting.  Thus both Knuth-style Monte
Carlo and depth-specific branching estimates study the same search tree as
stack/BFS, including the center-out clockwise spiral configurations.

The Knuth estimate is the mean of branching-product-weighted random walks;
the depth heuristic instead multiplies the separate average branching counts.
Both estimate candidate inspections (``explored_nodes``), not solution count.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import random

from algorithms.implementations.spiral_order import clockwise_spiral_order


@dataclass(frozen=True)
class TreeProbeResult:
    knuth_candidate_nodes: float
    depth_candidate_nodes: float
    trials: int
    root_children: int
    avg_branching: tuple[float, ...]
    avg_attempts: tuple[float, ...]


def _rows_to_inspect(n: int, depth: int, positions: list[int], order: tuple[int, ...],
                     rows_by_col: tuple[tuple[int, ...], ...] | None,
                     *, spiral_order: bool, remove_symmetry: bool) -> tuple[int, ...]:
    """Mirror the root/depth-1 restrictions in ConfiguredStackDFS._make_frame."""
    col = order[depth]
    row_order = rows_by_col[col] if rows_by_col is not None else tuple(range(n))
    if not remove_symmetry:
        return row_order
    first_row = positions[order[0]]
    if spiral_order:
        # Spiral root visits the lower half first; odd-sized central first
        # queen requires a second-level tie break on the same reflection axis.
        if depth == 0:
            return tuple(r for r in row_order if r >= n // 2)
        if depth == 1 and n % 2 and first_row == n // 2:
            return tuple(r for r in row_order if r > n // 2)
    else:
        if depth == 0:
            return tuple(r for r in row_order if r < (n + 1) // 2)
        if depth == 1 and n % 2 and first_row == n // 2:
            return tuple(r for r in row_order if r < n // 2)
    return row_order


def _candidate_options(n: int, positions: list[int], col: int,
                       rows: tuple[int, ...], *, bit_optimized: bool,
                       depth: int) -> tuple[int, list[int]]:
    """Return exactly (candidate inspections, expandable children) for a node.

    All candidates are inspected in plain scanning and on the first level of
    bit variants. Later bit levels inspect *only safe candidates* because the
    actual solver pre-filters them via ``remaining_bits``.
    """
    children = [
        row for row in rows
        if all(old_row != row and abs(old_col - col) != abs(old_row - row)
               for old_col, old_row in enumerate(positions) if old_row >= 0)
    ]
    attempts = len(children) if bit_optimized and depth > 0 else len(rows)
    return attempts, children


@lru_cache(maxsize=256)
def probe_search_tree(algorithm_id: str, n: int, *, centered: bool = False,
                      bit_optimized: bool = False, remove_symmetry: bool = False,
                      trials: int = 64, spiral_order: bool = False) -> TreeProbeResult:
    """Estimate the visited candidate nodes without executing the live solver.

    ``centered`` is a legacy compatibility parameter.  Current center-start
    variants use ``spiral_order=True`` and never fix a queen.  Old fixed-center
    callers are deliberately rejected rather than silently probing the wrong
    search tree.
    """
    if n < 1 or trials < 1:
        raise ValueError('n and trials must be positive')
    if centered:
        raise ValueError('fixed-center search is no longer supported by this probe')
    if spiral_order:
        order, rows_by_col = clockwise_spiral_order(n)
    else:
        order, rows_by_col = tuple(range(n)), None

    seed_data = f'{algorithm_id}/{n}/{spiral_order}/{bit_optimized}/{remove_symmetry}'
    seed = int.from_bytes(hashlib.sha256(seed_data.encode()).digest()[:8], 'big')
    rng = random.Random(seed)
    sum_knuth = 0.0
    branching_sums = [0.0] * n
    attempt_sums = [0.0] * n
    visits = [0] * n
    root_children = 0

    for trial in range(trials):
        positions = [-1] * n
        path_weight = 1.0
        candidate_work = 0.0
        for depth, col in enumerate(order):
            rows = _rows_to_inspect(
                n, depth, positions, order, rows_by_col,
                spiral_order=spiral_order, remove_symmetry=remove_symmetry,
            )
            attempts, children = _candidate_options(
                n, positions, col, rows, bit_optimized=bit_optimized, depth=depth,
            )
            if trial == 0 and depth == 0:
                root_children = len(children)
            candidate_work += path_weight * attempts
            branching_sums[depth] += len(children)
            attempt_sums[depth] += attempts
            visits[depth] += 1
            if not children:
                break
            path_weight *= len(children)
            positions[col] = rng.choice(children)
        sum_knuth += candidate_work

    avg_branching = tuple(
        branching_sums[d] / visits[d] if visits[d] else 0.0 for d in range(n)
    )
    avg_attempts = tuple(
        attempt_sums[d] / visits[d] if visits[d] else 0.0 for d in range(n)
    )
    depth_work = 0.0
    parents = 1.0
    for branching, attempts in zip(avg_branching, avg_attempts):
        depth_work += parents * attempts
        parents *= branching
    return TreeProbeResult(
        sum_knuth / trials, depth_work, trials, root_children,
        avg_branching, avg_attempts,
    )


def probe_for_algorithm(algorithm, *, trials: int = 64) -> TreeProbeResult:
    return probe_search_tree(
        algorithm.algorithm_id, algorithm.n,
        spiral_order=bool(getattr(algorithm, 'spiral_order', False)),
        bit_optimized=bool(getattr(algorithm, 'bit_optimized', False)),
        remove_symmetry=bool(getattr(algorithm, 'remove_symmetry', False)),
        trials=trials,
    )
