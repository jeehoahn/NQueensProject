"""PySide6 front end for sequential experiments with live ordered step playback."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
    QListWidget, QSplitter,
)
from PySide6.QtCore import Qt

import algorithms.implementations.backtracking.stack_backtracking  # noqa: F401
import algorithms.implementations.backtracking.variants  # noqa: F401
import algorithms.implementations.bfs.queue_bfs  # noqa: F401
import estimation.implementations.worst_case  # noqa: F401
import estimation.implementations.first_branch  # noqa: F401
import estimation.implementations.history_growth  # noqa: F401
import estimation.implementations.node_average  # noqa: F401
import estimation.implementations.knuth_monte_carlo  # noqa: F401
import estimation.implementations.depth_branching  # noqa: F401
import visualization.backtracking  # noqa: F401
import visualization.variants  # noqa: F401
from algorithms.registry import AlgorithmRegistry
from analysis.comparator import ResultComparator
from analysis.known_solutions import TOTAL_SOLUTIONS, solution_coverage
from estimation.registry import TimeEstimatorRegistry
from execution.controller import ExecutionController
from ui.widgets.step_board_widget import StepBoardWidget
from ui.widgets.comparison_chart import SortableComparisonChart
from analysis.chart_sort import ChartEntry
from visualization.registry import StepPresenterRegistry


def seconds_text(seconds: float | None) -> str:
    if seconds is None:
        return "측정 중…"
    if seconds < 1:
        return f"{seconds:.4f}초"
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

STEP_PLAYBACK_SPEED = 40  # 초당 40단계


def node_time_text(milliseconds: float | None) -> str:
    if milliseconds is None:
        return "측정 중…"
    if milliseconds < 0.001:
        return f"{milliseconds * 1000:.3f} μs/노드"
    return f"{milliseconds:.6f} ms/노드"


class SortableTableItem(QTableWidgetItem):
    """Preserve numeric ordering when users click a table column header."""

    def __init__(self, display, sort_value=None):
        super().__init__(str(display))
        self.sort_value = sort_value if sort_value is not None else (
            None if str(display) in ("-", "미측정", "미확인") else str(display)
        )

    def __lt__(self, other):
        if not isinstance(other, SortableTableItem):
            return super().__lt__(other)
        a, b = self.sort_value, other.sort_value
        if a is None:
            return False
        if b is None:
            return True
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a < b
        return str(a).casefold() < str(b).casefold()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("N-Queens · 탐색 및 실행 시간 예측 실험")
        self.resize(1170, 890)
        self.controller = ExecutionController(poll_interval=0.01)
        self.results = []
        self.selected_algorithm_ids: list[str] = []
        self.selected_estimator_ids: list[str] = []
        self.algorithm_index = 0
        self.stop_after_current = False
        self.visualize = True
        self.playing = True
        self._playback_credit = 0.0
        self._last_tick_ms = None
        self._last_step_seq = 0
        self.estimate_rows = {}
        self._prediction_chart_entries: dict[str, list[ChartEntry]] = {}
        self.prediction_algorithm_checks: dict[str, QCheckBox] = {}

        self.pages = QStackedWidget()
        self.setCentralWidget(self.pages)
        self._build_setup_page()
        self._build_execution_page()
        self._build_result_page()
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._update_execution)
        self.pages.setCurrentWidget(self.setup_page)

    def _build_setup_page(self):
        self.setup_page = QWidget()
        layout = QVBoxLayout(self.setup_page)
        title = QLabel("N-Queens 알고리즘 비교 · 시간 예측")
        title.setStyleSheet("font-size: 24px; font-weight: 700")
        layout.addWidget(title)
        explanation = QLabel(
            "알고리즘과 시간 예측기를 선택하세요. 처음에는 모두 선택되어 있습니다. "
            "하나의 탐색을 여러 예측기가 동시에 관찰합니다."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        group = QGroupBox("실행 설정")
        form = QFormLayout(group)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 30)
        self.size_spin.setValue(8)
        form.addRow("N×N 보드 크기", self.size_spin)

        algorithms_box = QWidget()
        algorithm_layout = QVBoxLayout(algorithms_box)
        algorithm_layout.setContentsMargins(0, 0, 0, 0)
        self.algorithm_checks = {}
        for aid, name in AlgorithmRegistry.available().items():
            check = QCheckBox(name)
            check.setChecked(True)
            self.algorithm_checks[aid] = check
            algorithm_layout.addWidget(check)
        form.addRow("탐색 알고리즘", algorithms_box)

        estimators_box = QWidget()
        estimator_layout = QVBoxLayout(estimators_box)
        estimator_layout.setContentsMargins(0, 0, 0, 0)
        self.estimator_checks = {}
        for eid, name in TimeEstimatorRegistry.available().items():
            check = QCheckBox(name)
            check.setChecked(True)
            self.estimator_checks[eid] = check
            estimator_layout.addWidget(check)
        form.addRow("시간 예측 방법", estimators_box)

        self.step_enabled_check = QCheckBox("Step-by-Step 탐색 시각화 활성화")
        self.step_enabled_check.setChecked(True)
        form.addRow("단계 재생", self.step_enabled_check)
        note = QLabel(
            "※ 단계 시각화는 각 이벤트를 순서대로 표시하기 위해 알고리즘 실행 속도를 제한합니다. "
            "시간 성능을 공정하게 비교하려면 시각화를 해제하고 실행하세요. "
            "예측 시간은 실제 시작 후의 정보를 사용하며 모든 방법이 반드시 예측값을 내는 것은 아닙니다."
        )
        note.setWordWrap(True)
        form.addRow(note)
        layout.addWidget(group)
        layout.addStretch(1)
        start_button = QPushButton("선택한 알고리즘 실행")
        start_button.setMinimumHeight(44)
        start_button.clicked.connect(self._start_sequence)
        layout.addWidget(start_button)
        self.pages.addWidget(self.setup_page)

    def _build_execution_page(self):
        self.execution_page = QWidget()
        outer = QVBoxLayout(self.execution_page)
        self.execution_title = QLabel("알고리즘 실행 중")
        self.execution_title.setStyleSheet("font-size: 22px; font-weight: 700")
        outer.addWidget(self.execution_title)
        self.queue_label = QLabel("")
        outer.addWidget(self.queue_label)

        self.prediction_group = QGroupBox("예측 총시간과 실시간 카운트다운")
        self.prediction_layout = QVBoxLayout(self.prediction_group)
        outer.addWidget(self.prediction_group)
        metrics = QHBoxLayout()
        self.elapsed_label = QLabel("실제 경과 시간: 00:00")
        self.node_label = QLabel("현재 탐색 노드: 0번째 (누적 후보 검사)")
        self.node_time_label = QLabel("평균 노드당 시간: 측정 중…")
        self.solution_label = QLabel("발견한 해답: 0")
        for lbl in (self.elapsed_label, self.node_label, self.node_time_label, self.solution_label):
            lbl.setStyleSheet("font-size: 15px; font-weight: 500; padding: 3px")
            metrics.addWidget(lbl)
        outer.addLayout(metrics)

        self.step_box = QGroupBox("Step-by-Step 탐색 과정")
        step_layout = QVBoxLayout(self.step_box)
        controls = QHBoxLayout()
        self.play_button = QPushButton("일시정지")
        self.play_button.clicked.connect(self._toggle_play)
        self.next_button = QPushButton("다음 한 단계")
        self.next_button.clicked.connect(self._single_step)
        self.next_button.setEnabled(False)
        controls.addWidget(self.play_button)
        controls.addWidget(self.next_button)
        controls.addStretch(1)
        step_layout.addLayout(controls)
        self.step_label = QLabel("단계 이벤트를 기다리는 중…")
        self.step_label.setWordWrap(True)
        step_layout.addWidget(self.step_label)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.step_board = StepBoardWidget()
        self.step_log = QListWidget()
        splitter.addWidget(self.step_board)
        splitter.addWidget(self.step_log)
        splitter.setSizes([550, 350])
        step_layout.addWidget(splitter, 1)
        outer.addWidget(self.step_box, 1)
        stop_controls = QHBoxLayout()
        self.stop_current_button = QPushButton("현재 알고리즘만 중단 · 다음 실행")
        self.stop_current_button.setMinimumHeight(42)
        self.stop_current_button.clicked.connect(self._stop_current_algorithm)
        stop_controls.addWidget(self.stop_current_button)
        self.stop_button = QPushButton("전체 알고리즘 실행 중단")
        self.stop_button.setMinimumHeight(42)
        self.stop_button.clicked.connect(self._stop_sequence)
        stop_controls.addWidget(self.stop_button)
        outer.addLayout(stop_controls)
        self.pages.addWidget(self.execution_page)

    def _build_result_page(self):
        self.result_page = QWidget()
        page_layout = QVBoxLayout(self.result_page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page_layout.addWidget(scroll)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        scroll.setWidget(inner)
        title = QLabel("실행 결과 · 노드 통계와 시간 예측 정확도")
        title.setStyleSheet("font-size: 22px; font-weight: 700")
        layout.addWidget(title)
        self.result_note = QLabel("")
        self.result_note.setWordWrap(True)
        layout.addWidget(self.result_note)

        layout.addWidget(self._section_title("알고리즘별 실제 실행 시간 · 탐색 노드 · 해답"))
        self.result_table = QTableWidget(0, 9)
        self.result_table.setHorizontalHeaderLabels([
            "알고리즘", "상태", "실제 시간(초)", "총 탐색 노드", "평균 시간(ms/노드)",
            "초당 노드", "탐색 해답", "기준 해답", "발견률",
        ])
        self._configure_table(self.result_table)
        layout.addWidget(self.result_table)
        layout.addWidget(self._section_title("실행 시간 비교 그래프 (빠른 순 기본 정렬)"))
        self.time_chart = SortableComparisonChart([
            ("algorithm", "알고리즘"), ("elapsed", "실행 시간"),
            ("nodes", "탐색 노드"), ("average_ms", "노드당 평균 시간"),
        ], default_sort="elapsed")
        layout.addWidget(self.time_chart)

        layout.addWidget(self._section_title("알고리즘별 예측 총시간 · 오차율 · 순위"))
        self.estimation_table = QTableWidget(0, 11)
        self.estimation_table.setHorizontalHeaderLabels([
            "알고리즘", "시간 예측 방법", "예측 시점(초)", "예측 총시간(초)",
            "예측 해답", "해답 예측 오차율(%)", "실제 시간(초)", "시간 오차율(%)", "순위", "상태", "예측 근거",
        ])
        self._configure_table(self.estimation_table)
        layout.addWidget(self.estimation_table)

        filter_title = QLabel("아래 세 그래프에 표시할 알고리즘 (체크 해제 시 해당 알고리즘 제외)")
        filter_title.setWordWrap(True)
        layout.addWidget(filter_title)
        self.prediction_filter_widget = QWidget()
        self.prediction_filter_layout = QHBoxLayout(self.prediction_filter_widget)
        self.prediction_filter_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.prediction_filter_widget)

        prediction_columns = [
            ("algorithm", "알고리즘"), ("estimator", "예측 방법"),
            ("predicted", "예측 총시간"), ("actual", "실제 시간"),
            ("error", "오차율"), ("rank", "순위"),
        ]
        layout.addWidget(self._section_title("예측 총시간 그래프 (정확한 예측 순 기본 정렬)"))
        self.predicted_time_chart = SortableComparisonChart(prediction_columns, default_sort="error")
        layout.addWidget(self.predicted_time_chart)
        layout.addWidget(self._section_title("예측 오차율 그래프 (낮을수록 정확)"))
        self.error_chart = SortableComparisonChart(prediction_columns, default_sort="error")
        layout.addWidget(self.error_chart)
        layout.addWidget(self._section_title("예측 정확도 순위 그래프 (알고리즘 내부 순위)"))
        self.rank_chart = SortableComparisonChart(prediction_columns, default_sort="rank")
        layout.addWidget(self.rank_chart)
        info = QLabel(
            "각 그래프의 열 이름을 클릭하면 해당 필드로 정렬되며 다시 클릭하면 정렬 방향이 바뀝니다. "
            "오차율 = |예측 총시간 − 실제 실행 시간| / 실제 실행 시간 × 100. "
            "순위는 같은 알고리즘에 적용한 시간 예측 방법끼리 계산한 상대 순위입니다. "
            "중단·오류 또는 예측 불가능한 경우 오차율/순위는 미측정입니다. "
            "평균 노드당 시간은 전체 경과 시간/탐색 노드 수이며 순수 후보 검사만의 시간은 아닙니다."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch(1)
        go_back = QPushButton("설정으로 돌아가기")
        go_back.clicked.connect(lambda: self.pages.setCurrentWidget(self.setup_page))
        page_layout.addWidget(go_back)
        self.pages.addWidget(self.result_page)

    @staticmethod
    def _section_title(label: str):
        widget = QLabel(label)
        widget.setStyleSheet("font-size: 16px; font-weight: 650; margin-top: 14px")
        return widget

    @staticmethod
    def _configure_table(table: QTableWidget):
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionsClickable(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(100)

    @staticmethod
    def _fill_table(table: QTableWidget, rows):
        table.setSortingEnabled(False)
        table.setRowCount(0)
        for values in rows:
            row = table.rowCount()
            table.insertRow(row)
            for col, value in enumerate(values):
                if isinstance(value, tuple):
                    label, sort_value = value
                else:
                    label, sort_value = value, None
                table.setItem(row, col, SortableTableItem(label, sort_value))
        table.setSortingEnabled(True)
        table.setFixedHeight(min(650, max(110, 34 * (len(rows) + 1))))

    def _rebuild_prediction_filters(self):
        """Default all completed/attempted algorithm runs to visible."""
        while self.prediction_filter_layout.count():
            item = self.prediction_filter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.prediction_algorithm_checks = {}
        for result in self.results:
            if result.algorithm_id in self.prediction_algorithm_checks:
                continue
            check = QCheckBox(result.algorithm_name)
            check.setChecked(True)
            check.toggled.connect(self._update_filtered_prediction_charts)
            self.prediction_filter_layout.addWidget(check)
            self.prediction_algorithm_checks[result.algorithm_id] = check
        self.prediction_filter_layout.addStretch(1)

    def _update_filtered_prediction_charts(self, *_args):
        selected = {
            key for key, check in self.prediction_algorithm_checks.items() if check.isChecked()
        }
        for chart_name, entries in self._prediction_chart_entries.items():
            getattr(self, chart_name).set_entries([
                row for row in entries if row.fields.get("algorithm_id") in selected
            ])

    def _create_prediction_rows(self):
        while self.prediction_layout.count():
            item = self.prediction_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.estimate_rows = {}
        names = TimeEstimatorRegistry.available()
        for estimator_id in self.selected_estimator_ids:
            row = QLabel(f"{names[estimator_id]}   |   예측 총시간: 측정 중…   |   남은 시간: 측정 중…")
            row.setStyleSheet("font-size: 16px; padding: 6px; border-bottom: 1px solid #999")
            self.prediction_layout.addWidget(row)
            self.estimate_rows[estimator_id] = row

    def _start_sequence(self):
        self.selected_algorithm_ids = [k for k, v in self.algorithm_checks.items() if v.isChecked()]
        self.selected_estimator_ids = [k for k, v in self.estimator_checks.items() if v.isChecked()]
        if not self.selected_algorithm_ids:
            QMessageBox.warning(self, "선택 오류", "최소 하나의 알고리즘을 선택해야 합니다.")
            return
        if not self.selected_estimator_ids:
            QMessageBox.warning(self, "선택 오류", "최소 하나의 시간 예측 방법을 선택해야 합니다.")
            return
        self.results = []
        self.algorithm_index = 0
        self.stop_after_current = False
        self.visualize = self.step_enabled_check.isChecked()
        self.step_box.setVisible(self.visualize)
        self._create_prediction_rows()
        self.play_button.setEnabled(self.visualize)
        self.next_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.stop_current_button.setEnabled(True)
        self.pages.setCurrentWidget(self.execution_page)
        self._start_next_algorithm()

    def _start_next_algorithm(self):
        if self.algorithm_index >= len(self.selected_algorithm_ids):
            self._show_results()
            return
        aid = self.selected_algorithm_ids[self.algorithm_index]
        self.execution_title.setText(f"실행 중: {AlgorithmRegistry.available()[aid]}")
        self.queue_label.setText(
            f"전체 {len(self.selected_algorithm_ids)}개 중 {self.algorithm_index + 1}번째 알고리즘"
        )
        for key, row in self.estimate_rows.items():
            row.setText(f"{TimeEstimatorRegistry.available()[key]}  |  예측 총시간: 측정 중…  |  남은 시간: 측정 중…")
        self.node_label.setText("현재 탐색 노드: 0번째 (누적 후보 검사)")
        self.node_time_label.setText("평균 노드당 시간: 측정 중…")
        self.solution_label.setText("발견한 해답: 0")
        self.stop_current_button.setEnabled(True)
        self.elapsed_label.setText("실제 경과 시간: 00:00")
        self.step_board.reset(self.size_spin.value())
        self.step_log.clear()
        self.step_label.setText("탐색 단계 이벤트를 기다리는 중…" if self.visualize else "시각화 비활성화 (순수 시간 측정)")
        self.playing = True
        self.play_button.setText("일시정지")
        self.next_button.setEnabled(False)
        self._playback_credit = 0.0
        self._last_step_seq = 0
        try:
            self.controller.start(
                self.size_spin.value(), aid,
                estimator_ids=self.selected_estimator_ids,
                visualize_steps=self.visualize,
            )
        except Exception as exc:
            QMessageBox.critical(self, "실행 오류", f"알고리즘 시작 실패:\n{exc}")
            self.stop_after_current = True
            self._show_results()
            return
        self.timer.start()

    def _consume_step(self) -> bool:
        step = self.controller.take_step()
        if step is None:
            return False
        if step.sequence != self._last_step_seq + 1:
            self.step_log.addItem("이벤트 순서 불일치 감지")
        self._last_step_seq = step.sequence
        presented = StepPresenterRegistry.present(step)
        self.step_board.set_step(step)
        self.step_label.setText(f"Step #{step.sequence:,} [{step.kind}]  {presented.caption}")
        self.step_log.addItem(f"#{step.sequence:,} {presented.caption}")
        if self.step_log.count() > 250:
            self.step_log.takeItem(0)
        self.step_log.scrollToBottom()
        return True

    def _toggle_play(self):
        if not self.visualize:
            return
        self.playing = not self.playing
        self.play_button.setText("일시정지" if self.playing else "자동 재생")
        self.next_button.setEnabled(not self.playing)
        self._playback_credit = 0.0

    def _single_step(self):
        if self.visualize and not self.playing:
            self._consume_step()

    def _update_execution(self):
        if self.visualize and self.playing:
            self._playback_credit += STEP_PLAYBACK_SPEED * self.timer.interval() / 1000.0
            # Process every event in order; the bounded producer queue applies back-pressure.
            nsteps = min(100, int(self._playback_credit))
            for _ in range(nsteps):
                if not self._consume_step():
                    break
                self._playback_credit -= 1
            self._playback_credit = min(self._playback_credit, 1.0)
        snap = self.controller.snapshot()
        if snap is None:
            return
        self.elapsed_label.setText(f"실제 경과 시간: {seconds_text(snap.elapsed_seconds)}")
        self.node_label.setText(f"현재 탐색 노드: {snap.explored_nodes:,}번째 (누적 후보 검사)")
        self.node_time_label.setText(
            f"평균 노드당 시간: {node_time_text(snap.average_node_ms)}"
        )
        self.solution_label.setText(f"발견한 해답: {snap.solution_count:,}")
        names = TimeEstimatorRegistry.available()
        for key, row in self.estimate_rows.items():
            if key in snap.estimator_errors:
                row.setText(f"{names[key]}   |   예측 오류: {snap.estimator_errors[key]}")
            elif snap.estimates.get(key) is not None:
                prediction = snap.estimates[key]
                left = max(0.0, prediction - snap.elapsed_seconds)
                count_prediction = snap.predicted_solutions.get(key)
                extra = f"   |   예측 해답: {count_prediction:,}개" if count_prediction is not None else ""
                note = snap.estimator_notes.get(key)
                suffix = f"   |   {note}" if note else ""
                row.setText(
                    f"{names[key]}   |   예측 총시간: {seconds_text(prediction)}"
                    f"   |   남은 시간: {seconds_text(left)}{extra}{suffix}"
                )
            else:
                note = snap.estimator_notes.get(key)
                if note:
                    row.setText(f"{names[key]}   |   예측 불가: {note}")
                else:
                    row.setText(f"{names[key]}   |   예측 총시간: 측정 중…   |   남은 시간: 측정 중…")

        if not snap.is_running:
            # Drain outstanding steps before advancing; the last board remains visible.
            while self.visualize and self._consume_step():
                pass
            result = self.controller.wait(timeout=0)
            if result is None:
                return
            self.timer.stop()
            self.results.append(result)
            self.algorithm_index += 1
            if self.stop_after_current:
                self._show_results()
            else:
                self._start_next_algorithm()

    def _stop_current_algorithm(self):
        """Cancel only this run; continue with remaining selected algorithms."""
        self.stop_current_button.setEnabled(False)
        self.controller.request_stop()
        self.execution_title.setText("현재 알고리즘 중단 처리 중… (이후 알고리즘 계속)")

    def _stop_sequence(self):
        """Cancel this run and skip every remaining selected algorithm."""
        self.stop_after_current = True
        self.stop_button.setEnabled(False)
        self.stop_current_button.setEnabled(False)
        self.controller.request_stop()
        self.execution_title.setText("전체 실행 중단 처리 중…")

    @staticmethod
    def _status(result):
        if result.error_message:
            return "오류"
        if result.is_cancelled:
            return "중단"
        return "완료" if result.is_complete_result else "미완료"

    def _show_results(self):
        self.timer.stop()
        time_rows, time_entries, pred_rows = [], [], []
        predicted_entries, error_entries, rank_entries = [], [], []
        notes = []
        for result in self.results:
            if result.solution_scope == "fixed_center":
                expected = None  # Standard all-solution totals do not apply.
                reference_label = "중앙 고정 조건"
                coverage = 100.0 if result.is_complete_result else None
            else:
                expected = TOTAL_SOLUTIONS.get(result.board_size)
                reference_label = f"{expected:,}" if expected is not None else "미확인"
                coverage = solution_coverage(
                    result.board_size, result.solution_count, complete=result.is_complete_result
                )
            average = result.average_node_ms
            time_rows.append([
                result.algorithm_name, self._status(result),
                (f"{result.elapsed_seconds:.6f}", result.elapsed_seconds),
                (f"{result.explored_nodes:,}", result.explored_nodes),
                ("미측정" if average is None else f"{average:.6f}", average),
                (f"{result.nodes_per_second:,.1f}", result.nodes_per_second),
                (f"{result.solution_count:,}", result.solution_count),
                (reference_label, expected),
                ("-" if coverage is None else f"{coverage:.2f}%", coverage),
            ])
            time_entries.append(ChartEntry(
                label=result.algorithm_name, value=result.elapsed_seconds,
                annotation=f"{result.elapsed_seconds:.4f}초",
                partial=not result.is_complete_result,
                fields={
                    "algorithm": result.algorithm_name,
                    "elapsed": result.elapsed_seconds,
                    "nodes": result.explored_nodes,
                    "average_ms": average,
                },
            ))
            if result.error_message:
                notes.append(f"{result.algorithm_name}: {result.error_message}")
            if result.history_error:
                notes.append(f"{result.algorithm_name} JSON 저장 실패: {result.history_error}")

            ranks = ResultComparator.estimation_ranks(result)
            for eid in self.selected_estimator_ids:
                metric = result.time_estimates.get(eid)
                if metric is None:
                    continue
                if metric.error_message:
                    status = "예측기 오류"
                elif not result.is_complete_result:
                    status = "전체 탐색 미완료"
                elif metric.predicted_seconds is None:
                    status = "예측 정보 부족"
                else:
                    status = "측정 완료"
                rank = ranks.get(eid)
                pred_rows.append([
                    result.algorithm_name, metric.estimator_name,
                    ("-" if metric.prediction_at_seconds is None else f"{metric.prediction_at_seconds:.4f}",
                     metric.prediction_at_seconds),
                    ("미측정" if metric.predicted_seconds is None else f"{metric.predicted_seconds:.4f}",
                     metric.predicted_seconds),
                    ("-" if metric.predicted_solutions is None else f"{metric.predicted_solutions:,}", metric.predicted_solutions),
                    ("-" if metric.solution_error_percent is None else f"{metric.solution_error_percent:.2f}%", metric.solution_error_percent),
                    (f"{result.elapsed_seconds:.4f}", result.elapsed_seconds),
                    ("-" if metric.error_percent is None else f"{metric.error_percent:.2f}%",
                     metric.error_percent),
                    ("-" if rank is None else str(rank), rank), status,
                    metric.prediction_note or "-",
                ])
                label = f"{result.algorithm_name} · {metric.estimator_name}"
                fields = {
                    "algorithm_id": result.algorithm_id,
                    "algorithm": result.algorithm_name,
                    "estimator": metric.estimator_name,
                    "predicted": metric.predicted_seconds,
                    "actual": result.elapsed_seconds,
                    "error": metric.error_percent,
                    "rank": rank,
                }
                incomplete = not result.is_complete_result
                predicted_entries.append(ChartEntry(
                    label, metric.predicted_seconds,
                    "미측정" if metric.predicted_seconds is None else f"{metric.predicted_seconds:.4f}초",
                    fields, partial=incomplete,
                ))
                error_entries.append(ChartEntry(
                    label, metric.error_percent,
                    "미측정" if metric.error_percent is None else f"{metric.error_percent:.2f}%",
                    fields, partial=incomplete,
                ))
                rank_entries.append(ChartEntry(
                    label, rank,
                    "미측정" if rank is None else f"{rank}위",
                    fields, partial=incomplete,
                ))
                if metric.error_message:
                    notes.append(f"{result.algorithm_name} / {metric.estimator_name}: {metric.error_message}")

        # Initial tables are ordered by useful values; clicking column headings re-sorts.
        time_rows.sort(key=lambda row: (row[1] != "완료", row[2][1]))
        pred_rows.sort(key=lambda row: (
            row[7][1] is None,
            float('inf') if row[7][1] is None else row[7][1],
            row[0], row[1],
        ))
        self._fill_table(self.result_table, time_rows)
        self.time_chart.set_entries(time_entries)
        self._fill_table(self.estimation_table, pred_rows)
        self._prediction_chart_entries = {
            "predicted_time_chart": predicted_entries,
            "error_chart": error_entries,
            "rank_chart": rank_entries,
        }
        self._rebuild_prediction_filters()
        self._update_filtered_prediction_charts()
        self.result_note.setText(
            "중앙 고정 알고리즘은 퀸 한 개를 중앙(짝수 N은 0부터 세어 (N//2,N//2) 칸)에 고정하므로 전체 해답 수와 직접 비교할 수 없습니다. "
            "완료된 중앙 고정 실행의 100%는 해당 조건의 탐색 완료를 의미합니다. "
            "일반 DFS/BFS는 후보 위치 검사 횟수를, 비트마스크 DFS는 허용된 비트 후보 수를 노드로 집계합니다. "
            "노드당 평균 시간 = 전체 실제 경과 시간 ÷ 누적 탐색 노드 수(시각화 대기 시간 포함). "
            "차트 상단 필드를 클릭해 정렬할 수 있고, 미완료 실행·미측정 결과는 뒤로 배치합니다. "
            "시간 예측은 최초 유효 값을 고정해 비교합니다. 공정한 성능 비교에는 단계 시각화를 끄세요. "
            "정답이 0개인 N=2, 3은 완전 탐색 시 발견률 100%로 표시합니다. "
            "실행 기록은 각 알고리즘별로 data/history/ 아래에 별도 JSON 파일로 보관하며, "
            "과거 기울기 예측은 동일 알고리즘에서 더 작은 서로 다른 N 두 종류가 필요합니다."
            + ("\n오류: " + " | ".join(notes) if notes else "")
        )
        self.pages.setCurrentWidget(self.result_page)

    def closeEvent(self, event):
        if self.controller.snapshot() and self.controller.snapshot().is_running:
            self.controller.request_stop()
        super().closeEvent(event)
