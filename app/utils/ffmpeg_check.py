"""Detección, validación y descarga automática de FFmpeg."""
import shutil
import zipfile
from pathlib import Path
from typing import Callable

from app.utils.logger import get_logger
from app.utils.subprocess_helper import run_hidden

logger = get_logger()


def _candidate_dirs() -> list[Path]:
    """Retorna los directorios donde buscar FFmpeg, en orden de prioridad."""
    from app.config import FFMPEG_BUNDLED_DIR, FFMPEG_LOCAL_DIR, FFMPEG_DIR
    return [FFMPEG_BUNDLED_DIR, FFMPEG_LOCAL_DIR, FFMPEG_DIR]


def find_ffmpeg() -> Path | None:
    """Busca ffmpeg.exe en todas las ubicaciones conocidas, luego en PATH."""
    for directory in _candidate_dirs():
        for name in ("ffmpeg.exe", "ffmpeg"):
            candidate = directory / name
            if candidate.exists():
                logger.debug("FFmpeg encontrado en: %s", candidate)
                return candidate
    system = shutil.which("ffmpeg")
    if system:
        return Path(system)
    return None


def find_ffprobe() -> Path | None:
    """Busca ffprobe.exe en todas las ubicaciones conocidas, luego en PATH."""
    for directory in _candidate_dirs():
        for name in ("ffprobe.exe", "ffprobe"):
            candidate = directory / name
            if candidate.exists():
                return candidate
    system = shutil.which("ffprobe")
    if system:
        return Path(system)
    return None


def validate_ffmpeg(path: Path) -> bool:
    """Ejecuta ffmpeg -version y verifica que responde correctamente."""
    try:
        result = run_hidden(
            [str(path), "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "ffmpeg version" in result.stdout.lower()
    except Exception as exc:
        logger.debug("FFmpeg no válido en %s: %s", path, exc)
        return False


def download_ffmpeg(
    progress_callback: Callable[[float, str], None] | None = None,
) -> Path:
    """
    Descarga el build estático de FFmpeg para Windows x64 y lo extrae
    en tools/ffmpeg/bin/ (directorio del proyecto).

    Retorna la ruta al ejecutable ffmpeg.exe extraído.
    """
    import urllib.request
    import io
    from app.config import FFMPEG_LOCAL_DIR, FFMPEG_DOWNLOAD_URL

    dest_dir = FFMPEG_LOCAL_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Si ya existe, no re-descargar
    existing = dest_dir / "ffmpeg.exe"
    if existing.exists() and validate_ffmpeg(existing):
        logger.info("FFmpeg ya existe en %s, saltando descarga", existing)
        return existing

    if progress_callback:
        progress_callback(0.0, "Descargando FFmpeg para Windows...")

    logger.info("Descargando FFmpeg desde %s", FFMPEG_DOWNLOAD_URL)

    def reporthook(block_num, block_size, total_size):
        if total_size > 0 and progress_callback:
            downloaded = min(block_num * block_size, total_size)
            pct = downloaded / total_size
            mb_done = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            progress_callback(pct * 0.8, f"Descargando FFmpeg... {mb_done:.0f} MB / {mb_total:.0f} MB")

    try:
        tmp_zip, _ = urllib.request.urlretrieve(FFMPEG_DOWNLOAD_URL, reporthook=reporthook)
    except Exception as exc:
        raise RuntimeError(f"No se pudo descargar FFmpeg: {exc}") from exc

    if progress_callback:
        progress_callback(0.85, "Extrayendo FFmpeg...")

    logger.info("Extrayendo FFmpeg...")
    try:
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            # El zip contiene una carpeta raíz (ej: ffmpeg-master-latest-win64-gpl/)
            # Dentro hay bin/ffmpeg.exe y bin/ffprobe.exe
            for member in zf.namelist():
                # Extraer solo los ejecutables de la carpeta bin/
                if "/bin/ffmpeg.exe" in member or "/bin/ffprobe.exe" in member:
                    exe_name = Path(member).name
                    target = dest_dir / exe_name
                    with zf.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())
                    logger.info("Extraído: %s", target)
    except Exception as exc:
        raise RuntimeError(f"Error extrayendo FFmpeg: {exc}") from exc
    finally:
        try:
            Path(tmp_zip).unlink(missing_ok=True)
        except Exception:
            pass

    if progress_callback:
        progress_callback(1.0, "FFmpeg instalado correctamente")

    ffmpeg_exe = dest_dir / "ffmpeg.exe"
    if not ffmpeg_exe.exists():
        raise RuntimeError("No se encontró ffmpeg.exe tras la extracción")

    logger.info("FFmpeg instalado en: %s", ffmpeg_exe)
    return ffmpeg_exe
