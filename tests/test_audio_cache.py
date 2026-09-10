import tempfile
import unittest
from pathlib import Path

from french_learning_app.services.audio_cache import AudioCache


class AudioCacheTests(unittest.TestCase):
    def test_clear_removes_only_cached_audio_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = AudioCache(Path(temp_dir))
            (cache.directory / "first.wav").write_bytes(b"audio")
            (cache.directory / "second.aiff").write_bytes(b"audio")

            self.assertEqual(cache.clear(), 2)
            self.assertTrue(cache.directory.exists())
            self.assertEqual(list(cache.directory.iterdir()), [])
