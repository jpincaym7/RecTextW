"""Worker QThread para descargar el modelo Whisper medium con progreso real."""
import io
import sys
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import WHISPER_MODEL
from app.utils.logger import get_logger

logger = get_logger()


class _ProgressTracker:
    """Intercepta el progreso de tqdm o urllib para reportarlo via callback."""

    def __init__(self, callback) -> None:
        self._callback = callback
        self._total = 0
        self._downloaded = 0

    def set_total(self, total: int) -> None:
        self._total = total

    def update(self, chunk_size: int) -> None:
        self._downloaded += chunk_size
        if self._total > 0:
            pct = min(self._downloaded / self._total, 1.0)
            speed_mb = chunk_size / (1024 * 1024)
            self._callback(pct, f"Descargando... {self._downloaded / (1024*1024):.1f} MB / {self._total / (1024*1024):.1f} MB")


class ModelDownloadWorker(QThread):
    """Descarga el modelo Whisper medium con reporte de progreso."""

    progress_updated = pyqtSignal(float, str)  # (percent 0-1, speed_info)
    download_done    = pyqtSignal()
    download_error   = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

    def run(self) -> None:
        """Descarga el modelo usando la API interna de Whisper."""
        try:
            logger.info("Iniciando descarga del modelo Whisper '%s'", WHISPER_MODEL)
            self.progress_updated.emit(0.0, "Iniciando descarga del modelo...")

            # Redirigir tqdm para capturar progreso
            self._patch_tqdm()

            import whisper
            whisper.load_model(WHISPER_MODEL)

            self._restore_tqdm()
            logger.info("Modelo Whisper descargado exitosamente")
            self.download_done.emit()

        except Exception as exc:
            logger.error("Error descargando modelo Whisper: %s", exc, exc_info=True)
            self._restore_tqdm()
            self.download_error.emit(str(exc))

    def _patch_tqdm(self) -> None:
        """Parchea tqdm para interceptar el progreso de descarga de Whisper."""
        try:
            import tqdm as tqdm_module
            original_init = tqdm_module.tqdm.__init__

            worker_ref = self

            def patched_init(self_tqdm, *args, **kwargs):
                original_init(self_tqdm, *args, **kwargs)
                if hasattr(self_tqdm, 'total') and self_tqdm.total:
                    worker_ref._tqdm_total = self_tqdm.total

            original_update = tqdm_module.tqdm.update

            def patched_update(self_tqdm, n=1):
                original_update(self_tqdm, n)
                if hasattr(self_tqdm, 'total') and self_tqdm.total and self_tqdm.total > 0:
                    pct = min(self_tqdm.n / self_tqdm.total, 1.0)
                    downloaded_mb = self_tqdm.n / (1024 * 1024)
                    total_mb = self_tqdm.total / (1024 * 1024)
                    worker_ref.progress_updated.emit(
                        pct, f"Descargando... {downloaded_mb:.0f} MB / {total_mb:.0f} MB"
                    )

            tqdm_module.tqdm.__init__ = patched_init
            tqdm_module.tqdm.update = patched_update
            self._original_tqdm_init = original_init
            self._original_tqdm_update = original_update
            self._tqdm_module = tqdm_module
        except ImportError:
            pass

    def _restore_tqdm(self) -> None:
        """Restaura tqdm a su estado original."""
        try:
            if hasattr(self, '_tqdm_module') and hasattr(self, '_original_tqdm_init'):
                self._tqdm_module.tqdm.__init__ = self._original_tqdm_init
                self._tqdm_module.tqdm.update = self._original_tqdm_update
        except Exception:
            pass
