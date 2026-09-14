# Hallmark · pre-emit critique: P5 H5 E5 S5 R5 V4
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QBoxLayout, QComboBox, QFrame, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QMainWindow, QPushButton,
                               QScrollArea, QSplitter, QSizePolicy, QTextEdit, QMessageBox,
                               QVBoxLayout, QWidget)

from ..models.sentence import Sentence
from ..services.audio_cache import AudioCache
from ..services.history import HistoryStore
from ..services.paths import app_data_dir
from ..services.sentence_splitter import split_sentences
from ..services.settings import SettingsStore
from ..services.tts import OnlineTTSEngine, PiperEngine, SupertonicEngine, SystemEngine, TTSResult
from .sentence_card import SentenceCard
from .settings_dialog import SettingsDialog
from .theme import APP_STYLESHEET
from .grid_panel import GridPanel


class SynthesisSignals(QObject):
    finished = Signal(int, object, str, bool, str, object, int)


class SynthesisWorker(QRunnable):
    def __init__(self, request_id, engine, text, speed, cache_path, continuing, source, card, start_word):
        super().__init__()
        self.request_id = request_id
        self.engine = engine
        self.text = text
        self.speed = speed
        self.cache_path = cache_path
        self.continuing = continuing
        self.source = source
        self.card = card
        self.start_word = start_word
        self.signals = SynthesisSignals()

    @Slot()
    def run(self):
        try:
            result = self.engine.synthesize(self.text, self.speed, self.cache_path)
        except Exception as exc:
            result = TTSResult(message=f"Audio generation failed: {exc}")
        self.signals.finished.emit(
            self.request_id, result, self.text, self.continuing, self.source,
            self.card, self.start_word
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Moshi French TTS")
        self.resize(1440, 900)
        data_dir = app_data_dir()
        self.settings_store = SettingsStore(data_dir)
        self.settings = self.settings_store.load()
        self.history = HistoryStore(data_dir)
        self.cache = AudioCache(data_dir)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.playbackStateChanged.connect(self._on_playback_state)
        self.player.positionChanged.connect(self._update_word_highlight)
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(2)
        self._workers: dict[int, SynthesisWorker] = {}
        self._request_id = 0
        self._preparing = False
        self._preparing_card: SentenceCard | None = None
        self._hover_worker_active = False
        self._pending_hover: tuple[SentenceCard, int, bool] | None = None
        self._hovered_word: tuple[SentenceCard, int, bool] | None = None
        self._active_source = ""
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(180)
        self.hover_timer.timeout.connect(self._perform_hover_jump)
        self.hover_leave_timer = QTimer(self)
        self.hover_leave_timer.setSingleShot(True)
        self.hover_leave_timer.setInterval(90)
        self.hover_leave_timer.timeout.connect(self._continue_after_hover)
        self.play_queue: list[SentenceCard] = []
        self.current_sentences: list[str] = []
        self.current_cards: list[SentenceCard] = []
        self.active_card: SentenceCard | None = None
        self.active_start_word = 0
        self._layout_mode = ""
        self._close_to_tray = False
        self._build_ui()

    def set_close_to_tray(self, enabled: bool):
        self._close_to_tray = enabled

    def closeEvent(self, event):
        if self._close_to_tray:
            event.ignore()
            self.hide()
            return
        super().closeEvent(event)

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("appRoot")
        root.setStyleSheet(APP_STYLESHEET)
        layout = QVBoxLayout(root)
        self.root_layout = layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header_layout = QBoxLayout(QBoxLayout.LeftToRight)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        heading = QLabel("∿  Moshi French TTS")
        heading.setObjectName("brandTitle")
        heading.setWordWrap(True)
        subtitle = QLabel("Turn a passage into focused, sentence-by-sentence audio.")
        subtitle.setObjectName("brandSubtitle")
        subtitle.setWordWrap(True)
        title_stack.addWidget(heading)
        subtitle.hide()
        self.settings_button = QPushButton("Voice models")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setToolTip("Configure local voices and playback defaults")
        self.settings_button.clicked.connect(self.open_settings)
        self.header_layout.addLayout(title_stack, 1)
        self.header_layout.setContentsMargins(20, 16, 20, 16)
        guide = QPushButton("Guide")
        guide.clicked.connect(self.show_guide)
        history_button = QPushButton("History")
        history_button.clicked.connect(self.show_history)
        self.header_layout.addWidget(guide)
        self.header_layout.addWidget(history_button)
        self.header_layout.addWidget(self.settings_button, 0, Qt.AlignTop)
        layout.addLayout(self.header_layout)

        self.workspace = QSplitter(Qt.Horizontal)
        self.workspace.setChildrenCollapsible(False)

        self.input_panel = GridPanel()
        self.input_panel.setObjectName("workspacePanel")
        input_layout = QVBoxLayout(self.input_panel)
        input_layout.setContentsMargins(18, 18, 18, 18)
        input_layout.setSpacing(10)
        input_label = QLabel("01 · TEXT")
        input_label.setObjectName("sectionLabel")
        input_title = QLabel("What would you\nlike to hear?")
        input_title.setObjectName("inputTitle")
        input_title.setWordWrap(True)
        input_layout.addWidget(input_label)
        input_layout.addWidget(input_title)
        input_note = QLabel("Paste French text. Practise at your own pace.")
        input_note.setWordWrap(True)
        input_note.setObjectName("helperText")
        input_layout.addWidget(input_note)
        input_layout.addWidget(QLabel("French Text"))
        self.input = QTextEdit()
        self.input.setPlaceholderText("Bonjour ! Collez un texte français ici…")
        self.input.setMinimumHeight(180)
        self.input.textChanged.connect(self._update_input_stats)
        input_layout.addWidget(self.input, 1)
        self.input_stats = QLabel("0 characters")
        self.input_stats.setObjectName("inputStats")
        input_layout.addWidget(self.input_stats)
        process = QPushButton("♫  Prepare listening")
        process.setObjectName("primaryButton")
        process.setToolTip("Split the French text into listening cards")
        process.clicked.connect(self.process_text)
        input_layout.addWidget(process)
        clear_row = QHBoxLayout()
        clear_form = QPushButton("Clear form")
        clear_form.clicked.connect(self.clear_form)
        clear_cache = QPushButton("Clear cache")
        clear_cache.clicked.connect(self.clear_audio_cache)
        clear_row.addWidget(clear_form)
        clear_row.addWidget(clear_cache)
        input_layout.addLayout(clear_row)
        history_label = QLabel("RECENT TEXTS")
        history_label.setObjectName("sectionLabel")
        history_label.hide()
        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.setMaximumHeight(140)
        self.history_list.setToolTip("Choose a saved text to put it back in the editor")
        self.history_list.itemClicked.connect(self.restore_history_item)
        self.history_list.hide()
        self.refresh_history()

        self.audio_panel = QFrame()
        self.audio_panel.setObjectName("workspacePanel")
        audio_layout = QVBoxLayout(self.audio_panel)
        audio_layout.setContentsMargins(18, 18, 18, 18)
        audio_layout.setSpacing(10)
        audio_label = QLabel("02 · LISTEN")
        audio_label.setObjectName("sectionLabel")
        audio_title = QLabel("Sentence Practice")
        audio_title.setObjectName("panelTitle")
        audio_title.setWordWrap(True)
        audio_layout.addWidget(audio_label)
        audio_layout.addWidget(audio_title)
        self.sentence_summary = QLabel("0 sentence cards · 0 different sentences")
        self.sentence_summary.setObjectName("inputStats")
        self.sentence_summary.setToolTip(
            "Number of sentence cards and distinct sentences in the current practice set"
        )
        audio_layout.addWidget(self.sentence_summary)

        self.controls_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.controls_layout.setSpacing(10)
        self.engine = QComboBox()
        self.engine.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.engine.setMinimumHeight(44)
        self.engine.addItems([SystemEngine.name, PiperEngine.name, SupertonicEngine.name, OnlineTTSEngine.name])
        self.engine.setCurrentText(self.settings.engine)
        self.engine.setToolTip("Choose the voice engine")
        self.engine.currentTextChanged.connect(self._on_engine_changed)
        self.voice = QComboBox()
        self.voice.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.voice.setMinimumHeight(44)
        self.voice.setToolTip("Choose a voice for this engine")
        self.voice.currentTextChanged.connect(self._save_selection)
        self.speed = QComboBox()
        self.speed.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.speed.setMinimumHeight(44)
        for value in (0.5, 0.75, 1.0, 1.25, 1.5):
            self.speed.addItem(f"{value:g}×", value)
        index = self.speed.findData(self.settings.speed)
        self.speed.setCurrentIndex(index if index >= 0 else 1)
        self.speed.setToolTip("Choose the speech speed")
        self.speed.currentIndexChanged.connect(self._save_selection)
        self.engine_label = QLabel("Voice engine")
        self.voice_label = QLabel("Voice")
        self.speed_label = QLabel("Speed")
        engine_container = QWidget()
        engine_container.setMinimumHeight(66)
        engine_group = QVBoxLayout(engine_container)
        engine_group.setContentsMargins(0, 0, 0, 0)
        engine_group.setSpacing(5)
        engine_group.addWidget(self.engine_label)
        engine_group.addWidget(self.engine)
        voice_container = QWidget()
        voice_container.setMinimumHeight(66)
        voice_group = QVBoxLayout(voice_container)
        voice_group.setContentsMargins(0, 0, 0, 0)
        voice_group.setSpacing(5)
        voice_group.addWidget(self.voice_label)
        voice_group.addWidget(self.voice)
        speed_container = QWidget()
        speed_container.setMinimumHeight(66)
        speed_group = QVBoxLayout(speed_container)
        speed_group.setContentsMargins(0, 0, 0, 0)
        speed_group.setSpacing(5)
        speed_group.addWidget(self.speed_label)
        speed_group.addWidget(self.speed)
        self.controls_layout.addWidget(engine_container, 3)
        self.controls_layout.addWidget(voice_container, 2)
        self.controls_layout.addWidget(speed_container, 1)
        self.player_bar = QBoxLayout(QBoxLayout.LeftToRight)

        self.transport_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.transport_layout.setSpacing(8)
        self.back_button = QPushButton("◀◀")
        self.back_button.setObjectName("transportButton")
        self.back_button.setFixedSize(48, 48)
        self.back_button.setAccessibleName("Rewind 10 seconds")
        self.back_button.setToolTip("Go back 10 seconds")
        self.back_button.clicked.connect(lambda: self.seek_relative(-10_000))
        self.play_all = QPushButton("▶")
        self.play_all.setObjectName("playAllButton")
        self.play_all.setFixedSize(64, 64)
        self.play_all.setAccessibleName("Play all sentences")
        self.play_all.setToolTip("Play every sentence in order")
        self.play_all.clicked.connect(self.toggle_play_all)
        self.stop_button = QPushButton("■")
        self.stop_button.setObjectName("transportButton")
        self.stop_button.setFixedSize(48, 48)
        self.stop_button.setAccessibleName("Stop playback")
        self.stop_button.setToolTip("Stop playback")
        self.stop_button.clicked.connect(self.stop_playback)
        self.forward_button = QPushButton("▶▶")
        self.forward_button.setObjectName("transportButton")
        self.forward_button.setFixedSize(48, 48)
        self.forward_button.setAccessibleName("Fast-forward 10 seconds")
        self.forward_button.setToolTip("Fast-forward 10 seconds")
        self.forward_button.clicked.connect(lambda: self.seek_relative(10_000))
        self.transport_layout.setAlignment(Qt.AlignCenter)
        self.transport_layout.addWidget(self.back_button)
        self.transport_layout.addWidget(self.play_all)
        self.transport_layout.addWidget(self.forward_button)
        self.transport_layout.addWidget(self.stop_button)
        self.player_bar.addLayout(self.transport_layout)
        self.player_bar.addLayout(self.controls_layout, 1)
        audio_layout.addLayout(self.player_bar)
        helper = QLabel("The current word is highlighted during playback. Hover a blue word to repeat it; move away to continue the sentence.")
        helper.setObjectName("helperText")
        helper.setWordWrap(True)
        helper.hide()
        self.sentence_count_label = QLabel("READY · 0 SENTENCES")
        self.sentence_count_label.setObjectName("sectionLabel")
        audio_layout.addWidget(self.sentence_count_label)
        self.status = QLabel("Ready. System speech works without an API key.")
        self.status.setObjectName("statusMessage")
        self.status.setWordWrap(True)
        audio_layout.addWidget(self.status)
        self.cards_layout = QVBoxLayout()
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(0)
        self.cards_layout.setAlignment(Qt.AlignTop)
        cards_widget = QWidget()
        cards_widget.setObjectName("cardsViewport")
        cards_widget.setLayout(self.cards_layout)
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setWidget(cards_widget)
        audio_layout.addWidget(self.cards_scroll, 1)

        self.workspace.addWidget(self.input_panel)
        self.workspace.addWidget(self.audio_panel)
        self.workspace.setStretchFactor(0, 3)
        self.workspace.setStretchFactor(1, 7)
        layout.addWidget(self.workspace, 1)
        footer = QLabel("MOSHI FRENCH TTS · PERSONAL LISTENING PRACTICE")
        footer.setObjectName("footer")
        footer.setWordWrap(True)
        layout.addWidget(footer)
        self.page_scroll = QScrollArea()
        self.page_scroll.setFrameShape(QFrame.NoFrame)
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.page_scroll.setWidget(root)
        self.setCentralWidget(self.page_scroll)
        self._populate_voices()
        self._apply_responsive_layout(self.width())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "workspace"):
            self._apply_responsive_layout(event.size().width())

    def _apply_responsive_layout(self, width: int):
        mode = "wide" if width >= 900 else "stacked"
        if mode != self._layout_mode:
            self._layout_mode = mode
            if mode == "wide":
                self.input_panel.setMinimumHeight(0)
                self.audio_panel.setMinimumHeight(0)
                self.workspace.setOrientation(Qt.Horizontal)
                self.workspace.setSizes([420, 980])
            else:
                self.input_panel.setMinimumHeight(460)
                self.audio_panel.setMinimumHeight(520)
                self.workspace.setOrientation(Qt.Vertical)
                self.workspace.setSizes([330, 520])
        compact = width < 520
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.input_panel.layout().setContentsMargins(
            12 if compact else 18, 18, 12 if compact else 18, 18
        )
        self.player_bar.setDirection(
            QBoxLayout.LeftToRight if width >= 1250 else QBoxLayout.TopToBottom
        )
        self.header_layout.setDirection(
            QBoxLayout.TopToBottom if compact else QBoxLayout.LeftToRight
        )
        self.header_layout.setAlignment(
            self.settings_button, Qt.AlignLeft if compact else Qt.AlignTop
        )
        self.controls_layout.setDirection(
            QBoxLayout.TopToBottom if compact else QBoxLayout.LeftToRight
        )
        self.transport_layout.setDirection(QBoxLayout.LeftToRight)

    def show_guide(self):
        QMessageBox.information(self, "Listening guide",
            "Paste French text and choose Prepare listening.\n\n"
            "Use Play to listen to all sentences, or a row's play button for one sentence.\n\n"
            "Single-click a word to hear it. Double-click to start from that word. "
            "Hover during playback to repeat a word; move away to continue.\n\n"
            "Expand the arrow to see IPA and meaning when available.")

    def show_history(self):
        from .history_dialog import HistoryDialog
        dialog = HistoryDialog(self.history.recent(HistoryStore.MAX_ITEMS), self)
        def restore(text):
            self.input.setPlainText(text)
            self.status.setText("Saved text restored. Prepare listening when you are ready.")
        dialog.passage_selected.connect(restore)
        dialog.exec()

    def clear_form(self):
        self.stop_playback()
        self.input.clear()
        self.current_sentences = []
        self.current_cards = []
        while self.cards_layout.count():
            widget = self.cards_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        self.sentence_count_label.setText("READY · 0 SENTENCES")
        self.status.setText("Ready. Paste French text to begin.")

    def refresh_cache_summary(self):
        try:
            size = sum(p.stat().st_size for p in self.cache.directory.iterdir() if p.is_file())
            self.cache_summary.setText(f"Audio cached on disk: {size / 1048576:.1f} MB")
        except OSError:
            self.cache_summary.setText("Audio cache unavailable")
        if not hasattr(self, "voice"):
            return
        engine = self._engine_instance()
        for card in self.current_cards:
            path = self.cache.path_for(
                f"{engine.name}|{self.voice.currentText()}", card.text_from(0),
                float(self.speed.currentData()), suffix=engine.cache_suffix,
            )
            card.cache_badge.setVisible(path.is_file() and self.width() >= 900)

    def _update_input_stats(self):
        count = len(self.input.toPlainText())
        self.input_stats.setText(f"{count:,} character{'s' if count != 1 else ''}")

    @staticmethod
    def _distinct_sentence_count(sentences: list[str]) -> int:
        """Count sentences once, ignoring capitalization and extra spacing."""
        normalized = {" ".join(sentence.split()).casefold() for sentence in sentences}
        return len(normalized - {""})

    def _update_sentence_summary(self):
        total = len(self.current_sentences)
        distinct = self._distinct_sentence_count(self.current_sentences)
        total_label = f"{total} sentence card{'s' if total != 1 else ''}"
        distinct_label = f"{distinct} different sentence{'s' if distinct != 1 else ''}"
        self.sentence_summary.setText(f"{total_label} · {distinct_label}")

    def refresh_history(self):
        self.history_list.clear()
        for source_text, _created_at in self.history.recent(HistoryStore.MAX_ITEMS):
            preview = " ".join(source_text.split())
            if len(preview) > 100:
                preview = f"{preview[:97].rstrip()}…"
            item = QListWidgetItem(preview or "(empty text)")
            item.setData(Qt.UserRole, source_text)
            item.setToolTip(source_text)
            self.history_list.addItem(item)

    def restore_history_item(self, item: QListWidgetItem):
        source_text = item.data(Qt.UserRole)
        if not isinstance(source_text, str):
            return
        self.input.setPlainText(source_text)
        self.status.setText("Saved text restored. Create sentence cards when you are ready.")

    def _save_selection(self):
        self.settings.engine = self.engine.currentText()
        self.settings.speed = float(self.speed.currentData())
        if self.engine.currentText() == SystemEngine.name:
            self.settings.system_voice = self.voice.currentText()
        elif self.engine.currentText() == SupertonicEngine.name:
            self.settings.supertonic_voice = self.voice.currentText()
        self.settings_store.save(self.settings)

    def _on_engine_changed(self):
        self._populate_voices()
        self._save_selection()

    def _populate_voices(self):
        engine_name = self.engine.currentText()
        if engine_name == SystemEngine.name:
            voices = SystemEngine.available_voices()
            preferred = self.settings.system_voice
            if not voices:
                voices = ["System default"]
        elif engine_name == SupertonicEngine.name:
            voices = [f"F{i}" for i in range(1, 6)] + [f"M{i}" for i in range(1, 6)]
            preferred = self.settings.supertonic_voice
        elif engine_name == PiperEngine.name:
            voices = ["Configured Piper model"]
            preferred = voices[0]
        else:
            voices = ["Provider default"]
            preferred = voices[0]
        self.voice.blockSignals(True)
        self.voice.clear()
        self.voice.addItems(voices)
        if preferred in voices:
            self.voice.setCurrentText(preferred)
        self.voice.blockSignals(False)

    def process_text(self):
        text = self.input.toPlainText().strip()
        sentences = split_sentences(text)
        if not sentences:
            self.status.setText("No French text found. Paste at least one sentence, then create the cards.")
            self.input.setFocus()
            return
        self.player.stop()
        self.play_queue = []
        self._clear_word_highlight()
        self._reset_hover_state()
        self._request_id += 1
        self._preparing = False
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.current_sentences = sentences
        self._update_sentence_summary()
        self.current_cards = []
        for raw in sentences:
            card = SentenceCard(Sentence(raw))
            card.play_requested.connect(self.play_sentence)
            card.word_clicked.connect(self.play_clicked_word)
            card.word_hovered.connect(self.jump_to_word)
            card.word_hover_left.connect(self.leave_word)
            self.cards_layout.addWidget(card)
            self.current_cards.append(card)
        self.history.save(text)
        self.refresh_history()
        self.status.setText(f"Ready to listen — {len(sentences)} sentence card{'s' if len(sentences) != 1 else ''}.")
        self._update_play_button()

    def toggle_play_all(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            return
        if self.player.playbackState() == QMediaPlayer.PausedState:
            self.player.play()
            return
        if not self.current_sentences:
            self.process_text()
        if self.current_cards:
            self.play_queue = list(self.current_cards)
            self._play_next()

    def _play_next(self):
        if not self.play_queue:
            self.status.setText("Finished playing all sentences.")
            self._update_play_button()
            return
        card = self.play_queue.pop(0)
        self._start_audio(card.text_from(0), continuing=True, source="queue", card=card, start_word=0)

    def _on_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self._active_source == "hover_loop":
                return
            if self.play_queue:
                self._play_next()
            else:
                self.status.setText("Playback finished.")
                self._clear_word_highlight()
                self._update_play_button()

    def _on_playback_state(self, state):
        self._update_play_button()

    def _update_play_button(self):
        state = self.player.playbackState()
        if state == QMediaPlayer.PlayingState:
            self.play_all.setEnabled(True)
            self.play_all.setText("❚❚")
            self.play_all.setAccessibleName("Pause playback")
            self.play_all.setToolTip("Pause playback")
        elif state == QMediaPlayer.PausedState:
            self.play_all.setEnabled(True)
            self.play_all.setText("▶")
            self.play_all.setAccessibleName("Resume playback")
            self.play_all.setToolTip("Resume playback")
        elif self._preparing:
            self.play_all.setEnabled(False)
            self.play_all.setText("…")
            self.play_all.setAccessibleName("Preparing audio")
            self.play_all.setToolTip("Preparing audio…")
        else:
            self.play_all.setEnabled(True)
            self.play_all.setText("▶")
            self.play_all.setAccessibleName("Play all sentences")
            self.play_all.setToolTip("Play every sentence in order")
        has_media = bool(self.player.source().toString())
        self.stop_button.setEnabled(state != QMediaPlayer.StoppedState or self._preparing)
        self.back_button.setEnabled(has_media)
        self.forward_button.setEnabled(has_media)
        for card in self.current_cards:
            if card is self._preparing_card and self._preparing:
                card.set_playback_state("loading")
            elif card is self.active_card and state == QMediaPlayer.PlayingState:
                card.set_playback_state("playing")
            elif card is self.active_card and state == QMediaPlayer.PausedState:
                card.set_playback_state("paused")
            else:
                card.set_playback_state("idle")

    def jump_to_word(self, card: SentenceCard, index: int):
        """Temporarily loop the hovered word while sentence audio is playing."""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.hover_leave_timer.stop()
            continuing = bool(self.play_queue) or self._active_source in {"queue", "hover_resume"}
            self._hovered_word = (card, index, continuing)
            self._pending_hover = self._hovered_word
            self.hover_timer.start()

    def leave_word(self, card: SentenceCard, index: int):
        if self._hovered_word and self._hovered_word[:2] == (card, index):
            self.hover_leave_timer.start()

    def _perform_hover_jump(self):
        if not self._pending_hover or self.player.playbackState() != QMediaPlayer.PlayingState:
            return
        if self._hover_worker_active:
            return
        card, index, continuing = self._pending_hover
        self._pending_hover = None
        spoken_word = card.words[index].strip(".,!?;:—–()[]«»\"") or card.words[index]
        self._start_audio(
            spoken_word, continuing=continuing, source="hover_loop",
            card=card, start_word=index,
        )

    def _continue_after_hover(self):
        if not self._hovered_word:
            return
        card, index, continuing = self._hovered_word
        self._hovered_word = None
        self._pending_hover = None
        self.hover_timer.stop()

        if self._hover_worker_active and self._active_source != "hover_loop":
            self._request_id += 1
            self._hover_worker_active = False
            self.status.setText("Continuing sentence audio.")
            return
        if self._active_source != "hover_loop":
            return

        next_word = index + 1
        self.player.setLoops(1)
        self.player.stop()
        if next_word < len(card.words):
            self._start_audio(
                card.text_from(next_word), continuing=continuing,
                source="hover_resume", card=card, start_word=next_word,
            )
        elif self.play_queue:
            self._play_next()
        else:
            self._clear_word_highlight()
            self.status.setText("Sentence finished.")
            self._update_play_button()

    def _engine_instance(self):
        if self.engine.currentText() == PiperEngine.name:
            return PiperEngine(self.settings.piper_executable, self.settings.piper_model)
        if self.engine.currentText() == SupertonicEngine.name:
            return SupertonicEngine(self.voice.currentText())
        if self.engine.currentText() == OnlineTTSEngine.name:
            return OnlineTTSEngine()
        voice = self.voice.currentText()
        return SystemEngine("" if voice == "System default" else voice)

    def play_sentence(self, card: SentenceCard, index: int):
        if card is self.active_card and self._active_source != "word":
            if self.player.playbackState() == QMediaPlayer.PlayingState:
                self.player.pause()
                return
            if self.player.playbackState() == QMediaPlayer.PausedState:
                self.player.play()
                return
        self.play_queue = []
        self._reset_hover_state()
        self.player.stop()
        self._start_audio(
            card.text_from(index), continuing=False, source="sentence",
            card=card, start_word=index,
        )

    def play_clicked_word(self, card: SentenceCard, index: int):
        """Speak only the clicked word whenever sentence playback is inactive."""
        if self.player.playbackState() == QMediaPlayer.PlayingState or self._preparing:
            return
        self.play_queue = []
        self._reset_hover_state()
        self.player.stop()
        spoken_word = card.words[index].strip(".,!?;:—–()[]«»\"") or card.words[index]
        self._start_audio(
            spoken_word, continuing=False, source="word",
            card=card, start_word=index,
        )

    def _start_audio(self, text: str, continuing: bool, source: str,
                     card: SentenceCard, start_word: int):
        engine = self._engine_instance()
        speed = float(self.speed.currentData())
        cache_path = self.cache.path_for(
            f"{engine.name}|{self.voice.currentText()}", text, speed,
            suffix=engine.cache_suffix,
        )
        self._request_id += 1
        request_id = self._request_id
        self._preparing = source != "hover_loop"
        self._preparing_card = card if self._preparing else None
        self._hover_worker_active = source == "hover_loop"
        if source == "hover_loop":
            self.status.setText("Preparing a word loop… sentence audio will continue meanwhile.")
        elif source == "hover_resume":
            self.status.setText("Continuing the sentence…")
        else:
            self.status.setText("Preparing audio…")
        self._update_play_button()
        worker = SynthesisWorker(
            request_id, engine, text, speed, cache_path, continuing, source,
            card, start_word,
        )
        worker.signals.finished.connect(self._audio_ready)
        self._workers[request_id] = worker
        self.thread_pool.start(worker)

    def _audio_ready(self, request_id, result, text, continuing, source, card, start_word):
        self._workers.pop(request_id, None)
        if source == "hover_loop":
            self._hover_worker_active = False
        if request_id != self._request_id:
            if self._pending_hover:
                self.hover_timer.start()
            return
        self._preparing = False
        self._preparing_card = None
        if result.audio_path:
            self._clear_word_highlight()
            self.active_card = card
            self.active_start_word = start_word
            self._active_source = source
            card.set_active_word(start_word)
            self.player.setLoops(QMediaPlayer.Infinite if source == "hover_loop" else 1)
            self.player.setPlaybackRate(result.playback_rate)
            self.player.setSource(QUrl.fromLocalFile(str(result.audio_path)))
            self.player.play()
            if source == "hover_loop":
                self.status.setText(f'Repeating “{card.words[start_word]}”. Move away to continue.')
            elif source == "hover_resume":
                self.status.setText("Continuing sentence audio.")
            elif source == "word":
                self.status.setText(f'Playing “{card.words[start_word]}”.')
            else:
                self.status.setText("Playing sentence audio.")
        else:
            if source == "hover_loop":
                self._hovered_word = None
                self.status.setText(f"Could not repeat that word. {result.message}")
            else:
                self.status.setText(result.message)
                self.play_queue = []
        self._update_play_button()
        if self._pending_hover and self.player.playbackState() == QMediaPlayer.PlayingState:
            self.hover_timer.start()

    def seek_relative(self, milliseconds: int):
        if not self.player.source().toString():
            return
        duration = self.player.duration()
        target = max(0, self.player.position() + milliseconds)
        if duration > 0:
            target = min(target, duration)
        self.player.setPosition(target)

    def stop_playback(self):
        self._reset_hover_state()
        self.play_queue = []
        self._request_id += 1
        self._preparing = False
        self._preparing_card = None
        self._hover_worker_active = False
        self.player.setLoops(1)
        self.player.stop()
        self._clear_word_highlight()
        self.status.setText("Playback stopped.")
        self._update_play_button()

    def _clear_word_highlight(self):
        if self.active_card is not None:
            self.active_card.set_active_word(None)
        self.active_card = None
        self._active_source = ""

    def _reset_hover_state(self):
        self.hover_timer.stop()
        self.hover_leave_timer.stop()
        self._pending_hover = None
        self._hovered_word = None
        self._hover_worker_active = False
        self.player.setLoops(1)

    @staticmethod
    def _word_index_for_progress(card: SentenceCard, start_word: int, progress: float) -> int:
        words = card.words[start_word:]
        if not words:
            return start_word
        weights = [max(1, len(word.strip(".,!?;:—–()[]«»\"'"))) + 1 for word in words]
        target = max(0.0, min(1.0, progress)) * sum(weights)
        total = 0
        for offset, weight in enumerate(weights):
            total += weight
            if target < total:
                return start_word + offset
        return start_word + len(words) - 1

    def _update_word_highlight(self, position: int):
        if self.active_card is None:
            return
        if self._active_source == "word":
            self.active_card.set_active_word(self.active_start_word)
            return
        duration = self.player.duration()
        if duration <= 0:
            return
        index = self._word_index_for_progress(
            self.active_card, self.active_start_word, position / duration
        )
        self.active_card.set_active_word(index)

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        dialog.clear_audio_cache_requested.connect(self.clear_audio_cache)
        if dialog.exec():
            self.settings = dialog.updated_settings(self.settings)
            self.settings_store.save(self.settings)
            index = self.speed.findData(self.settings.speed)
            if index >= 0:
                self.speed.setCurrentIndex(index)
            self._populate_voices()
            self.status.setText("Settings saved locally.")

    def clear_audio_cache(self):
        answer = QMessageBox.question(
            self,
            "Clear generated audio?",
            "Delete all locally saved generated audio? This does not remove your text history or downloaded voice models.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        removed = self.cache.clear()
        self.status.setText(f"Cleared {removed} generated audio file{'s' if removed != 1 else ''}.")
        QMessageBox.information(self, "Audio cache cleared", self.status.text())
