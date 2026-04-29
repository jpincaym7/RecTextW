"""Repository pattern — toda la lógica de queries SQLite centralizada aquí."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from app.db.database import initialize_database
from app.db.models import ProcessingRecord
from app.utils.logger import get_logger

logger = get_logger()


class ProcessingRepository:
    """Encapsula toda la lógica de acceso a SQLite."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        initialize_database(db_path)

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Verifica e inicializa el esquema si es necesario."""
        initialize_database(self._db_path)

    def insert(self, record: ProcessingRecord) -> int:
        """Inserta un registro y retorna el ID generado."""
        sql = """
            INSERT INTO procesamientos
                (video_path, video_name, output_dir, status, duration_seconds,
                 language_detected, ai_provider, ai_model, transcription_confidence,
                 created_at, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            record.video_path,
            record.video_name,
            record.output_dir,
            record.status,
            record.duration_seconds,
            record.language_detected,
            record.ai_provider,
            record.ai_model,
            record.transcription_confidence,
            record.created_at.isoformat(),
            record.error_message,
        )
        with self._connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid

    def get_all(self, limit: int = 100) -> list[ProcessingRecord]:
        """Retorna los registros más recientes, limitados por `limit`."""
        sql = "SELECT * FROM procesamientos ORDER BY created_at DESC LIMIT ?"
        with self._connection() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_by_id(self, record_id: int) -> ProcessingRecord | None:
        """Retorna un registro por su ID, o None si no existe."""
        sql = "SELECT * FROM procesamientos WHERE id = ?"
        with self._connection() as conn:
            row = conn.execute(sql, (record_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def delete(self, record_id: int) -> None:
        """Elimina un registro por su ID."""
        with self._connection() as conn:
            conn.execute("DELETE FROM procesamientos WHERE id = ?", (record_id,))

    def delete_all(self) -> None:
        """Elimina todos los registros del historial."""
        with self._connection() as conn:
            conn.execute("DELETE FROM procesamientos")

    def update_status(self, record_id: int, status: str, error_message: str | None = None) -> None:
        """Actualiza el estado de un registro."""
        with self._connection() as conn:
            conn.execute(
                "UPDATE procesamientos SET status = ?, error_message = ? WHERE id = ?",
                (status, error_message, record_id),
            )

    def _row_to_record(self, row: sqlite3.Row) -> ProcessingRecord:
        return ProcessingRecord(
            id=row["id"],
            video_path=row["video_path"],
            video_name=row["video_name"],
            output_dir=row["output_dir"],
            status=row["status"],
            duration_seconds=row["duration_seconds"],
            language_detected=row["language_detected"],
            ai_provider=row["ai_provider"],
            ai_model=row["ai_model"],
            transcription_confidence=row["transcription_confidence"],
            created_at=datetime.fromisoformat(row["created_at"]),
            error_message=row["error_message"],
        )
