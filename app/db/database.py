"""Conexión SQLite, creación del esquema y migraciones versionadas."""
import sqlite3
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger()

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS procesamientos (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    video_path              TEXT NOT NULL,
    video_name              TEXT NOT NULL,
    output_dir              TEXT NOT NULL,
    status                  TEXT NOT NULL CHECK(status IN ('completed', 'error', 'cancelled')),
    duration_seconds        REAL NOT NULL DEFAULT 0,
    language_detected       TEXT NOT NULL DEFAULT '',
    ai_provider             TEXT NOT NULL DEFAULT '',
    ai_model                TEXT NOT NULL DEFAULT '',
    transcription_confidence REAL NOT NULL DEFAULT 0,
    created_at              TEXT NOT NULL,
    error_message           TEXT
);
"""


def initialize_database(db_path: Path) -> None:
    """Crea la base de datos y aplica migraciones si es necesario."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _migrate(conn)
    logger.debug("Base de datos inicializada en %s", db_path)


def _migrate(conn: sqlite3.Connection) -> None:
    """Aplica migraciones incrementales según la versión del esquema."""
    conn.executescript(_SCHEMA_V1)
    row = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
    current_version = row[0] if row else 0

    if current_version < 1:
        conn.execute("INSERT OR REPLACE INTO schema_version(version) VALUES (1)")
        conn.commit()
        logger.info("Migración a schema v1 aplicada")
