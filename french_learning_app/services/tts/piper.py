import subprocess
from pathlib import Path
from .base import TTSEngine, TTSResult


class PiperEngine(TTSEngine):
    name = "Piper (offline)"

    def __init__(self, executable: str = "", model: str = ""):
        self.executable, self.model = executable, model

    def synthesize(self, text: str, speed: float, cache_path: Path) -> TTSResult:
        if cache_path.exists():
            return TTSResult(audio_path=cache_path, playback_rate=speed)
        if not self.executable or not self.model:
            return TTSResult(message="Piper needs an executable and French voice model. Set both in Settings.")
        if not Path(self.executable).exists() or not Path(self.model).exists():
            return TTSResult(message="Piper executable or voice model path was not found. Check Settings.")
        try:
            subprocess.run([self.executable, "--model", self.model, "--output_file", str(cache_path)], input=text,
                           text=True, check=True, capture_output=True, timeout=60)
            return TTSResult(audio_path=cache_path, playback_rate=speed)
        except (OSError, subprocess.SubprocessError) as exc:
            return TTSResult(message=f"Piper could not create audio: {exc}")
