"""Orquestador del flujo completo de procesamiento de un video."""
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.core.audio_extractor import AudioExtractor
from app.core.transcriber import Transcriber
from app.core.ai_client import AIClientProtocol
from app.core.document_generator import DocumentGenerator, GuionData, ProcessingMetadata
from app.db.models import ProcessingRecord
from app.db.repository import ProcessingRepository
from app.utils.file_utils import clean_temp_files
from app.utils.logger import get_logger

logger = get_logger()


@dataclass
class PipelineCallbacks:
    """Agrupación de callbacks para el pipeline (DRY: evita firmas largas)."""
    on_progress: Callable[[float, str], None]
    on_stage_complete: Callable[[str], None]
    on_error: Callable[[str, Exception], None]
    on_cancelled: Callable[[], None]


@dataclass
class PipelineResult:
    record_id: int | None
    output_dir: Path
    transcription_text: str
    timestamped_text: str
    resumen: str
    titulo: str
    funcionalidad: str
    palabras_clave: list[str]
    guion_base: str
    duration_seconds: float
    language_detected: str
    transcription_confidence: float
    files_generated: list[str] = field(default_factory=list)


# Rangos de progreso por etapa (inicio%, fin%)
_STAGE_RANGES = {
    "metadata":   (0,  5),
    "audio":      (5,  20),
    "model":      (20, 30),
    "transcribe": (30, 70),
    "summary":    (70, 80),
    "titles":     (80, 88),
    "script":     (88, 93),
    "extras":     (93, 96),
    "export":     (96, 98),
    "save":       (98, 100),
}


class Pipeline:
    """Orquesta el flujo completo de procesamiento de un video."""

    def __init__(
        self,
        extractor: AudioExtractor,
        transcriber: Transcriber,
        ai_client: AIClientProtocol,
        doc_generator: DocumentGenerator,
        repository: ProcessingRepository,
        callbacks: PipelineCallbacks,
        cancel_flag: threading.Event,
    ) -> None:
        self._extractor = extractor
        self._transcriber = transcriber
        self._ai_client = ai_client
        self._doc_generator = doc_generator
        self._repository = repository
        self._cb = callbacks
        self._cancel_flag = cancel_flag

    def run(self, video_path: Path, output_dir: Path) -> PipelineResult:
        """Ejecuta el pipeline completo."""
        temp_wav: Path | None = None
        try:
            return self._execute(video_path, output_dir, lambda p: None)
        finally:
            if temp_wav and temp_wav.exists():
                clean_temp_files([temp_wav])

    def _execute(self, video_path: Path, output_dir: Path, _unused) -> PipelineResult:
        temp_wav = output_dir / "_audio_temp.wav"

        # ── Etapa 1: Metadatos ────────────────────────────────────────────
        self._progress("metadata", 0.5, "Analizando metadatos del video...")
        if self._cancel_flag.is_set():
            self._cb.on_cancelled(); return  # type: ignore[return-value]
        video_info = self._extractor.get_video_info(video_path)
        self._complete("metadata")

        # ── Etapa 2: Extracción de audio ──────────────────────────────────
        def audio_progress(p: float) -> None:
            self._progress("audio", p, f"Extrayendo audio... {p:.0%}")

        if self._cancel_flag.is_set():
            self._cb.on_cancelled(); return  # type: ignore[return-value]
        self._progress("audio", 0.0, "Extrayendo audio con FFmpeg...")
        self._extractor.extract_audio(video_path, temp_wav, audio_progress)
        self._complete("audio")

        # ── Etapa 3: Cargar modelo Whisper ────────────────────────────────
        if self._cancel_flag.is_set():
            self._cb.on_cancelled(); return  # type: ignore[return-value]
        self._progress("model", 0.0, "Cargando modelo Whisper en memoria...")
        self._transcriber.load_model(
            lambda p, msg: self._progress("model", p, msg)
        )
        self._complete("model")

        # ── Etapa 4: Transcripción ────────────────────────────────────────
        if self._cancel_flag.is_set():
            self._cb.on_cancelled(); return  # type: ignore[return-value]
        self._progress("transcribe", 0.0, "Transcribiendo audio con Whisper...")
        transcription = self._transcriber.transcribe(
            temp_wav,
            lambda p, msg: self._progress("transcribe", p, msg),
        )
        self._complete("transcribe")

        # ── Etapa 5: Resumen ──────────────────────────────────────────────
        if self._cancel_flag.is_set():
            self._cb.on_cancelled(); return  # type: ignore[return-value]
        self._progress("summary", 0.0, "Generando resumen ejecutivo con IA...")
        resumen = self._generate_ai_text("resumen", transcription.full_text)
        self._complete("summary")

        # ── Etapa 6: Título y palabras clave ─────────────────────────────
        if self._cancel_flag.is_set():
            self._cb.on_cancelled(); return  # type: ignore[return-value]
        self._progress("titles", 0.0, "Identificando título y palabras clave...")
        titles_raw = self._generate_ai_text("titulos", transcription.full_text)
        titulo, funcionalidad, palabras_clave = self._parse_titles_response(titles_raw)
        self._complete("titles")

        # ── Etapa 7: Guión base ───────────────────────────────────────────
        if self._cancel_flag.is_set():
            self._cb.on_cancelled(); return  # type: ignore[return-value]
        self._progress("script", 0.0, "Organizando guión base...")
        guion_base_text = self._generate_ai_text("guion_base", transcription.full_text)
        self._complete("script")

        # ── Etapa 8: Insumos adicionales ──────────────────────────────────
        if self._cancel_flag.is_set():
            self._cb.on_cancelled(); return  # type: ignore[return-value]
        self._progress("extras", 0.0, "Generando insumos adicionales...")
        introduccion, pasos, cierre = self._parse_guion_response(guion_base_text)
        guion_data = GuionData(
            titulo=titulo,
            funcionalidad=funcionalidad,
            palabras_clave=palabras_clave,
            introduccion=introduccion,
            pasos=pasos,
            cierre=cierre,
            resumen=resumen,
        )
        self._complete("extras")

        # ── Etapa 9: Exportar documentos ─────────────────────────────────
        if self._cancel_flag.is_set():
            self._cb.on_cancelled(); return  # type: ignore[return-value]
        self._progress("export", 0.0, "Exportando documentos...")
        files = self._export_documents(transcription, guion_data, output_dir)
        self._complete("export")

        # ── Etapa 10: Guardar en historial ────────────────────────────────
        if self._cancel_flag.is_set():
            self._cb.on_cancelled(); return  # type: ignore[return-value]
        self._progress("save", 0.0, "Guardando en historial...")
        record = ProcessingRecord(
            video_path=str(video_path),
            video_name=video_path.name,
            output_dir=str(output_dir),
            status="completed",
            duration_seconds=video_info.duration_seconds,
            language_detected=transcription.language_detected,
            ai_provider=self._ai_client.get_provider_name(),
            ai_model="",
            transcription_confidence=transcription.get_word_confidence_avg(),
            created_at=datetime.now(),
        )
        record_id = self._repository.insert(record)
        self._complete("save")

        clean_temp_files([temp_wav])

        return PipelineResult(
            record_id=record_id,
            output_dir=output_dir,
            transcription_text=transcription.full_text,
            timestamped_text=transcription.to_timestamped_text(),
            resumen=resumen,
            titulo=titulo,
            funcionalidad=funcionalidad,
            palabras_clave=palabras_clave,
            guion_base=guion_base_text,
            duration_seconds=video_info.duration_seconds,
            language_detected=transcription.language_detected,
            transcription_confidence=transcription.get_word_confidence_avg(),
            files_generated=files,
        )

    def _progress(self, stage: str, stage_pct: float, message: str) -> None:
        start, end = _STAGE_RANGES[stage]
        overall = start + (end - start) * stage_pct
        self._cb.on_progress(overall, message)

    def _complete(self, stage: str) -> None:
        start, end = _STAGE_RANGES[stage]
        self._cb.on_progress(end, f"Etapa completada: {stage}")
        self._cb.on_stage_complete(stage)

    def _generate_ai_text(self, prompt_name: str, transcription: str) -> str:
        from app.config import PROMPTS_DIR
        prompt_file = PROMPTS_DIR / f"{prompt_name}.txt"
        if prompt_file.exists():
            template = prompt_file.read_text(encoding="utf-8")
            system_prompt = template.split("{transcription}")[0].strip()
        else:
            system_prompt = "Analiza la siguiente transcripción y genera el contenido solicitado."
        return self._ai_client.generate_text(system_prompt, transcription)

    def _parse_titles_response(self, raw: str) -> tuple[str, str, list[str]]:
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end])
            kw = data.get("palabras_clave", [])
            if isinstance(kw, str):
                kw = [w.strip() for w in kw.split(",") if w.strip()]
            return (
                data.get("titulo", "Sin título"),
                data.get("funcionalidad", ""),
                kw,
            )
        except Exception:
            return "Sin título", "", []

    def _parse_guion_response(self, guion_text: str) -> tuple[str, list[str], str]:
        """Parsea INTRODUCCIÓN, PASOS y CIERRE del texto estructurado del guión."""
        import re

        intro_match = re.search(
            r"INTRODUCCI[ÓO]N\s*:\s*(.+?)(?=PASOS\s*:|CIERRE\s*:|$)",
            guion_text, re.IGNORECASE | re.DOTALL,
        )
        introduccion = intro_match.group(1).strip() if intro_match else ""

        steps_match = re.search(
            r"PASOS\s*:(.*?)(?=CIERRE\s*:|$)",
            guion_text, re.IGNORECASE | re.DOTALL,
        )
        pasos: list[str] = []
        if steps_match:
            pasos = re.findall(r"^\s*\d+\.\s+(.+)$", steps_match.group(1), re.MULTILINE)
        if not pasos:
            pasos = re.findall(r"^\s*\d+\.\s+(.+)$", guion_text, re.MULTILINE)
        if not pasos:
            pasos = [guion_text[:300]]

        cierre_match = re.search(
            r"CIERRE\s*:\s*(.+?)$",
            guion_text, re.IGNORECASE | re.DOTALL,
        )
        cierre = cierre_match.group(1).strip() if cierre_match else ""

        return introduccion, pasos, cierre

    def _export_documents(self, transcription, guion_data: GuionData, output_dir: Path) -> list[str]:
        files = []

        # 1. Transcripción en TXT (referencia rápida con timestamps)
        txt_path = output_dir / "transcripcion.txt"
        self._doc_generator.generate_transcription_txt(transcription, txt_path)
        files.append(str(txt_path))

        # 2. Informe completo en DOCX (resumen + guión + transcripción)
        docx_path = output_dir / "informe_completo.docx"
        self._doc_generator.generate_complete_docx(transcription, guion_data, docx_path)
        files.append(str(docx_path))

        # 3. Metadata JSON
        metadata = ProcessingMetadata(
            video_name=guion_data.titulo,
            video_path="",
            duration_seconds=transcription.duration_seconds,
            language_detected=transcription.language_detected,
            transcription_confidence=transcription.get_word_confidence_avg(),
            ai_provider=self._ai_client.get_provider_name(),
            ai_model="",
            processed_at=datetime.now().isoformat(),
            output_dir=str(output_dir),
        )
        json_path = output_dir / "metadata.json"
        self._doc_generator.generate_metadata_json(metadata, json_path)
        files.append(str(json_path))

        return files
