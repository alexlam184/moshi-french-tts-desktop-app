import hashlib
from pathlib import Path


class AudioCache:
    """Small filesystem cache for synthesized audio, keyed by engine/text/speed."""
    def __init__(self, data_dir: Path):
        self.directory = data_dir / "audio_cache"
        self.directory.mkdir(exist_ok=True)

    def path_for(self, engine: str, text: str, speed: float, suffix: str = ".wav") -> Path:
        key = hashlib.sha256(f"{engine}|{speed}|{text}".encode()).hexdigest()
        return self.directory / f"{key}{suffix}"

    def clear(self) -> int:
        """Remove generated audio only; the cache directory itself remains."""
        removed = 0
        for item in self.directory.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                    removed += 1
                except OSError:
                    # Keep going so one locked audio file does not prevent the
                    # user from clearing the rest of the cache.
                    continue
        return removed
