"""Generate training JSON by running the selected algorithms on smaller Ns.

Examples:
    python scripts/build_history.py --start 4 --end 7 --repeats 3
    python scripts/build_history.py --start 5 --end 8 --algorithms stack_backtracking pure_bfs
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import algorithms.implementations  # noqa: F401,E402
from algorithms.registry import AlgorithmRegistry  # noqa: E402
from execution.controller import ExecutionController  # noqa: E402
from storage.history import HistoryStore  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="작은 N들의 실행 결과를 JSON에 누적 저장합니다.")
    parser.add_argument("--start", type=int, default=4, help="시작 N (기본 4)")
    parser.add_argument("--end", type=int, default=7, help="끝 N (기본 7)")
    parser.add_argument("--repeats", type=int, default=2, help="각 N의 반복 횟수 (기본 2)")
    parser.add_argument("--algorithms", nargs="+", default=None, help="알고리즘 ID; 생략 시 9개 모두")
    parser.add_argument("--history-dir", type=Path, default=None, help="JSON 저장 폴더 변경")
    options = parser.parse_args(argv)
    if not 1 <= options.start <= options.end <= 12:
        parser.error("1 <= start <= end <= 12 조건이 필요합니다. (큰 N은 매우 오래 걸릴 수 있음)")
    if not 1 <= options.repeats <= 100:
        parser.error("1 <= repeats <= 100 조건이 필요합니다.")

    available = AlgorithmRegistry.available()
    selected = options.algorithms if options.algorithms is not None else list(available)
    for algorithm_id in selected:
        if algorithm_id not in available:
            parser.error(f"알 수 없는 알고리즘 ID: {algorithm_id}")
    if len(selected) != len(set(selected)):
        parser.error("같은 알고리즘을 중복 선택할 수 없습니다.")

    history_store = HistoryStore(options.history_dir)
    controller = ExecutionController(history_store=history_store)
    total = len(selected) * (options.end - options.start + 1) * options.repeats
    completed = 0
    for algorithm_id in selected:
        for n in range(options.start, options.end + 1):
            for repeat in range(1, options.repeats + 1):
                controller.start(n, algorithm_id, estimator_ids=["history_growth"], visualize_steps=False)
                result = controller.wait()
                if result is None or not result.is_complete_result or result.history_error:
                    print(f"기록 생성 실패: {algorithm_id} N={n}: "
                          f"{getattr(result, 'error_message', None) or getattr(result, 'history_error', None)}",
                          file=sys.stderr)
                    return 1
                completed += 1
                print(f"[{completed}/{total}] {algorithm_id} N={n} ({repeat}/{options.repeats}) "
                      f"해답={result.solution_count} 노드={result.explored_nodes} "
                      f"실행={result.elapsed_seconds:.6f}초 JSON={result.history_file}", flush=True)
    print(f"저장 위치: {history_store.root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
