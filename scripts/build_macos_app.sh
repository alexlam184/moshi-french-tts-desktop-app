#!/bin/zsh
# Build Moshi French TTS as a double-clickable macOS application bundle.
# Run from any directory: ./scripts/build_macos_app.sh

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  print -u2 "This builder must run on macOS because it creates a .app bundle."
  exit 1
fi

PROJECT_DIR="${0:A:h:h}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"
APP_NAME="Moshi French TTS"
DIST_APP="$PROJECT_DIR/dist/$APP_NAME.app"
ICON_TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/moshi-icon.XXXXXX")"
ICONSET_DIR="$ICON_TEMP_DIR/moshi_french_tts.iconset"
ICON_PATH="$PROJECT_DIR/build/moshi_french_tts.icns"

cleanup() {
  rm -rf "$ICON_TEMP_DIR"
}
trap cleanup EXIT

if [[ ! -x "$PYTHON_BIN" ]]; then
  print -u2 "Python was not found at $PYTHON_BIN"
  print -u2 "Create the virtual environment first, or set PYTHON_BIN to the desired Python executable."
  exit 1
fi

if ! "$PYTHON_BIN" -c 'import PyInstaller' 2>/dev/null; then
  print -u2 "PyInstaller is not installed in this environment."
  print -u2 "Run: $PYTHON_BIN -m pip install '.[macos-build]'"
  exit 1
fi

mkdir -p "$PROJECT_DIR/build"
mkdir "$ICONSET_DIR"
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$PROJECT_DIR/french_learning_app/assets/moshi_french_tts_logo.png" \
    --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null
  double_size=$((size * 2))
  sips -z "$double_size" "$double_size" "$PROJECT_DIR/french_learning_app/assets/moshi_french_tts_logo.png" \
    --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET_DIR" -o "$ICON_PATH"

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --osx-bundle-identifier "com.alexlam.moshifrenchtts" \
  --icon "$ICON_PATH" \
  --paths "$PROJECT_DIR" \
  --add-data "$PROJECT_DIR/french_learning_app/assets:french_learning_app/assets" \
  --collect-all supertonic \
  --collect-all piper \
  --hidden-import piper.voice \
  --distpath "$PROJECT_DIR/dist" \
  --workpath "$PROJECT_DIR/build/pyinstaller" \
  --specpath "$PROJECT_DIR/build" \
  "$PROJECT_DIR/packaging/macos/app_entry.py"

if [[ ! -d "$DIST_APP" ]]; then
  print -u2 "PyInstaller did not create the expected app bundle: $DIST_APP"
  exit 1
fi

plutil -replace CFBundleDisplayName -string "$APP_NAME" "$DIST_APP/Contents/Info.plist"
codesign --force --deep --sign - "$DIST_APP"

print "Built: $DIST_APP"
print "Install it by dragging it to /Applications, then open it normally."
print "For sharing with other Macs, sign and notarize the app with an Apple Developer ID."
