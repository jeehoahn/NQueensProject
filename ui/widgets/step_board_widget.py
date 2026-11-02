"""Generic N×N painter: events are interpreted by a separate presenter."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from algorithms.steps import SearchStep
from visualization.registry import StepPresenterRegistry
import visualization.backtracking  # noqa: F401


class StepBoardWidget(QWidget):
    ACCENTS = {
        "neutral": QColor("#64748b"), "blue": QColor("#2563eb"),
        "red": QColor("#dc2626"), "green": QColor("#16a34a"),
        "gold": QColor("#ca8a04"), "orange": QColor("#ea580c"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.n = 8
        self.step: SearchStep | None = None
        self.setMinimumSize(260, 260)

    def reset(self, n: int):
        self.n = n
        self.step = None
        self.update()

    def set_step(self, step: SearchStep):
        self.n = len(step.positions)
        self.step = step
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().base())
        size = max(1, min(self.width(), self.height()) - 18)
        cell = size / self.n
        x0 = (self.width() - size) / 2
        y0 = (self.height() - size) / 2
        step = self.step
        color = self.ACCENTS[StepPresenterRegistry.present(step).accent] if step else self.ACCENTS["neutral"]
        focus = (step.column, step.row) if step else (None, None)
        for c in range(self.n):
            for r in range(self.n):
                rect = QRectF(x0 + c * cell, y0 + r * cell, cell, cell)
                bg = QColor("#e2e8f0") if (r + c) % 2 == 0 else QColor("#94a3b8")
                painter.fillRect(rect, bg)
                if (c, r) == focus:
                    painter.fillRect(rect, QColor(color.red(), color.green(), color.blue(), 115))
        painter.setPen(QPen(QColor("#0f172a")))
        if step:
            font = QFont(painter.font())
            font.setBold(True)
            font.setPixelSize(max(7, min(38, int(cell * 0.75))))
            painter.setFont(font)
            for c, r in enumerate(step.positions):
                if r >= 0:
                    rect = QRectF(x0 + c * cell, y0 + r * cell, cell, cell)
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "♛")
        painter.end()
