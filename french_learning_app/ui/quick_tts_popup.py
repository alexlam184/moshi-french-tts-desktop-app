from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QSettings, QThreadPool, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QFrame, QHBoxLayout, QLabel,
                               QPlainTextEdit, QProgressBar, QPushButton, QToolButton,
                               QVBoxLayout, QWidget, QApplication)

from ..services.tts import TTSResult
from ..services.tts_manager import TTSManager


class QuickTTSWorkerSignals(QObject):
    finished = Signal(int, object)


class QuickTTSWorker(QRunnable):
    def __init__(self, manager: TTSManager, model: str, voice: str, text: str, speed: float, request_id: int = 0):
        super().__init__()
        self.manager, self.model, self.voice = manager, model, voice
        self.text, self.speed = text, speed
        self.request_id = request_id
        self.cancelled = Event()
        self.signals = QuickTTSWorkerSignals()

    @Slot()
    def run(self):
        if self.cancelled.is_set():
            self.signals.finished.emit(self.request_id, TTSResult(message="Cancelled."))
            return
        try:
            result = self.manager.synthesize(
                self.model, self.voice, self.text, self.speed,
            )
        except Exception as exc:
            result = TTSResult(message=f"Quick TTS could not create audio: {exc}")
        self.signals.finished.emit(self.request_id, result)


class SupertonicWarmupWorker(QRunnable):
    """Preload the default neural voice while the app is otherwise idle."""

    def __init__(self, manager: TTSManager):
        super().__init__()
        self.manager = manager

    @Slot()
    def run(self):
        self.manager.preload()


class QuickTTSMenuPanel(QWidget):
    """A menu-style popover for native macOS status-bar use."""

    close_requested = Signal()

    def __init__(self, manager: TTSManager, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.manager = manager
        self.settings = QSettings("FrenchLearningApp", "French Learning App")
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self._workers = {}
        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.player.setAudioOutput(self.output)
        self.player.playbackStateChanged.connect(self._update_play_button)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.errorOccurred.connect(self._on_player_error)
        self._request_id = 0
        self._preparing = False
        self._text = ""
        self._build_ui()
        self._restore_settings()
        self.close_requested.connect(self.close_panel)

    def warm_supertonic(self):
        """Begin background model loading after the application has started."""
        if self.model.currentText() != TTSManager.SUPERTONIC_MODEL:
            return
        # The initial model download/load can take time, but later Play presses
        # reuse the in-memory engine and do not block the interface.
        self.thread_pool.start(SupertonicWarmupWorker(self.manager))

    def _build_ui(self):
        self.setWindowTitle("Moshi French TTS")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Moshi French TTS")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        close = QPushButton("×")
        close.setFixedSize(30, 30)
        close.setToolTip("Close menu")
        close.clicked.connect(self.close_requested)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close)
        layout.addLayout(header)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(
            "Select French text in another app, then choose Speak French."
        )
        self.text_edit.setMinimumHeight(64)
        self.text_edit.setMaximumHeight(120)
        self.text_edit.setStyleSheet(
            "background:#ffffff; color:#18212f; border:1px solid #bec9d7;"
            "border-radius:7px; padding:7px;"
        )
        layout.addWidget(self.text_edit)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.model = QComboBox()
        self.model.addItems(self.manager.models())
        self.model.currentTextChanged.connect(self._model_changed)
        self.voice = QComboBox()
        self.voice.currentTextChanged.connect(self._save_settings)
        for label, widget in (("Model", self.model), ("Voice", self.voice)):
            column = QVBoxLayout()
            column.setSpacing(4)
            caption = QLabel(label)
            caption.setStyleSheet("font-size:12px; font-weight:700;")
            column.addWidget(caption)
            column.addWidget(widget)
            controls.addLayout(column, 1)
        layout.addLayout(controls)

        layout.addWidget(QLabel("Speed"))
        speed_row = QHBoxLayout()
        self.speed_group = QButtonGroup(self)
        self.speed_group.setExclusive(True)
        self.speed_buttons: dict[float, QToolButton] = {}
        speed_labels = {0.5: "0.5x", 0.75: "0.75x", 1.0: "1.0x", 1.25: "1.25x"}
        for speed in (0.5, 0.75, 1.0, 1.25):
            button = QToolButton()
            button.setText(speed_labels[speed])
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setMinimumHeight(34)
            self.speed_group.addButton(button)
            self.speed_buttons[speed] = button
            speed_row.addWidget(button)
        self.speed_group.buttonClicked.connect(self._save_settings)
        layout.addLayout(speed_row)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#43536a;")
        layout.addWidget(self.status)
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setFixedHeight(4)
        self.loading_bar.hide()
        layout.addWidget(self.loading_bar)
        playback_row = QHBoxLayout()
        playback_row.setSpacing(8)
        self.play_button = QPushButton("▶  Play")
        self.play_button.setMinimumHeight(42)
        self.play_button.clicked.connect(self.play)
        self.stop_button = QPushButton("■  Stop")
        self.stop_button.setMinimumHeight(42)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop)
        playback_row.addWidget(self.play_button, 2)
        playback_row.addWidget(self.stop_button, 1)
        layout.addLayout(playback_row)

        play_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        play_shortcut.activated.connect(self.toggle_playback)
        escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        escape_shortcut.activated.connect(self.close_requested)
        close_shortcut = QShortcut(QKeySequence("Meta+W"), self)
        close_shortcut.activated.connect(self.close_requested)

    def _restore_settings(self):
        model = self.settings.value("quickTts/model", TTSManager.SYSTEM_MODEL, type=str)
        self.model.setCurrentText(model if model in self.manager.models() else TTSManager.SYSTEM_MODEL)
        speed = float(self.settings.value("quickTts/speed", 1.0))
        self.speed_buttons[min(self.speed_buttons, key=lambda option: abs(option - speed))].setChecked(True)
        self._model_changed(self.model.currentText())
        last_text = self.settings.value("quickTts/lastText", "", type=str).strip()
        if last_text:
            self._text = last_text
            self.text_edit.setPlainText(last_text)

    def _model_changed(self, model: str):
        old_voice = self.voice.currentText()
        self.voice.blockSignals(True)
        self.voice.clear()
        self.voice.addItems(self.manager.voices_for(model))
        saved = self.settings.value(f"quickTts/{model}/voice", old_voice, type=str)
        self.voice.setCurrentText(saved)
        if self.voice.currentIndex() < 0:
            self.voice.setCurrentIndex(0)
        self.voice.blockSignals(False)
        self._save_settings()

    def _save_settings(self, *_):
        self.settings.setValue("quickTts/model", self.model.currentText())
        self.settings.setValue("quickTts/speed", self.selected_speed())
        self.settings.setValue(f"quickTts/{self.model.currentText()}/voice", self.voice.currentText())

    def selected_speed(self) -> float:
        for speed, button in self.speed_buttons.items():
            if button.isChecked():
                return speed
        return 1.0

    def show_text(self, text: str):
        self.stop()
        self._text = text.strip()
        self.text_edit.setPlainText(self._text)
        self.text_edit.moveCursor(QTextCursor.Start)
        self.settings.setValue("quickTts/lastText", self._text)
        self.settings.sync()
        self.status.setText("")

    def show_at(self, position):
        """Show as an anchored menu-like surface, never inside a native QMenu."""
        self.adjustSize()
        self.move(position)
        self.show()
        self.raise_()
        self.activateWindow()
        self.text_edit.setFocus()

    def focusOutEvent(self, event):
        """Match a native menu: dismiss the panel when the user clicks away."""
        super().focusOutEvent(event)
        QTimer.singleShot(0, self._close_if_focus_left_panel)

    def _close_if_focus_left_panel(self):
        if not self.isVisible():
            return
        # A combo-box list is a temporary popup window. Do not dismiss the
        # panel while the user is choosing a model or voice from that list.
        if self.model.view().isVisible() or self.voice.view().isVisible():
            return
        active = QApplication.activeWindow()
        if active is self or (active is not None and self.isAncestorOf(active)):
            return
        self.close_panel()

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.stop()
            return
        self.play()

    def play(self):
        if self._preparing or self.player.playbackState() == QMediaPlayer.PlayingState:
            return
        self._text = self.text_edit.toPlainText().strip()
        if not self._text:
            self.status.setText("No selected French text was received.")
            return
        self._request_id += 1
        request_id = self._request_id
        self._preparing = True
        self.status.setText("Loading voice…")
        self._update_play_button()
        worker = QuickTTSWorker(
            self.manager, self.model.currentText(), self.voice.currentText(),
            self._text, self.selected_speed(),
            request_id,
        )
        self._workers[request_id] = worker
        worker.signals.finished.connect(self._audio_ready, Qt.QueuedConnection)
        self.thread_pool.start(worker)

    @Slot(int, object)
    def _audio_ready(self, request_id: int, result: TTSResult):
        self._workers.pop(request_id, None)
        if request_id != self._request_id:
            return
        self._preparing = False
        self.play_button.setEnabled(True)
        if not result.audio_path:
            self.status.setText(result.message or "Could not create audio.")
            self._update_play_button()
            return
        self.player.setPlaybackRate(result.playback_rate)
        self.player.setSource(QUrl.fromLocalFile(str(Path(result.audio_path))))
        self.player.play()
        self.status.setText("Playing selected text.")
        self._update_play_button()

    def stop(self):
        self._request_id += 1
        for worker in self._workers.values():
            worker.cancelled.set()
        self._preparing = False
        self.player.stop()
        self.status.setText("Stopped.")
        self._update_play_button()

    @Slot(object, str)
    def _on_player_error(self, error, message):
        self._preparing = False
        self.status.setText(message or "Audio playback failed. Try another voice.")
        self._update_play_button()

    def _on_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.status.setText("Finished.")
            self._update_play_button()

    def _update_play_button(self, *_):
        playing = self.player.playbackState() == QMediaPlayer.PlayingState
        self.play_button.setText("Loading…" if self._preparing else "▶  Play")
        self.play_button.setEnabled(not self._preparing and not playing)
        self.stop_button.setEnabled(self._preparing or playing)
        self.loading_bar.setVisible(self._preparing)

    def close_panel(self):
        self.stop()
        self.hide()

    def release_resources(self):
        """Release cached in-memory engine objects during application quit."""
        self.stop()
        self.thread_pool.waitForDone()
        self.manager.release_loaded_models()
