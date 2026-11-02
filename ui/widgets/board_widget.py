from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget


class BoardWidget(QWidget):
    """Paint one N-Queens solution without coupling the algorithm to Qt."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.positions: tuple[int, ...] | None = None
        self.setMinimumSize(320, 320)

    def set_solution(self, solution):
        self.positions = solution.positions if solution is not None else None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.contentsRect().adjusted(8, 8, -8, -8)
        if not self.positions:
            painter.setPen(Qt.GlobalColor.gray)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "표시할 해답이 없습니다.")
            return

        n = len(self.positions)
        cell = min(rect.width(), rect.height()) / n
        board_w = cell * n
        board_h = cell * n
        left = rect.center().x() - board_w / 2
        top = rect.center().y() - board_h / 2
        for row in range(n):
            for col in range(n):
                color = QColor("#F0D9B5") if (row + col) % 2 == 0 else QColor("#B58863")
                x, y = left + col * cell, top + row * cell
                painter.fillRect(int(x), int(y), int(cell + 1), int(cell + 1), color)
                if self.positions[col] == row:
                    painter.setPen(QPen(QColor("#202020"), max(1, cell * 0.04)))
                    painter.setFont(QFont("Arial", max(8, int(cell * 0.68)), QFont.Weight.Bold))
                    painter.drawText(int(x), int(y), int(cell), int(cell),
                                     Qt.AlignmentFlag.AlignCenter, "♛")
