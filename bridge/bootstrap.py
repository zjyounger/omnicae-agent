"""Load this file with the FreeCAD GUI to start the bridge."""

import os
import sys
from pathlib import Path

import FreeCAD as App


bridge_root = Path(__file__).resolve().parent
if str(bridge_root) not in sys.path:
    sys.path.insert(0, str(bridge_root))

from freecad_bridge import start  # noqa: E402


server = start()
App.Console.PrintMessage(
    "Bridge ready: {}\nAllowed roots: {}\n".format(
        server.socket_path,
        ", ".join(server.path_policy.describe()),
    )
)
