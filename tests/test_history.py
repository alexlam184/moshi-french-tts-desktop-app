import tempfile
import unittest
from pathlib import Path

from french_learning_app.services.history import HistoryStore


class HistoryStoreTests(unittest.TestCase):
    def test_keeps_only_the_latest_twenty_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = HistoryStore(Path(temp_dir))
            for number in range(21):
                store.save(f"Text {number}")

            saved_texts = [source_text for source_text, _created_at in store.recent()]
            store.close()

        self.assertEqual(saved_texts, [f"Text {number}" for number in range(20, 0, -1)])
