# Moshi French TTS

A cross-platform PySide6 app for turning pasted French into sentence-by-sentence listening practice. It works immediately without cloud credentials or Piper by using the built-in macOS or Windows speech service. Translation and IPA are intentionally provider interfaces, so a future service can be added without changing the UI.

## Features

- Paste a large French passage and split it into sentence cards.
- Play, pause, stop, rewind 10 seconds, or fast-forward 10 seconds.
- Highlight the current spoken word (estimated from audio progress).
- Hover a word during playback to repeat it; move away to continue from the following word.
- A playing sentence's own button changes to Pause, then Resume when paused.
- Expand the triangle before a sentence to show or hide its IPA and meaning.
- Sentence rows are borderless; only the currently playing row receives a light-grey background.
- Single-click a word to play only that word; double-click it to play the sentence from that word.
- Select an engine, voice, and speech speed from the main player.
- Built-in safe fallback when Piper or an online provider is unavailable.
- SQLite history and local JSON settings.
- Disk-backed generated-audio cache with a manual clear button; a normal app Quit also clears it.
- System / Browser TTS, Piper, Supertonic HD, and an online-engine extension point.
- Responsive workspace: side-by-side text/audio panes on wide screens and stacked panes on narrow screens.
- Non-blocking speech synthesis so local model work does not freeze the interface.
- Single-instance behavior: launching the app again activates the existing copy.
- Supertonic preloads in the background and remains in memory until the app quits.
- macOS Quick TTS: select text anywhere, use **Services → Speak French**, and play it
  from a menu-bar popover without reopening the main window.

## Setup

Use Python 3.11 or newer. Create a virtual environment in the project folder, then install dependencies.

Run these commands from the **`moshi-french-tts-desktop-app` folder**—the one containing `README.md`, `requirements.txt`, and the inner `french_learning_app` package. Do not run `__main__.py` directly.

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m french_learning_app
```

### Windows (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m french_learning_app
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` and try again.

## Optional Piper setup

Install Piper and a French voice model, then set **Piper executable** and **Piper voice model** in Settings. The app invokes Piper with `--output_file`; its synthesized WAV result is stored in the local cache and played by the app. If Piper is not configured, the app keeps running and explains what is missing.

## Adding an online provider

`OnlineTTSEngine` is a structured placeholder in `french_learning_app/services/tts/online.py`. Add an Azure Speech or Google Cloud client in `synthesize`, return its audio bytes plus a MIME type, and register provider settings in the settings dialog. No API keys are embedded or required by this MVP.

## Supertonic HD (local neural voice)

Supertonic is included in `requirements.txt`. Select **Supertonic HD (local)** in the app, then choose one of its built-in voice names (`F1` is the default) in Settings. On its first use it downloads the local model assets (about 400 MB); afterward it synthesizes locally and needs no API key or internet connection. French is passed to the engine with language code `fr`.

The Supertonic model has its own OpenRAIL-M license; review it before public distribution or commercial deployment.

## Voice and word timing notes

**System / Browser TTS** maps to the native voice service (`say` on macOS and System.Speech on Windows), so it needs no browser, account, or API key. Available voices vary by operating system. Piper voices come from the configured `.onnx` model; choose a different Piper model in Settings to change that voice.

Piper and Supertonic do not currently return word timestamps. The app therefore estimates the highlighted word from playback position and word length. Hovering a word generates audio from that exact word, so the jump itself is precise even though the moving highlight is approximate.

## Data locations

The app stores settings, history, and generated audio in your user data directory:

- macOS: `~/Library/Application Support/FrenchLearningApp`
- Windows: `%APPDATA%\\FrenchLearningApp`

Generated audio remains available during the current session for faster repeated playback.
Use **Settings → Clear generated audio cache** to remove it immediately. A normal **Quit**
from the menu-bar app also clears generated audio. Downloaded Piper/Supertonic model files,
settings, and text history are not removed.

## macOS Quick TTS Service

Quick TTS uses a local operating-system socket, not a web server. The service forwards
selected text to the running app; if it is not running, it starts the app and opens the
Quick TTS controls as a menu-bar popover.

First install the app command while the virtual environment is active:

    pip install -e .

Then create the macOS right-click service once:

1. Open **Automator** and create a **Quick Action**.
2. Set “Workflow receives current” to **text** in **any application**.
3. Add **Run Shell Script**, set “Pass input” to **to stdin**, and paste the contents
   of macos/automator-speak-french.sh after replacing PROJECT_DIR with this project’s
   full path.
4. Save it as **Speak French**.

You can now select French text in another macOS app, right-click it, choose
**Services → Speak French**, and use the menu-bar player. It offers Supertonic HD
and Piper, keeps a separate remembered voice for each model, defaults to Supertonic HD at
1.0×, and provides exactly 0.5×, 0.75×, 1.0×, and 1.25× speeds. Press **Space** to
play/stop and **Esc** or **Command-W** to close the menu.

When the main window is closed it hides to the menu bar. Use the menu-bar icon for
the Quick TTS player, **Open Main Window**, or **Quit**.

## Checks

```bash
python -m compileall french_learning_app
python -m unittest discover -s tests
```
