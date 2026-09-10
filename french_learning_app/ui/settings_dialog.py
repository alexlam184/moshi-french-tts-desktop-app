from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
                               QDoubleSpinBox, QPushButton)

from ..services.settings import AppSettings


class SettingsDialog(QDialog):
    clear_audio_cache_requested = Signal()

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.piper_executable = QLineEdit(settings.piper_executable)
        self.piper_model = QLineEdit(settings.piper_model)
        self.supertonic_voice = QLineEdit(settings.supertonic_voice)
        self.supertonic_voice.setPlaceholderText("F1, F2, F3, F4, F5, M1–M5")
        self.default_speed = QDoubleSpinBox()
        self.default_speed.setRange(0.5, 1.5)
        self.default_speed.setSingleStep(0.05)
        self.default_speed.setValue(settings.speed)
        layout = QFormLayout(self)
        layout.addRow("Piper executable", self.piper_executable)
        layout.addRow("Piper voice model", self.piper_model)
        layout.addRow("Supertonic voice", self.supertonic_voice)
        layout.addRow("Default speech speed", self.default_speed)
        clear_cache = QPushButton("Clear generated audio cache")
        clear_cache.setToolTip("Delete saved speech audio from this computer")
        clear_cache.clicked.connect(self.clear_audio_cache_requested)
        layout.addRow("Saved audio", clear_cache)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def updated_settings(self, current: AppSettings) -> AppSettings:
        current.piper_executable = self.piper_executable.text().strip()
        current.piper_model = self.piper_model.text().strip()
        current.supertonic_voice = self.supertonic_voice.text().strip().upper() or "F1"
        current.speed = self.default_speed.value()
        return current
