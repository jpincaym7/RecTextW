"""Transcripción local con Whisper medium. Import lazy para arranque rápido."""
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.config import WHISPER_MODEL
from app.utils.logger import get_logger
from app.utils.whisper_check import is_model_available

logger = get_logger()

# Parámetros base para español técnico — beam_size se ajusta según device en runtime
_WHISPER_BASE_PARAMS = {
    "language": "es",
    "task": "transcribe",
    "temperature": 0.0,
    "compression_ratio_threshold": 2.4,
    "logprob_threshold": -1.0,
    "no_speech_threshold": 0.6,
    "condition_on_previous_text": True,
    "word_timestamps": True,
    "verbose": False,
    "fp16": False,
    "initial_prompt": (
        "Este es un videotutorial técnico en español sobre un sistema de software "
        "empresarial. Se explican funcionalidades, opciones de menú y procedimientos."
    ),
}

# CPU: decodificación greedy (beam_size=1) — 3-5× más rápido que beam_size=5
_PARAMS_CPU = {**_WHISPER_BASE_PARAMS, "beam_size": 1, "best_of": 1}
# GPU: beam search completo para máxima calidad
_PARAMS_GPU = {**_WHISPER_BASE_PARAMS, "beam_size": 5, "best_of": 5, "fp16": True}


class ModelNotFoundError(Exception):
    pass


class TranscriptionError(Exception):
    pass


@dataclass
class Word:
    start: float
    end: float
    word: str
    probability: float


@dataclass
class Segment:
    id: int
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0


@dataclass
class TranscriptionResult:
    full_text: str
    segments: list[Segment]
    words: list[Word]
    language_detected: str
    duration_seconds: float
    model_used: str = WHISPER_MODEL

    def to_timestamped_text(self) -> str:
        """Genera el texto con timestamps [HH:MM:SS] al inicio de cada segmento."""
        lines = []
        for seg in self.segments:
            h = int(seg.start // 3600)
            m = int((seg.start % 3600) // 60)
            s = int(seg.start % 60)
            ts = f"[{h:02d}:{m:02d}:{s:02d}]"
            lines.append(f"{ts} {seg.text.strip()}")
        return "\n".join(lines)

    def get_key_timestamps(self, max_count: int = 10) -> list[tuple[float, str]]:
        """Identifica timestamps relevantes (cambios de tema) mediante heurística de pausa."""
        if not self.segments:
            return []
        timestamps = [(0.0, self.segments[0].text.strip())]
        for i in range(1, len(self.segments)):
            gap = self.segments[i].start - self.segments[i - 1].end
            if gap > 1.5:
                timestamps.append((self.segments[i].start, self.segments[i].text.strip()))
            if len(timestamps) >= max_count:
                break
        return timestamps

    def get_word_confidence_avg(self) -> float:
        """Retorna la confianza promedio de la transcripción (0.0 a 1.0)."""
        if not self.words:
            return 0.0
        return sum(w.probability for w in self.words) / len(self.words)


class Transcriber:
    """Gestiona la carga del modelo Whisper y la transcripción de audio local."""

    def __init__(self) -> None:
        self._model = None
        self._model_loaded: bool = False
        self._device: str = "cpu"

    def is_model_available(self) -> bool:
        """Verifica si el modelo medium está descargado localmente."""
        return is_model_available(WHISPER_MODEL)

    def load_model(
        self,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> None:
        """Carga el modelo Whisper en memoria. Import lazy de whisper y torch."""
        if self._model_loaded:
            return
        if not self.is_model_available():
            raise ModelNotFoundError(
                f"El modelo Whisper '{WHISPER_MODEL}' no está descargado. "
                "Descárguelo desde la pantalla de inicio."
            )
        if progress_callback:
            progress_callback(0.0, "Cargando modelo Whisper en memoria...")

        # Import lazy — no ejecutar a nivel de módulo para no demorar el arranque
        import torch
        import whisper

        if torch.cuda.is_available():
            self._device = "cuda"
            logger.info("CUDA disponible — usando GPU para Whisper")
        else:
            self._device = "cpu"
            logger.info("CUDA no disponible — usando CPU para Whisper")

        self._model = whisper.load_model(WHISPER_MODEL, device=self._device)
        self._model_loaded = True
        logger.info("Modelo Whisper '%s' cargado en %s", WHISPER_MODEL, self._device)

        if progress_callback:
            progress_callback(1.0, f"Modelo cargado en {self._device.upper()}")

    def transcribe(
        self,
        audio_path: Path,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> TranscriptionResult:
        """Transcribe el archivo de audio y retorna el resultado estructurado."""
        if not self._model_loaded or self._model is None:
            raise TranscriptionError("El modelo no está cargado. Llame a load_model() primero.")

        on_gpu = self._device == "cuda"
        params = _PARAMS_GPU if on_gpu else _PARAMS_CPU
        device_label = "GPU" if on_gpu else "CPU (puede tardar varios minutos)"

        if progress_callback:
            progress_callback(0.05, f"Transcribiendo en {device_label}...")

        logger.info("Iniciando transcripción en %s: %s", self._device, audio_path)

        # Lanza un hilo daemon que actualiza el elapsed time cada 3 s mientras
        # Whisper bloquea — mantiene la UI activa aunque no haya progreso real.
        _done = threading.Event()

        def _elapsed_reporter() -> None:
            start = time.monotonic()
            fraction = 0.1
            while not _done.wait(timeout=3.0):
                elapsed = int(time.monotonic() - start)
                mins, secs = divmod(elapsed, 60)
                label = f"{mins}m {secs}s" if mins else f"{secs}s"
                if progress_callback:
                    progress_callback(fraction, f"Transcribiendo en {device_label}... ({label})")
                fraction = min(fraction + 0.02, 0.85)

        reporter = threading.Thread(target=_elapsed_reporter, daemon=True)
        reporter.start()

        try:
            result = self._model.transcribe(str(audio_path), **params)
        finally:
            _done.set()
            reporter.join(timeout=1.0)

        if progress_callback:
            progress_callback(0.9, "Procesando resultado...")

        segments = []
        all_words: list[Word] = []
        for raw_seg in result.get("segments", []):
            words = [
                Word(
                    start=w["start"],
                    end=w["end"],
                    word=w["word"],
                    probability=w.get("probability", 1.0),
                )
                for w in raw_seg.get("words", [])
            ]
            all_words.extend(words)
            segments.append(Segment(
                id=raw_seg["id"],
                start=raw_seg["start"],
                end=raw_seg["end"],
                text=raw_seg["text"],
                words=words,
                avg_logprob=raw_seg.get("avg_logprob", 0.0),
                no_speech_prob=raw_seg.get("no_speech_prob", 0.0),
            ))

        duration = segments[-1].end if segments else 0.0
        tr = TranscriptionResult(
            full_text=result.get("text", "").strip(),
            segments=segments,
            words=all_words,
            language_detected=result.get("language", "es"),
            duration_seconds=duration,
        )
        logger.info(
            "Transcripción completada: %d segmentos, idioma=%s, confianza=%.2f",
            len(segments), tr.language_detected, tr.get_word_confidence_avg()
        )
        if progress_callback:
            progress_callback(1.0, "Transcripción completada")
        return tr

    def unload_model(self) -> None:
        """Libera el modelo de memoria RAM/VRAM."""
        if self._model is not None:
            try:
                import torch
                del self._model
                self._model = None
                self._model_loaded = False
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                logger.info("Modelo Whisper liberado de memoria")
            except Exception as exc:
                logger.warning("Error al liberar el modelo: %s", exc)
