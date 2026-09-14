"""Quiet graph-paper surface for the text workspace."""
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame
from .theme import PAPER, GRID


class GridPanel(QFrame):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(PAPER))
        painter.setPen(QColor(GRID))
        for x in range(0, self.width(), 40):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 40):
            painter.drawLine(0, y, self.width(), y)
        painter.end()
