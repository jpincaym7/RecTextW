"""Worker QThread para ejecutar el pipeline sin bloquear la UI."""
import threading
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import DB_PATH
from app.core.audio_extractor import AudioExtractor
from app.core.transcriber import Transcriber
from app.core.ai_client import build_ai_client
from app.core.document_generator import DocumentGenerator
from app.core.pipeline import Pipeline, PipelineCallbacks
from app.db.repository import ProcessingRepository
from app.utils.file_utils import generate_output_dir
from app.utils.logger import get_logger
from app.utils.secrets import AIConfig

logger = get_logger()


class ProcessingWorker(QThread):
    """Ejecuta el pipeline completo en un hilo separado."""

    progress_updated     = pyqtSignal(float, str, str)   # (percent, stage_key, message)
    stage_completed      = pyqtSignal(str)                # stage_key
    processing_done      = pyqtSignal(dict)               # resultado completo
    processing_error     = pyqtSignal(str, str)           # (stage, error_message)
    processing_cancelled = pyqtSignal()

    def __init__(self, video_path: Path, ai_config: AIConfig, output_dir: Path) -> None:
        super().__init__()
        self._video_path = video_path
        self._ai_config = ai_config
        self._output_dir = output_dir
        self._cancel_flag = threading.Event()
        self._current_stage = "metadata"

    def run(self) -> None:
        """Ejecuta el pipeline en el hilo secundario."""
        try:
            extractor = AudioExtractor()
            transcriber = Transcriber()
            ai_client = build_ai_client(self._ai_config)
            doc_gen = DocumentGenerator()
            repository = ProcessingRepository(DB_PATH)

            callbacks = PipelineCallbacks(
                on_progress=self._on_progress,
                on_stage_complete=self._on_stage_complete,
                on_error=self._on_error,
                on_cancelled=self._on_cancelled,
            )

            pipeline = Pipeline(
                extractor=extractor,
                transcriber=transcriber,
                ai_client=ai_client,
                doc_generator=doc_gen,
                repository=repository,
                callbacks=callbacks,
                cancel_flag=self._cancel_flag,
            )

            result = pipeline.run(self._video_path, self._output_dir)
            if result is not None and not self._cancel_flag.is_set():
                self.processing_done.emit({
                    "record_id": result.record_id,
                    "output_dir": str(result.output_dir),
                    "transcription_text": result.transcription_text,
                    "timestamped_text": result.timestamped_text,
                    "resumen": result.resumen,
                    "titulo": result.titulo,
                    "funcionalidad": result.funcionalidad,
                    "palabras_clave": result.palabras_clave,
                    "guion_base": result.guion_base,
                    "duration_seconds": result.duration_seconds,
                    "language_detected": result.language_detected,
                    "transcription_confidence": result.transcription_confidence,
                    "files_generated": result.files_generated,
                })
        except Exception as exc:
            logger.error("Error en el worker de procesamiento: %s", exc, exc_info=True)
            self.processing_error.emit(self._current_stage, str(exc))

    def cancel(self) -> None:
        """Solicita la cancelación del procesamiento."""
        self._cancel_flag.set()
        logger.info("Cancelación solicitada por el usuario")

    def _on_progress(self, percent: float, message: str) -> None:
        self.progress_updated.emit(percent, self._current_stage, message)

    def _on_stage_complete(self, stage: str) -> None:
        self._current_stage = stage
        self.stage_completed.emit(stage)

    def _on_error(self, stage: str, exc: Exception) -> None:
        self.processing_error.emit(stage, str(exc))

    def _on_cancelled(self) -> None:
        self.processing_cancelled.emit()
