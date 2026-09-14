"""Listening history, styled to match the editorial desktop workbench."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)
from .theme import PAPER, INK, MUTED, RULE, COBALT, DISPLAY


class HistoryDialog(QDialog):
    passage_selected = Signal(str)

    def __init__(self, passages, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Listening History")
        self.resize(900, 500)
        if parent and parent.screen():
            available = parent.screen().availableGeometry()
            self.resize(min(900, available.width() - 40), min(500, available.height() - 60))
        self.setObjectName("listeningHistory")
        self.setStyleSheet(f"""
            QDialog#listeningHistory {{ background: {PAPER}; color: {INK}; }}
            QLabel {{ color: {INK}; background: transparent; }}
            QLabel#historyEyebrow {{ color: {MUTED}; font-size: 13px; }}
            QLabel#historyTitle {{ font-family: {DISPLAY}; font-size: 48px; }}
            QLabel#historyIntro {{ color: {MUTED}; font-size: 18px; }}
            QWidget#historySummary {{ border-top: 1px solid {RULE}; border-bottom: 1px solid {RULE}; }}
            QLabel#historyCount {{ font-size: 18px; font-weight: 700; }}
            QPushButton {{ border: 0; padding: 10px; background: transparent; color: {COBALT}; }}
            QPushButton:hover {{ background: {RULE}; }}
            QPushButton:pressed {{ background: {PAPER}; }}
            QPushButton:focus {{ border: 1px solid {COBALT}; }}
            QPushButton#historyPassage {{ color: {INK}; text-align: left; font-size: 17px; }}
            QWidget#historyRow {{ border-bottom: 1px solid {RULE}; }}
            QScrollArea {{ border: 0; background: transparent; }}
            QWidget#historyRows {{ background: {PAPER}; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        layout.addWidget(QLabel("RECENT TEXT", objectName="historyEyebrow"))
        heading = QHBoxLayout()
        title = QLabel("Listening History", objectName="historyTitle")
        title.setWordWrap(True)
        heading.addWidget(title, 1)
        close = QPushButton("×")
        close.setAccessibleName("Close listening history")
        close.setFixedSize(44, 44)
        close.clicked.connect(self.reject)
        heading.addWidget(close, 0, Qt.AlignTop)
        layout.addLayout(heading)
        intro = QLabel(
            "Your latest 20 prepared passages stay on this computer. "
            "Select one to return it to the editor.", objectName="historyIntro",
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        summary = QWidget(objectName="historySummary")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(0, 16, 0, 16)
        summary_layout.addWidget(QLabel("Saved Passages"))
        self.count_label = QLabel(f"{len(passages)} / 20", objectName="historyCount")
        summary_layout.addWidget(self.count_label, 0, Qt.AlignRight)
        layout.addWidget(summary)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        rows = QWidget(objectName="historyRows")
        row_layout = QVBoxLayout(rows)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        row_layout.setAlignment(Qt.AlignTop)
        for text, _created_at in passages:
            row = QWidget(objectName="historyRow")
            contents = QHBoxLayout(row)
            contents.setContentsMargins(0, 8, 0, 8)
            passage = ElidedPassage(" ".join(text.split()))
            passage.setToolTip(text)
            passage.setAccessibleName(text)
            passage.clicked.connect(lambda _checked=False, value=text: self.restore(value))
            restore = QPushButton("RESTORE")
            restore.setAccessibleName("Restore passage: " + " ".join(text.split())[:80])
            restore.clicked.connect(lambda _checked=False, value=text: self.restore(value))
            contents.addWidget(passage, 1)
            contents.addWidget(restore)
            row_layout.addWidget(row)
        if not passages:
            empty = QLabel("No saved passages yet. Prepare listening to save your first text.")
            empty.setWordWrap(True)
            row_layout.addWidget(empty)
        scroll.setWidget(rows)
        layout.addWidget(scroll, 1)

    def restore(self, text):
        self.passage_selected.emit(text)
        self.accept()


class ElidedPassage(QPushButton):
    def __init__(self, text):
        super().__init__()
        self.full_text = text
        self.setObjectName("historyPassage")
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setMinimumWidth(0)
        self.setMinimumHeight(48)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setText(self.fontMetrics().elidedText(
            self.full_text, Qt.ElideRight, max(0, self.width() - 24),
        ))
