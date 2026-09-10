import json
import platform
import shutil
import subprocess
from pathlib import Path

from .base import TTSEngine, TTSResult


class SystemEngine(TTSEngine):
    """Use the operating system's built-in speech service without an API key."""

    name = "System / Browser TTS"
    cache_suffix = ".aiff" if platform.system() == "Darwin" else ".wav"

    def __init__(self, voice: str = ""):
        self.voice = voice

    @staticmethod
    def available_voices() -> list[str]:
        try:
            if platform.system() == "Darwin" and shutil.which("say"):
                result = subprocess.run(
                    ["say", "-v", "?"], capture_output=True, text=True,
                    check=False, timeout=5,
                )
                french = []
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].lower().startswith("fr_"):
                        french.append(parts[0])
                return french
            if platform.system() == "Windows" and shutil.which("powershell"):
                script = (
                    "Add-Type -AssemblyName System.Speech; "
                    "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    "$s.GetInstalledVoices() | ForEach-Object {$_.VoiceInfo.Name}"
                )
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", script],
                    capture_output=True, text=True, check=False, timeout=8,
                )
                return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except (OSError, subprocess.SubprocessError):
            pass
        return []

    def synthesize(self, text: str, speed: float, cache_path: Path) -> TTSResult:
        if cache_path.exists():
            return TTSResult(cache_path, playback_rate=speed)
        try:
            if platform.system() == "Darwin" and shutil.which("say"):
                command = ["say"]
                if self.voice:
                    command.extend(["-v", self.voice])
                command.extend(["-o", str(cache_path), text])
                result = subprocess.run(
                    command, capture_output=True, text=True, check=False, timeout=120,
                )
            elif platform.system() == "Windows" and shutil.which("powershell"):
                payload = json.dumps({"text": text, "path": str(cache_path), "voice": self.voice})
                script = (
                    "$p=([Console]::In.ReadToEnd() | ConvertFrom-Json); "
                    "Add-Type -AssemblyName System.Speech; "
                    "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    "if ($p.voice) {$s.SelectVoice($p.voice)}; "
                    "$s.SetOutputToWaveFile($p.path); $s.Speak($p.text); $s.Dispose()"
                )
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", script], input=payload,
                    capture_output=True, text=True, check=False, timeout=120,
                )
            else:
                return TTSResult(message="System speech is unavailable. Choose Piper or Supertonic HD.")
        except (OSError, subprocess.SubprocessError) as exc:
            return TTSResult(message=f"System speech could not start: {exc}")

        if result.returncode != 0 or not cache_path.exists():
            detail = result.stderr.strip() or "No audio file was created."
            return TTSResult(message=f"System speech failed: {detail}")
        return TTSResult(cache_path, playback_rate=speed)
