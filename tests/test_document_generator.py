"""Tests del generador de documentos."""
import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.document_generator import DocumentGenerator, GuionData, ProcessingMetadata
from app.core.transcriber import TranscriptionResult, Segment, Word


def _make_transcription() -> TranscriptionResult:
    words = [Word(0.0, 0.5, "hola", 0.95), Word(0.5, 1.0, "mundo", 0.90)]
    segments = [
        Segment(id=0, start=0.0, end=5.0, text="Hola mundo, este es un tutorial.", words=words),
        Segment(id=1, start=5.0, end=10.0, text="Vamos a aprender a usar el sistema.", words=[]),
    ]
    return TranscriptionResult(
        full_text="Hola mundo, este es un tutorial. Vamos a aprender a usar el sistema.",
        segments=segments,
        words=words,
        language_detected="es",
        duration_seconds=10.0,
    )


def test_generate_transcription_txt(tmp_path):
    gen = DocumentGenerator()
    tr = _make_transcription()
    path = tmp_path / "transcripcion.txt"
    gen.generate_transcription_txt(tr, path)

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "[00:00:00]" in content
    assert "Hola mundo" in content


def test_generate_complete_docx(tmp_path):
    gen = DocumentGenerator()
    tr = _make_transcription()
    guion = GuionData(
        titulo="Tutorial de prueba",
        funcionalidad="Módulo de reportes",
        palabras_clave=["reporte", "sistema", "módulo"],
        introduccion="Este tutorial explica el módulo de reportes.",
        pasos=["Ingresar al módulo", "Seleccionar fecha", "Exportar PDF"],
        cierre="Así se genera un reporte.",
        resumen="Tutorial sobre el módulo de reportes del sistema.",
    )
    path = tmp_path / "informe_completo.docx"
    gen.generate_complete_docx(tr, guion, path)
    assert path.exists() and path.stat().st_size > 0


def test_generate_metadata_json(tmp_path):
    gen = DocumentGenerator()
    meta = ProcessingMetadata(
        video_name="tutorial.mp4",
        video_path="/videos/tutorial.mp4",
        duration_seconds=120.0,
        language_detected="es",
        transcription_confidence=0.93,
        ai_provider="Groq",
        ai_model="llama-3.3-70b-versatile",
        processed_at="2025-01-01T10:00:00",
        output_dir="/output/test",
    )
    path = tmp_path / "metadata.json"
    gen.generate_metadata_json(meta, path)

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["video_name"] == "tutorial.mp4"
    assert data["transcription_confidence"] == 0.93


def test_transcription_timestamped_text():
    tr = _make_transcription()
    ts_text = tr.to_timestamped_text()
    assert "[00:00:00]" in ts_text
    assert "[00:00:05]" in ts_text


def test_word_confidence_avg():
    tr = _make_transcription()
    avg = tr.get_word_confidence_avg()
    assert 0.0 <= avg <= 1.0
    assert abs(avg - 0.925) < 0.01
