from html import escape
from math import ceil

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QTextBrowser, QToolButton,
                               QVBoxLayout, QWidget)

from ..models.sentence import Sentence
from .theme import ACCENT, ACTIVE_WORD, HOVER_WORD, INK, MUTED


class WordBrowser(QTextBrowser):
    """A wrapping, height-aware word surface with no nested scroll bars."""

    word_entered = Signal(int)
    word_left = Signal(int)
    word_clicked = Signal(int)
    word_double_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # QTextBrowser lays its document at the top of any spare height. Keep
        # the widget exactly as tall as its text so the row layout can center
        # the actual sentence, rather than an invisible empty area below it.
        self.document().setDocumentMargin(0)
        self._hover_index: int | None = None
        self._pending_click_index: int | None = None
        self._ignore_release_after_double_click = False
        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.timeout.connect(self._emit_pending_single_click)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.document().documentLayout().documentSizeChanged.connect(lambda _size: self._schedule_height())

    def eventFilter(self, watched, event):
        if watched is self.viewport() and event.type() == QEvent.MouseButtonDblClick:
            index = self._word_index_at(event.position().toPoint())
            if index is not None:
                self._single_click_timer.stop()
                self._pending_click_index = None
                self._ignore_release_after_double_click = True
                self.word_double_clicked.emit(index)
                return True
        elif watched is self.viewport() and event.type() == QEvent.MouseButtonRelease:
            if event.button() != Qt.LeftButton:
                return super().eventFilter(watched, event)
            if self._ignore_release_after_double_click:
                self._ignore_release_after_double_click = False
                return True
            index = self._word_index_at(event.position().toPoint())
            if index is not None:
                # Wait for the system double-click interval. If a second click
                # arrives, only the sentence action is emitted; otherwise this
                # becomes a normal single-word click.
                self._pending_click_index = index
                interval = QApplication.instance().doubleClickInterval()
                self._single_click_timer.start(interval)
                return True
        elif watched is self.viewport() and event.type() == QEvent.MouseMove:
            anchor = self.anchorAt(event.position().toPoint())
            try:
                index = int(anchor) if anchor else None
            except ValueError:
                index = None
            if index != self._hover_index:
                previous = self._hover_index
                self._hover_index = index
                if previous is not None:
                    self.word_left.emit(previous)
                if index is not None:
                    self.word_entered.emit(index)
        elif watched is self.viewport() and event.type() == QEvent.Leave:
            if self._hover_index is not None:
                previous = self._hover_index
                self._hover_index = None
                self.word_left.emit(previous)
        return super().eventFilter(watched, event)

    def _word_index_at(self, point) -> int | None:
        anchor = self.anchorAt(point)
        try:
            return int(anchor) if anchor else None
        except ValueError:
            return None

    def _emit_pending_single_click(self):
        index = self._pending_click_index
        self._pending_click_index = None
        if index is not None:
            self.word_clicked.emit(index)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_height()

    def _schedule_height(self):
        QTimer.singleShot(0, self._fit_height)

    def _fit_height(self):
        width = max(120, self.viewport().width())
        self.document().setTextWidth(width)
        self.setFixedHeight(max(1, ceil(self.document().size().height())))


class SentenceCard(QFrame):
    play_requested = Signal(object, int)
    word_clicked = Signal(object, int)
    word_hovered = Signal(object, int)
    word_hover_left = Signal(object, int)

    def __init__(self, sentence: Sentence, parent=None):
        super().__init__(parent)
        self.sentence = sentence
        self.words = sentence.french.split()
        self.selected_index = 0
        self.active_index: int | None = None
        self.hover_index: int | None = None
        self._last_hover_index = None
        self.setObjectName("sentenceCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.details_toggle = QToolButton()
        self.details_toggle.setObjectName("sentenceToggle")
        self.details_toggle.setArrowType(Qt.NoArrow)
        self.details_toggle.setText("▶")
        self.details_toggle.setCheckable(True)
        self.details_toggle.setFixedSize(36, 44)
        self.details_toggle.setAccessibleName("Show IPA and meaning")
        self.details_toggle.setToolTip("Show IPA and meaning")
        self.details_toggle.toggled.connect(self._toggle_details)

        self.play_button = QPushButton("▶")
        self.play_button.setObjectName("sentencePlay")
        self.play_button.setFixedSize(36, 36)
        self.play_button.setAccessibleName("Play sentence")
        self.play_button.setToolTip("Play this sentence from the selected word")
        self.play_button.clicked.connect(
            lambda: self.play_requested.emit(self, self.selected_index)
        )
        self.title = WordBrowser()
        self.title.setObjectName("sentenceWords")
        self._render_words()
        self.title.word_entered.connect(self._hover_word)
        self.title.word_left.connect(self._leave_word)
        self.title.anchorClicked.connect(self._select_start_word)
        self.title.word_clicked.connect(self._select_start_word_index)
        self.title.word_double_clicked.connect(self._play_from_double_clicked_word)
        self.ipa = QLabel(sentence.ipa)
        self.ipa.setWordWrap(True)
        self.ipa.setStyleSheet(f"color: {MUTED};")
        self.translation = QLabel(sentence.translation)
        self.translation.setWordWrap(True)
        self.details = QWidget()
        self.details.setObjectName("sentenceDetails")
        details_layout = QVBoxLayout(self.details)
        details_layout.setContentsMargins(42, 0, 52, 8)
        details_layout.setSpacing(4)
        details_layout.addWidget(self.ipa)
        details_layout.addWidget(self.translation)
        self.details.hide()
        self.top_row = QHBoxLayout()
        self.top_row.setContentsMargins(4, 18, 4, 18)
        self.top_row.setSpacing(8)
        self.top_row.setAlignment(Qt.AlignVCenter)
        self.top_row.addWidget(self.details_toggle, 0, Qt.AlignVCenter)
        self.top_row.addWidget(self.title, 1, Qt.AlignVCenter)
        self.cache_badge = QLabel("● CACHED")
        self.cache_badge.setObjectName("cacheBadge")
        self.cache_badge.hide()
        self.top_row.addWidget(self.cache_badge, 0, Qt.AlignVCenter)
        self.top_row.addWidget(self.play_button, 0, Qt.AlignVCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignTop)
        layout.addLayout(self.top_row)
        layout.addWidget(self.details)

    def text_from(self, index: int = 0) -> str:
        return " ".join(self.words[max(0, index):])

    def set_active_word(self, index: int | None):
        if index == self.active_index:
            return
        self.active_index = index
        self._render_words()

    @property
    def highlight_index(self) -> int | None:
        return self.hover_index if self.hover_index is not None else self.active_index

    def set_playback_state(self, state: str):
        labels = {
            "playing": "❚❚",
            "paused": "▶",
            "loading": "…",
            "idle": "▶",
        }
        accessible_names = {
            "playing": "Pause sentence",
            "paused": "Resume sentence",
            "loading": "Preparing sentence audio",
            "idle": "Play sentence",
        }
        self.play_button.setText(labels.get(state, labels["idle"]))
        self.play_button.setAccessibleName(accessible_names.get(state, accessible_names["idle"]))
        self.play_button.setToolTip(accessible_names.get(state, accessible_names["idle"]))
        self.play_button.setEnabled(state != "loading")
        self.play_button.setProperty("playbackState", state)
        self.setProperty("playbackState", state)
        self.play_button.style().unpolish(self.play_button)
        self.play_button.style().polish(self.play_button)
        self.style().unpolish(self)
        self.style().polish(self)

    def _render_words(self):
        linked_words = []
        for index, word in enumerate(self.words):
            style = self._word_style(index)
            linked_words.append(
                f'<a href="{index}" title="Repeat this word while hovering" '
                f'style="{style}text-decoration:none;">{escape(word)}</a>'
            )
        self.title.setHtml(
            f'<div style="margin:0;padding:0;font-size:16px;font-weight:600;'
            f'color:{INK};line-height:145%;">'
            f'{" ".join(linked_words)}</div>'
        )

    def _word_style(self, index: int) -> str:
        is_speaking = index == self.active_index
        is_hovered = index == self.hover_index
        if is_hovered:
            return f"background-color:{HOVER_WORD};color:{INK};font-weight:700;"
        # Hover repetition temporarily owns the visual focus. Keep tracking
        # the sentence internally, but hide its blue highlight until hover ends.
        if is_speaking and self.hover_index is None:
            return f"background-color:{ACTIVE_WORD};color:{INK};font-weight:700;"
        return f"color:{INK};"

    def _hover_word(self, index: int):
        if 0 <= index < len(self.words):
            self.hover_index = index
            self._last_hover_index = index
            self._render_words()
            self.word_hovered.emit(self, index)

    def _leave_word(self, index: int):
        if self.hover_index == index:
            self.hover_index = None
            self._render_words()
        self.word_hover_left.emit(self, index)
        self._last_hover_index = None

    def _toggle_details(self, checked: bool):
        self.details.setVisible(checked)
        self.details_toggle.setText("▼" if checked else "▶")
        label = "Hide IPA and meaning" if checked else "Show IPA and meaning"
        self.details_toggle.setAccessibleName(label)
        self.details_toggle.setToolTip(label)

    def _select_start_word(self, url):
        """Set the next click-to-play start point without navigating the document."""
        try:
            raw = url.toString() if hasattr(url, "toString") else str(url)
            if not raw:
                return
            index = int(raw)
            if index < 0 or index >= len(self.words):
                return
            self._select_start_word_index(index)
        except (ValueError, IndexError):
            pass

    def _select_start_word_index(self, index: int):
        if 0 <= index < len(self.words):
            self.selected_index = index
            self.word_clicked.emit(self, index)

    def _play_from_double_clicked_word(self, index: int):
        """Double-click starts the whole sentence at this word."""
        if 0 <= index < len(self.words):
            self.selected_index = index
            self.play_requested.emit(self, index)
