import os
import unittest
from math import ceil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QApplication

from french_learning_app.models.sentence import Sentence
from french_learning_app.ui.main_window import MainWindow
from french_learning_app.ui.sentence_card import SentenceCard
from french_learning_app.ui.theme import ACTIVE_WORD, HOVER_WORD


class SentenceInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_word_click_keeps_sentence_visible(self):
        card = SentenceCard(Sentence("Bonjour tout le monde."))
        original = card.title.toPlainText()
        clicked = []
        card.word_clicked.connect(lambda _card, index: clicked.append(index))

        card.title.anchorClicked.emit(QUrl("1"))
        self.app.processEvents()

        self.assertFalse(card.title.openLinks())
        self.assertEqual(card.title.toPlainText(), original)
        self.assertEqual(card.selected_index, 1)
        self.assertEqual(clicked, [1])

    def test_double_clicking_a_word_requests_sentence_playback_from_that_word(self):
        card = SentenceCard(Sentence("Bonjour tout le monde."))
        requests = []
        card.play_requested.connect(lambda _card, index: requests.append(index))

        card.title.word_double_clicked.emit(2)

        self.assertEqual(card.selected_index, 2)
        self.assertEqual(requests, [2])

    def test_window_uses_moshi_french_tts_branding(self):
        window = MainWindow()
        self.assertEqual(window.windowTitle(), "Moshi French TTS")

    def test_sentence_summary_counts_distinct_sentences(self):
        window = MainWindow()
        window.current_sentences = ["Bonjour.", " bonjour. ", "Bonsoir !"]
        window._update_sentence_summary()

        self.assertEqual(window.sentence_summary.text(), "3 sentence cards · 2 different sentences")

    def test_word_progress_reaches_first_and_last_words(self):
        card = SentenceCard(Sentence("Bonjour tout le monde."))
        self.assertEqual(MainWindow._word_index_for_progress(card, 0, 0.0), 0)
        self.assertEqual(MainWindow._word_index_for_progress(card, 0, 1.0), 3)

    def test_hover_enter_and_leave_are_distinct_from_click(self):
        card = SentenceCard(Sentence("Bonjour tout le monde."))
        events = []
        card.word_hovered.connect(lambda _card, index: events.append(("enter", index)))
        card.word_hover_left.connect(lambda _card, index: events.append(("leave", index)))

        card.title.word_entered.emit(2)
        card.title.word_left.emit(2)

        self.assertEqual(events, [("enter", 2), ("leave", 2)])
        self.assertEqual(card.selected_index, 0)

    def test_sentence_button_reflects_playback_state(self):
        card = SentenceCard(Sentence("Bonjour tout le monde."))
        card.set_playback_state("playing")
        self.assertEqual(card.play_button.accessibleName(), "Pause sentence")
        self.assertEqual(card.property("playbackState"), "playing")
        card.set_playback_state("paused")
        self.assertEqual(card.play_button.accessibleName(), "Resume sentence")

    def test_sentence_row_centers_controls_and_uses_compact_play_button(self):
        card = SentenceCard(Sentence("Bonjour tout le monde."))

        self.assertEqual(card.play_button.minimumWidth(), 36)
        self.assertEqual(card.play_button.minimumHeight(), 36)
        for index in range(card.top_row.count()):
            alignment = card.top_row.itemAt(index).alignment()
            self.assertTrue(alignment & Qt.AlignVCenter)

    def test_sentence_text_has_no_spare_top_aligned_browser_area(self):
        card = SentenceCard(Sentence("Bonjour tout le monde."))
        card.title._fit_height()

        self.assertEqual(
            card.title.height(),
            ceil(card.title.document().size().height()),
        )

    def test_details_toggle_controls_ipa_and_meaning(self):
        card = SentenceCard(Sentence("Bonjour.", translation="Hello.", ipa="/bɔ̃.ʒuʁ/"))
        self.assertFalse(card.details.isVisible())
        card.details_toggle.setChecked(True)
        self.assertFalse(card.details.isHidden())
        self.assertEqual(card.details_toggle.text(), "▼")
        card.details_toggle.setChecked(False)
        self.assertTrue(card.details.isHidden())
        self.assertEqual(card.details_toggle.text(), "▶")

    def test_hover_highlight_overrides_playback_highlight(self):
        card = SentenceCard(Sentence("Bonjour tout le monde."))
        card.set_active_word(1)
        card.title.word_entered.emit(2)
        card.set_active_word(3)
        self.assertEqual(card.highlight_index, 2)
        card.title.word_left.emit(2)
        self.assertEqual(card.highlight_index, 3)

    def test_hover_repetition_temporarily_hides_speaking_highlight(self):
        card = SentenceCard(Sentence("Bonjour tout le monde."))
        card.set_active_word(1)
        card.title.word_entered.emit(2)

        self.assertNotIn(ACTIVE_WORD, card._word_style(1))
        self.assertIn(HOVER_WORD, card._word_style(2))
        card.title.word_left.emit(2)
        self.assertIn(ACTIVE_WORD, card._word_style(1))

    def test_transport_controls_use_reference_hierarchy(self):
        window = MainWindow()
        controls = [
            window.transport_layout.itemAt(index).widget()
            for index in range(window.transport_layout.count())
        ]
        self.assertEqual(
            controls,
            [window.back_button, window.play_all, window.forward_button, window.stop_button],
        )
        secondary_widths = [
            button.minimumWidth() for button in controls if button is not window.play_all
        ]
        self.assertTrue(all(width == secondary_widths[0] for width in secondary_widths))
        self.assertGreater(window.play_all.minimumWidth(), secondary_widths[0])
        self.assertEqual(window.play_all.accessibleName(), "Play all sentences")

    def test_inactive_playback_speaks_only_clicked_word(self):
        window = MainWindow()
        card = SentenceCard(Sentence("Bonjour tout le monde."))
        calls = []
        window._start_audio = lambda *args, **kwargs: calls.append((args, kwargs))

        window.play_clicked_word(card, 2)

        self.assertEqual(
            calls,
            [(("le",), {
                "continuing": False,
                "source": "word",
                "card": card,
                "start_word": 2,
            })],
        )

    def test_word_only_playback_keeps_highlight_on_clicked_word(self):
        window = MainWindow()
        card = SentenceCard(Sentence("Bonjour tout le monde."))
        window.active_card = card
        window.active_start_word = 2
        window._active_source = "word"

        window._update_word_highlight(500)

        self.assertEqual(card.highlight_index, 2)

    def test_history_selection_restores_full_text_to_editor(self):
        window = MainWindow()
        saved_text = "Bonjour !\nComment allez-vous ?"
        window.history.recent = lambda _limit: [(saved_text, "2026-09-09 12:00:00")]

        window.refresh_history()
        window.restore_history_item(window.history_list.item(0))

        self.assertEqual(window.input.toPlainText(), saved_text)
        self.assertEqual(window.history_list.count(), 1)


if __name__ == "__main__":
    unittest.main()
