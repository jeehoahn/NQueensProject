"""Published solution totals for the standard N-Queens problem, N=1..15.

Counts distinguish all rotations/reflections (not 'fundamental' solutions).
For other N values we deliberately do not invent a total or percentage.
"""

TOTAL_SOLUTIONS: dict[int, int] = {
    1: 1,
    2: 0,
    3: 0,
    4: 2,
    5: 10,
    6: 4,
    7: 40,
    8: 92,
    9: 352,
    10: 724,
    11: 2680,
    12: 14200,
    13: 73712,
    14: 365596,
    15: 2279184,
}


def solution_coverage(n: int, found: int, *, complete: bool) -> float | None:
    """Fraction of known solutions found, or None when not meaningful.

    For N=2,3, finding zero solutions is correct only on a completed search.
    Coverage of an interrupted run reflects discovery, not correctness.
    """
    expected = TOTAL_SOLUTIONS.get(n)
    if expected is None:
        return None
    if expected == 0:
        return 100.0 if complete and found == 0 else None
    return 100.0 * found / expected
