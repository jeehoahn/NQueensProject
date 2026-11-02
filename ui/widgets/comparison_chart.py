"""Small built-in Qt horizontal bar chart; no plotting dependency required."""

from dataclasses import dataclass

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget, QScrollArea, QFrame


@dataclass(frozen=True)
class BarItem:
    label: str
    value: float | None
    annotation: str
    # Optional distinction between completed / incomplete runs.
    partial: bool = False


class ComparisonChart(QWidget):
    """Draw labelled bars. None values are shown as '미측정'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: list[BarItem] = []
        self.setMinimumHeight(150)
        self.setFixedWidth(1500)  # Default chart width exceeds the usual result viewport.

    def set_items(self, items: list[BarItem]) -> None:
        self.items = items
        self.setFixedHeight(max(150, 30 + 39 * len(items)))
        fm = QFontMetrics(self.font())
        longest_label = max((fm.horizontalAdvance(item.label) for item in items), default=0)
        self.setFixedWidth(max(1500, min(longest_label + 850, 2400)))
        self.updateGeometry()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().base())

        if not self.items:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "표시할 실행 결과가 없습니다.")
            return

        fm = QFontMetrics(painter.font())
        left_margin = min(650, max(280, max(fm.horizontalAdvance(item.label) for item in self.items) + 24))
        right_margin = 150
        chart_width = max(20, self.width() - left_margin - right_margin - 15)
        max_value = max((item.value or 0.0 for item in self.items), default=0.0)
        scale = max(max_value, 1e-9)

        for idx, item in enumerate(self.items):
            top = 17 + idx * 39
            baseline = top + 13
            label = fm.elidedText(item.label, Qt.TextElideMode.ElideRight, left_margin - 24)
            painter.setPen(self.palette().text().color())
            painter.drawText(10, baseline + 4, label)

            painter.fillRect(QRectF(left_margin, top, chart_width, 21), QColor("#E9EDF2"))
            if item.value is not None:
                bar_w = chart_width * min(max(0.0, item.value) / scale, 1.0)
                bar_color = QColor("#94A3B8") if item.partial else QColor("#2878C8")
                painter.fillRect(QRectF(left_margin, top, bar_w, 21), bar_color)

            painter.setPen(QPen(self.palette().text().color()))
            annotation = fm.elidedText(item.annotation, Qt.TextElideMode.ElideRight, right_margin - 8)
            painter.drawText(left_margin + chart_width + 8, baseline + 4, annotation)
        painter.end()


class SortableComparisonChart(QWidget):
    """Horizontal bars with clickable field headers and ascending/descending sorting."""

    def __init__(self, columns: list[tuple[str, str]], default_sort: str, parent=None):
        from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QLabel
        from analysis.chart_sort import sort_chart_entries

        super().__init__(parent)
        self._sort_entries = sort_chart_entries
        self.columns = columns
        self.sort_key = default_sort
        self.descending = False  # Default: best (smaller duration/error/rank) first.
        self.entries = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        self.sort_buttons = {}
        for field, label in columns:
            button = QPushButton(label)
            button.setToolTip(f"'{label}'을 기준으로 정렬 (재클릭 시 오름차순/내림차순 전환)")
            button.clicked.connect(lambda checked=False, key=field: self.sort_by(key))
            self.sort_buttons[field] = button
            header.addWidget(button)
        outer.addLayout(header)
        # QScrollArea needs a NON-resizable child that can be wider than the
        # viewport; otherwise Qt shrinks the chart and no horizontal bar appears.
        self.chart = ComparisonChart()
        self.chart_scroll = QScrollArea(self)
        self.chart_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chart_scroll.setWidgetResizable(False)
        self.chart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.chart_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chart_scroll.setWidget(self.chart)
        self.chart_scroll.setFixedHeight(self.chart.minimumHeight() + 22)
        self.chart_scroll.setToolTip('아래 가로 스크롤 막대를 움직여 그래프 좌우 이동')
        outer.addWidget(self.chart_scroll)
        self._update_headers()

    def set_entries(self, entries) -> None:
        self.entries = list(entries)
        self._refresh()

    def sort_by(self, field: str) -> None:
        if field not in self.sort_buttons:
            raise KeyError(field)
        if field == self.sort_key:
            self.descending = not self.descending
        else:
            self.sort_key = field
            self.descending = False
        self._refresh()

    def _update_headers(self) -> None:
        for field, name in self.columns:
            arrow = (' ▼' if self.descending else ' ▲') if field == self.sort_key else ''
            self.sort_buttons[field].setText(name + arrow)

    def _refresh(self) -> None:
        ordered = self._sort_entries(self.entries, self.sort_key, self.descending)
        self.chart.set_items([
            BarItem(row.label, row.value, row.annotation, partial=row.partial)
            for row in ordered
        ])
        # Resize only content height, never make the area shrink chart width.
        self.chart_scroll.setFixedHeight(self.chart.height() + 22)
        self._update_headers()
