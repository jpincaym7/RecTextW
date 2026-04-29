"""Validaciones reutilizables (paths, API keys, formatos de archivo)."""
import re
from pathlib import Path

from app.config import SUPPORTED_VIDEO_FORMATS


def is_valid_video_path(path: Path) -> bool:
    """Verifica que el path es un archivo de video soportado y existe."""
    return path.exists() and path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_FORMATS


def is_valid_api_key(key: str, provider: str) -> bool:
    """Validación superficial de formato de API key por proveedor."""
    if not key or len(key.strip()) < 8:
        return False
    patterns = {
        "gemini": r"^AIza[0-9A-Za-z_\-]{35,}$",
        "groq": r"^gsk_[0-9A-Za-z]{48,}$",
        "openrouter": r"^sk-or-[0-9A-Za-z_\-]{30,}$",
    }
    pattern = patterns.get(provider)
    if pattern:
        return bool(re.match(pattern, key.strip()))
    return len(key.strip()) >= 16


def is_writable_dir(path: Path) -> bool:
    """Verifica que el directorio existe y es escribible."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        return True
    except Exception:
        return False
