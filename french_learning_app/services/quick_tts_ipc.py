import json
import os

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def socket_name() -> str:
    user_id = getattr(os, "getuid", lambda: 0)()
    return f"FrenchLearningAppQuickTTS-{user_id}"


class QuickTTSIPC(QObject):
    """A local socket relay for the macOS Service and a running app instance."""

    text_received = Signal(str)
    activation_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._accept_connection)

    def start(self) -> bool:
        name = socket_name()
        if self.server.listen(name):
            return True

        # Never take over a socket owned by a live copy of the app.  A failed
        # listen can also be caused by a stale socket left after a crash, so
        # remove it only after confirming nothing is listening there.
        probe = QLocalSocket()
        probe.connectToServer(name)
        if probe.waitForConnected(150):
            probe.disconnectFromServer()
            return False
        QLocalServer.removeServer(name)
        return self.server.listen(name)

    @staticmethod
    def forward(text: str = "", *, activate: bool = False, timeout_ms: int = 350) -> bool:
        """Deliver text to the running app, or ask it to bring itself forward."""
        socket = QLocalSocket()
        socket.connectToServer(socket_name())
        if not socket.waitForConnected(timeout_ms):
            return False
        payload = json.dumps({"text": text, "activate": activate}, ensure_ascii=False).encode("utf-8")
        if socket.write(payload) != len(payload):
            return False
        socket.flush()
        # The running app acknowledges receipt. This keeps the short-lived
        # macOS Service process alive until its selected text is delivered.
        return socket.waitForReadyRead(timeout_ms) and bytes(socket.readAll()) == b"OK"

    def _accept_connection(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.readyRead.connect(lambda sock=socket: self._read_socket(sock))
            socket.disconnected.connect(socket.deleteLater)

    def _read_socket(self, socket: QLocalSocket):
        try:
            payload = json.loads(bytes(socket.readAll()).decode("utf-8"))
            text = str(payload.get("text", "")).strip()
            activate = bool(payload.get("activate", False))
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError):
            text = ""
            activate = False
        if text:
            self.text_received.emit(text)
        if activate:
            self.activation_requested.emit()
        # Acknowledge every valid IPC request, including an activation-only
        # request, so a second launch can safely exit without becoming another
        # app instance.
        socket.write(b"OK")
        socket.flush()
        socket.disconnectFromServer()
