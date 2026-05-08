"""Utilidades para verificar y solicitar privilegios de administrador en Windows."""
import sys
from pathlib import Path


def is_admin() -> bool:
    """Retorna True si el proceso tiene privilegios de administrador."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin() -> None:
    """Relanza la aplicación con privilegios de administrador vía UAC y cierra la actual."""
    if sys.platform != "win32":
        return
    import ctypes
    from PyQt6.QtWidgets import QApplication

    exe = sys.executable
    params = " ".join(f'"{a}"' for a in sys.argv) if sys.argv else ""
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    QApplication.quit()


def check_writable(path: Path) -> bool:
    """Verifica que el directorio sea escribible intentando crear un archivo test."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_test"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        return True
    except (PermissionError, OSError):
        return False


def get_free_space_mb(path: Path) -> float:
    """Retorna el espacio libre en MB en la unidad del path dado."""
    import shutil
    try:
        usage = shutil.disk_usage(path)
        return usage.free / (1024 * 1024)
    except Exception:
        return float("inf")
