"""Operaciones de archivo reutilizables (DRY: crear carpetas, limpiar temporales)."""
from datetime import datetime
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger()


def ensure_dir(path: Path) -> None:
    """Crea el directorio si no existe; lanza si no hay permisos."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise PermissionError(f"Sin permisos para crear directorio: {path}") from exc


def clean_temp_files(paths: list[Path]) -> None:
    """Elimina archivos temporales en silencio (no lanza si no existen)."""
    for path in paths:
        try:
            if path.exists():
                path.unlink()
                logger.debug("Archivo temporal eliminado: %s", path)
        except Exception as exc:
            logger.warning("No se pudo eliminar archivo temporal %s: %s", path, exc)


def generate_output_dir(video_name: str, base_dir: Path) -> Path:
    """Genera un directorio de salida único: base_dir/YYYYMMDD_HHMMSS_<nombre>."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in video_name)
    safe_name = safe_name[:40]
    output_dir = base_dir / f"{timestamp}_{safe_name}"
    ensure_dir(output_dir)
    return output_dir
