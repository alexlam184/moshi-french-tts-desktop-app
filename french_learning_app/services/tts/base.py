from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TTSResult:
    audio_path: Path | None = None
    message: str = ""
    playback_rate: float = 1.0


class TTSEngine(ABC):
    name: str
    cache_suffix: str = ".wav"

    @abstractmethod
    def synthesize(self, text: str, speed: float, cache_path: Path) -> TTSResult:
        """Return cached/generated audio, or an explanatory message without raising."""
