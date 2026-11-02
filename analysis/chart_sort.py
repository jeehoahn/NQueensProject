"""Qt-independent data model and sorting for interactive comparison charts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class ChartEntry:
    label: str
    value: float | None
    annotation: str
    fields: Mapping[str, str | int | float | None] = field(default_factory=dict)
    partial: bool = False


def sort_chart_entries(
    entries: list[ChartEntry], key: str, descending: bool = False
) -> list[ChartEntry]:
    """Sort using an arbitrary column; incomplete and unknown values come last.

    The visual bar's magnitude remains unchanged; only its row order changes.
    """
    complete, partial = [], []
    for entry in entries:
        (partial if entry.partial else complete).append(entry)

    def order(items: list[ChartEntry]) -> list[ChartEntry]:
        present = [item for item in items if item.fields.get(key) is not None]
        absent = [item for item in items if item.fields.get(key) is None]
        present.sort(
            key=lambda item: (
                item.fields[key].casefold()
                if isinstance(item.fields[key], str)
                else item.fields[key],
                item.label.casefold(),
            ),
            reverse=descending,
        )
        return present + absent

    return order(complete) + order(partial)
