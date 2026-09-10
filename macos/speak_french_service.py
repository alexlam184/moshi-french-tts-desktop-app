#!/usr/bin/env python3
"""Automator/Services helper: forwards selected text to Moshi French TTS."""

import os
import shlex
import subprocess
import sys

from PySide6.QtCore import QSettings


def main() -> int:
    text = sys.stdin.read().strip()
    if not text:
        return 0
    pending = QSettings("FrenchLearningApp", "French Learning App")
    pending.setValue("quickTts/pendingText", text)
    pending.sync()
    configured_command = os.environ.get("FRENCH_LEARNING_COMMAND", "").strip()
    command = shlex.split(configured_command) if configured_command else [
        sys.executable, "-m", "french_learning_app",
    ]
    try:
        subprocess.Popen(
            [*command, "--quick-tts", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        print(f"Could not start Moshi French TTS: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
