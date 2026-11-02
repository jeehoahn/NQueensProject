from dataclasses import dataclass, field


@dataclass
class BacktrackingState:
    """Mutable state owned exclusively by StackBacktracking."""

    next_row_by_column: list[int]
    positions: list[int]
    occupied_rows: set[int] = field(default_factory=set)
    occupied_diag_down: set[int] = field(default_factory=set)
    occupied_diag_up: set[int] = field(default_factory=set)
    depth: int = 0
