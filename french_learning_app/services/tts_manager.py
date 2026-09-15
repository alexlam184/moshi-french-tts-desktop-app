from pathlib import Path

from .audio_cache import AudioCache
from .settings import AppSettings
from .tts import PiperEngine, SupertonicEngine, SystemEngine, TTSResult


class TTSManager:
    """Creates local TTS engines for the compact player without UI coupling."""

    SUPERTONIC_MODEL = "Supertonic HD"
    PIPER_MODEL = "Piper"
    SYSTEM_MODEL = SystemEngine.name

    def __init__(self, settings: AppSettings, cache: AudioCache):
        self.settings = settings
        self.cache = cache
        self._engines: dict[tuple[str, str], PiperEngine | SupertonicEngine | SystemEngine] = {}

    @staticmethod
    def models() -> list[str]:
        return [TTSManager.SUPERTONIC_MODEL, TTSManager.PIPER_MODEL, TTSManager.SYSTEM_MODEL]

    def voices_for(self, model: str) -> list[str]:
        if model == self.SYSTEM_MODEL:
            return SystemEngine.available_voices() or ["System default"]
        if model == self.SUPERTONIC_MODEL:
            return ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "M5"]
        if self.settings.piper_model:
            return [Path(self.settings.piper_model).stem]
        return ["Configure Piper in Settings"]

    def synthesize(self, model: str, voice: str, text: str, speed: float) -> TTSResult:
        engine = self._engine_for(model, voice)
        cache_path = self.cache.path_for(
            f"quick-tts|{model}|{voice}", text, speed, suffix=engine.cache_suffix,
        )
        return engine.synthesize(text, speed, cache_path)

    def preload(self, model: str | None = None, voice: str = "F1") -> str:
        """Warm a local neural engine without generating speech."""
        model = model or self.SUPERTONIC_MODEL
        engine = self._engine_for(model, voice)
        if isinstance(engine, SupertonicEngine):
            return engine.preload()
        return ""

    def release_loaded_models(self):
        """Drop references to local TTS models before the app process exits."""
        self._engines.clear()

    def _engine_for(self, model: str, voice: str):
        key = (model, voice)
        if key not in self._engines:
            if model == self.PIPER_MODEL:
                self._engines[key] = PiperEngine(self.settings.piper_executable, self.settings.piper_model)
            elif model == self.SYSTEM_MODEL:
                self._engines[key] = SystemEngine("" if voice == "System default" else voice)
            else:
                self._engines[key] = SupertonicEngine(voice)
        return self._engines[key]
