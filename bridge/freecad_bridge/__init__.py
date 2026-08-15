"""Public lifecycle API for the in-process FreeCAD bridge.

FreeCAD imports are intentionally lazy so external adapters can import the
shared contract without loading FreeCAD.
"""


_server = None


def start(socket_path=None, path_policy=None):
    global _server
    if _server is not None and _server.listening:
        return _server
    from .server import BridgeServer

    _server = BridgeServer(socket_path=socket_path, path_policy=path_policy)
    _server.start()
    return _server


def stop():
    global _server
    if _server is not None:
        _server.stop()
        _server = None


def current():
    return _server


# Reloaded in dependency order. This package itself is deliberately absent: it
# holds _server, and reloading it would drop the only handle on the running
# Bridge.
_RELOADABLE = ("errors", "contract", "security", "api", "server")


def _reload_modules():
    import importlib
    import sys

    reloaded = []
    for suffix in _RELOADABLE:
        module = sys.modules.get("{}.{}".format(__name__, suffix))
        if module is not None:
            importlib.reload(module)
            reloaded.append(suffix)
    return reloaded


def reload_now():
    """Reload the Bridge modules in place and rebind the socket.

    Module reload happens before anything is torn down. If the new code does not
    import, the running Bridge is left untouched and serving, so a typo cannot
    strand FreeCAD without a Bridge.
    """
    global _server
    import FreeCAD as App

    if _server is None:
        raise RuntimeError("Bridge is not running")

    socket_path = _server.socket_path
    roots = _server.path_policy.describe()
    try:
        reloaded = _reload_modules()
    except Exception as exc:
        App.Console.PrintError(
            "Bridge reload failed, keeping the running Bridge: {}: {}\n".format(
                type(exc).__name__, exc
            )
        )
        return None

    previous = _server
    try:
        from .security import PathPolicy
        from .server import BridgeServer

        previous.stop()
        _server = BridgeServer(socket_path=socket_path, path_policy=PathPolicy(roots))
        _server.start()
    except Exception as exc:
        App.Console.PrintError("Bridge reload could not rebind: {}\n".format(exc))
        _server = previous
        try:
            _server.start()
        except Exception:
            App.Console.PrintError("Bridge is down; reload bootstrap.py manually.\n")
        return None

    from .contract import BRIDGE_VERSION

    App.Console.PrintMessage(
        "Bridge reloaded: version {}, modules {}\n".format(BRIDGE_VERSION, ", ".join(reloaded))
    )
    return _server


def schedule_reload(delay_ms=250):
    """Reload once the current request has been answered and the stack unwound."""
    from PySide import QtCore

    QtCore.QTimer.singleShot(int(delay_ms), reload_now)
