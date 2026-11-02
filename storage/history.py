"""One immutable JSON file per execution, with strict filters for forecasts.

All runs (finished, cancelled, failed, and visualized) are recorded.  Runtime
extrapolation uses only successful runs with Step-by-Step disabled so playback
throttling does not bias the historical time measurements.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import os
from statistics import mean
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY_DIR = ROOT / "data" / "history"


@dataclass(frozen=True)
class MeanHistory:
    n: int
    mean_seconds: float
    mean_solutions: float
    runs: int


class HistoryStore:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or os.environ.get("NQUEENS_HISTORY_DIR") or DEFAULT_HISTORY_DIR)

    def save_result(self, result, *, visualize_steps: bool) -> Path:
        # Known registration IDs are alphanumeric plus underscores. Reject
        # paths from untrusted metadata rather than accidentally escaping root.
        if not result.algorithm_id.replace("_", "").isalnum():
            raise ValueError("Unsafe algorithm ID for history file")
        directory = self.root / result.algorithm_id / f"n_{result.board_size}"
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        identifier = uuid4().hex
        path = directory / f"{timestamp}_{identifier}.json"
        payload = {
            "version": 1,
            "run_id": identifier,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "algorithm_id": result.algorithm_id,
            "algorithm_name": result.algorithm_name,
            "n": result.board_size,
            "solution_scope": result.solution_scope,
            "fixed_queen_column_row": list(result.fixed_queen) if result.fixed_queen else None,
            "solution_count": result.solution_count,
            "explored_nodes": result.explored_nodes,
            "average_node_ms": result.average_node_ms,
            "elapsed_seconds": result.elapsed_seconds,
            "finished": result.is_finished,
            "cancelled": result.is_cancelled,
            "error_message": result.error_message,
            "step_visualization_enabled": visualize_steps,
            "time_estimates": {
                key: {
                    "predicted_seconds": metric.predicted_seconds,
                    "predicted_solutions": metric.predicted_solutions,
                    "solution_error_percent": metric.solution_error_percent,
                    "prediction_note": metric.prediction_note,
                    "error_percent": metric.error_percent,
                }
                for key, metric in result.time_estimates.items()
            },
        }
        # Atomic completion: a killed process never leaves a half JSON record.
        temporary = directory / (path.name + ".tmp")
        try:
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def records(self, algorithm_id: str) -> list[dict]:
        if not algorithm_id.replace("_", "").isalnum():
            return []
        base = self.root / algorithm_id
        if not base.is_dir():
            return []
        found: list[dict] = []
        for path in sorted(base.glob("n_*/*.json")):
            try:
                content = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(content, dict) and content.get("version") == 1 and content.get("algorithm_id") == algorithm_id:
                    found.append(content)
            except (OSError, UnicodeError, ValueError, TypeError):
                # Broken foreign/partial files cannot affect valid records.
                continue
        return found

    def smaller_n_averages(self, algorithm_id: str, target_n: int, *, scope: str) -> list[MeanHistory]:
        by_size: dict[int, list[dict]] = defaultdict(list)
        for record in self.records(algorithm_id):
            n = record.get("n")
            elapsed = record.get("elapsed_seconds")
            solutions = record.get("solution_count")
            if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n < target_n:
                continue
            if record.get("solution_scope") != scope or record.get("step_visualization_enabled") is not False:
                continue
            if record.get("finished") is not True or record.get("cancelled") is not False or record.get("error_message") is not None:
                continue
            if not isinstance(elapsed, (float, int)) or not math.isfinite(elapsed) or elapsed <= 0:
                continue
            if not isinstance(solutions, int) or isinstance(solutions, bool) or solutions < 0:
                continue
            by_size[n].append(record)
        return [MeanHistory(n, mean(row["elapsed_seconds"] for row in data),
                            mean(row["solution_count"] for row in data), len(data))
                for n, data in sorted(by_size.items())]
