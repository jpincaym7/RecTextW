"""Verificación del modelo Whisper descargado localmente."""
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger()

_WHISPER_CACHE_DIR = Path.home() / ".cache" / "whisper"
_MODEL_FILES = {
    "medium": "medium.pt",
    "small": "small.pt",
    "large": "large.pt",
    "base": "base.pt",
    "tiny": "tiny.pt",
}


def is_model_available(model: str = "medium") -> bool:
    """Verifica si el modelo Whisper especificado está descargado localmente."""
    model_file = _WHISPER_CACHE_DIR / _MODEL_FILES.get(model, f"{model}.pt")
    available = model_file.exists() and model_file.stat().st_size > 1024 * 1024
    logger.debug("Modelo Whisper '%s' disponible: %s (%s)", model, available, model_file)
    return available


def get_model_path(model: str = "medium") -> Path | None:
    """Retorna la ruta local del modelo si existe, None si no."""
    model_file = _WHISPER_CACHE_DIR / _MODEL_FILES.get(model, f"{model}.pt")
    return model_file if model_file.exists() else None
