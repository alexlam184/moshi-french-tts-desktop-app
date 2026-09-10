import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QSettings, QTimer
from PySide6.QtGui import QCursor, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .services.audio_cache import AudioCache
from .services.paths import app_data_dir
from .services.quick_tts_ipc import QuickTTSIPC
from .services.settings import SettingsStore
from .services.tts_manager import TTSManager
from .ui.main_window import MainWindow
from .ui.quick_tts_popup import QuickTTSMenuPanel


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    app.setApplicationName("Moshi French TTS")
    app.setOrganizationName("FrenchLearningApp")
    logo_path = Path(__file__).with_name("assets") / "moshi_french_tts_logo.png"
    app_icon = QIcon(str(logo_path))
    app.setWindowIcon(app_icon)
    app.setQuitOnLastWindowClosed(False)
    quick_text = ""
    if "--quick-tts" in argv:
        index = argv.index("--quick-tts")
        if index + 1 < len(argv):
            quick_text = argv[index + 1].strip()
    if quick_text:
        if QuickTTSIPC.forward(quick_text):
            return 0
    elif QuickTTSIPC.forward(activate=True):
        # A normal second launch simply brings the existing copy forward.
        return 0

    window = MainWindow()
    window.set_close_to_tray(True)
    data_dir = app_data_dir()
    quick_panel = QuickTTSMenuPanel(TTSManager(SettingsStore(data_dir).load(), AudioCache(data_dir)))
    ipc = QuickTTSIPC(app)
    if not ipc.start():
        # Another process owns the local app socket.  Do not create a second
        # copy, even if it is an older app version that cannot acknowledge an
        # activation request.
        return 0

    tray = QSystemTrayIcon(app_icon, app)
    tray.setToolTip("Moshi French TTS")
    tray_menu = QMenu()
    open_action = tray_menu.addAction("Open Main Window")

    def show_main_window():
        window.showNormal()
        window.raise_()
        window.activateWindow()

    open_action.triggered.connect(show_main_window)
    tray_menu.addSeparator()
    quit_action = tray_menu.addAction("Quit")
    pending_text = QSettings("FrenchLearningApp", "French Learning App")

    def load_service_text():
        pending_text.sync()
        text = pending_text.value("quickTts/pendingText", "", type=str).strip()
        if text:
            quick_panel.show_text(text)
            pending_text.remove("quickTts/pendingText")
            pending_text.sync()

    service_text_timer = QTimer(app)
    service_text_timer.setInterval(250)
    service_text_timer.timeout.connect(load_service_text)
    service_text_timer.start()

    def open_quick_menu(text: str):
        quick_panel.show_text(text)
        tray_geometry = tray.geometry()
        if tray_geometry.isValid():
            position = QPoint(
                tray_geometry.right() - quick_panel.sizeHint().width() + 1,
                tray_geometry.bottom() + 1,
            )
        else:
            position = QCursor.pos()
        quick_panel.show_at(position)

    ipc.text_received.connect(open_quick_menu)
    ipc.activation_requested.connect(show_main_window)

    def tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            load_service_text()
            open_quick_menu(quick_panel.text_edit.toPlainText())

    tray.activated.connect(tray_activated)

    def quit_app():
        window.set_close_to_tray(False)
        quick_panel.release_resources()
        # Generated speech is a convenience cache, not a permanent library.
        # Stop players first, then remove cache files during an intentional quit.
        AudioCache(data_dir).clear()
        tray.hide()
        app.quit()

    quit_action.triggered.connect(quit_app)
    tray.setContextMenu(tray_menu)
    tray.show()
    window.show()
    # Warm Supertonic after the window and tray are available, never on the
    # UI thread. Its model is then ready when the menu-bar Play button is used.
    QTimer.singleShot(0, quick_panel.warm_supertonic)
    if quick_text:
        QTimer.singleShot(0, lambda: open_quick_menu(quick_text))
    return app.exec()
