"""Navigate FreeCAD's 3D view with a game controller, such as a PlayStation DualSense, on macOS."""

import os
import sys

import FreeCAD as App

from . import commands

_navigator = None


def _add_package_dir():
    """Makes the packages that install.sh (and the Addon Manager) put in FreeCAD's user folder importable."""
    path = os.path.join(
        App.getUserAppDataDir(), "AdditionalPythonPackages", "py%d%d" % sys.version_info[:2]
    )
    if os.path.isdir(path) and path not in sys.path:
        sys.path.append(path)


def start():
    """Starts reading the controller. Calling it again returns the running navigator."""
    global _navigator
    if _navigator is None:
        _add_package_dir()
        from .gamepad import Gamepad
        from .navigator import Navigator

        _navigator = Navigator(Gamepad())
        _navigator.start()
    return _navigator


def toggle():
    start().toggle()
