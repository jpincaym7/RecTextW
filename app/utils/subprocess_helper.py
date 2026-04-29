"""Wrappers de subprocess que ocultan la ventana de consola en Windows.

En PyInstaller --windowed (console=False) la app no tiene consola, pero los
hijos creados con subprocess sí abren una ventana de cmd negra a menos que se
pase creationflags=CREATE_NO_WINDOW. Estos wrappers normalizan ese flag.
"""
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000  # Windows-only; ignorado en otras plataformas


def _hidden_kwargs(kwargs: dict) -> dict:
    if sys.platform == "win32":
        kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
    return kwargs


def run_hidden(cmd, **kwargs):
    return subprocess.run(cmd, **_hidden_kwargs(kwargs))


def popen_hidden(cmd, **kwargs):
    return subprocess.Popen(cmd, **_hidden_kwargs(kwargs))
