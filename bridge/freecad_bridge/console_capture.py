"""Capture messages emitted by FreeCAD during one Bridge request.

FreeCAD's Report View is a Console observer. Reading its text before and after
an operation preserves messages from host-side FEM and meshing code that do not
otherwise reach the external client.
"""

MAX_CAPTURE_CHARS = 20_000


def report_view_text(gui):
    """Return the current Report View text, or ``None`` when it is unavailable."""
    try:
        from PySide import QtWidgets
    except ImportError:  # Older FreeCAD PySide compatibility API.
        from PySide import QtGui as QtWidgets

    report_view = gui.getMainWindow().findChild(QtWidgets.QTextEdit, "Report view")
    if report_view is None:
        return None
    return str(report_view.toPlainText())


class ConsoleCapture:
    """Measure the Report View delta around exactly one host operation."""

    def __init__(self, reader, limit=MAX_CAPTURE_CHARS):
        self._reader = reader
        self._limit = int(limit)
        self._before = None
        self._start_error = None
        try:
            self._before = reader()
        except Exception as exc:
            self._start_error = "{}: {}".format(type(exc).__name__, exc)

    def finish(self):
        if self._start_error is not None:
            return self._unavailable(self._start_error)
        if self._before is None:
            return self._unavailable("report_view_unavailable")
        try:
            after = self._reader()
        except Exception as exc:
            return self._unavailable("{}: {}".format(type(exc).__name__, exc))
        if after is None:
            return self._unavailable("report_view_unavailable")

        history_reset = not after.startswith(self._before)
        text = after[len(self._before) :] if not history_reset else after
        truncated = len(text) > self._limit
        if truncated:
            text = text[-self._limit :]
        return {
            "channel": "freecad_report_view",
            "capture_available": True,
            "text": text,
            "truncated": truncated,
            "history_reset": history_reset,
        }

    @staticmethod
    def _unavailable(reason):
        return {
            "channel": "freecad_report_view",
            "capture_available": False,
            "text": "",
            "truncated": False,
            "history_reset": False,
            "reason": str(reason),
        }
