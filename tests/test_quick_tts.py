import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from french_learning_app.services.audio_cache import AudioCache
from french_learning_app.services.quick_tts_ipc import socket_name
from french_learning_app.services.settings import AppSettings
from french_learning_app.services.tts_manager import TTSManager
from french_learning_app.ui.quick_tts_popup import QuickTTSMenuPanel


class QuickTTSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_manager_exposes_requested_local_models(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TTSManager(AppSettings(), AudioCache(Path(temp_dir)))

            self.assertEqual(manager.models(), ["Supertonic HD", "Piper"])
            self.assertEqual(manager.voices_for("Supertonic HD")[0], "F1")
            self.assertEqual(manager.voices_for("Piper"), ["Configure Piper in Settings"])

    def test_popup_speed_values_are_limited_to_the_requested_four(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            popup = QuickTTSMenuPanel(TTSManager(AppSettings(), AudioCache(Path(temp_dir))))
            self.assertEqual(
                [button.text() for button in popup.speed_buttons.values()],
                ["0.5x", "0.75x", "1.0x", "1.25x"],
            )

    def test_quick_tts_controls_are_a_menu_style_popover(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            panel = QuickTTSMenuPanel(TTSManager(AppSettings(), AudioCache(Path(temp_dir))))

            self.assertTrue(panel.isWindow())
            self.assertTrue(panel.windowFlags() & Qt.Tool)
            self.assertTrue(panel.windowFlags() & Qt.WindowStaysOnTopHint)

    def test_service_text_is_placed_in_the_menu_text_area(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            panel = QuickTTSMenuPanel(TTSManager(AppSettings(), AudioCache(Path(temp_dir))))

            panel.show_text("Bonjour depuis le service.")

            self.assertEqual(panel.text_edit.toPlainText(), "Bonjour depuis le service.")
            self.assertEqual(
                panel.settings.value("quickTts/lastText", "", type=str),
                "Bonjour depuis le service.",
            )

    def test_menu_text_area_remains_editable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            panel = QuickTTSMenuPanel(TTSManager(AppSettings(), AudioCache(Path(temp_dir))))
            panel.show_text("Bonjour.")
            panel.text_edit.setPlainText("Bonsoir.")

            self.assertEqual(panel.text_edit.toPlainText(), "Bonsoir.")

    def test_menu_has_separate_play_stop_and_loading_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            panel = QuickTTSMenuPanel(TTSManager(AppSettings(), AudioCache(Path(temp_dir))))
            self.assertEqual(panel.play_button.text(), "▶  Play")
            self.assertEqual(panel.stop_button.text(), "■  Stop")
            self.assertFalse(panel.stop_button.isEnabled())

            panel._preparing = True
            panel._update_play_button()

            self.assertEqual(panel.play_button.text(), "Loading…")
            self.assertFalse(panel.play_button.isEnabled())
            self.assertTrue(panel.stop_button.isEnabled())
            self.assertFalse(panel.loading_bar.isHidden())

    def test_ipc_name_is_user_scoped(self):
        self.assertTrue(socket_name().startswith("FrenchLearningAppQuickTTS-"))
