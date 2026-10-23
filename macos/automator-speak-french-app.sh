#!/bin/zsh
# Paste this into an Automator Quick Action's “Run Shell Script” action after
# building and installing Moshi French TTS.app in /Applications.
# Configure Automator: Workflow receives current “text” in “any application”;
# Pass input: “to stdin”.

set -euo pipefail

APP_PATH="/Applications/Moshi French TTS.app"
text="$(cat)"

if [[ -z "${text//[[:space:]]/}" ]]; then
  exit 0
fi

if [[ ! -d "$APP_PATH" ]]; then
  osascript -e 'display alert "Moshi French TTS is not installed" message "Move Moshi French TTS.app to /Applications, then try again."' >&2
  exit 1
fi

# A second launch forwards --quick-tts through the app's local IPC socket to
# the already-running menu-bar process; no duplicate app is kept open.
open "$APP_PATH" --args --quick-tts "$text"
