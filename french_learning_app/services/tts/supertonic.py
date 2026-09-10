from pathlib import Path
from threading import RLock

from .base import TTSEngine, TTSResult


class SupertonicEngine(TTSEngine):
    """Local Supertonic 3 engine. The package downloads model assets on first use."""
    name = "Supertonic HD (local)"

    def __init__(self, voice: str = "F1"):
        self.voice = voice if voice in {"M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"} else "F1"
        self._tts = None
        self._load_lock = RLock()

    def preload(self) -> str:
        """Load the neural model once, ready for the first playback request."""
        try:
            self._get_tts()
        except Exception as exc:
            return f"Supertonic could not load: {exc}"
        return ""

    def _get_tts(self):
        with self._load_lock:
            if self._tts is not None:
                return self._tts
            try:
                from supertonic import TTS
            except ImportError as exc:
                raise RuntimeError(
                    "Supertonic is not installed. In the app folder, run: pip install -r requirements.txt"
                ) from exc
            # This may download model files the first time. Keeping the object
            # alive makes every later menu-bar request avoid that load.
            self._tts = TTS(auto_download=True)
            return self._tts

    def synthesize(self, text: str, speed: float, cache_path: Path) -> TTSResult:
        if cache_path.exists():
            return TTSResult(audio_path=cache_path)
        try:
            # Synthesis is also guarded because the model is reused by the
            # background preload and the player worker.
            with self._load_lock:
                tts = self._get_tts()
                style = tts.get_voice_style(voice_name=self.voice)
                # Supertonic's documented natural range begins at 0.7×.
                wav, _ = tts.synthesize(text=text, voice_style=style, speed=max(0.7, speed), lang="fr", verbose=False)
                tts.save_audio(wav, str(cache_path))
            return TTSResult(audio_path=cache_path)
        except Exception as exc:  # Third-party model/runtime errors are shown without crashing the app.
            return TTSResult(message=f"Supertonic could not create audio: {exc}")
