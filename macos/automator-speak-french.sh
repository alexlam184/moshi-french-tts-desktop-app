#!/bin/zsh
# Paste this into an Automator Quick Action's “Run Shell Script” action.
# Configure Automator: Workflow receives current “text” in “any application”;
# Pass input: “to stdin”.

PROJECT_DIR="/REPLACE/WITH/THE/moshi-french-tts-desktop-app/FOLDER"
export PATH="$PROJECT_DIR/.venv/bin:$PATH"
exec "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/macos/speak_french_service.py"
