"""Dataclasses que representan las tablas de la base de datos."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class ProcessingRecord:
    """Representa un registro en la tabla `procesamientos` de SQLite."""
    video_path: str
    video_name: str
    output_dir: str
    status: Literal["completed", "error", "cancelled"]
    duration_seconds: float
    language_detected: str
    ai_provider: str
    ai_model: str
    transcription_confidence: float
    created_at: datetime = field(default_factory=datetime.now)
    error_message: str | None = None
    id: int | None = None
