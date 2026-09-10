from pathlib import Path
from .base import TTSEngine, TTSResult


class OnlineTTSEngine(TTSEngine):
    """Provider seam for Azure Speech or Google Cloud; no network/config required yet."""
    name = "Online (configure later)"

    def synthesize(self, text: str, speed: float, cache_path: Path) -> TTSResult:
        return TTSResult(message="Online TTS is not configured yet. Add Azure or Google Cloud credentials in a future provider implementation.")
