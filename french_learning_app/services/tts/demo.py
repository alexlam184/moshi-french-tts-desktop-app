from pathlib import Path
from .base import TTSEngine, TTSResult


class DemoEngine(TTSEngine):
    name = "Demo (no setup)"

    def synthesize(self, text: str, speed: float, cache_path: Path) -> TTSResult:
        return TTSResult(message="Demo voice selected. Configure Piper in Settings to play offline audio.")
