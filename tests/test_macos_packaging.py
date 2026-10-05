import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MacOSPackagingTests(unittest.TestCase):
    def test_macos_builder_is_kept_in_source_control(self):
        builder = PROJECT_ROOT / "scripts" / "build_macos_app.sh"
        source = builder.read_text()

        self.assertIn("PyInstaller", source)
        self.assertIn("--windowed", source)
        self.assertIn("--osx-bundle-identifier", source)
        self.assertIn("codesign --force --deep --sign -", source)
        self.assertIn("--collect-all supertonic", source)
        self.assertIn("--collect-all piper", source)
        self.assertNotIn("piper_phonemize", source)

    def test_installed_app_service_launches_the_app_bundle(self):
        service = (PROJECT_ROOT / "macos" / "automator-speak-french-app.sh").read_text()

        self.assertIn('/Applications/Moshi French TTS.app', service)
        self.assertIn('open "$APP_PATH" --args --quick-tts "$text"', service)

    def test_pyproject_has_an_opt_in_macos_build_dependency(self):
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()

        self.assertIn("macos-build", pyproject)
        self.assertIn("pyinstaller", pyproject)
