from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
                               QDoubleSpinBox, QPushButton, QLabel, QVBoxLayout,
                               QHBoxLayout, QWidget, QScrollArea, QFileDialog)
from .theme import PAPER, LISTEN_PAPER, INK, MUTED, RULE, COBALT, DISPLAY

from ..services.settings import AppSettings


class SettingsDialog(QDialog):
    clear_audio_cache_requested = Signal()

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Offline voices")
        self.resize(820, 740)
        if parent and parent.screen():
            area = parent.screen().availableGeometry()
            self.resize(min(820, area.width() - 40), min(740, area.height() - 60))
        self.setObjectName("voiceModels")
        self.setStyleSheet(f"""
            QDialog#voiceModels, QWidget#voiceContent {{ background: {PAPER}; }}
            QLabel {{ color: {INK}; }}
            QLabel#voiceTitle {{ font-family: {DISPLAY}; font-size: 48px; }}
            QLabel#voiceMuted {{ color: {MUTED}; font-size: 17px; }}
            QLabel#voiceSection {{ font-size: 21px; font-weight: 700; }}
            QLabel#voiceNote {{ background: {LISTEN_PAPER}; padding: 20px; color: {MUTED}; }}
            QWidget#voicePackage {{ border-top: 1px solid {RULE}; }}
            QPushButton {{ padding: 10px 16px; border: 1px solid {RULE};
                border-radius: 8px; background: {PAPER}; color: {INK}; }}
            QPushButton:hover {{ background: {LISTEN_PAPER}; }}
            QPushButton:focus {{ border-color: {COBALT}; }}
            QPushButton:pressed {{ background: {RULE}; }}
            QLineEdit, QDoubleSpinBox {{ padding: 8px; border: 1px solid {RULE};
                border-radius: 6px; color: {INK}; background: {PAPER};
                selection-background-color: {COBALT}; selection-color: {PAPER}; }}
            QScrollArea {{ border: 0; }}
        """)
        self.piper_executable = QLineEdit(settings.piper_executable)
        self.piper_model = QLineEdit(settings.piper_model)
        self.supertonic_voice = QLineEdit(settings.supertonic_voice)
        self.supertonic_voice.setPlaceholderText("F1, F2, F3, F4, F5, M1–M5")
        self.default_speed = QDoubleSpinBox()
        self.default_speed.setRange(0.5, 1.5)
        self.default_speed.setSingleStep(0.05)
        self.default_speed.setValue(settings.speed)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget(objectName="voiceContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(24)
        layout.addWidget(QLabel("MODEL STORAGE", objectName="voiceMuted"))
        heading = QHBoxLayout()
        title = QLabel("Offline voices", objectName="voiceTitle")
        title.setWordWrap(True)
        heading.addWidget(title, 1)
        close = QPushButton("×")
        close.setAccessibleName("Close voice models")
        close.clicked.connect(self.reject)
        heading.addWidget(close)
        layout.addLayout(heading)
        intro = QLabel("Voice packages stay on this computer. Set up a voice once, "
                       "then use it locally for offline playback.", objectName="voiceMuted")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        note = QLabel("DESKTOP MODEL STORAGE\n\n"
            "Downloaded voice models are separate from generated audio. "
            "Clearing the audio cache keeps your voice models. "
            "Supertonic downloads its model files on first use.",
            objectName="voiceNote")
        note.setWordWrap(True)
        layout.addWidget(note)

        def section(title, description):
            panel = QWidget(objectName="voicePackage")
            box = QVBoxLayout(panel)
            box.setContentsMargins(0, 20, 0, 8)
            box.setSpacing(12)
            box.addWidget(QLabel(title, objectName="voiceSection"))
            label = QLabel(description, objectName="voiceMuted")
            label.setWordWrap(True)
            box.addWidget(label)
            layout.addWidget(panel)
            return box

        piper = section("Piper · French", "Compact ONNX voice for offline listening. "
                        "Choose an installed executable and its French voice model.")
        piper_form = QFormLayout()
        piper_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        for label, field, file_filter in (
            ("Piper executable", self.piper_executable, "All files (*)"),
            ("French voice model", self.piper_model, "ONNX models (*.onnx)"),
        ):
            row = QHBoxLayout()
            row.addWidget(field, 1)
            browse = QPushButton("Browse")
            browse.clicked.connect(lambda _checked=False, target=field, filters=file_filter:
                                   self.choose_file(target, filters))
            row.addWidget(browse)
            piper_form.addRow(label, row)
        piper.addLayout(piper_form)
        supertonic = section("Supertonic HD", "Ten voice styles · local neural speech")
        supertonic_form = QFormLayout()
        supertonic_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        supertonic_form.addRow("Preferred voice", self.supertonic_voice)
        supertonic.addLayout(supertonic_form)
        playback = section("Playback & audio cache", "Choose your default speed and manage saved speech audio.")
        defaults = QFormLayout()
        defaults.addRow("Default speech speed", self.default_speed)
        playback.addLayout(defaults)
        clear_cache = QPushButton("Clear generated audio cache")
        clear_cache.setToolTip("Delete saved speech audio from this computer")
        clear_cache.clicked.connect(self.clear_audio_cache_requested)
        playback.addWidget(clear_cache)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def choose_file(self, field, file_filter):
        path, _ = QFileDialog.getOpenFileName(self, "Choose installed Piper file", field.text(), file_filter)
        if path:
            field.setText(path)

    def updated_settings(self, current: AppSettings) -> AppSettings:
        current.piper_executable = self.piper_executable.text().strip()
        current.piper_model = self.piper_model.text().strip()
        current.supertonic_voice = self.supertonic_voice.text().strip().upper() or "F1"
        current.speed = self.default_speed.value()
        return current
