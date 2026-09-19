"""Qt local-socket JSON-RPC server hosted inside FreeCAD."""

import json
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtNetwork

from .api import FreeCADAPI
from .console_capture import ConsoleCapture, report_view_text
from .errors import (
    BridgeError,
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    PARSE_ERROR,
)
from .security import PathPolicy


MAX_MESSAGE_BYTES = 1024 * 1024


def default_socket_path():
    configured = os.environ.get("CAE_BRIDGE_SOCKET")
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return os.path.join(runtime_dir, "opensource-cae-freecad.sock")
    return "/tmp/opensource-cae-freecad-{}.sock".format(os.getuid())


class BridgeServer(QtCore.QObject):
    def __init__(self, socket_path=None, path_policy=None, parent=None):
        super().__init__(parent)
        self.socket_path = socket_path or default_socket_path()
        self.path_policy = path_policy or PathPolicy.from_environment()
        self.api = FreeCADAPI(self.path_policy, self.socket_path)
        self._server = QtNetwork.QLocalServer(self)
        self._buffers = {}
        # A GUI handler may call Gui.updateGui(), which re-enters the Qt event
        # loop. While that is happening the Bridge must not dispatch a second
        # request into FreeCAD, and it must not destroy a socket that Qt is
        # still delivering read notifications for.
        self._dispatch_depth = 0
        self._pending_delete = []
        self._server.newConnection.connect(self._accept_connections)

    @property
    def listening(self):
        return self._server.isListening()

    def start(self):
        if self.listening:
            return self.info()
        self._set_user_only_socket_option()
        if not self._server.listen(self.socket_path):
            if self._socket_is_stale():
                QtNetwork.QLocalServer.removeServer(self.socket_path)
                if not self._server.listen(self.socket_path):
                    raise RuntimeError(self._server.errorString())
            else:
                raise RuntimeError(
                    "Bridge socket is already in use: {} ({})".format(
                        self.socket_path, self._server.errorString()
                    )
                )
        if os.path.exists(self.socket_path):
            os.chmod(self.socket_path, 0o600)
        App.Console.PrintMessage("Open Source CAE Bridge listening at {}\n".format(self.socket_path))
        return self.info()

    def stop(self):
        for connection in list(self._buffers):
            try:
                connection.disconnectFromServer()
            except RuntimeError:
                pass
        self._buffers.clear()
        self._server.close()
        QtNetwork.QLocalServer.removeServer(self.socket_path)

    def info(self):
        return {
            "socket": self.socket_path,
            "listening": self.listening,
            "allowed_roots": self.path_policy.describe(),
        }

    def _set_user_only_socket_option(self):
        try:
            option = QtNetwork.QLocalServer.UserAccessOption
        except AttributeError:
            option = QtNetwork.QLocalServer.SocketOption.UserAccessOption
        self._server.setSocketOptions(option)

    def _socket_is_stale(self):
        probe = QtNetwork.QLocalSocket()
        probe.connectToServer(self.socket_path)
        connected = probe.waitForConnected(150)
        if connected:
            probe.disconnectFromServer()
        return not connected

    def _accept_connections(self):
        while self._server.hasPendingConnections():
            connection = self._server.nextPendingConnection()
            self._buffers[connection] = bytearray()
            connection.readyRead.connect(
                lambda connection=connection: self._read_connection(connection)
            )
            connection.disconnected.connect(
                lambda connection=connection: self._drop_connection(connection)
            )

    def _drop_connection(self, connection):
        self._buffers.pop(connection, None)
        if self._dispatch_depth:
            # Destroying the socket from inside a nested event loop frees it
            # while Qt still holds a live read notification for it, which
            # segfaults FreeCAD. Wait until the request stack has unwound.
            if connection not in self._pending_delete:
                self._pending_delete.append(connection)
            return
        connection.deleteLater()

    def _release_pending(self):
        pending, self._pending_delete = self._pending_delete, []
        for connection in pending:
            try:
                connection.deleteLater()
            except RuntimeError:
                pass

    def _read_connection(self, connection):
        buffer = self._buffers.get(connection)
        if buffer is None:
            return
        try:
            buffer.extend(bytes(connection.readAll()))
        except RuntimeError:
            self._buffers.pop(connection, None)
            return
        self._drain(connection)

    def _drain(self, connection):
        buffer = self._buffers.get(connection)
        if buffer is None:
            return
        if self._dispatch_depth:
            # Re-entered through Gui.updateGui(); keep the bytes and come back
            # once the in-flight request has returned.
            QtCore.QTimer.singleShot(0, lambda: self._drain(connection))
            return
        if len(buffer) > MAX_MESSAGE_BYTES and b"\n" not in buffer:
            self._write_error(connection, None, INVALID_REQUEST, "Message exceeds 1 MiB")
            connection.disconnectFromServer()
            return
        while b"\n" in buffer:
            raw, remainder = buffer.split(b"\n", 1)
            buffer[:] = remainder
            if not raw.strip():
                continue
            if len(raw) > MAX_MESSAGE_BYTES:
                self._write_error(connection, None, INVALID_REQUEST, "Message exceeds 1 MiB")
                continue
            self._handle_message(connection, raw)
            if self._buffers.get(connection) is not buffer:
                return
        if len(buffer) > MAX_MESSAGE_BYTES:
            self._write_error(connection, None, INVALID_REQUEST, "Message exceeds 1 MiB")
            connection.disconnectFromServer()

    def _handle_message(self, connection, raw):
        self._dispatch_depth += 1
        try:
            self._dispatch_message(connection, raw)
        finally:
            self._dispatch_depth -= 1
            if not self._dispatch_depth and self._pending_delete:
                self._release_pending()

    def _dispatch_message(self, connection, raw):
        request_id = None
        console = ConsoleCapture(lambda: report_view_text(Gui))
        try:
            try:
                request = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                raise BridgeError(PARSE_ERROR, "Parse error", {"detail": str(exc)})
            if not isinstance(request, dict):
                raise BridgeError(INVALID_REQUEST, "Request must be an object")
            request_id = request.get("id")
            if request.get("jsonrpc") != "2.0":
                raise BridgeError(INVALID_REQUEST, "jsonrpc must be 2.0")
            method = request.get("method")
            if not isinstance(method, str) or not method:
                raise BridgeError(INVALID_REQUEST, "method must be a non-empty string")
            params = request.get("params", {})
            if not isinstance(params, dict):
                raise BridgeError(INVALID_PARAMS, "params must be an object")
            result = self.api.dispatch(method, params)
            if "id" in request:
                self._write(
                    connection,
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": self._with_host_messages(result, console.finish()),
                    },
                )
        except BridgeError as exc:
            self._write_error(
                connection,
                request_id,
                exc.code,
                exc.message,
                self._with_error_messages(exc.data, console.finish()),
            )
        except Exception as exc:
            App.Console.PrintError("Bridge internal error: {}\n".format(exc))
            self._write_error(
                connection,
                request_id,
                INTERNAL_ERROR,
                "Internal error",
                self._with_error_messages(
                    {"type": type(exc).__name__}, console.finish()
                ),
            )

    @staticmethod
    def _with_host_messages(result, host_messages):
        if not isinstance(result, dict):
            return {"value": result, "host_messages": host_messages}
        result = dict(result)
        result["host_messages"] = host_messages
        return result

    @staticmethod
    def _with_error_messages(data, host_messages):
        if data is None:
            result = {}
        elif isinstance(data, dict):
            result = dict(data)
        else:
            result = {"detail": data}
        result["host_messages"] = host_messages
        return result

    def _write_error(self, connection, request_id, code, message, data=None):
        error = {"code": int(code), "message": str(message)}
        if data is not None:
            error["data"] = data
        self._write(connection, {"jsonrpc": "2.0", "id": request_id, "error": error})

    @staticmethod
    def _write(connection, payload):
        """Write one response, tolerating a peer that vanished mid-request.

        A slow GUI call can outlive the client's timeout. By the time the handler
        returns, Qt may already have deleted the socket, so writing must never
        raise back into the event loop or into the error path below.
        """
        encoded = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        try:
            connection.write(encoded)
            connection.flush()
        except RuntimeError:
            return False
        return True
