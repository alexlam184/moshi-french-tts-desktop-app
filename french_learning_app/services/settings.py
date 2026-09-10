import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AppSettings:
    engine: str = "System / Browser TTS"
    speed: float = 0.75
    system_voice: str = ""
    piper_executable: str = ""
    piper_model: str = ""
    supertonic_voice: str = "F1"


class SettingsStore:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "settings.json"

    def load(self) -> AppSettings:
        try:
            return AppSettings(**json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
