"""Piper launcher with a short pronunciation-data path for macOS."""
import argparse
import sys
import tempfile
import wave
from pathlib import Path


def main():
    import piper
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output_file", required=True)
    args = parser.parse_args()
    data = Path(piper.__file__).parent / "espeak-ng-data"
    # eSpeak cannot reliably initialize with the long nested project path.
    # A temporary alias keeps the installed package intact.
    with tempfile.TemporaryDirectory(prefix="moshi-piper-") as directory:
        short = Path(directory) / "espeak-ng-data"
        if sys.platform == "darwin":
            short.symlink_to(data, target_is_directory=True)
        else:
            short = data
        voice = piper.PiperVoice.load(args.model, espeak_data_dir=short)
        with wave.open(args.output_file, "wb") as output:
            voice.synthesize_wav(sys.stdin.read(), output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
