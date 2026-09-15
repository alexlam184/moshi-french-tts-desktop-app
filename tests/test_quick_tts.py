import os
import tempfile
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QThread, Slot
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from french_learning_app.services.audio_cache import AudioCache
from french_learning_app.services.quick_tts_ipc import socket_name
from french_learning_app.services.settings import AppSettings
from french_learning_app.services.tts_manager import TTSManager
from french_learning_app.ui.quick_tts_popup import QuickTTSMenuPanel, QuickTTSWorker
from french_learning_app.services.tts import SystemEngine, TTSResult


class QuickTTSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_manager_exposes_requested_local_models(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TTSManager(AppSettings(), AudioCache(Path(temp_dir)))

            self.assertEqual(manager.models(), ["Supertonic HD", "Piper", "System / Browser TTS"])
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

    def test_system_model_uses_native_engine_and_default_voice(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = TTSManager(AppSettings(), AudioCache(Path(directory)))
            with patch.object(SystemEngine, "available_voices", return_value=[]):
                self.assertEqual(manager.voices_for(manager.SYSTEM_MODEL), ["System default"])
            engine = manager._engine_for(manager.SYSTEM_MODEL, "System default")
            self.assertIsInstance(engine, SystemEngine)
            self.assertEqual(engine.voice, "")

    def test_menu_defaults_to_system_without_neural_preload(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = TTSManager(AppSettings(), AudioCache(Path(directory)))
            with patch.object(SystemEngine, "available_voices", return_value=["French voice"]):
                panel = QuickTTSMenuPanel(manager)
                panel.settings = Mock()
                panel.settings.value.side_effect = lambda key, default, **kwargs: default
                panel._restore_settings()
                self.assertEqual(panel.model.currentText(), TTSManager.SYSTEM_MODEL)
                self.assertEqual(panel.selected_speed(), 1.0)
                with patch.object(panel.thread_pool, "start") as start:
                    panel.warm_supertonic()
                    start.assert_not_called()

    def test_cancelled_queued_worker_does_not_synthesize(self):
        manager = Mock()
        worker = QuickTTSWorker(manager, "Piper", "voice", "Bonjour", 1.0)
        worker.cancelled.set()
        worker.run()
        manager.synthesize.assert_not_called()

    def test_worker_completion_runs_on_ui_thread_and_stale_result_is_ignored(self):
        class Panel(QuickTTSMenuPanel):
            completion_thread = None

            @Slot(int, object)
            def _audio_ready(self, request_id, result):
                self.completion_thread = QThread.currentThread()
                super()._audio_ready(request_id, result)

        with tempfile.TemporaryDirectory() as directory:
            manager = TTSManager(AppSettings(), AudioCache(Path(directory)))
            manager.synthesize = Mock(return_value=TTSResult(message="Test completion"))
            panel = Panel(manager)
            panel.show_text("Bonjour")
            panel.play()
            panel.thread_pool.waitForDone()
            for _ in range(20):
                QTest.qWait(10)
                if panel.completion_thread is not None:
                    break
            self.assertEqual(panel.completion_thread, self.app.thread())
            self.assertFalse(panel._workers)
            panel.stop()
            panel._audio_ready(panel._request_id - 1, TTSResult(message="Stale"))
            self.assertEqual(panel.status.text(), "Stopped.")
            panel.release_resources()
