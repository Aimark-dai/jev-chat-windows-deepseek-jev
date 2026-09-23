"""Fail a Windows build if the packaged QtCore cannot load its native DLLs."""

import ctypes
import os
import sys
from pathlib import Path


def check(bundle: Path) -> None:
    if sys.platform != "win32":
        raise RuntimeError("Qt bundle check must run on Windows")
    internal = bundle.resolve() / "_internal"
    qt = internal / "PySide6"
    core = qt / "QtCore.pyd"
    if not core.is_file():
        raise FileNotFoundError(core)
    handles = [os.add_dll_directory(str(path)) for path in
               (internal, qt, internal / "shiboken6")]
    try:
        ctypes.WinDLL(str(core))
    finally:
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tools/check_bundle_qt.py <bundle-folder>")
    check(Path(sys.argv[1]))
    print("Packaged QtCore loaded successfully")
